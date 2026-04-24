from __future__ import annotations

import random
from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name
from pokequiz.models import Pokemon

TYPE_NAMES = (
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


def _pretty(slug: str) -> str:
    return slug.replace("-", " ").title()


@lru_cache(maxsize=128)
def moves_for_type(type_name: str) -> tuple[str, ...]:
    payload = _fetch_json(f"https://pokeapi.co/api/v2/type/{type_name}")
    moves = [m.get("name") for m in payload.get("moves", []) if m.get("name")]
    return tuple(sorted(str(m) for m in moves))


@lru_cache(maxsize=4096)
def level_for_move_by_levelup(mon_name: str, move_name: str) -> int | None:
    payload = _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{normalize_name(mon_name)}")
    best: int | None = None
    for item in payload.get("moves", []):
        if item.get("move", {}).get("name") != move_name:
            continue
        for d in item.get("version_group_details", []):
            if d.get("move_learn_method", {}).get("name") != "level-up":
                continue
            lvl = int(d.get("level_learned_at", 0) or 0)
            if best is None or lvl < best:
                best = lvl
    return best


def build_challenge(pool: list[Pokemon], option_count: int = 3) -> tuple[str, list[tuple[Pokemon, int]]]:
    """
    Optimization path requested:
    1) random type
    2) random move from that type
    3) N pokemon of that type that learn it naturally (level-up)
    """
    if option_count < 2:
        raise ValueError("Level Race needs at least 2 options.")

    type_list = list(TYPE_NAMES)
    random.shuffle(type_list)

    for t in type_list:
        typed_pool = [p for p in pool if t in p.types]
        if len(typed_pool) < option_count:
            continue

        try:
            moves = list(moves_for_type(t))
        except Exception:
            continue
        random.shuffle(moves)

        # Per request, pick random mons iteratively and check one-by-one.
        for move in moves[:80]:
            candidates: list[tuple[Pokemon, int]] = []
            tried: set[str] = set()
            max_attempts = min(len(typed_pool) * 2, 200)
            attempts = 0
            while len(candidates) < option_count and attempts < max_attempts and len(tried) < len(typed_pool):
                mon = random.choice(typed_pool)
                if mon.name in tried:
                    attempts += 1
                    continue
                tried.add(mon.name)
                try:
                    lvl = level_for_move_by_levelup(mon.name, move)
                except Exception:
                    attempts += 1
                    continue
                if lvl is not None:
                    candidates.append((mon, lvl))
                attempts += 1

            if len(candidates) >= option_count:
                return move, candidates[:option_count]

    raise ValueError("Could not build a Level Race challenge from current filters.")


def display_move_name(move_slug: str) -> str:
    return _pretty(move_slug)

