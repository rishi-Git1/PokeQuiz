"""Stat Scramble: identify a specific base stat from scrambled values."""

from __future__ import annotations

import random
from dataclasses import dataclass

from pokequiz.models import Pokemon


@dataclass(frozen=True, slots=True)
class StatScrambleChallenge:
    pokemon_name: str
    asked_stat: str
    scrambled_values: tuple[int, ...]
    answer_value: int


_STAT_FIELDS: tuple[tuple[str, str], ...] = (
    ("hp", "HP"),
    ("attack", "Attack"),
    ("defense", "Defense"),
    ("special_attack", "Special Attack"),
    ("special_defense", "Special Defense"),
    ("speed", "Speed"),
)


def build_challenge(pool: list[Pokemon]) -> StatScrambleChallenge | None:
    if not pool:
        return None
    mon = random.choice(pool)
    values = [
        mon.hp,
        mon.attack,
        mon.defense,
        mon.special_attack,
        mon.special_defense,
        mon.speed,
    ]
    random.shuffle(values)
    stat_field, stat_label = random.choice(_STAT_FIELDS)
    answer = int(getattr(mon, stat_field))
    return StatScrambleChallenge(
        pokemon_name=mon.name,
        asked_stat=stat_label,
        scrambled_values=tuple(values),
        answer_value=answer,
    )
