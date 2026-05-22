"""OutageEvent dataclass — the data contract for outage detection events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.constants import OutageEventType


@dataclass
class OutageEvent:
    """Represents a single outage detection event.

    Fields:
        event_type:               What kind of event occurred.
        timestamp:                When the event was recorded (UTC).
        probe_results:            Human-readable summary of probe outcomes, e.g.
                                  "2/3 probes failed (1.1.1.1:53 OK, 8.8.8.8:53 FAIL, 9.9.9.9:53 FAIL)".
        duration_seconds:         Seconds the outage lasted (only set for CONNECTIVITY_RESTORED).
        isp_name:                 ISP name from the last known SpeedResult, if available.
        asn:                      Autonomous System Number from RIPE Stat, if enrichment is enabled.
        bgp_unstable:             True when RIPE Stat BGP update activity is anomalously high.
        cloudflare_outage_desc:   Annotation text from Cloudflare Radar, if available.
    """

    event_type: OutageEventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    probe_results: str = ""
    duration_seconds: float | None = None
    isp_name: str | None = None
    asn: str | None = None
    bgp_unstable: bool | None = None
    cloudflare_outage_desc: str | None = None

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        if self.duration_seconds is not None and self.duration_seconds < 0:
            raise ValueError(
                f"duration_seconds cannot be negative: {self.duration_seconds}"
            )
