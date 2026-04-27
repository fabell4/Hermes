# src/runtime_config.py

"""
Runtime configuration — persists user changes made via the UI across restarts.
Stored as a JSON file mapped as a Docker volume.
"""

import json
import logging
from pathlib import Path
from typing import cast

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
            return cast(dict, json.load(f))
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


# --- Run trigger ---
# Written by the UI process; consumed and deleted by the scheduler process.

RUN_TRIGGER_PATH = Path("data/.run_trigger")


def trigger_run() -> None:
    """Signal the scheduler process to run a test immediately."""
    _ensure_dir()
    RUN_TRIGGER_PATH.touch()


def consume_run_trigger() -> bool:
    """
    Check whether the UI requested an immediate run.
    Deletes the trigger file and returns True if it was present.
    """
    if RUN_TRIGGER_PATH.exists():
        try:
            RUN_TRIGGER_PATH.unlink()
        except OSError as exc:
            logger.warning(
                "Could not remove run-trigger file %s: %s", RUN_TRIGGER_PATH, exc
            )
        return True
    return False


# --- Running state ---
# Written by the scheduler when a test is in progress; deleted when done.
# Lets the UI show a live "Running speedtest..." indicator.

RUNNING_PATH = Path("data/.running")


def mark_running() -> None:
    """Creates the running sentinel file to signal an active speedtest."""
    _ensure_dir()
    RUNNING_PATH.touch()


def mark_done() -> None:
    """Removes the running sentinel file when the speedtest finishes."""
    RUNNING_PATH.unlink(missing_ok=True)


def is_running() -> bool:
    """Returns True if a speedtest is currently in progress."""
    return RUNNING_PATH.exists()


# --- Next run time ---
# Written by the scheduler each poll cycle so the UI can show a countdown.


def get_next_run_at() -> str | None:
    """Returns the ISO-format next run timestamp, or None if not yet set."""
    return load().get("next_run_at")


def set_next_run_at(iso_timestamp: str) -> None:
    """Persists the next scheduled run time (ISO format) for the UI to read."""
    save({"next_run_at": iso_timestamp})


# --- Last successful run ---


def get_last_run_at() -> str | None:
    """Returns the ISO-format timestamp of the last successful run, or None."""
    return load().get("last_run_at")


def set_last_run_at(iso_timestamp: str) -> None:
    """Persists the timestamp of the last successful speedtest run."""
    save({"last_run_at": iso_timestamp})


# --- Scheduler paused state ---


def get_scheduler_paused() -> bool:
    """Returns True if automated scans have been paused via the UI."""
    return bool(load().get("scheduler_paused", False))


def set_scheduler_paused(paused: bool) -> None:
    """Persists whether automated scans are paused."""
    save({"scheduler_paused": paused})


# --- Alert configuration ---


def _load_alert_config_from_env() -> dict:
    """
    Load alert configuration from environment variables.

    Returns a dict with keys:
    - enabled: bool
    - failure_threshold: int
    - cooldown_minutes: int
    - providers: dict[str, dict]
    """
    from . import config  # Import here to avoid circular dependency

    providers = {}

    # Webhook provider
    if config.ALERT_WEBHOOK_URL:
        providers["webhook"] = {
            "enabled": True,
            "url": config.ALERT_WEBHOOK_URL,
        }

    # Gotify provider
    if config.ALERT_GOTIFY_URL and config.ALERT_GOTIFY_TOKEN:
        providers["gotify"] = {
            "enabled": True,
            "url": config.ALERT_GOTIFY_URL,
            "token": config.ALERT_GOTIFY_TOKEN,
            "priority": config.ALERT_GOTIFY_PRIORITY,
        }

    # ntfy provider
    if config.ALERT_NTFY_TOPIC:
        providers["ntfy"] = {
            "enabled": True,
            "url": config.ALERT_NTFY_URL or "https://ntfy.sh",
            "topic": config.ALERT_NTFY_TOPIC,
            "token": config.ALERT_NTFY_TOKEN or "",
            "priority": config.ALERT_NTFY_PRIORITY,
            "tags": config.ALERT_NTFY_TAGS,
        }

    # Apprise provider
    if config.ALERT_APPRISE_URL:
        providers["apprise"] = {
            "enabled": True,
            "url": config.ALERT_APPRISE_URL,
        }

    # Determine if alerting is enabled (threshold > 0 OR any providers configured)
    enabled = config.ALERT_FAILURE_THRESHOLD > 0 or len(providers) > 0

    return {
        "enabled": enabled,
        "failure_threshold": max(config.ALERT_FAILURE_THRESHOLD, 1)
        if config.ALERT_FAILURE_THRESHOLD > 0
        else 3,
        "cooldown_minutes": config.ALERT_COOLDOWN_MINUTES,
        "providers": providers,
    }


def get_alert_config() -> dict:
    """
    Returns the alert configuration with defaults.

    Priority order:
    1. Runtime config file (user has saved settings in UI)
    2. Environment variables (initial configuration)
    3. Hard-coded defaults

    Returns a dict with keys:
    - enabled: bool
    - failure_threshold: int
    - cooldown_minutes: int
    - providers: dict[str, dict] (webhook, gotify, ntfy configurations)
    """
    data = load().get("alert_config")

    # If runtime config exists, use it (user has customized via UI)
    if data is not None:
        return {
            "enabled": data.get("enabled", False),
            "failure_threshold": data.get("failure_threshold", 3),
            "cooldown_minutes": data.get("cooldown_minutes", 60),
            "providers": data.get("providers", {}),
        }

    # Otherwise, load from environment variables
    return _load_alert_config_from_env()


def set_alert_config(config: dict) -> None:
    """
    Persists alert configuration to disk.

    Args:
        config: Dict with keys: enabled, failure_threshold, cooldown_minutes, providers
    """
    save({"alert_config": config})
