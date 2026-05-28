"""Time-of-day analysis for Hermes.

Computes per-hour averages from the results database to reveal congestion
patterns (e.g. download speeds dipping between 20:00 and 22:00).

Timestamps are evaluated in UTC as stored in the database.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

# Static SQL templates — no user input interpolated into these strings.
_SQL_HOURLY_RECENT = """
        SELECT
            CAST(strftime('%H', timestamp) AS INTEGER) AS hour,
            COUNT(*)                                   AS sample_count,
            ROUND(AVG(download_mbps), 2)               AS avg_download_mbps,
            ROUND(AVG(upload_mbps),   2)               AS avg_upload_mbps,
            ROUND(AVG(ping_ms),       2)               AS avg_ping_ms,
            ROUND(MIN(download_mbps), 2)               AS min_download_mbps,
            ROUND(MAX(download_mbps), 2)               AS max_download_mbps
        FROM results
        WHERE timestamp >= datetime('now', ?)
        GROUP BY hour
        ORDER BY hour ASC
    """

_SQL_HOURLY_ALL = """
        SELECT
            CAST(strftime('%H', timestamp) AS INTEGER) AS hour,
            COUNT(*)                                   AS sample_count,
            ROUND(AVG(download_mbps), 2)               AS avg_download_mbps,
            ROUND(AVG(upload_mbps),   2)               AS avg_upload_mbps,
            ROUND(AVG(ping_ms),       2)               AS avg_ping_ms,
            ROUND(MIN(download_mbps), 2)               AS min_download_mbps,
            ROUND(MAX(download_mbps), 2)               AS max_download_mbps
        FROM results
        GROUP BY hour
        ORDER BY hour ASC
    """


@dataclass(frozen=True)
class HourlyStats:
    """Aggregate statistics for a single hour-of-day slot (0–23)."""

    hour: int
    sample_count: int
    avg_download_mbps: float
    avg_upload_mbps: float
    avg_ping_ms: float
    min_download_mbps: float
    max_download_mbps: float


def analyse(db_path: str | Path, days: int = 30) -> list[HourlyStats]:
    """Return per-hour aggregate stats drawn from the last *days* days.

    Only hours with at least one sample are included.
    Results are ordered by hour ascending (0–23).

    Args:
        db_path: Path to the SQLite database.
        days: Lookback window in days (0 = all time).

    Returns:
        A list of HourlyStats, one per distinct hour observed.
    """
    path = Path(db_path)
    if not path.exists():
        return []

    if days > 0:
        sql: str = _SQL_HOURLY_RECENT
        params: list[object] = [f"-{days} days"]
    else:
        sql = _SQL_HOURLY_ALL
        params = []

    with closing(sqlite3.connect(str(path))) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()

    return [HourlyStats(**dict(r)) for r in rows]
