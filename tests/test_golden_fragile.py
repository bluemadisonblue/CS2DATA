"""Golden regression tests for historically fragile behavior.

- FACEIT CS2 public match links must use ``/cs2/room/`` (``/cs2/match/`` 404s).
- Inline compare parsing: ``vs`` / ``v`` / ``|`` / Cyrillic separators, dedup.
- ``steam_community_url``: every documented shape of FACEIT player payloads.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from faceit_api import (
    _normalize_faceit_cs2_room_url,
    faceit_match_url,
    resolve_match_faceit_url,
    steam_community_url,
)
from handlers.inline_mode import (
    _looks_like_compare_intent,
    _normalize_inline_query,
    _try_parse_vs_query,
)

_STEAM_ID = "76561198000000000"
_STEAM_URL = f"https://steamcommunity.com/profiles/{_STEAM_ID}"


# ---------------------------------------------------------------------------
# Match room URLs (faceit_match_url, normalize, resolve)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "match_id,expected",
    [
        ("1-abc-uuid", "https://www.faceit.com/en/cs2/room/1-abc-uuid"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_golden_faceit_match_url(match_id: str, expected: str) -> None:
    assert faceit_match_url(match_id) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            "https://www.faceit.com/en/cs2/match/1-deadbeef",
            "https://www.faceit.com/en/cs2/room/1-deadbeef",
        ),
        (
            "https://faceit.com/cs2/match/abc-123",
            "https://faceit.com/cs2/room/abc-123",
        ),
        (
            "https://www.faceit.com/en/cs2/room/unchanged",
            "https://www.faceit.com/en/cs2/room/unchanged",
        ),
        (
            "https://x/en/cs2/match/a/en/cs2/match/b",
            "https://x/en/cs2/room/a/en/cs2/match/b",
        ),
    ],
)
def test_golden_normalize_faceit_cs2_room_url(raw: str, expected: str) -> None:
    assert _normalize_faceit_cs2_room_url(raw) == expected


@pytest.mark.parametrize(
    "meta,mid,expected",
    [
        (
            {"faceit_url": "https://www.faceit.com/en/cs2/room/x"},
            "ignored",
            "https://www.faceit.com/en/cs2/room/x",
        ),
        (
            {"faceit_url": "https://www.faceit.com/en/cs2/match/1-deadbeef"},
            "ignored",
            "https://www.faceit.com/en/cs2/room/1-deadbeef",
        ),
        (
            {"faceitUrl": "https://www.faceit.com/cs2/match/abc"},
            "x",
            "https://www.faceit.com/cs2/room/abc",
        ),
        (
            {"url": "https://www.faceit.com/en/cs2/match/z"},
            "y",
            "https://www.faceit.com/en/cs2/room/z",
        ),
        (
            {},
            "mid-1",
            "https://www.faceit.com/en/cs2/room/mid-1",
        ),
    ],
)
def test_golden_resolve_match_faceit_url(
    meta: dict, mid: str, expected: str
) -> None:
    assert resolve_match_faceit_url(meta, mid) == expected


# ---------------------------------------------------------------------------
# Inline vs / | parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query,expected",
    [
        ("unaidy v baler1on", ["unaidy", "baler1on"]),
        ("unaidy vs baler1on", ["unaidy", "baler1on"]),
        ("unaidy|baler1on", ["unaidy", "baler1on"]),
        ("nick1vs nick2", ["nick1", "nick2"]),
        ("a vs b vs c", ["a", "b", "c"]),
        (
            "\u0430\u043d\u043d\u0430 \u0432 \u043f\u0435\u0442\u044f",
            ["\u0430\u043d\u043d\u0430", "\u043f\u0435\u0442\u044f"],
        ),
        ("player1 versus player2", ["player1", "player2"]),
        ("dup vs dup", None),
        ("a VS b", ["a", "b"]),
        ("solo", None),
        ("a|b|c", ["a", "b", "c"]),
    ],
)
def test_golden_try_parse_vs_query(
    query: str, expected: list[str] | None
) -> None:
    assert _try_parse_vs_query(query) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  a  b  ", "a b"),
        ("a\u3000b", "a b"),
    ],
)
def test_golden_normalize_inline_query(raw: str, expected: str) -> None:
    assert _normalize_inline_query(raw) == expected


@pytest.mark.parametrize(
    "query,expected",
    [
        ("solo", False),
        ("a|b", True),
        ("a vs", True),
        ("x \u0432\u0441 y", True),
        ("no compare here", False),
    ],
)
def test_golden_looks_like_compare_intent(query: str, expected: bool) -> None:
    assert _looks_like_compare_intent(query) is expected


# ---------------------------------------------------------------------------
# Steam profile URL extraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "player,expected",
    [
        ({"steam_id_64": _STEAM_ID}, _STEAM_URL),
        ({"steam64": _STEAM_ID}, _STEAM_URL),
        ({"steam_id": _STEAM_ID}, _STEAM_URL),
        ({"platforms": {"steam": {"id": _STEAM_ID}}}, _STEAM_URL),
        ({"platforms": {"steam": {"player_id": _STEAM_ID}}}, _STEAM_URL),
        ({"platforms": {"steam": {"steam_id": _STEAM_ID}}}, _STEAM_URL),
        ({"platforms": {"steam": {"steam_id_64": _STEAM_ID}}}, _STEAM_URL),
        ({"platforms": {"steam": {"steam64": _STEAM_ID}}}, _STEAM_URL),
        ({"platforms": {"STEAM": _STEAM_ID}}, _STEAM_URL),
        ({"platforms": {"steam": _STEAM_ID}}, _STEAM_URL),
        ({"games": {"cs2": {"steam_id_64": _STEAM_ID}}}, _STEAM_URL),
        ({"games": {"cs2": {"steam_id": _STEAM_ID}}}, _STEAM_URL),
        (
            {
                "games": {
                    "cs2": {"platforms": {"steam": {"player_id": _STEAM_ID}}}
                }
            },
            _STEAM_URL,
        ),
        ({"steam_id_64": "12345"}, None),
        ({"steam_id_64": "notdigits"}, None),
        ({"nickname": "x"}, None),
    ],
)
def test_golden_steam_community_url(
    player: dict, expected: str | None
) -> None:
    assert steam_community_url(player) == expected
