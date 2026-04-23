from __future__ import annotations

from dataclasses import dataclass

from pokequiz.models import Pokemon

STAT_NAMES = ["hp", "attack", "defense", "special_attack", "special_defense", "speed"]
STAT_LABELS = {
    "hp": "HP",
    "attack": "Attack",
    "defense": "Defense",
    "special_attack": "Special Attack",
    "special_defense": "Special Defense",
    "speed": "Speed",
}


@dataclass(slots=True)
class StatleTurnResult:
    stat: str
    value: int


def remaining_stats(picked: list[str]) -> list[str]:
    picked_set = set(picked)
    return [s for s in STAT_NAMES if s not in picked_set]


def resolve_turn(mon: Pokemon, chosen_stat: str) -> StatleTurnResult:
    return StatleTurnResult(stat=chosen_stat, value=getattr(mon, chosen_stat))


def total_score(results: list[StatleTurnResult]) -> int:
    return sum(r.value for r in results)
