"""Defensive tests for SpeedtestRunner._attempt() against unexpected external data.

Principle 2 — Don't trust external data:
  speedtest.net may change its schema, return unexpected types, or omit fields
  at any time.  For every field parsed from the external response we test:
    1. Valid input   — the happy path
    2. Invalid input — assert a safe fallback (None) rather than a crash
    3. Unexpected    — wrong type, empty string, or completely absent key
"""
# pylint: disable=missing-function-docstring,protected-access

import pytest
from unittest.mock import MagicMock, patch

from src.services.speedtest_runner import SpeedtestRunner


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

_UNSET = object()  # sentinel so client=None can be passed explicitly


def _make_mock_st(
    *,
    best: dict | None = None,
    download: float = 100_000_000,
    upload: float = 50_000_000,
    ping: float = 12.5,
    jitter=None,
    client=_UNSET,
) -> MagicMock:
    """Build a fully-configured speedtest.Speedtest mock."""
    if best is None:
        best = {
            "sponsor": "Test ISP",
            "name": "Test City",
            "country": "DE",
            "id": "1234",
        }
    if client is _UNSET:
        client = {"isp": "Test ISP"}
    mock_st = MagicMock()
    mock_st.get_best_server.return_value = best
    mock_st.download.return_value = download
    mock_st.upload.return_value = upload
    mock_st.results.ping = ping
    mock_st.results.jitter = jitter
    mock_st.results.client = client
    return mock_st


# ---------------------------------------------------------------------------
# server_id — three categories
# ---------------------------------------------------------------------------


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_server_id_numeric_string_parses_to_int(mock_cls):
    """1. Valid: a numeric string id ('9876') is coerced to int 9876."""
    mock_cls.return_value = _make_mock_st(
        best={"sponsor": "ISP", "name": "City", "country": "DE", "id": "9876"}
    )
    assert SpeedtestRunner()._attempt().server_id == 9876


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_server_id_integer_value_parses_correctly(mock_cls):
    """1. Valid: a plain int id is stored correctly."""
    mock_cls.return_value = _make_mock_st(
        best={"sponsor": "ISP", "name": "City", "country": "DE", "id": 42}
    )
    assert SpeedtestRunner()._attempt().server_id == 42


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_server_id_absent_key_becomes_none(mock_cls):
    """2. Invalid: missing 'id' key must produce None rather than a crash."""
    mock_cls.return_value = _make_mock_st(
        best={"sponsor": "ISP", "name": "City", "country": "DE"}
    )
    assert SpeedtestRunner()._attempt().server_id is None


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_server_id_non_numeric_string_becomes_none(mock_cls):
    """3. Unexpected: a non-numeric string must fall back to None without raising."""
    mock_cls.return_value = _make_mock_st(
        best={"sponsor": "ISP", "name": "City", "country": "DE", "id": "not-an-id"}
    )
    assert SpeedtestRunner()._attempt().server_id is None


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_server_id_float_string_becomes_none(mock_cls):
    """3. Unexpected: a float-format string like '12.3' cannot round-trip to int — None."""
    mock_cls.return_value = _make_mock_st(
        best={"sponsor": "ISP", "name": "City", "country": "DE", "id": "12.3"}
    )
    assert SpeedtestRunner()._attempt().server_id is None


# ---------------------------------------------------------------------------
# isp_name / client dict — three categories
# ---------------------------------------------------------------------------


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_isp_name_extracted_from_valid_client_dict(mock_cls):
    """1. Valid: isp_name is correctly extracted when client is a proper dict."""
    mock_cls.return_value = _make_mock_st(client={"isp": "Fancy ISP"})
    assert SpeedtestRunner()._attempt().isp_name == "Fancy ISP"


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_isp_name_empty_string_normalised_to_none(mock_cls):
    """2. Invalid: an empty isp string must be normalised to None."""
    mock_cls.return_value = _make_mock_st(client={"isp": ""})
    assert SpeedtestRunner()._attempt().isp_name is None


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_isp_name_absent_key_becomes_none(mock_cls):
    """2. Invalid: isp key missing from client dict must produce None."""
    mock_cls.return_value = _make_mock_st(client={"country": "DE"})
    assert SpeedtestRunner()._attempt().isp_name is None


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_isp_name_null_client_becomes_none(mock_cls):
    """3. Unexpected: client=None must not raise AttributeError."""
    mock_cls.return_value = _make_mock_st(client=None)
    assert SpeedtestRunner()._attempt().isp_name is None


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_isp_name_non_dict_client_becomes_none(mock_cls):
    """3. Unexpected: client returned as a non-dict object must not crash."""
    mock_st = _make_mock_st()
    mock_st.results.client = "unexpected-string"
    mock_cls.return_value = mock_st
    assert SpeedtestRunner()._attempt().isp_name is None


