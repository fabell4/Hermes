from __future__ import annotations

from datetime import datetime, timezone
import json
from unittest.mock import MagicMock, patch

import requests

import pytest

from src.exporters.loki_exporter import LokiExporter
from src.models.speed_result import SpeedResult


def _sample_result() -> SpeedResult:
    return SpeedResult(
        timestamp=datetime(2026, 3, 4, 12, 0, 0, tzinfo=timezone.utc),
        download_mbps=123.45,
        upload_mbps=67.89,
        ping_ms=10.2,
        server_name="Berlin-1",
        server_location="DE",
        server_id=42,
    )


def test_build_push_url_appends_path() -> None:
    exporter = LokiExporter("http://localhost:3100")
    assert exporter._push_url == "http://localhost:3100/loki/api/v1/push"


def test_build_push_url_keeps_full_path() -> None:
    exporter = LokiExporter("http://localhost:3100/loki/api/v1/push")
    assert exporter._push_url == "http://localhost:3100/loki/api/v1/push"


def test_build_push_url_strips_trailing_slash() -> None:
    exporter = LokiExporter("http://localhost:3100/")
    assert exporter._push_url == "http://localhost:3100/loki/api/v1/push"


def test_export_posts_valid_payload() -> None:
    exporter = LokiExporter("http://localhost:3100", job_label="hermes_test")
    result = _sample_result()

    mock_response = MagicMock()
    mock_response.status_code = 204

    with patch(
        "src.exporters.loki_exporter.requests.post", return_value=mock_response
    ) as mock_post:
        exporter.export(result)

    url = mock_post.call_args[0][0]
    body = json.loads(mock_post.call_args[1]["data"].decode("utf-8"))
    line_obj = json.loads(body["streams"][0]["values"][0][1])

    assert url == "http://localhost:3100/loki/api/v1/push"
    assert body["streams"][0]["stream"]["job"] == "hermes_test"
    assert line_obj["download_mbps"] == pytest.approx(123.45)
    assert line_obj["server_name"] == "Berlin-1"


def test_export_raises_on_http_status_401() -> None:
    exporter = LokiExporter("http://localhost:3100")
    result = _sample_result()

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    with patch("src.exporters.loki_exporter.requests.post", return_value=mock_response):
        with pytest.raises(RuntimeError, match="401"):
            exporter.export(result)


def test_export_raises_on_connection_error() -> None:
    exporter = LokiExporter("http://localhost:3100")
    result = _sample_result()

    with patch(
        "src.exporters.loki_exporter.requests.post",
        side_effect=requests.exceptions.ConnectionError("connection refused"),
    ):
        with pytest.raises(RuntimeError, match="connection error"):
            exporter.export(result)


def test_export_raises_on_timeout() -> None:
    exporter = LokiExporter("http://localhost:3100")
    result = _sample_result()

    with patch(
        "src.exporters.loki_exporter.requests.post",
        side_effect=requests.exceptions.Timeout("timed out"),
    ):
        with pytest.raises(RuntimeError, match="timed out"):
            exporter.export(result)


def test_init_requires_url() -> None:
    with pytest.raises(ValueError, match="Loki URL is required"):
        LokiExporter("")


def test_init_rejects_file_scheme() -> None:
    with pytest.raises(ValueError, match="http or https"):
        LokiExporter("file:///etc/passwd")


def test_init_rejects_custom_scheme() -> None:
    with pytest.raises(ValueError, match="http or https"):
        LokiExporter("ftp://localhost:3100")


def test_init_rejects_url_without_hostname() -> None:
    with pytest.raises(ValueError, match="must include a hostname"):
        LokiExporter("http://")


def test_init_rejects_negative_timeout() -> None:
    with pytest.raises(ValueError, match="Timeout must be positive"):
        LokiExporter("http://localhost:3100", timeout_seconds=-1)


def test_init_rejects_zero_timeout() -> None:
    with pytest.raises(ValueError, match="Timeout must be positive"):
        LokiExporter("http://localhost:3100", timeout_seconds=0)


def test_init_rejects_empty_job_label() -> None:
    with pytest.raises(ValueError, match="job label cannot be empty"):
        LokiExporter("http://localhost:3100", job_label="")


def test_init_rejects_whitespace_only_job_label() -> None:
    with pytest.raises(ValueError, match="job label cannot be empty"):
        LokiExporter("http://localhost:3100", job_label="   ")


def test_init_strips_job_label_whitespace() -> None:
    exporter = LokiExporter("http://localhost:3100", job_label="  hermes_test  ")
    assert exporter._job_label == "hermes_test"


def test_init_warns_on_credentials_in_url(caplog) -> None:
    with caplog.at_level("WARNING"):
        LokiExporter("http://user:pass@localhost:3100")
    assert "embedded credentials" in caplog.text


def test_loki_timestamp_ns_with_naive_datetime() -> None:
    # SpeedResult now requires timezone-aware datetimes
    result = SpeedResult(
        timestamp=datetime(2026, 3, 4, 12, 0, 0, tzinfo=timezone.utc),
        download_mbps=1.0,
        upload_mbps=1.0,
        ping_ms=1.0,
        server_name="x",
        server_location="y",
        server_id=1,
    )
    # Should not raise; datetime is UTC-aware
    ns = LokiExporter._to_loki_timestamp_ns(result)
    assert ns.isdigit()


