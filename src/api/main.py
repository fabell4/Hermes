"""FastAPI entry-point for the Hermes REST API.

Run with:
    uvicorn src.api.main:app --port 8080 --reload
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse

from src.api.routes import config, results, trigger, alerts
from src import runtime_config as rc
from src import shared_state
from src.services.alert_manager import AlertManager
from src.services.alert_providers import (
    WebhookProvider,
    GotifyProvider,
    NtfyProvider,
    AppriseProvider,
)
from src import config as app_config

logger = logging.getLogger(__name__)

_START_TIME = time.time()

# Path to the pre-built Vite output — present in Docker, absent in dev.
_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


def _build_alert_manager_for_api() -> AlertManager:
    """
    Build alert manager for the API process.
    This is separate from the scheduler's alert manager since they run in different processes.
    """
    alert_config = rc.get_alert_config()

    failure_threshold = alert_config.get(
        "failure_threshold", app_config.ALERT_FAILURE_THRESHOLD
    )
    cooldown_minutes = alert_config.get(
        "cooldown_minutes", app_config.ALERT_COOLDOWN_MINUTES
    )

    manager = AlertManager(
        failure_threshold=max(1, failure_threshold),
        cooldown_minutes=cooldown_minutes,
    )

    # Always register providers for API (used for test notifications)
    # Individual providers check their own enabled flag
    _register_alert_providers(manager, alert_config.get("providers", {}))

    return manager


def _register_webhook_provider(manager: AlertManager, providers_config: dict) -> None:
    """Register webhook alert provider if configured and enabled."""
    webhook_url = (
        providers_config.get("webhook", {}).get("url") or app_config.ALERT_WEBHOOK_URL
    )
    if webhook_url and providers_config.get("webhook", {}).get("enabled", False):
        try:
            manager.add_provider("webhook", WebhookProvider(url=webhook_url))
        except Exception as e:  # pylint: disable=broad-except  # NOSONAR
            logger.warning("Could not initialize webhook alert provider: %s", e)


def _register_gotify_provider(manager: AlertManager, providers_config: dict) -> None:
    """Register Gotify alert provider if configured and enabled."""
    gotify_config = providers_config.get("gotify", {})
    gotify_url = gotify_config.get("url") or app_config.ALERT_GOTIFY_URL
    gotify_token = gotify_config.get("token") or app_config.ALERT_GOTIFY_TOKEN
    if gotify_url and gotify_token and gotify_config.get("enabled", False):
        try:
            manager.add_provider(
                "gotify",
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


def _register_ntfy_provider(manager: AlertManager, providers_config: dict) -> None:
    """Register ntfy alert provider if configured and enabled."""
    ntfy_config = providers_config.get("ntfy", {})
    ntfy_topic = ntfy_config.get("topic") or app_config.ALERT_NTFY_TOPIC
    if ntfy_topic and ntfy_config.get("enabled", False):
        try:
            manager.add_provider(
                "ntfy",
                NtfyProvider(
                    url=ntfy_config.get("url")
                    or app_config.ALERT_NTFY_URL
                    or "https://ntfy.sh",
                    topic=ntfy_topic,
                    token=ntfy_config.get("token") or app_config.ALERT_NTFY_TOKEN,
                    priority=ntfy_config.get(
                        "priority", app_config.ALERT_NTFY_PRIORITY
                    ),
                    tags=ntfy_config.get("tags", app_config.ALERT_NTFY_TAGS),
                ),
            )
        except Exception as e:  # pylint: disable=broad-except  # NOSONAR
            logger.warning("Could not initialize ntfy alert provider: %s", e)


def _register_apprise_provider(manager: AlertManager, providers_config: dict) -> None:
    """Register Apprise alert provider if configured and enabled."""
    apprise_config = providers_config.get("apprise", {})
    apprise_url = apprise_config.get("url") or app_config.ALERT_APPRISE_URL
    apprise_urls = apprise_config.get("urls", [])
    if apprise_url and apprise_config.get("enabled", False):
        try:
            manager.add_provider(
                "apprise",
                AppriseProvider(
                    url=apprise_url, urls=apprise_urls if apprise_urls else None
                ),
            )
        except Exception as e:  # pylint: disable=broad-except  # NOSONAR
            logger.warning("Could not initialize Apprise alert provider: %s", e)


def _register_alert_providers(manager: AlertManager, providers_config: dict) -> None:
    """Register alert providers based on configuration."""
    _register_webhook_provider(manager, providers_config)
    _register_gotify_provider(manager, providers_config)
    _register_ntfy_provider(manager, providers_config)
    _register_apprise_provider(manager, providers_config)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    # Startup
    logger.info("Initializing alert manager for API process...")
    alert_manager = _build_alert_manager_for_api()
    shared_state.set_alert_manager(alert_manager)
    logger.info("Alert manager initialized.")
    yield
    # Shutdown (if cleanup needed)


app = FastAPI(
    title="Hermes API",
    description="REST interface for the Hermes speed-monitor.",
    version="0.1.0",
    lifespan=lifespan,
)


# Security middleware
class _RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforce maximum request body size to prevent memory exhaustion."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > app_config.MAX_REQUEST_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": f"Request body too large (max {app_config.MAX_REQUEST_BODY_SIZE} bytes)"
                },
            )
        return await call_next(request)


class _SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(_RequestSizeLimitMiddleware)
app.add_middleware(_SecurityHeadersMiddleware)

# Parse CORS origins from config
_cors_origins = [
    origin.strip() for origin in app_config.CORS_ORIGINS.split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type", "X-Api-Key"],
)

app.include_router(results.router, prefix="/api")
app.include_router(trigger.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")


class HealthResponse(BaseModel):
    """Response schema for the /api/health endpoint."""

    status: Literal["ok", "degraded"]
    scheduler_running: bool
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    uptime_seconds: float
    version: str


@app.get("/api/health", tags=["health"])
def health() -> HealthResponse:
    """Return scheduler and application health status."""
    data = rc.load()
    return HealthResponse(
        status="ok",
        scheduler_running=not data.get("scanning_disabled", False),
        last_run=data.get("last_run_at"),
        next_run=data.get("next_run_at"),
        uptime_seconds=round(time.time() - _START_TIME, 1),
        version=os.environ.get("APP_VERSION", "dev"),
    )


# ---------------------------------------------------------------------------
# SPA static file serving — only active when the Vite dist folder exists
# (i.e. in the Docker image). In development the Vite dev server handles this.
# API routes registered above take precedence; this catch-all serves the SPA.
# ---------------------------------------------------------------------------
if _DIST.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=str(_DIST / "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        """Return index.html for all non-API paths to support client-side routing."""
        logger.debug("SPA fallback: /%s", full_path)
        return FileResponse(str(_DIST / "index.html"))
