"""Tests for SSRF protection in alert configuration endpoints.

NOTE: This file intentionally uses insecure URLs, private IPs, and dangerous schemes
to verify that our SSRF protection correctly BLOCKS them. All flagged security issues
are test vectors, not vulnerabilities.
"""
# pylint: disable=missing-function-docstring
# NOSONAR - All http://, private IPs, and dangerous URLs in this file are intentional test data

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


def _put_alerts_with_webhook_url(url: str, auth_enabled_fixture) -> dict:
    """Helper to PUT alert config with a specific webhook URL."""
    payload = {
        "enabled": False,
        "failure_threshold": 3,
        "cooldown_minutes": 60,
        "providers": {
            "webhook": {"enabled": True, "url": url},
            "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
            "ntfy": {
                "enabled": False,
                "url": "https://ntfy.sh",
                "topic": "",
                "token": "",
                "priority": 3,
                "tags": ["warning", "rotating_light"],
            },
            "apprise": {"enabled": False, "url": ""},
        },
    }
    return client.put(
        "/api/alerts",
        json=payload,
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    ).json()


# ---------------------------------------------------------------------------
# Valid URLs (should be accepted)
# ---------------------------------------------------------------------------


def test_valid_https_url_accepted(auth_enabled):
    """Valid HTTPS URL should be accepted."""
    response = client.put(
        "/api/alerts",
        json={
            "enabled": False,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {
                "webhook": {
                    "enabled": True,
                    "url": "https://hooks.example.com/webhook",
                },
                "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
                "ntfy": {
                    "enabled": False,
                    "url": "https://ntfy.sh",
                    "topic": "",
                    "token": "",
                    "priority": 3,
                    "tags": ["warning"],
                },
                "apprise": {"enabled": False, "url": ""},
            },
        },
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    )
    assert response.status_code == 200


def test_valid_http_url_accepted(auth_enabled):
    """Valid HTTP URL should be accepted."""
    response = client.put(
        "/api/alerts",
        json={
            "enabled": False,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {
                "webhook": {
                    "enabled": True,
                    "url": "http://hooks.example.com:8080/webhook",
                },
                "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
                "ntfy": {
                    "enabled": False,
                    "url": "https://ntfy.sh",
                    "topic": "",
                    "token": "",
                    "priority": 3,
                    "tags": [],
                },
                "apprise": {"enabled": False, "url": ""},
            },
        },
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    )
    assert response.status_code == 200


