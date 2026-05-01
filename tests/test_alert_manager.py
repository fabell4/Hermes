"""Tests for src/services/alert_manager.py."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from src.services.alert_manager import AlertManager
from src.services.alert_providers import AlertProvider


class MockProvider(AlertProvider):
    """Mock alert provider for testing."""

    def __init__(self):
        self.alerts_sent: list[tuple[int, str, datetime]] = []

    def send_alert(
        self,
        failure_count: int,
        last_error: str,
        timestamp: datetime,
    ) -> None:
        self.alerts_sent.append((failure_count, last_error, timestamp))


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def test_alert_manager_initialization():
    """Alert manager initializes with correct defaults."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=60)
    assert manager.failure_threshold == 3
    assert manager.cooldown_minutes == 60
    assert manager.consecutive_failures == 0
    assert manager.last_error is None
    assert manager.last_failure_time is None
    assert manager.last_alert_time is None


def test_alert_manager_raises_on_invalid_threshold():
    """Alert manager raises ValueError for invalid threshold."""
    with pytest.raises(ValueError, match="at least 1"):
        AlertManager(failure_threshold=0)


def test_alert_manager_raises_on_negative_cooldown():
    """Alert manager raises ValueError for negative cooldown."""
    with pytest.raises(ValueError, match="cannot be negative"):
        AlertManager(cooldown_minutes=-10)


def test_alert_manager_raises_on_threshold_too_high():
    """Alert manager raises ValueError for threshold above 100."""
    with pytest.raises(ValueError, match="cannot exceed 100"):
        AlertManager(failure_threshold=101)


def test_alert_manager_raises_on_cooldown_too_high():
    """Alert manager raises ValueError for cooldown above 10080 minutes (1 week)."""
    with pytest.raises(ValueError, match="cannot exceed 10080"):
        AlertManager(cooldown_minutes=10081)


def test_alert_manager_accepts_maximum_valid_threshold():
    """Alert manager accepts threshold of 100."""
    manager = AlertManager(failure_threshold=100)
    assert manager.failure_threshold == 100


def test_alert_manager_accepts_maximum_valid_cooldown():
    """Alert manager accepts cooldown of 10080 minutes (1 week)."""
    manager = AlertManager(cooldown_minutes=10080)
    assert manager.cooldown_minutes == 10080


# ---------------------------------------------------------------------------
# Provider Management
# ---------------------------------------------------------------------------


def test_add_provider_registers_provider():
    """Adding a provider makes it available."""
    manager = AlertManager()
    provider = MockProvider()
    manager.add_provider("test", provider)
    assert "test" in manager.provider_names


def test_remove_provider_deregisters():
    """Removing a provider removes it from the list."""
    manager = AlertManager()
    manager.add_provider("test", MockProvider())
    manager.remove_provider("test")
    assert "test" not in manager.provider_names


def test_clear_providers_removes_all():
    """Clearing providers removes all registered providers."""
    manager = AlertManager()
    manager.add_provider("p1", MockProvider())
    manager.add_provider("p2", MockProvider())
    manager.clear_providers()
    assert manager.provider_names == []


# ---------------------------------------------------------------------------
# Failure Recording
# ---------------------------------------------------------------------------


def test_record_failure_increments_counter():
    """Recording a failure increments the consecutive failure count."""
    manager = AlertManager(failure_threshold=3)
    manager.record_failure("Error 1")
    assert manager.consecutive_failures == 1
    manager.record_failure("Error 2")
    assert manager.consecutive_failures == 2


def test_record_failure_stores_error_and_time():
    """Recording a failure stores the error message and timestamp."""
    manager = AlertManager()
    timestamp = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)
    manager.record_failure("Network timeout", timestamp)

    assert manager.last_error == "Network timeout"
    assert manager.last_failure_time == timestamp


def test_record_failure_without_timestamp_uses_now():
    """Recording a failure without timestamp uses current time."""
    manager = AlertManager()
    before = datetime.now(timezone.utc)
    manager.record_failure("Error")
    after = datetime.now(timezone.utc)

    assert manager.last_failure_time is not None
    assert before <= manager.last_failure_time <= after


# ---------------------------------------------------------------------------
# Success Recording
# ---------------------------------------------------------------------------


def test_record_success_resets_counter():
    """Recording a success resets the consecutive failure count."""
    manager = AlertManager()
    manager.record_failure("Error 1")
    manager.record_failure("Error 2")
    assert manager.consecutive_failures == 2

    manager.record_success()
    assert manager.consecutive_failures == 0
    assert manager.last_error is None
    assert manager.last_failure_time is None


