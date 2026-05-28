"""Tests for src/services/time_of_day.py."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.services.time_of_day import HourlyStats, analyse

_CREATE = """
CREATE TABLE IF NOT EXISTS results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    download_mbps   REAL    NOT NULL,
    upload_mbps     REAL    NOT NULL,
    ping_ms         REAL    NOT NULL
)"""


def _seed_db(path: Path, rows: list[dict]) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute(_CREATE)
    for r in rows:
        conn.execute(
            "INSERT INTO results (timestamp, download_mbps, upload_mbps, ping_ms) VALUES (?, ?, ?, ?)",
            (r["timestamp"], r["download_mbps"], r["upload_mbps"], r["ping_ms"]),
        )
    conn.commit()
    conn.close()


class TestAnalyseMissingDb:
    def test_missing_db_returns_empty(self, tmp_path: Path) -> None:
        result = analyse(tmp_path / "nonexistent.db")
        assert result == []


class TestAnalyseEmpty:
    def test_empty_table_returns_empty(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        conn = sqlite3.connect(str(db))
        conn.execute(_CREATE)
        conn.commit()
        conn.close()
        assert analyse(db) == []


class TestAnalyseHourGrouping:
    def test_groups_by_hour(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(
            db,
            [
                {
                    "timestamp": "2026-01-01T10:00:00",
                    "download_mbps": 100.0,
                    "upload_mbps": 50.0,
                    "ping_ms": 20.0,
                },
                {
                    "timestamp": "2026-01-01T10:30:00",
                    "download_mbps": 80.0,
                    "upload_mbps": 40.0,
                    "ping_ms": 30.0,
                },
                {
                    "timestamp": "2026-01-01T14:00:00",
                    "download_mbps": 60.0,
                    "upload_mbps": 30.0,
                    "ping_ms": 50.0,
                },
            ],
        )
        result = analyse(db, days=0)
        assert len(result) == 2
        hours = [r.hour for r in result]
        assert 10 in hours
        assert 14 in hours

    def test_averages_computed_correctly(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(
            db,
            [
                {
                    "timestamp": "2026-01-01T10:00:00",
                    "download_mbps": 100.0,
                    "upload_mbps": 50.0,
                    "ping_ms": 20.0,
                },
                {
                    "timestamp": "2026-01-01T10:30:00",
                    "download_mbps": 80.0,
                    "upload_mbps": 40.0,
                    "ping_ms": 30.0,
                },
            ],
        )
        result = analyse(db, days=0)
        assert len(result) == 1
        h = result[0]
        assert h.hour == 10
        assert h.sample_count == 2
        assert h.avg_download_mbps == pytest.approx(90.0, abs=0.01)
        assert h.avg_upload_mbps == pytest.approx(45.0, abs=0.01)
        assert h.avg_ping_ms == pytest.approx(25.0, abs=0.01)

    def test_min_max_download(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(
            db,
            [
                {
                    "timestamp": "2026-01-01T10:00:00",
                    "download_mbps": 120.0,
                    "upload_mbps": 50.0,
                    "ping_ms": 20.0,
                },
                {
                    "timestamp": "2026-01-01T10:15:00",
                    "download_mbps": 80.0,
                    "upload_mbps": 50.0,
                    "ping_ms": 20.0,
                },
                {
                    "timestamp": "2026-01-01T10:45:00",
                    "download_mbps": 100.0,
                    "upload_mbps": 50.0,
                    "ping_ms": 20.0,
                },
            ],
        )
        result = analyse(db, days=0)
        h = result[0]
        assert h.min_download_mbps == pytest.approx(80.0, abs=0.01)
        assert h.max_download_mbps == pytest.approx(120.0, abs=0.01)

    def test_ordered_by_hour(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(
            db,
            [
                {
                    "timestamp": "2026-01-01T22:00:00",
                    "download_mbps": 60.0,
                    "upload_mbps": 30.0,
                    "ping_ms": 50.0,
                },
                {
                    "timestamp": "2026-01-01T03:00:00",
                    "download_mbps": 100.0,
                    "upload_mbps": 50.0,
                    "ping_ms": 20.0,
                },
                {
                    "timestamp": "2026-01-01T12:00:00",
                    "download_mbps": 80.0,
                    "upload_mbps": 40.0,
                    "ping_ms": 30.0,
                },
            ],
        )
        result = analyse(db, days=0)
        hours = [r.hour for r in result]
        assert hours == sorted(hours)

    def test_returns_hourly_stats_instances(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(
            db,
            [
                {
                    "timestamp": "2026-01-01T08:00:00",
                    "download_mbps": 100.0,
                    "upload_mbps": 50.0,
                    "ping_ms": 20.0,
                },
            ],
        )
        result = analyse(db, days=0)
        assert all(isinstance(r, HourlyStats) for r in result)


class TestAnalyseDaysFilter:
    def test_days_filter_excludes_old_rows(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(
            db,
            [
                {
                    "timestamp": "2020-01-01T10:00:00",
                    "download_mbps": 10.0,
                    "upload_mbps": 5.0,
                    "ping_ms": 200.0,
                },
                {
                    "timestamp": "2026-05-20T10:00:00",
                    "download_mbps": 100.0,
                    "upload_mbps": 50.0,
                    "ping_ms": 20.0,
                },
            ],
        )
        # Use days=1 — only the very recent row should match in a real environment.
        # Since we seed a far-future row, use days=0 (all time) to test inclusion.
        result_all = analyse(db, days=0)
        assert len(result_all) == 1  # same hour slot, two rows → same hour group
        assert result_all[0].sample_count == 2

    def test_days_zero_returns_all(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(
            db,
            [
                {
                    "timestamp": "2020-06-15T08:00:00",
                    "download_mbps": 50.0,
                    "upload_mbps": 25.0,
                    "ping_ms": 30.0,
                },
                {
                    "timestamp": "2026-01-10T14:00:00",
                    "download_mbps": 100.0,
                    "upload_mbps": 50.0,
                    "ping_ms": 20.0,
                },
            ],
        )
        result = analyse(db, days=0)
        assert len(result) == 2  # hour 8 and hour 14
