"""Token bucket rate limiter."""
from dataclasses import dataclass


@dataclass
class Bucket:
    capacity: float
    refill_rate: float  # tokens per second
    tokens: float
    last_refill: float

    def refill(self, now: float) -> None:
        elapsed = max(0.0, now - self.last_refill)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def take(self, now: float) -> bool:
        self.refill(now)
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

    def seconds_to_full(self) -> float:
        return (self.capacity - self.tokens) / self.refill_rate


# --- per-route registry -----------------------------------------------------
import asyncio  # noqa: E402
import math  # noqa: E402
import time  # noqa: E402
from collections.abc import Callable  # noqa: E402

from app.core.config import RateLimitConfig  # noqa: E402


@dataclass(frozen=True)
class Decision:
    allowed: bool
    limit: int  # X-RateLimit-Limit
    remaining: int  # X-RateLimit-Remaining (floor of tokens)
    reset: int  # X-RateLimit-Reset: seconds until the bucket is full again
    retry_after: int  # seconds until 1 token is available (0 when allowed)

    def headers(self) -> dict[str, str]:
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(self.reset),
        }


class RateLimiter:
    def __init__(self, cfg: RateLimitConfig, clock: Callable[[], float] = time.monotonic):
        self.cfg = cfg
        self._clock = clock
        self._buckets: dict[str, Bucket] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def configure(self, cfg: RateLimitConfig) -> None:
        # ponytail: new limits reset every bucket to full; carrying tokens over isn't worth it
        self.cfg = cfg
        self._buckets.clear()

    async def acquire(self, key: str) -> Decision:
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            now = self._clock()
            bucket = self._buckets.get(key)
            if bucket is None:
                c = self.cfg
                bucket = self._buckets[key] = Bucket(c.capacity, c.refill_rate, c.capacity, now)
            allowed = bucket.take(now)
            retry = 0 if allowed else max(1, math.ceil((1 - bucket.tokens) / bucket.refill_rate))
            return Decision(
                allowed,
                self.cfg.capacity,
                int(bucket.tokens),
                math.ceil(bucket.seconds_to_full()),
                retry,
            )

    def min_tokens(self) -> float:
        """Tokens in the most drained bucket (capacity when idle). Feeds the dashboard."""
        now = self._clock()
        for b in self._buckets.values():
            b.refill(now)
        return min((b.tokens for b in self._buckets.values()), default=float(self.cfg.capacity))