def test_empty_url_accepted(auth_enabled):
    """Empty URL (disabled provider) should be accepted."""
    response = client.put(
        "/api/alerts",
        json={
            "enabled": False,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {
                "webhook": {"enabled": False, "url": ""},
                "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
                "ntfy": {
                    "enabled": False,
                    "url": "",
                    "topic": "",
                    "token": "",
                    "priority": 3,
                    "tags": [],
                },
                "apprise": {"enabled": False, "url": ""},
            },
        },
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Invalid schemes (should be rejected)
# ---------------------------------------------------------------------------


def test_file_scheme_rejected(auth_enabled):
    """file:// scheme should be rejected to prevent file system access."""
    response = client.put(
        "/api/alerts",
        json={
            "enabled": False,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {
                "webhook": {"enabled": True, "url": "file:///etc/passwd"},
                "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
                "ntfy": {
                    "enabled": False,
                    "url": "https://ntfy.sh",
                    "topic": "",
                    "token": "",
                    "priority": 3,
                    "tags": [],
                },
                "apprise": {"enabled": False, "url": ""},
            },
        },
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    )
    assert response.status_code == 422
    assert "file://" in response.json()["detail"].lower()


def test_ftp_scheme_rejected(auth_enabled):
    """ftp:// scheme should be rejected."""
    response = client.put(
        "/api/alerts",
        json={
            "enabled": False,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {
                "webhook": {"enabled": False, "url": ""},
                "gotify": {
                    "enabled": True,
                    "url": "ftp://internal.server/path",
                    "token": "x",
                    "priority": 5,
                },
                "ntfy": {
                    "enabled": False,
                    "url": "https://ntfy.sh",
                    "topic": "",
                    "token": "",
                    "priority": 3,
                    "tags": [],
                },
                "apprise": {"enabled": False, "url": ""},
            },
        },
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    )
    assert response.status_code == 422
    assert "ftp://" in response.json()["detail"].lower()


def test_data_scheme_rejected(auth_enabled):
    """data: scheme should be rejected."""
    response = client.put(
        "/api/alerts",
        json={
            "enabled": False,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {
                "webhook": {"enabled": False, "url": ""},
                "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
                "ntfy": {
                    "enabled": True,
                    "url": "data:text/plain,hello",
                    "topic": "test",
                    "token": "",
                    "priority": 3,
                    "tags": [],
                },
                "apprise": {"enabled": False, "url": ""},
            },
        },
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    )
    assert response.status_code == 422
    assert "data://" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Localhost addresses (should be rejected)
# ---------------------------------------------------------------------------


def test_localhost_hostname_rejected(auth_enabled):
    """localhost hostname should be rejected."""
    response = client.put(
        "/api/alerts",
        json={
            "enabled": False,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {
                "webhook": {"enabled": True, "url": "http://localhost:6379/"},
                "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
                "ntfy": {
                    "enabled": False,
                    "url": "https://ntfy.sh",
                    "topic": "",
                    "token": "",
                    "priority": 3,
                    "tags": [],
                },
                "apprise": {"enabled": False, "url": ""},
            },
        },
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    )
    assert response.status_code == 422
    assert "localhost" in response.json()["detail"].lower()


def test_ipv4_localhost_rejected(auth_enabled):
    """127.0.0.1 should be rejected."""
    response = client.put(
        "/api/alerts",
        json={
            "enabled": False,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {
                "webhook": {"enabled": False, "url": ""},
                "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
                "ntfy": {
                    "enabled": False,
                    "url": "https://ntfy.sh",
                    "topic": "",
                    "token": "",
                    "priority": 3,
                    "tags": [],
                },
                "apprise": {"enabled": True, "url": "http://127.0.0.1:8000/notify"},
            },
        },
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    )
    assert response.status_code == 422
    assert "localhost" in response.json()["detail"].lower()


def test_ipv6_localhost_rejected(auth_enabled):
    """::1 should be rejected."""
    response = client.put(
        "/api/alerts",
        json={
            "enabled": False,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {
                "webhook": {"enabled": True, "url": "http://[::1]:8080/hook"},
                "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
                "ntfy": {
                    "enabled": False,
                    "url": "https://ntfy.sh",
                    "topic": "",
                    "token": "",
                    "priority": 3,
                    "tags": [],
                },
                "apprise": {"enabled": False, "url": ""},
            },
        },
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    )
    assert response.status_code == 422
    assert "localhost" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Private IP ranges (should be rejected)
# ---------------------------------------------------------------------------


def test_private_ip_10_rejected(auth_enabled):
    """10.x.x.x (RFC 1918) should be rejected."""
    response = client.put(
        "/api/alerts",
        json={
            "enabled": False,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {
                "webhook": {"enabled": True, "url": "http://10.0.0.1:8080/webhook"},
                "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
                "ntfy": {
                    "enabled": False,
                    "url": "https://ntfy.sh",
                    "topic": "",
                    "token": "",
                    "priority": 3,
                    "tags": [],
                },
                "apprise": {"enabled": False, "url": ""},
            },
        },
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    )
    assert response.status_code == 422
    assert "private" in response.json()["detail"].lower()


def test_private_ip_192_rejected(auth_enabled):
    """192.168.x.x (RFC 1918) should be rejected."""
    response = client.put(
        "/api/alerts",
        json={
            "enabled": False,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {
                "webhook": {"enabled": False, "url": ""},
                "gotify": {
                    "enabled": True,
                    "url": "http://192.168.1.1/gotify",
                    "token": "x",
                    "priority": 5,
                },
                "ntfy": {
                    "enabled": False,
                    "url": "https://ntfy.sh",
                    "topic": "",
                    "token": "",
                    "priority": 3,
                    "tags": [],
                },
                "apprise": {"enabled": False, "url": ""},
            },
        },
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    )
    assert response.status_code == 422
    assert "private" in response.json()["detail"].lower()


def test_private_ip_172_rejected(auth_enabled):
    """172.16-31.x.x (RFC 1918) should be rejected."""
    response = client.put(
        "/api/alerts",
        json={
            "enabled": False,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {
                "webhook": {"enabled": False, "url": ""},
                "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
                "ntfy": {
                    "enabled": True,
                    "url": "http://172.20.0.5:5000",
                    "topic": "test",
                    "token": "",
                    "priority": 3,
                    "tags": [],
                },
                "apprise": {"enabled": False, "url": ""},
            },
        },
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    )
    assert response.status_code == 422
    assert "private" in response.json()["detail"].lower()


def test_link_local_rejected(auth_enabled):
    """169.254.x.x (link-local) should be rejected."""
    response = client.put(
        "/api/alerts",
        json={
            "enabled": False,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {
                "webhook": {
                    "enabled": True,
                    "url": "http://169.254.169.254/latest/meta-data/",
                },
                "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
                "ntfy": {
                    "enabled": False,
                    "url": "https://ntfy.sh",
                    "topic": "",
                    "token": "",
                    "priority": 3,
                    "tags": [],
                },
                "apprise": {"enabled": False, "url": ""},
            },
        },
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    )
    assert response.status_code == 422
    assert "link-local" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_url_without_hostname_rejected(auth_enabled):
    """URL without hostname should be rejected."""
    response = client.put(
        "/api/alerts",
        json={
            "enabled": False,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {
                "webhook": {"enabled": True, "url": "http://"},
                "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
                "ntfy": {
                    "enabled": False,
                    "url": "https://ntfy.sh",
                    "topic": "",
                    "token": "",
                    "priority": 3,
                    "tags": [],
                },
                "apprise": {"enabled": False, "url": ""},
            },
        },
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    )
    assert response.status_code == 422


def test_multiple_provider_urls_validated(auth_enabled):
    """All provider URLs should be validated, not just the first one."""
    response = client.put(
        "/api/alerts",
        json={
            "enabled": False,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {
                "webhook": {"enabled": True, "url": "https://valid.example.com"},
                "gotify": {
                    "enabled": True,
                    "url": "http://localhost:8080",
                    "token": "x",
                    "priority": 5,
                },
                "ntfy": {
                    "enabled": False,
                    "url": "https://ntfy.sh",
                    "topic": "",
                    "token": "",
                    "priority": 3,
                    "tags": [],
                },
                "apprise": {"enabled": False, "url": ""},
            },
        },
        headers={"X-Api-Key": "test-key-32-characters-long-abc"},
    )
    assert response.status_code == 422
    # Should fail on the second provider (Gotify with localhost)
    assert "gotify" in response.json()["detail"].lower()
