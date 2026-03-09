"""SpeedResult dataclass — the shared data contract between all layers."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class SpeedResult:
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    download_mbps: float = 0.0
    upload_mbps: float = 0.0
    ping_ms: float = 0.0
    server_name: str = ""
    server_location: str = ""
    server_id: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Serializable dict — used by exporters and the web layer."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "download_mbps": self.download_mbps,
            "upload_mbps": self.upload_mbps,
            "ping_ms": self.ping_ms,
            "server_name": self.server_name,
            "server_location": self.server_location,
            "server_id": self.server_id,
        }
