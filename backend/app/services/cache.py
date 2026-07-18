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
