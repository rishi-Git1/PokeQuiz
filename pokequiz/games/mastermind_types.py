"""Mastermind: guess a hidden two-slot type combination."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Iterable


TYPE_NAMES: tuple[str, ...] = (
    "normal",
    "fire",
    "water",
    "electric",
    "grass",
    "ice",
    "fighting",
    "poison",
    "ground",
    "flying",
    "psychic",
    "bug",
    "rock",
    "ghost",
    "dragon",
    "dark",
    "steel",
    "fairy",
)


@dataclass(frozen=True, slots=True)
class MastermindChallenge:
    secret: tuple[str, str]


def display_type_name(type_slug: str) -> str:
    return type_slug.replace("-", " ").title()


def build_challenge(*, mono_chance: float = 0.22) -> MastermindChallenge:
    t1 = random.choice(TYPE_NAMES)
    if random.random() < mono_chance:
        t2 = t1
    else:
        t2 = random.choice([t for t in TYPE_NAMES if t != t1])
    return MastermindChallenge(secret=(t1, t2))


def parse_guess(raw: str) -> tuple[tuple[str, str] | None, str | None]:
    """
    Parse "type1 type2" or "type1/type2".
    Returns (guess_tuple_or_none, error_message_or_none).
    """
    line = (raw or "").strip().casefold()
    if not line:
        return None, "Guess cannot be blank."
    parts = [p for p in re.split(r"[\s,;/|]+", line) if p]
    if len(parts) != 2:
        return None, 'Enter exactly two types (example: "water ground").'
    a, b = parts
    if a not in TYPE_NAMES or b not in TYPE_NAMES:
        bad = [x for x in (a, b) if x not in TYPE_NAMES]
        return None, f'Unknown type(s): {", ".join(bad)}.'
    if a == b:
        return None, "Duplicate types are not allowed in guesses."
    return (a, b), None


def feedback_colors(secret: tuple[str, str], guess: tuple[str, str]) -> tuple[str, str]:
    """
    Two-color feedback only, prioritized Green > Yellow > Gray.
    """
    greens = 0
    secret_left: list[str] = []
    guess_left: list[str] = []
    for s, g in zip(secret, guess):
        if s == g:
            greens += 1
        else:
            secret_left.append(s)
            guess_left.append(g)

    yellows = 0
    for g in list(guess_left):
        if g in secret_left:
            yellows += 1
            secret_left.remove(g)

    grays = 2 - greens - yellows
    out: list[str] = []
    out.extend(["Green"] * greens)
    out.extend(["Yellow"] * yellows)
    out.extend(["Gray"] * grays)
    return out[0], out[1]


def format_guess(guess: Iterable[str]) -> str:
    a, b = tuple(guess)
    return f"{display_type_name(a)} / {display_type_name(b)}"
