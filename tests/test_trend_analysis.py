"""Tests for src/services/trend_analysis.py."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.services.trend_analysis import MonthlyStats, TrendReport, _linear_slope, analyse

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


class TestLinearSlope:
    def test_positive_slope(self) -> None:
        slope = _linear_slope([0, 1, 2], [0.0, 1.0, 2.0])
        assert slope == pytest.approx(1.0)

    def test_negative_slope(self) -> None:
        slope = _linear_slope([0, 1, 2], [10.0, 5.0, 0.0])
        assert slope == pytest.approx(-5.0)

    def test_flat_line(self) -> None:
        slope = _linear_slope([0, 1, 2], [5.0, 5.0, 5.0])
        assert slope == pytest.approx(0.0)

    def test_single_point_returns_none(self) -> None:
        assert _linear_slope([0.0], [1.0]) is None

    def test_empty_returns_none(self) -> None:
        assert _linear_slope([], []) is None

    def test_zero_variance_in_x_returns_none(self) -> None:
        # All x values identical → denom = 0
        assert _linear_slope([1.0, 1.0], [2.0, 3.0]) is None


class TestAnalyseMissingDb:
    def test_missing_db_returns_empty_report(self, tmp_path: Path) -> None:
        report = analyse(tmp_path / "nonexistent.db")
        assert report.months_available == 0
        assert report.monthly_stats == []
        assert report.download_slope is None
        assert not report.degradation_detected


class TestAnalyseEmpty:
    def test_empty_table_returns_empty_report(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        conn = sqlite3.connect(str(db))
        conn.execute(_CREATE)
        conn.commit()
        conn.close()
        report = analyse(db)
        assert report.months_available == 0


class TestAnalyseSingleMonth:
    def test_one_month_no_slopes(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(db, [
            {"timestamp": "2026-03-01T10:00:00", "download_mbps": 100.0, "upload_mbps": 50.0, "ping_ms": 20.0},
        ])
        report = analyse(db, months=0)
        assert report.months_available == 1
        assert report.download_slope is None
        assert not report.degradation_detected
        assert len(report.monthly_stats) == 1
        assert isinstance(report.monthly_stats[0], MonthlyStats)


class TestAnalyseMultipleMonths:
    def test_two_months_slopes_computed(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(db, [
            {"timestamp": "2026-01-15T10:00:00", "download_mbps": 100.0, "upload_mbps": 50.0, "ping_ms": 20.0},
            {"timestamp": "2026-02-15T10:00:00", "download_mbps": 90.0, "upload_mbps": 45.0, "ping_ms": 25.0},
        ])
        report = analyse(db, months=0)
        assert report.months_available == 2
        assert report.download_slope is not None
        assert report.upload_slope is not None
        assert report.ping_slope is not None

    def test_declining_download_detected(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(db, [
            {"timestamp": "2026-01-15T10:00:00", "download_mbps": 100.0, "upload_mbps": 50.0, "ping_ms": 20.0},
            {"timestamp": "2026-02-15T10:00:00", "download_mbps": 80.0, "upload_mbps": 48.0, "ping_ms": 22.0},
            {"timestamp": "2026-03-15T10:00:00", "download_mbps": 60.0, "upload_mbps": 46.0, "ping_ms": 24.0},
        ])
        report = analyse(db, months=0)
        assert report.degradation_detected
        assert report.download_slope is not None
        assert report.download_slope < 0

    def test_increasing_ping_detected(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(db, [
            {"timestamp": "2026-01-15T10:00:00", "download_mbps": 100.0, "upload_mbps": 50.0, "ping_ms": 15.0},
            {"timestamp": "2026-02-15T10:00:00", "download_mbps": 100.0, "upload_mbps": 50.0, "ping_ms": 30.0},
            {"timestamp": "2026-03-15T10:00:00", "download_mbps": 100.0, "upload_mbps": 50.0, "ping_ms": 50.0},
        ])
        report = analyse(db, months=0)
        assert report.degradation_detected
        assert report.ping_slope is not None
        assert report.ping_slope > 0

    def test_improving_trend_no_degradation(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(db, [
            {"timestamp": "2026-01-15T10:00:00", "download_mbps": 60.0, "upload_mbps": 30.0, "ping_ms": 50.0},
            {"timestamp": "2026-02-15T10:00:00", "download_mbps": 80.0, "upload_mbps": 40.0, "ping_ms": 30.0},
            {"timestamp": "2026-03-15T10:00:00", "download_mbps": 100.0, "upload_mbps": 50.0, "ping_ms": 15.0},
        ])
        report = analyse(db, months=0)
        assert not report.degradation_detected
        assert report.download_slope is not None
        assert report.download_slope > 0
        assert report.ping_slope is not None
        assert report.ping_slope < 0

    def test_monthly_stats_ordered_oldest_first(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(db, [
            {"timestamp": "2026-03-15T10:00:00", "download_mbps": 80.0, "upload_mbps": 40.0, "ping_ms": 30.0},
            {"timestamp": "2026-01-15T10:00:00", "download_mbps": 100.0, "upload_mbps": 50.0, "ping_ms": 20.0},
        ])
        report = analyse(db, months=0)
        assert report.monthly_stats[0].month < report.monthly_stats[-1].month

    def test_monthly_averages_correct(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(db, [
            {"timestamp": "2026-01-10T10:00:00", "download_mbps": 100.0, "upload_mbps": 50.0, "ping_ms": 20.0},
            {"timestamp": "2026-01-20T10:00:00", "download_mbps": 80.0, "upload_mbps": 40.0, "ping_ms": 30.0},
        ])
        report = analyse(db, months=0)
        m = report.monthly_stats[0]
        assert m.month == "2026-01"
        assert m.sample_count == 2
        assert m.avg_download_mbps == pytest.approx(90.0, abs=0.01)
        assert m.avg_upload_mbps == pytest.approx(45.0, abs=0.01)
        assert m.avg_ping_ms == pytest.approx(25.0, abs=0.01)

    def test_slopes_rounded_to_four_places(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(db, [
            {"timestamp": "2026-01-15T10:00:00", "download_mbps": 100.0, "upload_mbps": 50.0, "ping_ms": 20.0},
            {"timestamp": "2026-02-15T10:00:00", "download_mbps": 90.0, "upload_mbps": 45.0, "ping_ms": 25.0},
        ])
        report = analyse(db, months=0)
        for slope in (report.download_slope, report.upload_slope, report.ping_slope):
            if slope is not None:
                assert round(slope, 4) == slope

    def test_returns_trend_report_instance(self, tmp_path: Path) -> None:
        db = tmp_path / "hermes.db"
        _seed_db(db, [
            {"timestamp": "2026-01-15T10:00:00", "download_mbps": 100.0, "upload_mbps": 50.0, "ping_ms": 20.0},
        ])
        assert isinstance(analyse(db, months=0), TrendReport)
