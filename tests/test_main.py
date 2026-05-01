"""Tests for current SpeedtestRunner and main.run_once behavior."""
# pylint: disable=missing-function-docstring,protected-access

import json
import logging
import subprocess
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

import src.main as main_module
from src.exporters.base_exporter import BaseExporter
from src.exporters.loki_exporter import LokiExporter
from src.main import (
    build_alert_manager,
    build_dispatcher,
    build_scheduler,
    run_once,
    update_alert_providers,
    update_exporters,
    _build_health_status,
    _handle_scheduler_pause_toggle,
    _poll_once,
    _validate_environment,
    _validate_loki_endpoint,
)
from src.models.speed_result import SpeedResult
from src.result_dispatcher import DispatchError
from src.services.speedtest_runner import SpeedtestRunner


class DummyExporter(BaseExporter):
    """Minimal no-op exporter for test isolation."""

    def export(self, result: SpeedResult) -> None:
        return None


def _raise_loki_url_required() -> BaseExporter:
    raise ValueError("Loki URL is required")


def _make_mock_speedtest_json() -> str:
    """Return a mock JSON response from Ookla speedtest CLI."""
    return json.dumps(
        {
            "download": {"bandwidth": 12500000},  # 100 Mbps in bytes/s
            "upload": {"bandwidth": 6250000},  # 50 Mbps in bytes/s
            "ping": {"latency": 12.5, "jitter": 2.3},
            "server": {
                "name": "Test ISP",
                "location": "Test City",
                "country": "DE",
                "id": 1234,
            },
            "isp": "Test ISP",
        }
    )


@patch("src.services.speedtest_runner.subprocess.run")
def test_speedtest_runner_run_success(mock_run):
    mock_result = Mock()
    mock_result.stdout = _make_mock_speedtest_json()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    result = SpeedtestRunner("/usr/bin/speedtest").run()

    assert result.download_mbps == pytest.approx(100.0)
    assert result.upload_mbps == pytest.approx(50.0)
    assert result.ping_ms == pytest.approx(12.5)
    assert result.server_name == "Test ISP"
    assert result.server_location == "Test City, DE"
    assert result.server_id == 1234
    assert result.jitter_ms == pytest.approx(2.3)


@patch("src.main.runtime_config.mark_running")
@patch("src.main.runtime_config.mark_done")
def test_run_once_dispatches_result(mock_done, mock_running):
    service = MagicMock()
    dispatcher = MagicMock()
    result = SpeedResult(
        timestamp=datetime.now(timezone.utc),
        download_mbps=100.0,
        upload_mbps=50.0,
        ping_ms=10.0,
        server_name="Test ISP",
        server_location="Test City, DE",
        server_id=1234,
    )
    service.run.return_value = result

    run_once(service, dispatcher)

    service.run.assert_called_once()
    dispatcher.dispatch.assert_called_once_with(result)
    mock_running.assert_called_once()
    mock_done.assert_called_once()


@patch("src.main.runtime_config.mark_running")
@patch("src.main.runtime_config.mark_done")
def test_run_once_handles_runner_error_without_dispatch(mock_done, mock_running):
    service = MagicMock()
    dispatcher = MagicMock()
    service.run.side_effect = RuntimeError("network error")

    run_once(service, dispatcher)

    service.run.assert_called_once()
    dispatcher.dispatch.assert_not_called()
    mock_running.assert_called_once()
    mock_done.assert_called_once()


@patch("src.main.runtime_config.mark_running")
@patch("src.main.runtime_config.mark_done")
def test_run_once_logs_dispatch_errors(mock_done, _mock_running, caplog):
    service = MagicMock()
    dispatcher = MagicMock()
    result = SpeedResult(
        timestamp=datetime.now(timezone.utc),
        download_mbps=10.0,
        upload_mbps=5.0,
        ping_ms=20.0,
        server_name="ISP",
        server_location="City, DE",
        server_id=1,
    )
    service.run.return_value = result
    dispatcher.dispatch.side_effect = DispatchError({"csv": OSError("disk full")})

    with caplog.at_level(logging.WARNING):
        run_once(service, dispatcher)

    assert "disk full" in caplog.text
    mock_done.assert_called_once()


