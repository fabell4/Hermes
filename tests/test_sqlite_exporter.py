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


def test_jitter_ms_stored_when_present(db_path: Path) -> None:
    """jitter_ms should be stored when provided."""
    exp = SQLiteExporter(path=db_path)
    result = _make_result()
    result.jitter_ms = 4.2
    exp.export(result)
    conn = sqlite3.connect(db_path)
    jitter = conn.execute("SELECT jitter_ms FROM results").fetchone()[0]
    conn.close()
    assert jitter == pytest.approx(4.2)


def test_jitter_ms_stored_as_null_when_none(db_path: Path) -> None:
    """jitter_ms=None should be stored as SQL NULL."""
    exp = SQLiteExporter(path=db_path)
    exp.export(_make_result())  # jitter_ms defaults to None
    conn = sqlite3.connect(db_path)
    jitter = conn.execute("SELECT jitter_ms FROM results").fetchone()[0]
    conn.close()
    assert jitter is None


def test_isp_name_stored_when_present(db_path: Path) -> None:
    """isp_name should be stored when provided."""
    exp = SQLiteExporter(path=db_path)
    result = _make_result()
    result.isp_name = "Comcast"
    exp.export(result)
    conn = sqlite3.connect(db_path)
    isp = conn.execute("SELECT isp_name FROM results").fetchone()[0]
    conn.close()
    assert isp == "Comcast"


def test_isp_name_stored_as_null_when_none(db_path: Path) -> None:
    """isp_name=None should be stored as SQL NULL."""
    exp = SQLiteExporter(path=db_path)
    exp.export(_make_result())  # isp_name defaults to None
    conn = sqlite3.connect(db_path)
    isp = conn.execute("SELECT isp_name FROM results").fetchone()[0]
    conn.close()
    assert isp is None


# ---------------------------------------------------------------------------
# Boundary values — all optional fields None
# ---------------------------------------------------------------------------


def test_export_with_all_optional_fields_none(db_path: Path) -> None:
    """A result with jitter_ms, isp_name, and server_id all None must store without error."""
    exp = SQLiteExporter(path=db_path)
    result = _make_result()
    result.jitter_ms = None
    result.isp_name = None
    result.server_id = None
    exp.export(result)
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT jitter_ms, isp_name, server_id FROM results").fetchone()
    conn.close()
    assert row == (None, None, None)


def test_export_with_all_zero_numeric_values(db_path: Path) -> None:
    """Zero values for download, upload, and ping are valid boundary inputs."""
    exp = SQLiteExporter(path=db_path)
    exp.export(_make_result(download_mbps=0.0, upload_mbps=0.0, ping_ms=0.0))
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT download_mbps, upload_mbps, ping_ms FROM results"
    ).fetchone()
    conn.close()
    assert row == (0.0, 0.0, 0.0)


def test_export_with_very_large_float_values(db_path: Path) -> None:
    """Extremely large (but valid) floats must be stored and retrieved without truncation."""
    exp = SQLiteExporter(path=db_path)
    large = 9_999.99
    exp.export(_make_result(download_mbps=large, upload_mbps=large, ping_ms=large))
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT download_mbps, upload_mbps, ping_ms FROM results"
    ).fetchone()
    conn.close()
    assert row[0] == pytest.approx(large)
    assert row[1] == pytest.approx(large)
    assert row[2] == pytest.approx(large)


def test_export_empty_string_server_fields(db_path: Path) -> None:
    """Empty strings for server_name and server_location are valid — NOT SQL NULL."""
    exp = SQLiteExporter(path=db_path)
    exp.export(_make_result(server_name="", server_location=""))
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT server_name, server_location FROM results").fetchone()
    conn.close()
    assert row == ("", "")


def test_export_raises_on_missing_table(db_path: Path) -> None:
    """Exporting after the results table is dropped must raise RuntimeError, not swallow."""
    exp = SQLiteExporter(path=db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("DROP TABLE results")
    conn.commit()
    conn.close()
    with pytest.raises(RuntimeError, match="SQLite write failed"):
        exp.export(_make_result())

# ---------------------------------------------------------------------------
# Lock timeout and error handling tests
# ---------------------------------------------------------------------------


def test_export_raises_lock_timeout_when_lock_held(db_path: Path) -> None:
    """Export should raise SQLiteLockTimeout if lock cannot be acquired."""
    from src.exporters.sqlite_exporter import SQLiteLockTimeout
    from unittest.mock import Mock

    exp = SQLiteExporter(path=db_path)

    # Replace the lock with a mock that returns False on acquire (simulating timeout)
    mock_lock = Mock()
    mock_lock.acquire.return_value = False
    exp._lock = mock_lock

    with pytest.raises(SQLiteLockTimeout) as exc_info:
        exp.export(_make_result())
    assert exc_info.value.timeout == pytest.approx(30.0)
    assert str(db_path) in exc_info.value.db_path


def test_sqlite_lock_timeout_exception_contains_diagnostics(db_path: Path) -> None:
    """SQLiteLockTimeout exception should include timeout and db_path."""
    from src.exporters.sqlite_exporter import SQLiteLockTimeout

    exc = SQLiteLockTimeout(timeout=30.0, db_path=db_path)
    assert exc.timeout == pytest.approx(30.0)
    assert exc.db_path == str(db_path)
    assert "30.0s" in str(exc)
    assert str(db_path) in str(exc)


def test_export_creates_missing_parent_directories(tmp_path: Path) -> None:
    """SQLiteExporter should create missing parent directories."""
    deep_path = tmp_path / "nested" / "deep" / "db" / "test.db"
    exp = SQLiteExporter(path=deep_path)
    assert deep_path.exists()
    exp.export(_make_result())
    # Verify data was written
    conn = sqlite3.connect(deep_path)
    count = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    conn.close()
    assert count == 1