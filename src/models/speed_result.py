"""SpeedResult dataclass — the shared data contract between all layers."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class SpeedResult:
    """Shared data contract for a single speedtest measurement."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    download_mbps: float = 0.0
    upload_mbps: float = 0.0
    ping_ms: float = 0.0
    server_name: str = ""
    server_location: str = ""
    server_id: Optional[int] = None
    jitter_ms: Optional[float] = None
    isp_name: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate field values after initialization."""
        # Validate speeds are non-negative
        if self.download_mbps < 0:
            raise ValueError(f"download_mbps cannot be negative: {self.download_mbps}")
        if self.upload_mbps < 0:
            raise ValueError(f"upload_mbps cannot be negative: {self.upload_mbps}")
        if self.ping_ms < 0:
            raise ValueError(f"ping_ms cannot be negative: {self.ping_ms}")
        if self.jitter_ms is not None and self.jitter_ms < 0:
            raise ValueError(f"jitter_ms cannot be negative: {self.jitter_ms}")

        # Validate timestamp has timezone info
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")

        # Validate server_id if present
        if self.server_id is not None and self.server_id < 0:
            raise ValueError(f"server_id cannot be negative: {self.server_id}")

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
        }
