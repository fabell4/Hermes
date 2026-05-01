"""AlertManager — tracks consecutive failures and triggers alerts with cooldown."""

from __future__ import annotations

import concurrent.futures
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from src.services.alert_providers import AlertProvider

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Manages alerting for consecutive speedtest failures.

    Features:
    - Tracks consecutive failure count
    - Triggers alerts after N consecutive failures
    - Enforces cooldown period between alerts
    - Supports multiple alert providers
    - Sends alerts asynchronously to avoid blocking speedtest runs
    """

    # Class-level thread pool for async alert sending (shared across all instances)
    _executor: ClassVar[concurrent.futures.ThreadPoolExecutor | None] = None

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_minutes: int = 60,
    ) -> None:
        """
        Initialize the alert manager.

        Args:
            failure_threshold: Number of consecutive failures before alerting
            cooldown_minutes: Minimum minutes between alerts
        """
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if cooldown_minutes < 0:
            raise ValueError("cooldown_minutes cannot be negative")

        self.failure_threshold = failure_threshold
        self.cooldown_minutes = cooldown_minutes

        self._consecutive_failures = 0
        self._last_error: str | None = None
        self._last_failure_time: datetime | None = None
        self._last_alert_time: datetime | None = None

        self._providers: dict[str, AlertProvider] = {}

        # Initialize thread pool (lazy, only once)
        if AlertManager._executor is None:
            AlertManager._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=3,
                thread_name_prefix="alert-sender"
            )
            logger.debug("Alert thread pool initialized (max_workers=3)")

    def add_provider(self, name: str, provider: AlertProvider) -> None:
        """Register an alert provider under a given name."""
        self._providers[name] = provider
        logger.info("Registered alert provider: %s", name)

    def remove_provider(self, name: str) -> None:
        """Unregister an alert provider by name."""
        if name in self._providers:
            del self._providers[name]
            logger.info("Removed alert provider: %s", name)

    def clear_providers(self) -> None:
        """Remove all registered alert providers."""
        names = list(self._providers.keys())
        self._providers.clear()
        logger.info("Cleared all alert providers: %s", names)

    def record_success(self) -> None:
        """Record a successful speedtest run, resetting the failure counter."""
        if self._consecutive_failures > 0:
            logger.info(
                "Speedtest succeeded after %d consecutive failure(s) — resetting counter.",
                self._consecutive_failures,
            )
            self._consecutive_failures = 0
            self._last_error = None
            self._last_failure_time = None

    def record_failure(self, error: str, timestamp: datetime | None = None) -> None:
        """
        Record a failed speedtest run and trigger alerts if threshold is reached.

        Args:
            error: Error message from the failed attempt
            timestamp: When the failure occurred (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        self._consecutive_failures += 1
        self._last_error = error
        self._last_failure_time = timestamp

        logger.warning(
            "Speedtest failure recorded (%d consecutive): %s",
            self._consecutive_failures,
            error,
        )

        # Check if we should trigger an alert
        if self._consecutive_failures >= self.failure_threshold:
            self._maybe_send_alert(timestamp)

    def _send_alert_async(
        self,
        name: str,
        provider: AlertProvider,
        failure_count: int,
        last_error: str,
        timestamp: datetime,
    ) -> None:
        """Send alert in background thread (called by thread pool)."""
        try:
            provider.send_alert(
                failure_count=failure_count,
                last_error=last_error,
                timestamp=timestamp,
            )
            logger.info("Alert sent successfully via %s", name)
        except Exception as e:  # pylint: disable=broad-exception-caught  # NOSONAR
            logger.error("Alert provider '%s' failed: %s", name, e, exc_info=True)

    def _maybe_send_alert(self, timestamp: datetime) -> None:
        """Send alert if cooldown period has elapsed."""
        # Check cooldown
        if self._last_alert_time is not None:
            cooldown_elapsed = timestamp - self._last_alert_time
            cooldown_required = timedelta(minutes=self.cooldown_minutes)

            if cooldown_elapsed < cooldown_required:
                remaining = cooldown_required - cooldown_elapsed
                logger.info(
                    "Alert suppressed — cooldown active for %s more seconds.",
                    int(remaining.total_seconds()),
                )
                return

        # Send alert via all registered providers
        if not self._providers:
            logger.warning(
                "Alert triggered (%d consecutive failures) but no providers registered.",
                self._consecutive_failures,
            )
            return

        logger.warning(
            "Alert triggered: %d consecutive failures — sending to %d provider(s).",
            self._consecutive_failures,
            len(self._providers),
        )

        # Submit all alerts to thread pool (non-blocking)
        if AlertManager._executor:
            for name, provider in self._providers.items():
                AlertManager._executor.submit(
                    self._send_alert_async,
                    name,
                    provider,
                    self._consecutive_failures,
                    self._last_error or "Unknown error",
                    timestamp,
                )
            logger.debug("Submitted %d alert(s) to thread pool", len(self._providers))
        else:
            # Fallback to synchronous (should never happen, but defensive)
            logger.warning("Thread pool not initialized, sending alerts synchronously")
            for name, provider in self._providers.items():
                try:
                    provider.send_alert(
                        failure_count=self._consecutive_failures,
                        last_error=self._last_error or "Unknown error",
                        timestamp=timestamp,
                    )
                    logger.info("Alert sent successfully via %s", name)
                except Exception as e:  # pylint: disable=broad-exception-caught  # NOSONAR
                    logger.error("Alert provider '%s' failed: %s", name, e, exc_info=True)

        # Update last alert time immediately (don't wait for delivery)
        self._last_alert_time = timestamp

    @property
    def consecutive_failures(self) -> int:
        """Current count of consecutive failures."""
        return self._consecutive_failures

    @property
    def last_error(self) -> str | None:
        """Error message from the most recent failure."""
        return self._last_error

    @property
    def last_failure_time(self) -> datetime | None:
        """Timestamp of the most recent failure."""
        return self._last_failure_time

    @property
    def last_alert_time(self) -> datetime | None:
        """Timestamp of the most recent alert sent."""
        return self._last_alert_time

    @property
    def provider_names(self) -> list[str]:
        """Names of all registered alert providers."""
        return list(self._providers.keys())

    def send_test_alert(self) -> dict[str, bool]:
        """Send a test alert to all registered providers.

        Returns:
            Dictionary mapping provider names to success status.
        """
        if not self._providers:
            logger.warning("Test alert requested but no providers registered.")
            return {}

        logger.info(
            "Sending test alert to %d provider(s): %s",
            len(self._providers),
            ", ".join(self._providers.keys()),
        )

        results: dict[str, bool] = {}
        timestamp = datetime.now(timezone.utc)

        for name, provider in self._providers.items():
            try:
                provider.send_alert(
                    failure_count=0,
                    last_error="This is a test notification from Hermes",
                    timestamp=timestamp,
                )
                logger.info("Test alert sent successfully via %s", name)
                results[name] = True
            except Exception as e:  # pylint: disable=broad-exception-caught  # NOSONAR
                logger.error("Test alert failed via %s: %s", name, e, exc_info=True)
                results[name] = False

        return results

    def _wait_for_pending_alerts(self, timeout: float = 5.0) -> None:
        """Wait for all pending async alerts to complete (for testing).
        
        Args:
            timeout: Maximum time to wait in seconds
        """
        if AlertManager._executor:
            # Submit a no-op task and wait for it to complete
            # This ensures all previously submitted tasks are done
            future = AlertManager._executor.submit(lambda: None)
            try:
                future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                logger.warning("Timeout waiting for pending alerts to complete")

    def reset(self) -> None:
        """Reset all failure tracking and alert state (for testing)."""
        self._consecutive_failures = 0
        self._last_error = None
        self._last_failure_time = None
        self._last_alert_time = None
        logger.info("Alert manager state reset.")
