"""Application-wide constants for Hermes.

This module defines constants for exporter names, alert provider names,
and other magic strings used throughout the application.
"""

from enum import StrEnum


class ExporterType(StrEnum):
    """Valid exporter type identifiers.

    StrEnum provides type safety while maintaining string compatibility.
    Values can be compared directly with strings: ExporterType.CSV == "csv" is True.
    """

    CSV = "csv"
    PROMETHEUS = "prometheus"
    LOKI = "loki"
    SQLITE = "sqlite"


class AlertProviderType(StrEnum):
    """Valid alert provider type identifiers.

    StrEnum provides type safety while maintaining string compatibility.
    Values can be compared directly with strings.
    """

    WEBHOOK = "webhook"
    GOTIFY = "gotify"
    NTFY = "ntfy"
    APPRISE = "apprise"


# Backward compatibility aliases - can be removed in future major version
EXPORTER_CSV = ExporterType.CSV
EXPORTER_PROMETHEUS = ExporterType.PROMETHEUS
EXPORTER_LOKI = ExporterType.LOKI
EXPORTER_SQLITE = ExporterType.SQLITE

PROVIDER_WEBHOOK = AlertProviderType.WEBHOOK
PROVIDER_GOTIFY = AlertProviderType.GOTIFY
PROVIDER_NTFY = AlertProviderType.NTFY
PROVIDER_APPRISE = AlertProviderType.APPRISE

# Default values
DEFAULT_ALERT_TIMEOUT_SECONDS = 10
