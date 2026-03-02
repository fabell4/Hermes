"""
Tests for src/main.py and src/speedtest_runner.py
"""
from unittest.mock import MagicMock, patch

from src.services.speedtest_runner import display_results, run_speedtest


@patch("src.speedtest_runner.speedtest.Speedtest")
def test_run_speedtest(mock_st_class):
    mock_st = MagicMock()
    mock_st.download.return_value = 100_000_000
    mock_st.upload.return_value = 50_000_000
    mock_st.results.ping = 12.5
    mock_st.results.server = {"name": "Test Server"}
    mock_st_class.return_value = mock_st

    results = run_speedtest()

    assert results["download_mbps"] == 100.0
    assert results["upload_mbps"] == 50.0
    assert results["ping_ms"] == 12.5
    assert results["server"] == "Test Server"


def test_display_results(capsys):
    results = {
        "download_mbps": 100.0,
        "upload_mbps": 50.0,
        "ping_ms": 12.5,
        "server": "Test Server",
    }
    display_results(results)
    captured = capsys.readouterr()
    assert "100.0 Mbps" in captured.out
    assert "50.0 Mbps" in captured.out
    assert "12.5 ms" in captured.out
    assert "Test Server" in captured.out
