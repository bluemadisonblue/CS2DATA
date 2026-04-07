"""Log each incoming Telegram update (kind, user_id, command/callback/query snippet)."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, Update

from config import LOG_UPDATES

logger = logging.getLogger("bot.requests")


def _detail_from_message(m: Message) -> str:
    text = (m.text or m.caption or "").strip()
    if not text:
        return "non_text"
    if text.startswith("/"):
        token = text.split()[0]
        base = token.split("@")[0]
        return base[:64]
    return "text"


def _describe_update(update: Update) -> tuple[str, int | None, str]:
    """Return (kind, user_id, detail) for structured logs."""
    if update.message:
        m = update.message
        uid = m.from_user.id if m.from_user else None
        return "message", uid, _detail_from_message(m)
    if update.edited_message:
        m = update.edited_message
        uid = m.from_user.id if m.from_user else None
        return "edited_message", uid, _detail_from_message(m)
    if update.callback_query:
        cq = update.callback_query
        uid = cq.from_user.id if cq.from_user else None
        data = (cq.data or "")[:120]
        return "callback_query", uid, data
    if update.inline_query:
        iq = update.inline_query
        uid = iq.from_user.id if iq.from_user else None
        q = (iq.query or "").replace("\n", " ")[:80]
        return "inline_query", uid, q
    if update.chosen_inline_result:
        cir = update.chosen_inline_result
        uid = cir.from_user.id if cir.from_user else None
        qid = (cir.result_id or "")[:64]
        return "chosen_inline_result", uid, qid
    if update.my_chat_member and update.my_chat_member.from_user:
        return (
            "my_chat_member",
            update.my_chat_member.from_user.id,
            (update.my_chat_member.new_chat_member.status or "")[:32],
        )
    return "other", None, ""


class UpdateLoggingMiddleware(BaseMiddleware):
    """Runs first in the update chain when registered before other update middlewares."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if LOG_UPDATES and isinstance(event, Update):
            kind, uid, detail = _describe_update(event)
            safe_detail = detail.replace("\r", " ").replace("\n", " ")
            logger.info(
                "update id=%s kind=%s user_id=%s detail=%s",
                event.update_id,
                kind,
                uid if uid is not None else "-",
                safe_detail,
            )
        return await handler(event, data)
