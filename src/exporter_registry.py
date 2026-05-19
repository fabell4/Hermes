"""Shared exporter registry for Hermes.

Defines the canonical mapping from exporter name → factory callable so that
both the scheduler (``src/main.py``) and the API trigger route
(``src/api/routes/trigger.py``) build exporters from the same source,
eliminating duplicate factory definitions.

Factory callables return ``BaseExporter | None``.  A ``None`` return means the
exporter is not available in the current environment (e.g. Loki when
``LOKI_URL`` is unset) and should be silently skipped by the caller.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from src import config
from src.exporters.base_exporter import BaseExporter
from src.exporters.csv_exporter import CSVExporter
from src.exporters.influxdb_exporter import InfluxDBExporter
from src.exporters.loki_exporter import LokiExporter
from src.exporters.prometheus_exporter import PrometheusExporter
from src.exporters.sqlite_exporter import SQLiteExporter

logger = logging.getLogger(__name__)


def _build_loki() -> LokiExporter | None:
    """Return a LokiExporter if ``LOKI_URL`` is configured, otherwise ``None``."""
    if not config.LOKI_URL:
        logger.warning(
            "Loki exporter is enabled but LOKI_URL is not set — skipping."
        )
        return None
    return LokiExporter(url=config.LOKI_URL, job_label=config.LOKI_JOB_LABEL)


def _build_influxdb() -> InfluxDBExporter | None:
    """Return an InfluxDBExporter if ``INFLUXDB_URL`` and ``INFLUXDB_TOKEN`` are configured."""
    if not config.INFLUXDB_URL:
        logger.warning(
            "InfluxDB exporter is enabled but INFLUXDB_URL is not set — skipping."
        )
        return None
    if not config.INFLUXDB_TOKEN:
        logger.warning(
            "InfluxDB exporter is enabled but INFLUXDB_TOKEN is not set — skipping."
        )
        return None
    return InfluxDBExporter(
        url=config.INFLUXDB_URL,
        token=config.INFLUXDB_TOKEN,
        org=config.INFLUXDB_ORG,
        bucket=config.INFLUXDB_BUCKET,
        timeout_ms=config.INFLUXDB_TIMEOUT_MS,
    )


# All known exporters and how to build them.
# Keys are StrEnum values (strings) for runtime flexibility.
EXPORTER_REGISTRY: dict[str, Callable[[], BaseExporter | None]] = {
    "csv": lambda: CSVExporter(
        path=config.CSV_LOG_PATH,
        max_rows=config.CSV_MAX_ROWS,
        retention_days=config.CSV_RETENTION_DAYS,
    ),
    "prometheus": lambda: PrometheusExporter(port=config.PROMETHEUS_PORT),
    "loki": _build_loki,
    "sqlite": lambda: SQLiteExporter(
        path=config.SQLITE_DB_PATH,
        max_rows=config.SQLITE_MAX_ROWS,
        retention_days=config.SQLITE_RETENTION_DAYS,
    ),
    "influxdb": _build_influxdb,
}
