"""DexIt: higher/lower on National Pokédex numbers (in-memory dex_number), with chained rounds."""

from __future__ import annotations

import random

from pokequiz.models import Pokemon


def pick_target_and_guess(pool: list[Pokemon], *, max_attempts: int = 200) -> tuple[Pokemon, Pokemon] | None:
    """Two distinct species with different National Dex numbers (start of a chain or after a reset)."""
    if len(pool) < 2:
        return None
    for _ in range(max_attempts):
        a, b = random.sample(pool, 2)
        if a.dex_number != b.dex_number:
            return (a, b)
    return None


def pick_next_guess(anchor: Pokemon, pool: list[Pokemon]) -> Pokemon | None:
    """A new species to compare: not the anchor, and a different National Dex #."""
    candidates = [p for p in pool if p.name != anchor.name and p.dex_number != anchor.dex_number]
    if not candidates:
        return None
    return random.choice(candidates)


def parse_higher_lower(raw: str) -> bool | None:
    """True = user says Guess is higher than Target, False = lower, None = not understood."""
    t = raw.strip().casefold()
    if not t:
        return None
    if t in {
        "h",
        "hi",
        "high",
        "higher",
        "up",
        "+",
        "more",
        "greater",
    }:
        return True
    if t in {
        "l",
        "lo",
        "low",
        "lower",
        "down",
        "-",
        "less",
    }:
        return False
    return None


def is_correct_guess(user_says_higher: bool, target: Pokemon, guess: Pokemon) -> bool:
    """True if the user’s higher/lower call matches the actual order of National Dex numbers."""
    truth_higher = guess.dex_number > target.dex_number
    return user_says_higher == truth_higher
