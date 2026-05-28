"""SpeedResult dataclass — the shared data contract between all layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _check_non_negative(value: float, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative: {value}")


def _check_optional_non_negative(value: float | None, name: str) -> None:
    if value is not None and value < 0:
        raise ValueError(f"{name} cannot be negative: {value}")


def _check_optional_range(
    value: float | None, name: str, lo: float, hi: float
) -> None:
    if value is not None and not (lo <= value <= hi):
        raise ValueError(f"{name} must be {lo}–{hi}: {value}")


@dataclass
class SpeedResult:
    """Shared data contract for a single speedtest measurement."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    download_mbps: float = 0.0
    upload_mbps: float = 0.0
    ping_ms: float = 0.0
    server_name: str = ""
    server_location: str = ""
    server_id: int | None = None
    jitter_ms: float | None = None
    isp_name: str | None = None
    packet_loss_pct: float | None = None
    quality_score: float | None = None
    sla_ok: bool | None = None

    def __post_init__(self) -> None:
        """Validate field values after initialization."""
        _check_non_negative(self.download_mbps, "download_mbps")
        _check_non_negative(self.upload_mbps, "upload_mbps")
        _check_non_negative(self.ping_ms, "ping_ms")
        _check_optional_non_negative(self.jitter_ms, "jitter_ms")

        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")

        if self.server_id is not None and self.server_id < 0:
            raise ValueError(f"server_id cannot be negative: {self.server_id}")

        _check_optional_range(self.packet_loss_pct, "packet_loss_pct", 0.0, 100.0)
        _check_optional_range(self.quality_score, "quality_score", 0.0, 100.0)

    def to_dict(self) -> dict[str, Any]:
        """Serializable dict — used by exporters and the web layer."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "download_mbps": self.download_mbps,
            "upload_mbps": self.upload_mbps,
            "ping_ms": self.ping_ms,
            "jitter_ms": self.jitter_ms,
            "isp_name": self.isp_name,
            "server_name": self.server_name,
            "server_location": self.server_location,
            "server_id": self.server_id,
            "packet_loss_pct": self.packet_loss_pct,
            "quality_score": self.quality_score,
            "sla_ok": self.sla_ok,
        }
