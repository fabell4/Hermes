"""LokiExporter — ships SpeedResult as structured log events to Loki's push API."""

from __future__ import annotations

import json
import logging
from datetime import timezone
from typing import Any
from urllib import error, request
from urllib.parse import urlparse

from ..models.speed_result import SpeedResult
from .base_exporter import BaseExporter

logger = logging.getLogger(__name__)

_LOKI_PUSH_PATH = "/loki/api/v1/push"


class LokiExporter(BaseExporter):
    """Export speed-test results to a Loki HTTP endpoint."""

    def __init__(
        self,
        url: str,
        job_label: str = "hermes_speedtest",
        timeout_seconds: float = 5.0,
        static_labels: dict[str, str] | None = None,
    ) -> None:
        if not url or not url.strip():
            raise ValueError("Loki URL is required")
        stripped = url.strip()
        scheme = urlparse(stripped).scheme.lower()
        if scheme not in ("http", "https"):
            raise ValueError(f"Loki URL must use http or https, got: '{scheme}'")
        self._push_url = self._build_push_url(stripped)
        self._job_label = job_label
        self._timeout_seconds = timeout_seconds
        self._static_labels = static_labels or {}

    @staticmethod
    def _build_push_url(url: str) -> str:
        if url.endswith(_LOKI_PUSH_PATH):
            return url
        if url.endswith("/"):
            return f"{url[:-1]}{_LOKI_PUSH_PATH}"
        return f"{url}{_LOKI_PUSH_PATH}"

    @staticmethod
    def _to_loki_timestamp_ns(result: SpeedResult) -> str:
        ts = result.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return str(int(ts.timestamp() * 1_000_000_000))

    def _build_labels(self, result: SpeedResult) -> dict[str, str]:
        labels: dict[str, str] = {
            "job": self._job_label,
            "server_name": result.server_name or "unknown",
            "server_location": result.server_location or "unknown",
        }
        labels.update(self._static_labels)
        return labels

    def _build_payload(self, result: SpeedResult) -> dict[str, Any]:
        line = json.dumps(result.to_dict(), ensure_ascii=False, separators=(",", ":"))
        return {
            "streams": [
                {
                    "stream": self._build_labels(result),
                    "values": [[self._to_loki_timestamp_ns(result), line]],
                }
            ]
        }

    def export(self, result: SpeedResult) -> None:
        payload = self._build_payload(result)
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=self._push_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self._timeout_seconds) as response:
                status = getattr(response, "status", response.getcode())
                if status >= 300:
                    response_body = response.read().decode("utf-8", errors="replace")
                    raise RuntimeError(
                        f"Loki push failed with status {status}: {response_body[:500]}"
                    )
            logger.debug("Loki event pushed successfully to %s", self._push_url)
        except error.HTTPError as exc:
            raw = exc.read() if exc.fp else b""
            body_text = (
                raw.decode("utf-8", errors="replace")
                if isinstance(raw, bytes)
                else str(raw)
            )
            raise RuntimeError(
                f"Loki push HTTP error {exc.code}: {body_text[:500]}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"Loki push connection error: {exc}") from exc
