"""Tests for src/api/auth.py — rate limiting and logging behaviour."""
# pylint: disable=missing-function-docstring

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.auth import _reset_rate_limit_state

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_rate_state():
    """Reset in-process rate-limit counters between every test."""
    _reset_rate_limit_state()
    yield
    _reset_rate_limit_state()


# ---------------------------------------------------------------------------
# Rate limiting — allowed requests
# ---------------------------------------------------------------------------


def test_rate_limit_allows_requests_under_limit():
    with (
        patch("src.api.auth.config.API_KEY", "secret"),
        patch("src.api.auth.config.RATE_LIMIT_PER_MINUTE", 5),
        patch("src.api.routes.trigger._run_test"),
    ):
        for _ in range(5):
            resp = client.post("/api/trigger", headers={"X-Api-Key": "secret"})
            assert resp.status_code == 200


def test_rate_limit_blocks_at_limit():
    with (
        patch("src.api.auth.config.API_KEY", "secret"),
        patch("src.api.auth.config.RATE_LIMIT_PER_MINUTE", 3),
        patch("src.api.routes.trigger._run_test"),
    ):
        for _ in range(3):
            client.post("/api/trigger", headers={"X-Api-Key": "secret"})
        resp = client.post("/api/trigger", headers={"X-Api-Key": "secret"})
    assert resp.status_code == 429


def test_rate_limit_zero_disables_limiting():
    with (
        patch("src.api.auth.config.API_KEY", "secret"),
        patch("src.api.auth.config.RATE_LIMIT_PER_MINUTE", 0),
        patch("src.api.routes.trigger._run_test"),
    ):
        for _ in range(10):
            resp = client.post("/api/trigger", headers={"X-Api-Key": "secret"})
            assert resp.status_code == 200


def test_rate_limit_not_applied_when_auth_disabled():
    """No rate limiting when API_KEY is not configured."""
    with (
        patch("src.api.auth.config.API_KEY", None),
        patch("src.api.auth.config.RATE_LIMIT_PER_MINUTE", 1),
        patch("src.api.routes.trigger._run_test"),
    ):
        for _ in range(5):
            resp = client.post("/api/trigger")
            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Auth failure logging
# ---------------------------------------------------------------------------


def test_missing_key_is_logged(caplog):
    import logging

    with (
        patch("src.api.auth.config.API_KEY", "secret"),
        caplog.at_level(logging.WARNING, logger="src.api.auth"),
    ):
        client.post("/api/trigger")
    assert any("missing" in r.message.lower() for r in caplog.records)


def test_wrong_key_is_logged(caplog):
    import logging

    with (
        patch("src.api.auth.config.API_KEY", "secret"),
        caplog.at_level(logging.WARNING, logger="src.api.auth"),
    ):
        client.post("/api/trigger", headers={"X-Api-Key": "bad"})
    assert any("invalid" in r.message.lower() for r in caplog.records)


def test_rate_limit_breach_is_logged(caplog):
    import logging

    with (
        patch("src.api.auth.config.API_KEY", "secret"),
        patch("src.api.auth.config.RATE_LIMIT_PER_MINUTE", 1),
        patch("src.api.routes.trigger._run_test"),
        caplog.at_level(logging.WARNING, logger="src.api.auth"),
    ):
        client.post("/api/trigger", headers={"X-Api-Key": "secret"})
        client.post("/api/trigger", headers={"X-Api-Key": "secret"})
    assert any("rate limit" in r.message.lower() for r in caplog.records)
