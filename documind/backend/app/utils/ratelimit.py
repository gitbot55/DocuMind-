"""Small in-memory sliding-window rate limiter (per client IP)."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from ..config import get_settings

_hits: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(request: Request) -> None:
    """FastAPI dependency: raise 429 when a client exceeds the per-minute limit."""
    limit = get_settings().rate_limit_per_minute
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = _hits[ip]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= limit:
        retry = max(1, int(60 - (now - window[0])))
        raise HTTPException(
            status_code=429,
            detail=f"Too many questions. Try again in {retry} seconds.",
            headers={"Retry-After": str(retry)},
        )
    window.append(now)
