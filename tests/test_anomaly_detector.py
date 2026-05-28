"""Tests for src/services/anomaly_detector.py."""

from __future__ import annotations

import datetime

import pytest

from src.models.speed_result import SpeedResult
from src.services.anomaly_detector import AnomalyDetector, AnomalyFlag, AnomalyResult

_TS = datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)


def _make(
    download: float = 100.0,
    upload: float = 50.0,
    ping: float = 20.0,
    ts: datetime.datetime | None = None,
) -> SpeedResult:
    return SpeedResult(
        download_mbps=download,
        upload_mbps=upload,
        ping_ms=ping,
        server_name="Test",
        server_location="Test City",
        timestamp=ts or _TS,
    )


def _baseline(
    n: int = 20, download: float = 100.0, upload: float = 50.0, ping: float = 20.0
) -> list[SpeedResult]:
    """Return *n* identical baseline results."""
    return [_make(download=download, upload=upload, ping=ping) for _ in range(n)]


class TestAnomalyDetectorInit:
    def test_default_params(self) -> None:
        d = AnomalyDetector()
        assert d.window == 20
        assert d.threshold == 2.5

    def test_custom_params(self) -> None:
        d = AnomalyDetector(window=10, threshold=3.0)
        assert d.window == 10
        assert d.threshold == 3.0

    def test_window_too_small_raises(self) -> None:
        with pytest.raises(ValueError, match="window"):
            AnomalyDetector(window=2)

    def test_threshold_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="threshold"):
            AnomalyDetector(threshold=0.0)

    def test_threshold_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="threshold"):
            AnomalyDetector(threshold=-1.0)


class TestAnomalyResultClassMethods:
    def test_normal_returns_no_anomaly(self) -> None:
        r = AnomalyResult.normal()
        assert not r.is_anomaly
        assert r.flags == ()

    def test_insufficient_data_returns_no_anomaly(self) -> None:
        r = AnomalyResult.insufficient_data()
        assert not r.is_anomaly
        assert r.flags == ()


class TestInsufficientData:
    def test_empty_baseline_returns_insufficient(self) -> None:
        d = AnomalyDetector()
        r = d.check(_make(), baseline=[])
        assert not r.is_anomaly

    def test_two_baseline_results_returns_insufficient(self) -> None:
        d = AnomalyDetector()
        r = d.check(_make(), baseline=[_make(), _make()])
        assert not r.is_anomaly

    def test_three_baseline_results_is_enough(self) -> None:
        # 3 identical results have stdev=0, so metric is skipped → no anomaly
        d = AnomalyDetector()
        result = d.check(_make(download=200.0), baseline=[_make()] * 3)
        assert not result.is_anomaly

    def test_exactly_min_window_used(self) -> None:
        d = AnomalyDetector(window=5)
        result = d.check(_make(), baseline=[_make()] * 5)
        assert not result.is_anomaly


class TestNormalResult:
    def test_result_within_threshold_not_flagged(self) -> None:
        base = [_make(download=100.0 + i * 0.5) for i in range(20)]
        result = _make(download=101.0)
        d = AnomalyDetector()
        out = d.check(result, base)
        assert not out.is_anomaly
        assert out.flags == ()

    def test_identical_baseline_skips_zero_stdev(self) -> None:
        base = _baseline(20, download=100.0)
        result = _make(download=999.0)  # extreme deviation but stdev=0 → skip
        d = AnomalyDetector()
        out = d.check(result, base)
        assert not out.is_anomaly


class TestAnomalousResult:
    def _varied_baseline(self, n: int = 20) -> list[SpeedResult]:
        """Return a baseline with small natural variation (stdev ~1)."""
        return [_make(download=100.0 + (i % 5) * 0.3) for i in range(n)]

    def test_high_download_flagged(self) -> None:
        base = self._varied_baseline()
        result = _make(download=200.0)  # far from ~100 mean
        d = AnomalyDetector(threshold=2.5)
        out = d.check(result, base)
        assert out.is_anomaly
        metrics = [f.metric for f in out.flags]
        assert "download_mbps" in metrics

    def test_low_download_flagged(self) -> None:
        base = self._varied_baseline()
        result = _make(download=0.1)
        d = AnomalyDetector(threshold=2.5)
        out = d.check(result, base)
        assert out.is_anomaly

    def test_high_ping_flagged(self) -> None:
        base = [_make(ping=20.0 + (i % 3) * 0.5) for i in range(20)]
        result = _make(ping=200.0)
        d = AnomalyDetector(threshold=2.5)
        out = d.check(result, base)
        assert out.is_anomaly
        metrics = [f.metric for f in out.flags]
        assert "ping_ms" in metrics

    def test_flag_contains_correct_fields(self) -> None:
        base = [_make(download=100.0 + (i % 5) * 0.4) for i in range(20)]
        result = _make(download=200.0)
        d = AnomalyDetector(threshold=2.5)
        out = d.check(result, base)
        assert out.is_anomaly
        flag = next(f for f in out.flags if f.metric == "download_mbps")
        assert isinstance(flag, AnomalyFlag)
        assert flag.value == pytest.approx(200.0, abs=0.01)
        assert flag.z_score > 2.5
        assert flag.baseline_mean == pytest.approx(100.6, abs=0.5)
        assert flag.baseline_stdev > 0

    def test_multiple_metrics_flagged(self) -> None:
        base = [_make(download=100.0 + i * 0.2, ping=20.0 + i * 0.1) for i in range(20)]
        result = _make(download=0.1, ping=300.0)
        d = AnomalyDetector(threshold=2.5)
        out = d.check(result, base)
        assert out.is_anomaly
        metrics = {f.metric for f in out.flags}
        assert "download_mbps" in metrics
        assert "ping_ms" in metrics

    def test_window_limits_baseline_used(self) -> None:
        # Build a long baseline where only the last 5 are relevant
        old = [_make(download=10.0) for _ in range(50)]
        recent = [_make(download=100.0 + i * 0.2) for i in range(5)]
        base = old + recent
        # Result consistent with recent window — should be normal
        result = _make(download=100.5)
        d = AnomalyDetector(window=5, threshold=2.5)
        out = d.check(result, base)
        assert not out.is_anomaly

    def test_strict_threshold_flags_less(self) -> None:
        base = [_make(download=100.0 + (i % 5) * 2.0) for i in range(20)]
        result = _make(download=110.0)
        loose = AnomalyDetector(threshold=0.5)
        strict = AnomalyDetector(threshold=5.0)
        assert loose.check(result, base).is_anomaly
        assert not strict.check(result, base).is_anomaly
