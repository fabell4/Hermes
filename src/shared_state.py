"""Shared application state for API access to core components."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.alert_manager import AlertManager

_alert_manager: AlertManager | None = None
_lock = threading.Lock()


def set_alert_manager(manager: AlertManager) -> None:
    """Store the AlertManager instance for API access (thread-safe)."""
    global _alert_manager
    with _lock:
        _alert_manager = manager


def get_alert_manager() -> AlertManager | None:
    """Retrieve the AlertManager instance (thread-safe)."""
    with _lock:
        return _alert_manager
