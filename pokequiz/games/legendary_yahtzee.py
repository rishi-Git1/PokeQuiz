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
    "three_kind",
    "full_house",
    "small_straight",
    "large_straight",
    "four_kind",
    "legendary",
    "chance",
)

CATEGORY_LABELS: dict[str, str] = {
    "three_kind": "Three of a Kind (type)",
    "full_house": "Full House (types 3+2)",
    "small_straight": "Small Straight (4 consecutive power steps)",
    "large_straight": "Large Straight (power +10 steps)",
    "four_kind": "Four of a Kind (damage class)",
    "legendary": "Legendary (all same type)",
    "chance": "Chance (sum of all powers)",
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
    if cat == "chance":
        return sum(power_value(m) for m in hand)
    if cat == "four_kind":
        counts: dict[str, int] = {}
        for m in hand:
            counts[m.damage_class] = counts.get(m.damage_class, 0) + 1
        if max(counts.values(), default=0) >= 4:
            return sum(power_value(m) for m in hand)
        return 0
    if cat == "three_kind":
        counts: dict[str, int] = {}
        for m in hand:
            counts[m.type_slug] = counts.get(m.type_slug, 0) + 1
        if max(counts.values(), default=0) >= 3:
            return sum(power_value(m) for m in hand)
        return 0
    if cat == "full_house":
        counts: dict[str, int] = {}
        for m in hand:
            counts[m.type_slug] = counts.get(m.type_slug, 0) + 1
        vals = sorted(counts.values())
        return 25 if vals == [2, 3] else 0
    if cat == "small_straight":
        powers = [m.power for m in hand]
        if any(p is None for p in powers):
            return 0
        vals = sorted({int(p) for p in powers if p is not None})
        run = 1
        best = 1
        for i in range(1, len(vals)):
            if vals[i] - vals[i - 1] == 10:
                run += 1
                if run > best:
                    best = run
            else:
                run = 1
        return 30 if best >= 4 else 0
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
    hand: list[RollMove], available: set[str]
) -> int:
    """
    Fast rule-based keep-mask chooser.
    Bit i = keep die i.
    """
    # Priority 1: lock in or chase Four of a Kind by damage class.
    class_counts: dict[str, int] = {}
    for m in hand:
        class_counts[m.damage_class] = class_counts.get(m.damage_class, 0) + 1
    best_class = max(class_counts, key=class_counts.get)
    best_class_count = class_counts[best_class]
    if "four_kind" in available and best_class_count >= 3:
        mask = 0
        for i, m in enumerate(hand):
            if m.damage_class == best_class:
                mask |= 1 << i
        return mask

    # Priority 2: chase Legendary / Three of a Kind by type.
    type_counts: dict[str, int] = {}
    for m in hand:
        type_counts[m.type_slug] = type_counts.get(m.type_slug, 0) + 1
    best_type = max(type_counts, key=type_counts.get)
    best_type_count = type_counts[best_type]
    if ("legendary" in available or "three_kind" in available) and best_type_count >= 3:
        mask = 0
        for i, m in enumerate(hand):
            if m.type_slug == best_type:
                mask |= 1 << i
        return mask

    # Priority 3: chase straights by keeping the longest +10 run.
    if "large_straight" in available or "small_straight" in available:
        idx_by_power: dict[int, list[int]] = {}
        for i, m in enumerate(hand):
            if m.power is None:
                continue
            idx_by_power.setdefault(int(m.power), []).append(i)
        vals = sorted(idx_by_power)
        best_run_start = 0
        best_run_len = 0
        run_start = 0
        run_len = 1
        for i in range(1, len(vals)):
            if vals[i] - vals[i - 1] == 10:
                run_len += 1
            else:
                if run_len > best_run_len:
                    best_run_len = run_len
                    best_run_start = run_start
                run_start = i
                run_len = 1
        if vals and run_len > best_run_len:
            best_run_len = run_len
            best_run_start = run_start
        if best_run_len >= 3:
            keep_vals = set(vals[best_run_start : best_run_start + best_run_len])
            mask = 0
            used_power: set[int] = set()
            for i, m in enumerate(hand):
                p = m.power
                if p is None:
                    continue
                pv = int(p)
                if pv in keep_vals and pv not in used_power:
                    mask |= 1 << i
                    used_power.add(pv)
            if mask:
                return mask

    # Priority 4: keep highest-power two for Chance fallback.
    ranked = sorted(enumerate(hand), key=lambda x: power_value(x[1]), reverse=True)
    mask = 0
    for i, _m in ranked[:2]:
        mask |= 1 << i
    return mask
