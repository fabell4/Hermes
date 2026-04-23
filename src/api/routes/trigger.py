"""POST /api/trigger — manually kick off a speed test."""

from __future__ import annotations

import logging
import threading
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src import config, runtime_config
from src.api.auth import require_api_key
from src.exporters.csv_exporter import CSVExporter
from src.exporters.loki_exporter import LokiExporter
from src.exporters.prometheus_exporter import PrometheusExporter
from src.exporters.sqlite_exporter import SQLiteExporter
from src.result_dispatcher import ResultDispatcher
from src.services.speedtest_runner import SpeedtestRunner

logger = logging.getLogger(__name__)

router = APIRouter(tags=["trigger"])

# Simple in-process lock — one test at a time.
_test_lock = threading.Lock()


class TriggerResponse(BaseModel):
    """Response schema for the manual trigger endpoint."""

    status: Literal["started", "already_running"]


def _run_test() -> None:
    """Execute a speed test in the background and write results via exporters."""

    exporter_registry = {
        "csv": lambda: CSVExporter(
            path=config.CSV_LOG_PATH,
            max_rows=config.CSV_MAX_ROWS,
            retention_days=config.CSV_RETENTION_DAYS,
        ),
        "sqlite": lambda: SQLiteExporter(
            path=config.SQLITE_DB_PATH,
            max_rows=config.SQLITE_MAX_ROWS,
            retention_days=config.SQLITE_RETENTION_DAYS,
        ),
        "prometheus": lambda: PrometheusExporter(port=config.PROMETHEUS_PORT),
        "loki": lambda: (
            LokiExporter(url=config.LOKI_URL, job_label=config.LOKI_JOB_LABEL)
            if config.LOKI_URL
            else None
        ),
    }

    enabled = runtime_config.get_enabled_exporters(config.ENABLED_EXPORTERS)
    dispatcher = ResultDispatcher()
    for name in enabled:
        factory = exporter_registry.get(name)
        if factory is None:
            continue
        exp = factory()
        if exp is not None:
            dispatcher.add_exporter(name, exp)

    try:
        result = SpeedtestRunner().run()
        dispatcher.dispatch(result)
        logger.info(
            "Manual trigger complete: %.1f / %.1f Mbps, %.1f ms",
            result.download_mbps,
            result.upload_mbps,
            result.ping_ms,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception("Manual trigger failed: %s", exc)
    finally:
        _test_lock.release()


@router.post("/trigger", dependencies=[Depends(require_api_key)])
def trigger_test() -> TriggerResponse:
    """Kick off a speed test if one is not already running."""
    acquired = _test_lock.acquire(blocking=False)
    if not acquired:
        return TriggerResponse(status="already_running")

    thread = threading.Thread(target=_run_test, daemon=True)
    thread.start()
    return TriggerResponse(status="started")
