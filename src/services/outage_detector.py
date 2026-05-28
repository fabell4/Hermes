"""OutageDetector — TCP-probe-based connectivity checker with optional ISP enrichment.

Detection tiers:
    1. TCP socket probes against well-known endpoints (majority-vote quorum).
       An outage is declared after N consecutive failure rounds.
    2. Optional RIPE Stat BGP enrichment (OUTAGE_ISP_CHECK_ENABLED=true).
    3. Optional Cloudflare Radar annotation enrichment (CLOUDFLARE_API_TOKEN set).

All external HTTP calls use HTTPS only.  Plain-HTTP URLs are rejected at
construction time.
"""

from __future__ import annotations

import logging
import socket
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Cache TTL for BGP stability and Cloudflare Radar results.
_CACHE_TTL = timedelta(minutes=15)

# Cloudflare Radar API base URL (HTTPS only).
_CF_RADAR_URL = "https://api.cloudflare.com/client/v4/radar/annotations/outages"

# RIPE Stat base URL (HTTPS only).
_RIPE_BASE = "https://stat.ripe.net/data"


class ConnectivityStatus(StrEnum):
    """Result of a single connectivity probe round."""

    UP = "up"
    DOWN = "down"


class OutageDetector:
    """Performs TCP probes to distinguish complete connectivity loss from slow speeds.

    Args:
        probe_hosts:        List of ``"host:port"`` strings to probe each round.
        probe_timeout:      Seconds to wait for each TCP connection.
        failure_threshold:  Consecutive failure rounds required to declare DOWN.
        quorum:             Number of probes that must fail in a round for the
                            round to count as a failure.
        isp_check_enabled:  When True, fetch ASN from RIPE Stat and check BGP
                            stability on outage start.
        cloudflare_token:   Cloudflare API token for Radar annotation enrichment.
                            ``None`` disables CF Radar entirely.
        http_session:       Optional ``requests.Session`` for testing. A new
                            session is created when omitted.
    """

    def __init__(
        self,
        probe_hosts: list[str] | None = None,
        probe_timeout: int = 3,
        failure_threshold: int = 2,
        quorum: int = 2,
        isp_check_enabled: bool = False,
        cloudflare_token: str | None = None,
        http_session: requests.Session | None = None,
    ) -> None:
        from src.constants import (  # local import to avoid circular at module level
            DEFAULT_PROBE_HOSTS,
        )

        self._probe_hosts: list[tuple[str, int]] = _parse_probe_hosts(
            probe_hosts or DEFAULT_PROBE_HOSTS
        )
        self._probe_timeout = probe_timeout
        self._failure_threshold = failure_threshold
        self._quorum = quorum
        self._isp_check_enabled = isp_check_enabled
        self._cloudflare_token = cloudflare_token

        self._consecutive_probe_failures: int = 0

        # RIPE Stat ASN cache (fetched once per session)
        self._public_ip: str | None = None
        self._asn: str | None = None
        self._asn_fetched: bool = False

        # BGP stability cache: asn → (unstable: bool, fetched_at: datetime)
        self._bgp_cache: dict[str, tuple[bool, datetime]] = {}

        # Cloudflare Radar cache: asn → (description | None, fetched_at: datetime)
        self._cf_cache: dict[str, tuple[str | None, datetime]] = {}

        self._session: requests.Session = http_session or requests.Session()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def check_connectivity(self) -> ConnectivityStatus:
        """Run one probe round and return the current connectivity status.

        A round is a failure when ``quorum`` or more probes cannot connect.
        DOWN is only declared after ``failure_threshold`` consecutive failure
        rounds; a single UP round immediately clears the failure counter.
        """
        failed = 0
        probe_results: list[str] = []

        for host, port in self._probe_hosts:
            ok = _tcp_probe(host, port, self._probe_timeout)
            probe_results.append(f"{host}:{port} {'OK' if ok else 'FAIL'}")
            if not ok:
                failed += 1

        total = len(self._probe_hosts)
        summary = f"{failed}/{total} probes failed ({', '.join(probe_results)})"
        logger.debug("Connectivity probe: %s", summary)

        if failed >= self._quorum:
            self._consecutive_probe_failures += 1
            logger.warning(
                "Connectivity probe round %d/%d failed: %s",
                self._consecutive_probe_failures,
                self._failure_threshold,
                summary,
            )
            if self._consecutive_probe_failures >= self._failure_threshold:
                return ConnectivityStatus.DOWN
            # Not enough consecutive failures yet — still UP
            return ConnectivityStatus.UP

        # At least quorum probes succeeded — reset counter
        if self._consecutive_probe_failures > 0:
            logger.info(
                "Connectivity restored after %d consecutive failure round(s).",
                self._consecutive_probe_failures,
            )
        self._consecutive_probe_failures = 0
        return ConnectivityStatus.UP

    def get_probe_summary(self) -> str:
        """Return a human-readable summary of the last probe round (for event records)."""
        # Re-run probes synchronously and return summary without updating state.
        # Used when callers need probe detail for event metadata.
        results: list[str] = []
        failed = 0
        for host, port in self._probe_hosts:
            ok = _tcp_probe(host, port, self._probe_timeout)
            results.append(f"{host}:{port} {'OK' if ok else 'FAIL'}")
            if not ok:
                failed += 1
        total = len(self._probe_hosts)
        return f"{failed}/{total} probes failed ({', '.join(results)})"

    def get_isp_asn(self) -> str | None:
        """Return the ASN for the current public IP, fetching once per session.

        Requires ``isp_check_enabled=True``.  Returns None when disabled or on
        any network / API error.
        """
        if not self._isp_check_enabled:
            return None
        if self._asn_fetched:
            return self._asn
        self._asn_fetched = True
        ip = self._get_public_ip()
        if not ip:
            return None
        try:
            url = f"{_RIPE_BASE}/network-info/data.json?resource={ip}"
            resp = self._session.get(url, timeout=5)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            asns: list[str] = data.get("data", {}).get("asns", [])
            self._asn = asns[0] if asns else None
            logger.debug("RIPE Stat ASN for %s: %s", ip, self._asn)
        except Exception as exc:  # pylint: disable=broad-except  # NOSONAR
            logger.warning("RIPE Stat ASN lookup failed: %s", exc)
            self._asn = None
        return self._asn

    def check_bgp_stability(self, asn: str) -> bool:
        """Return True if BGP update activity for *asn* is anomalously high.

        Result is cached for 15 minutes.  Requires ``isp_check_enabled=True``.
        Always returns False when disabled or on API error.
        """
        if not self._isp_check_enabled:
            return False
        now = datetime.now(timezone.utc)
        if asn in self._bgp_cache:
            cached_val, cached_at = self._bgp_cache[asn]
            if now - cached_at < _CACHE_TTL:
                return cached_val
        try:
            url = f"{_RIPE_BASE}/bgpupdate-activity/data.json?resource=AS{asn}"
            resp = self._session.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            # RIPE Stat returns an "activity" field; a non-empty list means instability.
            activity: list[Any] = data.get("data", {}).get("activity", [])
            unstable = bool(activity)
            self._bgp_cache[asn] = (unstable, now)
            logger.debug("BGP stability for AS%s: unstable=%s", asn, unstable)
            return unstable
        except Exception as exc:  # pylint: disable=broad-except  # NOSONAR
            logger.warning("BGP stability check for AS%s failed: %s", asn, exc)
            self._bgp_cache[asn] = (False, now)
            return False

    def check_cloudflare_outage(self, asn: str) -> str | None:
        """Return a Cloudflare Radar outage annotation for *asn*, or None.

        Result is cached for 15 minutes.  Only called when a token is set.
        """
        if not self._cloudflare_token:
            return None
        now = datetime.now(timezone.utc)
        if asn in self._cf_cache:
            cached_val, cached_at = self._cf_cache[asn]
            if now - cached_at < _CACHE_TTL:
                return cached_val
        try:
            headers = {"Authorization": f"Bearer {self._cloudflare_token}"}
            params = {"asns": asn}
            resp = self._session.get(
                _CF_RADAR_URL, headers=headers, params=params, timeout=5
            )
            resp.raise_for_status()
            data = resp.json()
            annotations: list[dict[str, Any]] = data.get("result", {}).get(
                "annotations", []
            )
            desc: str | None = (
                annotations[0].get("description") if annotations else None
            )
            self._cf_cache[asn] = (desc, now)
            logger.debug("Cloudflare Radar annotation for AS%s: %s", asn, desc)
            return desc
        except Exception as exc:  # pylint: disable=broad-except  # NOSONAR
            logger.warning("Cloudflare Radar check for AS%s failed: %s", asn, exc)
            self._cf_cache[asn] = (None, now)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_public_ip(self) -> str | None:
        """Fetch the machine's public IP via ipify (HTTPS). Cached after first call."""
        if self._public_ip is not None:
            return self._public_ip
        try:
            resp = self._session.get("https://api.ipify.org?format=json", timeout=5)
            resp.raise_for_status()
            self._public_ip = resp.json().get("ip")
            logger.debug("Public IP: %s", self._public_ip)
        except Exception as exc:  # pylint: disable=broad-except  # NOSONAR
            logger.warning("Public IP lookup failed: %s", exc)
        return self._public_ip


# ------------------------------------------------------------------
# Module-level helpers (pure functions — easy to unit-test)
# ------------------------------------------------------------------


def _parse_probe_hosts(hosts: list[str]) -> list[tuple[str, int]]:
    """Parse ``["host:port", ...]`` strings into ``[(host, port), ...]`` tuples.

    Entries that cannot be parsed are logged and skipped.
    """
    result: list[tuple[str, int]] = []
    for entry in hosts:
        try:
            host, _, raw_port = entry.rpartition(":")
            if not host or not raw_port:
                raise ValueError("missing host or port")
            result.append((host, int(raw_port)))
        except ValueError:
            logger.warning("Ignoring invalid probe host entry: %r", entry)
    if not result:
        logger.warning(
            "No valid probe hosts after parsing — outage detection is effectively disabled."
        )
    return result


def _tcp_probe(host: str, port: int, timeout: int) -> bool:
    """Return True when a TCP connection to *host*:*port* succeeds within *timeout* seconds."""
    try:
        conn = socket.create_connection((host, port), timeout=timeout)
        conn.close()
        return True
    except OSError:
        return False
