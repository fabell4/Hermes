"""GET /api/alerts and PUT /api/alerts — alert configuration."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src import runtime_config
from src.api.auth import require_api_key
from src import shared_state

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


@router.get("/alerts")
def get_alerts() -> AlertConfigSchema:
    """Return the current alert configuration."""
    config = runtime_config.get_alert_config()

    # Convert runtime config dict to structured schema
    providers_data = config.get("providers", {})

    # Helper to get provider value with env var fallback
    from src import config as app_config

    return AlertConfigSchema(
        enabled=config.get("enabled", False),
        failure_threshold=config.get("failure_threshold", 3),
        cooldown_minutes=config.get("cooldown_minutes", 60),
        providers=AlertProvidersConfig(
            webhook=WebhookProviderConfig(
                enabled=providers_data.get("webhook", {}).get("enabled", False),
                url=providers_data.get("webhook", {}).get("url", "")
                or (app_config.ALERT_WEBHOOK_URL or ""),
            ),
            gotify=GotifyProviderConfig(
                enabled=providers_data.get("gotify", {}).get("enabled", False),
                url=providers_data.get("gotify", {}).get("url", "")
                or (app_config.ALERT_GOTIFY_URL or ""),
                token=providers_data.get("gotify", {}).get("token", "")
                or (app_config.ALERT_GOTIFY_TOKEN or ""),
                priority=providers_data.get("gotify", {}).get("priority", 5)
                or app_config.ALERT_GOTIFY_PRIORITY,
            ),
            ntfy=NtfyProviderConfig(
                enabled=providers_data.get("ntfy", {}).get("enabled", False),
                url=providers_data.get("ntfy", {}).get("url", "")
                or (app_config.ALERT_NTFY_URL or "https://ntfy.sh"),
                topic=providers_data.get("ntfy", {}).get("topic", "")
                or (app_config.ALERT_NTFY_TOPIC or ""),
                token=providers_data.get("ntfy", {}).get("token", "")
                or (app_config.ALERT_NTFY_TOKEN or ""),
                priority=providers_data.get("ntfy", {}).get("priority", 3)
                or app_config.ALERT_NTFY_PRIORITY,
                tags=providers_data.get("ntfy", {}).get("tags", [])
                or app_config.ALERT_NTFY_TAGS,
            ),
            apprise=AppriseProviderConfig(
                enabled=providers_data.get("apprise", {}).get("enabled", False),
                url=providers_data.get("apprise", {}).get("url", "")
                or (app_config.ALERT_APPRISE_URL or ""),
            ),
        ),
    )


@router.put(
    "/alerts",
    dependencies=[Depends(require_api_key)],
)
def update_alerts(body: AlertConfigSchema) -> AlertConfigSchema:
    """Persist updated alert configuration."""
    # Convert schema to dict for storage
    # Save all provider configurations, even if disabled or incomplete
    # This preserves user's partial configurations while they're editing
    providers_dict = {}

    # Webhook provider - save if any data is present
    if body.providers.webhook.enabled or body.providers.webhook.url:
        providers_dict["webhook"] = {
            "enabled": body.providers.webhook.enabled,
            "url": body.providers.webhook.url,
        }

    # Gotify provider - save if any data is present
    if (
        body.providers.gotify.enabled
        or body.providers.gotify.url
        or body.providers.gotify.token
    ):
        providers_dict["gotify"] = {
            "enabled": body.providers.gotify.enabled,
            "url": body.providers.gotify.url,
            "token": body.providers.gotify.token,
            "priority": body.providers.gotify.priority,
        }

    # ntfy provider - save if any data is present
    if body.providers.ntfy.enabled or body.providers.ntfy.topic:
        providers_dict["ntfy"] = {
            "enabled": body.providers.ntfy.enabled,
            "url": body.providers.ntfy.url,
            "topic": body.providers.ntfy.topic,
            "token": body.providers.ntfy.token,
            "priority": body.providers.ntfy.priority,
            "tags": body.providers.ntfy.tags,
        }

    # Apprise provider - save if any data is present
    if body.providers.apprise.enabled or body.providers.apprise.url:
        providers_dict["apprise"] = {
            "enabled": body.providers.apprise.enabled,
            "url": body.providers.apprise.url,
        }

    alert_config = {
        "enabled": body.enabled,
        "failure_threshold": body.failure_threshold,
        "cooldown_minutes": body.cooldown_minutes,
        "providers": providers_dict,
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
    responses={
        503: {
            "description": "Alert manager not initialized. Ensure scheduler is running."
        },
    },
)
def test_alerts() -> TestAlertResponse:
    """Send a test notification to all configured and enabled alert providers."""
    alert_manager = shared_state.get_alert_manager()

    if alert_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Alert manager not initialized. Ensure the scheduler is running.",
        )

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
