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
    INFLUXDB = "influxdb"


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
EXPORTER_INFLUXDB = ExporterType.INFLUXDB

PROVIDER_WEBHOOK = AlertProviderType.WEBHOOK
PROVIDER_GOTIFY = AlertProviderType.GOTIFY
PROVIDER_NTFY = AlertProviderType.NTFY
PROVIDER_APPRISE = AlertProviderType.APPRISE


class ProviderType(StrEnum):
    """Valid test provider type identifiers.

    StrEnum provides type safety while maintaining string compatibility.
    Values can be compared directly with strings: ProviderType.OOKLA == "ookla" is True.
    """

    OOKLA = "ookla"
    NDT7 = "ndt7"


class OutageEventType(StrEnum):
    """Outage event type identifiers for the outage detection subsystem.

    StrEnum provides type safety while maintaining string compatibility.
    Values can be compared directly with strings.
    """

    CONNECTIVITY_LOST = "connectivity_lost"
    CONNECTIVITY_RESTORED = "connectivity_restored"
    SPEEDTEST_SERVER_UNREACHABLE = "speedtest_server_unreachable"
    DNS_FAILURE = "dns_failure"


# Default values
DEFAULT_ALERT_TIMEOUT_SECONDS = 10

# Outage probe defaults
DEFAULT_PROBE_HOSTS: list[str] = ["1.1.1.1:53", "8.8.8.8:53", "9.9.9.9:53"]
DEFAULT_PROBE_TIMEOUT: int = 3
DEFAULT_PROBE_FAILURE_THRESHOLD: int = 2
DEFAULT_PROBE_QUORUM: int = 2