def test_record_success_when_no_failures_is_noop():
    """Recording a success when there are no failures does nothing."""
    manager = AlertManager()
    manager.record_success()  # Should not raise
    assert manager.consecutive_failures == 0


# ---------------------------------------------------------------------------
# Alert Triggering
# ---------------------------------------------------------------------------


def test_alert_triggered_at_threshold():
    """Alert is triggered when failure count reaches threshold."""
    manager = AlertManager(failure_threshold=3, cooldown_minutes=0)
    provider = MockProvider()
    manager.add_provider("test", provider)

    timestamp = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)

    manager.record_failure("Error 1", timestamp)
    manager.record_failure("Error 2", timestamp)
    assert len(provider.alerts_sent) == 0  # Not yet at threshold

    manager.record_failure("Error 3", timestamp)
    manager._wait_for_pending_alerts()  # Wait for async alert to complete
    assert len(provider.alerts_sent) == 1  # Alert triggered
    assert provider.alerts_sent[0] == (3, "Error 3", timestamp)


def test_alert_triggered_above_threshold():
    """Alert is triggered when failure count exceeds threshold."""
    manager = AlertManager(failure_threshold=2, cooldown_minutes=0)
    provider = MockProvider()
    manager.add_provider("test", provider)

    timestamp = datetime.now(timezone.utc)
    manager.record_failure("Error 1", timestamp)
    manager.record_failure("Error 2", timestamp)
    manager._wait_for_pending_alerts()  # Wait for async alert to complete
    assert len(provider.alerts_sent) == 1

    manager.record_failure("Error 3", timestamp + timedelta(seconds=1))
    manager._wait_for_pending_alerts()  # Wait for async alert to complete
    assert len(provider.alerts_sent) == 2  # Another alert


def test_no_alert_below_threshold():
    """No alert is sent when failure count is below threshold."""
    manager = AlertManager(failure_threshold=5)
    provider = MockProvider()
    manager.add_provider("test", provider)

    for i in range(4):
        manager.record_failure(f"Error {i}")

    assert len(provider.alerts_sent) == 0


# ---------------------------------------------------------------------------
# Cooldown
# ---------------------------------------------------------------------------


def test_cooldown_suppresses_alerts():
    """Alerts are suppressed during cooldown period."""
    manager = AlertManager(failure_threshold=2, cooldown_minutes=60)
    provider = MockProvider()
    manager.add_provider("test", provider)

    timestamp = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)

    # First alert
    manager.record_failure("Error 1", timestamp)
    manager.record_failure("Error 2", timestamp)
    manager._wait_for_pending_alerts()  # Wait for async alert to complete
    assert len(provider.alerts_sent) == 1

    # Within cooldown - no alert
    timestamp_within_cooldown = timestamp + timedelta(minutes=30)
    manager.record_failure("Error 3", timestamp_within_cooldown)
    manager._wait_for_pending_alerts()  # Wait (no alert expected due to cooldown)
    assert len(provider.alerts_sent) == 1  # Still only 1 alert


def test_alert_sent_after_cooldown():
    """Alert is sent again after cooldown period elapses."""
    manager = AlertManager(failure_threshold=2, cooldown_minutes=60)
    provider = MockProvider()
    manager.add_provider("test", provider)

    timestamp = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)

    # First alert
    manager.record_failure("Error 1", timestamp)
    manager.record_failure("Error 2", timestamp)
    manager._wait_for_pending_alerts()  # Wait for async alert to complete
    assert len(provider.alerts_sent) == 1

    # After cooldown - alert sent
    timestamp_after_cooldown = timestamp + timedelta(minutes=61)
    manager.record_failure("Error 3", timestamp_after_cooldown)
    manager._wait_for_pending_alerts()  # Wait for async alert to complete
    assert len(provider.alerts_sent) == 2


# ---------------------------------------------------------------------------
# Multiple Providers
# ---------------------------------------------------------------------------


def test_alert_sent_to_all_providers():
    """Alert is sent to all registered providers."""
    manager = AlertManager(failure_threshold=2, cooldown_minutes=0)
    provider1 = MockProvider()
    provider2 = MockProvider()
    manager.add_provider("p1", provider1)
    manager.add_provider("p2", provider2)

    timestamp = datetime.now(timezone.utc)
    manager.record_failure("Error 1", timestamp)
    manager.record_failure("Error 2", timestamp)
    manager._wait_for_pending_alerts()  # Wait for async alerts to complete

    assert len(provider1.alerts_sent) == 1
    assert len(provider2.alerts_sent) == 1


