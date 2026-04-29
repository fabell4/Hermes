"""Integration tests for scheduler persistence across restarts.

These tests verify that when the scheduler interval is changed and persisted
to runtime_config.json, a simulated application restart correctly loads and
applies the persisted interval.
"""

# pylint: disable=missing-function-docstring

import json
from unittest.mock import MagicMock

import pytest

import src.runtime_config as runtime_config
from src.main import build_scheduler, update_schedule


@pytest.fixture()
def config_path(tmp_path, monkeypatch):
    """Redirect RUNTIME_CONFIG_PATH to a temporary directory for each test."""
    path = tmp_path / "data" / "runtime_config.json"
    monkeypatch.setattr(runtime_config, "RUNTIME_CONFIG_PATH", path)
    return path


# ---------------------------------------------------------------------------
# Scheduler persistence integration tests
# ---------------------------------------------------------------------------


def test_scheduler_loads_persisted_interval_on_restart(config_path, monkeypatch):
    """
    Integration test: verify scheduler loads persisted interval after restart.

    Scenario:
    1. Scheduler starts with default interval (60 minutes)
    2. Interval is changed to 30 minutes and persisted
    3. Scheduler is stopped (simulating app shutdown)
    4. New scheduler is created (simulating app restart)
    5. New scheduler should use the persisted 30-minute interval
    """
    # Mock the speedtest service and dependencies
    mock_service = MagicMock()
    mock_dispatcher = MagicMock()
    mock_alert_manager = MagicMock()

    # Mock the default config interval
    import src.config as config_module

    monkeypatch.setattr(config_module, "SPEEDTEST_INTERVAL_MINUTES", 60)

    # Phase 1: Initial scheduler with default interval
    scheduler1 = build_scheduler(mock_service, mock_dispatcher, mock_alert_manager)
    scheduler1.start()

    job1 = scheduler1.get_job("speedtest_run")
    assert job1 is not None
    # Interval should be 60 minutes (3600 seconds)
    assert job1.trigger.interval.total_seconds() == 3600

    # Phase 2: Update interval to 30 minutes and persist
    runtime_config.save({"interval_minutes": 30})
    update_schedule(scheduler1, 30)

    job1_updated = scheduler1.get_job("speedtest_run")
    assert job1_updated.trigger.interval.total_seconds() == 1800

    # Verify persistence
    persisted_data = json.loads(config_path.read_text(encoding="utf-8"))
    assert persisted_data["interval_minutes"] == 30

    # Phase 3: Stop scheduler (simulate app shutdown)
    scheduler1.shutdown(wait=False)

    # Phase 4: Create new scheduler (simulate app restart)
    # The application should load the persisted interval
    persisted_interval = runtime_config.get_interval_minutes(default=60)
    assert persisted_interval == 30

    scheduler2 = build_scheduler(mock_service, mock_dispatcher, mock_alert_manager)
    # Manually apply the persisted interval (this is what main() does)
    update_schedule(scheduler2, persisted_interval)
    scheduler2.start()

    # Verify new scheduler uses persisted interval
    job2 = scheduler2.get_job("speedtest_run")
    assert job2 is not None
    assert job2.trigger.interval.total_seconds() == 1800

    scheduler2.shutdown(wait=False)


def test_scheduler_uses_default_when_no_persisted_interval(config_path, monkeypatch):
    """
    Integration test: verify scheduler uses default interval when no persisted value exists.
    """
    # Mock dependencies
    mock_service = MagicMock()
    mock_dispatcher = MagicMock()
    mock_alert_manager = MagicMock()

    # Mock the default config interval
    import src.config as config_module

    monkeypatch.setattr(config_module, "SPEEDTEST_INTERVAL_MINUTES", 45)

    # Ensure no persisted config exists
    assert not config_path.exists()

    # Create scheduler — should use default
    persisted_interval = runtime_config.get_interval_minutes(default=45)
    assert persisted_interval == 45

    scheduler = build_scheduler(mock_service, mock_dispatcher, mock_alert_manager)
    update_schedule(scheduler, persisted_interval)
    scheduler.start()

    job = scheduler.get_job("speedtest_run")
    assert job is not None
    # 45 minutes = 2700 seconds
    assert job.trigger.interval.total_seconds() == 2700

    scheduler.shutdown(wait=False)


