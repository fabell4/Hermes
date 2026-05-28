"""GET /api/export/csv and GET /api/export/json — bulk data export for backup/migration."""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from starlette.responses import StreamingResponse

from src import config as _cfg

router = APIRouter(tags=["export"])

_503: dict[int | str, dict[str, Any]] = {
    503: {"description": "Database not yet available."}
}

# Module-level DB path for test mocking
DB_PATH = Path(_cfg.SQLITE_DB_PATH)

_FIELDNAMES = [
    "id",
    "timestamp",
    "download_mbps",
    "upload_mbps",
    "ping_ms",
    "jitter_ms",
    "isp_name",
    "server_name",
    "server_location",
    "server_id",
    "packet_loss_pct",
    "quality_score",
    "sla_ok",
    "note",
]


def _require_db() -> None:
    """Raise 503 if the database file does not exist yet."""
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="No database found yet.")


def _open_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _parse_iso(value: str, param_name: str) -> str:
    """Validate an ISO 8601 datetime string and return it normalised to seconds."""
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid ISO 8601 datetime for '{param_name}': {value!r}",
        ) from exc


def _build_query(start: str | None, end: str | None) -> tuple[str, list[str]]:
    """Build a WHERE clause with optional inclusive timestamp filters.

    Returns (where_clause, params).  The caller is responsible for prepending
    ``SELECT <fields> FROM results`` and any ORDER BY clause.
    """
    conditions: list[str] = []
    params: list[str] = []
    if start is not None:
        conditions.append("timestamp >= ?")
        params.append(start)
    if end is not None:
        conditions.append("timestamp <= ?")
        params.append(end)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where, params


def _select_fields(conn: sqlite3.Connection) -> str:
    """Return the SELECT field list, substituting NULL AS for any missing columns.

    This makes the export resilient to pre-migration databases that lack newer
    columns (e.g. ``note`` on instances that haven't restarted since upgrade).
    """
    existing = {row[1] for row in conn.execute("PRAGMA table_info(results)").fetchall()}
    return ", ".join(f if f in existing else f"NULL as {f}" for f in _FIELDNAMES)


@router.get("/export/csv", responses=_503)
def export_csv(
    start: Annotated[
        str | None,
        Query(
            description="Start datetime filter, inclusive (ISO 8601, e.g. 2026-01-01T00:00:00)"
        ),
    ] = None,
    end: Annotated[
        str | None,
        Query(
            description="End datetime filter, inclusive (ISO 8601, e.g. 2026-12-31T23:59:59)"
        ),
    ] = None,
) -> StreamingResponse:
    """Download all results as a CSV file, optionally filtered by date range."""
    _require_db()
    if start is not None:
        start = _parse_iso(start, "start")
    if end is not None:
        end = _parse_iso(end, "end")

    where, params = _build_query(start, end)
    filename = (
        f"hermes_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    )

    def generate():
        # Yield header row
        buf = io.StringIO()
        csv.DictWriter(buf, fieldnames=_FIELDNAMES, lineterminator="\r\n").writeheader()
        yield buf.getvalue()

        with closing(_open_db()) as conn:
            fields = _select_fields(conn)
            # Column names cannot be SQL parameters; fields derives exclusively from
            # _FIELDNAMES (a hardcoded module constant) — no user input is interpolated.
            full_sql = f"SELECT {fields} FROM results {where} ORDER BY timestamp ASC"  # nosec B608  # NOSONAR
            for row in conn.execute(full_sql, params):
                buf = io.StringIO()
                writer = csv.DictWriter(
                    buf, fieldnames=_FIELDNAMES, lineterminator="\r\n"
                )
                writer.writerow(dict(row))
                yield buf.getvalue()

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/json", responses=_503)
def export_json(
    start: Annotated[
        str | None,
        Query(
            description="Start datetime filter, inclusive (ISO 8601, e.g. 2026-01-01T00:00:00)"
        ),
    ] = None,
    end: Annotated[
        str | None,
        Query(
            description="End datetime filter, inclusive (ISO 8601, e.g. 2026-12-31T23:59:59)"
        ),
    ] = None,
) -> StreamingResponse:
    """Download all results as a JSON file, optionally filtered by date range."""
    _require_db()
    if start is not None:
        start = _parse_iso(start, "start")
    if end is not None:
        end = _parse_iso(end, "end")

    where, params = _build_query(start, end)
    filename = (
        f"hermes_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    )
    exported_at = datetime.now(timezone.utc).isoformat()

    def generate():
        yield f'{{"exported_at": "{exported_at}", "results": ['
        first = True
        with closing(_open_db()) as conn:
            fields = _select_fields(conn)
            # Column names cannot be SQL parameters; fields derives exclusively from
            # _FIELDNAMES (a hardcoded module constant) — no user input is interpolated.
            full_sql = f"SELECT {fields} FROM results {where} ORDER BY timestamp ASC"  # nosec B608  # NOSONAR
            for row in conn.execute(full_sql, params):
                row_dict = dict(row)
                # Convert SQLite INTEGER (0/1/NULL) to JSON bool/null
                if row_dict.get("sla_ok") is not None:
                    row_dict["sla_ok"] = bool(row_dict["sla_ok"])
                sep = "" if first else ","
                first = False
                yield sep + json.dumps(row_dict, ensure_ascii=False)
        yield "]}"

    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
