"""Tests for GET /api/analysis/* in src/api/routes/analysis.py."""

from __future__ import annotations

import sqlite3
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

_CREATE = """
CREATE TABLE IF NOT EXISTS results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    download_mbps   REAL    NOT NULL,
    upload_mbps     REAL    NOT NULL,
    ping_ms         REAL    NOT NULL,
    jitter_ms       REAL,
    isp_name        TEXT,
    server_name     TEXT    NOT NULL DEFAULT '',
    server_location TEXT    NOT NULL DEFAULT '',
    server_id       INTEGER,
    packet_loss_pct REAL,
    quality_score   REAL,
    sla_ok          INTEGER
)"""


def _seed(conn: sqlite3.Connection, rows: list[dict]) -> None:
    for r in rows:
        conn.execute(
            """INSERT INTO results
               (timestamp, download_mbps, upload_mbps, ping_ms)
               VALUES (:timestamp, :download_mbps, :upload_mbps, :ping_ms)""",
            r,
        )
    conn.commit()


@pytest.fixture()
def empty_db(tmp_path):
    db = tmp_path / "hermes.db"
    conn = sqlite3.connect(str(db))
    conn.execute(_CREATE)
    conn.commit()
    conn.close()
    with patch("src.api.routes.analysis.DB_PATH", db):
        yield db


@pytest.fixture()
def populated_db(tmp_path):
    """DB with 25 rows across two months at different hours."""
    db = tmp_path / "hermes.db"
    conn = sqlite3.connect(str(db))
    conn.execute(_CREATE)
    rows = []
    for i in range(10):
        rows.append(
            {
                "timestamp": f"2026-04-{i + 1:02d}T10:00:00",
                "download_mbps": 100.0 + i,
                "upload_mbps": 50.0 + i * 0.5,
                "ping_ms": 20.0 + i * 0.2,
            }
        )
    for i in range(10):
        rows.append(
            {
                "timestamp": f"2026-05-{i + 1:02d}T14:00:00",
                "download_mbps": 90.0 + i,
                "upload_mbps": 45.0 + i * 0.5,
                "ping_ms": 25.0 + i * 0.2,
            }
        )
    _seed(conn, rows)
    conn.close()
    with patch("src.api.routes.analysis.DB_PATH", db):
        yield db


# ---------------------------------------------------------------------------
# Anomaly endpoint
# ---------------------------------------------------------------------------


class TestAnomaliesNoDb:
    def test_missing_db_returns_503(self, tmp_path):
        with patch("src.api.routes.analysis.DB_PATH", tmp_path / "noexist.db"):
            resp = client.get("/api/analysis/anomalies")
        assert resp.status_code == 503

    def test_empty_db_returns_empty_list(self, empty_db):
        resp = client.get("/api/analysis/anomalies")
        assert resp.status_code == 200
        assert resp.json() == []


