"""Tests for src/result_dispatcher.py."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.exporters.base_exporter import BaseExporter
from src.models.speed_result import SpeedResult
from src.result_dispatcher import DispatchError, ResultDispatcher


def _sample_result() -> SpeedResult:
    return SpeedResult(
        timestamp=datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc),
        download_mbps=100.0,
        upload_mbps=50.0,
        ping_ms=10.0,
        server_name="Test ISP",
        server_location="Test City, DE",
        server_id=1234,
    )


class GoodExporter(BaseExporter):
    def __init__(self):
        self.calls: list[SpeedResult] = []

    def export(self, result: SpeedResult) -> None:
        self.calls.append(result)


class BrokenExporter(BaseExporter):
    def export(self, result: SpeedResult) -> None:
        raise RuntimeError("export failed")


# ---------------------------------------------------------------------------
# DispatchError
# ---------------------------------------------------------------------------


def test_dispatch_error_message_includes_failure_details():
    err = ValueError("something bad")
    exc = DispatchError({"csv": err})
    assert "1 failure" in str(exc)
    assert "csv" in str(exc)
    assert exc.failures == {"csv": err}


# ---------------------------------------------------------------------------
# add_exporter()
# ---------------------------------------------------------------------------


def test_add_exporter_registers_by_name():
    dispatcher = ResultDispatcher()
    dispatcher.add_exporter("csv", GoodExporter())
    assert "csv" in dispatcher.exporter_names


def test_add_exporter_raises_type_error_for_non_exporter():
    dispatcher = ResultDispatcher()
    with pytest.raises(TypeError, match="BaseExporter"):
        dispatcher.add_exporter("bad", object())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# remove_exporter()
# ---------------------------------------------------------------------------


def test_remove_exporter_deregisters_by_name():
    dispatcher = ResultDispatcher()
    dispatcher.add_exporter("csv", GoodExporter())
    dispatcher.remove_exporter("csv")
    assert "csv" not in dispatcher.exporter_names


def test_remove_exporter_is_silent_when_not_found():
    dispatcher = ResultDispatcher()
    dispatcher.remove_exporter("nonexistent")  # must not raise


# ---------------------------------------------------------------------------
# clear()
# ---------------------------------------------------------------------------


def test_clear_removes_all_exporters():
    dispatcher = ResultDispatcher()
    dispatcher.add_exporter("csv", GoodExporter())
    dispatcher.add_exporter("loki", GoodExporter())
    dispatcher.clear()
    assert dispatcher.exporter_names == []


# ---------------------------------------------------------------------------
# dispatch()
# ---------------------------------------------------------------------------


def test_dispatch_calls_all_exporters(caplog):
    dispatcher = ResultDispatcher()
    e1 = GoodExporter()
    e2 = GoodExporter()
    dispatcher.add_exporter("a", e1)
    dispatcher.add_exporter("b", e2)

    result = _sample_result()
    dispatcher.dispatch(result)

    assert e1.calls == [result]
    assert e2.calls == [result]


def test_dispatch_with_no_exporters_logs_warning(caplog):
    dispatcher = ResultDispatcher()
    import logging

    with caplog.at_level(logging.WARNING):
        dispatcher.dispatch(_sample_result())

    assert "no exporters" in caplog.text.lower()


def test_dispatch_collects_all_failures_and_raises():
    dispatcher = ResultDispatcher()
    dispatcher.add_exporter("bad1", BrokenExporter())
    dispatcher.add_exporter("bad2", BrokenExporter())

    with pytest.raises(DispatchError) as exc_info:
        dispatcher.dispatch(_sample_result())

    assert "bad1" in exc_info.value.failures
    assert "bad2" in exc_info.value.failures


def test_dispatch_continues_after_partial_failure():
    dispatcher = ResultDispatcher()
    good = GoodExporter()
    dispatcher.add_exporter("bad", BrokenExporter())
    dispatcher.add_exporter("good", good)

    with pytest.raises(DispatchError):
        dispatcher.dispatch(_sample_result())

    # good exporter must still have received the result
    assert len(good.calls) == 1
