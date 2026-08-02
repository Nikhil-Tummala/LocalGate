"""Shared proxy state, created once at startup and hung off app.state."""
from dataclasses import dataclass, field

import httpx

from app.core.config import AppConfig
from app.services.cache import LRUCache
from app.services.chaos import ChaosInjector
from app.services.metrics import Metrics
from app.services.rate_limiter import RateLimiter


@dataclass
class ProxyState:
    config: AppConfig
    limiter: RateLimiter
    cache: LRUCache
    chaos: ChaosInjector
    metrics: Metrics
    client: httpx.AsyncClient
    websockets: set = field(default_factory=set)

    @classmethod
    def create(cls, config: AppConfig) -> "ProxyState":
        return cls(
            config=config,
            limiter=RateLimiter(config.rate_limit),
            cache=LRUCache(config.cache.max_entries),
            chaos=ChaosInjector(config.chaos),
            metrics=Metrics(),
            # one pooled client for the whole process; no overall timeout cap so streams can run long
            client=httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, read=None),
                limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
                follow_redirects=False,
            ),
        )

    def apply(self, config: AppConfig) -> None:
        """Swap in a new config and push it to every service. No restart needed."""
        self.config = config
        self.limiter.configure(config.rate_limit)
        self.cache.resize(config.cache.max_entries)
        self.chaos.configure(config.chaos)
