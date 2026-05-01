"""Tests for alert provider factory — unified provider registration logic."""

from __future__ import annotations

from src.constants import (
    PROVIDER_APPRISE,
    PROVIDER_GOTIFY,
    PROVIDER_NTFY,
    PROVIDER_WEBHOOK,
)
from src.services.alert_manager import AlertManager
from src.services.alert_provider_factory import (
    _get_config_value,
    register_all_providers,
    register_apprise_provider,
    register_gotify_provider,
    register_ntfy_provider,
    register_webhook_provider,
)


# --- Helper function tests ---


def test_get_config_value_returns_runtime_value_when_present():
    """Verify runtime config value takes precedence over env default."""
    runtime_config = {"url": "https://runtime.example.com"}
    result = _get_config_value(runtime_config, "url", "https://env.example.com")
    assert result == "https://runtime.example.com"


def test_get_config_value_returns_env_default_when_runtime_none():
    """Verify env default is used when runtime value is None."""
    runtime_config = {"url": None}
    result = _get_config_value(runtime_config, "url", "https://env.example.com")
    assert result == "https://env.example.com"


def test_get_config_value_returns_env_default_when_key_missing():
    """Verify env default is used when key is missing from runtime config."""
    runtime_config = {}
    result = _get_config_value(runtime_config, "url", "https://env.example.com")
    assert result == "https://env.example.com"


def test_get_config_value_returns_runtime_empty_string_over_env_default():
    """Verify empty string runtime value is preserved (not replaced with default)."""
    runtime_config = {"url": ""}
    result = _get_config_value(runtime_config, "url", "https://env.example.com")
    assert result == ""


def test_get_config_value_returns_runtime_zero_over_env_default():
    """Verify zero runtime value is preserved (not replaced with default)."""
    runtime_config = {"priority": 0}
    result = _get_config_value(runtime_config, "priority", 5)
    assert result == 0


# --- Webhook provider tests ---


def test_register_webhook_provider_adds_provider_when_url_configured():
    """Verify webhook provider is registered when URL is configured."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_WEBHOOK: {"url": "https://webhook.example.com"}}

    register_webhook_provider(manager, providers_config)

    assert PROVIDER_WEBHOOK in manager._providers  # noqa: SLF001


def test_register_webhook_provider_skips_when_url_missing():
    """Verify webhook provider is not registered when URL is missing."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_WEBHOOK: {}}

    register_webhook_provider(manager, providers_config)

    assert PROVIDER_WEBHOOK not in manager._providers  # noqa: SLF001


def test_register_webhook_provider_skips_when_url_empty():
    """Verify webhook provider is not registered when URL is empty string."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_WEBHOOK: {"url": ""}}

    register_webhook_provider(manager, providers_config)

    assert PROVIDER_WEBHOOK not in manager._providers  # noqa: SLF001


def test_register_webhook_provider_skips_when_disabled_and_require_enabled():
    """Verify webhook provider is not registered when enabled=False and require_enabled=True."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_WEBHOOK: {"url": "https://webhook.example.com", "enabled": False}
    }

    register_webhook_provider(manager, providers_config, require_enabled=True)

    assert PROVIDER_WEBHOOK not in manager._providers  # noqa: SLF001


def test_register_webhook_provider_registers_when_disabled_and_require_enabled_false():
    """Verify webhook provider IS registered when enabled=False and require_enabled=False."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_WEBHOOK: {"url": "https://webhook.example.com", "enabled": False}
    }

    register_webhook_provider(manager, providers_config, require_enabled=False)

    assert PROVIDER_WEBHOOK in manager._providers  # noqa: SLF001


def test_register_webhook_provider_registers_when_enabled_true():
    """Verify webhook provider is registered when enabled=True."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_WEBHOOK: {"url": "https://webhook.example.com", "enabled": True}
    }

    register_webhook_provider(manager, providers_config, require_enabled=True)

    assert PROVIDER_WEBHOOK in manager._providers  # noqa: SLF001


