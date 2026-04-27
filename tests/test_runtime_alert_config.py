"""Tests for alert configuration loading from env vars and runtime config."""

import json
from unittest.mock import patch

import pytest

from src import runtime_config


@pytest.fixture
def clean_runtime_config(tmp_path, monkeypatch):
    """Ensure runtime config doesn't exist for these tests."""
    config_path = tmp_path / "runtime_config.json"
    monkeypatch.setattr(runtime_config, "RUNTIME_CONFIG_PATH", config_path)
    return config_path


def test_get_alert_config_loads_from_env_vars(clean_runtime_config):
    """get_alert_config loads from env vars when no runtime config exists."""
    with (
        patch("src.config.ALERT_FAILURE_THRESHOLD", 5),
        patch("src.config.ALERT_COOLDOWN_MINUTES", 120),
        patch("src.config.ALERT_WEBHOOK_URL", "https://webhook.example.com"),
        patch("src.config.ALERT_GOTIFY_URL", "https://gotify.example.com"),
        patch("src.config.ALERT_GOTIFY_TOKEN", "gotify_token"),
        patch("src.config.ALERT_GOTIFY_PRIORITY", 7),
        patch("src.config.ALERT_NTFY_URL", "https://ntfy.sh"),
        patch("src.config.ALERT_NTFY_TOPIC", "alerts"),
        patch("src.config.ALERT_NTFY_TOKEN", "ntfy_token"),
        patch("src.config.ALERT_NTFY_PRIORITY", 4),
        patch("src.config.ALERT_NTFY_TAGS", ["warning", "alert"]),
        patch(
            "src.config.ALERT_APPRISE_URL",
            "http://apprise:8000",  # NOSONAR
        ),
    ):
        config = runtime_config.get_alert_config()

        assert config["enabled"] is True
        assert config["failure_threshold"] == 5
        assert config["cooldown_minutes"] == 120

        # Verify all providers loaded
        assert config["providers"]["webhook"]["enabled"] is True
        assert config["providers"]["webhook"]["url"] == "https://webhook.example.com"

        assert config["providers"]["gotify"]["enabled"] is True
        assert config["providers"]["gotify"]["url"] == "https://gotify.example.com"
        assert config["providers"]["gotify"]["token"] == "gotify_token"
        assert config["providers"]["gotify"]["priority"] == 7

        assert config["providers"]["ntfy"]["enabled"] is True
        assert config["providers"]["ntfy"]["url"] == "https://ntfy.sh"
        assert config["providers"]["ntfy"]["topic"] == "alerts"
        assert config["providers"]["ntfy"]["token"] == "ntfy_token"
        assert config["providers"]["ntfy"]["priority"] == 4
        assert config["providers"]["ntfy"]["tags"] == ["warning", "alert"]

        assert config["providers"]["apprise"]["enabled"] is True
        assert config["providers"]["apprise"]["url"] == "http://apprise:8000"  # NOSONAR


def test_get_alert_config_prefers_runtime_config_over_env(clean_runtime_config):
    """get_alert_config prefers saved runtime config over env vars."""
    # Write runtime config
    clean_runtime_config.parent.mkdir(parents=True, exist_ok=True)
    with open(clean_runtime_config, "w", encoding="utf-8") as f:
        json.dump(
            {
                "alert_config": {
                    "enabled": False,
                    "failure_threshold": 10,
                    "cooldown_minutes": 30,
                    "providers": {
                        "webhook": {
                            "enabled": True,
                            "url": "https://custom-webhook.example.com",
                        }
                    },
                }
            },
            f,
        )

    with (
        patch("src.config.ALERT_FAILURE_THRESHOLD", 5),
        patch("src.config.ALERT_COOLDOWN_MINUTES", 120),
        patch("src.config.ALERT_WEBHOOK_URL", "https://env-webhook.example.com"),
    ):
        config = runtime_config.get_alert_config()

        # Should use runtime config, not env vars
        assert config["enabled"] is False
        assert config["failure_threshold"] == 10
        assert config["cooldown_minutes"] == 30
        assert (
            config["providers"]["webhook"]["url"]
            == "https://custom-webhook.example.com"
        )


def test_get_alert_config_returns_defaults_when_no_config(clean_runtime_config):
    """get_alert_config returns defaults when no env vars or runtime config."""
    with (
        patch("src.config.ALERT_FAILURE_THRESHOLD", 0),
        patch("src.config.ALERT_COOLDOWN_MINUTES", 60),
        patch("src.config.ALERT_WEBHOOK_URL", None),
        patch("src.config.ALERT_GOTIFY_URL", None),
        patch("src.config.ALERT_GOTIFY_TOKEN", None),
        patch("src.config.ALERT_NTFY_URL", None),
        patch("src.config.ALERT_NTFY_TOPIC", None),
        patch("src.config.ALERT_APPRISE_URL", None),
    ):
        config = runtime_config.get_alert_config()

        assert config["enabled"] is False
        assert config["failure_threshold"] == 3
        assert config["cooldown_minutes"] == 60
        assert config["providers"] == {}
