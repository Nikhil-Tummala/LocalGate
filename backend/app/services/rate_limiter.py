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