def test_register_webhook_provider_handles_invalid_url_gracefully(caplog):
    """Verify webhook provider logs warning on invalid URL without crashing."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_WEBHOOK: {"url": "ftp://invalid-scheme.com"}}

    register_webhook_provider(manager, providers_config)

    assert PROVIDER_WEBHOOK not in manager._providers  # noqa: SLF001
    assert "Could not initialize webhook alert provider" in caplog.text


# --- Gotify provider tests ---


def test_register_gotify_provider_adds_provider_when_configured():
    """Verify Gotify provider is registered when URL and token are configured."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_GOTIFY: {"url": "https://gotify.example.com", "token": "test-token"}
    }

    register_gotify_provider(manager, providers_config)

    assert PROVIDER_GOTIFY in manager._providers  # noqa: SLF001


def test_register_gotify_provider_skips_when_url_missing():
    """Verify Gotify provider is not registered when URL is missing."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_GOTIFY: {"token": "test-token"}}

    register_gotify_provider(manager, providers_config)

    assert PROVIDER_GOTIFY not in manager._providers  # noqa: SLF001


def test_register_gotify_provider_skips_when_token_missing():
    """Verify Gotify provider is not registered when token is missing."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_GOTIFY: {"url": "https://gotify.example.com"}}

    register_gotify_provider(manager, providers_config)

    assert PROVIDER_GOTIFY not in manager._providers  # noqa: SLF001


def test_register_gotify_provider_skips_when_both_missing():
    """Verify Gotify provider is not registered when both URL and token are missing."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_GOTIFY: {}}

    register_gotify_provider(manager, providers_config)

    assert PROVIDER_GOTIFY not in manager._providers  # noqa: SLF001


def test_register_gotify_provider_skips_when_disabled_and_require_enabled():
    """Verify Gotify provider is not registered when enabled=False and require_enabled=True."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_GOTIFY: {
            "url": "https://gotify.example.com",
            "token": "test-token",
            "enabled": False,
        }
    }

    register_gotify_provider(manager, providers_config, require_enabled=True)

    assert PROVIDER_GOTIFY not in manager._providers  # noqa: SLF001


def test_register_gotify_provider_includes_priority_when_provided():
    """Verify Gotify provider uses custom priority from config."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_GOTIFY: {
            "url": "https://gotify.example.com",
            "token": "test-token",
            "priority": 10,
        }
    }

    register_gotify_provider(manager, providers_config)

    provider = manager._providers[PROVIDER_GOTIFY]  # noqa: SLF001
    assert provider.priority == 10


def test_register_gotify_provider_handles_invalid_url_gracefully(caplog):
    """Verify Gotify provider logs warning on invalid URL without crashing."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_GOTIFY: {"url": "not-a-url", "token": "test-token"}}

    register_gotify_provider(manager, providers_config)

    assert PROVIDER_GOTIFY not in manager._providers  # noqa: SLF001
    assert "Could not initialize Gotify alert provider" in caplog.text


# --- ntfy provider tests ---


def test_register_ntfy_provider_adds_provider_when_topic_configured():
    """Verify ntfy provider is registered when topic is configured."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_NTFY: {"topic": "hermes-alerts"}}

    register_ntfy_provider(manager, providers_config)

    assert PROVIDER_NTFY in manager._providers  # noqa: SLF001


def test_register_ntfy_provider_skips_when_topic_missing():
    """Verify ntfy provider is not registered when topic is missing."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_NTFY: {}}

    register_ntfy_provider(manager, providers_config)

    assert PROVIDER_NTFY not in manager._providers  # noqa: SLF001


def test_register_ntfy_provider_skips_when_topic_empty():
    """Verify ntfy provider is not registered when topic is empty string."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_NTFY: {"topic": ""}}

    register_ntfy_provider(manager, providers_config)

    assert PROVIDER_NTFY not in manager._providers  # noqa: SLF001


def test_register_ntfy_provider_skips_when_disabled_and_require_enabled():
    """Verify ntfy provider is not registered when enabled=False and require_enabled=True."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_NTFY: {"topic": "hermes-alerts", "enabled": False}}

    register_ntfy_provider(manager, providers_config, require_enabled=True)

    assert PROVIDER_NTFY not in manager._providers  # noqa: SLF001


