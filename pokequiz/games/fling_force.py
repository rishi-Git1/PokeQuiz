"""Fling Force: guess Fling power or fling effect from an item."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from pokequiz.data import _fetch_json


@dataclass(frozen=True, slots=True)
class FlingForceChallenge:
    item_slug: str
    fling_power: int | None
    fling_effect_slug: str | None


def _effect_display_name(effect_slug: str) -> str:
    special = {
        "paralyze": "Paralysis",
        "badly-poison": "Badly Poisoned",
    }
    if effect_slug in special:
        return special[effect_slug]
    return effect_slug.replace("-", " ").title()


def _normalized_text(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.casefold())


def _accepted_effect_answers(effect_slug: str) -> set[str]:
    base = {
        _normalized_text(effect_slug),
        _normalized_text(_effect_display_name(effect_slug)),
    }
    if effect_slug == "paralyze":
        base.add(_normalized_text("paralysis"))
    if effect_slug == "badly-poison":
        base.update({_normalized_text("toxic"), _normalized_text("toxic poison")})
    return {x for x in base if x}


def build_challenge(*, random_item_tries: int = 180) -> FlingForceChallenge | None:
    """Pick an item with either fling_power or fling_effect available."""
    for _ in range(random_item_tries):
        try:
            payload = _fetch_json(f"https://pokeapi.co/api/v2/item/{random.randint(1, 2208)}/")
        except Exception:
            continue
        item_slug = payload.get("name")
        if not isinstance(item_slug, str) or not item_slug:
            continue
        power_raw = payload.get("fling_power")
        try:
            power = int(power_raw) if power_raw is not None else None
        except (TypeError, ValueError):
            power = None
        effect_slug = (payload.get("fling_effect") or {}).get("name")
        if effect_slug is not None and not isinstance(effect_slug, str):
            effect_slug = None
        if power is None and effect_slug is None:
            continue
        return FlingForceChallenge(
            item_slug=item_slug,
            fling_power=power,
            fling_effect_slug=effect_slug,
        )
    return None


def clue_line(ch: FlingForceChallenge) -> str:
    if ch.fling_effect_slug is not None:
        return "Clue 1: This item's Fling interaction is status-oriented."
    return "Clue 1: This item's Fling interaction is damage-only."


def parse_guess(raw: str, ch: FlingForceChallenge) -> tuple[bool, str]:
    """
    Returns (is_correct, canonical_guess_key).
    canonical_guess_key is used for repeat detection.
    """
    s = raw.strip()
    if not s:
        return False, ""

    if s.isdigit():
        g = int(s)
        key = f"power:{g}"
        return (ch.fling_power is not None and g == ch.fling_power), key

    if ch.fling_effect_slug is None:
        # Text guesses are invalid when there is no fling effect.
        return False, ""

    t = _normalized_text(s)
    if not t:
        return False, ""
    ok = t in _accepted_effect_answers(ch.fling_effect_slug)
    return ok, f"effect:{t}"


def reveal_answer_line(ch: FlingForceChallenge) -> str:
    parts: list[str] = []
    if ch.fling_power is not None:
        parts.append(str(ch.fling_power))
    if ch.fling_effect_slug is not None:
        parts.append(_effect_display_name(ch.fling_effect_slug))
    if not parts:
        return "No valid Fling data available."
    if len(parts) == 1:
        return parts[0]
    return " or ".join(parts)
