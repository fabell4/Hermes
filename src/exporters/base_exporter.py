"""BaseExporter — abstract interface that all exporters must implement."""

from abc import ABC, abstractmethod
from src.models.outage_event import OutageEvent
from src.models.speed_result import SpeedResult


class BaseExporter(ABC):
    """
    Abstract base class for all result exporters.
    Subclasses must implement export() to ship SpeedResult
    data to a specific destination (CSV, Prometheus, Loki, etc).
    """

    @abstractmethod
    def export(self, result: SpeedResult) -> None:
        """Export a SpeedResult to the target destination."""
        ...

    def export_outage_event(self, event: OutageEvent) -> None:  # noqa: ARG002
        """Export an OutageEvent. Default is a no-op; override to handle outage data."""
