"""Stamina Hangman: guess a move name letter-by-letter with limited lives."""

from __future__ import annotations

import random
from dataclasses import dataclass

from pokequiz.data import _fetch_json


@dataclass(frozen=True, slots=True)
class StaminaHangmanChallenge:
    move_slug: str
    move_display: str
    move_type: str


def _pretty(slug: str) -> str:
    return slug.replace("-", " ").title()


def build_challenge(*, max_attempts: int = 140) -> StaminaHangmanChallenge | None:
    """Pick a move with a non-empty name and type."""
    for _ in range(max_attempts):
        try:
            payload = _fetch_json(f"https://pokeapi.co/api/v2/move/{random.randint(1, 1000)}/")
        except Exception:
            continue
        slug = payload.get("name")
        type_slug = (payload.get("type") or {}).get("name")
        if not isinstance(slug, str) or not slug:
            continue
        if not isinstance(type_slug, str) or not type_slug:
            continue
        display = _pretty(slug)
        if any(ch.isdigit() for ch in display):
            continue
        if len([c for c in display if c.isalpha()]) < 4:
            continue
        return StaminaHangmanChallenge(
            move_slug=slug,
            move_display=display,
            move_type=_pretty(type_slug),
        )
    return None
