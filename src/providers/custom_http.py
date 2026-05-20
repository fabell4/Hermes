"""CustomHttpProvider — speed test via user-supplied HTTP endpoints."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from urllib.parse import urlparse

from src import config
from src.models.speed_result import SpeedResult
from src.providers.base import BaseTestProvider

_log = logging.getLogger(__name__)

_ALLOWED_SCHEMES = {"http", "https"}
_PING_TIMEOUT_S = 5
_DOWNLOAD_CHUNK_BYTES = 1 << 20  # 1 MB per iteration chunk
_USER_AGENT = "hermes-speedtest/1.0"


def _validate_url(url: str, label: str) -> None:
    """Validate URL scheme to prevent SSRF via non-HTTP schemes.

    Args:
        url: The URL to validate.
        label: Human-readable label for error messages (e.g. "Download").

    Raises:
        RuntimeError: If the scheme is not http or https.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise RuntimeError(
            f"{label} URL has unsupported scheme '{parsed.scheme}'. "
            f"Only http and https are allowed."
        )
    if not parsed.netloc:
        raise RuntimeError(f"{label} URL is missing a host.")


class CustomHttpProvider(BaseTestProvider):
    """Speed test against user-supplied HTTP download/upload endpoints.

    Download: streams a GET response for up to duration_s seconds and measures
    throughput from bytes received.
    Upload: POSTs a randomly-generated payload and measures throughput from
    bytes sent vs. elapsed time.
    Ping: a HEAD request to the download URL before the download test.

    URL configuration:
        SPEEDTEST_CUSTOM_URL_DOWNLOAD — required; used for both ping and download.
        SPEEDTEST_CUSTOM_URL_UPLOAD   — optional; upload is skipped if absent.

    Test parameter configuration (see config.py for defaults):
        SPEEDTEST_CUSTOM_DURATION_S       — max seconds to stream during download.
        SPEEDTEST_CUSTOM_CONNECTIONS      — parallel download connections (Phase 4).
        SPEEDTEST_CUSTOM_CHUNK_SIZE_MB    — upload payload size in MB.
    """

    def __init__(
        self,
        download_url: str | None = None,
        upload_url: str | None = None,
        duration_s: int = 10,
        connections: int = 1,
        chunk_size_mb: int = 25,
    ) -> None:
        self._download_url = download_url
        self._upload_url = upload_url
        self._duration_s = duration_s
        self._connections = connections
        self._chunk_size_bytes = chunk_size_mb * 1_048_576  # MB → bytes

    @property
    def name(self) -> str:
        return "custom"

    def run(self) -> SpeedResult:
        """Run ping, download, and (optionally) upload tests.

        Raises:
            RuntimeError: If download URL is not configured, URL scheme is invalid,
                          or the download request fails.
        """
        if not self._download_url:
            raise RuntimeError(
                "CustomHttpProvider requires SPEEDTEST_CUSTOM_URL_DOWNLOAD to be set."
            )
        _validate_url(self._download_url, "Download")
        if self._upload_url:
            _validate_url(self._upload_url, "Upload")

        try:
            ping_ms = self._measure_ping()
            download_mbps = self._measure_download()
            upload_mbps = self._measure_upload() if self._upload_url else 0.0

            _tz_name = config.TIMEZONE
            try:
                _tz = ZoneInfo(_tz_name)
            except ZoneInfoNotFoundError:
                _tz = ZoneInfo("UTC")

            return SpeedResult(
                timestamp=datetime.now(_tz),
                download_mbps=round(download_mbps, 2),
                upload_mbps=round(upload_mbps, 2),
                ping_ms=round(ping_ms, 2),
                server_name="",
                server_location="",
                server_id=None,
                jitter_ms=None,
                isp_name=None,
                packet_loss_pct=None,
            )
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Custom HTTP test failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Ping
    # ------------------------------------------------------------------

    def _measure_ping(self) -> float:
        """Measure latency with a HEAD request. Returns ping_ms."""
        assert self._download_url is not None  # guaranteed by run() guard
        try:
            t0 = time.monotonic()
            requests.head(
                self._download_url,
                timeout=_PING_TIMEOUT_S,
                allow_redirects=True,
                headers={"User-Agent": _USER_AGENT},
            )
            return (time.monotonic() - t0) * 1_000
        except requests.RequestException as exc:
            _log.warning("Custom HTTP ping failed: %s; using 0.0 ms", exc)
            return 0.0

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def _measure_download(self) -> float:
        """Stream a GET response for up to duration_s seconds. Returns download_mbps."""
        assert self._download_url is not None  # guaranteed by run() guard
        total_bytes = 0
        start = time.monotonic()
        deadline = start + self._duration_s

        try:
            with requests.get(
                self._download_url,
                stream=True,
                timeout=self._duration_s + 10,
                headers={"User-Agent": _USER_AGENT},
            ) as resp:
                resp.raise_for_status()
                for chunk in resp.iter_content(chunk_size=_DOWNLOAD_CHUNK_BYTES):
                    total_bytes += len(chunk)
                    if time.monotonic() >= deadline:
                        break
        except requests.RequestException as exc:
            raise RuntimeError(f"Custom HTTP download failed: {exc}") from exc

        elapsed = max(time.monotonic() - start, 0.001)
        download_mbps = (total_bytes * 8) / elapsed / 1_000_000
        _log.debug("Custom download: %.2f Mbps (%d bytes)", download_mbps, total_bytes)
        return download_mbps

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def _measure_upload(self) -> float:
        """POST a generated payload and measure throughput. Returns upload_mbps."""
        assert self._upload_url is not None  # guaranteed by run() guard
        payload_size = max(self._chunk_size_bytes, _DOWNLOAD_CHUNK_BYTES)
        payload = os.urandom(payload_size)

        try:
            start = time.monotonic()
            resp = requests.post(
                self._upload_url,
                data=payload,
                timeout=self._duration_s + 10,
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": _USER_AGENT,
                },
            )
            elapsed = max(time.monotonic() - start, 0.001)

            if not resp.ok:
                _log.warning(
                    "Custom upload returned HTTP %d; measurement may be inaccurate",
                    resp.status_code,
                )
        except requests.RequestException as exc:
            raise RuntimeError(f"Custom HTTP upload failed: {exc}") from exc

        upload_mbps = (len(payload) * 8) / elapsed / 1_000_000
        _log.debug("Custom upload: %.2f Mbps (%d bytes)", upload_mbps, len(payload))
        return upload_mbps
