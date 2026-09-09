"""In-memory telemetry: counters, rolling latency window, per-second throughput."""
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

WINDOW_SECONDS = 60


def percentile(sorted_vals: list[float], p: float) -> float:
    """Linear-interpolated percentile (p in 0-100) of an already sorted list."""
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


@dataclass
class Metrics:
    clock: Callable[[], float] = time.time
    total: int = 0
    hits: int = 0
    misses: int = 0
    rate_limited: int = 0
    chaos_injected: int = 0
    latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    # second -> [cache hits, upstream fetches]; ponytail: single event loop, so no lock needed
    buckets: dict = field(default_factory=dict)

    def record(self, latency_ms: float, *, cache: str | None = None, outcome: str = "upstream") -> None:
        """cache: 'HIT', 'MISS' or None. outcome: 'upstream', 'limited' (429) or 'synthetic' (chaos)."""
        self.total += 1
        self.latencies.append(latency_ms)
        sec = int(self.clock())
        for old in [s for s in self.buckets if s < sec - WINDOW_SECONDS]:
            del self.buckets[old]
        slot = self.buckets.setdefault(sec, [0, 0])
        if outcome == "limited":
            self.rate_limited += 1
        elif outcome == "synthetic":
            self.chaos_injected += 1
        elif cache == "HIT":
            self.hits += 1
            slot[0] += 1
        elif outcome == "upstream":
            self.misses += cache == "MISS"
            slot[1] += 1

    def snapshot(self, tokens: float, capacity: int) -> dict:
        now = int(self.clock())
        series = []
        for s in range(now - WINDOW_SECONDS + 1, now + 1):
            h, u = self.buckets.get(s, (0, 0))
            series.append({"t": s, "hits": h, "upstream": u})
        vals = sorted(self.latencies)
        lookups = self.hits + self.misses
        last = series[-2] if len(series) > 1 else series[-1]  # last *complete* second
        return {
            "total_requests": self.total,
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "rate_limited": self.rate_limited,
            "chaos_injected": self.chaos_injected,
            "cache_hit_ratio": round(100 * self.hits / lookups, 1) if lookups else 0.0,
            "rps": last["hits"] + last["upstream"],
            "p50_ms": round(percentile(vals, 50), 2),
            "p95_ms": round(percentile(vals, 95), 2),
            "tokens": round(tokens, 1),
            "bucket_capacity": capacity,
            "series": series,
        }
