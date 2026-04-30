# src/runtime_config.py

"""
Runtime configuration — persists user changes made via the UI across restarts.
Stored as a JSON file mapped as a Docker volume.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

RUNTIME_CONFIG_PATH = Path("data/runtime_config.json")

# Cache for runtime config to avoid repeated file reads
_config_cache: dict | None = None
_config_mtime: float = 0


def _ensure_dir() -> None:
    RUNTIME_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _validate_interval_minutes(data: dict, sanitized: dict) -> None:
    """Validate and sanitize interval_minutes field (1 to 10080 minutes)."""
    if "interval_minutes" not in data:
        return

    try:
        val = int(data["interval_minutes"])
        if 1 <= val <= 10080:  # 1 week = 10080 minutes
            sanitized["interval_minutes"] = val
        else:
            logger.warning(
                "interval_minutes (%d) out of range [1, 10080] — discarding.", val
            )
    except (ValueError, TypeError):
        logger.warning(
            "Invalid interval_minutes value: %s — discarding.",
            data["interval_minutes"],
        )


def _validate_enabled_exporters(data: dict, sanitized: dict) -> None:
    """Validate and sanitize enabled_exporters field (must be list of strings)."""
    if "enabled_exporters" not in data:
        return

    if isinstance(data["enabled_exporters"], list):
        validated_exporters = [
            str(e)
            for e in data["enabled_exporters"]
            if isinstance(e, str) and e.strip()
        ]
        if validated_exporters:
            sanitized["enabled_exporters"] = validated_exporters
        else:
            logger.warning("enabled_exporters list is empty — discarding.")
    else:
        logger.warning(
            "enabled_exporters is not a list — discarding: %s",
            type(data["enabled_exporters"]).__name__,
        )


def _validate_scanning_disabled(data: dict, sanitized: dict) -> None:
    """Validate and sanitize scanning_disabled field (must be boolean)."""
    if "scanning_disabled" not in data:
        return

    if isinstance(data["scanning_disabled"], bool):
        sanitized["scanning_disabled"] = data["scanning_disabled"]
    else:
        logger.warning(
            "scanning_disabled is not a bool — discarding: %s",
            type(data["scanning_disabled"]).__name__,
        )


def _validate_scheduler_paused(data: dict, sanitized: dict) -> None:
    """Validate and sanitize scheduler_paused field (must be boolean)."""
    if "scheduler_paused" not in data:
        return

    if isinstance(data["scheduler_paused"], bool):
        sanitized["scheduler_paused"] = data["scheduler_paused"]
    else:
        logger.warning(
            "scheduler_paused is not a bool — discarding: %s",
            type(data["scheduler_paused"]).__name__,
        )


def _validate_timestamp_fields(data: dict, sanitized: dict) -> None:
    """Validate and sanitize timestamp string fields."""
    for key in ["last_run_at", "next_run_at"]:
        if key in data:
            if isinstance(data[key], str) and data[key].strip():
                sanitized[key] = data[key]
            elif data[key] is not None:
                logger.warning(
                    "%s is not a valid string — discarding: %s", key, data[key]
                )


def _validate_alert_config(data: dict, sanitized: dict) -> None:
    """Validate and sanitize alert_config field (must be dict)."""
    if "alert_config" not in data:
        return

    if isinstance(data["alert_config"], dict):
        sanitized["alert_config"] = data["alert_config"]
    else:
        logger.warning(
            "alert_config is not a dict — discarding: %s",
            type(data["alert_config"]).__name__,
        )


def load() -> dict:
    """
    Loads the runtime config from disk with validation.
    Returns an empty dict if the file doesn't exist yet.
    Invalid values are logged and discarded to prevent corrupted config from crashing the app.

    Uses file modification time caching to avoid repeated file reads and validation.
    Cache is invalidated when file is modified.
    """
    global _config_cache, _config_mtime

    if not RUNTIME_CONFIG_PATH.exists():
        return {}

    try:
        # Check modification time for caching
        current_mtime = RUNTIME_CONFIG_PATH.stat().st_mtime

        # Cache hit - file hasn't changed
        if _config_cache is not None and current_mtime == _config_mtime:
            return _config_cache.copy()  # Return copy to prevent mutation

        # Cache miss - reload and validate
        with open(RUNTIME_CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)

        # Validate structure - must be a dict
        if not isinstance(data, dict):
            logger.warning("Runtime config is not a dict — using defaults.")
            return {}

        # Sanitize and validate each field using helper functions
        sanitized: dict = {}
        _validate_interval_minutes(data, sanitized)
        _validate_enabled_exporters(data, sanitized)
        _validate_scanning_disabled(data, sanitized)
        _validate_scheduler_paused(data, sanitized)
        _validate_timestamp_fields(data, sanitized)
        _validate_alert_config(data, sanitized)

        # Update cache
        _config_cache = sanitized
        _config_mtime = current_mtime

        return sanitized

    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not read runtime config: %s — using defaults.", e)
        return {}


def save(data: dict) -> None:
    """
    Writes the runtime config to disk atomically.
    Merges with existing values so unrelated keys are preserved.

    Uses atomic write pattern (write to temp file, then rename) to prevent
    corruption if write fails or process crashes mid-write.
    """
    global _config_cache, _config_mtime

    _ensure_dir()
    existing = load()
    existing.update(data)

    config_path = Path(RUNTIME_CONFIG_PATH)

    # Write to temporary file first
    fd, temp_path = tempfile.mkstemp(
        dir=config_path.parent, prefix=".runtime_config_", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

        # Atomic rename (OS guarantees this is atomic)
        Path(temp_path).replace(config_path)

        # Invalidate cache so next load() will re-read
        _config_cache = None
        _config_mtime = 0

        logger.info("Runtime config saved: %s", existing)
    except Exception as e:
        # Clean up temp file on failure
        try:
            Path(temp_path).unlink(missing_ok=True)
        except OSError:
            pass  # Best effort cleanup
        logger.error("Could not save runtime config: %s", e)
        raise


def get_interval_minutes(default: int) -> int:
    """
    Returns the persisted interval if set and valid, otherwise the provided default.
    Enforces bounds: 1 minute minimum, 10080 minutes (1 week) maximum.
    """
    data = load()
    value = data.get("interval_minutes")
    if value is None:
        return default
    try:
        interval = int(value)
        # Enforce reasonable bounds (defense-in-depth, also validated in load())
        if interval < 1:
            logger.warning(
                "interval_minutes (%d) is below minimum (1), using default.", interval
            )
            return default
        if interval > 10080:  # 1 week
            logger.warning(
                "interval_minutes (%d) exceeds maximum (10080), using default.",
                interval,
            )
            return default
        return interval
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
