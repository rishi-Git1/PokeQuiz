from __future__ import annotations

import random
from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name
from pokequiz.models import Pokemon

LEGAL_LEARN_METHODS = {"level-up", "machine", "egg"}


def display_move_name(move_slug: str) -> str:
    return move_slug.replace("-", " ").title()


@lru_cache(maxsize=4096)
def legal_moves_for_name(name: str) -> frozenset[str]:
    """Moves learnable by level-up, TM/machine, or breeding/egg."""
    payload = _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{normalize_name(name)}")
    legal: set[str] = set()
    for item in payload.get("moves", []):
        move_name = item.get("move", {}).get("name")
        if not move_name:
            continue
        details = item.get("version_group_details", [])
        if any(d.get("move_learn_method", {}).get("name") in LEGAL_LEARN_METHODS for d in details):
            legal.add(str(move_name))
    return frozenset(legal)


def build_challenge(pool: list[Pokemon]) -> tuple[Pokemon, list[str]]:
    """Pick a target with at least 4 legal moves and sample 4 of them."""
    candidates = pool[:]
    random.shuffle(candidates)
    for mon in candidates:
        try:
            moves = list(legal_moves_for_name(mon.name))
        except Exception:
            continue
        if len(moves) >= 4:
            return mon, random.sample(moves, k=4)
    raise ValueError("Could not find a Pokémon with enough legal moves for a challenge.")


def guess_satisfies_moves(guess_name: str, required_moves: list[str]) -> bool:
    learned = legal_moves_for_name(guess_name)
    return set(required_moves).issubset(learned)