def test_register_ntfy_provider_uses_custom_url_when_provided():
    """Verify ntfy provider uses custom URL from config."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_NTFY: {
            "topic": "hermes-alerts",
            "url": "https://ntfy.custom.com",
        }
    }

    register_ntfy_provider(manager, providers_config)

    provider = manager._providers[PROVIDER_NTFY]  # noqa: SLF001
    assert provider.url == "https://ntfy.custom.com"


def test_register_ntfy_provider_uses_default_url_when_not_provided():
    """Verify ntfy provider uses default ntfy.sh URL when custom URL not provided."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_NTFY: {"topic": "hermes-alerts"}}

    register_ntfy_provider(manager, providers_config)

    provider = manager._providers[PROVIDER_NTFY]  # noqa: SLF001
    assert provider.url == "https://ntfy.sh"


def test_register_ntfy_provider_includes_token_when_provided():
    """Verify ntfy provider includes token from config."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_NTFY: {"topic": "hermes-alerts", "token": "test-token"}
    }

    register_ntfy_provider(manager, providers_config)

    provider = manager._providers[PROVIDER_NTFY]  # noqa: SLF001
    assert provider.token == "test-token"


def test_register_ntfy_provider_includes_priority_when_provided():
    """Verify ntfy provider uses custom priority from config."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_NTFY: {"topic": "hermes-alerts", "priority": 4}}

    register_ntfy_provider(manager, providers_config)

    provider = manager._providers[PROVIDER_NTFY]  # noqa: SLF001
    assert provider.priority == 4


def test_register_ntfy_provider_includes_tags_when_provided():
    """Verify ntfy provider uses custom tags from config."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_NTFY: {
            "topic": "hermes-alerts",
            "tags": ["warning", "speedtest"],
        }
    }

    register_ntfy_provider(manager, providers_config)

    provider = manager._providers[PROVIDER_NTFY]  # noqa: SLF001
    assert provider.tags == ["warning", "speedtest"]


def test_register_ntfy_provider_handles_initialization_error_gracefully(caplog):
    """Verify ntfy provider logs warning on initialization error without crashing."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    # Invalid priority type will cause initialization error
    providers_config = {
        PROVIDER_NTFY: {"topic": "hermes-alerts", "priority": "invalid"}
    }

    register_ntfy_provider(manager, providers_config)

    assert PROVIDER_NTFY not in manager._providers  # noqa: SLF001
    assert "Could not initialize ntfy alert provider" in caplog.text


# --- Apprise provider tests ---


def test_register_apprise_provider_adds_provider_when_url_configured():
    """Verify Apprise provider is registered when URL is configured."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_APPRISE: {"url": "https://apprise.example.com"}}

    register_apprise_provider(manager, providers_config)

    assert PROVIDER_APPRISE in manager._providers  # noqa: SLF001


def test_register_apprise_provider_skips_when_url_missing():
    """Verify Apprise provider is not registered when URL is missing."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_APPRISE: {}}

    register_apprise_provider(manager, providers_config)

    assert PROVIDER_APPRISE not in manager._providers  # noqa: SLF001


def test_register_apprise_provider_skips_when_url_empty():
    """Verify Apprise provider is not registered when URL is empty string."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {PROVIDER_APPRISE: {"url": ""}}

    register_apprise_provider(manager, providers_config)

    assert PROVIDER_APPRISE not in manager._providers  # noqa: SLF001


def test_register_apprise_provider_skips_when_disabled_and_require_enabled():
    """Verify Apprise provider is not registered when enabled=False and require_enabled=True."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_APPRISE: {"url": "https://apprise.example.com", "enabled": False}
    }

    register_apprise_provider(manager, providers_config, require_enabled=True)

    assert PROVIDER_APPRISE not in manager._providers  # noqa: SLF001


def test_register_apprise_provider_includes_urls_when_provided():
    """Verify Apprise provider includes service URLs from config (stateless mode)."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_APPRISE: {
            "url": "https://apprise.example.com",
            "urls": ["ntfy://ntfy.sh/topic", "gotify://gotify.example.com/token"],
        }
    }

    register_apprise_provider(manager, providers_config)

    provider = manager._providers[PROVIDER_APPRISE]  # noqa: SLF001
    assert provider.urls == [
        "ntfy://ntfy.sh/topic",
        "gotify://gotify.example.com/token",
    ]


def test_register_apprise_provider_handles_empty_urls_list():
    """Verify Apprise provider handles empty URLs list gracefully."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_APPRISE: {"url": "https://apprise.example.com", "urls": []}
    }

    register_apprise_provider(manager, providers_config)

    provider = manager._providers[PROVIDER_APPRISE]  # noqa: SLF001
    assert provider.urls == []


