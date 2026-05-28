"""Trend analysis for Hermes.

Computes per-month aggregate stats and detects sustained degradation via
linear regression across consecutive calendar months.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MonthlyStats:
    """Aggregate statistics for a single calendar month."""

    month: str  # "YYYY-MM"
    sample_count: int
    avg_download_mbps: float
    avg_upload_mbps: float
    avg_ping_ms: float


@dataclass(frozen=True)
class TrendReport:
    """Complete trend analysis report.

    Attributes:
        monthly_stats: Per-month stats ordered oldest → newest.
        download_slope: Linear regression slope (Mbps per month). Negative = degradation.
        upload_slope:   Linear regression slope (Mbps per month). Negative = degradation.
        ping_slope:     Linear regression slope (ms per month).   Positive = degradation.
        degradation_detected: True when any slope indicates worsening performance.
        months_available: Number of distinct calendar months in the data.
    """

    monthly_stats: list[MonthlyStats]
    download_slope: float | None
    upload_slope: float | None
    ping_slope: float | None
    degradation_detected: bool
    months_available: int


def _linear_slope(xs: list[float], ys: list[float]) -> float | None:
    """Return the OLS regression slope, or None when undefined (< 2 points)."""
    n = len(xs)
    if n < 2:
        return None
    sx = sum(xs)
    sy = sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    sxx = sum(x * x for x in xs)
    denom = n * sxx - sx * sx
    if denom == 0.0:
        return None
    return (n * sxy - sx * sy) / denom


def analyse(db_path: str | Path, months: int = 6) -> TrendReport:
    """Return a TrendReport covering the last *months* calendar months.

    Args:
        db_path: Path to the SQLite database.
        months: How many calendar months to include (0 = all time).

    Returns:
        TrendReport with monthly stats and regression-derived slopes.
    """
    path = Path(db_path)
    if not path.exists():
        return TrendReport(
            monthly_stats=[],
            download_slope=None,
            upload_slope=None,
            ping_slope=None,
            degradation_detected=False,
            months_available=0,
        )

    where = ""
    params: list[object] = []
    if months > 0:
        where = "WHERE timestamp >= datetime('now', ?)"
        params.append(f"-{months} months")

    sql = f"""
        SELECT
            strftime('%Y-%m', timestamp)   AS month,
            COUNT(*)                       AS sample_count,
            ROUND(AVG(download_mbps), 2)   AS avg_download_mbps,
            ROUND(AVG(upload_mbps),   2)   AS avg_upload_mbps,
            ROUND(AVG(ping_ms),       2)   AS avg_ping_ms
        FROM results
        {where}
        GROUP BY month
        ORDER BY month ASC
    """

    with closing(sqlite3.connect(str(path))) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()

    monthly = [MonthlyStats(**dict(r)) for r in rows]

    if len(monthly) < 2:
        return TrendReport(
            monthly_stats=monthly,
            download_slope=None,
            upload_slope=None,
            ping_slope=None,
            degradation_detected=False,
            months_available=len(monthly),
        )

    xs = list(range(len(monthly)))
    dl_slope = _linear_slope(xs, [m.avg_download_mbps for m in monthly])
    ul_slope = _linear_slope(xs, [m.avg_upload_mbps for m in monthly])
    pg_slope = _linear_slope(xs, [m.avg_ping_ms for m in monthly])

    degradation = (
        (dl_slope is not None and dl_slope < 0)
        or (ul_slope is not None and ul_slope < 0)
        or (pg_slope is not None and pg_slope > 0)
    )

    return TrendReport(
        monthly_stats=monthly,
        download_slope=round(dl_slope, 4) if dl_slope is not None else None,
        upload_slope=round(ul_slope, 4) if ul_slope is not None else None,
        ping_slope=round(pg_slope, 4) if pg_slope is not None else None,
        degradation_detected=degradation,
        months_available=len(monthly),
    )
