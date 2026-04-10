"""Generate a shareable PNG stats card for a FACEIT player using Pillow."""

from __future__ import annotations

import io
import os
import sys
from typing import Any

from PIL import Image, ImageDraw, ImageFont

# ── Card dimensions ──────────────────────────────────────────────────────────
CARD_W = 800
CARD_H = 400

# ── Color palette ────────────────────────────────────────────────────────────
_BG        = (13,   17,  23)   # #0d1117 — deep dark background
_BG2       = (22,   27,  34)   # #161b22 — slightly lighter panel
_ACCENT    = (255,  85,   0)   # #ff5500 — FACEIT orange
_WHITE     = (255, 255, 255)
_GRAY      = (139, 148, 158)   # #8b949e — muted labels
_GREEN     = (46,  160,  67)   # #2ea043 — win
_RED       = (248,  81,  73)   # #f85149 — loss
_DIM       = (36,   42,  50)   # #242a32 — divider / unknown form square


# ── Font loading ─────────────────────────────────────────────────────────────

def _font_candidates(bold: bool) -> list[str]:
    if sys.platform == "win32":
        root = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        if bold:
            return [
                os.path.join(root, "segoeuib.ttf"),
                os.path.join(root, "arialbd.ttf"),
                os.path.join(root, "calibrib.ttf"),
                os.path.join(root, "verdanab.ttf"),
            ]
        return [
            os.path.join(root, "segoeui.ttf"),
            os.path.join(root, "arial.ttf"),
            os.path.join(root, "calibri.ttf"),
            os.path.join(root, "verdana.ttf"),
        ]
    # Linux / macOS
    if bold:
        return [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/noto/NotoSans-Bold.ttf",
            "/usr/share/fonts/opentype/noto/NotoSans-Bold.ttf",
        ]
    return [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf",
    ]


def _load_font(
    size: int, bold: bool = False
) -> "ImageFont.FreeTypeFont | ImageFont.ImageFont":
    for path in _font_candidates(bold):
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    # Pillow ≥ 10.1 supports size kwarg on load_default
    try:
        return ImageFont.load_default(size=size)  # type: ignore[call-arg]
    except TypeError:
        return ImageFont.load_default()


_FONT_CACHE: dict[tuple[int, bool], "ImageFont.FreeTypeFont | ImageFont.ImageFont"] = {}


def _f(size: int, bold: bool = False):
    k = (size, bold)
    if k not in _FONT_CACHE:
        _FONT_CACHE[k] = _load_font(size, bold)
    return _FONT_CACHE[k]


# ── Drawing helpers ──────────────────────────────────────────────────────────

