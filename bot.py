"""Entry point: polling, dispatcher, middlewares, shared aiohttp session."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Awaitable, Callable

import aiohttp
import aiosqlite
from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import ErrorEvent, TelegramObject, Update

import database
from cache import TTLCache
from config import (
    BOT_TOKEN,
    BOT_VERSION,
    DB_PATH,
    FACEIT_API_KEY,
    MAX_CACHE_SIZE,
    SENTRY_DSN,
    WATCH_POLL_INTERVAL,
)
from faceit_api import FaceitAPI, FaceitAPIError, parse_match_stats_row
from fsm_storage import SQLiteFSMStorage
from commands_setup import register_bot_commands
from handlers import setup_routers
from middlewares.db_middleware import DbMiddleware
from middlewares.update_logging_middleware import UpdateLoggingMiddleware

logger = logging.getLogger(__name__)


def _init_sentry() -> None:
    if not SENTRY_DSN:
        return
    import sentry_sdk

    release = os.getenv("GIT_SHA") or os.getenv("SOURCE_VERSION") or BOT_VERSION
    env_name = (
        os.getenv("SENTRY_ENVIRONMENT")
        or os.getenv("RAILWAY_ENVIRONMENT_NAME")
        or "production"
    )
    raw_rate = os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0") or "0"
    try:
        traces = max(0.0, min(1.0, float(raw_rate)))
    except ValueError:
        traces = 0.0
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        release=release,
        environment=env_name,
        traces_sample_rate=traces,
    )
    logger.info("Sentry enabled (environment=%s release=%s).", env_name, release)


def _user_id_from_update(update: Update) -> int | None:
    if update.message and update.message.from_user:
        return update.message.from_user.id
    if update.edited_message and update.edited_message.from_user:
        return update.edited_message.from_user.id
    if update.callback_query and update.callback_query.from_user:
        return update.callback_query.from_user.id
    if update.inline_query and update.inline_query.from_user:
        return update.inline_query.from_user.id
    if update.chosen_inline_result and update.chosen_inline_result.from_user:
        return update.chosen_inline_result.from_user.id
    if update.my_chat_member and update.my_chat_member.from_user:
        return update.my_chat_member.from_user.id
    return None


class FaceitInjectMiddleware(BaseMiddleware):
    """Injects the shared FaceitAPI client (no per-request overhead)."""

    def __init__(self, faceit: FaceitAPI) -> None:
        self._faceit = faceit

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["faceit"] = self._faceit
        return await handler(event, data)


# ---------------------------------------------------------------------------
# Background watch loop
# ---------------------------------------------------------------------------

async def _check_all_watchers(bot: Bot, faceit: FaceitAPI) -> None:
    """Check every watching user for a new match and notify them."""
    async with aiosqlite.connect(DB_PATH) as db:
        users = await database.get_watching_users(db)

        for user in users:
            tid = user["telegram_id"]
            pid = user["faceit_player_id"]
            last_mid = user.get("last_match_id")

            try:
                raw = await faceit.get_player_match_stats(pid, limit=1, offset=0)
            except FaceitAPIError:
                continue

            items = (raw or {}).get("items") or []
            if not items or not isinstance(items[0], dict):
                continue

            stats = items[0].get("stats")
            if not isinstance(stats, dict):
                continue

            row = parse_match_stats_row(stats)
            mid = row.get("match_id")
            if not mid:
                continue

            if last_mid is None:
                await database.update_last_match_id(db, tid, mid)
                continue

            if mid == last_mid:
                continue

            await database.update_last_match_id(db, tid, mid)

            wl = "✅ Win" if row["won"] is True else ("❌ Loss" if row["won"] is False else "Match ended")
            map_name = row.get("map") or "—"
            kd_val = row.get("kd")
            kd_s = f"{kd_val:.2f}" if kd_val is not None else "—"

            msg = (
                f"🔔 <b>New match!</b>\n"
                f"{wl} · <b>{map_name}</b>\n"
                f"K/D <code>{kd_s}</code>"
            )
            try:
                await bot.send_message(tid, msg, parse_mode="HTML")
            except TelegramForbiddenError:
                logger.info("User %s blocked the bot — disabling watch.", tid)
                await database.set_watching(db, tid, False)
            except Exception as exc:
                logger.warning("Failed to notify user %s: %s", tid, exc)


async def watch_loop(bot: Bot, faceit: FaceitAPI) -> None:
    """Periodic background task — polls for new matches every WATCH_POLL_INTERVAL seconds."""
    logger.info("Watch loop started (interval=%ds).", WATCH_POLL_INTERVAL)
    while True:
        try:
            await asyncio.sleep(WATCH_POLL_INTERVAL)
        except asyncio.CancelledError:
            logger.info("Watch loop cancelled.")
            return
        try:
            await _check_all_watchers(bot, faceit)
        except Exception as exc:
            logger.error("Watch loop iteration failed: %s", exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    _init_sentry()
    if not BOT_TOKEN or not FACEIT_API_KEY:
        raise SystemExit(
            "Missing BOT_TOKEN or FACEIT_API_KEY. Set them as runtime environment variables. "
            "On DigitalOcean App Platform, edit the worker → Environment Variables and ensure "
            "each secret’s scope includes Run Time (not Build Time only)."
        )

    await database.init_db()

    _git = os.environ.get("GIT_SHA") or os.environ.get("SOURCE_VERSION") or "local"
    logger.info(
        "CS2DATA starting — version=%s build=%s db=%s watch_interval=%ss",
        BOT_VERSION,
        _git,
        DB_PATH,
        WATCH_POLL_INTERVAL,
    )

    # FSM in SQLite so /register confirmation survives restarts (see fsm_storage.py).
    storage = SQLiteFSMStorage(DB_PATH)

    async with aiohttp.ClientSession() as http:
        faceit = FaceitAPI(http, FACEIT_API_KEY, cache=TTLCache(maxsize=MAX_CACHE_SIZE))
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        try:
            await register_bot_commands(bot)
        except Exception as exc:
            logger.warning("Could not register / command menu: %s", exc)
        dp = Dispatcher(storage=storage)

        @dp.errors()
        async def global_errors(event: ErrorEvent) -> None:
            uid = _user_id_from_update(event.update)
            logger.error(
                "Handler error update_id=%s user_id=%s: %s",
                event.update.update_id,
                uid if uid is not None else "-",
                event.exception,
                exc_info=event.exception,
            )
            if SENTRY_DSN:
                import sentry_sdk

                sentry_sdk.capture_exception(event.exception)

        dp.update.middleware(UpdateLoggingMiddleware())
        dp.update.middleware(FaceitInjectMiddleware(faceit))
        dp.update.middleware(DbMiddleware())
        dp.include_router(setup_routers())

        watch_task = asyncio.create_task(watch_loop(bot, faceit))
        try:
            # handle_signals=True (default): SIGINT/SIGTERM stop polling gracefully on Unix.
            # Windows: Ctrl+C may raise KeyboardInterrupt in asyncio.run; finally still runs.
            await dp.start_polling(bot, handle_signals=True, close_bot_session=True)
        finally:
            watch_task.cancel()
            try:
                await watch_task
            except asyncio.CancelledError:
                pass
            await storage.close()
            await bot.session.close()
            logger.info("Bot shut down cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
