"""PrometheusExporter — updates Gauges and exposes a /metrics endpoint for scraping."""

from __future__ import annotations

import logging

from prometheus_client import Gauge, start_http_server

from src import config as app_config
from src.exporters.base_exporter import BaseExporter
from src.models.speed_result import SpeedResult

logger = logging.getLogger(__name__)

# Class-level Gauges so they are registered only once regardless of how many
# times the exporter is instantiated (prometheus_client raises if you register
# the same metric name twice in the default registry).
_DOWNLOAD = Gauge(
    "hermes_download_mbps",
    "Last measured download speed in Mbit/s",
    ["server_name", "server_location", "isp_name"],
)
_UPLOAD = Gauge(
    "hermes_upload_mbps",
    "Last measured upload speed in Mbit/s",
    ["server_name", "server_location", "isp_name"],
)
_PING = Gauge(
    "hermes_ping_ms",
    "Last measured latency in milliseconds",
    ["server_name", "server_location", "isp_name"],
)
_JITTER = Gauge(
    "hermes_jitter_ms",
    "Last measured jitter in milliseconds (None when not reported by server)",
    ["server_name", "server_location", "isp_name"],
)
_PACKET_LOSS = Gauge(
    "hermes_packet_loss_pct",
    "Last measured packet loss percentage (None when not reported by server)",
    ["server_name", "server_location", "isp_name"],
)
_QUALITY_SCORE = Gauge(
    "hermes_quality_score",
    "Composite connection quality score 0–100 (higher is better)",
    ["server_name", "server_location", "isp_name"],
)
_SLA_OK = Gauge(
    "hermes_sla_ok",
    "1 if last result met all configured SLA thresholds, 0 if breached, -1 if SLA disabled",
    ["server_name", "server_location", "isp_name"],
)


class PrometheusExporter(BaseExporter):
    """Export speed-test results as Prometheus Gauges.

    A lightweight HTTP server is started on *port* the first time an instance
    is created.  Scrape the ``/metrics`` endpoint (e.g. with Grafana Alloy or
    Prometheus) to collect the data.

    Label cardinality control
    -------------------------
    By default each unique (server_name, server_location, isp_name) combination
    creates a separate Prometheus time series.  In environments with many
    servers or ISPs this can grow without bound.  Set the environment variable
    ``PROMETHEUS_DISABLE_LABELS=true`` to collapse all label values to empty
    strings, keeping cardinality at exactly one time series per metric.
    """

    # Guard so the HTTP server is started at most once per process.
    _server_started: bool = False

    def __init__(self, port: int = 8000, disable_labels: bool | None = None) -> None:
        """
        Args:
            port: TCP port for the Prometheus metrics HTTP server.
            disable_labels: When True, all label values are set to empty strings
                to prevent unbounded cardinality.  Defaults to the value of the
                ``PROMETHEUS_DISABLE_LABELS`` environment variable.
        """
        if port <= 0 or port > 65535:
            raise ValueError(f"Invalid port number: {port}")

        self._port = port
        # Resolve label behaviour: explicit arg takes precedence over env var.
        self._disable_labels: bool = (
            disable_labels
            if disable_labels is not None
            else app_config.PROMETHEUS_DISABLE_LABELS
        )
        if self._disable_labels:
            logger.info(
                "Prometheus label cardinality management enabled — "
                "all label values collapsed to empty strings."
            )
        self._start_server(port)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _start_server(self, port: int) -> None:
        """Start the Prometheus HTTP server on *port*, or log if already running."""
        if PrometheusExporter._server_started:
            logger.debug(
                "Prometheus metrics server already running; skipping start on port %d",
                port,
            )
            return
        try:
            start_http_server(port)
            PrometheusExporter._server_started = True
            logger.info("Prometheus metrics server started on port %d", port)
        except OSError as e:
            if "Address already in use" in str(e) or "Only one usage" in str(e):
                raise RuntimeError(
                    f"Prometheus metrics port {port} is already in use. "
                    f"Set PROMETHEUS_PORT to a different value or stop the conflicting service."
                ) from e
            raise RuntimeError(
                f"Failed to start Prometheus server on port {port}: {e}"
            ) from e

    def _build_labels(self, result: SpeedResult) -> dict[str, str]:
        """Return the Prometheus label dict for *result*, respecting cardinality setting."""
        if self._disable_labels:
            return {"server_name": "", "server_location": "", "isp_name": ""}
        return {
            "server_name": result.server_name or "",
            "server_location": result.server_location or "",
            "isp_name": result.isp_name or "",
        }

    def _update_optional_gauges(
        self, result: SpeedResult, labels: dict[str, str]
    ) -> None:
        """Update gauges whose source field may be absent from a result."""
        if result.jitter_ms is not None:
            _JITTER.labels(**labels).set(result.jitter_ms)
        if result.packet_loss_pct is not None:
            _PACKET_LOSS.labels(**labels).set(result.packet_loss_pct)
        if result.quality_score is not None:
            _QUALITY_SCORE.labels(**labels).set(result.quality_score)
        # SLA: 1=pass, 0=fail, -1=disabled (not configured)
        sla_value = -1.0 if result.sla_ok is None else (1.0 if result.sla_ok else 0.0)
        _SLA_OK.labels(**labels).set(sla_value)

    # ------------------------------------------------------------------
    # BaseExporter interface
    # ------------------------------------------------------------------

    def export(self, result: SpeedResult) -> None:
        """Update all Gauges with values from *result*.

        When label cardinality management is active (``disable_labels=True``),
        all label values are replaced with empty strings so that only a single
        time series exists per metric.
        """
        labels = self._build_labels(result)
        try:
            _DOWNLOAD.labels(**labels).set(result.download_mbps)
            _UPLOAD.labels(**labels).set(result.upload_mbps)
            _PING.labels(**labels).set(result.ping_ms)
            self._update_optional_gauges(result, labels)
            logger.debug(
                "Prometheus gauges updated — down=%.2f up=%.2f ping=%.2f "
                "jitter=%s loss=%s quality=%s sla_ok=%s",
                result.download_mbps,
                result.upload_mbps,
                result.ping_ms,
                result.jitter_ms,
                result.packet_loss_pct,
                result.quality_score,
                result.sla_ok,
            )
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to update Prometheus gauges: %s", exc)
            raise