@patch("src.main.runtime_config.mark_running")
@patch("src.main.runtime_config.mark_done")
def test_run_once_mark_done_called_even_on_runner_error(mock_done, _mock_running):
    """Ensure mark_done is always called via the finally block."""
    service = MagicMock()
    dispatcher = MagicMock()
    service.run.side_effect = RuntimeError("fail")

    run_once(service, dispatcher)

    mock_done.assert_called_once()


def test_build_scheduler_returns_scheduler_with_job(monkeypatch):
    monkeypatch.setattr(main_module.config, "SPEEDTEST_INTERVAL_MINUTES", 60)
    service = MagicMock()
    dispatcher = MagicMock()

    scheduler = build_scheduler(service, dispatcher)

    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "speedtest_run"


def test_build_dispatcher_skips_loki_on_init_error(monkeypatch, caplog):
    monkeypatch.setattr(
        main_module.runtime_config,
        "get_enabled_exporters",
        lambda default: ["csv", "loki"],
    )
    monkeypatch.setattr(
        main_module,
        "EXPORTER_REGISTRY",
        {
            "csv": DummyExporter,
            "loki": _raise_loki_url_required,
        },
    )

    with caplog.at_level(logging.WARNING):
        dispatcher = build_dispatcher()

    assert dispatcher.exporter_names == ["csv"]
    assert "could not be initialized" in caplog.text


# ---------------------------------------------------------------------------
# SpeedtestRunner — exception paths
# ---------------------------------------------------------------------------


@patch("src.services.speedtest_runner.subprocess.run")
def test_speedtest_runner_raises_on_timeout(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["speedtest"], timeout=120)
    with pytest.raises(RuntimeError, match="timed out"):
        SpeedtestRunner("/usr/bin/speedtest").run()


@patch("src.services.speedtest_runner.subprocess.run")
def test_speedtest_runner_raises_on_process_error(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=["speedtest"], stderr="network error"
    )
    with pytest.raises(RuntimeError, match="Speedtest CLI failed"):
        SpeedtestRunner("/usr/bin/speedtest").run()


@patch("src.services.speedtest_runner.subprocess.run")
def test_speedtest_runner_raises_on_json_decode_error(mock_run):
    mock_result = Mock()
    mock_result.stdout = "not valid json"
    mock_result.returncode = 0
    mock_run.return_value = mock_result
    with pytest.raises(RuntimeError, match="Failed to parse"):
        SpeedtestRunner("/usr/bin/speedtest").run()


@patch("src.services.speedtest_runner.subprocess.run")
def test_speedtest_runner_raises_on_file_not_found(mock_run):
    mock_run.side_effect = FileNotFoundError("speedtest not found")
    with pytest.raises(RuntimeError, match="not found"):
        SpeedtestRunner("/usr/bin/speedtest").run()


@patch("src.services.speedtest_runner.subprocess.run")
def test_speedtest_runner_retries_once_on_transient_failure(mock_run):
    """First attempt raises; second attempt succeeds — run() should return result."""
    # First call fails
    mock_run.side_effect = [
        subprocess.TimeoutExpired(cmd=["speedtest"], timeout=120),
        Mock(stdout=_make_mock_speedtest_json(), returncode=0),
    ]

    result = SpeedtestRunner("/usr/bin/speedtest").run()
    assert result.download_mbps == pytest.approx(100.0)
    assert result.upload_mbps == pytest.approx(50.0)
    assert mock_run.call_count == 2


