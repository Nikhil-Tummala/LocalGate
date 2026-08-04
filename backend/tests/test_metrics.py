from app.services.metrics import Metrics, percentile


class Clock:
    t = 1000.0

    def __call__(self):
        return self.t


def test_percentile_interpolates():
    assert percentile([], 95) == 0
    assert percentile([7], 95) == 7
    assert percentile([1, 2, 3, 4, 5], 50) == 3
    assert percentile(list(range(1, 101)), 95) == 95.05


def test_counters_and_hit_ratio():
    m = Metrics(clock=Clock())
    m.record(5, cache="HIT")
    m.record(15, cache="MISS")
    m.record(1, outcome="limited")
    m.record(2, outcome="synthetic")
    s = m.snapshot(tokens=3.04, capacity=10)
    assert (s["total_requests"], s["cache_hits"], s["cache_misses"], s["rate_limited"]) == (4, 1, 1, 1)
    assert s["cache_hit_ratio"] == 50.0 and s["tokens"] == 3.0
    # limited and synthetic responses never count as upstream fetches
    assert s["series"][-1] == {"t": 1000, "hits": 1, "upstream": 1}


def test_rps_uses_last_complete_second_and_window_is_60s():
    clock = Clock()
    m = Metrics(clock=clock)
    for _ in range(4):
        m.record(1, cache="MISS")
    clock.t += 1
    s = m.snapshot(1, 1)
    assert s["rps"] == 4 and len(s["series"]) == 60
    clock.t += 100
    m.record(1, cache="MISS")
    assert list(m.buckets) == [1101]  # old seconds pruned
