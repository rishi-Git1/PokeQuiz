"""Environment Map: guess Nature Power's resulting move by generation + area."""

from __future__ import annotations

import random
from dataclasses import dataclass

from pokequiz.games.move_match import display_move_name


@dataclass(frozen=True, slots=True)
class EnvironmentMapChallenge:
    generation_label: str
    area_label: str
    move_slug: str


# Compact curated table for Nature Power outcomes across common environments.
# Note: this is a handcrafted lookup because PokéAPI does not expose a direct mapping field.
_NATURE_POWER_MAP: tuple[EnvironmentMapChallenge, ...] = (
    EnvironmentMapChallenge("Gen 3+", "Building / Link Battle", "tri-attack"),
    EnvironmentMapChallenge("Gen 4+", "Cave", "power-gem"),
    EnvironmentMapChallenge("Gen 6+", "Electric Terrain", "thunderbolt"),
    EnvironmentMapChallenge("Gen 6+", "Grassy Terrain", "energy-ball"),
    EnvironmentMapChallenge("Gen 6+", "Misty Terrain", "moonblast"),
    EnvironmentMapChallenge("Gen 6+", "Psychic Terrain", "psychic"),
)


def build_challenge() -> EnvironmentMapChallenge:
    return random.choice(_NATURE_POWER_MAP)


def parse_guess(move_slug_or_none: str | None, ch: EnvironmentMapChallenge, raw: str) -> tuple[bool, str, str | None]:
    """
    Returns (is_correct, canonical_key, error_message).
    Empty key means invalid guess format/name and should not consume a turn.
    """
    if move_slug_or_none is None:
        return False, "", f'That does not match a known move: "{raw}".'
    key = move_slug_or_none
    ok = key == ch.move_slug
    return ok, key, None


def reveal_answer_line(ch: EnvironmentMapChallenge) -> str:
    return display_move_name(ch.move_slug)
