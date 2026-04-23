"""Property-based tests for SpeedResult using Hypothesis.

Principle 3 — Unexpected inputs (category 3 from the defensive testing framework):
  Hypothesis generates hundreds of edge cases automatically — values a human
  wouldn't think to write manually — and verifies that core invariants hold
  across all of them.

Coverage targets:
  - SpeedResult.to_dict() invariants (keys, types, round-trip fidelity)
  - SQLite write-and-read round-trip for arbitrary valid SpeedResult values
"""
# pylint: disable=missing-function-docstring

import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.exporters.sqlite_exporter import SQLiteExporter
from src.models.speed_result import SpeedResult

# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

_mbps = st.floats(
    min_value=0.0, max_value=10_000.0, allow_nan=False, allow_infinity=False
)
_ping = st.floats(
    min_value=0.0, max_value=5_000.0, allow_nan=False, allow_infinity=False
)
_opt_float = st.one_of(
    st.none(),
    st.floats(min_value=0.0, max_value=1_000.0, allow_nan=False, allow_infinity=False),
)
_text = st.text(min_size=0, max_size=200)
_opt_int = st.one_of(st.none(), st.integers(min_value=0, max_value=2**31 - 1))

_EXPECTED_KEYS = frozenset(
    {
        "timestamp",
        "download_mbps",
        "upload_mbps",
        "ping_ms",
        "jitter_ms",
        "isp_name",
        "server_name",
        "server_location",
        "server_id",
    }
)


@st.composite
def speed_results(draw: st.DrawFn) -> SpeedResult:
    return SpeedResult(
        timestamp=datetime.now(timezone.utc),
        download_mbps=draw(_mbps),
        upload_mbps=draw(_mbps),
        ping_ms=draw(_ping),
        jitter_ms=draw(_opt_float),
        isp_name=draw(st.one_of(st.none(), _text)),
        server_name=draw(_text),
        server_location=draw(_text),
        server_id=draw(_opt_int),
    )


# ---------------------------------------------------------------------------
# SpeedResult.to_dict() invariants
# ---------------------------------------------------------------------------


@given(speed_results())
def test_to_dict_always_contains_all_expected_keys(result: SpeedResult) -> None:
    """to_dict() must always expose every key the frontend and exporters rely on."""
    assert set(result.to_dict()) == _EXPECTED_KEYS


@given(speed_results())
def test_to_dict_timestamp_is_always_valid_iso_string(result: SpeedResult) -> None:
    """to_dict()['timestamp'] must always be parseable as ISO 8601."""
    ts = result.to_dict()["timestamp"]
    assert isinstance(ts, str)
    datetime.fromisoformat(ts)  # raises ValueError if malformed


@given(_mbps, _mbps, _ping)
def test_to_dict_numeric_fields_survive_roundtrip(
    download: float, upload: float, ping: float
) -> None:
    """Numeric fields must not be mutated by to_dict()."""
    r = SpeedResult(download_mbps=download, upload_mbps=upload, ping_ms=ping)
    d = r.to_dict()
    assert d["download_mbps"] == download
    assert d["upload_mbps"] == upload
    assert d["ping_ms"] == ping


@given(speed_results())
def test_to_dict_optional_none_fields_are_present_not_absent(
    result: SpeedResult,
) -> None:
    """Optional fields must appear in to_dict() as None when unset, never be missing."""
    d = result.to_dict()
    for key in ("jitter_ms", "isp_name", "server_id"):
        assert key in d


# ---------------------------------------------------------------------------
# SQLite write-and-read round-trip property
# ---------------------------------------------------------------------------


@given(speed_results())
@settings(max_examples=50)
def test_sqlite_roundtrip_preserves_numeric_fields(result: SpeedResult) -> None:
    """Any valid SpeedResult written to SQLite must read back with identical values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "prop.db"
        SQLiteExporter(path=db).export(result)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT download_mbps, upload_mbps, ping_ms, jitter_ms FROM results"
        ).fetchone()
        conn.close()

    assert row[0] == pytest.approx(result.download_mbps, rel=1e-9)
    assert row[1] == pytest.approx(result.upload_mbps, rel=1e-9)
    assert row[2] == pytest.approx(result.ping_ms, rel=1e-9)
    if result.jitter_ms is None:
        assert row[3] is None
    else:
        assert row[3] == pytest.approx(result.jitter_ms, rel=1e-9)


@given(speed_results())
@settings(max_examples=50)
def test_sqlite_roundtrip_preserves_text_and_optional_fields(
    result: SpeedResult,
) -> None:
    """Text fields and optional integer server_id survive the SQLite round-trip intact."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "prop.db"
        SQLiteExporter(path=db).export(result)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT server_name, server_location, isp_name, server_id FROM results"
        ).fetchone()
        conn.close()

    assert row[0] == result.server_name
    assert row[1] == result.server_location
    assert row[2] == result.isp_name
    assert row[3] == result.server_id
