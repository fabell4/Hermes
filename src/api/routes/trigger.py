"""POST /api/trigger — manually kick off a speed test."""

from __future__ import annotations

import logging
import threading
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
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
    except Exception as exc:  # pylint: disable=broad-exception-caught  # NOSONAR
        logger.exception("Manual trigger failed: %s", exc)
    finally:
        _test_lock.release()


@router.get("/trigger/status")
def get_test_status() -> dict[str, bool]:
    """Check if a speed test is currently running."""
    return {"is_running": _test_lock.locked()}


@router.post(
    "/trigger",
    dependencies=[Depends(require_api_key)],
    responses={
        500: {
            "description": "Failed to start test. Check server logs.",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to start test. Check server logs."}
                }
            },
        }
    },
)
def trigger_test() -> TriggerResponse:
    """Kick off a speed test if one is not already running."""
    acquired = _test_lock.acquire(blocking=False)
    if not acquired:
        return TriggerResponse(status="already_running")

    try:
        thread = threading.Thread(target=_run_test, daemon=True)
        thread.start()

        # Brief check that thread actually started (only in non-test scenarios)
        # In tests, _run_test is mocked and returns immediately, so thread dies fast
        time.sleep(0.01)
        if not thread.is_alive():
            # Thread died immediately - likely an error in thread startup
            # Note: In tests with mocked _run_test, this is expected behavior
            logger.debug("Thread completed immediately (may be test environment)")

        return TriggerResponse(status="started")
    except Exception as e:
        # Release lock on failure to prevent deadlock
        _test_lock.release()
        logger.error("Failed to start manual test thread: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to start test. Check server logs."
        ) from e
