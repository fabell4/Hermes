"""Anomaly detection for Hermes speed results.

Uses a rolling z-score approach: a result is flagged as anomalous when any
metric (download, upload, or ping) deviates more than *threshold* standard
deviations from the mean of the preceding *window* results.

Requires at least 3 results in the window to produce a meaningful baseline.
Statistical outlier detection covers both impossible values (superseding the
standalone result validation) and genuine performance anomalies.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from src.models.speed_result import SpeedResult

_MIN_WINDOW = 3


@dataclass(frozen=True)
class AnomalyFlag:
    """Details about a single anomalous metric."""

    metric: str  # "download_mbps" | "upload_mbps" | "ping_ms"
    value: float
    baseline_mean: float
    baseline_stdev: float
    z_score: float


@dataclass(frozen=True)
class AnomalyResult:
    """Outcome of anomaly detection for one SpeedResult.

    Attributes:
        is_anomaly: True if any metric exceeded the z-score threshold.
        flags: Details for each anomalous metric (empty when is_anomaly is False).
    """

    is_anomaly: bool
    flags: tuple[AnomalyFlag, ...] = field(default_factory=tuple)

    @classmethod
    def normal(cls) -> AnomalyResult:
        """Return a non-anomalous result."""
        return cls(is_anomaly=False, flags=())

    @classmethod
    def insufficient_data(cls) -> AnomalyResult:
        """Return when there are too few baseline results to compute statistics."""
        return cls(is_anomaly=False, flags=())


class AnomalyDetector:
    """Detect speed-test anomalies using a rolling z-score baseline.

    Args:
        window: Number of recent baseline results to use (default 20).
        threshold: Z-score magnitude above which a result is flagged (default 2.5).
    """

    def __init__(self, window: int = 20, threshold: float = 2.5) -> None:
        if window < _MIN_WINDOW:
            raise ValueError(f"window must be at least {_MIN_WINDOW}")
        if threshold <= 0:
            raise ValueError("threshold must be positive")
        self.window = window
        self.threshold = threshold

    def check(self, result: SpeedResult, baseline: list[SpeedResult]) -> AnomalyResult:
        """Check whether *result* is anomalous relative to *baseline*.

        Args:
            result: The new result to evaluate.
            baseline: Historical results used as reference.
                      Should NOT include *result* itself.

        Returns:
            AnomalyResult with is_anomaly=True and per-metric details if anomalous.
        """
        samples = baseline[-self.window :]
        if len(samples) < _MIN_WINDOW:
            return AnomalyResult.insufficient_data()

        flags: list[AnomalyFlag] = []
        for metric, value in (
            ("download_mbps", result.download_mbps),
            ("upload_mbps", result.upload_mbps),
            ("ping_ms", result.ping_ms),
        ):
            values = [getattr(s, metric) for s in samples]
            mean = statistics.mean(values)
            try:
                stdev = statistics.stdev(values)
            except statistics.StatisticsError:
                continue
            if not stdev:
                continue
            z = abs(value - mean) / stdev
            if z > self.threshold:
                flags.append(
                    AnomalyFlag(
                        metric=metric,
                        value=round(value, 3),
                        baseline_mean=round(mean, 3),
                        baseline_stdev=round(stdev, 3),
                        z_score=round(z, 3),
                    )
                )

        return AnomalyResult(is_anomaly=bool(flags), flags=tuple(flags))
