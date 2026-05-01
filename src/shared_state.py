"""Shared application state for API access to core components.

This module provides thread-safe access to singleton instances that need to be
shared between the main scheduler process and the API process. Currently manages
the AlertManager instance.

Thread Safety:
    All functions use an internal lock to ensure thread-safe access to shared state.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.alert_manager import AlertManager

_alert_manager: AlertManager | None = None
_lock = threading.Lock()


def set_alert_manager(manager: AlertManager) -> None:
    """
    Store the AlertManager instance for API access.

    Thread-safe setter for the global AlertManager instance. This is typically
    called during API application startup to make the alert manager available
    to API endpoints.

    Args:
        manager: The AlertManager instance to store.

    Note:
        This function is thread-safe and can be called from any thread.
    """
    global _alert_manager
    with _lock:
        _alert_manager = manager


def get_alert_manager() -> AlertManager | None:
    """
    Retrieve the AlertManager instance.

    Thread-safe getter for the global AlertManager instance. API endpoints
    use this to access the alert manager for sending test notifications.

    Returns:
        AlertManager | None: The AlertManager instance if set, None otherwise.

    Note:
        This function is thread-safe and can be called from any thread.
    """
    with _lock:
        return _alert_manager
