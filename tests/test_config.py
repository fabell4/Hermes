"""Tests for src/config.py — environment variable parsing helpers and startup validation."""
# pylint: disable=missing-function-docstring

import subprocess
import sys


# ---------------------------------------------------------------------------
# _get_int helper
# ---------------------------------------------------------------------------


def test_get_int_returns_default_when_env_not_set(monkeypatch):
    """_get_int returns the default when the env var is absent."""
    monkeypatch.delenv("TEST_INT_VAR", raising=False)
    from src.config import _get_int  # noqa: PLC0415

    assert _get_int("TEST_INT_VAR", 42) == 42


def test_get_int_returns_parsed_value(monkeypatch):
    """_get_int returns the integer value when the env var is a valid integer."""
    monkeypatch.setenv("TEST_INT_VAR", "99")
    from src.config import _get_int  # noqa: PLC0415

    assert _get_int("TEST_INT_VAR", 0) == 99


def test_get_int_returns_default_on_invalid_value(monkeypatch):
    """_get_int returns default and logs a warning when the value is not an integer."""
    monkeypatch.setenv("TEST_INT_VAR", "notanint")
    from src.config import _get_int  # noqa: PLC0415

    assert _get_int("TEST_INT_VAR", 7) == 7


# ---------------------------------------------------------------------------
# _get_bool helper
# ---------------------------------------------------------------------------


def test_get_bool_returns_default_when_env_not_set(monkeypatch):
    """_get_bool returns default when the env var is absent."""
    monkeypatch.delenv("TEST_BOOL_VAR", raising=False)
    from src.config import _get_bool  # noqa: PLC0415

    assert _get_bool("TEST_BOOL_VAR", False) is False


def test_get_bool_accepts_true_string(monkeypatch):
    """_get_bool returns True for 'true' (case insensitive)."""
    monkeypatch.setenv("TEST_BOOL_VAR", "TRUE")
    from src.config import _get_bool  # noqa: PLC0415

    assert _get_bool("TEST_BOOL_VAR", False) is True


def test_get_bool_accepts_1_string(monkeypatch):
    """_get_bool returns True for '1'."""
    monkeypatch.setenv("TEST_BOOL_VAR", "1")
    from src.config import _get_bool  # noqa: PLC0415

    assert _get_bool("TEST_BOOL_VAR", False) is True


def test_get_bool_accepts_yes_string(monkeypatch):
    """_get_bool returns True for 'yes' (case insensitive)."""
    monkeypatch.setenv("TEST_BOOL_VAR", "yes")
    from src.config import _get_bool  # noqa: PLC0415

    assert _get_bool("TEST_BOOL_VAR", False) is True


def test_get_bool_returns_false_for_no_string(monkeypatch):
    """_get_bool returns False for 'no'."""
    monkeypatch.setenv("TEST_BOOL_VAR", "no")
    from src.config import _get_bool  # noqa: PLC0415

    assert _get_bool("TEST_BOOL_VAR", True) is False


def test_get_bool_returns_false_for_unrecognized_string(monkeypatch):
    """_get_bool returns False for unrecognized values."""
    monkeypatch.setenv("TEST_BOOL_VAR", "maybe")
    from src.config import _get_bool  # noqa: PLC0415

    assert _get_bool("TEST_BOOL_VAR", True) is False


# ---------------------------------------------------------------------------
# _get_csv_list helper
# ---------------------------------------------------------------------------


def test_get_csv_list_returns_default_when_env_not_set(monkeypatch):
    """_get_csv_list returns default when the env var is absent."""
    monkeypatch.delenv("TEST_CSV_VAR", raising=False)
    from src.config import _get_csv_list  # noqa: PLC0415

    assert _get_csv_list("TEST_CSV_VAR", ["a"]) == ["a"]


def test_get_csv_list_parses_comma_separated(monkeypatch):
    """_get_csv_list returns a list from comma-separated values."""
    monkeypatch.setenv("TEST_CSV_VAR", "csv,sqlite,loki")
    from src.config import _get_csv_list  # noqa: PLC0415

    assert _get_csv_list("TEST_CSV_VAR", []) == ["csv", "sqlite", "loki"]


def test_get_csv_list_strips_whitespace(monkeypatch):
    """_get_csv_list strips whitespace from individual values."""
    monkeypatch.setenv("TEST_CSV_VAR", " csv , sqlite ")
    from src.config import _get_csv_list  # noqa: PLC0415

    assert _get_csv_list("TEST_CSV_VAR", []) == ["csv", "sqlite"]


def test_get_csv_list_returns_default_for_empty_values(monkeypatch):
    """_get_csv_list returns default when all parsed values are empty."""
    monkeypatch.setenv("TEST_CSV_VAR", "  ,  ")
    from src.config import _get_csv_list  # noqa: PLC0415

    assert _get_csv_list("TEST_CSV_VAR", ["default"]) == ["default"]


# ---------------------------------------------------------------------------
# _get_str helper
# ---------------------------------------------------------------------------


def test_get_str_returns_default_when_env_not_set(monkeypatch):
    """_get_str returns default when the env var is absent."""
    monkeypatch.delenv("TEST_STR_VAR", raising=False)
    from src.config import _get_str  # noqa: PLC0415

    assert _get_str("TEST_STR_VAR", "fallback") == "fallback"


def test_get_str_returns_value_when_set(monkeypatch):
    """_get_str returns the env var value when present."""
    monkeypatch.setenv("TEST_STR_VAR", "hello")
    from src.config import _get_str  # noqa: PLC0415

    assert _get_str("TEST_STR_VAR", "fallback") == "hello"


def test_get_str_returns_default_for_whitespace_only(monkeypatch):
    """_get_str returns default when the env var is whitespace-only."""
    monkeypatch.setenv("TEST_STR_VAR", "   ")
    from src.config import _get_str  # noqa: PLC0415

    assert _get_str("TEST_STR_VAR", "fallback") == "fallback"


# ---------------------------------------------------------------------------
# API_KEY validation — subprocess test
# ---------------------------------------------------------------------------


def test_short_api_key_causes_startup_failure():
    """config.py raises SystemExit(1) when API_KEY is shorter than 32 characters."""
    result = subprocess.run(
        [sys.executable, "-c", "import src.config"],
        env={
            "API_KEY": "tooshort",
            "PATH": "",
            "PYTHONPATH": ".",
        },
        capture_output=True,
        cwd="c:/Users/psywa/source/repos/projects/Hermes",
    )
    assert result.returncode == 1
    assert b"API_KEY" in result.stderr


def test_valid_api_key_does_not_cause_startup_failure():
    """config.py imports successfully when API_KEY is at least 32 characters."""
    import os

    result = subprocess.run(
        [sys.executable, "-c", "import src.config; print('ok')"],
        env={
            **os.environ,
            "API_KEY": "a" * 32,
        },
        capture_output=True,
        cwd="c:/Users/psywa/source/repos/projects/Hermes",
    )
    assert result.returncode == 0
    assert b"ok" in result.stdout
