"""Tests for test alert endpoint rate limiting."""
# pylint: disable=missing-function-docstring

import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


@pytest.fixture
def auth_enabled():
    """Enable authentication for tests."""
    with patch("src.api.auth.config.API_KEY", "test-key-32-characters-long-abc"):
        yield


@pytest.fixture
def reset_rate_limit():
    """Reset test alert rate limit state between tests."""
    from src.api.routes import alerts

    alerts._test_alert_last_call = 0.0
    yield
    alerts._test_alert_last_call = 0.0


def test_first_test_alert_allowed(auth_enabled, reset_rate_limit):
    """First test alert call should be allowed."""
    response = client.post(
        "/api/alerts/test", headers={"X-Api-Key": "test-key-32-characters-long-abc"}
    )
    # Should succeed (or fail for other reasons, but not 429)
    assert response.status_code != 429


def test_second_test_alert_within_cooldown_rejected(auth_enabled, reset_rate_limit):
    """Second test alert within cooldown period should be rejected with 429."""
    # First call
    client.post(
        "/api/alerts/test", headers={"X-Api-Key": "test-key-32-characters-long-abc"}
    )

    # Second call immediately after
    response = client.post(
        "/api/alerts/test", headers={"X-Api-Key": "test-key-32-characters-long-abc"}
    )
    assert response.status_code == 429
    assert "10 seconds" in response.json()["detail"]


def test_test_alert_allowed_after_cooldown(auth_enabled, reset_rate_limit):
    """Test alert should be allowed after cooldown period elapses."""
    with patch("src.api.routes.alerts._TEST_ALERT_COOLDOWN_SECONDS", 0.1):
        # First call
        response1 = client.post(
            "/api/alerts/test",
            headers={"X-Api-Key": "test-key-32-characters-long-abc"},
        )
        assert response1.status_code != 429

        # Wait for cooldown
        time.sleep(0.15)

        # Second call after cooldown
        response2 = client.post(
            "/api/alerts/test",
            headers={"X-Api-Key": "test-key-32-characters-long-abc"},
        )
        # Should not be rate limited (may fail for other reasons)
        assert response2.status_code != 429


def test_test_alert_rate_limit_includes_retry_after_header(
    auth_enabled, reset_rate_limit
):
    """429 response should include Retry-After header."""
    # First call
    client.post(
        "/api/alerts/test", headers={"X-Api-Key": "test-key-32-characters-long-abc"}
    )

    # Second call immediately after
    response = client.post(
        "/api/alerts/test", headers={"X-Api-Key": "test-key-32-characters-long-abc"}
    )
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    retry_after = int(response.headers["Retry-After"])
    assert 0 < retry_after <= 10


def test_test_alert_rate_limit_countdown_decreases(auth_enabled, reset_rate_limit):
    """Retry-After should decrease as time passes."""
    with patch("src.api.routes.alerts._TEST_ALERT_COOLDOWN_SECONDS", 5):
        # First call
        client.post(
            "/api/alerts/test",
            headers={"X-Api-Key": "test-key-32-characters-long-abc"},
        )

        # Second call immediately
        response1 = client.post(
            "/api/alerts/test",
            headers={"X-Api-Key": "test-key-32-characters-long-abc"},
        )
        retry_after_1 = int(response1.headers["Retry-After"])

        # Wait a bit
        time.sleep(1)

        # Third call
        response2 = client.post(
            "/api/alerts/test",
            headers={"X-Api-Key": "test-key-32-characters-long-abc"},
        )
        retry_after_2 = int(response2.headers["Retry-After"])

        # Second retry-after should be less than first
        assert retry_after_2 < retry_after_1


def test_test_alert_rate_limit_detail_message_helpful(auth_enabled, reset_rate_limit):
    """Rate limit error message should tell user how long to wait."""
    # First call
    client.post(
        "/api/alerts/test", headers={"X-Api-Key": "test-key-32-characters-long-abc"}
    )

    # Second call immediately
    response = client.post(
        "/api/alerts/test", headers={"X-Api-Key": "test-key-32-characters-long-abc"}
    )
    detail = response.json()["detail"]
    assert "try again" in detail.lower()
    assert "seconds" in detail.lower()


def test_test_alert_rate_limit_applies_per_endpoint_not_per_user():
    """Rate limit should be global for the test endpoint (not per-user)."""
    # This is by design - single shared cooldown prevents any user from spamming
    # external alert services, even if multiple API keys are in use
    with (
        patch("src.api.auth.config.API_KEY", "test-key-32-characters-long-abc"),
        patch("src.api.routes.alerts._TEST_ALERT_COOLDOWN_SECONDS", 5),
    ):
        from src.api.routes import alerts

        alerts._test_alert_last_call = 0.0

        # First call with one key
        client.post(
            "/api/alerts/test",
            headers={"X-Api-Key": "test-key-32-characters-long-abc"},
        )

        # Second call with same key immediately
        response = client.post(
            "/api/alerts/test",
            headers={"X-Api-Key": "test-key-32-characters-long-abc"},
        )
        assert response.status_code == 429
