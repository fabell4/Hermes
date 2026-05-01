"""LokiExporter — ships SpeedResult as structured log events to Loki's push API."""

from __future__ import annotations

import json
import logging
from datetime import timezone
from typing import Any
from urllib.parse import urlparse

import requests

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
        parsed = urlparse(stripped)

        # Validate scheme
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Loki URL must use http or https, got: '{parsed.scheme}'")

        # Validate hostname exists
        if not parsed.hostname:
            raise ValueError("Loki URL must include a hostname")

        # Warn if URL contains credentials
        if parsed.username or parsed.password:
            logger.warning(
                "Loki URL contains embedded credentials. "
                "Consider using environment variables or a reverse proxy for authentication."
            )

        # Validate timeout
        if timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")

        # Validate job label
        if not job_label or not job_label.strip():
            raise ValueError("Loki job label cannot be empty")

        self._push_url = self._build_push_url(stripped)
        self._job_label = job_label.strip()
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

        try:
            response = requests.post(
                self._push_url,
                data=body,
                headers={"Content-Type": "application/json"},
                timeout=self._timeout_seconds,
            )
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(f"Loki push connection error: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(f"Loki push timed out: {exc}") from exc

        if response.status_code >= 300:
            raise RuntimeError(
                f"Loki push failed with status {response.status_code}: {response.text[:500]}"
            )
        logger.debug("Loki event pushed successfully to %s", self._push_url)
