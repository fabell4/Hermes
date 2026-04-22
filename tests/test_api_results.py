"""Tests for GET /api/results and GET /api/results/latest in src/api/routes/results.py."""
# pylint: disable=missing-function-docstring

import sqlite3
from pathlib import Path
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
    server_name     TEXT    NOT NULL,
    server_location TEXT    NOT NULL,
    server_id       INTEGER
)"""

_SAMPLE_ROW = {
    "timestamp": "2026-04-22T12:00:00",
    "download_mbps": 200.5,
    "upload_mbps": 50.2,
    "ping_ms": 14.3,
    "jitter_ms": 2.1,
    "isp_name": "Test ISP",
    "server_name": "Test Server",
    "server_location": "Berlin, DE",
    "server_id": 99,
}


@pytest.fixture()
def empty_db(tmp_path):
    """Yield a path to an empty results DB."""
    db = tmp_path / "hermes.db"
    conn = sqlite3.connect(db)
    conn.execute(_CREATE)
    conn.commit()
    conn.close()
    with patch("src.api.routes.results.DB_PATH", db):
        yield db


@pytest.fixture()
def populated_db(tmp_path):
    """Yield a path to a DB with 3 rows."""
    db = tmp_path / "hermes.db"
    conn = sqlite3.connect(db)
    conn.execute(_CREATE)
    for i in range(3):
        row = {
            **_SAMPLE_ROW,
            "timestamp": f"2026-04-22T12:0{i}:00",
            "download_mbps": 100.0 + i,
        }
        conn.execute(
            """INSERT INTO results
               (timestamp, download_mbps, upload_mbps, ping_ms, jitter_ms, isp_name,
                server_name, server_location, server_id)
               VALUES (:timestamp, :download_mbps, :upload_mbps, :ping_ms, :jitter_ms,
                       :isp_name, :server_name, :server_location, :server_id)""",
            row,
        )
    conn.commit()
    conn.close()
    with patch("src.api.routes.results.DB_PATH", db):
        yield db


# ---------------------------------------------------------------------------
# GET /api/results — 503 when no DB
# ---------------------------------------------------------------------------


def test_results_503_when_no_db():
    missing = Path("/nonexistent/hermes.db")
    with patch("src.api.routes.results.DB_PATH", missing):
        resp = client.get("/api/results")
    assert resp.status_code == 503


def test_results_latest_503_when_no_db():
    missing = Path("/nonexistent/hermes.db")
    with patch("src.api.routes.results.DB_PATH", missing):
        resp = client.get("/api/results/latest")
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# GET /api/results — empty database
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("empty_db")
def test_results_empty_db_returns_200():
    resp = client.get("/api/results")
    assert resp.status_code == 200


@pytest.mark.usefixtures("empty_db")
def test_results_empty_db_returns_empty_list():
    body = client.get("/api/results").json()
    assert body["results"] == []
    assert body["total"] == 0


@pytest.mark.usefixtures("empty_db")
def test_results_page_defaults():
    body = client.get("/api/results").json()
    assert body["page"] == 1
    assert body["page_size"] == 50


# ---------------------------------------------------------------------------
# GET /api/results — with data
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("populated_db")
def test_results_returns_correct_count():
    body = client.get("/api/results").json()
    assert body["total"] == 3
    assert len(body["results"]) == 3


@pytest.mark.usefixtures("populated_db")
def test_results_ordered_newest_first():
    body = client.get("/api/results").json()
    timestamps = [r["timestamp"] for r in body["results"]]
    assert timestamps == sorted(timestamps, reverse=True)


@pytest.mark.usefixtures("populated_db")
def test_results_pagination():
    body = client.get("/api/results?page=1&page_size=2").json()
    assert len(body["results"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 2


@pytest.mark.usefixtures("populated_db")
def test_results_page_2():
    body = client.get("/api/results?page=2&page_size=2").json()
    assert len(body["results"]) == 1


@pytest.mark.usefixtures("populated_db")
def test_results_contains_expected_fields():
    result = client.get("/api/results").json()["results"][0]
    for field in (
        "id",
        "timestamp",
        "download_mbps",
        "upload_mbps",
        "ping_ms",
        "server_name",
    ):
        assert field in result


@pytest.mark.usefixtures("populated_db")
def test_results_isp_name_present():
    result = client.get("/api/results").json()["results"][0]
    assert result["isp_name"] == "Test ISP"


# ---------------------------------------------------------------------------
# GET /api/results/latest
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("empty_db")
def test_latest_returns_null_on_empty_db():
    body = client.get("/api/results/latest").json()
    assert body is None


@pytest.mark.usefixtures("populated_db")
def test_latest_returns_most_recent_row():
    body = client.get("/api/results/latest").json()
    assert body is not None
    assert body["timestamp"] == "2026-04-22T12:02:00"


@pytest.mark.usefixtures("populated_db")
def test_latest_contains_all_fields():
    body = client.get("/api/results/latest").json()
    for field in (
        "id",
        "download_mbps",
        "upload_mbps",
        "ping_ms",
        "server_name",
        "server_location",
    ):
        assert field in body


@pytest.mark.usefixtures("populated_db")
def test_latest_optional_fields_present():
    body = client.get("/api/results/latest").json()
    assert body["jitter_ms"] == pytest.approx(2.1)
    assert body["isp_name"] == "Test ISP"


def test_latest_optional_fields_null_when_absent(tmp_path):
    db = tmp_path / "hermes.db"
    conn = sqlite3.connect(db)
    conn.execute(_CREATE)
    conn.execute(
        """INSERT INTO results
           (timestamp, download_mbps, upload_mbps, ping_ms, jitter_ms, isp_name,
            server_name, server_location, server_id)
           VALUES ('2026-01-01T00:00:00', 100.0, 50.0, 10.0, NULL, NULL,
                   'S', 'L', NULL)"""
    )
    conn.commit()
    conn.close()
    with patch("src.api.routes.results.DB_PATH", db):
        body = client.get("/api/results/latest").json()
    assert body["jitter_ms"] is None
    assert body["isp_name"] is None
    assert body["server_id"] is None
