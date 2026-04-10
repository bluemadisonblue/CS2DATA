"""In-memory pending referral store.

When a user opens the bot via a referral deep-link (/start ref_<referrer_id>)
we record the pairing here.  The entry is consumed when they complete /register
for the first time.  Restarting the bot clears pending entries — that's fine,
as the window between opening the link and registering is usually short.
"""

from __future__ import annotations

# new_user_telegram_id -> referrer_telegram_id
_pending: dict[int, int] = {}


def set_pending(new_user_id: int, referrer_id: int) -> None:
    if new_user_id != referrer_id:
        _pending[new_user_id] = referrer_id


def consume_pending(new_user_id: int) -> int | None:
    """Return and remove the pending referrer ID, or None if absent."""
    return _pending.pop(new_user_id, None)
