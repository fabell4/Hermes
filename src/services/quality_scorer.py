"""Connection quality scoring for Hermes.

Computes a composite 0–100 score from up to five measured dimensions of a
SpeedResult.  A higher score indicates a better connection.

Reference thresholds
--------------------
Scores are interpolated linearly between the *ideal* value (100 points) and
the *maximum bad* value (0 points).  Values beyond the bad threshold are
clamped at 0.

| Dimension    | Ideal           | 0-point (worst) |
|--------------|-----------------|-----------------|
| Download     | 100 Mbps        | 0 Mbps          |
| Upload       | 50 Mbps         | 0 Mbps          |
| Ping         | 0 ms            | 150 ms          |
| Jitter       | 0 ms            | 30 ms           |
| Packet loss  | 0 %             | 5 %             |

Weights: download 30 %, upload 30 %, ping 20 %, jitter 10 %, packet loss 10 %.
Jitter and packet loss default to a perfect score when not reported by the server.
"""

from __future__ import annotations

from src.models.speed_result import SpeedResult

# ---- Reference thresholds ------------------------------------------------
_IDEAL_DOWNLOAD_MBPS: float = 100.0
_IDEAL_UPLOAD_MBPS: float = 50.0
_MAX_PING_MS: float = 150.0
_MAX_JITTER_MS: float = 30.0
_MAX_LOSS_PCT: float = 5.0

# ---- Weights (must sum to 1.0) -------------------------------------------
_W_DOWNLOAD: float = 0.30
_W_UPLOAD: float = 0.30
_W_PING: float = 0.20
_W_JITTER: float = 0.10
_W_LOSS: float = 0.10


def compute(result: SpeedResult) -> float:
    """Return a 0–100 quality score for *result*, rounded to one decimal place.

    Args:
        result: A SpeedResult instance with measured values.

    Returns:
        A float in [0.0, 100.0].
    """
    download_s = min(result.download_mbps / _IDEAL_DOWNLOAD_MBPS, 1.0)
    upload_s = min(result.upload_mbps / _IDEAL_UPLOAD_MBPS, 1.0)
    ping_s = max(1.0 - result.ping_ms / _MAX_PING_MS, 0.0)

    jitter_s = (
        max(1.0 - result.jitter_ms / _MAX_JITTER_MS, 0.0)
        if result.jitter_ms is not None
        else 1.0  # Assume perfect when not reported
    )

    loss_s = (
        max(1.0 - result.packet_loss_pct / _MAX_LOSS_PCT, 0.0)
        if result.packet_loss_pct is not None
        else 1.0  # Assume zero loss when not reported
    )

    score = (
        _W_DOWNLOAD * download_s
        + _W_UPLOAD * upload_s
        + _W_PING * ping_s
        + _W_JITTER * jitter_s
        + _W_LOSS * loss_s
    ) * 100.0

    return round(score, 1)
