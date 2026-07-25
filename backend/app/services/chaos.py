"""Chaos injector: optional latency, then optional synthetic upstream failure."""
import asyncio
import random
from dataclasses import dataclass

from app.core.config import ChaosConfig


@dataclass(frozen=True)
class ChaosResult:
    delay_ms: float = 0.0
    error_status: int | None = None


class ChaosInjector:
    def __init__(self, cfg: ChaosConfig, rng: random.Random | None = None):
        self.cfg = cfg
        self._rng = rng or random.Random()

    def configure(self, cfg: ChaosConfig) -> None:
        self.cfg = cfg

    async def apply(self) -> ChaosResult:
        c = self.cfg
        delay_ms = 0.0
        if c.latency_enabled:
            delay_ms = self._rng.uniform(c.min_delay_ms, c.max_delay_ms)
            await asyncio.sleep(delay_ms / 1000)  # non-blocking
        status = None
        if c.error_injection_enabled and self._rng.random() < c.failure_rate_percentage:
            status = self._rng.choice(c.error_status_codes)
        return ChaosResult(delay_ms, status)


def error_payload(status: int) -> dict:
    return {"error": "chaos_injected", "status": status, "message": "Synthetic failure from LocalGate chaos engine"}
