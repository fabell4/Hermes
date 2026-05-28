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
        raise HTTPException(  # NOSONAR python:S8415
            status_code=503, detail="No database found yet."
        )
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


# Fixed parameterised queries: every optional filter uses (? IS NULL OR condition)
# so the SQL is a compile-time constant — no string concatenation, no injection risk.
_FILTER_COUNT_SQL = """
SELECT COUNT(*) FROM results
WHERE (? IS NULL OR DATE(timestamp) >= ?)
  AND (? IS NULL OR DATE(timestamp) <= ?)
  AND (? IS NULL OR download_mbps >= ?)
  AND (? IS NULL OR download_mbps <= ?)
  AND (? IS NULL OR upload_mbps >= ?)
  AND (? IS NULL OR upload_mbps <= ?)
  AND (? IS NULL OR ping_ms <= ?)
  AND (? IS NULL OR server_name = ?)
  AND (? IS NULL OR isp_name = ?)
"""

_FILTER_DATA_SQL = """
SELECT * FROM results
WHERE (? IS NULL OR DATE(timestamp) >= ?)
  AND (? IS NULL OR DATE(timestamp) <= ?)
  AND (? IS NULL OR download_mbps >= ?)
  AND (? IS NULL OR download_mbps <= ?)
  AND (? IS NULL OR upload_mbps >= ?)
  AND (? IS NULL OR upload_mbps <= ?)
  AND (? IS NULL OR ping_ms <= ?)
  AND (? IS NULL OR server_name = ?)
  AND (? IS NULL OR isp_name = ?)
ORDER BY timestamp DESC LIMIT ? OFFSET ?
"""


@router.get("/results", responses=_503)
def get_results(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
    date_from: Annotated[
        str | None, Query(description="Start date filter inclusive (YYYY-MM-DD)")
    ] = None,
    date_to: Annotated[
        str | None, Query(description="End date filter inclusive (YYYY-MM-DD)")
    ] = None,
    min_download: Annotated[
        float | None, Query(ge=0, description="Minimum download speed (Mbps)")
    ] = None,
    max_download: Annotated[
        float | None, Query(ge=0, description="Maximum download speed (Mbps)")
    ] = None,
    min_upload: Annotated[
        float | None, Query(ge=0, description="Minimum upload speed (Mbps)")
    ] = None,
    max_upload: Annotated[
        float | None, Query(ge=0, description="Maximum upload speed (Mbps)")
    ] = None,
    max_ping: Annotated[
        float | None, Query(ge=0, description="Maximum ping (ms)")
    ] = None,
    server: Annotated[str | None, Query(description="Exact server name match")] = None,
    isp: Annotated[str | None, Query(description="Exact ISP name match")] = None,
) -> ResultsPage:
    """Return paginated results, newest first. Supports optional filtering."""
    # Each optional filter is passed twice: once for the IS NULL bypass, once
    # for the actual comparison. Python None becomes SQL NULL, so when no filter
    # is supplied the (NULL IS NULL) condition is TRUE and the row is included.
    filter_params: list[object] = [
        date_from,
        date_from,
        date_to,
        date_to,
        min_download,
        min_download,
        max_download,
        max_download,
        min_upload,
        min_upload,
        max_upload,
        max_upload,
        max_ping,
        max_ping,
        server,
        server,
        isp,
        isp,
    ]

    with closing(_connect()) as conn:
        total: int = conn.execute(_FILTER_COUNT_SQL, filter_params).fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(
            _FILTER_DATA_SQL, [*filter_params, page_size, offset]
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
