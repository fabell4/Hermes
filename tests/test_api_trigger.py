"""Tests for POST /api/trigger and _run_test in src/api/routes/trigger.py."""
# pylint: disable=missing-function-docstring,protected-access

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
import src.api.routes.trigger as trigger_module

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_lock():
    """Ensure the trigger lock is always released between tests."""
    yield
    # If the lock was acquired and never released, release it now.
    if trigger_module._test_lock.locked():  # pylint: disable=protected-access
        trigger_module._test_lock.release()  # pylint: disable=protected-access


def _make_mock_result():
    result = MagicMock()
    result.download_mbps = 200.0
    result.upload_mbps = 50.0
    result.ping_ms = 12.5
    return result


# ---------------------------------------------------------------------------
# POST /api/trigger — endpoint behaviour
# Patch _run_test directly so the real Thread.start() is used; patching
# threading.Thread.start globally would block starlette's own internal threads.
# ---------------------------------------------------------------------------


def test_trigger_returns_200():
    with patch("src.api.routes.trigger._run_test"):
        resp = client.post("/api/trigger")
    assert resp.status_code == 200


def test_trigger_returns_started():
    with patch("src.api.routes.trigger._run_test"):
        body = client.post("/api/trigger").json()
    assert body["status"] == "started"


def test_trigger_returns_already_running_when_lock_held():
    trigger_module._test_lock.acquire()  # pylint: disable=protected-access
    body = client.post("/api/trigger").json()
    assert body["status"] == "already_running"


# ---------------------------------------------------------------------------
# _run_test — unit tests (lock pre-acquired to mirror the real call path)
# ---------------------------------------------------------------------------


def test_run_test_dispatches_result():
    result = _make_mock_result()
    mock_runner = MagicMock()
    mock_runner.return_value.run.return_value = result
    mock_dispatcher = MagicMock()

    trigger_module._test_lock.acquire()  # pylint: disable=protected-access
    with (
        patch("src.api.routes.trigger.SpeedtestRunner", mock_runner),
        patch("src.api.routes.trigger.ResultDispatcher", mock_dispatcher),
        patch(
            "src.api.routes.trigger.runtime_config.get_enabled_exporters",
            return_value=[],
        ),
    ):
        trigger_module._run_test()

    mock_dispatcher.return_value.dispatch.assert_called_once_with(result)


def test_run_test_releases_lock_on_success():
    result = _make_mock_result()
    mock_runner = MagicMock()
    mock_runner.return_value.run.return_value = result

    trigger_module._test_lock.acquire()  # pylint: disable=protected-access
    with (
        patch("src.api.routes.trigger.SpeedtestRunner", mock_runner),
        patch("src.api.routes.trigger.ResultDispatcher"),
        patch(
            "src.api.routes.trigger.runtime_config.get_enabled_exporters",
            return_value=[],
        ),
    ):
        trigger_module._run_test()

    acquired = trigger_module._test_lock.acquire(blocking=False)  # pylint: disable=protected-access
    assert acquired


def test_run_test_releases_lock_on_exception():
    mock_runner = MagicMock()
    mock_runner.return_value.run.side_effect = RuntimeError("network failure")

    trigger_module._test_lock.acquire()  # pylint: disable=protected-access
    with (
        patch("src.api.routes.trigger.SpeedtestRunner", mock_runner),
        patch(
            "src.api.routes.trigger.runtime_config.get_enabled_exporters",
            return_value=[],
        ),
        patch("src.api.routes.trigger.ResultDispatcher"),
    ):
        trigger_module._run_test()

    acquired = trigger_module._test_lock.acquire(blocking=False)  # pylint: disable=protected-access
    assert acquired


def test_run_test_skips_unknown_exporter_name():
    result = _make_mock_result()
    mock_runner = MagicMock()
    mock_runner.return_value.run.return_value = result
    mock_dispatcher = MagicMock()

    trigger_module._test_lock.acquire()  # pylint: disable=protected-access
    with (
        patch("src.api.routes.trigger.SpeedtestRunner", mock_runner),
        patch(
            "src.api.routes.trigger.runtime_config.get_enabled_exporters",
            return_value=["influxdb"],
        ),
        patch("src.api.routes.trigger.ResultDispatcher", mock_dispatcher),
    ):
        trigger_module._run_test()

    mock_dispatcher.return_value.add_exporter.assert_not_called()


def test_run_test_registers_csv_exporter():
    result = _make_mock_result()
    mock_runner = MagicMock()
    mock_runner.return_value.run.return_value = result
    mock_dispatcher = MagicMock()
    mock_csv = MagicMock()

    trigger_module._test_lock.acquire()  # pylint: disable=protected-access
    with (
        patch("src.api.routes.trigger.SpeedtestRunner", mock_runner),
        patch(
            "src.api.routes.trigger.runtime_config.get_enabled_exporters",
            return_value=["csv"],
        ),
        patch("src.api.routes.trigger.ResultDispatcher", mock_dispatcher),
        patch("src.api.routes.trigger.CSVExporter", mock_csv),
    ):
        trigger_module._run_test()

    call_args = mock_dispatcher.return_value.add_exporter.call_args
    assert call_args[0][0] == "csv"


def test_run_test_no_loki_when_url_not_set():
    """When LOKI_URL is falsy the loki factory returns None and is skipped."""
    result = _make_mock_result()
    mock_runner = MagicMock()
    mock_runner.return_value.run.return_value = result
    mock_dispatcher = MagicMock()

    trigger_module._test_lock.acquire()  # pylint: disable=protected-access
    with (
        patch("src.api.routes.trigger.SpeedtestRunner", mock_runner),
        patch(
            "src.api.routes.trigger.runtime_config.get_enabled_exporters",
            return_value=["loki"],
        ),
        patch("src.api.routes.trigger.ResultDispatcher", mock_dispatcher),
        patch("src.api.routes.trigger.config.LOKI_URL", ""),
    ):
        trigger_module._run_test()

    mock_dispatcher.return_value.add_exporter.assert_not_called()
