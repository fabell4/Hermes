"""GET /api/alerts and PUT /api/alerts — alert configuration."""

from __future__ import annotations

import ipaddress
import logging
import time
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
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


# ---------------------------------------------------------------------------
# SSRF Protection
# ---------------------------------------------------------------------------


def _check_dangerous_hostnames(hostname: str, field_name: str) -> None:
    """Check for localhost and reserved hostnames.

    Args:
        hostname: The hostname to check
        field_name: Human-readable field name for error messages

    Raises:
        HTTPException: If hostname is localhost or a reserved address
    """
    hostname_lower = hostname.lower()
    if hostname_lower in (  # NOSONAR - checking values to BLOCK them (SSRF protection)
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "::",
    ):
        raise HTTPException(
            status_code=422,
            detail=f"{field_name}: Localhost addresses are not allowed.",
        )


def _check_ip_address_restrictions(hostname: str, field_name: str) -> None:
    """Check if hostname is an IP address with restrictions.

    Args:
        hostname: The hostname to check
        field_name: Human-readable field name for error messages

    Raises:
        HTTPException: If IP address is restricted (loopback, link-local, private, reserved)
    """
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_loopback:
            raise HTTPException(
                status_code=422,
                detail=f"{field_name}: Loopback addresses are not allowed.",
            )
        if ip.is_link_local:
            raise HTTPException(
                status_code=422,
                detail=f"{field_name}: Link-local addresses are not allowed.",
            )
        if ip.is_reserved:
            raise HTTPException(
                status_code=422,
                detail=f"{field_name}: Reserved IP addresses are not allowed.",
            )
        if ip.is_private:
            raise HTTPException(
                status_code=422,
                detail=f"{field_name}: Private IP addresses are not allowed (RFC 1918/4193).",
            )
    except ValueError:
        # Not an IP address — it's a hostname/domain, which is allowed
        # (DNS rebinding is a separate issue, not addressed here)
        logger.debug("%s is not an IP address (hostname/domain allowed)", hostname)


def validate_alert_url(url: str, field_name: str) -> None:
    """Validate alert provider URL to prevent Server-Side Request Forgery (SSRF).

    Blocks:
    - Non-HTTP(S) schemes (file://, ftp://, etc.)
    - Localhost addresses
    - Private IP ranges (RFC 1918, RFC 4193)
    - Link-local addresses

    Args:
        url: The URL to validate
        field_name: Human-readable field name for error messages

    Raises:
        HTTPException: If URL is invalid or unsafe (documented in endpoint responses)
    """
    if not url:
        return  # Empty URL is valid (provider disabled)

    try:
        parsed = urlparse(url)

        # Only allow http/https schemes
        if parsed.scheme not in ("http", "https"):
            raise HTTPException(
                status_code=422,
                detail=f"{field_name}: Only http:// and https:// URLs are allowed (got {parsed.scheme}://).",
            )

        if not parsed.hostname:
            raise HTTPException(
                status_code=422, detail=f"{field_name}: URL must include a hostname."
            )

        # Check for localhost and reserved hostnames
        _check_dangerous_hostnames(parsed.hostname, field_name)

        # Check for private IP ranges
        _check_ip_address_restrictions(parsed.hostname, field_name)

    except ValueError as e:
        raise HTTPException(
            status_code=422, detail=f"{field_name}: Invalid URL format — {e}"
        ) from e


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


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
    responses={
        422: {
            "description": "Invalid alert configuration (e.g., unsafe URL, invalid values)"
        }
    },
)
def update_alerts(body: AlertConfigSchema) -> AlertConfigSchema:
    """Persist updated alert configuration."""
    # Validate all provider URLs to prevent SSRF attacks
    validate_alert_url(body.providers.webhook.url, "Webhook URL")
    validate_alert_url(body.providers.gotify.url, "Gotify URL")
    validate_alert_url(body.providers.ntfy.url, "ntfy URL")
    validate_alert_url(body.providers.apprise.url, "Apprise URL")

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


# ---------------------------------------------------------------------------
# Test Alert Rate Limiting
# ---------------------------------------------------------------------------

_test_alert_last_call: float = 0.0
_TEST_ALERT_COOLDOWN_SECONDS = 10


def _check_test_alert_rate_limit() -> None:
    """Enforce rate limit for test alert endpoint to prevent abuse.

    Raises:
        HTTPException 429: if cooldown period has not elapsed
    """
    global _test_alert_last_call  # pylint: disable=global-statement
    now = time.time()
    elapsed = now - _test_alert_last_call

    if _test_alert_last_call > 0 and elapsed < _TEST_ALERT_COOLDOWN_SECONDS:
        remaining = int(_TEST_ALERT_COOLDOWN_SECONDS - elapsed)
        raise HTTPException(
            status_code=429,
            detail=f"Test alerts can only be sent every {_TEST_ALERT_COOLDOWN_SECONDS} seconds. Try again in {remaining} seconds.",
            headers={"Retry-After": str(remaining)},
        )

    _test_alert_last_call = now


# ---------------------------------------------------------------------------
# Test Alert Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/alerts/test",
    dependencies=[Depends(require_api_key)],
    responses={
        429: {
            "description": "Rate limit exceeded — wait before sending another test alert"
        }
    },
)
def test_alerts() -> TestAlertResponse:
    """Send a test notification to all configured and enabled alert providers.

    Builds a fresh alert manager from current config to ensure the test uses
    the latest settings (even if they were just saved).

    Rate limited to once every 10 seconds to prevent abuse.
    """
    # Enforce rate limit
    _check_test_alert_rate_limit()

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
