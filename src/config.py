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
        logging.warning("Config: invalid value for %s='%s', using default %s", key, value, default)
        return default


def _get_bool(key: str, default: bool) -> bool:
    """Read an env var as bool. Accepts 'true/false', '1/0', 'yes/no' (case insensitive)."""
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes")


# --- Application ---
APP_ENV: str = os.getenv("APP_ENV", "development")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

# --- Scheduler ---
# Runtime config takes priority over env var
_env_interval: int = _get_int("SPEEDTEST_INTERVAL_MINUTES", 60)
SPEEDTEST_INTERVAL_MINUTES: int = get_interval_minutes(default=_env_interval)

RUN_ON_STARTUP: bool = _get_bool("RUN_ON_STARTUP", True)

# --- CSV Exporter ---
CSV_LOG_PATH: Path = Path(os.getenv("CSV_LOG_PATH", "logs/results.csv"))

# --- Prometheus Exporter ---
PROMETHEUS_PORT: int = _get_int("PROMETHEUS_PORT", 8000)

# --- Loki Exporter ---
LOKI_URL: str | None = os.getenv("LOKI_URL", None)
LOKI_JOB_LABEL: str = os.getenv("LOKI_JOB_LABEL", "hermes_speedtest")