"""Small in-process rate limiter for ORBIT's local control plane."""

from __future__ import annotations

from dataclasses import dataclass
import time
from threading import Lock


@dataclass(slots=True)
class _Bucket:
    tokens: float
    updated_at: float


class RateLimiter:
    """Token-bucket limiter keyed by caller identity.

    The limiter is intentionally process-local. ORBIT's control plane is local-first;
    distributed rate limiting belongs at a reverse proxy or service boundary.
    """

    def __init__(self, rate_per_minute: int, burst: int) -> None:
        if rate_per_minute <= 0:
            raise ValueError("rate_per_minute must be positive")
        if burst <= 0:
            raise ValueError("burst must be positive")
        self.capacity = float(burst)
        self.refill_per_second = rate_per_minute / 60.0
        self._buckets: dict[str, _Bucket] = {}
        self._lock = Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=self.capacity, updated_at=now)
                self._buckets[key] = bucket
            else:
                elapsed = max(0.0, now - bucket.updated_at)
                bucket.tokens = min(self.capacity, bucket.tokens + elapsed * self.refill_per_second)
                bucket.updated_at = now
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True, 0
            retry_after = max(1, int((1.0 - bucket.tokens) / self.refill_per_second + 0.999))
            return False, retry_after
