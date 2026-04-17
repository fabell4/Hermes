"""Tests for src/exporters/prometheus_exporter.py."""

# pylint: disable=missing-function-docstring,protected-access
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.exporters.prometheus_exporter import PrometheusExporter
from src.models.speed_result import SpeedResult


def _sample_result() -> SpeedResult:
    return SpeedResult(
        timestamp=datetime.now(timezone.utc),
        download_mbps=100.0,
        upload_mbps=50.0,
        ping_ms=10.0,
        server_name="Test ISP",
        server_location="Berlin, DE",
        server_id=1,
    )


@pytest.fixture(autouse=True)
def reset_server_started():
    """Reset the class-level _server_started guard between tests."""
    original = PrometheusExporter._server_started
    PrometheusExporter._server_started = False
    yield
    PrometheusExporter._server_started = original


@patch("src.exporters.prometheus_exporter.start_http_server")
def test_init_starts_server_on_first_instantiation(mock_start):
    PrometheusExporter(port=9191)
    mock_start.assert_called_once_with(9191)
    assert PrometheusExporter._server_started is True


@patch("src.exporters.prometheus_exporter.start_http_server")
def test_init_skips_server_when_already_started(mock_start):
    PrometheusExporter._server_started = True
    PrometheusExporter(port=9191)
    mock_start.assert_not_called()


@patch("src.exporters.prometheus_exporter.start_http_server")
def test_export_updates_gauges_without_raising(_mock_start):
    exporter = PrometheusExporter(port=9191)
    exporter.export(_sample_result())  # should not raise
