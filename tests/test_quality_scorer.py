"""Tests for src/services/quality_scorer.py."""

from __future__ import annotations

import datetime

import pytest

from src.models.speed_result import SpeedResult
from src.services.quality_scorer import compute


def _make(
    download: float = 100.0,
    upload: float = 50.0,
    ping: float = 0.0,
    jitter: float | None = None,
    loss: float | None = None,
) -> SpeedResult:
    return SpeedResult(
        download_mbps=download,
        upload_mbps=upload,
        ping_ms=ping,
        jitter_ms=jitter,
        packet_loss_pct=loss,
        server_name="Test Server",
        server_location="Test City",
        timestamp=datetime.datetime(2025, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
    )


class TestComputeIdeal:
    def test_perfect_values_score_100(self) -> None:
        result = _make(download=100, upload=50, ping=0, jitter=0, loss=0)
        assert compute(result) == 100.0

    def test_returns_float(self) -> None:
        assert isinstance(compute(_make()), float)

    def test_score_in_range(self) -> None:
        result = _make(download=10, upload=5, ping=80, jitter=15, loss=2)
        score = compute(result)
        assert 0.0 <= score <= 100.0


class TestComputeDegradation:
    def test_zero_download_lowers_score(self) -> None:
        good = _make(download=100)
        bad = _make(download=0)
        assert compute(bad) < compute(good)

    def test_high_ping_lowers_score(self) -> None:
        good = _make(ping=0)
        bad = _make(ping=150)
        assert compute(bad) < compute(good)

    def test_beyond_max_ping_clamps_to_zero_contribution(self) -> None:
        # ping=200 is worse than 150 but both clamp to 0 contribution
        at_max = _make(ping=150)
        beyond_max = _make(ping=200)
        assert compute(at_max) == compute(beyond_max)

    def test_packet_loss_5pct_max_bad(self) -> None:
        low_loss = _make(loss=0)
        high_loss = _make(loss=5)
        assert compute(high_loss) < compute(low_loss)

    def test_packet_loss_beyond_5pct_clamps(self) -> None:
        at_max = _make(loss=5)
        beyond = _make(loss=10)
        assert compute(at_max) == compute(beyond)


class TestMissingOptionalFields:
    def test_missing_jitter_scores_perfect_for_that_dimension(self) -> None:
        without_jitter = _make(jitter=None)
        with_perfect_jitter = _make(jitter=0)
        assert compute(without_jitter) == compute(with_perfect_jitter)

    def test_missing_loss_scores_perfect_for_that_dimension(self) -> None:
        without_loss = _make(loss=None)
        with_zero_loss = _make(loss=0)
        assert compute(without_loss) == compute(with_zero_loss)


class TestRounding:
    def test_score_has_one_decimal(self) -> None:
        result = _make(download=33, upload=17, ping=45, jitter=10, loss=1)
        score = compute(result)
        # Round-trip: score * 10 should have no fractional part
        assert score == round(score, 1)
