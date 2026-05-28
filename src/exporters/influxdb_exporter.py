"""InfluxDBExporter — ships SpeedResult measurements to an InfluxDB v2 instance."""

from __future__ import annotations

import logging
from datetime import timezone
from typing import Any
from urllib.parse import urlparse

from influxdb_client import InfluxDBClient  # type: ignore[import-untyped]
from influxdb_client.client.write_api import SYNCHRONOUS  # type: ignore[import-untyped]
from influxdb_client.client.exceptions import InfluxDBError  # type: ignore[import-untyped]

from ..models.speed_result import SpeedResult
from .base_exporter import BaseExporter

logger = logging.getLogger(__name__)

_MEASUREMENT = "speedtest"


class InfluxDBExporter(BaseExporter):
    """Export speed-test results to an InfluxDB v2 bucket.

    Each :class:`~src.models.speed_result.SpeedResult` is written as a single
    point in the ``speedtest`` measurement with the following schema:

    **Tags** (indexed, low-cardinality):

    - ``server_name``
    - ``server_location``
    - ``isp_name``

    **Fields** (numeric measurements):

    - ``download_mbps``
    - ``upload_mbps``
    - ``ping_ms``
    - ``jitter_ms`` (omitted when ``None``)
    - ``packet_loss_pct`` (omitted when ``None``)
    - ``quality_score`` (omitted when ``None``)
    - ``sla_ok`` (0 / 1 integer; omitted when ``None``)
    - ``server_id`` (omitted when ``None``)

    The timestamp stored in InfluxDB is the UTC epoch time from
    ``SpeedResult.timestamp`` with **nanosecond** precision.
    """

    @staticmethod
    def _validate_url(url: str, parsed: Any) -> None:
        """Validate the InfluxDB URL argument."""
        if not url or not url.strip():
            raise ValueError("InfluxDB URL is required")
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"InfluxDB URL must use http or https, got: '{parsed.scheme}'"
            )
        if not parsed.hostname:
            raise ValueError("InfluxDB URL must include a hostname")

    @staticmethod
    def _validate_credentials(token: str, org: str, bucket: str) -> None:
        """Validate the InfluxDB authentication and destination arguments."""
        if not token or not token.strip():
            raise ValueError("InfluxDB token is required")
        if not org or not org.strip():
            raise ValueError("InfluxDB org is required")
        if not bucket or not bucket.strip():
            raise ValueError("InfluxDB bucket is required")

    @staticmethod
    def _validate_config(
        url: str,
        parsed: Any,
        token: str,
        org: str,
        bucket: str,
        timeout_ms: int,
    ) -> None:
        """Validate constructor arguments, raising ValueError on invalid input."""
        InfluxDBExporter._validate_url(url, parsed)
        InfluxDBExporter._validate_credentials(token, org, bucket)
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")

    def __init__(
        self,
        url: str,
        token: str,
        org: str,
        bucket: str,
        timeout_ms: int = 10_000,
    ) -> None:
        """
        Args:
            url: InfluxDB base URL, e.g. ``https://influxdb.example.com:8086``.
            token: API token with write permission on *bucket*.
            org: InfluxDB organisation name or ID.
            bucket: Destination bucket name.
            timeout_ms: HTTP request timeout in milliseconds (default 10 000).
        """
        stripped = url.strip() if url else ""
        parsed = urlparse(stripped)
        self._validate_config(stripped, parsed, token, org, bucket, timeout_ms)

        self._url = stripped
        self._org = org.strip()
        self._bucket = bucket.strip()

        self._client = InfluxDBClient(
            url=self._url,
            token=token.strip(),
            org=self._org,
            timeout=timeout_ms,
        )
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)

    # ------------------------------------------------------------------
    # BaseExporter interface
    # ------------------------------------------------------------------

    def export(self, result: SpeedResult) -> None:
        """Write *result* as a single point to InfluxDB."""
        point = self._build_point(result)
        try:
            self._write_api.write(bucket=self._bucket, record=point)
            logger.debug(
                "InfluxDB point written to bucket '%s' at %s",
                self._bucket,
                result.timestamp.isoformat(),
            )
        except InfluxDBError as exc:
            raise RuntimeError(
                f"InfluxDB write failed (HTTP {exc.response.status if exc.response else '?'}): "
                f"{exc}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"InfluxDB write failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_point(result: SpeedResult) -> Any:
        """Construct the line-protocol point dict consumed by ``WriteApi``."""
        from influxdb_client import Point  # type: ignore[import-untyped]

        ts = result.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        p = (
            Point(_MEASUREMENT)
            .time(ts)
            # Tags
            .tag("server_name", result.server_name or "unknown")
            .tag("server_location", result.server_location or "unknown")
            .tag("isp_name", result.isp_name or "unknown")
            # Required numeric fields
            .field("download_mbps", float(result.download_mbps))
            .field("upload_mbps", float(result.upload_mbps))
            .field("ping_ms", float(result.ping_ms))
        )

        if result.jitter_ms is not None:
            p = p.field("jitter_ms", float(result.jitter_ms))
        if result.packet_loss_pct is not None:
            p = p.field("packet_loss_pct", float(result.packet_loss_pct))
        if result.quality_score is not None:
            p = p.field("quality_score", float(result.quality_score))
        if result.sla_ok is not None:
            p = p.field("sla_ok", int(result.sla_ok))
        if result.server_id is not None:
            p = p.field("server_id", int(result.server_id))

        return p

    def close(self) -> None:
        """Release InfluxDB client resources. Call on application shutdown."""
        try:
            self._write_api.close()
            self._client.close()
        except Exception as exc:  # pragma: no cover
            logger.warning("Error closing InfluxDB client: %s", exc)
