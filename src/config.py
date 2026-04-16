# src/config.py

"""
Central configuration for Hermes.
All environment variables are read here — nowhere else in the app calls os.getenv() directly.
Reads from .env file automatically via python-dotenv.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
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


# --- Application ---
APP_ENV: str = os.getenv("APP_ENV", "development")
APP_VERSION: str = "0.1.0"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

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

# --- Loki Exporter ---
LOKI_URL: str | None = os.getenv("LOKI_URL", None)
LOKI_JOB_LABEL: str = os.getenv("LOKI_JOB_LABEL", "hermes_speedtest")
