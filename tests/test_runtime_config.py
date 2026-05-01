"""Tests for src/runtime_config.py — JSON persistence layer."""

# Pytest fixtures intentionally shadow the outer fixture name — this is standard pytest.
# pylint: disable=redefined-outer-name

import json
from unittest.mock import patch

import pytest

import src.runtime_config as runtime_config


@pytest.fixture()
def config_path(tmp_path, monkeypatch):
    """Redirect RUNTIME_CONFIG_PATH to a temporary directory for each test."""
    path = tmp_path / "data" / "runtime_config.json"
    monkeypatch.setattr(runtime_config, "RUNTIME_CONFIG_PATH", path)
    return path


# ---------------------------------------------------------------------------
# load()
# ---------------------------------------------------------------------------


def test_load_returns_empty_when_file_missing(config_path):
    """load() returns {} when the config file does not exist."""
    assert not config_path.exists()
    assert runtime_config.load() == {}


def test_load_returns_data_when_file_exists(config_path):
    """load() returns the parsed JSON when the file is present."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"interval_minutes": 30}', encoding="utf-8")
    assert runtime_config.load() == {"interval_minutes": 30}


def test_load_returns_empty_on_invalid_json(config_path):
    """load() returns {} and does not raise when the file contains invalid JSON."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("not valid json", encoding="utf-8")
    assert runtime_config.load() == {}


# ---------------------------------------------------------------------------
# save()
# ---------------------------------------------------------------------------


def test_save_creates_file_and_writes_data(config_path):
    """save() creates the config file and writes the given data."""
    runtime_config.save({"interval_minutes": 15})
    assert config_path.exists()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["interval_minutes"] == 15


def test_save_merges_with_existing_data(config_path):
    """save() merges new keys with existing data rather than overwriting."""
    runtime_config.save({"interval_minutes": 15})
    runtime_config.save({"enabled_exporters": ["csv"]})
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["interval_minutes"] == 15
    assert data["enabled_exporters"] == ["csv"]


