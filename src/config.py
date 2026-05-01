# src/config.py

"""
Central configuration for Hermes.
All environment variables are read here — nowhere else in the app calls os.getenv() directly.
Reads from .env file automatically via python-dotenv.
"""

from __future__ import annotations

# Standard library
import logging
import os
from pathlib import Path

# Third-party
from dotenv import load_dotenv

# Local
from .runtime_config import get_interval_minutes

# Load .env file if present — does nothing in production if env vars are set directly
load_dotenv()


def _get_int(key: str, default: int) -> int:
    """Read an env var as int, falling back to default if missing or invalid."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logging.warning(
            "Config: invalid value for %s='%s', using default %s", key, value, default
        )
        return default


def _get_bool(key: str, default: bool) -> bool:
    """Read an env var as bool. Accepts 'true/false', '1/0', 'yes/no' (case insensitive)."""
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes")


def _get_csv_list(key: str, default: list[str]) -> list[str]:
    """Read an env var as a comma-separated list of strings."""
    value = os.getenv(key)
    if value is None:
        return default
    parsed = [item.strip() for item in value.split(",") if item.strip()]
    if not parsed:
        return default
    return parsed


def _get_str(key: str, default: str) -> str:
    """Read an env var as string, falling back to default if missing."""
    value = os.getenv(key)
    if value is None:
        return default
    # Strip whitespace and return default if result is empty
    stripped = value.strip()
    return stripped if stripped else default


# --- Application ---
APP_ENV: str = os.getenv("APP_ENV", "development")
APP_VERSION: str = os.getenv("APP_VERSION", "dev")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
TIMEZONE: str = os.getenv("TZ", "UTC")

# --- Authentication ---
# If set, all write endpoints (POST /api/trigger, PUT /api/config) require
# an X-Api-Key header whose value matches this key.
# Leave unset to disable authentication (local dev / trusted network).
API_KEY: str | None = os.getenv("API_KEY") or None

# Validate API key length to prevent weak keys
if API_KEY is not None and len(API_KEY) < 32:
    logging.error(
        "API_KEY must be at least 32 characters for security. "
        "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )
    raise SystemExit(1)

# Maximum requests per API key per 60-second window on protected endpoints.
# Set to 0 to disable rate limiting while keeping auth on.
_raw_rate_limit = _get_int("RATE_LIMIT_PER_MINUTE", 60)
RATE_LIMIT_PER_MINUTE: int = max(0, _raw_rate_limit)  # Clamp to non-negative

if _raw_rate_limit < 0:
    logging.warning(
        "RATE_LIMIT_PER_MINUTE cannot be negative (%d), using 0 (disabled)",
        _raw_rate_limit,
    )

# Maximum request body size in bytes (1 MB default)
MAX_REQUEST_BODY_SIZE: int = _get_int("MAX_REQUEST_BODY_SIZE", 1_048_576)

# CORS allowed origins (comma-separated URLs)
# NOSONAR - Development default for local frontend (http://localhost:5173,4173)
CORS_ORIGINS: str = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:4173",  # NOSONAR
)

# --- Scheduler ---
# Runtime config takes priority over env var
_env_interval: int = _get_int("SPEEDTEST_INTERVAL_MINUTES", 60)
SPEEDTEST_INTERVAL_MINUTES: int = get_interval_minutes(default=_env_interval)

RUN_ON_STARTUP: bool = _get_bool("RUN_ON_STARTUP", True)
ENABLED_EXPORTERS: list[str] = _get_csv_list("ENABLED_EXPORTERS", ["csv"])

# --- CSV Exporter ---
# CSV_MAX_ROWS and CSV_RETENTION_DAYS default to 0, which means unlimited.
CSV_LOG_PATH: Path = Path(os.getenv("CSV_LOG_PATH", "logs/results.csv"))
CSV_MAX_ROWS: int = _get_int("CSV_MAX_ROWS", 0)
CSV_RETENTION_DAYS: int = _get_int("CSV_RETENTION_DAYS", 0)

# --- Prometheus Exporter ---
PROMETHEUS_PORT: int = _get_int("PROMETHEUS_PORT", 8000)

# --- Health Endpoint ---
HEALTH_PORT: int = _get_int("HEALTH_PORT", 8080)

# --- SQLite Exporter ---
SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "data/hermes.db")
SQLITE_MAX_ROWS: int = _get_int("SQLITE_MAX_ROWS", 0)
SQLITE_RETENTION_DAYS: int = _get_int("SQLITE_RETENTION_DAYS", 0)

# --- Loki Exporter ---
LOKI_URL: str | None = os.getenv("LOKI_URL", None)
LOKI_JOB_LABEL: str = os.getenv("LOKI_JOB_LABEL", "hermes_speedtest")

# --- Alerting ---
# Alerting is disabled by default. Enable by setting failure threshold > 0.
ALERT_FAILURE_THRESHOLD: int = _get_int("ALERT_FAILURE_THRESHOLD", 0)
ALERT_COOLDOWN_MINUTES: int = _get_int("ALERT_COOLDOWN_MINUTES", 60)

# Webhook alerting
ALERT_WEBHOOK_URL: str | None = os.getenv("ALERT_WEBHOOK_URL") or None

# Gotify alerting
ALERT_GOTIFY_URL: str | None = os.getenv("ALERT_GOTIFY_URL") or None
ALERT_GOTIFY_TOKEN: str | None = os.getenv("ALERT_GOTIFY_TOKEN") or None
ALERT_GOTIFY_PRIORITY: int = _get_int("ALERT_GOTIFY_PRIORITY", 5)

# ntfy alerting
ALERT_NTFY_URL: str | None = os.getenv("ALERT_NTFY_URL") or None
ALERT_NTFY_TOPIC: str | None = os.getenv("ALERT_NTFY_TOPIC") or None
ALERT_NTFY_TOKEN: str | None = os.getenv("ALERT_NTFY_TOKEN") or None
ALERT_NTFY_PRIORITY: int = _get_int("ALERT_NTFY_PRIORITY", 3)
ALERT_NTFY_TAGS: list[str] = _get_csv_list(
    "ALERT_NTFY_TAGS", ["warning", "rotating_light"]
)

# Apprise alerting (API service endpoint)
ALERT_APPRISE_URL: str | None = os.getenv("ALERT_APPRISE_URL") or None
