"""Application-wide constants for Hermes.

This module defines constants for exporter names, alert provider names,
and other magic strings used throughout the application.
"""

# Exporter names — used in EXPORTER_REGISTRY and runtime configuration
EXPORTER_CSV = "csv"
EXPORTER_PROMETHEUS = "prometheus"
EXPORTER_LOKI = "loki"
EXPORTER_SQLITE = "sqlite"

# Alert provider names — used in alert manager registration
PROVIDER_WEBHOOK = "webhook"
PROVIDER_GOTIFY = "gotify"
PROVIDER_NTFY = "ntfy"
PROVIDER_APPRISE = "apprise"

# Default values
DEFAULT_ALERT_TIMEOUT_SECONDS = 10