class TestAnomaliesResponse:
    def test_returns_list(self, populated_db):
        resp = client.get("/api/analysis/anomalies")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_each_item_has_required_fields(self, populated_db):
        resp = client.get("/api/analysis/anomalies")
        for item in resp.json():
            assert "id" in item
            assert "timestamp" in item
            assert "download_mbps" in item
            assert "upload_mbps" in item
            assert "ping_ms" in item
            assert "is_anomaly" in item
            assert "anomaly_flags" in item

    def test_limit_respected(self, populated_db):
        resp = client.get("/api/analysis/anomalies?limit=5")
        assert resp.status_code == 200
        assert len(resp.json()) <= 5

    def test_newest_first(self, populated_db):
        resp = client.get("/api/analysis/anomalies")
        data = resp.json()
        if len(data) > 1:
            assert data[0]["timestamp"] >= data[-1]["timestamp"]

    def test_window_param_accepted(self, populated_db):
        resp = client.get("/api/analysis/anomalies?window=5")
        assert resp.status_code == 200

    def test_threshold_param_accepted(self, populated_db):
        resp = client.get("/api/analysis/anomalies?threshold=1.0")
        assert resp.status_code == 200

    def test_invalid_limit_rejected(self, empty_db):
        resp = client.get("/api/analysis/anomalies?limit=0")
        assert resp.status_code == 422

    def test_invalid_window_rejected(self, empty_db):
        resp = client.get("/api/analysis/anomalies?window=2")
        assert resp.status_code == 422

    def test_invalid_threshold_rejected(self, empty_db):
        resp = client.get("/api/analysis/anomalies?threshold=0.1")
        assert resp.status_code == 422

    def test_anomalous_result_flagged(self, tmp_path):
        """Seed a DB with a varied baseline + one extreme outlier."""
        db = tmp_path / "hermes.db"
        conn = sqlite3.connect(str(db))
        conn.execute(_CREATE)
        rows = []
        # 20 baseline results with small natural variation (stdev ~1 on download)
        for i in range(20):
            rows.append(
                {
                    "timestamp": f"2026-04-{i + 1:02d}T10:00:00",
                    "download_mbps": 100.0 + (i % 5) * 0.5,  # 100–102, stdev ~0.8
                    "upload_mbps": 50.0,
                    "ping_ms": 20.0 + (i % 3) * 0.1,
                }
            )
        # 1 extreme outlier (download far from baseline mean)
        rows.append(
            {
                "timestamp": "2026-04-22T12:00:00",
                "download_mbps": 1.0,  # z-score >> 2.5
                "upload_mbps": 50.0,
                "ping_ms": 20.0,
            }
        )
        _seed(conn, rows)
        conn.close()
        with patch("src.api.routes.analysis.DB_PATH", db):
            resp = client.get("/api/analysis/anomalies?limit=5&window=20&threshold=2.5")
        assert resp.status_code == 200
        data = resp.json()
        # Most recent (the outlier) should be is_anomaly=True
        assert data[0]["is_anomaly"] is True
        assert any(f["metric"] == "download_mbps" for f in data[0]["anomaly_flags"])


# ---------------------------------------------------------------------------
# Time-of-day endpoint
# ---------------------------------------------------------------------------


class TestTimeOfDayNoDb:
    def test_missing_db_returns_empty(self, tmp_path):
        with patch("src.api.routes.analysis.DB_PATH", tmp_path / "noexist.db"):
            resp = client.get("/api/analysis/time-of-day")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_empty_db_returns_empty(self, empty_db):
        resp = client.get("/api/analysis/time-of-day")
        assert resp.status_code == 200
        assert resp.json() == []


class TestTimeOfDayResponse:
    def test_returns_list(self, populated_db):
        resp = client.get("/api/analysis/time-of-day?days=0")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_each_item_has_required_fields(self, populated_db):
        resp = client.get("/api/analysis/time-of-day?days=0")
        for item in resp.json():
            assert "hour" in item
            assert "sample_count" in item
            assert "avg_download_mbps" in item
            assert "avg_upload_mbps" in item
            assert "avg_ping_ms" in item
            assert "min_download_mbps" in item
            assert "max_download_mbps" in item

    def test_hours_in_range(self, populated_db):
        resp = client.get("/api/analysis/time-of-day?days=0")
        for item in resp.json():
            assert 0 <= item["hour"] <= 23

    def test_ordered_by_hour(self, populated_db):
        resp = client.get("/api/analysis/time-of-day?days=0")
        hours = [item["hour"] for item in resp.json()]
        assert hours == sorted(hours)

    def test_days_param_accepted(self, populated_db):
        resp = client.get("/api/analysis/time-of-day?days=7")
        assert resp.status_code == 200

    def test_days_zero_accepted(self, populated_db):
        resp = client.get("/api/analysis/time-of-day?days=0")
        assert resp.status_code == 200

    def test_invalid_days_rejected(self, empty_db):
        resp = client.get("/api/analysis/time-of-day?days=-1")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Trends endpoint
