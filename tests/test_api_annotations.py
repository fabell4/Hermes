"""Tests for PUT /api/results/{id}/note (result annotations) in src/api/routes/results.py."""
# pylint: disable=missing-function-docstring

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

_CREATE_WITH_NOTE = """
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
    sla_ok          INTEGER,
    note            TEXT
)"""

_CREATE_WITHOUT_NOTE = """
CREATE TABLE IF NOT EXISTS results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    download_mbps   REAL    NOT NULL,
    upload_mbps     REAL    NOT NULL,
    ping_ms         REAL    NOT NULL,
    server_name     TEXT    NOT NULL,
    server_location TEXT    NOT NULL
)"""

_SAMPLE_ROW = {
    "timestamp": "2026-04-22T12:00:00",
    "download_mbps": 200.0,
    "upload_mbps": 50.0,
    "ping_ms": 12.0,
    "jitter_ms": None,
    "isp_name": None,
    "server_name": "Test Server",
    "server_location": "Berlin, DE",
    "server_id": None,
    "packet_loss_pct": None,
    "quality_score": None,
    "sla_ok": None,
}

_INSERT = """
INSERT INTO results
    (timestamp, download_mbps, upload_mbps, ping_ms, jitter_ms, isp_name,
     server_name, server_location, server_id, packet_loss_pct, quality_score, sla_ok)
VALUES
    (:timestamp, :download_mbps, :upload_mbps, :ping_ms, :jitter_ms, :isp_name,
     :server_name, :server_location, :server_id, :packet_loss_pct, :quality_score, :sla_ok)
"""


@pytest.fixture()
def db_with_note_col(tmp_path):
    """DB whose schema already includes the note column."""
    db = tmp_path / "hermes.db"
    conn = sqlite3.connect(db)
    conn.execute(_CREATE_WITH_NOTE)
    conn.execute(_INSERT, _SAMPLE_ROW)
    conn.commit()
    conn.close()
    with patch("src.api.routes.results.DB_PATH", db):
        yield db


@pytest.fixture()
def db_without_note_col(tmp_path):
    """DB created by an older Hermes version — no note column yet."""
    db = tmp_path / "hermes.db"
    conn = sqlite3.connect(db)
    conn.execute(_CREATE_WITHOUT_NOTE)
    conn.execute(
        "INSERT INTO results (timestamp, download_mbps, upload_mbps, ping_ms, server_name, server_location)"
        " VALUES ('2026-04-22T12:00:00', 100.0, 20.0, 15.0, 'Server', 'London, GB')"
    )
    conn.commit()
    conn.close()
    with patch("src.api.routes.results.DB_PATH", db):
        yield db


# ---------------------------------------------------------------------------
# GET /api/results — note field included in response
# ---------------------------------------------------------------------------


def test_results_include_note_field(db_with_note_col):
    resp = client.get("/api/results")
    assert resp.status_code == 200
    row = resp.json()["results"][0]
    assert "note" in row
    assert row["note"] is None


def test_results_latest_includes_note_field(db_with_note_col):
    resp = client.get("/api/results/latest")
    assert resp.status_code == 200
    assert "note" in resp.json()


def test_results_note_default_none_when_column_missing(db_without_note_col):
    """Old DBs without the note column should return note=null without error."""
    resp = client.get("/api/results")
    assert resp.status_code == 200
    row = resp.json()["results"][0]
    assert row.get("note") is None


# ---------------------------------------------------------------------------
# PUT /api/results/{id}/note — set a note
# ---------------------------------------------------------------------------


