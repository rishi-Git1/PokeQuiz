from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations

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


def optimal_statle_assignment(round_mons: list[Pokemon]) -> tuple[int, list[str]]:
    """Best total if each of the six stats is used exactly once across these six rounds (brute-force over 6! orders)."""
    n = len(round_mons)
    if n != len(STAT_NAMES):
        raise ValueError(f"Expected {len(STAT_NAMES)} rounds, got {n}")

    best_total = -1
    best_order: tuple[str, ...] | None = None
    for order in permutations(STAT_NAMES):
        total = sum(getattr(round_mons[i], order[i]) for i in range(n))
        if total > best_total or (total == best_total and best_order is not None and order < best_order):
            best_total = total
            best_order = order

    assert best_order is not None
    return best_total, list(best_order)


def format_optimal_statle_summary(
    round_mons: list[Pokemon],
    plan_stats: list[str],
    optimal_total: int,
    *,
    your_total: int,
) -> str:
    lines: list[str] = []
    lines.append(f"Best possible total with this run's six Pokémon: {optimal_total}")
    if your_total >= optimal_total:
        lines.append("You matched the optimum.")
    else:
        lines.append(f"Your total was {your_total} (room to gain {optimal_total - your_total}).")

    lines.append("\nOne optimal way to assign stats to rounds:")
    for i, mon in enumerate(round_mons):
        st = plan_stats[i]
        val = getattr(mon, st)
        lines.append(f"  Round {i + 1} - {mon.name}: {STAT_LABELS[st]} = {val}")
    lines.append(f"  (sums to {optimal_total})")
    return "\n".join(lines)
