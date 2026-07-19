"""In-memory LRU response cache with per-entry TTL."""
import hashlib
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit


def make_key(method: str, url: str, body: bytes = b"") -> str:
    """SHA-256 over METHOD + URL (sans query) + sorted query + sha256(body)."""
    parts = urlsplit(url)
    base = f"{parts.scheme}://{parts.netloc}{parts.path}"
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    raw = "\n".join([method.upper(), base, query, hashlib.sha256(body).hexdigest()])
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class CacheEntry:
    body: bytes
    status_code: int
    content_type: str | None
    created_at: float
    ttl: float

    def fresh(self, now: float) -> bool:
        return now < self.created_at + self.ttl


class LRUCache:
    def __init__(self, max_entries: int = 1000, clock: Callable[[], float] = time.monotonic):
        self.max_entries = max_entries
        self._clock = clock
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()

    def __len__(self) -> int:
        return len(self._store)

    def get(self, key: str) -> CacheEntry | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if not entry.fresh(self._clock()):
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return entry

    def put(self, key: str, body: bytes, status_code: int, content_type: str | None, ttl: float) -> None:
        self._store[key] = CacheEntry(body, status_code, content_type, self._clock(), ttl)
        self._store.move_to_end(key)
        self._evict()

    def resize(self, max_entries: int) -> None:
        self.max_entries = max_entries
        self._evict()

    def clear(self) -> int:
        n = len(self._store)
        self._store.clear()
        return n

    def _evict(self) -> None:
        while len(self._store) > self.max_entries:
            self._store.popitem(last=False)  # least recently used is at the front
