# pylint: disable=redefined-outer-name
"""Tests for SQLiteExporter."""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.exporters.sqlite_exporter import SQLiteExporter
from src.models.speed_result import SpeedResult


def _make_result(**kwargs) -> SpeedResult:
    """Return a SpeedResult with sensible defaults, overridable via kwargs."""
    defaults: dict = {
        "download_mbps": 100.0,
        "upload_mbps": 50.0,
        "ping_ms": 10.0,
        "server_name": "Test Server",
        "server_location": "Test City",
        "server_id": 1,
    }
    defaults.update(kwargs)
    return SpeedResult(**defaults)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Return a temporary path for a test SQLite database."""
    return tmp_path / "test_hermes.db"


@pytest.fixture
def exporter(db_path: Path) -> SQLiteExporter:
    """Return a SQLiteExporter backed by a temporary database."""
    return SQLiteExporter(path=db_path)


def test_creates_database_file_on_init(db_path: Path) -> None:
    """Database file should exist after instantiation."""
    SQLiteExporter(path=db_path)
    assert db_path.exists()


def test_creates_results_table(db_path: Path) -> None:
    """The results table should be present after init."""
    SQLiteExporter(path=db_path)
    conn = sqlite3.connect(db_path)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    conn.close()
    assert ("results",) in tables


def test_creates_parent_directories(tmp_path: Path) -> None:
    """Missing parent directories are created automatically."""
    nested = tmp_path / "deep" / "nested" / "hermes.db"
    SQLiteExporter(path=nested)
    assert nested.exists()


def test_export_inserts_one_row(exporter: SQLiteExporter, db_path: Path) -> None:
    """A single export() call should produce exactly one row."""
    exporter.export(_make_result())
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    conn.close()
    assert count == 1


def test_export_stores_correct_values(exporter: SQLiteExporter, db_path: Path) -> None:
    """Exported numeric values should be stored with full precision."""
    exporter.export(_make_result(download_mbps=200.5, upload_mbps=80.25, ping_ms=4.9))
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT download_mbps, upload_mbps, ping_ms FROM results"
    ).fetchone()
    conn.close()
    assert row == (200.5, 80.25, 4.9)


def test_export_multiple_rows(exporter: SQLiteExporter, db_path: Path) -> None:
    """Multiple export() calls should each insert a separate row."""
    for i in range(3):
        exporter.export(_make_result(download_mbps=float(i * 10)))
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    conn.close()
    assert count == 3


def test_export_stores_timestamp_as_iso(
    exporter: SQLiteExporter, db_path: Path
) -> None:
    """The timestamp column should be a valid ISO-format string."""
    exporter.export(_make_result())
    conn = sqlite3.connect(db_path)
    ts = conn.execute("SELECT timestamp FROM results").fetchone()[0]
    conn.close()
    parsed = datetime.fromisoformat(ts)
    assert parsed is not None


def test_prune_max_rows_keeps_newest(db_path: Path) -> None:
    """max_rows=2 should retain only the 2 most recent rows."""
    exp = SQLiteExporter(path=db_path, max_rows=2)
    for i in range(4):
        exp.export(_make_result(download_mbps=float(i * 10)))
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    conn.close()
    assert count == 2


def test_prune_retention_days_removes_old_rows(db_path: Path) -> None:
    """Rows older than retention_days should be deleted."""
    exp = SQLiteExporter(path=db_path, retention_days=1)
    old = _make_result()
    old.timestamp = datetime.now(timezone.utc) - timedelta(days=5)
    recent = _make_result()
    exp.export(old)
    exp.export(recent)
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    conn.close()
    assert count == 1


def test_no_prune_when_limits_are_zero(db_path: Path) -> None:
    """With max_rows=0 and retention_days=0, all rows are kept."""
    exp = SQLiteExporter(path=db_path, max_rows=0, retention_days=0)
    for _ in range(10):
        exp.export(_make_result())
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    conn.close()
    assert count == 10


def test_raises_on_write_failure(tmp_path: Path) -> None:
    """A RuntimeError should be raised when the DB write fails."""
    exp = SQLiteExporter(path=tmp_path / "test.db")
    conn = sqlite3.connect(exp.path)
    conn.execute("DROP TABLE results")
    conn.commit()
    conn.close()
    with pytest.raises(RuntimeError, match="SQLite write failed"):
        exp.export(_make_result())


def test_server_id_none_stored_as_null(exporter: SQLiteExporter, db_path: Path) -> None:
    """server_id=None should be stored as SQL NULL."""
    result = _make_result()
    result.server_id = None
    exporter.export(result)
    conn = sqlite3.connect(db_path)
    server_id = conn.execute("SELECT server_id FROM results").fetchone()[0]
    conn.close()
    assert server_id is None


def test_wal_journal_mode_enabled(db_path: Path) -> None:
    """The database should be configured with WAL journal mode."""
    exp = SQLiteExporter(path=db_path)
    with exp._transaction() as conn:  # pylint: disable=protected-access
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"