def test_export_raises_on_bad_status() -> None:
    exporter = LokiExporter("http://localhost:3100")
    result = _sample_result()

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("src.exporters.loki_exporter.requests.post", return_value=mock_response):
        with pytest.raises(RuntimeError, match="500"):
            exporter.export(result)


# ---------------------------------------------------------------------------
# Integration tests — payload structure validation
# ---------------------------------------------------------------------------


def test_loki_payload_structure_complete() -> None:
    """Integration test: verify Loki payload conforms to expected schema."""
    exporter = LokiExporter("http://localhost:3100", job_label="hermes_integration")
    result = _sample_result()

    mock_response = MagicMock()
    mock_response.status_code = 204

    with patch(
        "src.exporters.loki_exporter.requests.post", return_value=mock_response
    ) as mock_post:
        exporter.export(result)

    # Extract and validate the payload
    assert mock_post.call_count == 1

    # Validate URL
    url = mock_post.call_args[0][0]
    assert url == "http://localhost:3100/loki/api/v1/push"

    # Validate headers
    headers = mock_post.call_args[1]["headers"]
    assert headers["Content-Type"] == "application/json"

    # Validate payload structure
    body_bytes = mock_post.call_args[1]["data"]
    body = json.loads(body_bytes.decode("utf-8"))

    # Top-level structure
    assert "streams" in body
    assert isinstance(body["streams"], list)
    assert len(body["streams"]) == 1

    stream = body["streams"][0]

    # Stream structure
    assert "stream" in stream
    assert "values" in stream

    # Labels
    labels = stream["stream"]
    assert labels["job"] == "hermes_integration"
    assert labels["server_name"] == "Berlin-1"
    assert labels["server_location"] == "DE"
    # Note: server_id is not in labels, only in the line content

    # Values array
    values = stream["values"]
    assert isinstance(values, list)
    assert len(values) == 1

    # Timestamp and line
    timestamp_ns, line_json = values[0]
    assert isinstance(timestamp_ns, str)
    assert timestamp_ns.isdigit()
    assert len(timestamp_ns) == 19  # nanosecond timestamp

    # Line content
    line = json.loads(line_json)
    assert line["download_mbps"] == pytest.approx(123.45)
    assert line["upload_mbps"] == pytest.approx(67.89)
    assert line["ping_ms"] == pytest.approx(10.2)
    assert line["server_name"] == "Berlin-1"
    assert line["server_location"] == "DE"
    assert line["server_id"] == 42


def test_loki_payload_includes_all_fields() -> None:
    """Integration test: verify all SpeedResult fields are included in Loki payload."""
    exporter = LokiExporter("http://localhost:3100", job_label="hermes_test")

    # Create result with all optional fields populated
    result = SpeedResult(
        timestamp=datetime(2026, 4, 29, 15, 30, 45, tzinfo=timezone.utc),
        download_mbps=456.78,
        upload_mbps=234.56,
        ping_ms=8.9,
        jitter_ms=2.5,
        isp_name="Comcast",
        server_name="NYC-Server",
        server_location="New York, NY",
        server_id=55555,
    )

    mock_response = MagicMock()
    mock_response.status_code = 204

    with patch(
        "src.exporters.loki_exporter.requests.post", return_value=mock_response
    ) as mock_post:
        exporter.export(result)

    body = json.loads(mock_post.call_args[1]["data"].decode("utf-8"))
    line = json.loads(body["streams"][0]["values"][0][1])

    # Verify all fields are present and correct
    assert line["download_mbps"] == pytest.approx(456.78)
    assert line["upload_mbps"] == pytest.approx(234.56)
    assert line["ping_ms"] == pytest.approx(8.9)
    assert line["jitter_ms"] == pytest.approx(2.5)
    assert line["isp_name"] == "Comcast"
    assert line["server_name"] == "NYC-Server"
    assert line["server_location"] == "New York, NY"
    assert line["server_id"] == 55555
    assert "timestamp" in line


def test_loki_payload_handles_none_values() -> None:
    """Integration test: verify Loki payload correctly handles None values."""
    exporter = LokiExporter("http://localhost:3100")

    result = SpeedResult(
        timestamp=datetime.now(timezone.utc),
        download_mbps=100.0,
        upload_mbps=50.0,
        ping_ms=10.0,
        jitter_ms=None,
        isp_name=None,
        server_name="Server",
        server_location="Location",
        server_id=1,
    )

    mock_response = MagicMock()
    mock_response.status_code = 204

    with patch(
        "src.exporters.loki_exporter.requests.post", return_value=mock_response
    ) as mock_post:
        exporter.export(result)

    body = json.loads(mock_post.call_args[1]["data"].decode("utf-8"))
    line = json.loads(body["streams"][0]["values"][0][1])

    # Verify None values are handled (should be null in JSON)
    assert line["jitter_ms"] is None
    assert line["isp_name"] is None

    # Verify other fields still present
    assert line["download_mbps"] == pytest.approx(100.0)