def test_save_raises_on_os_error(config_path, monkeypatch):
    """save() re-raises Exception when the file cannot be written (atomic write)."""
    # With atomic write, we need to mock tempfile.mkstemp to simulate failure
    import tempfile

    def _bad_mkstemp(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(tempfile, "mkstemp", _bad_mkstemp)
    with pytest.raises(OSError, match="disk full"):
        runtime_config.save({"interval_minutes": 5})


# ---------------------------------------------------------------------------
# get_interval_minutes()
# ---------------------------------------------------------------------------


def test_get_interval_minutes_returns_default_when_missing(config_path):
    """get_interval_minutes() returns the default when no value is persisted."""
    assert not config_path.exists()
    assert runtime_config.get_interval_minutes(60) == 60


def test_get_interval_minutes_returns_persisted_value(config_path):
    """get_interval_minutes() returns the value stored in the config file."""
    runtime_config.save({"interval_minutes": 45})
    assert config_path.exists()
    assert runtime_config.get_interval_minutes(60) == 45


def test_get_interval_minutes_returns_default_on_invalid_value(config_path):
    """get_interval_minutes() returns the default when the stored value is not an int."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"interval_minutes": "not_a_number"}', encoding="utf-8")
    assert runtime_config.get_interval_minutes(60) == 60


# ---------------------------------------------------------------------------
# set_interval_minutes()
# ---------------------------------------------------------------------------


def test_set_interval_minutes_persists_value(config_path):
    """set_interval_minutes() writes the value so get_interval_minutes reads it back."""
    runtime_config.set_interval_minutes(20)
    assert config_path.exists()
    assert runtime_config.get_interval_minutes(60) == 20


# ---------------------------------------------------------------------------
# get_enabled_exporters()
# ---------------------------------------------------------------------------


def test_get_enabled_exporters_returns_default_when_missing(config_path):
    """get_enabled_exporters() returns the default when no value is persisted."""
    assert not config_path.exists()
    assert runtime_config.get_enabled_exporters(["csv"]) == ["csv"]


def test_get_enabled_exporters_returns_persisted_value(config_path):
    """get_enabled_exporters() returns the list stored in the config file."""
    runtime_config.save({"enabled_exporters": ["csv", "loki"]})
    assert config_path.exists()
    assert runtime_config.get_enabled_exporters(["csv"]) == ["csv", "loki"]


def test_get_enabled_exporters_returns_default_on_invalid_type(config_path):
    """get_enabled_exporters() returns the default when the stored value is not a list."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"enabled_exporters": "not_a_list"}', encoding="utf-8")
    assert runtime_config.get_enabled_exporters(["csv"]) == ["csv"]


# ---------------------------------------------------------------------------
# set_enabled_exporters()
# ---------------------------------------------------------------------------


def test_set_enabled_exporters_persists_value(config_path):
    """set_enabled_exporters() writes the list so get_enabled_exporters reads it back."""
    runtime_config.set_enabled_exporters(["prometheus"])
    assert config_path.exists()
    assert runtime_config.get_enabled_exporters([]) == ["prometheus"]


# ---------------------------------------------------------------------------
# trigger_run() / consume_run_trigger()
# ---------------------------------------------------------------------------


def test_trigger_run_creates_trigger_file(tmp_path, monkeypatch):
    """trigger_run() creates the trigger sentinel file on disk."""
    trigger_path = tmp_path / "data" / ".run_trigger"
    monkeypatch.setattr(runtime_config, "RUN_TRIGGER_PATH", trigger_path)
    monkeypatch.setattr(
        runtime_config, "RUNTIME_CONFIG_PATH", tmp_path / "data" / "runtime_config.json"
    )

    runtime_config.trigger_run()

    assert trigger_path.exists()


def test_consume_run_trigger_returns_true_and_deletes_file(tmp_path, monkeypatch):
    """consume_run_trigger() returns True and removes the file when it exists."""
    trigger_path = tmp_path / "data" / ".run_trigger"
    trigger_path.parent.mkdir(parents=True, exist_ok=True)
    trigger_path.touch()
    monkeypatch.setattr(runtime_config, "RUN_TRIGGER_PATH", trigger_path)

    result = runtime_config.consume_run_trigger()

    assert result is True
    assert not trigger_path.exists()


def test_consume_run_trigger_returns_false_when_no_file(tmp_path, monkeypatch):
    """consume_run_trigger() returns False when the trigger file is absent."""
    trigger_path = tmp_path / "data" / ".run_trigger"
    monkeypatch.setattr(runtime_config, "RUN_TRIGGER_PATH", trigger_path)

    result = runtime_config.consume_run_trigger()

    assert result is False


def test_consume_run_trigger_returns_true_on_unlink_error(tmp_path, monkeypatch):
    """unlink raises OSError — should still return True (file was there)."""
    trigger_path = tmp_path / "data" / ".run_trigger"
    trigger_path.parent.mkdir(parents=True, exist_ok=True)
    trigger_path.touch()
    monkeypatch.setattr(runtime_config, "RUN_TRIGGER_PATH", trigger_path)

    with patch.object(type(trigger_path), "unlink", side_effect=OSError("locked")):
        result = runtime_config.consume_run_trigger()

    assert result is True


# ---------------------------------------------------------------------------
# mark_running() / mark_done() / is_running()
# ---------------------------------------------------------------------------


@pytest.fixture()
def running_path(tmp_path, monkeypatch):
    """Redirect RUNNING_PATH and RUNTIME_CONFIG_PATH to a temporary directory for each test."""
    path = tmp_path / "data" / ".running"
    monkeypatch.setattr(runtime_config, "RUNNING_PATH", path)
    monkeypatch.setattr(
        runtime_config, "RUNTIME_CONFIG_PATH", tmp_path / "data" / "runtime_config.json"
    )
    return path


def test_mark_running_creates_sentinel_file(running_path):
    """mark_running() creates the running sentinel file on disk."""
    runtime_config.mark_running()
    assert running_path.exists()


def test_mark_done_removes_sentinel_file(running_path):
    """mark_done() removes the running sentinel file when it exists."""
    running_path.parent.mkdir(parents=True, exist_ok=True)
    running_path.touch()
    runtime_config.mark_done()
    assert not running_path.exists()


def test_mark_done_is_noop_when_file_absent(running_path):
    """mark_done() does not raise when the sentinel file is already absent."""
    # Should not raise even if the file doesn't exist.
    assert not running_path.exists()
    runtime_config.mark_done()


def test_is_running_returns_true_when_file_exists(running_path):
    """is_running() returns True when the sentinel file is present."""
    running_path.parent.mkdir(parents=True, exist_ok=True)
    running_path.touch()
    assert runtime_config.is_running() is True


def test_is_running_returns_false_when_file_absent(running_path):
    """is_running() returns False when the sentinel file is absent."""
    assert not running_path.exists()
    assert runtime_config.is_running() is False


# ---------------------------------------------------------------------------
# get/set_next_run_at
# ---------------------------------------------------------------------------


def test_get_next_run_at_returns_none_when_missing(config_path):
    """get_next_run_at() returns None when no value is persisted."""
    assert not config_path.exists()
    assert runtime_config.get_next_run_at() is None


def test_set_next_run_at_persists_value(config_path):
    """set_next_run_at() writes the timestamp so get_next_run_at reads it back."""
    runtime_config.set_next_run_at("2026-04-16T12:00:00+00:00")
    assert config_path.exists()
    assert runtime_config.get_next_run_at() == "2026-04-16T12:00:00+00:00"


# ---------------------------------------------------------------------------
# get/set_last_run_at
# ---------------------------------------------------------------------------


def test_get_last_run_at_returns_none_when_missing(config_path):
    """get_last_run_at() returns None when no value is persisted."""
    assert not config_path.exists()
    assert runtime_config.get_last_run_at() is None


def test_set_last_run_at_persists_value(config_path):
    """set_last_run_at() writes the timestamp so get_last_run_at reads it back."""
    runtime_config.set_last_run_at("2026-04-16T11:00:00+00:00")
    assert config_path.exists()
    assert runtime_config.get_last_run_at() == "2026-04-16T11:00:00+00:00"


# ---------------------------------------------------------------------------
# get/set_scheduler_paused
# ---------------------------------------------------------------------------
def test_get_scheduler_paused_defaults_to_false(config_path):
    """Returns False when the key is not present in the config."""
    assert not config_path.exists()
    assert runtime_config.get_scheduler_paused() is False


def test_set_scheduler_paused_persists_true(config_path):
    """Persists paused=True and get_scheduler_paused returns True."""
    runtime_config.set_scheduler_paused(True)
    assert config_path.exists()
    assert runtime_config.get_scheduler_paused() is True


def test_set_scheduler_paused_persists_false(config_path):
    """Persists paused=False after previously being True."""
    runtime_config.set_scheduler_paused(True)
    runtime_config.set_scheduler_paused(False)
    assert config_path.exists()
    assert runtime_config.get_scheduler_paused() is False


# ---------------------------------------------------------------------------
# load() — validation edge cases (via writing raw JSON to the config file)
# ---------------------------------------------------------------------------


def test_load_returns_empty_when_config_is_not_dict(config_path, caplog):
    """load() returns {} and logs a warning when the config file contains a JSON array."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("[1, 2, 3]", encoding="utf-8")

    with caplog.at_level("WARNING"):
        result = runtime_config.load()

    assert result == {}
    assert "not a dict" in caplog.text


def test_load_discards_interval_out_of_range_low(config_path, caplog):
    """load() discards interval_minutes when it is below the valid range (< 1)."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"interval_minutes": 0}', encoding="utf-8")

    with caplog.at_level("WARNING"):
        result = runtime_config.load()

    assert "interval_minutes" not in result
    assert "out of range" in caplog.text


def test_load_discards_interval_out_of_range_high(config_path, caplog):
    """load() discards interval_minutes when it exceeds the maximum (> 10080)."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"interval_minutes": 99999}', encoding="utf-8")

    with caplog.at_level("WARNING"):
        result = runtime_config.load()

    assert "interval_minutes" not in result
    assert "out of range" in caplog.text


def test_load_discards_enabled_exporters_empty_after_filtering(config_path, caplog):
    """load() discards enabled_exporters when it resolves to an empty list after filtering."""
    # List with only empty strings — all filtered out
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"enabled_exporters": ["  ", ""]}', encoding="utf-8")

    with caplog.at_level("WARNING"):
        result = runtime_config.load()

    assert "enabled_exporters" not in result
    assert "empty" in caplog.text


def test_load_discards_enabled_exporters_not_a_list(config_path, caplog):
    """load() discards enabled_exporters when it is not a list."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"enabled_exporters": 42}', encoding="utf-8")

    with caplog.at_level("WARNING"):
        result = runtime_config.load()

    assert "enabled_exporters" not in result
    assert "not a list" in caplog.text


def test_load_discards_scanning_disabled_not_bool(config_path, caplog):
    """load() discards scanning_disabled when it is not a boolean."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"scanning_disabled": "yes"}', encoding="utf-8")

    with caplog.at_level("WARNING"):
        result = runtime_config.load()

    assert "scanning_disabled" not in result


def test_load_discards_scheduler_paused_not_bool(config_path, caplog):
    """load() discards scheduler_paused when it is not a boolean."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"scheduler_paused": 1}', encoding="utf-8")

    with caplog.at_level("WARNING"):
        result = runtime_config.load()

    assert "scheduler_paused" not in result


def test_load_discards_invalid_timestamp(config_path, caplog):
    """load() discards next_run_at when it is not a valid string."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"next_run_at": 12345}', encoding="utf-8")

    with caplog.at_level("WARNING"):
        result = runtime_config.load()

    assert "next_run_at" not in result


# ---------------------------------------------------------------------------
# get_interval_minutes — defense-in-depth bounds (monkeypatched load)
# ---------------------------------------------------------------------------


def test_get_interval_minutes_below_minimum_defence_in_depth(config_path, monkeypatch):
    """get_interval_minutes() returns default when value is below 1 (defense-in-depth)."""
    # Bypass load() validation by monkeypatching it to return raw invalid data
    monkeypatch.setattr(runtime_config, "load", lambda: {"interval_minutes": 0})

    result = runtime_config.get_interval_minutes(60)

    assert result == 60


def test_get_interval_minutes_above_maximum_defence_in_depth(config_path, monkeypatch):
    """get_interval_minutes() returns default when value exceeds 10080 (defense-in-depth)."""
    monkeypatch.setattr(runtime_config, "load", lambda: {"interval_minutes": 99999})

    result = runtime_config.get_interval_minutes(60)

    assert result == 60


def test_get_interval_minutes_type_error_defence_in_depth(config_path, monkeypatch):
    """get_interval_minutes() returns default when value cannot be cast to int."""
    # A list can't be converted to int
    monkeypatch.setattr(runtime_config, "load", lambda: {"interval_minutes": [1, 2, 3]})

    result = runtime_config.get_interval_minutes(60)

    assert result == 60


# ---------------------------------------------------------------------------
# get_enabled_exporters — defense-in-depth (monkeypatched load)
# ---------------------------------------------------------------------------


def test_get_enabled_exporters_not_list_defence_in_depth(config_path, monkeypatch):
    """get_enabled_exporters() returns default when value is not a list (defense-in-depth)."""
    monkeypatch.setattr(runtime_config, "load", lambda: {"enabled_exporters": "csv"})

    result = runtime_config.get_enabled_exporters(["csv"])

    assert result == ["csv"]


# ---------------------------------------------------------------------------
# load() — cache hit path
# ---------------------------------------------------------------------------


def test_load_returns_cached_result_when_file_unchanged(config_path):
    """load() returns cached result on subsequent calls without file changes."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"interval_minutes": 15}', encoding="utf-8")

    # First call populates cache
    first = runtime_config.load()
    # Second call should use cache (same mtime)
    second = runtime_config.load()

    assert first == second
    assert first.get("interval_minutes") == 15
