"""In-memory per-key rate limiter (fixed window, per-process).

Suitable for single-replica deployments. For multi-replica setups,
replace with a Redis-backed implementation.
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request

from app.config import settings

_lock = Lock()
_counters: dict[str, list[float]] = defaultdict(list)


def _prune(timestamps: list[float], window: float) -> list[float]:
    cutoff = time.monotonic() - window
    return [t for t in timestamps if t >= cutoff]


def check_rate_limit(key: str, limit: int, window_seconds: float = 60.0) -> None:
    """Raise HTTP 429 if key has exceeded limit hits in the last window_seconds."""
    with _lock:
        now = time.monotonic()
        _counters[key] = _prune(_counters[key], window_seconds)
        if len(_counters[key]) >= limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please slow down.",
                headers={"Retry-After": str(int(window_seconds))},
            )
        _counters[key].append(now)


def webhook_rate_limit(request: Request, slug: str) -> None:
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"webhook:{slug}:{ip}", settings.webhook_rate_limit_per_minute)


def api_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"api:{ip}", settings.api_rate_limit_per_minute)
