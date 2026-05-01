"""Integration tests — end-to-end flows for key Hermes subsystems."""
# pylint: disable=missing-function-docstring

import json
import threading
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.exporters.csv_exporter import CSVExporter
from src.exporters.sqlite_exporter import SQLiteExporter
from src.models.speed_result import SpeedResult
from src.result_dispatcher import ResultDispatcher
from src.services.alert_manager import AlertManager
from src.services.alert_providers import AlertProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    download: float = 100.0,
    upload: float = 50.0,
    ping: float = 10.0,
) -> SpeedResult:
    """Create a SpeedResult with default test values."""
    return SpeedResult(
        timestamp=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
        download_mbps=download,
        upload_mbps=upload,
        ping_ms=ping,
        server_name="Test ISP",
        server_location="Test City, DE",
        server_id=1234,
    )


class SentinelProvider(AlertProvider):
    """Alert provider that records received alerts for assertions."""

    def __init__(self):
        self.received: list[dict] = []
        self._event = threading.Event()

    def send_alert(
        self, failure_count: int, last_error: str, timestamp: datetime
    ) -> None:
        self.received.append(
            {
                "failure_count": failure_count,
                "error": last_error,
                "timestamp": timestamp,
            }
        )
        self._event.set()

    def wait_for_alert(self, timeout: float = 5.0) -> bool:
        """Block until an alert is received or timeout expires."""
        result = self._event.wait(timeout=timeout)
        self._event.clear()
        return result


# ---------------------------------------------------------------------------
# Integration: speedtest → export → dispatch lifecycle
# ---------------------------------------------------------------------------


def test_speedtest_to_csv_export_lifecycle(tmp_path):
    """End-to-end: a SpeedResult flows from the runner mock through to CSV on disk."""
    csv_path = tmp_path / "results.csv"
    exporter = CSVExporter(path=csv_path)
    dispatcher = ResultDispatcher()
    dispatcher.add_exporter("csv", exporter)

    with patch("src.services.speedtest_runner.subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            stdout=json.dumps(
                {
                    "download": {"bandwidth": int(250.5 * 125000)},
                    "upload": {"bandwidth": int(45.2 * 125000)},
                    "ping": {"latency": 12.3, "jitter": 2.1},
                    "server": {
                        "name": "Test ISP",
                        "location": "Test City",
                        "country": "DE",
                        "id": 1234,
                    },
                    "isp": "Test ISP",
                }
            ),
            returncode=0,
        )
        from src.services.speedtest_runner import SpeedtestRunner

        runner = SpeedtestRunner("/usr/bin/speedtest")
        measured = runner.run()

    dispatcher.dispatch(measured)

    assert csv_path.exists()
    content = csv_path.read_text(encoding="utf-8")
    assert "download_mbps" in content
    assert str(round(measured.download_mbps, 1)) in content


def test_speedtest_to_sqlite_export_lifecycle(tmp_path):
    """End-to-end: a SpeedResult flows through the dispatcher into SQLite storage."""
    db_path = tmp_path / "results.db"
    exporter = SQLiteExporter(path=db_path)
    dispatcher = ResultDispatcher()
    dispatcher.add_exporter("sqlite", exporter)

    result = _make_result(download=120.0, upload=30.0, ping=5.0)
    dispatcher.dispatch(result)

    # Verify the result was stored
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT download_mbps, upload_mbps FROM results").fetchall()

    assert len(rows) == 1
    assert rows[0][0] == pytest.approx(120.0)
    assert rows[0][1] == pytest.approx(30.0)


def test_multi_exporter_dispatch_lifecycle(tmp_path):
    """End-to-end: result dispatches to both CSV and SQLite simultaneously."""
    csv_path = tmp_path / "results.csv"
    db_path = tmp_path / "results.db"

    dispatcher = ResultDispatcher()
    dispatcher.add_exporter("csv", CSVExporter(path=csv_path))
    dispatcher.add_exporter("sqlite", SQLiteExporter(path=db_path))

    result = _make_result()
    dispatcher.dispatch(result)

    assert csv_path.exists()
    assert db_path.exists()

    import sqlite3

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    assert count == 1


# ---------------------------------------------------------------------------
# Integration: alert flow — failure to recovery
# ---------------------------------------------------------------------------


def test_alert_lifecycle_failure_then_recovery():
    """End-to-end: consecutive failures trigger alert; success resets the counter."""
    provider = SentinelProvider()
    manager = AlertManager(failure_threshold=3, cooldown_minutes=0)
    manager.add_provider("sentinel", provider)

    ts = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Two failures — not enough to trigger
    manager.record_failure("Error 1", ts)
    manager.record_failure("Error 2", ts)
    manager._wait_for_pending_alerts(timeout=10.0)
    assert len(provider.received) == 0

    # Third failure — triggers alert
    manager.record_failure("Error 3", ts)
    assert provider.wait_for_alert(timeout=10.0), "Alert was not received in time"
    assert len(provider.received) == 1
    assert provider.received[0]["failure_count"] == 3

    # Recovery — resets counter
    manager.record_success()
    assert manager.consecutive_failures == 0

    # New failure sequence starts fresh
    manager.record_failure("New Error", ts)
    manager._wait_for_pending_alerts(timeout=10.0)
    # Still only 1 alert (counter was reset, threshold not reached again)
    assert len(provider.received) == 1


