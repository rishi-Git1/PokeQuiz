from __future__ import annotations

from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name


def _pretty(slug: str) -> str:
    return slug.replace("-", " ").title()


@lru_cache(maxsize=4096)
def held_item_profile_for_name(name: str) -> tuple[tuple[str, int], ...]:
    """
    Return sorted (item_name, rarity_percent) profile from pokemon/{name}.held_items.
    Percent is from version_details.rarity (e.g. 50, 5, 1).
    """
    payload = _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{normalize_name(name)}")
    rates: dict[str, int] = {}
    for item in payload.get("held_items", []):
        item_name = item.get("item", {}).get("name")
        if not item_name:
            continue
        max_rarity = 0
        for vd in item.get("version_details", []):
            r = int(vd.get("rarity", 0) or 0)
            if r > max_rarity:
                max_rarity = r
        if max_rarity > 0:
            rates[str(item_name)] = max_rarity
    return tuple(sorted(rates.items(), key=lambda x: (x[1], x[0]), reverse=True))


def profile_clues(profile: tuple[tuple[str, int], ...]) -> list[str]:
    return [f"{rate}% chance to hold: {_pretty(item)}" for item, rate in profile]

