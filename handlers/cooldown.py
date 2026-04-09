"""Shared per-user cooldown — TTLCache-backed so memory stays bounded.

All command handlers that enforce a refresh cooldown import check_cooldown()
from here instead of maintaining their own per-module _last dict, which would
grow unbounded and wouldn't share state across commands.
"""

from __future__ import annotations

import time

from cache import TTLCache
from config import COOLDOWN_SEC

# Bounded to 10 000 unique users; LRU eviction keeps memory flat.
_store: TTLCache = TTLCache(maxsize=10_000)


def check_cooldown(user_id: int, cooldown_sec: float = COOLDOWN_SEC) -> str | None:
    """Return an error string if *user_id* is within cooldown, else record the call and return None.

    All commands share the same store, so a user cannot bypass the cooldown by
    rapidly switching between /stats, /profile, /rank, etc.
    """
    key = str(user_id)
    now = time.monotonic()
    prev = _store.get(key, cooldown_sec)
    if prev is not None:
        left = cooldown_sec - (now - prev)
        return f"Wait ~{max(0, left):.0f}s before refreshing."
    _store.set(key, now)
    return None
