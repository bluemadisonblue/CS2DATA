"""Environment and shared constants (loaded from `.env` via python-dotenv)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

BOT_VERSION: str = "1.4.0"

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
FACEIT_API_KEY: str = os.getenv("FACEIT_API_KEY", "")
FACEIT_BASE_URL: str = "https://open.faceit.com/data/v4"
GAME_ID: str = "cs2"
DB_PATH: str = os.getenv(
    "DB_PATH",
    str(Path(__file__).resolve().parent / "bot_data.db"),
)

# Rate limits & UX
COOLDOWN_SEC: float = 10.0
MATCHES_PAGE_SIZE: int = 5
RECENT_FORM_LIMIT: int = 12
LEADERBOARD_MAX_USERS: int = 40
PARTY_MAX_PLAYERS: int = 6
INLINE_STATS_MIN_QUERY_LEN: int = 2

# In-process API cache (LRU)
MAX_CACHE_SIZE: int = 2000

# HTTP / FACEIT retries
HTTP_TIMEOUT_SEC: int = 15
FACEIT_RETRY_EXTRA_ATTEMPTS: int = 1
FACEIT_RETRY_BASE_DELAY_SEC: float = 1.5
FACEIT_RETRY_MAX_DELAY_SEC: float = 10.0

# Background match watch (seconds between polls)
WATCH_POLL_INTERVAL: int = 300

# FACEIT CS2 ELO bands: (level, min_elo inclusive, max_elo inclusive). Level 10 is open-ended.
LEVEL_ELO_RANGES: list[tuple[int, int, int]] = [
    (1, 100, 500),
    (2, 501, 750),
    (3, 751, 900),
    (4, 901, 1050),
    (5, 1051, 1200),
    (6, 1201, 1350),
    (7, 1351, 1530),
    (8, 1531, 1750),
    (9, 1751, 2000),
    (10, 2001, 999_999),
]


def level_tier_emoji(level: int) -> str:
    if level <= 2:
        return "🟤"
    if level <= 4:
        return "🟡"
    if level <= 6:
        return "🟠"
    if level <= 8:
        return "🔴"
    if level == 9:
        return "🔵"
    return "🟣"


def elo_progress_in_level(elo: int, level: int) -> tuple[float, int, int | None]:
    """Fraction within current level band, band_min, next_level_min (None at level 10)."""
    if level >= 10:
        return 1.0, elo, None
    band = next((b for b in LEVEL_ELO_RANGES if b[0] == level), None)
    if not band:
        return 0.0, elo, None
    _, lo, hi = band
    span = max(hi - lo, 1)
    frac = max(0.0, min(1.0, (elo - lo) / span))
    next_min = next((b[1] for b in LEVEL_ELO_RANGES if b[0] == level + 1), None)
    return frac, lo, next_min
