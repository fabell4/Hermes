"""ResultDispatcher — fans out a SpeedResult to all registered exporters."""

import logging
from src.exporters.base_exporter import BaseExporter
from src.models.speed_result import SpeedResult

logger = logging.getLogger(__name__)


class DispatchError(Exception):
    """Raised when one or more exporters fail during dispatch."""
    def __init__(self, failures: dict[str, Exception]):
        self.failures = failures
        summary = ", ".join(f"{name}: {err}" for name, err in failures.items())
        super().__init__(f"Dispatch completed with {len(failures)} failure(s): {summary}")


class ResultDispatcher:
    """
    Receives a SpeedResult and fans it out to all registered exporters.

    Exporters are called in registration order. If one fails, the others
    still run. All failures are collected and raised together as a
    DispatchError after all exporters have been attempted.
    """

    def __init__(self):
        self._exporters: dict[str, BaseExporter] = {}

    def add_exporter(self, name: str, exporter: BaseExporter) -> None:
        """
        Register an exporter under a given name.
        The name is used for logging and error reporting.

        Example:
            dispatcher.add_exporter("csv", CSVExporter(...))
            dispatcher.add_exporter("prometheus", PrometheusExporter(...))
        """
        if not isinstance(exporter, BaseExporter):  # type: ignore[misc]
            raise TypeError(f"Expected a BaseExporter subclass, got {type(exporter).__name__}")

        self._exporters[name] = exporter
        logger.info("Registered exporter: %s", name)

    def remove_exporter(self, name: str) -> None:
        """Unregister an exporter by name. Silently ignored if not found."""
        if name in self._exporters:
            del self._exporters[name]
            logger.info("Removed exporter: %s", name)

    def dispatch(self, result: SpeedResult) -> None:
        """
        Send a SpeedResult to all registered exporters.

        All exporters are attempted regardless of individual failures.
        Raises DispatchError if any exporters fail, after all have been tried.
        """
        if not self._exporters:
            logger.warning("Dispatch called but no exporters are registered.")
            return

        failures: dict[str, Exception] = {}

        for name, exporter in self._exporters.items():
            try:
                logger.debug("Dispatching to exporter: %s", name)
                exporter.export(result)
                logger.info("Exporter '%s' completed successfully.", name)
            except Exception as e:
                logger.error("Exporter '%s' failed: %s", name, e, exc_info=True)
                failures[name] = e

        if failures:
            raise DispatchError(failures)

    @property
    def exporter_names(self) -> list[str]:
        """Returns the names of all currently registered exporters."""
        return list(self._exporters.keys())