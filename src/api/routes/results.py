"""GET /api/results and GET /api/results/latest — reads from the SQLite DB."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

DB_PATH = Path("data/hermes.db")

router = APIRouter(tags=["results"])

_503: dict[int | str, dict[str, Any]] = {503: {"description": "Database not yet available."}}


class SpeedResultSchema(BaseModel):
    """Schema for a single speed-test result row."""

    id: int
    timestamp: str
    download_mbps: float
    upload_mbps: float
    ping_ms: float
    jitter_ms: Optional[float] = None
    isp_name: Optional[str] = None
    server_name: str
    server_location: str
    server_id: Optional[int] = None


class ResultsPage(BaseModel):
    """Paginated wrapper around a list of speed-test results."""

    results: list[SpeedResultSchema]
    total: int
    page: int
    page_size: int


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="No database found yet.")
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/results", responses=_503)
def get_results(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
) -> ResultsPage:
    """Return paginated results, newest first."""
    conn = _connect()
    try:
        total: int = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(
            "SELECT * FROM results ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()
    finally:
        conn.close()

    return ResultsPage(
        results=[SpeedResultSchema(**dict(r)) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/results/latest", responses=_503)
def get_latest_result() -> Optional[SpeedResultSchema]:
    """Return the most recent result, or null if the database is empty."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM results ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    return SpeedResultSchema(**dict(row))
