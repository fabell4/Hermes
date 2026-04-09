"""Tests for current SpeedtestRunner and main.run_once behavior."""

from datetime import datetime, timezone
import logging
from unittest.mock import MagicMock, patch

import pytest

import src.main as main_module
from src.exporters.base_exporter import BaseExporter
from src.main import build_dispatcher, run_once
from src.models.speed_result import SpeedResult
from src.services.speedtest_runner import SpeedtestRunner


class DummyExporter(BaseExporter):
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


def test_run_once_dispatches_result():
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


def test_run_once_handles_runner_error_without_dispatch():
    service = MagicMock()
    dispatcher = MagicMock()
    service.run.side_effect = RuntimeError("network error")

    run_once(service, dispatcher)

    service.run.assert_called_once()
    dispatcher.dispatch.assert_not_called()


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
            "csv": lambda: DummyExporter(),
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

import speedtest as speedtest_module


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
