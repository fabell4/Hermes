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
        raise HTTPException(status_code=503, detail="No database found yet.")  # NOSONAR python:S8415
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
    conditions: list[str] = []
    params: list[object] = []

    if date_from is not None:
        conditions.append("DATE(timestamp) >= ?")
        params.append(date_from)
    if date_to is not None:
        conditions.append("DATE(timestamp) <= ?")
        params.append(date_to)
    if min_download is not None:
        conditions.append("download_mbps >= ?")
        params.append(min_download)
    if max_download is not None:
        conditions.append("download_mbps <= ?")
        params.append(max_download)
    if min_upload is not None:
        conditions.append("upload_mbps >= ?")
        params.append(min_upload)
    if max_upload is not None:
        conditions.append("upload_mbps <= ?")
        params.append(max_upload)
    if max_ping is not None:
        conditions.append("ping_ms <= ?")
        params.append(max_ping)
    if server is not None:
        conditions.append("server_name = ?")
        params.append(server)
    if isp is not None:
        conditions.append("isp_name = ?")
        params.append(isp)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    count_sql = f"SELECT COUNT(*) FROM results {where}"
    data_sql = f"SELECT * FROM results {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?"

    with closing(_connect()) as conn:
        total: int = conn.execute(count_sql, params).fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(data_sql, [*params, page_size, offset]).fetchall()

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
