"""Tests for GET /api/config and PUT /api/config in src/api/routes/config.py."""
# pylint: disable=missing-function-docstring

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

_BASE_CONFIG = {
    "interval_minutes": 30,
    "enabled_exporters": ["csv", "sqlite"],
    "scanning_enabled": True,
}

_RUNTIME_LOAD = {"scanning_disabled": False}


def _patch_config_reads(interval=30, exporters=None):
    """Return a context manager that stubs the three read helpers."""
    if exporters is None:
        exporters = ["csv", "sqlite"]
    return (
        patch("src.api.routes.config.runtime_config.get_interval_minutes", return_value=interval),
        patch("src.api.routes.config.runtime_config.get_enabled_exporters", return_value=exporters),
        patch("src.api.routes.config.runtime_config.load", return_value=_RUNTIME_LOAD),
    )


# ---------------------------------------------------------------------------
# GET /api/config
# ---------------------------------------------------------------------------

def test_get_config_returns_200():
    p1, p2, p3 = _patch_config_reads()
    with p1, p2, p3:
        resp = client.get("/api/config")
    assert resp.status_code == 200


def test_get_config_returns_interval():
    p1, p2, p3 = _patch_config_reads(interval=60)
    with p1, p2, p3:
        body = client.get("/api/config").json()
    assert body["interval_minutes"] == 60


def test_get_config_returns_exporters():
    p1, p2, p3 = _patch_config_reads(exporters=["prometheus"])
    with p1, p2, p3:
        body = client.get("/api/config").json()
    assert body["enabled_exporters"] == ["prometheus"]


def test_get_config_scanning_enabled_when_not_disabled():
    p1, p2, p3 = _patch_config_reads()
    with p1, p2, p3:
        body = client.get("/api/config").json()
    assert body["scanning_enabled"] is True


def test_get_config_scanning_disabled():
    p1, p2, p3 = (
        patch("src.api.routes.config.runtime_config.get_interval_minutes", return_value=30),
        patch("src.api.routes.config.runtime_config.get_enabled_exporters", return_value=["csv"]),
        patch("src.api.routes.config.runtime_config.load",
              return_value={"scanning_disabled": True}),
    )
    with p1, p2, p3:
        body = client.get("/api/config").json()
    assert body["scanning_enabled"] is False


# ---------------------------------------------------------------------------
# PUT /api/config
# ---------------------------------------------------------------------------

def test_put_config_returns_200_on_valid_body():
    mock_save = MagicMock()
    p1, p2, p3 = _patch_config_reads()
    with patch("src.api.routes.config.runtime_config.save", mock_save), p1, p2, p3:
        resp = client.put("/api/config", json=_BASE_CONFIG)
    assert resp.status_code == 200


def test_put_config_persists_via_save():
    mock_save = MagicMock()
    p1, p2, p3 = _patch_config_reads()
    with patch("src.api.routes.config.runtime_config.save", mock_save), p1, p2, p3:
        client.put("/api/config", json=_BASE_CONFIG)
    mock_save.assert_called_once()
    saved = mock_save.call_args[0][0]
    assert saved["interval_minutes"] == 30
    assert saved["enabled_exporters"] == ["csv", "sqlite"]
    assert saved["scanning_disabled"] is False


def test_put_config_scanning_disabled_flag():
    mock_save = MagicMock()
    payload = {**_BASE_CONFIG, "scanning_enabled": False}
    p1, p2, p3 = _patch_config_reads()
    with patch("src.api.routes.config.runtime_config.save", mock_save), p1, p2, p3:
        client.put("/api/config", json=payload)
    saved = mock_save.call_args[0][0]
    assert saved["scanning_disabled"] is True


def test_put_config_unknown_exporter_returns_422():
    payload = {**_BASE_CONFIG, "enabled_exporters": ["csv", "ftp"]}
    resp = client.put("/api/config", json=payload)
    assert resp.status_code == 422


def test_put_config_422_detail_names_unknown_exporter():
    payload = {**_BASE_CONFIG, "enabled_exporters": ["notreal"]}
    body = client.put("/api/config", json=payload).json()
    assert "notreal" in body["detail"]


def test_put_config_all_valid_exporters_accepted():
    mock_save = MagicMock()
    payload = {**_BASE_CONFIG, "enabled_exporters": ["csv", "sqlite", "prometheus", "loki"]}
    p1, p2, p3 = _patch_config_reads(exporters=["csv", "sqlite", "prometheus", "loki"])
    with patch("src.api.routes.config.runtime_config.save", mock_save), p1, p2, p3:
        resp = client.put("/api/config", json=payload)
    assert resp.status_code == 200


@pytest.mark.parametrize("interval", [4, 1441])
def test_put_config_rejects_out_of_range_interval(interval):
    payload = {**_BASE_CONFIG, "interval_minutes": interval}
    resp = client.put("/api/config", json=payload)
    assert resp.status_code == 422
