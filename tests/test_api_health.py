"""Tests for GET /api/health in src/api/main.py."""
# pylint: disable=missing-function-docstring

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def _make_health_patch(data: dict):
    return patch("src.api.main.rc.load", return_value=data)


def test_health_returns_200():
    with _make_health_patch({}):
        resp = client.get("/api/health")
    assert resp.status_code == 200


def test_health_status_ok_when_scanning_enabled():
    with _make_health_patch({"scanning_disabled": False}):
        body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["scheduler_running"] is True


def test_health_scheduler_running_false_when_disabled():
    with _make_health_patch({"scanning_disabled": True}):
        body = client.get("/api/health").json()
    assert body["scheduler_running"] is False


def test_health_last_run_populated():
    ts = "2026-04-22T12:00:00"
    with _make_health_patch({"last_run_at": ts}):
        body = client.get("/api/health").json()
    assert body["last_run"] == ts


def test_health_next_run_populated():
    ts = "2026-04-22T13:00:00"
    with _make_health_patch({"next_run_at": ts}):
        body = client.get("/api/health").json()
    assert body["next_run"] == ts


def test_health_last_run_none_when_absent():
    with _make_health_patch({}):
        body = client.get("/api/health").json()
    assert body["last_run"] is None
    assert body["next_run"] is None


def test_health_uptime_seconds_is_positive_float():
    with _make_health_patch({}):
        body = client.get("/api/health").json()
    assert isinstance(body["uptime_seconds"], float)
    assert body["uptime_seconds"] >= 0
