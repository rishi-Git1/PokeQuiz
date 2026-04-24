from __future__ import annotations

from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name


def display_move_name(slug: str) -> str:
    return slug.replace("-", " ").title()


@lru_cache(maxsize=4096)
def level_up_moves_for_name(name: str) -> tuple[tuple[int, str], ...]:
    """Return sorted (level, move_name) tuples from level-up learnset."""
    payload = _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{normalize_name(name)}")
    move_levels: dict[str, int] = {}
    for item in payload.get("moves", []):
        move_name = item.get("move", {}).get("name")
        if not move_name:
            continue
        for d in item.get("version_group_details", []):
            method = d.get("move_learn_method", {}).get("name")
            if method != "level-up":
                continue
            lvl = int(d.get("level_learned_at", 0) or 0)
            current = move_levels.get(str(move_name))
            if current is None or lvl < current:
                move_levels[str(move_name)] = lvl
    return tuple(sorted(((lvl, move) for move, lvl in move_levels.items()), key=lambda x: (x[0], x[1])))