# ---------------------------------------------------------------------------
# jitter_ms — three categories
# ---------------------------------------------------------------------------


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_jitter_valid_float_is_stored(mock_cls):
    """1. Valid: a float jitter value is correctly rounded and stored."""
    mock_cls.return_value = _make_mock_st(jitter=5.25)
    assert SpeedtestRunner()._attempt().jitter_ms == pytest.approx(5.25)


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_jitter_absent_becomes_none(mock_cls):
    """2. Invalid: absent jitter attribute must produce None."""
    mock_cls.return_value = _make_mock_st(jitter=None)
    assert SpeedtestRunner()._attempt().jitter_ms is None


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_jitter_numeric_string_parses_to_float(mock_cls):
    """3. Unexpected: jitter returned as a numeric string is parsed to float."""
    mock_cls.return_value = _make_mock_st(jitter="7.8")
    assert SpeedtestRunner()._attempt().jitter_ms == pytest.approx(7.8)


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_jitter_empty_string_becomes_none(mock_cls):
    """3. Unexpected: an empty-string jitter must not raise ValueError — fall back to None."""
    mock_cls.return_value = _make_mock_st(jitter="")
    assert SpeedtestRunner()._attempt().jitter_ms is None


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_jitter_non_numeric_string_becomes_none(mock_cls):
    """3. Unexpected: a non-numeric jitter string must fall back to None without raising."""
    mock_cls.return_value = _make_mock_st(jitter="bad-value")
    assert SpeedtestRunner()._attempt().jitter_ms is None


# ---------------------------------------------------------------------------
# server_name / location — fallback for missing keys
# ---------------------------------------------------------------------------


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_missing_sponsor_falls_back_to_unknown(mock_cls):
    """2. Invalid: absent 'sponsor' key must produce the string 'Unknown'."""
    mock_cls.return_value = _make_mock_st(
        best={"name": "City", "country": "DE", "id": "1"}
    )
    assert SpeedtestRunner()._attempt().server_name == "Unknown"


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_missing_location_fields_produce_safe_string(mock_cls):
    """2. Invalid: absent name/country keys produce a safe empty-formatted string."""
    mock_cls.return_value = _make_mock_st(best={"sponsor": "ISP", "id": "1"})
    result = SpeedtestRunner()._attempt()
    assert result.server_location == ", "


# ---------------------------------------------------------------------------
# Boundary / zero values
# ---------------------------------------------------------------------------


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_zero_download_speed_is_valid(mock_cls):
    """Boundary: zero download speed is stored as 0.0."""
    mock_cls.return_value = _make_mock_st(download=0)
    assert SpeedtestRunner()._attempt().download_mbps == pytest.approx(0.0)


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_zero_upload_speed_is_valid(mock_cls):
    """Boundary: zero upload speed is stored as 0.0."""
    mock_cls.return_value = _make_mock_st(upload=0)
    assert SpeedtestRunner()._attempt().upload_mbps == pytest.approx(0.0)


@patch("src.services.speedtest_runner.speedtest.Speedtest")
def test_zero_ping_is_valid(mock_cls):
    """Boundary: zero ping is stored as 0.0."""
    mock_st = _make_mock_st()
    mock_st.results.ping = 0.0
    mock_cls.return_value = mock_st
    assert SpeedtestRunner()._attempt().ping_ms == pytest.approx(0.0)