def test_provider_failure_does_not_stop_others():
    """If one provider fails, others still receive the alert."""
    manager = AlertManager(failure_threshold=2, cooldown_minutes=0)

    failing_provider = Mock(spec=AlertProvider)
    failing_provider.send_alert.side_effect = RuntimeError("Provider failed")

    working_provider = MockProvider()

    manager.add_provider("failing", failing_provider)
    manager.add_provider("working", working_provider)

    timestamp = datetime.now(timezone.utc)
    manager.record_failure("Error 1", timestamp)
    manager.record_failure("Error 2", timestamp)
    manager._wait_for_pending_alerts()  # Wait for async alerts to complete

    # Working provider still received alert
    assert len(working_provider.alerts_sent) == 1


def test_no_alert_when_no_providers():
    """No error occurs when alerting with no providers registered."""
    manager = AlertManager(failure_threshold=2)
    # No providers registered

    manager.record_failure("Error 1")
    manager.record_failure("Error 2")
    # Should not raise


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


def test_reset_clears_all_state():
    """Reset clears all failure tracking and alert state."""
    manager = AlertManager(failure_threshold=2, cooldown_minutes=60)
    timestamp = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)

    manager.record_failure("Error 1", timestamp)
    manager.record_failure("Error 2", timestamp)

    manager.reset()

    assert manager.consecutive_failures == 0
    assert manager.last_error is None
    assert manager.last_failure_time is None
    assert manager.last_alert_time is None


# ---------------------------------------------------------------------------
# Test Alerts
# ---------------------------------------------------------------------------


def test_send_test_alert_with_no_providers():
    """send_test_alert returns empty dict when no providers registered."""
    manager = AlertManager()
    results = manager.send_test_alert()
    assert results == {}


def test_send_test_alert_sends_to_all_providers():
    """send_test_alert sends test notification to all registered providers."""
    manager = AlertManager()
    provider1 = MockProvider()
    provider2 = MockProvider()
    manager.add_provider("p1", provider1)
    manager.add_provider("p2", provider2)

    results = manager.send_test_alert()

    assert results == {"p1": True, "p2": True}
    assert len(provider1.alerts_sent) == 1
    assert len(provider2.alerts_sent) == 1

    # Check test alert content
    count, error, _ = provider1.alerts_sent[0]
    assert count == 0
    assert error == "This is a test notification from Hermes"


def test_send_test_alert_handles_provider_failure():
    """send_test_alert reports failures but continues to other providers."""
    manager = AlertManager()
    good_provider = MockProvider()
    bad_provider = Mock(spec=AlertProvider)
    bad_provider.send_alert.side_effect = RuntimeError("Provider error")

    manager.add_provider("good", good_provider)
    manager.add_provider("bad", bad_provider)

    results = manager.send_test_alert()

    assert results == {"good": True, "bad": False}
    assert len(good_provider.alerts_sent) == 1
    bad_provider.send_alert.assert_called_once()


# ---------------------------------------------------------------------------
# H6: Multi-Provider Network Failure Scenarios (v1.1 Test Coverage Gaps)
# ---------------------------------------------------------------------------


def test_all_providers_fail_alert_completes():
    """Alert operation completes even when all providers fail."""
    import requests

    manager = AlertManager(failure_threshold=2, cooldown_minutes=0)

    provider1 = Mock(spec=AlertProvider)
    provider1.send_alert.side_effect = requests.exceptions.Timeout("Provider 1 timeout")

    provider2 = Mock(spec=AlertProvider)
    provider2.send_alert.side_effect = requests.exceptions.ConnectionError(
        "Provider 2 unreachable"
    )

    provider3 = Mock(spec=AlertProvider)
    provider3.send_alert.side_effect = RuntimeError("Provider 3 service error")

    manager.add_provider("p1", provider1)
    manager.add_provider("p2", provider2)
    manager.add_provider("p3", provider3)

    timestamp = datetime.now(timezone.utc)
    manager.record_failure("Error 1", timestamp)
    manager.record_failure("Error 2", timestamp)
    manager._wait_for_pending_alerts()  # Wait for async alerts to complete

    # All providers were attempted despite failures
    provider1.send_alert.assert_called_once()
    provider2.send_alert.assert_called_once()
    provider3.send_alert.assert_called_once()

    # Alert timestamp was still recorded
    assert manager.last_alert_time == timestamp


