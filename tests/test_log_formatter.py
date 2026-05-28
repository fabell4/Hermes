"""Tests for src/log_formatter.py — JsonFormatter."""

import json
import logging


from src.log_formatter import JsonFormatter


def _make_record(
    message: str = "test message",
    level: int = logging.INFO,
    logger_name: str = "test.logger",
    exc_info: tuple | None = None,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name=logger_name,
        level=level,
        pathname="test.py",
        lineno=1,
        msg=message,
        args=(),
        exc_info=exc_info,
    )
    return record


# ── Output structure ──────────────────────────────────────────────────────────


def test_output_is_valid_json():
    fmt = JsonFormatter()
    output = fmt.format(_make_record())
    parsed = json.loads(output)
    assert isinstance(parsed, dict)


def test_output_contains_required_fields():
    fmt = JsonFormatter()
    parsed = json.loads(fmt.format(_make_record()))
    assert "time" in parsed
    assert "level" in parsed
    assert "logger" in parsed
    assert "message" in parsed


def test_output_is_single_line():
    fmt = JsonFormatter()
    output = fmt.format(_make_record())
    assert "\n" not in output


# ── Field values ──────────────────────────────────────────────────────────────


def test_level_field_matches_log_level():
    fmt = JsonFormatter()
    for level, name in [
        (logging.DEBUG, "DEBUG"),
        (logging.INFO, "INFO"),
        (logging.WARNING, "WARNING"),
        (logging.ERROR, "ERROR"),
        (logging.CRITICAL, "CRITICAL"),
    ]:
        parsed = json.loads(fmt.format(_make_record(level=level)))
        assert parsed["level"] == name


def test_logger_field_matches_logger_name():
    fmt = JsonFormatter()
    parsed = json.loads(fmt.format(_make_record(logger_name="src.main")))
    assert parsed["logger"] == "src.main"


def test_message_field_matches_log_message():
    fmt = JsonFormatter()
    parsed = json.loads(fmt.format(_make_record(message="hello world")))
    assert parsed["message"] == "hello world"


def test_time_field_is_iso8601_utc():
    import re

    fmt = JsonFormatter()
    parsed = json.loads(fmt.format(_make_record()))
    # e.g. "2026-05-18T14:23:45.123Z"
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", parsed["time"])


# ── Exception handling ────────────────────────────────────────────────────────


def test_exc_info_absent_when_no_exception():
    fmt = JsonFormatter()
    parsed = json.loads(fmt.format(_make_record()))
    assert "exc_info" not in parsed


def test_exc_info_present_on_exception_record():
    fmt = JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    record = _make_record(exc_info=exc_info)
    parsed = json.loads(fmt.format(record))
    assert "exc_info" in parsed
    assert "ValueError" in parsed["exc_info"]
    assert "boom" in parsed["exc_info"]


# ── Encoding ──────────────────────────────────────────────────────────────────


def test_non_ascii_characters_preserved():
    fmt = JsonFormatter()
    parsed = json.loads(fmt.format(_make_record(message="速度テスト — réseau")))
    assert parsed["message"] == "速度テスト — réseau"


def test_message_with_format_args():
    """Log records that use % formatting are resolved correctly."""
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Down: %s Mbps",
        args=("120.5",),
        exc_info=None,
    )
    fmt = JsonFormatter()
    parsed = json.loads(fmt.format(record))
    assert parsed["message"] == "Down: 120.5 Mbps"
