"""Tests for GET /api/export/csv and GET /api/export/json in src/api/routes/export.py."""
# pylint: disable=missing-function-docstring

import csv
import io
import json
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
    server_id       INTEGER,
    packet_loss_pct REAL,
    quality_score   REAL,
    sla_ok          INTEGER
)"""

_INSERT = """
INSERT INTO results
    (timestamp, download_mbps, upload_mbps, ping_ms, jitter_ms, isp_name,
     server_name, server_location, server_id, packet_loss_pct, quality_score, sla_ok)
VALUES
    (:timestamp, :download_mbps, :upload_mbps, :ping_ms, :jitter_ms, :isp_name,
     :server_name, :server_location, :server_id, :packet_loss_pct, :quality_score, :sla_ok)
"""

_SAMPLE_ROWS = [
    {
        "timestamp": "2026-04-01T10:00:00",
        "download_mbps": 150.0,
        "upload_mbps": 30.0,
        "ping_ms": 10.5,
        "jitter_ms": 1.2,
        "isp_name": "ISP A",
        "server_name": "Server 1",
        "server_location": "Berlin, DE",
        "server_id": 10,
        "packet_loss_pct": 0.0,
        "quality_score": 88.5,
        "sla_ok": 1,
    },
    {
        "timestamp": "2026-04-02T12:00:00",
        "download_mbps": 80.0,
        "upload_mbps": 20.0,
        "ping_ms": 25.0,
        "jitter_ms": None,
        "isp_name": None,
        "server_name": "Server 2",
        "server_location": "Paris, FR",
        "server_id": None,
        "packet_loss_pct": None,
        "quality_score": None,
        "sla_ok": 0,
    },
    {
        "timestamp": "2026-05-01T08:00:00",
        "download_mbps": 200.0,
        "upload_mbps": 50.0,
        "ping_ms": 8.0,
        "jitter_ms": 0.5,
        "isp_name": "ISP B",
        "server_name": "Server 3",
        "server_location": "London, GB",
        "server_id": 99,
        "packet_loss_pct": 0.1,
        "quality_score": 95.0,
        "sla_ok": None,
    },
]


@pytest.fixture()
def empty_db(tmp_path):
    """Yield a path to an empty results database."""
    db = tmp_path / "hermes.db"
    conn = sqlite3.connect(db)
    conn.execute(_CREATE)
    conn.commit()
    conn.close()
    with patch("src.api.routes.export.DB_PATH", db):
        yield db


@pytest.fixture()
def populated_db(tmp_path):
    """Yield a path to a database with 3 rows spanning two months."""
    db = tmp_path / "hermes.db"
    conn = sqlite3.connect(db)
    conn.execute(_CREATE)
    for row in _SAMPLE_ROWS:
        conn.execute(_INSERT, row)
    conn.commit()
    conn.close()
    with patch("src.api.routes.export.DB_PATH", db):
        yield db


# ---------------------------------------------------------------------------
# 503 when database is missing
# ---------------------------------------------------------------------------


def test_csv_export_503_when_no_db():
    with patch("src.api.routes.export.DB_PATH", Path("/nonexistent/hermes.db")):
        resp = client.get("/api/export/csv")
    assert resp.status_code == 503


def test_json_export_503_when_no_db():
    with patch("src.api.routes.export.DB_PATH", Path("/nonexistent/hermes.db")):
        resp = client.get("/api/export/json")
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# CSV export — response headers
# ---------------------------------------------------------------------------


def test_csv_export_headers(populated_db):
    resp = client.get("/api/export/csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.headers["content-disposition"].endswith('.csv"')


def test_json_export_headers(populated_db):
    resp = client.get("/api/export/json")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.headers["content-disposition"].endswith('.json"')


# ---------------------------------------------------------------------------
# CSV export — content
# ---------------------------------------------------------------------------


def test_csv_export_all_rows(populated_db):
    resp = client.get("/api/export/csv")
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 3
    # Ordered ascending by timestamp
    assert rows[0]["timestamp"] == "2026-04-01T10:00:00"
    assert rows[1]["timestamp"] == "2026-04-02T12:00:00"
    assert rows[2]["timestamp"] == "2026-05-01T08:00:00"


def test_csv_export_has_id_column(populated_db):
    resp = client.get("/api/export/csv")
    reader = csv.DictReader(io.StringIO(resp.text))
    row = next(reader)
    assert "id" in row
    assert row["id"].isdigit()


def test_csv_export_empty_db(empty_db):
    resp = client.get("/api/export/csv")
    assert resp.status_code == 200
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert rows == []


def test_csv_export_fieldnames(populated_db):
    resp = client.get("/api/export/csv")
    reader = csv.DictReader(io.StringIO(resp.text))
    assert reader.fieldnames is not None
    expected = [
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
    assert reader.fieldnames == expected


def test_csv_export_numeric_values(populated_db):
    resp = client.get("/api/export/csv")
    reader = csv.DictReader(io.StringIO(resp.text))
    row = next(reader)
    assert float(row["download_mbps"]) == pytest.approx(150.0)
    assert float(row["upload_mbps"]) == pytest.approx(30.0)
    assert float(row["ping_ms"]) == pytest.approx(10.5)


# ---------------------------------------------------------------------------
# JSON export — content
# ---------------------------------------------------------------------------


def test_json_export_all_rows(populated_db):
    resp = client.get("/api/export/json")
    data = json.loads(resp.content)
    assert "results" in data
    assert "exported_at" in data
    assert len(data["results"]) == 3


def test_json_export_ascending_order(populated_db):
    resp = client.get("/api/export/json")
    data = json.loads(resp.content)
    timestamps = [r["timestamp"] for r in data["results"]]
    assert timestamps == sorted(timestamps)


def test_json_export_empty_db(empty_db):
    resp = client.get("/api/export/json")
    assert resp.status_code == 200
    data = json.loads(resp.content)
    assert data["results"] == []


def test_json_export_sla_ok_true_is_bool(populated_db):
    """sla_ok stored as INTEGER 1 in SQLite should be exported as JSON true."""
    resp = client.get("/api/export/json")
    data = json.loads(resp.content)
    row_with_sla_true = next(
        r for r in data["results"] if r["timestamp"] == "2026-04-01T10:00:00"
    )
    assert row_with_sla_true["sla_ok"] is True


def test_json_export_sla_ok_false_is_bool(populated_db):
    """sla_ok stored as INTEGER 0 in SQLite should be exported as JSON false."""
    resp = client.get("/api/export/json")
    data = json.loads(resp.content)
    row_with_sla_false = next(
        r for r in data["results"] if r["timestamp"] == "2026-04-02T12:00:00"
    )
    assert row_with_sla_false["sla_ok"] is False


def test_json_export_sla_ok_null_is_none(populated_db):
    """sla_ok stored as NULL in SQLite should be exported as JSON null."""
    resp = client.get("/api/export/json")
    data = json.loads(resp.content)
    row_null_sla = next(
        r for r in data["results"] if r["timestamp"] == "2026-05-01T08:00:00"
    )
    assert row_null_sla["sla_ok"] is None


def test_json_export_nullable_fields_are_null(populated_db):
    """Nullable fields stored as NULL should appear as null in JSON."""
    resp = client.get("/api/export/json")
    data = json.loads(resp.content)
    row = next(r for r in data["results"] if r["timestamp"] == "2026-04-02T12:00:00")
    assert row["jitter_ms"] is None
    assert row["isp_name"] is None
    assert row["server_id"] is None
    assert row["packet_loss_pct"] is None
    assert row["quality_score"] is None


def test_json_export_has_id_field(populated_db):
    resp = client.get("/api/export/json")
    data = json.loads(resp.content)
    for row in data["results"]:
        assert "id" in row
        assert isinstance(row["id"], int)


# ---------------------------------------------------------------------------
# Date range filters — CSV
# ---------------------------------------------------------------------------


def test_csv_export_start_filter(populated_db):
    resp = client.get("/api/export/csv?start=2026-05-01T00:00:00")
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["timestamp"] == "2026-05-01T08:00:00"


def test_csv_export_end_filter(populated_db):
    resp = client.get("/api/export/csv?end=2026-04-01T23:59:59")
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["timestamp"] == "2026-04-01T10:00:00"


def test_csv_export_start_and_end_filter(populated_db):
    resp = client.get(
        "/api/export/csv?start=2026-04-01T00:00:00&end=2026-04-30T23:59:59"
    )
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 2


def test_csv_export_filter_no_matches(populated_db):
    resp = client.get("/api/export/csv?start=2030-01-01T00:00:00")
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert rows == []


# ---------------------------------------------------------------------------
# Date range filters — JSON
# ---------------------------------------------------------------------------


def test_json_export_start_filter(populated_db):
    resp = client.get("/api/export/json?start=2026-05-01T00:00:00")
    data = json.loads(resp.content)
    assert len(data["results"]) == 1
    assert data["results"][0]["timestamp"] == "2026-05-01T08:00:00"


def test_json_export_end_filter(populated_db):
    resp = client.get("/api/export/json?end=2026-04-01T23:59:59")
    data = json.loads(resp.content)
    assert len(data["results"]) == 1


def test_json_export_start_and_end_filter(populated_db):
    resp = client.get(
        "/api/export/json?start=2026-04-01T00:00:00&end=2026-04-30T23:59:59"
    )
    data = json.loads(resp.content)
    assert len(data["results"]) == 2


def test_json_export_filter_no_matches(populated_db):
    resp = client.get("/api/export/json?start=2030-01-01T00:00:00")
    data = json.loads(resp.content)
    assert data["results"] == []


# ---------------------------------------------------------------------------
# Invalid date parameters
# ---------------------------------------------------------------------------


def test_csv_export_invalid_start(populated_db):
    resp = client.get("/api/export/csv?start=not-a-date")
    assert resp.status_code == 422
    assert "start" in resp.json()["detail"]


def test_csv_export_invalid_end(populated_db):
    resp = client.get("/api/export/csv?end=31-13-2026")
    assert resp.status_code == 422
    assert "end" in resp.json()["detail"]


def test_json_export_invalid_start(populated_db):
    resp = client.get("/api/export/json?start=not-a-date")
    assert resp.status_code == 422


def test_json_export_invalid_end(populated_db):
    resp = client.get("/api/export/json?end=bad-value")
    assert resp.status_code == 422
