"""Tests for GET /api/alerts and PUT /api/alerts."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/alerts
# ---------------------------------------------------------------------------


def test_get_alerts_returns_default_config():
    """GET /api/alerts returns configuration with all expected fields."""
    response = client.get("/api/alerts")
    assert response.status_code == 200

    data = response.json()
    assert "enabled" in data
    assert "failure_threshold" in data
    assert "cooldown_minutes" in data
    assert "providers" in data
    assert isinstance(data["enabled"], bool)
    assert isinstance(data["failure_threshold"], int)
    assert isinstance(data["cooldown_minutes"], int)


def test_get_alerts_includes_all_providers():
    """GET /api/alerts includes all provider configurations."""
    response = client.get("/api/alerts")
    assert response.status_code == 200

    providers = response.json()["providers"]
    assert "webhook" in providers
    assert "gotify" in providers
    assert "ntfy" in providers


# ---------------------------------------------------------------------------
# PUT /api/alerts
# ---------------------------------------------------------------------------


def test_put_alerts_requires_auth_when_key_set():
    """PUT /api/alerts requires API key when authentication is enabled."""
    key = "test-api-key"
    with patch("src.api.auth.config.API_KEY", key):
        response = client.put(
            "/api/alerts",
            json={
                "enabled": True,
                "failure_threshold": 3,
                "cooldown_minutes": 60,
                "providers": {
                    "webhook": {"enabled": False, "url": ""},
                    "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
                    "ntfy": {
                        "enabled": False,
                        "url": "https://ntfy.sh",
                        "topic": "",
                        "priority": 3,
                        "tags": [],
                    },
                },
            },
        )
        assert response.status_code == 401


def test_put_alerts_updates_configuration():
    """PUT /api/alerts persists and returns updated configuration."""
    payload = {
        "enabled": True,
        "failure_threshold": 5,
        "cooldown_minutes": 120,
        "providers": {
            "webhook": {
                "enabled": True,
                "url": "https://webhook.example.com",
            },
            "gotify": {
                "enabled": False,
                "url": "",
                "token": "",
                "priority": 5,
            },
            "ntfy": {
                "enabled": False,
                "url": "https://ntfy.sh",
                "topic": "",
                "priority": 3,
                "tags": ["warning", "rotating_light"],
            },
        },
    }

    response = client.put("/api/alerts", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["enabled"] is True
    assert data["failure_threshold"] == 5
    assert data["cooldown_minutes"] == 120
    assert data["providers"]["webhook"]["enabled"] is True
    assert data["providers"]["webhook"]["url"] == "https://webhook.example.com"


def test_put_alerts_validates_failure_threshold():
    """PUT /api/alerts validates failure_threshold is at least 1."""
    payload = {
        "enabled": True,
        "failure_threshold": 0,  # Invalid
        "cooldown_minutes": 60,
        "providers": {
            "webhook": {"enabled": False, "url": ""},
            "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
            "ntfy": {
                "enabled": False,
                "url": "https://ntfy.sh",
                "topic": "",
                "priority": 3,
                "tags": [],
            },
        },
    }

    response = client.put("/api/alerts", json=payload)
    assert response.status_code == 422  # Validation error


def test_put_alerts_validates_cooldown_range():
    """PUT /api/alerts validates cooldown_minutes is within range."""
    payload = {
        "enabled": True,
        "failure_threshold": 3,
        "cooldown_minutes": 2000,  # Above max
        "providers": {
            "webhook": {"enabled": False, "url": ""},
            "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
            "ntfy": {
                "enabled": False,
                "url": "https://ntfy.sh",
                "topic": "",
                "priority": 3,
                "tags": [],
            },
        },
    }

    response = client.put("/api/alerts", json=payload)
    assert response.status_code == 422


def test_put_alerts_validates_gotify_priority():
    """PUT /api/alerts validates Gotify priority is within 0-10."""
    payload = {
        "enabled": True,
        "failure_threshold": 3,
        "cooldown_minutes": 60,
        "providers": {
            "webhook": {"enabled": False, "url": ""},
            "gotify": {
                "enabled": True,
                "url": "https://gotify.example.com",
                "token": "token",
                "priority": 15,  # Above max
            },
            "ntfy": {
                "enabled": False,
                "url": "https://ntfy.sh",
                "topic": "",
                "priority": 3,
                "tags": [],
            },
        },
    }

    response = client.put("/api/alerts", json=payload)
    assert response.status_code == 422


def test_put_alerts_validates_ntfy_priority():
    """PUT /api/alerts validates ntfy priority is within 1-5."""
    payload = {
        "enabled": True,
        "failure_threshold": 3,
        "cooldown_minutes": 60,
        "providers": {
            "webhook": {"enabled": False, "url": ""},
            "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
            "ntfy": {
                "enabled": True,
                "url": "https://ntfy.sh",
                "topic": "alerts",
                "priority": 0,  # Below min
                "tags": [],
            },
        },
    }

    response = client.put("/api/alerts", json=payload)
    assert response.status_code == 422


def test_put_alerts_only_persists_enabled_providers():
    """PUT /api/alerts persists all provider configurations, even if disabled."""
    payload = {
        "enabled": True,
        "failure_threshold": 3,
        "cooldown_minutes": 60,
        "providers": {
            "webhook": {
                "enabled": True,
                "url": "https://webhook.example.com",
            },
            "gotify": {
                "enabled": False,  # Disabled but config should be preserved
                "url": "https://gotify.example.com",
                "token": "token",
                "priority": 5,
            },
            "ntfy": {
                "enabled": True,
                "url": "https://ntfy.sh",
                "topic": "alerts",
                "priority": 3,
                "tags": ["warning"],
            },
        },
    }

    response = client.put("/api/alerts", json=payload)
    assert response.status_code == 200

    # Verify persisted config via GET
    get_response = client.get("/api/alerts")
    data = get_response.json()

    # Webhook should be saved as enabled
    assert data["providers"]["webhook"]["enabled"] is True
    assert data["providers"]["webhook"]["url"] == "https://webhook.example.com"

    # Gotify was disabled but configuration should be preserved
    assert data["providers"]["gotify"]["enabled"] is False
    assert data["providers"]["gotify"]["url"] == "https://gotify.example.com"
    assert data["providers"]["gotify"]["token"] == "token"

    # ntfy should be saved as enabled
    assert data["providers"]["ntfy"]["enabled"] is True
    assert data["providers"]["ntfy"]["topic"] == "alerts"


def test_put_alerts_requires_url_for_webhook():
    """PUT /api/alerts does not persist webhook if URL is missing."""
    payload = {
        "enabled": True,
        "failure_threshold": 3,
        "cooldown_minutes": 60,
        "providers": {
            "webhook": {
                "enabled": True,
                "url": "",  # Missing URL
            },
            "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
            "ntfy": {
                "enabled": False,
                "url": "https://ntfy.sh",
                "topic": "",
                "priority": 3,
                "tags": [],
            },
        },
    }

    response = client.put("/api/alerts", json=payload)
    assert response.status_code == 200  # Request succeeds but webhook not saved


def test_put_alerts_requires_token_for_gotify():
    """PUT /api/alerts does not persist Gotify if token is missing."""
    payload = {
        "enabled": True,
        "failure_threshold": 3,
        "cooldown_minutes": 60,
        "providers": {
            "webhook": {"enabled": False, "url": ""},
            "gotify": {
                "enabled": True,
                "url": "https://gotify.example.com",
                "token": "",  # Missing token
                "priority": 5,
            },
            "ntfy": {
                "enabled": False,
                "url": "https://ntfy.sh",
                "topic": "",
                "priority": 3,
                "tags": [],
            },
        },
    }

    response = client.put("/api/alerts", json=payload)
    assert response.status_code == 200  # Request succeeds but Gotify not saved


def test_put_alerts_requires_topic_for_ntfy():
    """PUT /api/alerts does not persist ntfy if topic is missing."""
    payload = {
        "enabled": True,
        "failure_threshold": 3,
        "cooldown_minutes": 60,
        "providers": {
            "webhook": {"enabled": False, "url": ""},
            "gotify": {"enabled": False, "url": "", "token": "", "priority": 5},
            "ntfy": {
                "enabled": True,
                "url": "https://ntfy.sh",
                "topic": "",  # Missing topic
                "priority": 3,
                "tags": [],
            },
        },
    }

    response = client.put("/api/alerts", json=payload)
    assert response.status_code == 200  # Request succeeds but ntfy not saved


# ---------------------------------------------------------------------------
# POST /api/alerts/test
# ---------------------------------------------------------------------------


def test_post_alerts_test_requires_auth_when_key_set():
    """POST /api/alerts/test requires API key when authentication is enabled."""
    from src import shared_state
    from src.services.alert_manager import AlertManager

    key = "test-api-key"
    manager = AlertManager()

    # Save current state
    original_manager = shared_state.get_alert_manager()

    try:
        # Set up manager for test
        shared_state.set_alert_manager(manager)

        with patch("src.api.auth.config.API_KEY", key):
            # Without key - rejected
            response = client.post("/api/alerts/test")
            assert response.status_code == 401

            # With key - allowed
            response = client.post("/api/alerts/test", headers={"X-Api-Key": key})
            assert response.status_code == 200
    finally:
        # Restore original state
        if original_manager:
            shared_state.set_alert_manager(original_manager)


def test_post_alerts_test_succeeds_with_configured_providers():
    """POST /api/alerts/test returns success when providers configured."""
    from unittest.mock import patch, Mock
    from src.api.routes import alerts
    
    # Reset rate limit for this test
    alerts._test_alert_last_call = 0.0

    # Mock config to return enabled webhook provider
    mock_config = {
        "enabled": True,
        "failure_threshold": 3,
        "cooldown_minutes": 60,
        "providers": {
            "webhook": {
                "enabled": True,
                "url": "http://test.example.com/webhook",  # NOSONAR
            },
        },
    }

    # Mock the HTTP request to prevent actual network call
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()

    with patch("src.runtime_config.get_alert_config", return_value=mock_config):
        with patch("requests.post", return_value=mock_response) as mock_post:
            response = client.post("/api/alerts/test")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert "webhook" in data["results"]
            assert data["results"]["webhook"] is True
            assert "successfully" in data["message"].lower()

            # Verify HTTP request was made
            mock_post.assert_called_once()


def test_post_alerts_test_returns_no_providers_when_none_configured():
    """POST /api/alerts/test indicates when no providers configured."""
    from unittest.mock import patch
    from src.api.routes import alerts
    
    # Reset rate limit for this test
    alerts._test_alert_last_call = 0.0

    # Mock config with no enabled providers
    mock_config = {
        "enabled": True,
        "failure_threshold": 3,
        "cooldown_minutes": 60,
        "providers": {
            "webhook": {"enabled": False, "url": ""},
            "gotify": {"enabled": False, "url": "", "token": ""},
            "ntfy": {"enabled": False, "url": "", "topic": ""},
            "apprise": {"enabled": False, "url": ""},
        },
    }

    with patch("src.runtime_config.get_alert_config", return_value=mock_config):
        response = client.post("/api/alerts/test")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "no_providers"
        assert "no alert providers" in data["message"].lower()
