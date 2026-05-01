"""Defensive tests for SpeedtestRunner._attempt() against unexpected external data.

Principle 2 — Don't trust external data:
  Ookla speedtest CLI may change its JSON schema, return unexpected types, or omit
  fields at any time. For every field parsed from the external response we test:
    1. Valid input   — the happy path
    2. Invalid input — assert a safe fallback (None) rather than a crash
    3. Unexpected    — wrong type, empty string, or completely absent key
"""
# pylint: disable=missing-function-docstring,protected-access

import json
import pytest
from unittest.mock import Mock, patch

from src.services.speedtest_runner import SpeedtestRunner


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


def _make_mock_json(
    *,
    download_bandwidth: int = 12500000,
    upload_bandwidth: int = 6250000,
    latency: float = 12.5,
    jitter: float | None = 2.3,
    server_name: str = "Test ISP",
    server_location: str = "Test City",
    server_country: str = "DE",
    server_id: int | str | None = 1234,
    isp: str | None = "Test ISP",
) -> str:
    """Build a mock Ookla CLI JSON response."""
    data = {
        "download": {"bandwidth": download_bandwidth},
        "upload": {"bandwidth": upload_bandwidth},
        "ping": {"latency": latency},
        "server": {
            "name": server_name,
            "location": server_location,
            "country": server_country,
        },
    }
    if jitter is not None:
        data["ping"]["jitter"] = jitter
    if server_id is not None:
        data["server"]["id"] = server_id
    if isp is not None:
        data["isp"] = isp
    return json.dumps(data)


# ---------------------------------------------------------------------------
# server_id — three categories
# ---------------------------------------------------------------------------


@patch("src.services.speedtest_runner.subprocess.run")
def test_server_id_integer_value_parses_correctly(mock_run):
    """1. Valid: a plain int id is stored correctly."""
    mock_run.return_value = Mock(stdout=_make_mock_json(server_id=42), returncode=0)
    assert SpeedtestRunner("/usr/bin/speedtest")._attempt().server_id == 42


@patch("src.services.speedtest_runner.subprocess.run")
def test_server_id_absent_key_becomes_none(mock_run):
    """2. Invalid: missing 'id' key must produce None rather than a crash."""
    mock_run.return_value = Mock(stdout=_make_mock_json(server_id=None), returncode=0)
    assert SpeedtestRunner("/usr/bin/speedtest")._attempt().server_id is None


# ---------------------------------------------------------------------------
# isp_name — three categories
# ---------------------------------------------------------------------------


@patch("src.services.speedtest_runner.subprocess.run")
def test_isp_name_extracted_from_valid_json(mock_run):
    """1. Valid: isp_name is correctly extracted from JSON."""
    mock_run.return_value = Mock(stdout=_make_mock_json(isp="Fancy ISP"), returncode=0)
    assert SpeedtestRunner("/usr/bin/speedtest")._attempt().isp_name == "Fancy ISP"


@patch("src.services.speedtest_runner.subprocess.run")
def test_isp_name_absent_key_becomes_none(mock_run):
    """2. Invalid: missing isp key must produce None."""
    mock_run.return_value = Mock(stdout=_make_mock_json(isp=None), returncode=0)
    assert SpeedtestRunner("/usr/bin/speedtest")._attempt().isp_name is None


# ---------------------------------------------------------------------------
# jitter_ms — three categories
# ---------------------------------------------------------------------------


@patch("src.services.speedtest_runner.subprocess.run")
def test_jitter_ms_valid_float_rounded_correctly(mock_run):
    """1. Valid: jitter is rounded to 2 decimal places."""
    mock_run.return_value = Mock(stdout=_make_mock_json(jitter=3.456), returncode=0)
    assert SpeedtestRunner("/usr/bin/speedtest")._attempt().jitter_ms == pytest.approx(
        3.46
    )


@patch("src.services.speedtest_runner.subprocess.run")
def test_jitter_ms_absent_becomes_none(mock_run):
    """2. Invalid: missing jitter key must produce None."""
    mock_run.return_value = Mock(stdout=_make_mock_json(jitter=None), returncode=0)
    assert SpeedtestRunner("/usr/bin/speedtest")._attempt().jitter_ms is None