# ---------------------------------------------------------------------------


class TestTrendsNoDb:
    def test_missing_db_returns_empty_report(self, tmp_path):
        with patch("src.api.routes.analysis.DB_PATH", tmp_path / "noexist.db"):
            resp = client.get("/api/analysis/trends")
        assert resp.status_code == 200
        data = resp.json()
        assert data["months_available"] == 0
        assert data["monthly_stats"] == []
        assert not data["degradation_detected"]

    def test_empty_db_returns_empty_report(self, empty_db):
        resp = client.get("/api/analysis/trends")
        assert resp.status_code == 200
        assert resp.json()["months_available"] == 0


class TestTrendsResponse:
    def test_returns_trend_report_schema(self, populated_db):
        resp = client.get("/api/analysis/trends?months=0")
        assert resp.status_code == 200
        data = resp.json()
        assert "monthly_stats" in data
        assert "degradation_detected" in data
        assert "months_available" in data
        assert "download_slope" in data

    def test_monthly_stats_fields(self, populated_db):
        resp = client.get("/api/analysis/trends?months=0")
        for m in resp.json()["monthly_stats"]:
            assert "month" in m
            assert "sample_count" in m
            assert "avg_download_mbps" in m
            assert "avg_upload_mbps" in m
            assert "avg_ping_ms" in m

    def test_two_months_in_data(self, populated_db):
        resp = client.get("/api/analysis/trends?months=0")
        assert resp.json()["months_available"] == 2

    def test_months_param_accepted(self, populated_db):
        resp = client.get("/api/analysis/trends?months=3")
        assert resp.status_code == 200

    def test_months_zero_accepted(self, populated_db):
        resp = client.get("/api/analysis/trends?months=0")
        assert resp.status_code == 200

    def test_invalid_months_rejected(self, empty_db):
        resp = client.get("/api/analysis/trends?months=-1")
        assert resp.status_code == 422

    def test_degradation_detected_when_declining(self, tmp_path):
        db = tmp_path / "hermes.db"
        conn = sqlite3.connect(str(db))
        conn.execute(_CREATE)
        _seed(
            conn,
            [
                {
                    "timestamp": "2026-01-15T10:00:00",
                    "download_mbps": 100.0,
                    "upload_mbps": 50.0,
                    "ping_ms": 20.0,
                },
                {
                    "timestamp": "2026-02-15T10:00:00",
                    "download_mbps": 80.0,
                    "upload_mbps": 40.0,
                    "ping_ms": 25.0,
                },
                {
                    "timestamp": "2026-03-15T10:00:00",
                    "download_mbps": 60.0,
                    "upload_mbps": 30.0,
                    "ping_ms": 30.0,
                },
            ],
        )
        conn.close()
        with patch("src.api.routes.analysis.DB_PATH", db):
            resp = client.get("/api/analysis/trends?months=0")
        assert resp.status_code == 200
        assert resp.json()["degradation_detected"] is True

    def test_no_degradation_when_stable(self, tmp_path):
        db = tmp_path / "hermes.db"
        conn = sqlite3.connect(str(db))
        conn.execute(_CREATE)
        _seed(
            conn,
            [
                {
                    "timestamp": "2026-01-15T10:00:00",
                    "download_mbps": 100.0,
                    "upload_mbps": 50.0,
                    "ping_ms": 20.0,
                },
                {
                    "timestamp": "2026-02-15T10:00:00",
                    "download_mbps": 100.0,
                    "upload_mbps": 50.0,
                    "ping_ms": 20.0,
                },
            ],
        )
        conn.close()
        with patch("src.api.routes.analysis.DB_PATH", db):
            resp = client.get("/api/analysis/trends?months=0")
        assert resp.status_code == 200
        # Flat slopes → no degradation
        assert resp.json()["degradation_detected"] is False
