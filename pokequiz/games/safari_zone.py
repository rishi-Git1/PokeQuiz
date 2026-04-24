from __future__ import annotations

from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name


def _pretty(slug: str) -> str:
    return slug.replace("-", " ").title()


@lru_cache(maxsize=4096)
def encounter_clues_for_name(name: str) -> tuple[str, ...]:
    """
    Return unique location+method clues from pokemon/{name}/encounters.
    Example: 'Kanto Route 2 Area (Walking)'
    """
    payload = _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{normalize_name(name)}/encounters")
    seen: set[str] = set()
    clues: list[str] = []
    for area in payload:
        area_name = str(area.get("location_area", {}).get("name", "") or "")
        if not area_name:
            continue
        for vd in area.get("version_details", []):
            for ed in vd.get("encounter_details", []):
                method = str(ed.get("method", {}).get("name", "") or "")
                if not method:
                    continue
                clue = f"{_pretty(area_name)} ({_pretty(method)})"
                if clue in seen:
                    continue
                seen.add(clue)
                clues.append(clue)
    return tuple(sorted(clues))