def _text_w(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    try:
        bb = draw.textbbox((0, 0), text, font=font)
        return bb[2] - bb[0]
    except AttributeError:
        w, _ = draw.textsize(text, font=font)  # type: ignore[attr-defined]
        return w


def _right(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font, fill) -> None:
    draw.text((x - _text_w(draw, text, font), y), text, font=font, fill=fill)


def _center(draw: ImageDraw.ImageDraw, cx: int, y: int, text: str, font, fill) -> None:
    draw.text((cx - _text_w(draw, text, font) // 2, y), text, font=font, fill=fill)


def _parse_form(form_str: str) -> list[bool | None]:
    """Convert emoji form string to list of True/False/None."""
    out: list[bool | None] = []
    for ch in form_str:
        if ch == "\U0001f7e9":   # 🟩
            out.append(True)
        elif ch == "\U0001f7e5":  # 🟥
            out.append(False)
        elif ch in ("\u2b1c", "—"):  # ⬜
            out.append(None)
    return out


def _rounded_rect(draw: ImageDraw.ImageDraw, xy: tuple, radius: int, fill) -> None:
    """Draw a rectangle with rounded corners (Pillow ≥ 8.2 has rounded_rectangle)."""
    try:
        draw.rounded_rectangle(xy, radius=radius, fill=fill)  # type: ignore[call-arg]
    except AttributeError:
        draw.rectangle(xy, fill=fill)


# ── Card generator ───────────────────────────────────────────────────────────

def generate_stats_card(bundle: dict[str, Any]) -> bytes:
    """Return PNG bytes for a shareable stats card."""
    img = Image.new("RGB", (CARD_W, CARD_H), _BG)
    draw = ImageDraw.Draw(img)

    # Left accent bar (6 px)
    draw.rectangle([0, 0, 6, CARD_H], fill=_ACCENT)

    # ── HEADER ──────────────────────────────────────────────────────────────
    nick    = (bundle.get("nickname") or "?")[:22]
    elo     = bundle.get("elo") or 0
    level   = bundle.get("level") or 0
    region  = bundle.get("region") or "—"
    country = ((bundle.get("player") or {}).get("country") or "").upper()

    # Nickname — large bold white, left
    draw.text((20, 18), nick, font=_f(42, bold=True), fill=_WHITE)

    # ELO — large orange, right-aligned
    _right(draw, CARD_W - 20, 18, f"{elo}", font=_f(42, bold=True), fill=_ACCENT)

    # "ELO" label — small gray, right under ELO number
    _right(draw, CARD_W - 20, 66, "ELO", font=_f(18), fill=_GRAY)

    # Level — below "ELO" label, orange, right
    _right(draw, CARD_W - 20, 88, f"Level {level}", font=_f(18), fill=_ACCENT)

    # Region / country — gray, below nick
    region_label = f"{region}  ·  {country}" if country else region
    draw.text((20, 70), region_label, font=_f(19), fill=_GRAY)

    # ── DIVIDER 1 ────────────────────────────────────────────────────────────
    y_div1 = 115
    draw.rectangle([20, y_div1, CARD_W - 20, y_div1 + 1], fill=_DIM)

    # ── STATS GRID (4 columns) ───────────────────────────────────────────────
    y_label = y_div1 + 12
    y_value = y_label + 22

    stats_cols = [
        ("K/D",       bundle.get("recent_kd_s") or bundle.get("kd_s") or "—"),
        ("HS%",       bundle.get("recent_hs_s") or bundle.get("hs_s") or "—"),
        ("Win Rate",  bundle.get("recent_wr_s") or bundle.get("wr_s") or "—"),
        ("Matches",   bundle.get("mp_s") or "—"),
    ]
    col_xs = [28, 218, 418, 614]

    for (label, value), cx in zip(stats_cols, col_xs):
        draw.text((cx, y_label), label, font=_f(16), fill=_GRAY)
        draw.text((cx, y_value), value, font=_f(36, bold=True), fill=_WHITE)

    # Recent label — small italic gray, right-aligned below values
    rlabel = bundle.get("recent_label") or ""
    if rlabel:
        _right(draw, CARD_W - 20, y_value + 48, rlabel, font=_f(14), fill=_GRAY)

    # ── DIVIDER 2 ────────────────────────────────────────────────────────────
    y_div2 = y_value + 68
    draw.rectangle([20, y_div2, CARD_W - 20, y_div2 + 1], fill=_DIM)

    # ── RECENT FORM ──────────────────────────────────────────────────────────
    y_form_label = y_div2 + 10
    draw.text((20, y_form_label), "Recent form", font=_f(16), fill=_GRAY)

    form_items = _parse_form(bundle.get("form") or "")
    sq = 28     # square size
    gap = 6     # gap between squares
    y_sq = y_form_label + 24

    if form_items:
        x_sq = 20
        for result in form_items[:14]:
            color = _GREEN if result is True else (_RED if result is False else _DIM)
            _rounded_rect(draw, [x_sq, y_sq, x_sq + sq, y_sq + sq], radius=4, fill=color)
            x_sq += sq + gap
    else:
        draw.text((20, y_sq + 4), "No recent data", font=_f(18), fill=_GRAY)

    # Streak text — right of form bar
    streak = bundle.get("streak")
    if streak is not None:
        is_win, n = streak
        streak_text = f"{n} win streak" if is_win else f"{n} loss streak"
        streak_color = _GREEN if is_win else _RED
        _right(draw, CARD_W - 20, y_sq + 4, streak_text, font=_f(18, bold=True), fill=streak_color)

    # ── DIVIDER 3 ────────────────────────────────────────────────────────────
    y_div3 = y_sq + sq + 14
    draw.rectangle([20, y_div3, CARD_W - 20, y_div3 + 1], fill=_DIM)

    # ── TOTALS ROW ───────────────────────────────────────────────────────────
    y_totals = y_div3 + 10
    totals_parts = [
        f"W/L  {bundle.get('wl_s') or '—'}",
        f"Best streak  {bundle.get('streak_s') or '—'}",
        f"K/R  {bundle.get('recent_kr_s') or bundle.get('kr_s') or '—'}",
    ]
    tx = 20
    for part in totals_parts:
        draw.text((tx, y_totals), part, font=_f(16), fill=_GRAY)
        tx += _text_w(draw, part, _f(16)) + 40

    # ── FOOTER / BRANDING ────────────────────────────────────────────────────
    # Bottom orange bar
    draw.rectangle([0, CARD_H - 12, CARD_W, CARD_H], fill=_ACCENT)

    # Brand text above orange bar
    _right(
        draw, CARD_W - 16, CARD_H - 34,
        "CS2DATA · faceit-stats bot",
        font=_f(14), fill=_GRAY,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
