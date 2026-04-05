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


def test_loki_timestamp_ns_with_naive_datetime() -> None:
    result = SpeedResult(
        timestamp=datetime(2026, 3, 4, 12, 0, 0),  # no tzinfo
        download_mbps=1.0,
        upload_mbps=1.0,
        ping_ms=1.0,
        server_name="x",
        server_location="y",
        server_id=1,
    )
    # Should not raise; naive datetime is treated as UTC
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
