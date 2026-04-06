"""Tests for src/runtime_config.py — JSON persistence layer."""

import json

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
