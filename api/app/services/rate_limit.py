"""Per-IP sliding-window rate limiter for the Overreach endpoint.

In-memory only — fine for single-process dev and the Phase 5 soft
launch. Phase 5 may swap this for a Redis-backed limiter when we
deploy multiple workers.

The window is one hour. The limit is 3 calls per IP per hour by
default (configurable via OVERREACH_RATE_LIMIT_PER_HOUR).
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

WINDOW_SECONDS = 3600


class RateLimiter:
    def __init__(self, window_seconds: int = WINDOW_SECONDS) -> None:
        self._window = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int) -> tuple[bool, int]:
        """Returns (allowed, retry_after_seconds).

        retry_after_seconds is 0 when allowed; otherwise the number of
        seconds until the oldest in-window call falls off.
        """
        if limit <= 0:
            return False, self._window
        now = time.time()
        with self._lock:
            bucket = self._buckets[key]
            cutoff = now - self._window
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_in = int(bucket[0] + self._window - now) + 1
                return False, max(retry_in, 1)
            bucket.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


# Module-level singleton: one limiter for the Overreach endpoint.
overreach_limiter = RateLimiter()
