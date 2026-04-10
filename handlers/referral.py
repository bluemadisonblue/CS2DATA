"""Referral program: /referral — show link, count, and invite instructions."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

import database as dbmod
from keyboards.inline import referral_kb, with_navigation
from ui_text import bold, code, italic, section, sep

router = Router(name="referral")

logger = logging.getLogger(__name__)

# Cached bot username (resolved once on first use)
_BOT_USERNAME: str | None = None


async def _username(message: Message) -> str:
    global _BOT_USERNAME
    if _BOT_USERNAME is None and message.bot:
        try:
            me = await message.bot.get_me()
            _BOT_USERNAME = me.username or "CS2DATAbot"
        except Exception:
            _BOT_USERNAME = "CS2DATAbot"
    return _BOT_USERNAME or "CS2DATAbot"


async def send_referral_page(
    message: Message,
    db,
    *,
    actor_id: int | None = None,
) -> None:
    tid = actor_id if actor_id is not None else (
        message.from_user.id if message.from_user else None
    )
    if tid is None:
        return

    bot_name = await _username(message)
    ref_url = f"https://t.me/{bot_name}?start=ref_{tid}"

    stats = await dbmod.get_referral_stats(db, tid)
    total = stats["total"]
    last_at = stats["last_at"]

    # Format last referral date
    last_str = ""
    if last_at:
        try:
            dt = datetime.fromisoformat(str(last_at).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            last_str = dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            last_str = str(last_at)[:10]

    lines = [
        section("👥", "Referral program"),
        "",
        bold("Invite friends to CS2DATA"),
        italic("Share your personal link — every friend who registers counts."),
        "",
        sep(24),
        "",
        bold("Your referral link:"),
        code(ref_url),
        "",
        sep(24),
        "",
    ]

    if total == 0:
        lines += [
            "You haven't referred anyone yet.",
            "",
            italic("Share your link and grow the leaderboard!"),
        ]
    elif total == 1:
        lines += [
            f"✅ {bold('1')} friend referred" + (f"  ·  {italic(last_str)}" if last_str else ""),
        ]
    else:
        lines += [
            f"✅ {bold(str(total))} friends referred"
            + (f"  ·  last {italic(last_str)}" if last_str else ""),
        ]

    lines += [
        "",
        sep(24),
        "",
        italic("How it works:"),
        f"1. Share your link above",
        f"2. Friend opens it and runs {code('/register')}",
        f"3. They appear on the leaderboard — your count goes up",
    ]

    await message.answer(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=referral_kb(ref_url),
    )


@router.message(Command("referral"))
async def cmd_referral(message: Message, db) -> None:
    await send_referral_page(message, db)
