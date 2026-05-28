"""NDT7Provider — speed test via M-Lab NDT7 public infrastructure."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
import websockets.exceptions
from websockets.sync.client import connect as ws_connect
from websockets.typing import Subprotocol

from src import config
from src.models.speed_result import SpeedResult
from src.providers.base import BaseTestProvider

_log = logging.getLogger(__name__)

_LOCATE_URL = "https://locate.measurementlab.net/v2/nearest/ndt/ndt7"
_NDT7_SUBPROTOCOL = "net.measurementlab.ndt.v7"
_CONNECT_TIMEOUT_S = 10
_TEST_DURATION_S = 10
_RECV_TIMEOUT_S = 15  # safety margin above NDT7's 13 s protocol maximum


class NDT7Provider(BaseTestProvider):
    """Speed test using M-Lab's NDT7 WebSocket infrastructure.

    Requires no user configuration — server selection is automatic via the
    M-Lab Locate v2 API. Uses the websockets library synchronous client.

    Download: counts bytes received while the server streams binary frames,
    stopping when the server closes the connection (~10 s).
    Upload: sends binary frames for _TEST_DURATION_S using a dedicated thread
    while a receiver thread collects server-side byte counts from text frames.
    Ping: derived from TCPInfo.MinRTT in the final download measurement message.
    """

    @property
    def name(self) -> str:
        return "ndt7"

    def run(self) -> SpeedResult:
        """Run download + upload tests and return a SpeedResult.

        Raises:
            RuntimeError: If locate, download, or upload fails.
        """
        try:
            server = self._locate_server()
            download_mbps, rtt_ms = self._run_download(server["dl_url"])
            upload_mbps = self._run_upload(server["ul_url"])

            _tz_name = config.TIMEZONE
            try:
                _tz = ZoneInfo(_tz_name)
            except ZoneInfoNotFoundError:
                _tz = ZoneInfo("UTC")

            return SpeedResult(
                timestamp=datetime.now(_tz),
                download_mbps=round(download_mbps, 2),
                upload_mbps=round(upload_mbps, 2),
                ping_ms=round(rtt_ms, 2),
                server_name=server["host"],
                server_location=server["location"],
                server_id=None,
                jitter_ms=None,
                isp_name=None,
                packet_loss_pct=None,
            )
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"NDT7 test failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Server discovery
    # ------------------------------------------------------------------

    def _locate_server(self) -> dict[str, str]:
        """Query M-Lab Locate v2 API for the nearest NDT7 server."""
        try:
            resp = requests.get(
                _LOCATE_URL,
                timeout=_CONNECT_TIMEOUT_S,
                headers={"User-Agent": f"hermes-ndt7-client/{config.APP_VERSION}"},
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"NDT7 locate request failed: {exc}") from exc

        data: dict[str, Any] = resp.json()
        results = data.get("results", [])
        if not results:
            raise RuntimeError(
                "NDT7 locate returned no servers (M-Lab may be at capacity)."
            )

        first = results[0]
        urls: dict[str, str] = first.get("urls", {})

        # Locate v2 uses triple-slash keys: "wss:///ndt/v7/download"
        dl_url = urls.get("wss:///ndt/v7/download")
        ul_url = urls.get("wss:///ndt/v7/upload")

        if not dl_url or not ul_url:
            raise RuntimeError(
                f"NDT7 locate response missing WebSocket URLs. Keys: {list(urls)}"
            )

        loc = first.get("location", {})
        city, country = loc.get("city", ""), loc.get("country", "")
        location = f"{city}, {country}".strip(", ") if (city or country) else ""

        _log.debug("NDT7 server: %s (%s)", first.get("machine", ""), location)
        return {
            "dl_url": dl_url,
            "ul_url": ul_url,
            "host": first.get("machine", ""),
            "location": location,
        }

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_download_frames(
        ws: Any, deadline: float
    ) -> tuple[int, dict[str, Any]]:
        """Receive frames from an open download WebSocket until deadline or close.

        Returns:
            (total_bytes, last_measurement) where last_measurement is the final
            parsed text frame (contains TCPInfo for RTT extraction).
        """
        total_bytes = 0
        last_measurement: dict[str, Any] = {}
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                message = ws.recv(timeout=remaining)
            except (TimeoutError, websockets.exceptions.ConnectionClosed):
                break
            if isinstance(message, bytes):
                total_bytes += len(message)
            elif isinstance(message, str):
                try:
                    last_measurement = json.loads(message)
                except json.JSONDecodeError:
                    _log.debug("NDT7: ignoring unparseable text frame: %r", message[:80])
        return total_bytes, last_measurement

    def _run_download(self, url: str) -> tuple[float, float]:
        """Download test. Returns (download_mbps, rtt_ms).

        Counts bytes in binary frames until the server closes the connection
        or _RECV_TIMEOUT_S elapses. RTT is extracted from the final text
        measurement's TCPInfo.MinRTT (microseconds → ms).
        """
        total_bytes = 0
        last_measurement: dict[str, Any] = {}
        start = time.monotonic()

        try:
            with ws_connect(
                url,
                subprotocols=[Subprotocol(_NDT7_SUBPROTOCOL)],
                open_timeout=_CONNECT_TIMEOUT_S,
                close_timeout=5,
            ) as ws:
                deadline = time.monotonic() + _RECV_TIMEOUT_S
                total_bytes, last_measurement = self._collect_download_frames(
                    ws, deadline
                )
        except websockets.exceptions.WebSocketException as exc:
            raise RuntimeError(f"NDT7 download WebSocket error: {exc}") from exc

        elapsed = max(time.monotonic() - start, 0.001)
        download_mbps = (total_bytes * 8) / elapsed / 1_000_000

        tcp_info = last_measurement.get("TCPInfo", {})
        rtt_us = tcp_info.get("MinRTT") or tcp_info.get("RTT")
        rtt_ms = (rtt_us / 1_000) if rtt_us is not None else 0.0

        _log.debug("NDT7 download: %.2f Mbps, RTT %.2f ms", download_mbps, rtt_ms)
        return download_mbps, rtt_ms

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------
    # Upload helpers (static to keep _run_upload complexity low)
    # ------------------------------------------------------------------

    @staticmethod
    def _upload_sender(
        ws: Any,
        chunk: bytes,
        sender_bytes: list[int],
        stop_event: threading.Event,
    ) -> None:
        """Send 8 KB binary frames until stop_event is set or duration expires."""
        deadline = time.monotonic() + _TEST_DURATION_S
        try:
            while not stop_event.is_set() and time.monotonic() < deadline:
                ws.send(chunk)
                sender_bytes[0] += len(chunk)
        except Exception:  # pylint: disable=broad-exception-caught  # NOSONAR  # nosec
            _log.debug("NDT7 upload sender: send interrupted.")
        finally:
            stop_event.set()
            try:
                ws.close()
            except Exception:  # pylint: disable=broad-exception-caught  # NOSONAR  # nosec
                _log.debug("NDT7 upload sender: error closing WebSocket.")

    @staticmethod
    def _upload_receiver(
        ws: Any,
        server_num_bytes: list[int],
        stop_event: threading.Event,
    ) -> None:
        """Collect AppInfo.NumBytes from server measurement frames."""
        deadline = time.monotonic() + _TEST_DURATION_S + 3
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    message = ws.recv(timeout=remaining)
                except (TimeoutError, websockets.exceptions.ConnectionClosed):
                    break
                if isinstance(message, str):
                    try:
                        nb = json.loads(message).get("AppInfo", {}).get("NumBytes")
                        if nb is not None:
                            server_num_bytes.append(int(nb))
                    except ValueError:
                        pass
        except Exception:  # pylint: disable=broad-exception-caught  # NOSONAR  # nosec
            _log.debug("NDT7 upload receiver: connection error during receive.")
        finally:
            stop_event.set()

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def _run_upload(self, url: str) -> float:
        """Upload test. Returns upload_mbps.

        A sender thread pushes 8 KB binary frames for _TEST_DURATION_S.
        A receiver thread collects AppInfo.NumBytes from server text frames.
        Server-measured bytes are preferred over client-side bytes for accuracy.
        """
        chunk = os.urandom(1 << 13)  # 8 KB — NDT7 spec starting size
        sender_bytes: list[int] = [0]
        server_num_bytes: list[int] = []
        stop_event = threading.Event()

        start = time.monotonic()
        try:
            with ws_connect(
                url,
                subprotocols=[Subprotocol(_NDT7_SUBPROTOCOL)],
                open_timeout=_CONNECT_TIMEOUT_S,
                close_timeout=5,
            ) as ws:
                t_recv = threading.Thread(
                    target=self._upload_receiver,
                    args=(ws, server_num_bytes, stop_event),
                    daemon=True,
                )
                t_send = threading.Thread(
                    target=self._upload_sender,
                    args=(ws, chunk, sender_bytes, stop_event),
                    daemon=True,
                )
                t_recv.start()
                t_send.start()
                t_send.join(timeout=_TEST_DURATION_S + 3)
                stop_event.set()
                t_recv.join(timeout=5)
        except websockets.exceptions.WebSocketException as exc:
            if not sender_bytes[0]:
                raise RuntimeError(f"NDT7 upload connection failed: {exc}") from exc

        elapsed = max(time.monotonic() - start, 0.001)
        # Prefer server-measured bytes (more accurate); fall back to client-side
        measured_bytes = server_num_bytes[-1] if server_num_bytes else sender_bytes[0]
        upload_mbps = (measured_bytes * 8) / elapsed / 1_000_000

        _log.debug("NDT7 upload: %.2f Mbps", upload_mbps)
        return upload_mbps
