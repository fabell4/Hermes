"""Tests for src/exporters/csv_exporter.py."""

import csv
from datetime import datetime, timezone, timedelta

import pytest

from src.exporters.csv_exporter import CSVExporter, FIELDNAMES
from src.models.speed_result import SpeedResult


def _sample_result(days_ago: float = 0) -> SpeedResult:
    ts = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    return SpeedResult(
        timestamp=ts,
        download_mbps=150.0,
        upload_mbps=75.0,
        ping_ms=8.5,
        server_name="Test ISP",
        server_location="Berlin, DE",
        server_id=9999,
    )


# ---------------------------------------------------------------------------
# Initialisation / _ensure_file
# ---------------------------------------------------------------------------


def test_creates_file_with_headers_on_init(tmp_path):
    path = tmp_path / "results.csv"
    CSVExporter(path)
    assert path.exists()
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == FIELDNAMES


def test_does_not_overwrite_existing_file(tmp_path):
    path = tmp_path / "results.csv"
    # Write a pre-existing row
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerow(dict.fromkeys(FIELDNAMES, "existing"))

    CSVExporter(path)  # should not truncate
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["download_mbps"] == "existing"


def test_creates_parent_directories(tmp_path):
    path = tmp_path / "deep" / "nested" / "results.csv"
    CSVExporter(path)
    assert path.exists()


# ---------------------------------------------------------------------------
# export()
# ---------------------------------------------------------------------------


def test_export_appends_row(tmp_path):
    path = tmp_path / "results.csv"
    exporter = CSVExporter(path)
    result = _sample_result()

    exporter.export(result)

    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert float(rows[0]["download_mbps"]) == pytest.approx(150.0)
    assert float(rows[0]["upload_mbps"]) == pytest.approx(75.0)
    assert float(rows[0]["ping_ms"]) == pytest.approx(8.5)
    assert rows[0]["server_name"] == "Test ISP"


def test_export_appends_multiple_rows(tmp_path):
    path = tmp_path / "results.csv"
    exporter = CSVExporter(path)

    exporter.export(_sample_result())
    exporter.export(_sample_result())

    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2


def test_export_raises_on_os_error(tmp_path, monkeypatch):
    path = tmp_path / "results.csv"
    exporter = CSVExporter(path)

    import builtins

    real_open = builtins.open

    def _bad_open(p, mode="r", **kwargs):
        if "a" in mode:
            raise OSError("disk full")
        return real_open(p, mode, **kwargs)

    monkeypatch.setattr(builtins, "open", _bad_open)
    with pytest.raises(OSError, match="disk full"):
        exporter.export(_sample_result())


# ---------------------------------------------------------------------------
# get_file_path()
# ---------------------------------------------------------------------------


def test_get_file_path_returns_resolved_path(tmp_path):
    path = tmp_path / "results.csv"
    exporter = CSVExporter(path)
    assert exporter.get_file_path() == path.resolve()


# ---------------------------------------------------------------------------
# get_row_count()
# ---------------------------------------------------------------------------


def test_get_row_count_zero_on_empty_file(tmp_path):
    path = tmp_path / "results.csv"
    exporter = CSVExporter(path)
    assert exporter.get_row_count() == 0


def test_get_row_count_reflects_exported_rows(tmp_path):
    path = tmp_path / "results.csv"
    exporter = CSVExporter(path)
    exporter.export(_sample_result())
    exporter.export(_sample_result())
    assert exporter.get_row_count() == 2


def test_get_row_count_zero_when_file_missing(tmp_path):
    path = tmp_path / "missing.csv"
    exporter = CSVExporter.__new__(CSVExporter)
    exporter.path = path
    assert exporter.get_row_count() == 0


# ---------------------------------------------------------------------------
# _prune() — max_rows
# ---------------------------------------------------------------------------


def test_prune_no_op_when_limits_unset(tmp_path):
    path = tmp_path / "results.csv"
    exporter = CSVExporter(path)
    for _ in range(5):
        exporter.export(_sample_result())
    assert exporter.get_row_count() == 5


def test_prune_trims_to_max_rows(tmp_path):
    path = tmp_path / "results.csv"
    exporter = CSVExporter(path, max_rows=3)
    for _ in range(5):
        exporter.export(_sample_result())
    assert exporter.get_row_count() == 3


def test_prune_keeps_newest_rows_when_trimming(tmp_path):
    path = tmp_path / "results.csv"
    exporter = CSVExporter(path, max_rows=2)
    for i in range(4):
        exporter.export(SpeedResult(
            timestamp=datetime.now(tz=timezone.utc),
            download_mbps=float(i * 10),
            upload_mbps=10.0,
            ping_ms=5.0,
            server_name="ISP",
            server_location="City",
            server_id=i,
        ))
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert float(rows[0]["download_mbps"]) == pytest.approx(20.0)
    assert float(rows[1]["download_mbps"]) == pytest.approx(30.0)


def test_prune_no_op_when_under_max_rows(tmp_path):
    path = tmp_path / "results.csv"
    exporter = CSVExporter(path, max_rows=10)
    for _ in range(3):
        exporter.export(_sample_result())
    assert exporter.get_row_count() == 3


# ---------------------------------------------------------------------------
# _prune() — retention_days
# ---------------------------------------------------------------------------


def test_prune_removes_old_rows_by_retention_days(tmp_path):
    path = tmp_path / "results.csv"
    exporter = CSVExporter(path, retention_days=7)
    exporter.export(_sample_result(days_ago=10))  # old — should be pruned
    exporter.export(_sample_result(days_ago=5))   # recent — should remain
    exporter.export(_sample_result(days_ago=1))   # recent — should remain
    assert exporter.get_row_count() == 2


def test_prune_keeps_all_rows_within_retention(tmp_path):
    path = tmp_path / "results.csv"
    exporter = CSVExporter(path, retention_days=30)
    for _ in range(4):
        exporter.export(_sample_result(days_ago=1))
    assert exporter.get_row_count() == 4


# ---------------------------------------------------------------------------
# _prune() — both limits combined
# ---------------------------------------------------------------------------


def test_prune_applies_both_limits(tmp_path):
    path = tmp_path / "results.csv"
    exporter = CSVExporter(path, max_rows=2, retention_days=7)
    exporter.export(_sample_result(days_ago=10))  # pruned by retention
    exporter.export(_sample_result(days_ago=3))   # recent
    exporter.export(_sample_result(days_ago=2))   # recent
    exporter.export(_sample_result(days_ago=1))   # recent — only 2 kept by max_rows
    assert exporter.get_row_count() == 2
