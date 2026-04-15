"""Tests for current SpeedtestRunner and main.run_once behavior."""
# pylint: disable=missing-function-docstring,protected-access

from datetime import datetime, timezone
import logging
from unittest.mock import MagicMock, patch

import speedtest as speedtest_module

import pytest

import src.main as main_module
from src.exporters.base_exporter import BaseExporter
from src.exporters.loki_exporter import LokiExporter
from src.main import build_dispatcher, build_scheduler, run_once, update_exporters, _poll_once
from src.models.speed_result import SpeedResult
from src.result_dispatcher import DispatchError
from src.services.speedtest_runner import SpeedtestRunner


class DummyExporter(BaseExporter):
    """Minimal no-op exporter for test isolation."""

    def export(self, result: SpeedResult) -> None:
        return None


def _raise_loki_url_required() -> BaseExporter:
    raise ValueError("Loki URL is required")


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_speedtest_runner_run_success(mock_st_class):
    mock_st = MagicMock()
    mock_st.get_best_server.return_value = {
        "sponsor": "Test ISP",
        "name": "Test City",
        "country": "DE",
        "id": "1234",
    }
    mock_st.download.return_value = 100_000_000
    mock_st.upload.return_value = 50_000_000
    mock_st.results.ping = 12.5
    mock_st_class.return_value = mock_st

    result = SpeedtestRunner().run()

    assert result.download_mbps == pytest.approx(100.0)
    assert result.upload_mbps == pytest.approx(50.0)
    assert result.ping_ms == pytest.approx(12.5)
    assert result.server_name == "Test ISP"
    assert result.server_location == "Test City, DE"
    assert result.server_id == 1234


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


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_speedtest_runner_raises_on_config_error(mock_st_class):
    mock_st_class.side_effect = speedtest_module.ConfigRetrievalError
    with pytest.raises(RuntimeError, match="speedtest.net"):
        SpeedtestRunner().run()


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_speedtest_runner_raises_on_no_matched_servers(mock_st_class):
    mock_st = MagicMock()
    mock_st.get_best_server.side_effect = speedtest_module.NoMatchedServers
    mock_st_class.return_value = mock_st
    with pytest.raises(RuntimeError, match="No speedtest servers"):
        SpeedtestRunner().run()


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_speedtest_runner_raises_on_http_error(mock_st_class):
    mock_st = MagicMock()
    mock_st.get_best_server.side_effect = speedtest_module.SpeedtestHTTPError
    mock_st_class.return_value = mock_st
    with pytest.raises(RuntimeError, match="HTTP error"):
        SpeedtestRunner().run()


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_speedtest_runner_raises_on_generic_speedtest_exception(mock_st_class):
    mock_st = MagicMock()
    mock_st.get_best_server.side_effect = speedtest_module.SpeedtestException("oops")
    mock_st_class.return_value = mock_st
    with pytest.raises(RuntimeError, match="Speedtest failed"):
        SpeedtestRunner().run()


# ---------------------------------------------------------------------------
# _poll_once
# ---------------------------------------------------------------------------


def _make_poll_deps():
    """Return mock scheduler, dispatcher, service for _poll_once tests."""
    return MagicMock(), MagicMock(), MagicMock()


def test_poll_once_no_changes_returns_same_state(monkeypatch):
    scheduler, dispatcher, service = _make_poll_deps()
    monkeypatch.setattr(
        main_module.runtime_config, "get_interval_minutes", lambda default: 60
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_enabled_exporters", lambda default: ["csv"]
    )
    monkeypatch.setattr(
        main_module.runtime_config, "consume_run_trigger", lambda: False
    )
    monkeypatch.setattr(main_module.runtime_config, "set_next_run_at", lambda t: None)

    interval, exporters = _poll_once(scheduler, dispatcher, service, 60, ["csv"])

    assert interval == 60
    assert exporters == ["csv"]
    scheduler.reschedule_job.assert_not_called()
    dispatcher.clear.assert_not_called()
    service.run.assert_not_called()


def test_poll_once_interval_changed_calls_update_schedule(monkeypatch):
    scheduler, dispatcher, service = _make_poll_deps()
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
    monkeypatch.setattr(main_module.runtime_config, "set_next_run_at", lambda t: None)

    interval, _ = _poll_once(scheduler, dispatcher, service, 60, ["csv"])

    assert interval == 30
    scheduler.reschedule_job.assert_called_once()


def test_poll_once_exporters_changed_calls_update_exporters(monkeypatch):
    scheduler, dispatcher, service = _make_poll_deps()
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
    monkeypatch.setattr(main_module.runtime_config, "set_next_run_at", lambda t: None)
    monkeypatch.setattr(
        main_module,
        "EXPORTER_REGISTRY",
        {
            "csv": DummyExporter,
            "prometheus": DummyExporter,
        },
    )

    _, exporters = _poll_once(scheduler, dispatcher, service, 60, ["csv"])

    assert sorted(exporters) == ["csv", "prometheus"]
    dispatcher.clear.assert_called_once()


def test_poll_once_trigger_fires_calls_run_once(monkeypatch):
    scheduler, dispatcher, service = _make_poll_deps()
    monkeypatch.setattr(
        main_module.runtime_config, "get_interval_minutes", lambda default: 60
    )
    monkeypatch.setattr(
        main_module.runtime_config, "get_enabled_exporters", lambda default: ["csv"]
    )
    monkeypatch.setattr(main_module.runtime_config, "consume_run_trigger", lambda: True)
    monkeypatch.setattr(main_module.runtime_config, "mark_running", lambda: None)
    monkeypatch.setattr(main_module.runtime_config, "mark_done", lambda: None)
    monkeypatch.setattr(main_module.runtime_config, "set_next_run_at", lambda t: None)

    result = MagicMock()
    service.run.return_value = result

    _poll_once(scheduler, dispatcher, service, 60, ["csv"])

    service.run.assert_called_once()


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
    monkeypatch.setattr(main_module, "build_scheduler", lambda s, d: mock_scheduler)
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
    monkeypatch.setattr(main_module, "SpeedtestRunner", MagicMock)
    monkeypatch.setattr(main_module, "build_dispatcher", MagicMock)
    monkeypatch.setattr(main_module, "build_scheduler", lambda s, d: mock_scheduler)
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
