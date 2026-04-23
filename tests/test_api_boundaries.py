"""API endpoint boundary and rejection tests.

Principle 1 — Fail fast and loudly:
  Every external input is tested in three categories:
  1. Valid       — accepted with the correct success status code
  2. Invalid     — rejected with the correct error status code
  3. Boundary    — values at the exact edge of the valid range

Principle 4 — Defence in depth at boundaries:
  Every protected endpoint must reject unauthenticated requests consistently.
  All HTTP error responses must carry a "detail" field for uniform error handling.
  Public endpoints must remain accessible without auth headers.
"""
# pylint: disable=missing-function-docstring

import sqlite3
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

_VALID_CONFIG_BODY = {
    "interval_minutes": 60,
    "enabled_exporters": ["csv"],
    "scanning_enabled": True,
}

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def auth_enabled():
    """Enable API-key auth with a known test key. Returns the key string."""
    key = "boundary-test-key-abc"
    with patch("src.api.auth.config.API_KEY", key):
        yield key


@pytest.fixture()
def empty_db(tmp_path):
    """Provide a path to an empty results database, patched into the results route."""
    db = tmp_path / "hermes.db"
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            download_mbps REAL NOT NULL,
            upload_mbps REAL NOT NULL,
            ping_ms REAL NOT NULL,
            jitter_ms REAL,
            isp_name TEXT,
            server_name TEXT NOT NULL,
            server_location TEXT NOT NULL,
            server_id INTEGER
        )"""
    )
    conn.commit()
    conn.close()
    with patch("src.api.routes.results.DB_PATH", db):
        yield db


# ---------------------------------------------------------------------------
# Principle 4: every protected endpoint rejects unauthenticated requests
# ---------------------------------------------------------------------------

_PROTECTED: list[tuple[str, str]] = [
    ("POST", "/api/trigger"),
    ("PUT", "/api/config"),
]

_PUBLIC: list[tuple[str, str]] = [
    ("GET", "/api/health"),
    ("GET", "/api/config"),
]


@pytest.mark.parametrize("method,path", _PROTECTED)
def test_protected_endpoint_returns_401_when_key_missing(auth_enabled, method, path):
    """Every protected endpoint must return 401 when no X-Api-Key header is sent."""
    resp = client.request(method, path, json=_VALID_CONFIG_BODY)
    assert resp.status_code == 401


@pytest.mark.parametrize("method,path", _PROTECTED)
def test_protected_endpoint_returns_403_when_key_wrong(auth_enabled, method, path):
    """Every protected endpoint must return 403 when an incorrect key is sent."""
    resp = client.request(
        method, path, json=_VALID_CONFIG_BODY, headers={"X-Api-Key": "wrong"}
    )
    assert resp.status_code == 403


@pytest.mark.parametrize("method,path", _PUBLIC)
def test_public_endpoint_accessible_without_auth(method, path):
    """Public endpoints must return 200 without any auth header."""
    with patch("src.api.main.rc.load", return_value={}):
        with patch(
            "src.api.routes.config.runtime_config.get_interval_minutes", return_value=60
        ):
            with patch(
                "src.api.routes.config.runtime_config.get_enabled_exporters",
                return_value=["csv"],
            ):
                with patch(
                    "src.api.routes.config.runtime_config.load", return_value={}
                ):
                    resp = client.request(method, path)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Principle 3: error responses always carry a consistent "detail" field
# ---------------------------------------------------------------------------


def test_401_response_has_detail_field(auth_enabled):
    resp = client.post("/api/trigger", json={})
    assert resp.status_code == 401
    assert "detail" in resp.json()


def test_403_response_has_detail_field(auth_enabled):
    resp = client.post("/api/trigger", json={}, headers={"X-Api-Key": "wrong"})
    assert resp.status_code == 403
    assert "detail" in resp.json()


def test_422_response_has_detail_field():
    """A validation error must include the 'detail' field."""
    resp = client.put("/api/config", json={})
    assert resp.status_code == 422
    assert "detail" in resp.json()


# ---------------------------------------------------------------------------
# PUT /api/config — request body validation (principle 1: fail fast)
# ---------------------------------------------------------------------------


def test_put_config_empty_body_returns_422():
    """An empty body must be rejected — all three fields are required."""
    assert client.put("/api/config", json={}).status_code == 422


def test_put_config_wrong_type_for_interval_returns_422():
    """A string where int is expected must be rejected by Pydantic."""
    body = {**_VALID_CONFIG_BODY, "interval_minutes": "not-an-int"}
    assert client.put("/api/config", json=body).status_code == 422


def test_put_config_wrong_type_for_exporters_list_returns_422():
    """A scalar string where a list is expected must be rejected."""
    body = {**_VALID_CONFIG_BODY, "enabled_exporters": "csv"}
    assert client.put("/api/config", json=body).status_code == 422


def test_put_config_null_exporters_returns_422():
    """A null enabled_exporters must be rejected — the field is required."""
    body = {**_VALID_CONFIG_BODY, "enabled_exporters": None}
    assert client.put("/api/config", json=body).status_code == 422


def test_put_config_missing_scanning_enabled_returns_422():
    """A body missing scanning_enabled must be rejected."""
    body = {"interval_minutes": 30, "enabled_exporters": ["csv"]}
    assert client.put("/api/config", json=body).status_code == 422


def test_put_config_missing_interval_returns_422():
    """A body missing interval_minutes must be rejected."""
    body = {"enabled_exporters": ["csv"], "scanning_enabled": True}
    assert client.put("/api/config", json=body).status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/config — interval boundary values (ge=5, le=1440)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("interval", [5, 720, 1440])
def test_put_config_valid_interval_is_accepted(interval):
    """Boundary and mid-range intervals 5, 720, and 1440 must all be accepted."""
    body = {**_VALID_CONFIG_BODY, "interval_minutes": interval}
    with patch("src.api.routes.config.runtime_config.save"):
        with patch("src.api.routes.config.runtime_config.load", return_value={}):
            with patch(
                "src.api.routes.config.runtime_config.get_interval_minutes",
                return_value=interval,
            ):
                with patch(
                    "src.api.routes.config.runtime_config.get_enabled_exporters",
                    return_value=["csv"],
                ):
                    resp = client.put("/api/config", json=body)
    assert resp.status_code == 200


@pytest.mark.parametrize("interval", [4, 1441])
def test_put_config_out_of_range_interval_returns_422(interval):
    """Intervals 4 and 1441 are outside [5, 1440] and must be rejected."""
    body = {**_VALID_CONFIG_BODY, "interval_minutes": interval}
    assert client.put("/api/config", json=body).status_code == 422


# ---------------------------------------------------------------------------
# GET /api/results — pagination boundary values (ge=1, page_size le=500)
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("empty_db")
def test_results_page_zero_returns_422():
    """page=0 is below ge=1 — must be rejected."""
    assert client.get("/api/results?page=0").status_code == 422


@pytest.mark.usefixtures("empty_db")
def test_results_page_size_zero_returns_422():
    """page_size=0 is below ge=1 — must be rejected."""
    assert client.get("/api/results?page_size=0").status_code == 422


@pytest.mark.usefixtures("empty_db")
def test_results_page_size_at_maximum_boundary_is_accepted():
    """page_size=500 is exactly at le=500 — must be accepted."""
    assert client.get("/api/results?page_size=500").status_code == 200


@pytest.mark.usefixtures("empty_db")
def test_results_page_size_over_maximum_returns_422():
    """page_size=501 exceeds le=500 — must be rejected."""
    assert client.get("/api/results?page_size=501").status_code == 422


@pytest.mark.usefixtures("empty_db")
def test_results_page_one_is_minimum_valid_value():
    """page=1 is the minimum valid value — must be accepted."""
    assert client.get("/api/results?page=1").status_code == 200


@pytest.mark.usefixtures("empty_db")
def test_results_non_integer_page_returns_422():
    """A non-integer page query parameter must be rejected."""
    assert client.get("/api/results?page=abc").status_code == 422


@pytest.mark.usefixtures("empty_db")
def test_results_non_integer_page_size_returns_422():
    """A non-integer page_size query parameter must be rejected."""
    assert client.get("/api/results?page_size=abc").status_code == 422
