"""War mode helpers: stat rounds over fixed Pokémon card hands."""

from __future__ import annotations

import random
from dataclasses import dataclass

from pokequiz.models import Pokemon


STAT_FIELDS: tuple[tuple[str, str], ...] = (
    ("hp", "HP"),
    ("attack", "Attack"),
    ("defense", "Defense"),
    ("special_attack", "Special Attack"),
    ("special_defense", "Special Defense"),
    ("speed", "Speed"),
)


@dataclass(frozen=True, slots=True)
class WarRoundStat:
    field: str
    label: str


def stat_value(mon: Pokemon, stat_field: str) -> int:
    return int(getattr(mon, stat_field))


def random_stat() -> WarRoundStat:
    field, label = random.choice(STAT_FIELDS)
    return WarRoundStat(field=field, label=label)


def choose_cpu_card(cpu_team: list[Pokemon], user_team: list[Pokemon], stat_field: str) -> Pokemon | None:
    """
    Choose CPU card that beats user's rounded-up median for the stat.
    Picks the smallest value that still beats the threshold.
    """
    user_vals = sorted(stat_value(m, stat_field) for m in user_team)
    if not user_vals:
        return None
    median_up = user_vals[len(user_vals) // 2]
    candidates = [c for c in cpu_team if stat_value(c, stat_field) > median_up]
    if candidates:
        candidates.sort(key=lambda m: (stat_value(m, stat_field), m.dex_number, m.name))
        return candidates[0]
    # If no card beats the median, play the highest remaining stat card.
    best = max(cpu_team, key=lambda m: (stat_value(m, stat_field), -m.dex_number))
    return best
