"""GET /api/alerts and PUT /api/alerts — alert configuration."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src import runtime_config
from src.api.auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(tags=["alerts"])

# Test alert status constants
TEST_ALERT_STATUS_SUCCESS = "success"
TEST_ALERT_STATUS_FAILED = "failed"
TEST_ALERT_STATUS_PARTIAL = "partial"
TEST_ALERT_STATUS_NO_PROVIDERS = "no_providers"


class WebhookProviderConfig(BaseModel):
    """Webhook alert provider configuration."""

    enabled: bool = False
    url: str = ""


class GotifyProviderConfig(BaseModel):
    """Gotify alert provider configuration."""

    enabled: bool = False
    url: str = ""
    token: str = ""
    priority: int = Field(default=5, ge=0, le=10)


class NtfyProviderConfig(BaseModel):
    """ntfy alert provider configuration."""

    enabled: bool = False
    url: str = "https://ntfy.sh"
    topic: str = ""
    token: str = ""
    priority: int = Field(default=3, ge=1, le=5)
    tags: list[str] = Field(default_factory=lambda: ["warning", "rotating_light"])


class AppriseProviderConfig(BaseModel):
    """Apprise alert provider configuration (API service endpoint)."""

    enabled: bool = False
    url: str = ""
    urls: list[
        str
    ] = []  # Service URLs for stateless mode (e.g., ['ntfy://...', 'gotify://...'])


class AlertProvidersConfig(BaseModel):
    """Alert providers configuration."""

    webhook: WebhookProviderConfig = Field(default_factory=WebhookProviderConfig)
    gotify: GotifyProviderConfig = Field(default_factory=GotifyProviderConfig)
    ntfy: NtfyProviderConfig = Field(default_factory=NtfyProviderConfig)
    apprise: AppriseProviderConfig = Field(default_factory=AppriseProviderConfig)


class AlertConfigSchema(BaseModel):
    """Request/response schema for alert configuration endpoints."""

    enabled: bool = False
    failure_threshold: int = Field(default=3, ge=1, le=100)
    cooldown_minutes: int = Field(default=60, ge=0, le=1440)
    providers: AlertProvidersConfig = Field(default_factory=AlertProvidersConfig)


def _build_webhook_config(providers_data: dict) -> WebhookProviderConfig:
    """Build webhook provider config with env var fallback."""
    from src import config as app_config

    webhook_data = providers_data.get("webhook", {})
    return WebhookProviderConfig(
        enabled=webhook_data.get("enabled", False),
        url=webhook_data.get("url", "") or (app_config.ALERT_WEBHOOK_URL or ""),
    )


def _build_gotify_config(providers_data: dict) -> GotifyProviderConfig:
    """Build Gotify provider config with env var fallback."""
    from src import config as app_config

    gotify_data = providers_data.get("gotify", {})
    return GotifyProviderConfig(
        enabled=gotify_data.get("enabled", False),
        url=gotify_data.get("url", "") or (app_config.ALERT_GOTIFY_URL or ""),
        token=gotify_data.get("token", "") or (app_config.ALERT_GOTIFY_TOKEN or ""),
        priority=gotify_data.get("priority", 5) or app_config.ALERT_GOTIFY_PRIORITY,
    )


def _build_ntfy_config(providers_data: dict) -> NtfyProviderConfig:
    """Build ntfy provider config with env var fallback."""
    from src import config as app_config

    ntfy_data = providers_data.get("ntfy", {})
    return NtfyProviderConfig(
        enabled=ntfy_data.get("enabled", False),
        url=ntfy_data.get("url", "")
        or (app_config.ALERT_NTFY_URL or "https://ntfy.sh"),
        topic=ntfy_data.get("topic", "") or (app_config.ALERT_NTFY_TOPIC or ""),
        token=ntfy_data.get("token", "") or (app_config.ALERT_NTFY_TOKEN or ""),
        priority=ntfy_data.get("priority", 3) or app_config.ALERT_NTFY_PRIORITY,
        tags=ntfy_data.get("tags", []) or app_config.ALERT_NTFY_TAGS,
    )


def _build_apprise_config(providers_data: dict) -> AppriseProviderConfig:
    """Build Apprise provider config with env var fallback."""
    from src import config as app_config

    apprise_data = providers_data.get("apprise", {})
    return AppriseProviderConfig(
        enabled=apprise_data.get("enabled", False),
        url=apprise_data.get("url", "") or (app_config.ALERT_APPRISE_URL or ""),
    )


@router.get("/alerts")
def get_alerts() -> AlertConfigSchema:
    """Return the current alert configuration."""
    config = runtime_config.get_alert_config()
    providers_data = config.get("providers", {})

    return AlertConfigSchema(
        enabled=config.get("enabled", False),
        failure_threshold=config.get("failure_threshold", 3),
        cooldown_minutes=config.get("cooldown_minutes", 60),
        providers=AlertProvidersConfig(
            webhook=_build_webhook_config(providers_data),
            gotify=_build_gotify_config(providers_data),
            ntfy=_build_ntfy_config(providers_data),
            apprise=_build_apprise_config(providers_data),
        ),
    )


def _build_providers_dict(providers: AlertProvidersConfig) -> dict:
    """
    Build providers dictionary from schema for storage.
    Saves all provider data to preserve user's configuration.
    """
    return {
        "webhook": {
            "enabled": providers.webhook.enabled,
            "url": providers.webhook.url,
        },
        "gotify": {
            "enabled": providers.gotify.enabled,
            "url": providers.gotify.url,
            "token": providers.gotify.token,
            "priority": providers.gotify.priority,
        },
        "ntfy": {
            "enabled": providers.ntfy.enabled,
            "url": providers.ntfy.url,
            "topic": providers.ntfy.topic,
            "token": providers.ntfy.token,
            "priority": providers.ntfy.priority,
            "tags": providers.ntfy.tags,
        },
        "apprise": {
            "enabled": providers.apprise.enabled,
            "url": providers.apprise.url,
        },
    }


@router.put(
    "/alerts",
    dependencies=[Depends(require_api_key)],
)
def update_alerts(body: AlertConfigSchema) -> AlertConfigSchema:
    """Persist updated alert configuration."""
    alert_config = {
        "enabled": body.enabled,
        "failure_threshold": body.failure_threshold,
        "cooldown_minutes": body.cooldown_minutes,
        "providers": _build_providers_dict(body.providers),
    }

    runtime_config.set_alert_config(alert_config)
    return get_alerts()


class TestAlertResponse(BaseModel):
    """Response schema for test alert endpoint."""

    status: str
    results: dict[str, bool] = Field(default_factory=dict)
    message: str = ""


@router.post(
    "/alerts/test",
    dependencies=[Depends(require_api_key)],
)
def test_alerts() -> TestAlertResponse:
    """Send a test notification to all configured and enabled alert providers.

    Builds a fresh alert manager from current config to ensure the test uses
    the latest settings (even if they were just saved).
    """
    from src.api.main import _build_alert_manager_for_api

    # Always build fresh manager from current config
    alert_manager = _build_alert_manager_for_api()

    results = alert_manager.send_test_alert()

    if not results:
        return TestAlertResponse(
            status=TEST_ALERT_STATUS_NO_PROVIDERS,
            message="No alert providers are configured or enabled.",
        )

    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    if success_count == total_count:
        status = TEST_ALERT_STATUS_SUCCESS
        message = f"Test alerts sent successfully to all {total_count} provider(s)."
    elif success_count == 0:
        status = TEST_ALERT_STATUS_FAILED
        message = f"Test alerts failed for all {total_count} provider(s)."
    else:
        status = TEST_ALERT_STATUS_PARTIAL
        message = f"Test alerts sent to {success_count}/{total_count} provider(s)."

    logger.info("Test alert completed: %s", message)

    return TestAlertResponse(
        status=status,
        results=results,
        message=message,
    )
