"""SQLite-backed FSM storage so registration confirmation survives bot restarts."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import aiosqlite
from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, DefaultKeyBuilder, StateType, StorageKey

logger = logging.getLogger(__name__)


class SQLiteFSMStorage(BaseStorage):
    """Persists FSM state in the same SQLite file as users (table fsm_state)."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._kb = DefaultKeyBuilder(with_bot_id=True)

    def _storage_key(self, key: StorageKey) -> str:
        return self._kb.build(key)

    async def _ensure_table(self, db: aiosqlite.Connection) -> None:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS fsm_state (
                storage_key TEXT PRIMARY KEY,
                state TEXT,
                data TEXT NOT NULL DEFAULT '{}'
            )
            """
        )

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        k = self._storage_key(key)
        if state is None:
            st: Optional[str] = None
        elif isinstance(state, State):
            st = state.state
        else:
            st = state

        async with aiosqlite.connect(self._path) as db:
            await self._ensure_table(db)
            async with db.execute(
                "SELECT data FROM fsm_state WHERE storage_key = ?", (k,)
            ) as cur:
                row = await cur.fetchone()
            data_s = row[0] if row else "{}"
            await db.execute(
                """
                INSERT INTO fsm_state (storage_key, state, data)
                VALUES (?, ?, ?)
                ON CONFLICT(storage_key) DO UPDATE SET state = excluded.state
                """,
                (k, st, data_s),
            )
            await db.commit()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        k = self._storage_key(key)
        async with aiosqlite.connect(self._path) as db:
            await self._ensure_table(db)
            async with db.execute(
                "SELECT state FROM fsm_state WHERE storage_key = ?", (k,)
            ) as cur:
                row = await cur.fetchone()
        return row[0] if row and row[0] is not None else None

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        k = self._storage_key(key)
        payload = json.dumps(data, separators=(",", ":"))
        async with aiosqlite.connect(self._path) as db:
            await self._ensure_table(db)
            async with db.execute(
                "SELECT state FROM fsm_state WHERE storage_key = ?", (k,)
            ) as cur:
                row = await cur.fetchone()
            st = row[0] if row else None
            await db.execute(
                """
                INSERT INTO fsm_state (storage_key, state, data)
                VALUES (?, ?, ?)
                ON CONFLICT(storage_key) DO UPDATE SET data = excluded.data
                """,
                (k, st, payload),
            )
            await db.commit()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        k = self._storage_key(key)
        async with aiosqlite.connect(self._path) as db:
            await self._ensure_table(db)
            async with db.execute(
                "SELECT data FROM fsm_state WHERE storage_key = ?", (k,)
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return {}
        try:
            raw = json.loads(row[0] or "{}")
            return raw if isinstance(raw, dict) else {}
        except json.JSONDecodeError:
            logger.warning("Corrupt FSM JSON for key %s", k)
            return {}

    async def close(self) -> None:
        pass