def test_put_note_sets_value(db_with_note_col):
    resp = client.put("/api/results/1/note", json={"note": "ISP maintenance"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["note"] == "ISP maintenance"
    assert body["id"] == 1


def test_put_note_clears_note_with_null(db_with_note_col):
    # First set a note
    client.put("/api/results/1/note", json={"note": "router reboot"})
    # Then clear it
    resp = client.put("/api/results/1/note", json={"note": None})
    assert resp.status_code == 200
    assert resp.json()["note"] is None


def test_put_note_clears_note_with_empty_string(db_with_note_col):
    """An empty string should be treated as clearing the note (stored as null)."""
    client.put("/api/results/1/note", json={"note": "storm"})
    resp = client.put("/api/results/1/note", json={"note": ""})
    assert resp.status_code == 200
    assert resp.json()["note"] is None


def test_put_note_persists_to_db(db_with_note_col):
    client.put("/api/results/1/note", json={"note": "planned downtime"})
    # Confirm the value is now returned by GET
    resp = client.get("/api/results")
    assert resp.json()["results"][0]["note"] == "planned downtime"


def test_put_note_returns_full_result_schema(db_with_note_col):
    resp = client.put("/api/results/1/note", json={"note": "test"})
    body = resp.json()
    assert "id" in body
    assert "timestamp" in body
    assert "download_mbps" in body
    assert "note" in body


def test_put_note_overwrites_existing_note(db_with_note_col):
    client.put("/api/results/1/note", json={"note": "first note"})
    resp = client.put("/api/results/1/note", json={"note": "updated note"})
    assert resp.status_code == 200
    assert resp.json()["note"] == "updated note"


def test_put_note_with_special_characters(db_with_note_col):
    note = "Storm ⛈️ — ISP said: \"works as expected\""
    resp = client.put("/api/results/1/note", json={"note": note})
    assert resp.status_code == 200
    assert resp.json()["note"] == note


def test_put_note_max_length_accepted(db_with_note_col):
    note = "x" * 500
    resp = client.put("/api/results/1/note", json={"note": note})
    assert resp.status_code == 200
    assert resp.json()["note"] == note


def test_put_note_exceeds_max_length_rejected(db_with_note_col):
    note = "x" * 501
    resp = client.put("/api/results/1/note", json={"note": note})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/results/{id}/note — error cases
# ---------------------------------------------------------------------------


def test_put_note_404_for_nonexistent_result(db_with_note_col):
    resp = client.put("/api/results/9999/note", json={"note": "ghost"})
    assert resp.status_code == 404
    assert "9999" in resp.json()["detail"]


def test_put_note_503_when_no_db():
    with patch("src.api.routes.results.DB_PATH", Path("/nonexistent/hermes.db")):
        resp = client.put("/api/results/1/note", json={"note": "test"})
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# PUT /api/results/{id}/note — lazy migration (old DB without note column)
# ---------------------------------------------------------------------------


def test_put_note_migrates_old_db(db_without_note_col):
    """PUT /note should add the note column if it doesn't exist yet."""
    resp = client.put("/api/results/1/note", json={"note": "migrated!"})
    assert resp.status_code == 200
    assert resp.json()["note"] == "migrated!"


def test_put_note_migration_idempotent(db_with_note_col):
    """Calling PUT /note on a DB that already has the column should not fail."""
    resp1 = client.put("/api/results/1/note", json={"note": "first"})
    resp2 = client.put("/api/results/1/note", json={"note": "second"})
    assert resp1.status_code == 200
    assert resp2.status_code == 200


# ---------------------------------------------------------------------------
# Export includes note column
# ---------------------------------------------------------------------------


def test_csv_export_includes_note_column(db_with_note_col):
    import csv
    import io

    with patch("src.api.routes.export.DB_PATH", db_with_note_col):
        resp = client.get("/api/export/csv")
    reader = csv.DictReader(io.StringIO(resp.text))
    assert reader.fieldnames is not None
    assert "note" in reader.fieldnames


def test_json_export_includes_note_field(db_with_note_col):
    import json as _json

    with patch("src.api.routes.export.DB_PATH", db_with_note_col):
        resp = client.get("/api/export/json")
    data = _json.loads(resp.content)
    assert "note" in data["results"][0]


def test_csv_export_note_value_in_row(db_with_note_col):
    import csv
    import io

    # Set a note first
    client.put("/api/results/1/note", json={"note": "export test note"})

    with patch("src.api.routes.export.DB_PATH", db_with_note_col):
        resp = client.get("/api/export/csv")
    reader = csv.DictReader(io.StringIO(resp.text))
    row = next(reader)
    assert row["note"] == "export test note"
