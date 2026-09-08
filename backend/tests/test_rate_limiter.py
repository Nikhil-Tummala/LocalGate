import asyncio

from app.core.config import RateLimitConfig
from app.services.rate_limiter import RateLimiter


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def make(capacity=3, rate=1.0):
    clock = Clock()
    return RateLimiter(RateLimitConfig(capacity=capacity, refill_rate=rate), clock), clock


def test_burst_then_reject_then_refill():
    async def run():
        rl, clock = make()
        got = [(await rl.acquire("r")).allowed for _ in range(4)]
        assert got == [True, True, True, False]
        clock.t = 1.0
        assert (await rl.acquire("r")).allowed
        assert not (await rl.acquire("r")).allowed

    asyncio.run(run())


def test_refill_is_capped_at_capacity():
    async def run():
        rl, clock = make()
        await rl.acquire("r")
        clock.t = 1000
        d = await rl.acquire("r")
        assert d.remaining == 2 and d.reset == 1

    asyncio.run(run())


def test_headers_and_retry_after():
    async def run():
        rl, _ = make(capacity=2, rate=0.5)
        await rl.acquire("r")
        await rl.acquire("r")
        d = await rl.acquire("r")
        assert not d.allowed and d.retry_after == 2 and d.reset == 4
        assert d.headers() == {
            "X-RateLimit-Limit": "2",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "4",
        }

    asyncio.run(run())


def test_routes_are_independent():
    async def run():
        rl, _ = make(capacity=1)
        assert (await rl.acquire("a")).allowed
        assert (await rl.acquire("b")).allowed
        assert not (await rl.acquire("a")).allowed

    asyncio.run(run())


def test_concurrent_requests_never_overspend():
    async def run():
        rl, _ = make(capacity=5, rate=0.001)
        res = await asyncio.gather(*(rl.acquire("r") for _ in range(50)))
        assert sum(d.allowed for d in res) == 5

    asyncio.run(run())


def test_idle_buckets_are_pruned_but_drained_ones_are_kept():
    async def run():
        clock = Clock()
        rl = RateLimiter(RateLimitConfig(capacity=2, refill_rate=1.0), clock, max_routes=3)
        await rl.acquire("drained")
        await rl.acquire("drained")  # 0 tokens left
        for i in range(2):
            await rl.acquire(f"idle{i}")
        clock.t = 0.5  # idle ones are still 0.5 short of full too, so nothing is prunable yet
        await rl.acquire("new1")
        assert len(rl._buckets) == 4
        clock.t = 10  # everything has refilled
        await rl.acquire("new2")
        assert set(rl._buckets) == {"new2"}
        # a drained bucket must survive pruning, or its owner would get a free refill
        await rl.acquire("x")
        await rl.acquire("x")
        await rl.acquire("y")
        await rl.acquire("z")
        assert "x" in rl._buckets and not (await rl.acquire("x")).allowed

    asyncio.run(run())
