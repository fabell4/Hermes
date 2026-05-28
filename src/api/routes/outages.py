"""GET /api/outages and GET /api/outage-status — outage detection endpoints."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src import config as _cfg
from src import shared_state

router = APIRouter(tags=["outages"])

_503: dict[int | str, dict[str, Any]] = {
    503: {"description": "Database not yet available."}
}

# Module-level DB path for test mocking
DB_PATH = Path(_cfg.SQLITE_DB_PATH)


class OutageEventSchema(BaseModel):
    """Schema for a single outage event row."""

    id: int
    event_type: str
    timestamp: str
    duration_seconds: float | None = None
    isp_name: str | None = None
    asn: str | None = None
    bgp_unstable: bool | None = None
    cloudflare_outage_desc: str | None = None
    probe_results: str


class OutagesPage(BaseModel):
    """Paginated wrapper around a list of outage events."""

    events: list[OutageEventSchema]
    total: int
    page: int
    page_size: int


class OutageStatusSchema(BaseModel):
    """Current outage status from SharedState."""

    outage_in_progress: bool
    outage_start_time: str | None


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="No database found yet.")  # NOSONAR
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_outage_table(conn: sqlite3.Connection) -> None:
    """Create the outage_events table if it doesn't exist yet."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS outage_events (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type              TEXT    NOT NULL,
            timestamp               TEXT    NOT NULL,
            duration_seconds        REAL,
            isp_name                TEXT,
            asn                     TEXT,
            bgp_unstable            INTEGER,
            cloudflare_outage_desc  TEXT,
            probe_results           TEXT    NOT NULL
        )
        """
    )
    conn.commit()


def _row_to_schema(row: sqlite3.Row) -> OutageEventSchema:
    d = dict(row)
    # SQLite stores booleans as INTEGER; convert back
    raw_bgp = d.get("bgp_unstable")
    d["bgp_unstable"] = bool(raw_bgp) if raw_bgp is not None else None
    return OutageEventSchema(**d)


@router.get("/outages", responses=_503)
def get_outages(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
) -> OutagesPage:
    """Return paginated outage events, newest first."""
    with closing(_connect()) as conn:
        _ensure_outage_table(conn)
        total: int = conn.execute("SELECT COUNT(*) FROM outage_events").fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(
            "SELECT * FROM outage_events ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()

    return OutagesPage(
        events=[_row_to_schema(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/outage-status")
def get_outage_status() -> OutageStatusSchema:
    """Return the current outage status from SharedState."""
    start_time = shared_state.get_outage_start_time()
    return OutageStatusSchema(
        outage_in_progress=shared_state.get_outage_in_progress(),
        outage_start_time=start_time.isoformat() if start_time else None,
    )