def test_partial_success_mixed_provider_failures(caplog):
    """When some providers fail and others succeed, successful alerts are logged."""
    import logging
    import requests
    import time

    caplog.set_level(logging.INFO)

    manager = AlertManager(failure_threshold=1, cooldown_minutes=0)

    # Two working providers
    working_provider1 = MockProvider()
    working_provider2 = MockProvider()

    # Two failing providers
    timeout_provider = Mock(spec=AlertProvider)
    timeout_provider.send_alert.side_effect = requests.exceptions.Timeout("Timeout")

    error_provider = Mock(spec=AlertProvider)
    error_provider.send_alert.side_effect = RuntimeError("Server error")

    manager.add_provider("working1", working_provider1)
    manager.add_provider("timeout", timeout_provider)
    manager.add_provider("working2", working_provider2)
    manager.add_provider("error", error_provider)

    timestamp = datetime.now(timezone.utc)
    manager.record_failure("Test error", timestamp)
    manager._wait_for_pending_alerts(timeout=10.0)  # Longer timeout
    time.sleep(0.2)  # Extra wait for async logging

    # Verify working providers received the alert
    assert len(working_provider1.alerts_sent) == 1
    assert len(working_provider2.alerts_sent) == 1

    # Verify failing providers were attempted
    timeout_provider.send_alert.assert_called_once()
    error_provider.send_alert.assert_called_once()

    # Verify logging captured successes and failures
    assert "Alert sent successfully via working1" in caplog.text
    assert "Alert sent successfully via working2" in caplog.text
    assert "Alert provider 'timeout' failed" in caplog.text
    assert "Alert provider 'error' failed" in caplog.text


def test_provider_failure_types_all_handled(caplog):
    """Different exception types from providers are all caught and logged."""
    import logging
    import requests
    import time

    caplog.set_level(logging.ERROR)

    manager = AlertManager(failure_threshold=1, cooldown_minutes=0)

    # Different failure types
    timeout_provider = Mock(spec=AlertProvider)
    timeout_provider.send_alert.side_effect = requests.exceptions.Timeout("Timeout after 30s")

    connection_provider = Mock(spec=AlertProvider)
    connection_provider.send_alert.side_effect = requests.exceptions.ConnectionError(
        "[Errno -2] Name or service not known"
    )

    http_provider = Mock(spec=AlertProvider)
    http_provider.send_alert.side_effect = requests.exceptions.HTTPError("404 Not Found")

    value_provider = Mock(spec=AlertProvider)
    value_provider.send_alert.side_effect = ValueError("Invalid configuration")

    manager.add_provider("timeout", timeout_provider)
    manager.add_provider("connection", connection_provider)
    manager.add_provider("http", http_provider)
    manager.add_provider("value", value_provider)

    timestamp = datetime.now(timezone.utc)
    manager.record_failure("Test error", timestamp)
    manager._wait_for_pending_alerts(timeout=10.0)  # Longer timeout
    time.sleep(0.2)  # Extra wait for async logging

    # All providers were attempted
    timeout_provider.send_alert.assert_called_once()
    connection_provider.send_alert.assert_called_once()
    http_provider.send_alert.assert_called_once()
    value_provider.send_alert.assert_called_once()

    # All failures logged
    assert "Alert provider 'timeout' failed" in caplog.text
    assert "Alert provider 'connection' failed" in caplog.text
    assert "Alert provider 'http' failed" in caplog.text
    assert "Alert provider 'value' failed" in caplog.text


def test_test_alert_all_providers_fail():
    """send_test_alert handles all providers failing gracefully."""
    import requests

    manager = AlertManager()

    provider1 = Mock(spec=AlertProvider)
    provider1.send_alert.side_effect = requests.exceptions.Timeout("Timeout")

    provider2 = Mock(spec=AlertProvider)
    provider2.send_alert.side_effect = RuntimeError("Error")

    manager.add_provider("p1", provider1)
    manager.add_provider("p2", provider2)

    results = manager.send_test_alert()

    assert results == {"p1": False, "p2": False}
    provider1.send_alert.assert_called_once()
    provider2.send_alert.assert_called_once()


def test_test_alert_partial_failure():
    """send_test_alert reports mixed success/failure accurately."""
    manager = AlertManager()

    working = MockProvider()
    failing = Mock(spec=AlertProvider)
    failing.send_alert.side_effect = RuntimeError("Failed")

    manager.add_provider("working", working)
    manager.add_provider("failing", failing)
    manager.add_provider("also_working", MockProvider())

    results = manager.send_test_alert()

    assert results["working"] is True
    assert results["failing"] is False
    assert results["also_working"] is True
