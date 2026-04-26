"""Legendary Yahtzee helpers."""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json


@dataclass(frozen=True, slots=True)
class RollMove:
    slug: str
    type_slug: str
    damage_class: str
    power: int | None


CATEGORIES: tuple[str, ...] = (
    "full_house",
    "large_straight",
    "four_kind",
    "legendary",
)

CATEGORY_LABELS: dict[str, str] = {
    "full_house": "Full House (types 3+2)",
    "large_straight": "Large Straight (power +10 steps)",
    "four_kind": "Four of a Kind (damage class)",
    "legendary": "Legendary (all same type)",
}


def display_move_name(slug: str) -> str:
    return slug.replace("-", " ").title()


def power_value(m: RollMove) -> int:
    return int(m.power) if m.power is not None else 0


@lru_cache(maxsize=4096)
def _move_by_id(move_id: int) -> RollMove | None:
    try:
        payload = _fetch_json(f"https://pokeapi.co/api/v2/move/{move_id}")
    except Exception:
        return None
    slug = payload.get("name")
    t = (payload.get("type") or {}).get("name")
    dc = (payload.get("damage_class") or {}).get("name")
    raw_power = payload.get("power")
    if not isinstance(slug, str) or not slug:
        return None
    if not isinstance(t, str) or not t:
        return None
    if not isinstance(dc, str) or not dc:
        return None
    try:
        p = int(raw_power) if raw_power is not None else None
    except (TypeError, ValueError):
        p = None
    return RollMove(slug=slug, type_slug=t, damage_class=dc, power=p)


def random_roll_move() -> RollMove:
    while True:
        m = _move_by_id(random.randint(1, 1000))
        if m is not None:
            return m


def score_category(hand: list[RollMove], cat: str) -> int:
    if cat == "legendary":
        return 50 if len({m.type_slug for m in hand}) == 1 else 0
    if cat == "four_kind":
        counts: dict[str, int] = {}
        for m in hand:
            counts[m.damage_class] = counts.get(m.damage_class, 0) + 1
        if max(counts.values(), default=0) >= 4:
            return sum(power_value(m) for m in hand)
        return 0
    if cat == "full_house":
        counts: dict[str, int] = {}
        for m in hand:
            counts[m.type_slug] = counts.get(m.type_slug, 0) + 1
        vals = sorted(counts.values())
        return 25 if vals == [2, 3] else 0
    if cat == "large_straight":
        powers = [m.power for m in hand]
        if any(p is None for p in powers):
            return 0
        vals = sorted(int(p) for p in powers if p is not None)
        if len(set(vals)) != 5:
            return 0
        # Consecutive in 10-point steps.
        for i in range(4):
            if vals[i + 1] - vals[i] != 10:
                return 0
        return 40
    return 0


def best_category_for_hand(hand: list[RollMove], available: set[str]) -> tuple[str, int]:
    best_cat = next(iter(available))
    best_score = -1
    for cat in available:
        s = score_category(hand, cat)
        if s > best_score:
            best_score = s
            best_cat = cat
    return best_cat, best_score


def cpu_best_keep_mask(
    hand: list[RollMove], available: set[str], *, samples: int = 24
) -> int:
    """
    Fast one-step expected-value keep-mask chooser.
    Bit i = keep die i.
    """
    best_mask = 0
    best_ev = -1.0
    for mask in range(32):
        ev_total = 0.0
        for _ in range(samples):
            trial = hand.copy()
            for i in range(5):
                if (mask >> i) & 1:
                    continue
                trial[i] = random_roll_move()
            _, score = best_category_for_hand(trial, available)
            ev_total += score
        ev = ev_total / samples
        if ev > best_ev:
            best_ev = ev
            best_mask = mask
    return best_mask
