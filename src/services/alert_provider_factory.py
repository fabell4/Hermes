"""Alert provider factory — unified provider registration logic.

This module contains shared logic for registering alert providers used by both
the main scheduler process and the API process. Eliminates code duplication.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src import config as app_config
from src.constants import (
    PROVIDER_APPRISE,
    PROVIDER_GOTIFY,
    PROVIDER_NTFY,
    PROVIDER_WEBHOOK,
)
from src.services.alert_providers import (
    AppriseProvider,
    GotifyProvider,
    NtfyProvider,
    WebhookProvider,
)

if TYPE_CHECKING:
    from src.services.alert_manager import AlertManager

logger = logging.getLogger(__name__)


def _get_config_value(runtime_config: dict, key: str, env_default: Any) -> Any:
    """Get config value from runtime config with fallback to environment default.

    Args:
        runtime_config: Runtime configuration dictionary (e.g., webhook_config)
        key: Key to look up in runtime config (e.g., "url")
        env_default: Environment variable default to use if runtime value is None/missing

    Returns:
        Runtime value if present and not None, otherwise env_default
    """
    value = runtime_config.get(key)
    return value if value is not None else env_default


def register_webhook_provider(
    manager: AlertManager,
    providers_config: dict,
    require_enabled: bool = False,
) -> None:
    """Register webhook alert provider if configured.

    Args:
        manager: AlertManager instance to register provider with
        providers_config: Provider configuration dictionary
        require_enabled: If True, only register if enabled=True in config
    """
    webhook_config = providers_config.get(PROVIDER_WEBHOOK, {})
    webhook_url = _get_config_value(webhook_config, "url", app_config.ALERT_WEBHOOK_URL)

    if not webhook_url:
        return

    if require_enabled and not webhook_config.get("enabled", False):
        return

    try:
        manager.add_provider(PROVIDER_WEBHOOK, WebhookProvider(url=webhook_url))
    except Exception as e:  # pylint: disable=broad-except  # NOSONAR
        logger.warning("Could not initialize webhook alert provider: %s", e)


def register_gotify_provider(
    manager: AlertManager,
    providers_config: dict,
    require_enabled: bool = False,
) -> None:
    """Register Gotify alert provider if configured.

    Args:
        manager: AlertManager instance to register provider with
        providers_config: Provider configuration dictionary
        require_enabled: If True, only register if enabled=True in config
    """
    gotify_config = providers_config.get(PROVIDER_GOTIFY, {})
    gotify_url = _get_config_value(gotify_config, "url", app_config.ALERT_GOTIFY_URL)
    gotify_token = _get_config_value(
        gotify_config, "token", app_config.ALERT_GOTIFY_TOKEN
    )

    if not (gotify_url and gotify_token):
        return

    if require_enabled and not gotify_config.get("enabled", False):
        return

    try:
        manager.add_provider(
            PROVIDER_GOTIFY,
            GotifyProvider(
                url=gotify_url,
                token=gotify_token,
                priority=gotify_config.get(
                    "priority", app_config.ALERT_GOTIFY_PRIORITY
                ),
            ),
        )
    except Exception as e:  # pylint: disable=broad-except  # NOSONAR
        logger.warning("Could not initialize Gotify alert provider: %s", e)


def register_ntfy_provider(
    manager: AlertManager,
    providers_config: dict,
    require_enabled: bool = False,
) -> None:
    """Register ntfy alert provider if configured.

    Args:
        manager: AlertManager instance to register provider with
        providers_config: Provider configuration dictionary
        require_enabled: If True, only register if enabled=True in config
    """
    ntfy_config = providers_config.get(PROVIDER_NTFY, {})
    ntfy_topic = _get_config_value(ntfy_config, "topic", app_config.ALERT_NTFY_TOPIC)

    if not ntfy_topic:
        return

    if require_enabled and not ntfy_config.get("enabled", False):
        return

    try:
        manager.add_provider(
            PROVIDER_NTFY,
            NtfyProvider(
                url=_get_config_value(
                    ntfy_config, "url", app_config.ALERT_NTFY_URL or "https://ntfy.sh"
                ),
                topic=ntfy_topic,
                token=_get_config_value(
                    ntfy_config, "token", app_config.ALERT_NTFY_TOKEN
                ),
                priority=_get_config_value(
                    ntfy_config, "priority", app_config.ALERT_NTFY_PRIORITY
                ),
                tags=_get_config_value(ntfy_config, "tags", app_config.ALERT_NTFY_TAGS),
            ),
        )
    except Exception as e:  # pylint: disable=broad-except  # NOSONAR
        logger.warning("Could not initialize ntfy alert provider: %s", e)


def register_apprise_provider(
    manager: AlertManager,
    providers_config: dict,
    require_enabled: bool = False,
) -> None:
    """Register Apprise alert provider if configured.

    Args:
        manager: AlertManager instance to register provider with
        providers_config: Provider configuration dictionary
        require_enabled: If True, only register if enabled=True in config
    """
    apprise_config = providers_config.get(PROVIDER_APPRISE, {})
    apprise_url = _get_config_value(apprise_config, "url", app_config.ALERT_APPRISE_URL)
    apprise_urls = apprise_config.get("urls", [])

    if not apprise_url:
        return

    if require_enabled and not apprise_config.get("enabled", False):
        return

    try:
        manager.add_provider(
            PROVIDER_APPRISE,
            AppriseProvider(
                url=apprise_url,
                urls=apprise_urls if apprise_urls else None,
            ),
        )
    except Exception as e:  # pylint: disable=broad-except  # NOSONAR
        logger.warning("Could not initialize Apprise alert provider: %s", e)


def register_all_providers(
    manager: AlertManager,
    providers_config: dict,
    require_enabled: bool = False,
) -> None:
    """
    Register all configured alert providers with the AlertManager.

    Iterates through all supported provider types (webhook, Gotify, ntfy, Apprise)
    and registers them with the AlertManager if they are properly configured.

    Args:
        manager: AlertManager instance to register providers with.
        providers_config: Dictionary containing provider configurations.
            Expected structure:
            {
                "webhook": {"url": "...", "enabled": bool},
                "gotify": {"url": "...", "token": "...", "enabled": bool},
                "ntfy": {"topic": "...", "enabled": bool},
                "apprise": {"url": "...", "enabled": bool}
            }
        require_enabled: If True, only register providers where enabled=True.
            If False (default), register all providers with valid configuration
            regardless of enabled status. This is used by the API for test
            notifications where only enabled providers should be tested.

    Note:
        Registration failures for individual providers are logged but do not
        stop registration of other providers. Invalid configurations (missing
        URLs, tokens, etc.) are silently skipped with a warning log.
    """
    register_webhook_provider(manager, providers_config, require_enabled)
    register_gotify_provider(manager, providers_config, require_enabled)
    register_ntfy_provider(manager, providers_config, require_enabled)
    register_apprise_provider(manager, providers_config, require_enabled)
