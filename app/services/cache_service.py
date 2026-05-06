from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from threading import RLock
from typing import Any, Callable, TypeVar


T = TypeVar("T")


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class SimpleTTLCache:
    """Small in-process TTL cache for API responses."""

    def __init__(self) -> None:
        self._items: dict[str, CacheEntry] = {}
        self._lock = RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any | None:
        now = monotonic()
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                self.misses += 1
                return None
            if entry.expires_at <= now:
                self.misses += 1
                self._items.pop(key, None)
                return None
            self.hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> Any:
        with self._lock:
            self._items[key] = CacheEntry(value=value, expires_at=monotonic() + ttl_seconds)
        return value

    def get_or_set(self, key: str, ttl_seconds: int, factory: Callable[[], T]) -> T:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = factory()
        self.set(key, value, ttl_seconds)
        return value

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self.hits = 0
            self.misses = 0

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {"entries": len(self._items), "hits": self.hits, "misses": self.misses}


default_cache = SimpleTTLCache()


def cache_key(namespace: str, *parts: Any, **kwargs: Any) -> str:
    normalized_kwargs = tuple(sorted(kwargs.items()))
    return repr((namespace, parts, normalized_kwargs))
