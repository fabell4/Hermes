"""PrometheusExporter — updates Gauges and exposes a /metrics endpoint for scraping."""

from __future__ import annotations

import logging

from prometheus_client import Gauge, start_http_server

from ..models.speed_result import SpeedResult
from .base_exporter import BaseExporter

logger = logging.getLogger(__name__)

# Class-level Gauges so they are registered only once regardless of how many
# times the exporter is instantiated (prometheus_client raises if you register
# the same metric name twice in the default registry).
_DOWNLOAD = Gauge(
    "hermes_download_mbps",
    "Last measured download speed in Mbit/s",
    ["server_name", "server_location"],
)
_UPLOAD = Gauge(
    "hermes_upload_mbps",
    "Last measured upload speed in Mbit/s",
    ["server_name", "server_location"],
)
_PING = Gauge(
    "hermes_ping_ms",
    "Last measured latency in milliseconds",
    ["server_name", "server_location"],
)

# Guard so the HTTP server is started at most once per process.
_server_started: bool = False


class PrometheusExporter(BaseExporter):
    """Export speed-test results as Prometheus Gauges.

    A lightweight HTTP server is started on *port* the first time an instance
    is created.  Scrape the ``/metrics`` endpoint (e.g. with Grafana Alloy or
    Prometheus) to collect the data.
    """

    def __init__(self, port: int = 8000) -> None:
        global _server_started
        self._port = port
        if not _server_started:
            start_http_server(port)
            _server_started = True
            logger.info("Prometheus metrics server started on port %d", port)
        else:
            logger.debug(
                "Prometheus metrics server already running; skipping start on port %d",
                port,
            )

    # ------------------------------------------------------------------
    # BaseExporter interface
    # ------------------------------------------------------------------

    def export(self, result: SpeedResult) -> None:
        """Update all Gauges with values from *result*."""
        labels = {
            "server_name": result.server_name or "",
            "server_location": result.server_location or "",
        }
        try:
            _DOWNLOAD.labels(**labels).set(result.download_mbps)
            _UPLOAD.labels(**labels).set(result.upload_mbps)
            _PING.labels(**labels).set(result.ping_ms)
            logger.debug(
                "Prometheus gauges updated — down=%.2f up=%.2f ping=%.2f",
                result.download_mbps,
                result.upload_mbps,
                result.ping_ms,
            )
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to update Prometheus gauges: %s", exc)
            raise
