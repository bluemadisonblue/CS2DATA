"""Registered users ranked by live FACEIT ELO."""

from __future__ import annotations

import asyncio
import html as html_mod

from aiogram import Router
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command
from aiogram.types import Message

import database as dbmod
from config import LEADERBOARD_MAX_USERS, level_tier_emoji
from handlers.cooldown import check_cooldown
from faceit_api import (
    FaceitAPIError,
    FaceitNotFoundError,
    FaceitRateLimitError,
    FaceitUnavailableError,
    extract_cs2_game,
)
from faceit_messages import html_faceit_transport_error
from keyboards.inline import with_navigation
from ui_text import bold, code, italic, section, sep

router = Router(name="leaderboard")

_FETCH_SEM = asyncio.Semaphore(8)


async def _fetch_lb_row(
    faceit, u: dict
) -> tuple[int, str, int, str]:
    nick_db = u.get("faceit_nickname") or "?"
    async with _FETCH_SEM:
        try:
            p = await faceit.get_player_by_id(u["faceit_player_id"])
        except FaceitNotFoundError:
            return (0, nick_db, 0, "❔")
    g = extract_cs2_game(p) or {}
    elo = int(g.get("faceit_elo") or 0)
    level = int(g.get("skill_level") or 0)
    tier = level_tier_emoji(level) if level else "❔"
    return (elo, str(p.get("nickname") or nick_db), level, tier)


@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: Message, db, faceit) -> None:
    if msg := check_cooldown(message.from_user.id):
        await message.answer(msg, parse_mode=ParseMode.HTML, reply_markup=with_navigation())
        return

    users = await dbmod.list_all_registered_users(db)
    if not users:
        await message.answer(
            bold("No one is registered yet.") + f"\n{italic('Use /register to link your FACEIT account.')}",
            parse_mode=ParseMode.HTML,
            reply_markup=with_navigation(),
        )
        return

    cap = min(len(users), LEADERBOARD_MAX_USERS)
    users = users[:cap]

    if message.bot:
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    loading = await message.answer("⏳ Fetching ELO for registered players…")

    results = await asyncio.gather(
        *[_fetch_lb_row(faceit, u) for u in users],
        return_exceptions=True,
    )

    rows: list[tuple[int, str, int, str]] = []
    for res in results:
        if isinstance(res, (FaceitUnavailableError, FaceitRateLimitError, FaceitAPIError)):
            await loading.delete()
            await message.answer(
                html_faceit_transport_error(res),
                parse_mode=ParseMode.HTML,
                reply_markup=with_navigation(),
            )
            return
        elif isinstance(res, tuple):
            rows.append(res)

    await loading.delete()

    rows.sort(key=lambda r: (-r[0], r[1].lower()))

    lines = [
        section("🏅", "Leaderboard"),
        italic("Registered bot users · live FACEIT CS2 ELO"),
        italic(f"{len(rows)} accounts · max {LEADERBOARD_MAX_USERS} fetched per request"),
        sep(28),
    ]
    for rank, (elo_val, disp, lvl, tier) in enumerate(rows, start=1):
        med = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"{rank}."))
        nick_e = html_mod.escape(disp[:22])
        lines.append(
            f"{med} <b>{nick_e}</b>  {tier} L{code(str(lvl))}  ELO {code(str(elo_val))}"
        )

    await message.answer(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=with_navigation(),
    )