@patch("src.services.speedtest_runner.subprocess.run")
def test_jitter_ms_zero_value_accepted(mock_run):
    """1. Valid: jitter=0.0 is a valid measurement."""
    mock_run.return_value = Mock(stdout=_make_mock_json(jitter=0.0), returncode=0)
    assert SpeedtestRunner("/usr/bin/speedtest")._attempt().jitter_ms == pytest.approx(
        0.0
    )


# ---------------------------------------------------------------------------
# bandwidth conversion — download/upload
# ---------------------------------------------------------------------------


@patch("src.services.speedtest_runner.subprocess.run")
def test_download_bandwidth_converts_correctly(mock_run):
    """1. Valid: bandwidth in bytes/s * 8 converts to Mbps correctly."""
    # 12500000 bytes/s * 8 = 100000000 bits/s = 100 Mbps
    mock_run.return_value = Mock(
        stdout=_make_mock_json(download_bandwidth=12500000), returncode=0
    )
    assert SpeedtestRunner(
        "/usr/bin/speedtest"
    )._attempt().download_mbps == pytest.approx(100.0)


@patch("src.services.speedtest_runner.subprocess.run")
def test_upload_bandwidth_converts_correctly(mock_run):
    """1. Valid: bandwidth in bytes/s * 8 converts to Mbps correctly."""
    # 6250000 bytes/s * 8 = 50000000 bits/s = 50 Mbps
    mock_run.return_value = Mock(
        stdout=_make_mock_json(upload_bandwidth=6250000), returncode=0
    )
    assert SpeedtestRunner(
        "/usr/bin/speedtest"
    )._attempt().upload_mbps == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# server location formatting
# ---------------------------------------------------------------------------


@patch("src.services.speedtest_runner.subprocess.run")
def test_server_location_formatted_correctly(mock_run):
    """1. Valid: location and country are concatenated correctly."""
    mock_run.return_value = Mock(
        stdout=_make_mock_json(
            server_location="New York", server_country="United States"
        ),
        returncode=0,
    )
    result = SpeedtestRunner("/usr/bin/speedtest")._attempt()
    assert result.server_location == "New York, United States"


@patch("src.services.speedtest_runner.subprocess.run")
def test_server_name_defaults_to_unknown(mock_run):
    """2. Invalid: missing server name defaults to 'Unknown'."""
    data = json.loads(_make_mock_json())
    del data["server"]["name"]
    mock_run.return_value = Mock(stdout=json.dumps(data), returncode=0)
    assert SpeedtestRunner("/usr/bin/speedtest")._attempt().server_name == "Unknown"


# ---------------------------------------------------------------------------
# Boundary / zero values
# ---------------------------------------------------------------------------


@patch("src.services.speedtest_runner.subprocess.run")
def test_zero_download_speed_is_valid(mock_run):
    """Boundary: zero download speed is stored as 0.0."""
    mock_run.return_value = Mock(
        stdout=_make_mock_json(download_bandwidth=0), returncode=0
    )
    assert SpeedtestRunner(
        "/usr/bin/speedtest"
    )._attempt().download_mbps == pytest.approx(0.0)


@patch("src.services.speedtest_runner.subprocess.run")
def test_zero_upload_speed_is_valid(mock_run):
    """Boundary: zero upload speed is stored as 0.0."""
    mock_run.return_value = Mock(
        stdout=_make_mock_json(upload_bandwidth=0), returncode=0
    )
    assert SpeedtestRunner(
        "/usr/bin/speedtest"
    )._attempt().upload_mbps == pytest.approx(0.0)


@patch("src.services.speedtest_runner.subprocess.run")
def test_missing_server_location_produces_safe_string(mock_run):
    """2. Invalid: absent location/country keys produce a safe comma-separated string."""
    data = json.loads(_make_mock_json())
    del data["server"]["location"]
    del data["server"]["country"]
    mock_run.return_value = Mock(stdout=json.dumps(data), returncode=0)
    result = SpeedtestRunner("/usr/bin/speedtest")._attempt()
    assert result.server_location == ", "


@patch("src.services.speedtest_runner.subprocess.run")
def test_zero_ping_is_valid(mock_run):
    """Boundary: zero ping is stored as 0.0."""
    mock_run.return_value = Mock(stdout=_make_mock_json(latency=0.0), returncode=0)
    assert SpeedtestRunner("/usr/bin/speedtest")._attempt().ping_ms == pytest.approx(
        0.0
    )
