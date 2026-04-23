"""API key authentication dependency for FastAPI.

If the ``API_KEY`` environment variable is set, every protected endpoint
requires the caller to supply a matching ``X-Api-Key`` header.

If ``API_KEY`` is *not* set, the dependency is a no-op — all requests are
permitted. This keeps local development and unauthenticated self-hosted
deployments zero-config.

Rate limiting (``RATE_LIMIT_PER_MINUTE``) is applied per API key when auth
is enabled. Set to 0 to disable rate limiting while keeping auth on.
"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from collections import defaultdict
from typing import Annotated

from fastapi import Header, HTTPException

from src import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sliding-window rate limiter (in-process, per API key)
# ---------------------------------------------------------------------------
_rate_lock = threading.Lock()
_request_timestamps: dict[str, list[float]] = defaultdict(list)
_WINDOW_SECONDS = 60


def _check_rate_limit(key: str) -> bool:
    """Return True if the request is within the rate limit, False if exceeded."""
    limit = config.RATE_LIMIT_PER_MINUTE
    if not limit:
        return True
    now = time.monotonic()
    cutoff = now - _WINDOW_SECONDS
    with _rate_lock:
        timestamps = _request_timestamps[key]
        _request_timestamps[key] = [t for t in timestamps if t > cutoff]
        if len(_request_timestamps[key]) >= limit:
            return False
        _request_timestamps[key].append(now)
        return True


def _reset_rate_limit_state() -> None:
    """Clear all rate-limit counters. Intended for use in tests only."""
    with _rate_lock:
        _request_timestamps.clear()


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """FastAPI dependency that enforces API key authentication and rate limiting.

    Raises:
        HTTPException 401: key is required but was not provided.
        HTTPException 403: key was provided but does not match.
        HTTPException 429: key is valid but rate limit has been exceeded.
    """
    if not config.API_KEY:
        return  # Auth disabled — allow all requests.
    if x_api_key is None:
        logger.warning("auth: rejected request — missing X-Api-Key header")
        raise HTTPException(status_code=401, detail="Missing X-Api-Key header.")
    if not secrets.compare_digest(x_api_key, config.API_KEY):
        logger.warning("auth: rejected request — invalid API key supplied")
        raise HTTPException(status_code=403, detail="Invalid API key.")
    if not _check_rate_limit(x_api_key):
        logger.warning("auth: rate limit exceeded for key prefix=%.4s", x_api_key)
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
