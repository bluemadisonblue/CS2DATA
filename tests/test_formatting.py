"""Tests for formatting.py: flag_emoji, recent_form_badge, score helpers."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from formatting import flag_emoji, format_score_from_history, pick_history_meta, recent_form_badge


class TestFlagEmoji:
    def test_germany(self):
        assert flag_emoji("DE") == "🇩🇪"

    def test_us(self):
        assert flag_emoji("US") == "🇺🇸"

    def test_lowercase_converted(self):
        assert flag_emoji("de") == "🇩🇪"

    def test_mixed_case(self):
        assert flag_emoji("De") == "🇩🇪"

    def test_none_returns_empty(self):
        assert flag_emoji(None) == ""

    def test_empty_string_returns_empty(self):
        assert flag_emoji("") == ""

    def test_three_letters_returns_empty(self):
        assert flag_emoji("DEU") == ""

    def test_one_letter_returns_empty(self):
        assert flag_emoji("D") == ""

    def test_non_alpha_returns_empty(self):
        assert flag_emoji("1A") == ""

    def test_both_non_alpha_returns_empty(self):
        assert flag_emoji("12") == ""

    def test_valid_unknown_country(self):
        # "XX" is valid format even if not a real country — should not crash
        result = flag_emoji("XX")
        assert isinstance(result, str)

    def test_brazil(self):
        assert flag_emoji("BR") == "🇧🇷"

    def test_turkey(self):
        assert flag_emoji("TR") == "🇹🇷"


class TestRecentFormBadge:
    def _make_item(self, result: str) -> dict:
        """Create a minimal match stats item."""
        return {"stats": {"Result": result}}

    def test_empty_items_returns_dash(self):
        text, n = recent_form_badge([])
        assert text == "—"
        assert n == 0

    def test_win(self):
        badge, n = recent_form_badge([self._make_item("1")])
        assert "🟩" in badge
        assert n == 1

    def test_loss(self):
        badge, n = recent_form_badge([self._make_item("0")])
        assert "🟥" in badge
        assert n == 1

    def test_unknown_result(self):
        badge, n = recent_form_badge([{"stats": {"Result": "?"}}])
        assert "⬜" in badge
        assert n == 1

    def test_mixed_results(self):
        items = [
            self._make_item("1"),
            self._make_item("0"),
            self._make_item("1"),
        ]
        badge, n = recent_form_badge(items)
        assert "🟩" in badge
        assert "🟥" in badge
        assert n == 3

    def test_limit_applied(self):
        items = [self._make_item("1")] * 20
        badge, n = recent_form_badge(items, limit=5)
        assert badge.count("🟩") == 5
        assert n == 5

    def test_default_limit_is_8(self):
        items = [self._make_item("1")] * 20
        badge, n = recent_form_badge(items)
        assert badge.count("🟩") == 8
        assert n == 8

    def test_non_dict_item_skipped(self):
        items = ["not_a_dict", self._make_item("1")]
        badge, _ = recent_form_badge(items)
        assert "🟩" in badge

    def test_missing_stats_key_skipped(self):
        items = [{"no_stats": {}}, self._make_item("1")]
        badge, _ = recent_form_badge(items)
        assert "🟩" in badge

    def test_all_unknown(self):
        items = [{"stats": {}}] * 3
        badge, n = recent_form_badge(items)
        assert badge.count("⬜") == 3
        assert n == 3


class TestFormatScoreFromHistory:
    def test_none_input(self):
        assert format_score_from_history(None) is None

    def test_empty_dict(self):
        assert format_score_from_history({}) is None

    def test_valid_score(self):
        results = {"score": {"faction1": 16, "faction2": 14}}
        result = format_score_from_history(results)
        assert result == "16–14"

    def test_score_sorted_descending(self):
        results = {"score": {"faction1": 10, "faction2": 16}}
        result = format_score_from_history(results)
        assert result == "16–10"

    def test_missing_score_key(self):
        results = {"winner": "faction1"}
        assert format_score_from_history(results) is None

    def test_empty_score_dict(self):
        results = {"score": {}}
        assert format_score_from_history(results) is None

    def test_invalid_score_values(self):
        results = {"score": {"a": "bad", "b": "data"}}
        assert format_score_from_history(results) is None

    def test_non_dict_score(self):
        results = {"score": "16-14"}
        assert format_score_from_history(results) is None


class TestPickHistoryMeta:
    def test_basic_fields(self):
        item = {
            "match_id": "abc123",
            "competition_name": "CS2 Matchmaking",
            "game_mode": "5v5",
            "results": {"score": {"a": 16, "b": 14}},
        }
        meta = pick_history_meta(item)
        assert meta["match_id"] == "abc123"
        assert meta["competition"] == "CS2 Matchmaking"
        assert meta["mode"] == "5v5"
        assert meta["score"] == "16–14"

    def test_missing_match_id(self):
        meta = pick_history_meta({"competition_name": "Test"})
        assert meta["match_id"] is None

    def test_id_fallback(self):
        item = {"ID": "xyz", "competition_name": "Test"}
        meta = pick_history_meta(item)
        assert meta["match_id"] == "xyz"

    def test_no_score(self):
        item = {"match_id": "abc", "results": {}}
        meta = pick_history_meta(item)
        assert meta["score"] is None

    def test_empty_item(self):
        meta = pick_history_meta({})
        assert meta["match_id"] is None
        assert meta["competition"] is None
        assert meta["mode"] is None
        assert meta["score"] is None
