"""Base test provider interface for Hermes."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.models.speed_result import SpeedResult


class BaseTestProvider(ABC):
    """Abstract base class for all speed test providers.

    Each provider is responsible for running a single speed test attempt and
    returning a SpeedResult. Retry logic and fallback orchestration are handled
    by SpeedtestRunner, not by individual providers.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider identifier (e.g. 'ookla', 'ndt7', 'custom')."""

    @abstractmethod
    def run(self) -> SpeedResult:
        """Run a speed test and return the result.

        Raises:
            RuntimeError: If the test fails for any reason. SpeedtestRunner
                          catches this to trigger fallback to the next provider.
        """
