from __future__ import annotations

import random
from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name
from pokequiz.games.level_ladder import level_up_moves_for_name
from pokequiz.models import Pokemon


def _pretty(slug: str) -> str:
    return slug.replace("-", " ").title()


@lru_cache(maxsize=4096)
def move_info(move_name: str) -> dict | None:
    try:
        payload = _fetch_json(f"https://pokeapi.co/api/v2/move/{normalize_name(move_name)}")
    except Exception:
        return None
    move_type = payload.get("type", {}).get("name")
    damage_class = payload.get("damage_class", {}).get("name")
    power = payload.get("power")
    return {
        "name": str(payload.get("name", normalize_name(move_name))),
        "type": _pretty(str(move_type)) if move_type else "Unknown",
        "damage_class": _pretty(str(damage_class)) if damage_class else "Unknown",
        "power": int(power) if power is not None else None,
    }


def build_challenge(pool: list[Pokemon]) -> tuple[Pokemon, list[tuple[int, str]], int, str]:
    candidates = pool[:]
    random.shuffle(candidates)
    for mon in candidates:
        moves = list(level_up_moves_for_name(mon.name))
        if len(moves) < 4:
            continue
        if len(moves) >= 5:
            missing_idx = random.randint(1, len(moves) - 2)
        else:
            missing_idx = random.randrange(len(moves))
        missing_move = moves[missing_idx][1]
        if move_info(missing_move) is None:
            continue
        return mon, moves, missing_idx, missing_move
    raise ValueError("Could not build a Missing Link challenge from current filters.")

