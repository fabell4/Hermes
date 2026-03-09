# src/runtime_config.py

"""
Runtime configuration — persists user changes made via the UI across restarts.
Stored as a JSON file mapped as a Docker volume.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

RUNTIME_CONFIG_PATH = Path("data/runtime_config.json")


def _ensure_dir() -> None:
    RUNTIME_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def load() -> dict:
    """
    Loads the runtime config from disk.
    Returns an empty dict if the file doesn't exist yet.
    """
    if not RUNTIME_CONFIG_PATH.exists():
        return {}
    try:
        with open(RUNTIME_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not read runtime config: %s — using defaults.", e)
        return {}


def save(data: dict) -> None:
    """
    Writes the runtime config to disk.
    Merges with existing values so unrelated keys are preserved.
    """
    _ensure_dir()
    existing = load()
    existing.update(data)
    try:
        with open(RUNTIME_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
        logger.info("Runtime config saved: %s", existing)
    except OSError as e:
        logger.error("Could not save runtime config: %s", e)
        raise


def get_interval_minutes(default: int) -> int:
    """Returns the persisted interval if set, otherwise the provided default."""
    data = load()
    value = data.get("interval_minutes")
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        logger.warning("Invalid interval_minutes in runtime config, using default.")
        return default


def set_interval_minutes(minutes: int) -> None:
    """Persists a new interval value to disk."""
    save({"interval_minutes": minutes})


def get_enabled_exporters(default: list[str]) -> list[str]:
    """
    Returns the persisted enabled exporters list if set,
    otherwise the provided default.
    """
    data = load()
    value = data.get("enabled_exporters")
    if value is None:
        return default
    if not isinstance(value, list):
        logger.warning("Invalid enabled_exporters in runtime config, using default.")
        return default
    return value


def set_enabled_exporters(exporters: list[str]) -> None:
    """Persists the enabled exporters list to disk."""
    save({"enabled_exporters": exporters})
