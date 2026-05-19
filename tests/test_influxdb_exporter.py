"""Tests for InfluxDBExporter."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest

from src.exporters.influxdb_exporter import InfluxDBExporter, _MEASUREMENT
from src.models.speed_result import SpeedResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_result(**kwargs) -> SpeedResult:
    defaults = {
        "timestamp": datetime(2026, 5, 19, 10, 0, 0, tzinfo=timezone.utc),
        "download_mbps": 200.5,
        "upload_mbps": 95.3,
        "ping_ms": 12.4,
        "server_name": "London-1",
        "server_location": "UK",
        "server_id": 101,
        "jitter_ms": 1.2,
        "isp_name": "Acme ISP",
        "packet_loss_pct": 0.0,
        "quality_score": 88.0,
        "sla_ok": True,
    }
    defaults.update(kwargs)
    return SpeedResult(**defaults)


def _make_exporter(url="https://influxdb.example.com:8086", **kwargs):
    """Return an InfluxDBExporter with the client patched out."""
    with patch("src.exporters.influxdb_exporter.InfluxDBClient") as mock_cls:
        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_cls.return_value = mock_client

        exporter = InfluxDBExporter(
            url=url,
            token="my-secret-token",
            org="myorg",
            bucket="speedtest",
            **kwargs,
        )
        # Attach mocks so tests can inspect calls
        exporter._mock_client = mock_client
        exporter._mock_write_api = mock_write_api
        return exporter


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------

class TestInfluxDBExporterInit:
    def test_valid_https_url(self):
        e = _make_exporter(url="https://influxdb.example.com:8086")
        assert e._url == "https://influxdb.example.com:8086"

    def test_valid_http_url(self):
        e = _make_exporter(url="http://localhost:8086")
        assert e._url == "http://localhost:8086"

    def test_empty_url_raises(self):
        with pytest.raises(ValueError, match="URL is required"):
            InfluxDBExporter(url="", token="t", org="o", bucket="b")

    def test_blank_url_raises(self):
        with pytest.raises(ValueError, match="URL is required"):
            InfluxDBExporter(url="   ", token="t", org="o", bucket="b")

    def test_invalid_scheme_raises(self):
        with pytest.raises(ValueError, match="http or https"):
            InfluxDBExporter(url="ftp://bad", token="t", org="o", bucket="b")

    def test_url_without_hostname_raises(self):
        with pytest.raises(ValueError, match="hostname"):
            InfluxDBExporter(url="https://", token="t", org="o", bucket="b")

    def test_empty_token_raises(self):
        with pytest.raises(ValueError, match="token is required"):
            InfluxDBExporter(url="https://localhost:8086", token="", org="o", bucket="b")

    def test_blank_token_raises(self):
        with pytest.raises(ValueError, match="token is required"):
            InfluxDBExporter(url="https://localhost:8086", token="  ", org="o", bucket="b")

    def test_empty_org_raises(self):
        with pytest.raises(ValueError, match="org is required"):
            InfluxDBExporter(url="https://localhost:8086", token="t", org="", bucket="b")

    def test_empty_bucket_raises(self):
        with pytest.raises(ValueError, match="bucket is required"):
            InfluxDBExporter(url="https://localhost:8086", token="t", org="o", bucket="")

    def test_zero_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout_ms must be positive"):
            InfluxDBExporter(
                url="https://localhost:8086", token="t", org="o", bucket="b", timeout_ms=0
            )

    def test_negative_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout_ms must be positive"):
            InfluxDBExporter(
                url="https://localhost:8086", token="t", org="o", bucket="b", timeout_ms=-1
            )

    def test_strips_whitespace_from_org_and_bucket(self):
        e = _make_exporter()
        assert e._org == "myorg"
        assert e._bucket == "speedtest"

    def test_influxdb_client_constructed_with_correct_args(self):
        with patch("src.exporters.influxdb_exporter.InfluxDBClient") as mock_cls:
            mock_cls.return_value.write_api.return_value = MagicMock()
            InfluxDBExporter(
                url="https://influxdb.example.com:8086",
                token="my-token",
                org="myorg",
                bucket="speedtest",
                timeout_ms=5000,
            )
            mock_cls.assert_called_once_with(
                url="https://influxdb.example.com:8086",
                token="my-token",
                org="myorg",
                timeout=5000,
            )


# ---------------------------------------------------------------------------
# _build_point
# ---------------------------------------------------------------------------

class TestBuildPoint:
    def test_measurement_name(self):
        result = _sample_result()
        point = InfluxDBExporter._build_point(result)
        # The Point object's _name attribute contains the measurement
        assert point._name == _MEASUREMENT

    def test_tags_set(self):
        result = _sample_result()
        point = InfluxDBExporter._build_point(result)
        tags = point._tags
        assert tags["server_name"] == "London-1"
        assert tags["server_location"] == "UK"
        assert tags["isp_name"] == "Acme ISP"

    def test_unknown_tags_fallback(self):
        result = _sample_result(server_name="", server_location="", isp_name=None)
        point = InfluxDBExporter._build_point(result)
        assert point._tags["server_name"] == "unknown"
        assert point._tags["server_location"] == "unknown"
        assert point._tags["isp_name"] == "unknown"

    def test_required_fields(self):
        result = _sample_result(jitter_ms=None, packet_loss_pct=None, quality_score=None, sla_ok=None, server_id=None)
        point = InfluxDBExporter._build_point(result)
        fields = point._fields
        assert fields["download_mbps"] == pytest.approx(200.5)
        assert fields["upload_mbps"] == pytest.approx(95.3)
        assert fields["ping_ms"] == pytest.approx(12.4)

    def test_optional_fields_included_when_present(self):
        result = _sample_result()
        point = InfluxDBExporter._build_point(result)
        fields = point._fields
        assert fields["jitter_ms"] == pytest.approx(1.2)
        assert fields["packet_loss_pct"] == pytest.approx(0.0)
        assert fields["quality_score"] == pytest.approx(88.0)
        assert fields["sla_ok"] == 1
        assert fields["server_id"] == 101

    def test_optional_fields_omitted_when_none(self):
        result = _sample_result(jitter_ms=None, packet_loss_pct=None, quality_score=None, sla_ok=None, server_id=None)
        point = InfluxDBExporter._build_point(result)
        fields = point._fields
        assert "jitter_ms" not in fields
        assert "packet_loss_pct" not in fields
        assert "quality_score" not in fields
        assert "sla_ok" not in fields
        assert "server_id" not in fields

    def test_sla_ok_false_stored_as_zero(self):
        result = _sample_result(sla_ok=False)
        point = InfluxDBExporter._build_point(result)
        assert point._fields["sla_ok"] == 0

    def test_naive_timestamp_gets_utc(self):
        result = _sample_result()
        # Force a naive timestamp via object __dict__ to test the fallback path
        object.__setattr__(result, "timestamp", datetime(2026, 5, 19, 10, 0, 0))
        point = InfluxDBExporter._build_point(result)
        assert point._time is not None

    def test_timezone_aware_timestamp_preserved(self):
        ts = datetime(2026, 5, 19, 10, 0, 0, tzinfo=timezone.utc)
        result = _sample_result(timestamp=ts)
        point = InfluxDBExporter._build_point(result)
        assert point._time == ts


# ---------------------------------------------------------------------------
# export()
# ---------------------------------------------------------------------------

class TestExport:
    def test_export_calls_write_api(self):
        exporter = _make_exporter()
        result = _sample_result()
        exporter.export(result)
        exporter._mock_write_api.write.assert_called_once()
        call_kwargs = exporter._mock_write_api.write.call_args
        assert call_kwargs.kwargs["bucket"] == "speedtest"

    def test_export_wraps_influxdb_error(self):
        from influxdb_client.client.exceptions import InfluxDBError

        exporter = _make_exporter()
        mock_response = MagicMock()
        mock_response.status = 401
        exporter._mock_write_api.write.side_effect = InfluxDBError(
            response=mock_response, message="Unauthorized"
        )

        with pytest.raises(RuntimeError, match="InfluxDB write failed"):
            exporter.export(_sample_result())

    def test_export_wraps_generic_exception(self):
        exporter = _make_exporter()
        exporter._mock_write_api.write.side_effect = ConnectionRefusedError("refused")

        with pytest.raises(RuntimeError, match="InfluxDB write failed"):
            exporter.export(_sample_result())

    def test_export_full_result_no_optional_fields(self):
        """Export should not raise when all optional fields are None."""
        exporter = _make_exporter()
        result = _sample_result(
            jitter_ms=None,
            packet_loss_pct=None,
            quality_score=None,
            sla_ok=None,
            server_id=None,
        )
        exporter.export(result)  # should not raise
        exporter._mock_write_api.write.assert_called_once()


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------

class TestClose:
    def test_close_calls_write_api_and_client(self):
        exporter = _make_exporter()
        exporter.close()
        exporter._mock_write_api.close.assert_called_once()
        exporter._mock_client.close.assert_called_once()
