"""GET /api/results and GET /api/results/latest — reads from the SQLite DB."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src import config as _cfg
from src.api.auth import require_api_key

router = APIRouter(tags=["results"])

_503: dict[int | str, dict[str, Any]] = {
    503: {"description": "Database not yet available."}
}

# Module-level DB path for test mocking
DB_PATH = Path(_cfg.SQLITE_DB_PATH)


class SpeedResultSchema(BaseModel):
    """Schema for a single speed-test result row."""

    id: int
    timestamp: str
    download_mbps: float
    upload_mbps: float
    ping_ms: float
    jitter_ms: float | None = None
    isp_name: str | None = None
    server_name: str
    server_location: str
    server_id: int | None = None
    packet_loss_pct: float | None = None
    quality_score: float | None = None
    sla_ok: bool | None = None
    note: str | None = None


class ResultsPage(BaseModel):
    """Paginated wrapper around a list of speed-test results."""

    results: list[SpeedResultSchema]
    total: int
    page: int
    page_size: int


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="No database found yet.")  # NOSONAR — S8415 false positive: every route that calls _connect() already declares responses=_503
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_note_column(conn: sqlite3.Connection) -> None:
    """Add the note column if the database pre-dates the annotations feature."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(results)").fetchall()}
    if "note" not in cols:
        conn.execute("ALTER TABLE results ADD COLUMN note TEXT")
        conn.commit()


class NoteRequest(BaseModel):
    """Request body for updating a result's annotation note."""

    note: str | None = Field(None, max_length=500)


@router.get("/results", responses=_503)
def get_results(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
) -> ResultsPage:
    """Return paginated results, newest first."""
    with closing(_connect()) as conn:
        total: int = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(
            "SELECT * FROM results ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()

    return ResultsPage(
        results=[SpeedResultSchema(**dict(r)) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/results/latest", responses=_503)
def get_latest_result() -> SpeedResultSchema | None:
    """Return the most recent result, or null if the database is empty."""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM results ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()

    if row is None:
        return None
    return SpeedResultSchema(**dict(row))


@router.put(
    "/results/{result_id}/note",
    dependencies=[Depends(require_api_key)],
    responses={**_503, 404: {"description": "Result not found."}},
)
def update_note(result_id: int, body: NoteRequest) -> SpeedResultSchema:
    """Set or clear the annotation note on a specific result."""
    with closing(_connect()) as conn:
        _ensure_note_column(conn)
        row = conn.execute(
            "SELECT id FROM results WHERE id = ?", (result_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=404, detail=f"Result {result_id} not found."
            )
        conn.execute(
            "UPDATE results SET note = ? WHERE id = ?", (body.note or None, result_id)
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM results WHERE id = ?", (result_id,)
        ).fetchone()
    return SpeedResultSchema(**dict(updated))
