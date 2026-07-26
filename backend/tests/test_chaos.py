import asyncio
import random

from app.core.config import ChaosConfig
from app.services.chaos import ChaosInjector


def run(cfg, seed=1):
    return asyncio.run(ChaosInjector(cfg, random.Random(seed)).apply())


def test_disabled_is_a_noop():
    r = run(ChaosConfig())
    assert r.delay_ms == 0 and r.error_status is None


def test_latency_stays_in_range():
    cfg = ChaosConfig(latency_enabled=True, min_delay_ms=5, max_delay_ms=15)
    for seed in range(10):
        assert 5 <= run(cfg, seed).delay_ms <= 15


def test_failure_rate_extremes():
    always = ChaosConfig(error_injection_enabled=True, failure_rate_percentage=1.0, error_status_codes=[503])
    never = ChaosConfig(error_injection_enabled=True, failure_rate_percentage=0.0)
    assert all(run(always, s).error_status == 503 for s in range(20))
    assert all(run(never, s).error_status is None for s in range(20))


def test_failure_rate_is_roughly_honoured():
    cfg = ChaosConfig(error_injection_enabled=True, failure_rate_percentage=0.3)
    inj = ChaosInjector(cfg, random.Random(7))
    hits = sum(asyncio.run(inj.apply()).error_status is not None for _ in range(2000))
    assert 500 < hits < 700
