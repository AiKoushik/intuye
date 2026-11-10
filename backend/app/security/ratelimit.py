"""Sliding-window rate limiter. In-memory for a single instance; swap for Redis when scaling out."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from app.errors import APIError


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window: float = 60.0) -> None:
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            raise APIError(429, "rate_limited", "Too many requests. Try again in a minute.")
        q.append(now)
