"""Compose routers for the bot."""

from aiogram import Router


def setup_routers() -> Router:
    root = Router()
    from . import (
        card,
        compare,
        inline_mode,
        leaderboard,
        maps,
        party,
        profile,
        rank,
        referral,
        register,
        start,
        stats,
        watch_trend,
    )

    root.include_router(start.router)
    root.include_router(inline_mode.router)
    root.include_router(register.router)
    root.include_router(card.router)
    root.include_router(referral.router)
    root.include_router(stats.router)
    root.include_router(maps.router)
    root.include_router(profile.router)
    root.include_router(rank.router)
    root.include_router(compare.router)
    root.include_router(party.router)
    root.include_router(leaderboard.router)
    root.include_router(watch_trend.router)
    return root