def test_alert_cooldown_prevents_repeated_alerts():
    """End-to-end: alert cooldown suppresses rapid re-alerting."""
    from datetime import timedelta

    provider = SentinelProvider()
    manager = AlertManager(failure_threshold=1, cooldown_minutes=60)
    manager.add_provider("sentinel", provider)

    ts = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)

    # First failure — triggers alert
    manager.record_failure("Error 1", ts)
    assert provider.wait_for_alert(timeout=10.0), "First alert not received in time"
    assert len(provider.received) == 1

    # Second failure immediately after — cooldown suppresses
    ts2 = ts + timedelta(minutes=5)  # Only 5 minutes later
    manager.record_failure("Error 2", ts2)
    manager._wait_for_pending_alerts(timeout=10.0)
    assert len(provider.received) == 1  # Still only 1 alert

    # Third failure after cooldown expires — triggers again
    ts3 = ts + timedelta(minutes=65)  # 65 minutes later
    manager.record_failure("Error 3", ts3)
    assert provider.wait_for_alert(timeout=10.0), "Second alert not received in time"
    assert len(provider.received) == 2  # Now 2 alerts


# ---------------------------------------------------------------------------
# Integration: runtime config persistence across restart
# ---------------------------------------------------------------------------


def test_runtime_config_persists_and_survives_reload(tmp_path, monkeypatch):
    """End-to-end: changes saved to runtime_config.json are read back correctly."""
    import src.runtime_config as rc

    config_path = tmp_path / "data" / "runtime_config.json"
    monkeypatch.setattr(rc, "RUNTIME_CONFIG_PATH", config_path)
    monkeypatch.setattr(rc, "_config_cache", None)
    monkeypatch.setattr(rc, "_config_mtime", 0)

    # Simulate saving settings
    rc.set_interval_minutes(45)
    rc.set_enabled_exporters(["csv", "sqlite"])
    rc.set_scheduler_paused(True)

    # Simulate restart by resetting the module cache
    monkeypatch.setattr(rc, "_config_cache", None)
    monkeypatch.setattr(rc, "_config_mtime", 0)

    # Read back as if a new process started
    assert rc.get_interval_minutes(60) == 45
    assert rc.get_enabled_exporters([]) == ["csv", "sqlite"]
    assert rc.get_scheduler_paused() is True


def test_runtime_config_run_trigger_lifecycle(tmp_path, monkeypatch):
    """End-to-end: trigger file is created then consumed exactly once."""
    import src.runtime_config as rc

    trigger_path = tmp_path / "data" / ".run_trigger"
    monkeypatch.setattr(rc, "RUN_TRIGGER_PATH", trigger_path)
    monkeypatch.setattr(
        rc, "RUNTIME_CONFIG_PATH", tmp_path / "data" / "runtime_config.json"
    )

    # No trigger initially
    assert rc.consume_run_trigger() is False

    # Create trigger
    rc.trigger_run()
    assert trigger_path.exists()

    # Consume — returns True and removes file
    assert rc.consume_run_trigger() is True
    assert not trigger_path.exists()

    # Subsequent consume — returns False
    assert rc.consume_run_trigger() is False


# ---------------------------------------------------------------------------
# Integration: run_once with alert manager — success and failure paths
# ---------------------------------------------------------------------------


def test_run_once_records_success_with_alert_manager(monkeypatch):
    """run_once calls alert_manager.record_success when speedtest succeeds."""
    import src.main as main_module

    service = MagicMock()
    dispatcher = MagicMock()
    alert_manager = MagicMock()

    result = _make_result()
    service.run.return_value = result

    monkeypatch.setattr(main_module.runtime_config, "mark_running", lambda: None)
    monkeypatch.setattr(main_module.runtime_config, "mark_done", lambda: None)
    monkeypatch.setattr(main_module.runtime_config, "set_last_run_at", lambda t: None)

    from src.main import run_once

    run_once(service, dispatcher, alert_manager)

    alert_manager.record_success.assert_called_once()
    alert_manager.record_failure.assert_not_called()


def test_run_once_records_failure_with_alert_manager(monkeypatch):
    """run_once calls alert_manager.record_failure when speedtest fails."""
    import src.main as main_module

    service = MagicMock()
    dispatcher = MagicMock()
    alert_manager = MagicMock()

    service.run.side_effect = RuntimeError("network timeout")

    monkeypatch.setattr(main_module.runtime_config, "mark_running", lambda: None)
    monkeypatch.setattr(main_module.runtime_config, "mark_done", lambda: None)
    monkeypatch.setattr(main_module.config, "APP_ENV", "production")

    from src.main import run_once

    run_once(service, dispatcher, alert_manager)

    alert_manager.record_failure.assert_called_once()
    call_args = alert_manager.record_failure.call_args[0]
    assert "network timeout" in call_args[0]
    alert_manager.record_success.assert_not_called()
