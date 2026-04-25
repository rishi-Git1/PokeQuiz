"""Catch & Hatch: identify capture rate vs base happiness."""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name
from pokequiz.models import Pokemon


@dataclass(frozen=True, slots=True)
class CatchHatchChallenge:
    pokemon_name: str
    shown_values: tuple[int, int]
    capture_rate: int
    base_happiness: int


@lru_cache(maxsize=4096)
def _species_capture_happiness(name: str) -> tuple[int, int] | None:
    try:
        payload = _fetch_json(f"https://pokeapi.co/api/v2/pokemon-species/{normalize_name(name)}")
    except Exception:
        return None
    cap = payload.get("capture_rate")
    happy = payload.get("base_happiness")
    try:
        capture = int(cap)
        happiness = int(happy)
    except (TypeError, ValueError):
        return None
    return capture, happiness


def build_challenge(pool: list[Pokemon], *, max_attempts: int = 140) -> CatchHatchChallenge | None:
    if not pool:
        return None
    for _ in range(max_attempts):
        mon = random.choice(pool)
        vals = _species_capture_happiness(mon.name)
        if vals is None:
            continue
        capture_rate, base_happiness = vals
        if capture_rate == base_happiness:
            continue
        shown = [capture_rate, base_happiness]
        random.shuffle(shown)
        return CatchHatchChallenge(
            pokemon_name=mon.name,
            shown_values=(shown[0], shown[1]),
            capture_rate=capture_rate,
            base_happiness=base_happiness,
        )
    return None
