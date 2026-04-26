"""Pokemon Tetris helpers."""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json

TYPE_ORDER: tuple[str, ...] = (
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
class InteractionResult:
    attacker_kept: bool
    defender_after: str | None
    note: str


@lru_cache(maxsize=1)
def type_effectiveness() -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {a: {d: 1.0 for d in TYPE_ORDER} for a in TYPE_ORDER}
    for t in TYPE_ORDER:
        payload = _fetch_json(f"https://pokeapi.co/api/v2/type/{t}")
        rel = payload.get("damage_relations") or {}
        for row in rel.get("double_damage_to") or []:
            d = row.get("name")
            if isinstance(d, str) and d in out[t]:
                out[t][d] *= 2.0
        for row in rel.get("half_damage_to") or []:
            d = row.get("name")
            if isinstance(d, str) and d in out[t]:
                out[t][d] *= 0.5
        for row in rel.get("no_damage_to") or []:
            d = row.get("name")
            if isinstance(d, str) and d in out[t]:
                out[t][d] = 0.0
    return out


def spawn_type() -> str:
    return random.choice(TYPE_ORDER)


def resolve_contact(attacker: str, defender: str) -> InteractionResult:
    eff = type_effectiveness()[attacker][defender]
    # Explicitly preserve user examples first.
    if attacker == "water" and defender == "fire":
        return InteractionResult(attacker_kept=False, defender_after=None, note="Super effective clash: both disappear!")
    if attacker == "grass" and defender == "water":
        return InteractionResult(attacker_kept=False, defender_after="grass", note="Absorb: Water converts into Grass.")
    if attacker == "dragon" and defender == "fairy":
        return InteractionResult(attacker_kept=False, defender_after="fairy", note="Dragon is nullified by Fairy.")

    if eff == 0:
        return InteractionResult(attacker_kept=False, defender_after=defender, note="No effect: falling block is destroyed.")
    if eff > 1:
        return InteractionResult(attacker_kept=False, defender_after=attacker, note="Super effective: defender converts to attacker type.")
    if eff < 1:
        return InteractionResult(attacker_kept=False, defender_after=defender, note="Not very effective: falling block is destroyed.")
    return InteractionResult(attacker_kept=True, defender_after=defender, note="Neutral contact: block stacks.")

