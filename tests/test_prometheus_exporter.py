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


# ---------------------------------------------------------------------------
# Integration tests — gauge value validation
# ---------------------------------------------------------------------------


@patch("src.exporters.prometheus_exporter.start_http_server")
def test_prometheus_gauges_reflect_exported_values(_mock_start):
    """Integration test: verify Prometheus gauges are set to correct metric values."""
    from src.exporters.prometheus_exporter import _DOWNLOAD, _UPLOAD, _PING, _JITTER

    exporter = PrometheusExporter(port=9192)

    # Create a result with known values
    result = SpeedResult(
        timestamp=datetime.now(timezone.utc),
        download_mbps=123.45,
        upload_mbps=67.89,
        ping_ms=15.2,
        jitter_ms=3.1,
        isp_name="TestISP",
        server_name="TestServer",
        server_location="Berlin, DE",
        server_id=9999,
    )

    exporter.export(result)

    # Verify gauge values match the exported result
    labels = {
        "server_name": "TestServer",
        "server_location": "Berlin, DE",
        "isp_name": "TestISP",
    }

    # Get the actual gauge values by collecting metrics
    assert _DOWNLOAD.labels(**labels)._value._value == pytest.approx(123.45)
    assert _UPLOAD.labels(**labels)._value._value == pytest.approx(67.89)
    assert _PING.labels(**labels)._value._value == pytest.approx(15.2)
    assert _JITTER.labels(**labels)._value._value == pytest.approx(3.1)


@patch("src.exporters.prometheus_exporter.start_http_server")
def test_prometheus_gauges_update_on_multiple_exports(_mock_start):
    """Integration test: verify gauges update correctly with new values."""
    from src.exporters.prometheus_exporter import _DOWNLOAD, _UPLOAD, _PING

    exporter = PrometheusExporter(port=9193)

    # Export first result
    result1 = SpeedResult(
        timestamp=datetime.now(timezone.utc),
        download_mbps=100.0,
        upload_mbps=50.0,
        ping_ms=10.0,
        server_name="Server1",
        server_location="Location1",
        server_id=1,
    )
    exporter.export(result1)

    labels1 = {"server_name": "Server1", "server_location": "Location1", "isp_name": ""}
    assert _DOWNLOAD.labels(**labels1)._value._value == pytest.approx(100.0)

    # Export second result with different values
    result2 = SpeedResult(
        timestamp=datetime.now(timezone.utc),
        download_mbps=200.0,
        upload_mbps=100.0,
        ping_ms=5.0,
        server_name="Server1",
        server_location="Location1",
        server_id=1,
    )
    exporter.export(result2)

    # Verify gauges updated to new values
    assert _DOWNLOAD.labels(**labels1)._value._value == pytest.approx(200.0)
    assert _UPLOAD.labels(**labels1)._value._value == pytest.approx(100.0)
    assert _PING.labels(**labels1)._value._value == pytest.approx(5.0)


@patch("src.exporters.prometheus_exporter.start_http_server")
def test_prometheus_gauges_handle_missing_jitter(_mock_start):
    """Integration test: verify jitter gauge is not updated when jitter_ms is None."""

    exporter = PrometheusExporter(port=9194)

    # Export result without jitter
    result = SpeedResult(
        timestamp=datetime.now(timezone.utc),
        download_mbps=100.0,
        upload_mbps=50.0,
        ping_ms=10.0,
        jitter_ms=None,
        server_name="Server",
        server_location="Location",
        server_id=1,
    )

    # This should not raise, and jitter gauge should not be set
    exporter.export(result)  # Should complete without error
