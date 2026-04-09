"""Tests for src/runtime_config.py — JSON persistence layer."""

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
    assert runtime_config.load() == {}


def test_load_returns_data_when_file_exists(config_path):
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"interval_minutes": 30}', encoding="utf-8")
    assert runtime_config.load() == {"interval_minutes": 30}


def test_load_returns_empty_on_invalid_json(config_path):
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("not valid json", encoding="utf-8")
    assert runtime_config.load() == {}


# ---------------------------------------------------------------------------
# save()
# ---------------------------------------------------------------------------


def test_save_creates_file_and_writes_data(config_path):
    runtime_config.save({"interval_minutes": 15})
    assert config_path.exists()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["interval_minutes"] == 15


def test_save_merges_with_existing_data(config_path):
    runtime_config.save({"interval_minutes": 15})
    runtime_config.save({"enabled_exporters": ["csv"]})
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["interval_minutes"] == 15
    assert data["enabled_exporters"] == ["csv"]


def test_save_raises_on_os_error(config_path, monkeypatch):
    import builtins

    real_open = builtins.open

    def _bad_open(path, mode="r", **kwargs):
        if "w" in mode and str(path) == str(config_path):
            raise OSError("disk full")
        return real_open(path, mode, **kwargs)

    monkeypatch.setattr(builtins, "open", _bad_open)
    with pytest.raises(OSError, match="disk full"):
        runtime_config.save({"interval_minutes": 5})


# ---------------------------------------------------------------------------
# get_interval_minutes()
# ---------------------------------------------------------------------------


def test_get_interval_minutes_returns_default_when_missing(config_path):
    assert runtime_config.get_interval_minutes(60) == 60


def test_get_interval_minutes_returns_persisted_value(config_path):
    runtime_config.save({"interval_minutes": 45})
    assert runtime_config.get_interval_minutes(60) == 45


def test_get_interval_minutes_returns_default_on_invalid_value(config_path):
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"interval_minutes": "not_a_number"}', encoding="utf-8")
    assert runtime_config.get_interval_minutes(60) == 60


# ---------------------------------------------------------------------------
# set_interval_minutes()
# ---------------------------------------------------------------------------


def test_set_interval_minutes_persists_value(config_path):
    runtime_config.set_interval_minutes(20)
    assert runtime_config.get_interval_minutes(60) == 20


# ---------------------------------------------------------------------------
# get_enabled_exporters()
# ---------------------------------------------------------------------------


def test_get_enabled_exporters_returns_default_when_missing(config_path):
    assert runtime_config.get_enabled_exporters(["csv"]) == ["csv"]


def test_get_enabled_exporters_returns_persisted_value(config_path):
    runtime_config.save({"enabled_exporters": ["csv", "loki"]})
    assert runtime_config.get_enabled_exporters(["csv"]) == ["csv", "loki"]


def test_get_enabled_exporters_returns_default_on_invalid_type(config_path):
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"enabled_exporters": "not_a_list"}', encoding="utf-8")
    assert runtime_config.get_enabled_exporters(["csv"]) == ["csv"]


# ---------------------------------------------------------------------------
# set_enabled_exporters()
# ---------------------------------------------------------------------------


def test_set_enabled_exporters_persists_value(config_path):
    runtime_config.set_enabled_exporters(["prometheus"])
    assert runtime_config.get_enabled_exporters([]) == ["prometheus"]


# ---------------------------------------------------------------------------
# trigger_run() / consume_run_trigger()
# ---------------------------------------------------------------------------


def test_trigger_run_creates_trigger_file(tmp_path, monkeypatch):
    trigger_path = tmp_path / "data" / ".run_trigger"
    monkeypatch.setattr(runtime_config, "RUN_TRIGGER_PATH", trigger_path)
    monkeypatch.setattr(
        runtime_config, "RUNTIME_CONFIG_PATH", tmp_path / "data" / "runtime_config.json"
    )

    runtime_config.trigger_run()

    assert trigger_path.exists()


def test_consume_run_trigger_returns_true_and_deletes_file(tmp_path, monkeypatch):
    trigger_path = tmp_path / "data" / ".run_trigger"
    trigger_path.parent.mkdir(parents=True, exist_ok=True)
    trigger_path.touch()
    monkeypatch.setattr(runtime_config, "RUN_TRIGGER_PATH", trigger_path)

    result = runtime_config.consume_run_trigger()

    assert result is True
    assert not trigger_path.exists()


def test_consume_run_trigger_returns_false_when_no_file(tmp_path, monkeypatch):
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
    path = tmp_path / "data" / ".running"
    monkeypatch.setattr(runtime_config, "RUNNING_PATH", path)
    monkeypatch.setattr(
        runtime_config, "RUNTIME_CONFIG_PATH", tmp_path / "data" / "runtime_config.json"
    )
    return path


def test_mark_running_creates_sentinel_file(running_path):
    runtime_config.mark_running()
    assert running_path.exists()


def test_mark_done_removes_sentinel_file(running_path):
    running_path.parent.mkdir(parents=True, exist_ok=True)
    running_path.touch()
    runtime_config.mark_done()
    assert not running_path.exists()


def test_mark_done_is_noop_when_file_absent(running_path):
    # Should not raise even if the file doesn't exist.
    runtime_config.mark_done()


def test_is_running_returns_true_when_file_exists(running_path):
    running_path.parent.mkdir(parents=True, exist_ok=True)
    running_path.touch()
    assert runtime_config.is_running() is True


def test_is_running_returns_false_when_file_absent(running_path):
    assert runtime_config.is_running() is False
