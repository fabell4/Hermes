"""GET /api/analysis/* — anomaly detection, time-of-day, and trend analysis."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src import config as _cfg
from src.models.speed_result import SpeedResult as DomainResult
from src.services import anomaly_detector, time_of_day, trend_analysis

router = APIRouter(tags=["analysis"])

_503: dict[int | str, dict[str, Any]] = {
    503: {"description": "Database not yet available."}
}

# Module-level DB path for test mocking
DB_PATH = Path(_cfg.SQLITE_DB_PATH)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _require_db() -> None:
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="No database found yet.")


def _open_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_domain(row: sqlite3.Row) -> DomainResult:
    """Convert a DB row to a SpeedResult domain object."""
    ts_raw: str = row["timestamp"]
    try:
        ts = datetime.fromisoformat(ts_raw)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        ts = datetime.now(timezone.utc)

    return DomainResult(
        timestamp=ts,
        download_mbps=float(row["download_mbps"]),
        upload_mbps=float(row["upload_mbps"]),
        ping_ms=float(row["ping_ms"]),
        jitter_ms=row["jitter_ms"],
        isp_name=row["isp_name"],
        server_name=row["server_name"] or "",
        server_location=row["server_location"] or "",
        server_id=row["server_id"],
        packet_loss_pct=row["packet_loss_pct"],
        quality_score=row["quality_score"],
        sla_ok=bool(row["sla_ok"]) if row["sla_ok"] is not None else None,
    )


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------


class AnomalyFlagSchema(BaseModel):
    """Details about one anomalous metric in a single result."""

    metric: str
    value: float
    baseline_mean: float
    baseline_stdev: float
    z_score: float


class AnnotatedResultSchema(BaseModel):
    """A speed-test result annotated with anomaly detection output."""

    id: int
    timestamp: str
    download_mbps: float
    upload_mbps: float
    ping_ms: float
    jitter_ms: float | None = None
    isp_name: str | None = None
    server_name: str
    server_location: str
    is_anomaly: bool
    anomaly_flags: list[AnomalyFlagSchema]


@router.get("/analysis/anomalies", responses=_503)
def get_anomalies(
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    window: Annotated[int, Query(ge=3, le=200)] = 20,
    threshold: Annotated[float, Query(ge=0.5, le=10.0)] = 2.5,
) -> list[AnnotatedResultSchema]:
    """Return the most recent *limit* results annotated with anomaly detection.

    Each result is compared against the *window* results that precede it.
    Results without enough baseline data are returned with ``is_anomaly=False``.

    - ``limit``: how many results to annotate and return (default 50).
    - ``window``: baseline window size for z-score computation (default 20).
    - ``threshold``: z-score magnitude that triggers an anomaly flag (default 2.5).
    """
    _require_db()

    fetch = limit + window
    with closing(_open_db()) as conn:
        rows = conn.execute(
            "SELECT * FROM results ORDER BY timestamp DESC LIMIT ?",
            (fetch,),
        ).fetchall()

    if not rows:
        return []

    # rows is newest→oldest; reverse to chronological order for sliding window
    rows_asc = list(reversed(rows))
    n_total = len(rows_asc)
    start_idx = max(0, n_total - limit)

    detector = anomaly_detector.AnomalyDetector(window=window, threshold=threshold)
    annotated: list[AnnotatedResultSchema] = []

    for i in range(start_idx, n_total):
        row = rows_asc[i]
        baseline_rows = rows_asc[max(0, i - window) : i]
        baseline = [_row_to_domain(r) for r in baseline_rows]
        result = _row_to_domain(row)
        detection = detector.check(result, baseline)
        annotated.append(
            AnnotatedResultSchema(
                id=row["id"],
                timestamp=row["timestamp"],
                download_mbps=result.download_mbps,
                upload_mbps=result.upload_mbps,
                ping_ms=result.ping_ms,
                jitter_ms=result.jitter_ms,
                isp_name=result.isp_name,
                server_name=result.server_name,
                server_location=result.server_location,
                is_anomaly=detection.is_anomaly,
                anomaly_flags=[
                    AnomalyFlagSchema(
                        metric=f.metric,
                        value=f.value,
                        baseline_mean=f.baseline_mean,
                        baseline_stdev=f.baseline_stdev,
                        z_score=f.z_score,
                    )
                    for f in detection.flags
                ],
            )
        )

    # Return newest first
    return list(reversed(annotated))


# ---------------------------------------------------------------------------
# Time-of-day analysis
# ---------------------------------------------------------------------------


class HourlyStatsSchema(BaseModel):
    """Average speeds for one hour-of-day slot."""

    hour: int
    sample_count: int
    avg_download_mbps: float
    avg_upload_mbps: float
    avg_ping_ms: float
    min_download_mbps: float
    max_download_mbps: float


@router.get("/analysis/time-of-day")
def get_time_of_day(
    days: Annotated[int, Query(ge=0, le=3650)] = 30,
) -> list[HourlyStatsSchema]:
    """Return average download, upload, and ping grouped by hour of day (UTC).

    Only hours with at least one sample in the lookback window are returned.
    Use ``days=0`` to query all time.
    """
    stats = time_of_day.analyse(DB_PATH, days=days)
    return [HourlyStatsSchema(**vars(s)) for s in stats]


# ---------------------------------------------------------------------------
# Trend analysis
# ---------------------------------------------------------------------------


class MonthlyStatsSchema(BaseModel):
    """Aggregate statistics for one calendar month."""

    month: str
    sample_count: int
    avg_download_mbps: float
    avg_upload_mbps: float
    avg_ping_ms: float


class TrendReportSchema(BaseModel):
    """Trend analysis report with monthly stats and regression slopes."""

    monthly_stats: list[MonthlyStatsSchema]
    download_slope: float | None = None
    upload_slope: float | None = None
    ping_slope: float | None = None
    degradation_detected: bool
    months_available: int


@router.get("/analysis/trends")
def get_trends(
    months: Annotated[int, Query(ge=0, le=120)] = 6,
) -> TrendReportSchema:
    """Return month-over-month statistics and degradation detection.

    - ``months``: lookback window in calendar months (0 = all time).

    Slopes are expressed as Mbps (or ms) per calendar month from the
    linear regression line.  Negative download/upload slope or positive
    ping slope indicates degradation.
    """
    report = trend_analysis.analyse(DB_PATH, months=months)
    return TrendReportSchema(
        monthly_stats=[MonthlyStatsSchema(**vars(s)) for s in report.monthly_stats],
        download_slope=report.download_slope,
        upload_slope=report.upload_slope,
        ping_slope=report.ping_slope,
        degradation_detected=report.degradation_detected,
        months_available=report.months_available,
    )
