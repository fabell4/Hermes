"""GET /api/alerts and PUT /api/alerts — alert configuration."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src import runtime_config
from src.api.auth import require_api_key

router = APIRouter(tags=["alerts"])


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


class AlertProvidersConfig(BaseModel):
    """Alert providers configuration."""

    webhook: WebhookProviderConfig = Field(default_factory=WebhookProviderConfig)
    gotify: GotifyProviderConfig = Field(default_factory=GotifyProviderConfig)
    ntfy: NtfyProviderConfig = Field(default_factory=NtfyProviderConfig)


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

    return AlertConfigSchema(
        enabled=config.get("enabled", False),
        failure_threshold=config.get("failure_threshold", 3),
        cooldown_minutes=config.get("cooldown_minutes", 60),
        providers=AlertProvidersConfig(
            webhook=WebhookProviderConfig(
                enabled=providers_data.get("webhook", {}).get("enabled", False),
                url=providers_data.get("webhook", {}).get("url", ""),
            ),
            gotify=GotifyProviderConfig(
                enabled=providers_data.get("gotify", {}).get("enabled", False),
                url=providers_data.get("gotify", {}).get("url", ""),
                token=providers_data.get("gotify", {}).get("token", ""),
                priority=providers_data.get("gotify", {}).get("priority", 5),
            ),
            ntfy=NtfyProviderConfig(
                enabled=providers_data.get("ntfy", {}).get("enabled", False),
                url=providers_data.get("ntfy", {}).get("url", "https://ntfy.sh"),
                topic=providers_data.get("ntfy", {}).get("topic", ""),
                priority=providers_data.get("ntfy", {}).get("priority", 3),
                tags=providers_data.get("ntfy", {}).get(
                    "tags", ["warning", "rotating_light"]
                ),
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
    providers_dict = {}

    # Only include providers that are actually configured
    if body.providers.webhook.enabled and body.providers.webhook.url:
        providers_dict["webhook"] = {
            "enabled": True,
            "url": body.providers.webhook.url,
        }

    if (
        body.providers.gotify.enabled
        and body.providers.gotify.url
        and body.providers.gotify.token
    ):
        providers_dict["gotify"] = {
            "enabled": True,
            "url": body.providers.gotify.url,
            "token": body.providers.gotify.token,
            "priority": body.providers.gotify.priority,
        }

    if body.providers.ntfy.enabled and body.providers.ntfy.topic:
        providers_dict["ntfy"] = {
            "enabled": True,
            "url": body.providers.ntfy.url,
            "topic": body.providers.ntfy.topic,
            "priority": body.providers.ntfy.priority,
            "tags": body.providers.ntfy.tags,
        }

    alert_config = {
        "enabled": body.enabled,
        "failure_threshold": body.failure_threshold,
        "cooldown_minutes": body.cooldown_minutes,
        "providers": providers_dict,
    }

    runtime_config.set_alert_config(alert_config)
    return get_alerts()
