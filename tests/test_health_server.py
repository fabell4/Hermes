"""Tests for HealthServer."""

import json
import socket
import time
import urllib.error
import urllib.request

import pytest

from src.services.health_server import HealthServer


def _free_port() -> int:
    """Return an available TCP port on localhost."""
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _get(url: str) -> tuple[int, dict]:
    """HTTP GET; returns (status_code, parsed_json)."""
    with urllib.request.urlopen(url) as resp:  # noqa: S310
        return resp.status, json.loads(resp.read())


def _get_raw(url: str) -> int:
    """Return only the HTTP status code, accepting error responses."""
    try:
        with urllib.request.urlopen(url) as resp:  # noqa: S310
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


# ---------------------------------------------------------------------------
# Basic response tests
# ---------------------------------------------------------------------------


def test_health_returns_200_when_status_ok():
    """GET /health returns 200 and status=ok when the status callback returns ok."""
    port = _free_port()
    server = HealthServer(port=port, get_status=lambda: {"status": "ok"})
    server.start()
    time.sleep(0.05)

    code, body = _get(f"http://localhost:{port}/health")

    assert code == 200
    assert body["status"] == "ok"
    server.stop()


def test_health_returns_503_when_status_degraded():
    """GET /health returns 503 when the status callback returns degraded."""
    port = _free_port()
    server = HealthServer(port=port, get_status=lambda: {"status": "degraded"})
    server.start()
    time.sleep(0.05)

    try:
        urllib.request.urlopen(f"http://localhost:{port}/health")  # noqa: S310
    except urllib.error.HTTPError as exc:
        assert exc.code == 503
    else:
        pytest.fail("Expected HTTPError 503")

    server.stop()


def test_health_returns_404_for_unknown_path():
    """Requests to paths other than /health return 404."""
    port = _free_port()
    server = HealthServer(port=port, get_status=lambda: {"status": "ok"})
    server.start()
    time.sleep(0.05)

    code = _get_raw(f"http://localhost:{port}/unknown")
    assert code == 404
    server.stop()


def test_health_payload_contains_expected_keys():
    """The JSON response includes all expected status fields."""
    port = _free_port()
    status = {
        "status": "ok",
        "scheduler": "running",
        "last_run_at": "2026-01-01T00:00:00+00:00",
        "next_run_at": "2026-01-01T01:00:00+00:00",
        "is_running": False,
    }
    server = HealthServer(port=port, get_status=lambda: status)
    server.start()
    time.sleep(0.05)

    _, body = _get(f"http://localhost:{port}/health")

    assert body["scheduler"] == "running"
    assert body["last_run_at"] == "2026-01-01T00:00:00+00:00"
    assert body["next_run_at"] == "2026-01-01T01:00:00+00:00"
    assert body["is_running"] is False
    server.stop()


def test_health_get_status_called_on_each_request():
    """The get_status callable is invoked once per request."""
    port = _free_port()
    call_count = 0

    def counting_status() -> dict:
        nonlocal call_count
        call_count += 1
        return {"status": "ok"}

    server = HealthServer(port=port, get_status=counting_status)
    server.start()
    time.sleep(0.05)

    _get(f"http://localhost:{port}/health")
    _get(f"http://localhost:{port}/health")

    assert call_count == 2
    server.stop()
