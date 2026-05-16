"""Shared type aliases for Hermes.

Centralises common ``dict``-based annotations so that every module uses the
same names rather than repeating ``dict[str, Any]`` inline.
"""

from __future__ import annotations

from typing import Any

# Generic JSON-serialisable dict (API payloads, runtime config, etc.)
JsonDict = dict[str, Any]

# Alert configuration dict (stored in runtime_config.json under "alert")
AlertConfig = dict[str, Any]
