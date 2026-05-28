"""SLA (Service-Level Agreement) monitoring for Hermes.

Checks a SpeedResult against configured minimum/maximum thresholds.
All four thresholds are optional — setting a threshold to None disables
that individual check.

Typical usage::

    monitor = SLAMonitor(
        min_download_mbps=50.0,
        max_ping_ms=80.0,
    )
    sla = monitor.check(result)
    if not sla.overall_ok:
        logger.warning("SLA breached!")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.models.speed_result import SpeedResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SLAResult:
    """Outcome of a single SLA evaluation against a SpeedResult.

    Each per-dimension flag is:
    - True  — threshold configured and met
    - False — threshold configured and breached
    - None  — threshold not configured (check skipped)
    """

    download_ok: bool | None
    upload_ok: bool | None
    ping_ok: bool | None
    packet_loss_ok: bool | None
    overall_ok: bool  # True only when all *configured* checks pass

    @classmethod
    def disabled(cls) -> SLAResult:
        """Return an all-pass result used when no thresholds are configured."""
        return cls(
            download_ok=None,
            upload_ok=None,
            ping_ok=None,
            packet_loss_ok=None,
            overall_ok=True,
        )


class SLAMonitor:
    """Evaluate a SpeedResult against configured thresholds."""

    def __init__(
        self,
        min_download_mbps: float | None = None,
        min_upload_mbps: float | None = None,
        max_ping_ms: float | None = None,
        max_packet_loss_pct: float | None = None,
    ) -> None:
        """
        Args:
            min_download_mbps: Minimum acceptable download speed (Mbps).
            min_upload_mbps:   Minimum acceptable upload speed (Mbps).
            max_ping_ms:       Maximum acceptable round-trip latency (ms).
            max_packet_loss_pct: Maximum acceptable packet loss (%).
        """
        self.min_download_mbps = min_download_mbps
        self.min_upload_mbps = min_upload_mbps
        self.max_ping_ms = max_ping_ms
        self.max_packet_loss_pct = max_packet_loss_pct

    @property
    def enabled(self) -> bool:
        """True if at least one threshold is configured."""
        return any(
            t is not None
            for t in (
                self.min_download_mbps,
                self.min_upload_mbps,
                self.max_ping_ms,
                self.max_packet_loss_pct,
            )
        )

    @staticmethod
    def _check_min(value: float, threshold: float | None) -> bool | None:
        """Return True if value meets minimum threshold, None if unconfigured."""
        return (value >= threshold) if threshold is not None else None

    @staticmethod
    def _check_max(value: float | None, threshold: float | None) -> bool | None:
        """Return True if value meets maximum threshold, None if unconfigured or missing."""
        if threshold is None or value is None:
            return None
        return value <= threshold

    def check(self, result: SpeedResult) -> SLAResult:
        """Evaluate *result* against all configured thresholds.

        Args:
            result: The SpeedResult to check.

        Returns:
            An SLAResult with per-dimension pass/fail flags and an overall flag.
        """
        if not self.enabled:
            return SLAResult.disabled()

        download_ok = self._check_min(result.download_mbps, self.min_download_mbps)
        upload_ok = self._check_min(result.upload_mbps, self.min_upload_mbps)
        ping_ok = self._check_max(result.ping_ms, self.max_ping_ms)
        packet_loss_ok = self._check_max(
            result.packet_loss_pct, self.max_packet_loss_pct
        )

        configured = [
            c
            for c in (download_ok, upload_ok, ping_ok, packet_loss_ok)
            if c is not None
        ]
        overall_ok = all(configured) if configured else True

        if not overall_ok:
            logger.warning(
                "SLA breach — download_ok=%s upload_ok=%s ping_ok=%s loss_ok=%s",
                download_ok,
                upload_ok,
                ping_ok,
                packet_loss_ok,
            )

        return SLAResult(
            download_ok=download_ok,
            upload_ok=upload_ok,
            ping_ok=ping_ok,
            packet_loss_ok=packet_loss_ok,
            overall_ok=overall_ok,
        )
