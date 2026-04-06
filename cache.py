"""In-memory LRU + TTL cache for FACEIT API responses.

Designed for single-threaded asyncio use — no locking needed.
Evicts the Least Recently Used entry when *maxsize* is exceeded,
so memory stays bounded regardless of how many unique players are queried.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any


class TTLCache:
    """Key-value store with per-entry TTL expiry and LRU eviction."""

    def __init__(self, maxsize: int = 1000) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._maxsize = maxsize

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def get(self, key: str, ttl: float) -> Any:
        """Return the cached value if it exists and is younger than *ttl* seconds.

        - Moves the entry to most-recently-used position on hit.
        - Removes and returns ``None`` on TTL expiry.
        - Returns ``None`` on cache miss.
        """
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, val = entry
        if time.monotonic() - ts > ttl:
            del self._store[key]
            return None
        # Promote to most-recently-used end
        self._store.move_to_end(key)
        return val

    def set(self, key: str, value: Any) -> None:
        """Store *value* under *key*, timestamped now.

        Evicts the least-recently-used entry if the cache is at *maxsize*.
        """
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (time.monotonic(), value)
        # Evict LRU entries until within maxsize
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)

    def invalidate(self, key: str) -> None:
        """Remove a single entry (no-op if missing)."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Wipe all cached entries."""
        self._store.clear()

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @property
    def maxsize(self) -> int:
        return self._maxsize

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        return key in self._store
