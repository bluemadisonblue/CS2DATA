"""Load environment variables via python-dotenv and define shared constants."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

BOT_VERSION: str = "1.4.0"

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
FACEIT_API_KEY: str = os.getenv("FACEIT_API_KEY", "")
FACEIT_BASE_URL: str = "https://open.faceit.com/data/v4"
GAME_ID: str = "cs2"
# Local default: project dir. For Docker/DO: set DB_PATH=/data/bot_data.db and mount a volume on /data.
DB_PATH: str = os.getenv(
    "DB_PATH",
    str(Path(__file__).resolve().parent / "bot_data.db"),
)

# ---------------------------------------------------------------------------
# Rate / cooldown settings
# ---------------------------------------------------------------------------
# How many seconds a user must wait between heavy stat commands.
COOLDOWN_SEC: float = 10.0

# ---------------------------------------------------------------------------
# Display settings
# ---------------------------------------------------------------------------
# Matches shown per page in /matches.
MATCHES_PAGE_SIZE: int = 5

# Recent matches fetched for the form badge in /stats.
RECENT_FORM_LIMIT: int = 12

# Max registered users to pull ELO for in /leaderboard (API + time bound).
LEADERBOARD_MAX_USERS: int = 40

# Max FACEIT nicknames in one /party compare.
PARTY_MAX_PLAYERS: int = 6

# Minimum characters before inline @bot nickname search runs.
INLINE_STATS_MIN_QUERY_LEN: int = 2

# ---------------------------------------------------------------------------
# Cache settings
# ---------------------------------------------------------------------------
# Maximum number of entries the in-process LRU cache may hold before evicting.
MAX_CACHE_SIZE: int = 2000

# ---------------------------------------------------------------------------
# HTTP client settings
# ---------------------------------------------------------------------------
# Hard timeout (seconds) for FACEIT API requests.
HTTP_TIMEOUT_SEC: int = 15

# Retries after the first request fails (429 / 5xx / timeout). Total attempts = 1 + this value.
FACEIT_RETRY_EXTRA_ATTEMPTS: int = 1
# Exponential backoff: sleep min(MAX, BASE * 2^attempt_index) seconds before each retry.
FACEIT_RETRY_BASE_DELAY_SEC: float = 1.5
FACEIT_RETRY_MAX_DELAY_SEC: float = 10.0

# ---------------------------------------------------------------------------
# Watch / alert settings
# ---------------------------------------------------------------------------
# How often (seconds) the background task polls for new matches.
WATCH_POLL_INTERVAL: int = 300  # 5 minutes

# ---------------------------------------------------------------------------
# Official FACEIT CS2 ELO ranges per level (min ELO inclusive, max inclusive).
# Level 10 is open-ended.
# ---------------------------------------------------------------------------
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
    """Visual tier emoji buckets (1–10) per product spec."""
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
    """
    Returns (fraction 0-1 within current level band, band_min, next_level_min_or_none).
    Level 10 has no next threshold.
    """
    if level >= 10:
        return 1.0, elo, None
    band = next((b for b in LEVEL_ELO_RANGES if b[0] == level), None)
    if not band:
        return 0.0, elo, None
    _, lo, hi = band
    span = max(hi - lo, 1)
    frac = (elo - lo) / span
    frac = max(0.0, min(1.0, frac))
    next_min = next((b[1] for b in LEVEL_ELO_RANGES if b[0] == level + 1), None)
    return frac, lo, next_min