@patch("src.services.speedtest_runner.subprocess.run")
def test_speedtest_runner_raises_after_two_failures(mock_run):
    """Both attempts fail — run() should raise RuntimeError."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["speedtest"], timeout=120)
    with pytest.raises(RuntimeError, match="timed out"):
        SpeedtestRunner("/usr/bin/speedtest").run()
    assert mock_run.call_count == 2


# ---------------------------------------------------------------------------
# _poll_once
# ---------------------------------------------------------------------------


def _make_poll_deps():
    """Return mock scheduler, dispatcher, service, alert_manager for _poll_once tests."""
    return MagicMock(), MagicMock(), MagicMock(), MagicMock()


def test_poll_once_no_changes_returns_same_state(monkeypatch):
    scheduler, dispatcher, service, alert_manager = _make_poll_deps()
    monkeypatch.setattr(
        main_module.runtime_config, "get_interval_minutes", lambda default: 60
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_enabled_exporters", lambda default: ["csv"]
    )
    monkeypatch.setattr(
        main_module.runtime_config, "consume_run_trigger", lambda: False
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_scheduler_paused", lambda: False
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_alert_config", lambda: {"enabled": False}
    )
    monkeypatch.setattr(main_module.runtime_config, "set_next_run_at", lambda t: None)

    interval, exporters, paused, _, _ = _poll_once(
        scheduler, dispatcher, service, alert_manager, 60, ["csv"]
    )

    assert interval == 60
    assert exporters == ["csv"]
    assert paused is False
    scheduler.reschedule_job.assert_not_called()
    dispatcher.clear.assert_not_called()
    service.run.assert_not_called()


def test_poll_once_interval_changed_calls_update_schedule(monkeypatch):
    scheduler, dispatcher, service, alert_manager = _make_poll_deps()
    monkeypatch.setattr(
        main_module.runtime_config, "get_interval_minutes", lambda default: 30
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_enabled_exporters", lambda default: ["csv"]
    )
    monkeypatch.setattr(
        main_module.runtime_config, "consume_run_trigger", lambda: False
    )
    monkeypatch.setattr(
        main_module.runtime_config, "set_interval_minutes", lambda m: None
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_scheduler_paused", lambda: False
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_alert_config", lambda: {"enabled": False}
    )
    monkeypatch.setattr(main_module.runtime_config, "set_next_run_at", lambda t: None)

    interval, _, _, _, _ = _poll_once(
        scheduler, dispatcher, service, alert_manager, 60, ["csv"]
    )

    assert interval == 30
    scheduler.reschedule_job.assert_called_once()


def test_poll_once_exporters_changed_calls_update_exporters(monkeypatch):
    scheduler, dispatcher, service, alert_manager = _make_poll_deps()
    monkeypatch.setattr(
        main_module.runtime_config, "get_interval_minutes", lambda default: 60
    )
    monkeypatch.setattr(
        main_module.runtime_config,
        "get_enabled_exporters",
        lambda default: ["csv", "prometheus"],
    )
    monkeypatch.setattr(
        main_module.runtime_config, "consume_run_trigger", lambda: False
    )
    monkeypatch.setattr(
        main_module.runtime_config, "set_enabled_exporters", lambda e: None
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_scheduler_paused", lambda: False
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_alert_config", lambda: {"enabled": False}
    )
    monkeypatch.setattr(main_module.runtime_config, "set_next_run_at", lambda t: None)
    monkeypatch.setattr(
        main_module,
        "EXPORTER_REGISTRY",
        {
            "csv": DummyExporter,
            "prometheus": DummyExporter,
        },
    )

    _, exporters, _, _, _ = _poll_once(
        scheduler, dispatcher, service, alert_manager, 60, ["csv"]
    )

    assert sorted(exporters) == ["csv", "prometheus"]
    dispatcher.clear.assert_called_once()


def test_poll_once_trigger_fires_calls_run_once(monkeypatch):
    scheduler, dispatcher, service, alert_manager = _make_poll_deps()
    monkeypatch.setattr(
        main_module.runtime_config, "get_interval_minutes", lambda default: 60
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_enabled_exporters", lambda default: ["csv"]
    )
    monkeypatch.setattr(main_module.runtime_config, "consume_run_trigger", lambda: True)
    monkeypatch.setattr(main_module.runtime_config, "mark_running", lambda: None)
    monkeypatch.setattr(main_module.runtime_config, "mark_done", lambda: None)
    monkeypatch.setattr(
        main_module.runtime_config, "get_scheduler_paused", lambda: False
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_alert_config", lambda: {"enabled": False}
    )
    monkeypatch.setattr(main_module.runtime_config, "set_next_run_at", lambda t: None)
    monkeypatch.setattr(main_module.runtime_config, "set_last_run_at", lambda t: None)

    result = MagicMock()
    service.run.return_value = result

    _poll_once(scheduler, dispatcher, service, alert_manager, 60, ["csv"])

    service.run.assert_called_once()


def test_poll_once_pause_calls_pause_job(monkeypatch):
    """When scheduler_paused transitions to True, pause_job is called."""
    scheduler, dispatcher, service, alert_manager = _make_poll_deps()
    monkeypatch.setattr(
        main_module.runtime_config, "get_interval_minutes", lambda default: 60
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_enabled_exporters", lambda default: ["csv"]
    )
    monkeypatch.setattr(
        main_module.runtime_config, "consume_run_trigger", lambda: False
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_scheduler_paused", lambda: True
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_alert_config", lambda: {"enabled": False}
    )
    monkeypatch.setattr(main_module.runtime_config, "set_next_run_at", lambda t: None)

    _, _, paused, _, _ = _poll_once(
        scheduler, dispatcher, service, alert_manager, 60, ["csv"], last_paused=False
    )

    scheduler.pause_job.assert_called_once_with("speedtest_run")
    scheduler.resume_job.assert_not_called()
    assert paused is True


def test_poll_once_resume_calls_resume_job(monkeypatch):
    """When scheduler_paused transitions to False, resume_job is called."""
    scheduler, dispatcher, service, alert_manager = _make_poll_deps()
    monkeypatch.setattr(
        main_module.runtime_config, "get_interval_minutes", lambda default: 60
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_enabled_exporters", lambda default: ["csv"]
    )
    monkeypatch.setattr(
        main_module.runtime_config, "consume_run_trigger", lambda: False
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_scheduler_paused", lambda: False
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_alert_config", lambda: {"enabled": False}
    )
    monkeypatch.setattr(main_module.runtime_config, "set_next_run_at", lambda t: None)

    _, _, paused, _, _ = _poll_once(
        scheduler, dispatcher, service, alert_manager, 60, ["csv"], last_paused=True
    )

    scheduler.resume_job.assert_called_once_with("speedtest_run")
    scheduler.pause_job.assert_not_called()
    assert paused is False


# ---------------------------------------------------------------------------
# _build_loki_exporter
# ---------------------------------------------------------------------------


def test_build_loki_exporter_raises_without_url(monkeypatch):
    monkeypatch.setattr(main_module.config, "LOKI_URL", "")
    with pytest.raises(ValueError, match="LOKI_URL"):
        main_module._build_loki_exporter()


def test_build_loki_exporter_returns_loki_exporter(monkeypatch):
    monkeypatch.setattr(main_module.config, "LOKI_URL", "http://localhost:3100")
    monkeypatch.setattr(main_module.config, "LOKI_JOB_LABEL", "hermes")

    exporter = main_module._build_loki_exporter()

    assert isinstance(exporter, LokiExporter)


# ---------------------------------------------------------------------------
# build_dispatcher / update_exporters — unknown exporter branch
# ---------------------------------------------------------------------------


def test_build_dispatcher_warns_on_unknown_exporter(monkeypatch, caplog):
    monkeypatch.setattr(
        main_module.runtime_config,
        "get_enabled_exporters",
        lambda default: ["nonexistent"],
    )
    monkeypatch.setattr(main_module, "EXPORTER_REGISTRY", {})

    with caplog.at_level(logging.WARNING):
        dispatcher = build_dispatcher()

    assert "nonexistent" in caplog.text
    assert not dispatcher.exporter_names


def test_update_exporters_warns_on_unknown_exporter(monkeypatch, caplog):
    monkeypatch.setattr(main_module, "EXPORTER_REGISTRY", {})
    monkeypatch.setattr(
        main_module.runtime_config, "set_enabled_exporters", lambda e: None
    )
    dispatcher = MagicMock()

    with caplog.at_level(logging.WARNING):
        update_exporters(dispatcher, ["nonexistent"])

    assert "nonexistent" in caplog.text
    dispatcher.clear.assert_called_once()


def test_update_exporters_warns_on_init_error(monkeypatch, caplog):
    monkeypatch.setattr(
        main_module,
        "EXPORTER_REGISTRY",
        {"failing": _raise_loki_url_required},
    )
    monkeypatch.setattr(
        main_module.runtime_config, "set_enabled_exporters", lambda e: None
    )
    dispatcher = MagicMock()

    with caplog.at_level(logging.WARNING):
        update_exporters(dispatcher, ["failing"])

    assert "could not be initialized" in caplog.text


def test_main_shuts_down_cleanly_on_keyboard_interrupt(monkeypatch):
    mock_scheduler = MagicMock()
    mock_job = MagicMock()
    mock_job.next_run_time = datetime.now(timezone.utc)
    mock_scheduler.get_job.return_value = mock_job

    monkeypatch.setattr(main_module.config, "RUN_ON_STARTUP", False)
    monkeypatch.setattr(main_module.config, "SPEEDTEST_INTERVAL_MINUTES", 60)
    monkeypatch.setattr(main_module.runtime_config, "mark_done", lambda: None)
    monkeypatch.setattr(
        main_module.runtime_config, "get_interval_minutes", lambda default: 60
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_enabled_exporters", lambda default: ["csv"]
    )
    monkeypatch.setattr(main_module.runtime_config, "set_next_run_at", lambda t: None)
    monkeypatch.setattr(main_module, "SpeedtestRunner", MagicMock)
    monkeypatch.setattr(main_module, "build_dispatcher", MagicMock)
    monkeypatch.setattr(main_module, "build_alert_manager", MagicMock)
    monkeypatch.setattr(main_module, "build_scheduler", lambda s, d, a: mock_scheduler)
    monkeypatch.setattr(main_module, "HealthServer", MagicMock)
    monkeypatch.setattr(
        main_module.time, "sleep", MagicMock(side_effect=KeyboardInterrupt)
    )

    with pytest.raises(KeyboardInterrupt):
        main_module.main()

    mock_scheduler.shutdown.assert_called_once()


def test_main_run_on_startup_and_poll_loop(monkeypatch):
    """Covers RUN_ON_STARTUP path and the _poll_once call inside the while loop."""
    mock_scheduler = MagicMock()
    mock_job = MagicMock()
    mock_job.next_run_time = datetime.now(timezone.utc)
    mock_scheduler.get_job.return_value = mock_job

    monkeypatch.setattr(main_module.config, "RUN_ON_STARTUP", True)
    monkeypatch.setattr(main_module.config, "SPEEDTEST_INTERVAL_MINUTES", 60)
    monkeypatch.setattr(main_module.runtime_config, "mark_done", lambda: None)
    monkeypatch.setattr(main_module.runtime_config, "mark_running", lambda: None)
    monkeypatch.setattr(
        main_module.runtime_config, "get_interval_minutes", lambda default: 60
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_enabled_exporters", lambda default: ["csv"]
    )
    monkeypatch.setattr(main_module.runtime_config, "set_next_run_at", lambda t: None)
    monkeypatch.setattr(
        main_module.runtime_config, "consume_run_trigger", lambda: False
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_alert_config", lambda: {"enabled": False}
    )
    monkeypatch.setattr(main_module, "SpeedtestRunner", MagicMock)
    monkeypatch.setattr(main_module, "build_dispatcher", MagicMock)
    monkeypatch.setattr(main_module, "build_alert_manager", MagicMock)
    monkeypatch.setattr(main_module, "build_scheduler", lambda s, d, a: mock_scheduler)
    monkeypatch.setattr(main_module, "HealthServer", MagicMock)
    # sleep succeeds once; _poll_once raises KeyboardInterrupt to exit the loop
    monkeypatch.setattr(main_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        main_module, "_poll_once", MagicMock(side_effect=KeyboardInterrupt)
    )
    # run_once needs mark_running/mark_done; service.run raises so no dispatch needed
    mock_svc = MagicMock()
    mock_svc.run.side_effect = RuntimeError("skip")
    monkeypatch.setattr(main_module, "SpeedtestRunner", lambda: mock_svc)

    with pytest.raises(KeyboardInterrupt):
        main_module.main()

    mock_scheduler.shutdown.assert_called_once()


# ---------------------------------------------------------------------------
# build_alert_manager
# ---------------------------------------------------------------------------


def test_build_alert_manager_registers_providers_when_enabled(monkeypatch):
    """build_alert_manager registers providers when alerting is enabled in config."""
    monkeypatch.setattr(
        main_module.runtime_config,
        "get_alert_config",
        lambda: {
            "enabled": True,
            "failure_threshold": 3,
            "cooldown_minutes": 60,
            "providers": {},
        },
    )
    monkeypatch.setattr(main_module.config, "ALERT_FAILURE_THRESHOLD", 3)
    monkeypatch.setattr(main_module.config, "ALERT_COOLDOWN_MINUTES", 60)

    manager = build_alert_manager()

    assert manager.failure_threshold == 3
    assert manager.cooldown_minutes == 60


def test_build_alert_manager_registers_providers_when_threshold_positive(monkeypatch):
    """build_alert_manager registers providers when threshold > 0 even if not enabled."""
    monkeypatch.setattr(
        main_module.runtime_config,
        "get_alert_config",
        lambda: {
            "enabled": False,
            "failure_threshold": 5,
            "cooldown_minutes": 30,
            "providers": {},
        },
    )
    monkeypatch.setattr(main_module.config, "ALERT_FAILURE_THRESHOLD", 5)
    monkeypatch.setattr(main_module.config, "ALERT_COOLDOWN_MINUTES", 30)

    manager = build_alert_manager()

    assert manager.failure_threshold == 5


def test_build_alert_manager_no_providers_when_disabled_zero_threshold(monkeypatch):
    """build_alert_manager skips provider registration when disabled and threshold is 0."""
    monkeypatch.setattr(
        main_module.runtime_config,
        "get_alert_config",
        lambda: {
            "enabled": False,
            "failure_threshold": 0,
            "cooldown_minutes": 60,
            "providers": {},
        },
    )
    monkeypatch.setattr(main_module.config, "ALERT_FAILURE_THRESHOLD", 0)
    monkeypatch.setattr(main_module.config, "ALERT_COOLDOWN_MINUTES", 60)

    manager = build_alert_manager()

    # failure_threshold is clamped to 1 (max(1, 0)) but no providers are registered
    assert manager.failure_threshold == 1
    assert manager.provider_names == []


# ---------------------------------------------------------------------------
# update_alert_providers
# ---------------------------------------------------------------------------


def test_update_alert_providers_updates_threshold_and_cooldown(monkeypatch):
    """update_alert_providers sets threshold and cooldown when present in config."""
    monkeypatch.setattr(main_module.runtime_config, "set_alert_config", lambda c: None)
    manager = MagicMock()

    update_alert_providers(
        manager,
        {
            "enabled": False,
            "failure_threshold": 5,
            "cooldown_minutes": 30,
        },
    )

    assert manager.failure_threshold == 5
    assert manager.cooldown_minutes == 30


def test_update_alert_providers_enabled_registers_providers(monkeypatch, caplog):
    """update_alert_providers registers providers and logs when alerting is enabled."""
    registered = []

    def _fake_register(manager, providers, require_enabled):
        registered.append((manager, providers))

    monkeypatch.setattr(main_module, "register_all_providers", _fake_register)
    monkeypatch.setattr(main_module.runtime_config, "set_alert_config", lambda c: None)
    manager = MagicMock()

    with caplog.at_level(logging.INFO):
        update_alert_providers(
            manager,
            {"enabled": True, "providers": {"webhook": {"url": "https://example.com"}}},
        )

    assert len(registered) == 1
    assert "updated and enabled" in caplog.text


def test_update_alert_providers_disabled_clears_providers(monkeypatch, caplog):
    """update_alert_providers logs disabled message when alerting is disabled."""
    monkeypatch.setattr(main_module.runtime_config, "set_alert_config", lambda c: None)
    manager = MagicMock()

    with caplog.at_level(logging.INFO):
        update_alert_providers(manager, {"enabled": False})

    manager.clear_providers.assert_called_once()
    assert "disabled" in caplog.text.lower()


# ---------------------------------------------------------------------------
# _handle_scheduler_pause_toggle — job missing
# ---------------------------------------------------------------------------


def test_handle_scheduler_pause_toggle_when_job_missing():
    """_handle_scheduler_pause_toggle returns early when the job does not exist."""
    scheduler = MagicMock()
    scheduler.get_job.return_value = None

    # Should not raise or call pause_job/resume_job
    _handle_scheduler_pause_toggle(scheduler, should_pause=True)

    scheduler.pause_job.assert_not_called()
    scheduler.resume_job.assert_not_called()


# ---------------------------------------------------------------------------
# _build_health_status
# ---------------------------------------------------------------------------


def test_build_health_status_paused(monkeypatch):
    """_build_health_status returns 'paused' scheduler state when paused."""
    monkeypatch.setattr(
        main_module.runtime_config, "get_scheduler_paused", lambda: True
    )
    monkeypatch.setattr(main_module.runtime_config, "get_last_run_at", lambda: None)
    monkeypatch.setattr(main_module.runtime_config, "get_next_run_at", lambda: None)
    monkeypatch.setattr(main_module.runtime_config, "is_running", lambda: False)

    scheduler = MagicMock()
    scheduler.running = True

    status = _build_health_status(scheduler)

    assert status["scheduler"] == "paused"
    assert status["scans_paused"] is True


def test_build_health_status_stopped(monkeypatch):
    """_build_health_status returns 'stopped' and 'degraded' when scheduler not running."""
    monkeypatch.setattr(
        main_module.runtime_config, "get_scheduler_paused", lambda: False
    )
    monkeypatch.setattr(main_module.runtime_config, "get_last_run_at", lambda: None)
    monkeypatch.setattr(main_module.runtime_config, "get_next_run_at", lambda: None)
    monkeypatch.setattr(main_module.runtime_config, "is_running", lambda: False)

    scheduler = MagicMock()
    scheduler.running = False

    status = _build_health_status(scheduler)

    assert status["scheduler"] == "stopped"
    assert status["status"] == "degraded"


def test_build_health_status_running(monkeypatch):
    """_build_health_status returns 'running' and 'ok' when scheduler is active."""
    monkeypatch.setattr(
        main_module.runtime_config, "get_scheduler_paused", lambda: False
    )
    monkeypatch.setattr(
        main_module.runtime_config,
        "get_last_run_at",
        lambda: "2026-05-01T10:00:00+00:00",
    )
    monkeypatch.setattr(
        main_module.runtime_config,
        "get_next_run_at",
        lambda: "2026-05-01T11:00:00+00:00",
    )
    monkeypatch.setattr(main_module.runtime_config, "is_running", lambda: False)

    scheduler = MagicMock()
    scheduler.running = True

    status = _build_health_status(scheduler)

    assert status["scheduler"] == "running"
    assert status["status"] == "ok"


# ---------------------------------------------------------------------------
# _validate_loki_endpoint
# ---------------------------------------------------------------------------


@patch("src.main.requests.head")
def test_validate_loki_endpoint_timeout(mock_head, caplog):
    """_validate_loki_endpoint logs a warning on Timeout."""
    mock_head.side_effect = requests.exceptions.Timeout()

    with caplog.at_level(logging.WARNING):
        _validate_loki_endpoint("http://loki:3100")

    assert "timed out" in caplog.text


@patch("src.main.requests.head")
def test_validate_loki_endpoint_connection_error(mock_head, caplog):
    """_validate_loki_endpoint logs a warning on ConnectionError."""
    mock_head.side_effect = requests.exceptions.ConnectionError("refused")

    with caplog.at_level(logging.WARNING):
        _validate_loki_endpoint("http://loki:3100")

    assert "unreachable" in caplog.text


@patch("src.main.requests.head")
def test_validate_loki_endpoint_http_error(mock_head, caplog):
    """_validate_loki_endpoint logs a warning on HTTPError."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "403 Forbidden"
    )
    mock_head.return_value = mock_response

    with caplog.at_level(logging.WARNING):
        _validate_loki_endpoint("http://loki:3100")

    assert "HTTP error" in caplog.text