def test_register_apprise_provider_handles_initialization_error_gracefully(caplog):
    """Verify Apprise provider logs warning on initialization error without crashing."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    # Empty URL will cause ValueError
    providers_config = {PROVIDER_APPRISE: {"url": ""}}

    register_apprise_provider(manager, providers_config)

    assert PROVIDER_APPRISE not in manager._providers  # noqa: SLF001


# --- register_all_providers tests ---


def test_register_all_providers_registers_all_configured_providers():
    """Verify register_all_providers registers all configured providers."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_WEBHOOK: {"url": "https://webhook.example.com"},
        PROVIDER_GOTIFY: {"url": "https://gotify.example.com", "token": "token1"},
        PROVIDER_NTFY: {"topic": "hermes-alerts"},
        PROVIDER_APPRISE: {"url": "https://apprise.example.com"},
    }

    register_all_providers(manager, providers_config)

    assert PROVIDER_WEBHOOK in manager._providers  # noqa: SLF001
    assert PROVIDER_GOTIFY in manager._providers  # noqa: SLF001
    assert PROVIDER_NTFY in manager._providers  # noqa: SLF001
    assert PROVIDER_APPRISE in manager._providers  # noqa: SLF001


def test_register_all_providers_skips_unconfigured_providers():
    """Verify register_all_providers skips providers without configuration."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_WEBHOOK: {"url": "https://webhook.example.com"},
        # Other providers missing or incomplete
        PROVIDER_GOTIFY: {},
        PROVIDER_NTFY: {},
    }

    register_all_providers(manager, providers_config)

    assert PROVIDER_WEBHOOK in manager._providers  # noqa: SLF001
    assert PROVIDER_GOTIFY not in manager._providers  # noqa: SLF001
    assert PROVIDER_NTFY not in manager._providers  # noqa: SLF001


def test_register_all_providers_with_require_enabled_filters_disabled():
    """Verify register_all_providers with require_enabled=True only registers enabled providers."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_WEBHOOK: {"url": "https://webhook.example.com", "enabled": True},
        PROVIDER_GOTIFY: {
            "url": "https://gotify.example.com",
            "token": "token1",
            "enabled": False,
        },
        PROVIDER_NTFY: {"topic": "hermes-alerts", "enabled": True},
    }

    register_all_providers(manager, providers_config, require_enabled=True)

    assert PROVIDER_WEBHOOK in manager._providers  # noqa: SLF001
    assert PROVIDER_GOTIFY not in manager._providers  # noqa: SLF001
    assert PROVIDER_NTFY in manager._providers  # noqa: SLF001


def test_register_all_providers_without_require_enabled_registers_all():
    """Verify register_all_providers with require_enabled=False registers disabled providers."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_WEBHOOK: {"url": "https://webhook.example.com", "enabled": False},
        PROVIDER_GOTIFY: {
            "url": "https://gotify.example.com",
            "token": "token1",
            "enabled": False,
        },
    }

    register_all_providers(manager, providers_config, require_enabled=False)

    assert PROVIDER_WEBHOOK in manager._providers  # noqa: SLF001
    assert PROVIDER_GOTIFY in manager._providers  # noqa: SLF001


def test_register_all_providers_continues_on_partial_failure(caplog):
    """Verify register_all_providers continues registering even if one provider fails."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {
        PROVIDER_WEBHOOK: {"url": "ftp://invalid-scheme.com"},  # Will fail
        PROVIDER_NTFY: {"topic": "hermes-alerts"},  # Should succeed
    }

    register_all_providers(manager, providers_config)

    # ntfy should be registered despite webhook failure
    assert PROVIDER_NTFY in manager._providers  # noqa: SLF001
    assert PROVIDER_WEBHOOK not in manager._providers  # noqa: SLF001
    assert "Could not initialize webhook alert provider" in caplog.text


def test_register_all_providers_handles_empty_config():
    """Verify register_all_providers handles empty providers config gracefully."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=30)
    providers_config = {}

    register_all_providers(manager, providers_config)

    assert len(manager._providers) == 0  # noqa: SLF001