def test_scheduler_persists_multiple_interval_changes(config_path, monkeypatch):
    """
    Integration test: verify multiple interval changes are correctly persisted.
    """
    mock_service = MagicMock()
    mock_dispatcher = MagicMock()
    mock_alert_manager = MagicMock()

    import src.config as config_module

    monkeypatch.setattr(config_module, "SPEEDTEST_INTERVAL_MINUTES", 60)

    scheduler = build_scheduler(mock_service, mock_dispatcher, mock_alert_manager)
    scheduler.start()

    # Change 1: 60 -> 15
    runtime_config.save({"interval_minutes": 15})
    update_schedule(scheduler, 15)
    assert scheduler.get_job("speedtest_run").trigger.interval.total_seconds() == 900

    # Change 2: 15 -> 90
    runtime_config.save({"interval_minutes": 90})
    update_schedule(scheduler, 90)
    assert scheduler.get_job("speedtest_run").trigger.interval.total_seconds() == 5400

    # Change 3: 90 -> 5
    runtime_config.save({"interval_minutes": 5})
    update_schedule(scheduler, 5)
    assert scheduler.get_job("speedtest_run").trigger.interval.total_seconds() == 300

    # Verify final persisted value
    persisted_data = json.loads(config_path.read_text(encoding="utf-8"))
    assert persisted_data["interval_minutes"] == 5

    # Simulate restart
    scheduler.shutdown(wait=False)

    persisted_interval = runtime_config.get_interval_minutes(default=60)
    assert persisted_interval == 5

    scheduler2 = build_scheduler(mock_service, mock_dispatcher, mock_alert_manager)
    update_schedule(scheduler2, persisted_interval)
    scheduler2.start()

    assert scheduler2.get_job("speedtest_run").trigger.interval.total_seconds() == 300

    scheduler2.shutdown(wait=False)


def test_scheduler_persists_across_restart_with_other_config(config_path, monkeypatch):
    """
    Integration test: verify interval persistence works alongside other config values.
    """
    mock_service = MagicMock()
    mock_dispatcher = MagicMock()
    mock_alert_manager = MagicMock()

    import src.config as config_module

    monkeypatch.setattr(config_module, "SPEEDTEST_INTERVAL_MINUTES", 60)

    # Persist interval along with other config
    runtime_config.save(
        {
            "interval_minutes": 20,
            "enabled_exporters": ["csv", "prometheus"],
            "scheduler_paused": False,
        }
    )

    # Load persisted interval
    persisted_interval = runtime_config.get_interval_minutes(default=60)
    assert persisted_interval == 20

    # Create scheduler with persisted interval
    scheduler = build_scheduler(mock_service, mock_dispatcher, mock_alert_manager)
    update_schedule(scheduler, persisted_interval)
    scheduler.start()

    job = scheduler.get_job("speedtest_run")
    assert job.trigger.interval.total_seconds() == 1200

    # Verify other config values are preserved
    config_data = runtime_config.load()
    assert config_data["enabled_exporters"] == ["csv", "prometheus"]
    assert config_data["scheduler_paused"] is False

    scheduler.shutdown(wait=False)


def test_update_schedule_reschedules_job_with_new_interval(monkeypatch):
    """
    Unit test: verify update_schedule correctly reschedules with new interval.
    """
    mock_service = MagicMock()
    mock_dispatcher = MagicMock()
    mock_alert_manager = MagicMock()

    scheduler = build_scheduler(mock_service, mock_dispatcher, mock_alert_manager)
    scheduler.start()

    # Initial interval check
    job = scheduler.get_job("speedtest_run")
    original_trigger = job.trigger

    # Update to new interval
    update_schedule(scheduler, 45)

    # Verify job was rescheduled
    job_after = scheduler.get_job("speedtest_run")
    assert job_after is not None
    assert job_after.trigger.interval.total_seconds() == 2700
    assert job_after.trigger is not original_trigger  # New trigger instance

    scheduler.shutdown(wait=False)