@patch("src.main.requests.head")
def test_validate_loki_endpoint_generic_request_error(mock_head, caplog):
    """_validate_loki_endpoint logs a warning on generic RequestException."""
    mock_head.side_effect = requests.exceptions.RequestException("ssl error")

    with caplog.at_level(logging.WARNING):
        _validate_loki_endpoint("http://loki:3100")

    assert "validation failed" in caplog.text


@patch("src.main.requests.head")
def test_validate_loki_endpoint_success(mock_head):
    """_validate_loki_endpoint does not raise when endpoint is reachable."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_head.return_value = mock_response

    # Should not raise
    _validate_loki_endpoint("http://loki:3100")
    mock_head.assert_called_once()


# ---------------------------------------------------------------------------
# _validate_environment
# ---------------------------------------------------------------------------


def test_validate_environment_loki_enabled_no_url(monkeypatch, caplog):
    """_validate_environment warns when loki is enabled but LOKI_URL is not set."""
    monkeypatch.setattr(
        main_module.runtime_config,
        "get_enabled_exporters",
        lambda default: ["loki"],
    )
    monkeypatch.setattr(main_module.config, "ENABLED_EXPORTERS", ["loki"])
    monkeypatch.setattr(main_module.config, "LOKI_URL", "")

    with caplog.at_level(logging.WARNING):
        _validate_environment()

    assert "LOKI_URL is not set" in caplog.text


def test_validate_environment_no_loki_exporter(monkeypatch):
    """_validate_environment does not call loki validation when loki is not enabled."""
    monkeypatch.setattr(
        main_module.runtime_config,
        "get_enabled_exporters",
        lambda default: ["csv"],
    )
    monkeypatch.setattr(main_module.config, "ENABLED_EXPORTERS", ["csv"])

    # Should not raise; no loki endpoint to validate
    _validate_environment()


# ---------------------------------------------------------------------------
# main() — restored paused state at startup
# ---------------------------------------------------------------------------


def test_main_restores_paused_state_on_startup(monkeypatch):
    """main() pauses the scheduler job when runtime config indicates paused state."""
    mock_scheduler = MagicMock()
    mock_job = MagicMock()
    mock_job.next_run_time = datetime.now(timezone.utc)
    mock_scheduler.get_job.return_value = mock_job

    monkeypatch.setattr(main_module.config, "RUN_ON_STARTUP", False)
    monkeypatch.setattr(main_module.config, "SPEEDTEST_INTERVAL_MINUTES", 60)
    monkeypatch.setattr(main_module.runtime_config, "mark_done", lambda: None)
    monkeypatch.setattr(
        main_module.runtime_config, "get_interval_minutes", lambda default: 60
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_enabled_exporters", lambda default: ["csv"]
    )
    monkeypatch.setattr(main_module.runtime_config, "set_next_run_at", lambda t: None)
    monkeypatch.setattr(
        main_module.runtime_config, "consume_run_trigger", lambda: False
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_alert_config", lambda: {"enabled": False}
    )
    # get_scheduler_paused returns True to trigger the restore path
    monkeypatch.setattr(
        main_module.runtime_config, "get_scheduler_paused", lambda: True
    )
    monkeypatch.setattr(main_module, "SpeedtestRunner", MagicMock)
    monkeypatch.setattr(main_module, "build_dispatcher", MagicMock)
    monkeypatch.setattr(main_module, "build_alert_manager", MagicMock)
    monkeypatch.setattr(main_module, "build_scheduler", lambda s, d, a: mock_scheduler)
    monkeypatch.setattr(main_module, "HealthServer", MagicMock)
    monkeypatch.setattr(
        main_module.time, "sleep", MagicMock(side_effect=KeyboardInterrupt)
    )

    with pytest.raises(KeyboardInterrupt):
        main_module.main()

    mock_scheduler.pause_job.assert_called_once_with("speedtest_run")


# ---------------------------------------------------------------------------
# _poll_once — alert config change
# ---------------------------------------------------------------------------


def test_poll_once_alert_config_changed(monkeypatch):
    """_poll_once calls update_alert_providers when alert config changes."""
    scheduler, dispatcher, service, alert_manager = _make_poll_deps()

    new_alert_config = {
        "enabled": True,
        "failure_threshold": 3,
        "cooldown_minutes": 10,
        "providers": {},
    }

    monkeypatch.setattr(
        main_module.runtime_config, "get_interval_minutes", lambda default: 60
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_enabled_exporters", lambda default: ["csv"]
    )
    monkeypatch.setattr(
        main_module.runtime_config, "consume_run_trigger", lambda: False
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_scheduler_paused", lambda: False
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_alert_config", lambda: new_alert_config
    )
    monkeypatch.setattr(main_module.runtime_config, "set_next_run_at", lambda t: None)
    monkeypatch.setattr(main_module.runtime_config, "set_alert_config", lambda c: None)

    updated_configs = []

    def _fake_update(manager, cfg):
        updated_configs.append(cfg)
        manager.clear_providers()

    monkeypatch.setattr(main_module, "update_alert_providers", _fake_update)

    _, _, _, returned_alert_config, _ = _poll_once(
        scheduler,
        dispatcher,
        service,
        alert_manager,
        60,
        ["csv"],
        last_alert_config={"enabled": False},
    )

    assert len(updated_configs) == 1
    assert returned_alert_config == new_alert_config
