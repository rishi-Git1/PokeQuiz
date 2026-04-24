from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name

STAT_LABELS = {
    "hp": "HP",
    "attack": "Attack",
    "defense": "Defense",
    "special-attack": "Special Attack",
    "special-defense": "Special Defense",
    "speed": "Speed",
}


def _pretty(slug: str) -> str:
    return slug.replace("-", " ").title()


def _capture_rate_band(rate: int | None) -> str | None:
    if rate is None:
        return None
    if rate < 50:
        return "very-low"
    if rate < 100:
        return "low"
    if rate < 150:
        return "medium"
    return "high"


@dataclass(frozen=True, slots=True)
class EVProfile:
    ev_yields: tuple[tuple[str, int], ...]
    generation: int | None
    types: tuple[str, ...]
    evolution_stage: str
    color: str | None
    egg_groups: tuple[str, ...]
    primary_ability: str | None
    capture_rate_band: str | None


@lru_cache(maxsize=4096)
def _pokemon_payload(name: str) -> dict:
    return _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{normalize_name(name)}")


@lru_cache(maxsize=4096)
def _species_payload(name: str) -> dict:
    return _fetch_json(f"https://pokeapi.co/api/v2/pokemon-species/{normalize_name(name)}")


def _generation_number(gen_name: str | None) -> int | None:
    lookup = {
        "generation-i": 1,
        "generation-ii": 2,
        "generation-iii": 3,
        "generation-iv": 4,
        "generation-v": 5,
        "generation-vi": 6,
        "generation-vii": 7,
        "generation-viii": 8,
        "generation-ix": 9,
    }
    return lookup.get(gen_name or "")


@lru_cache(maxsize=4096)
def _evolution_stage_for_name(name: str) -> str:
    species = _species_payload(name)
    species_name = str(species.get("name", normalize_name(name)))
    chain_url = str(species.get("evolution_chain", {}).get("url", "") or "")
    if not chain_url:
        return "Unknown"
    chain = _fetch_json(chain_url)
    root = chain.get("chain", {})

    def walk(node: dict, depth: int) -> tuple[int, bool] | None:
        node_name = str(node.get("species", {}).get("name", ""))
        children = node.get("evolves_to", [])
        if node_name == species_name:
            return depth, bool(children)
        for child in children:
            found = walk(child, depth + 1)
            if found is not None:
                return found
        return None

    found = walk(root, 0)
    if found is None:
        return "Unknown"
    depth, has_children = found
    if depth == 0 and has_children:
        return "Base stage"
    if depth == 0 and not has_children:
        return "Single-stage"
    if depth > 0 and has_children:
        return "Middle stage"
    return "Final stage"


@lru_cache(maxsize=4096)
def profile_for_name(name: str) -> EVProfile:
    mon = _pokemon_payload(name)
    species = _species_payload(name)

    yields: list[tuple[str, int]] = []
    for s in mon.get("stats", []):
        stat_name = s.get("stat", {}).get("name")
        effort = int(s.get("effort", 0) or 0)
        if stat_name and effort > 0:
            yields.append((str(stat_name), effort))
    ev_yields = tuple(sorted(yields, key=lambda x: x[0]))

    types = tuple(sorted(_pretty(t.get("type", {}).get("name")) for t in mon.get("types", []) if t.get("type", {}).get("name")))
    gen = _generation_number(species.get("generation", {}).get("name"))
    color = species.get("color", {}).get("name")
    egg_groups = tuple(sorted(_pretty(e.get("name")) for e in species.get("egg_groups", []) if e.get("name")))

    primary_ability = None
    for a in mon.get("abilities", []):
        if a.get("is_hidden"):
            continue
        if int(a.get("slot", 0) or 0) == 1:
            nm = a.get("ability", {}).get("name")
            if nm:
                primary_ability = _pretty(str(nm))
                break

    capture_rate = species.get("capture_rate")
    cap_band = _capture_rate_band(int(capture_rate) if capture_rate is not None else None)
    evo_stage = _evolution_stage_for_name(name)

    return EVProfile(
        ev_yields=ev_yields,
        generation=gen,
        types=types,
        evolution_stage=evo_stage,
        color=_pretty(str(color)) if color else None,
        egg_groups=egg_groups,
        primary_ability=primary_ability,
        capture_rate_band=cap_band,
    )


def ev_yield_line(profile: EVProfile) -> str:
    if not profile.ev_yields:
        return "EV Yield: None (0 EV)"
    parts = [f"+{val} {STAT_LABELS.get(stat, _pretty(stat))}" for stat, val in profile.ev_yields]
    return "EV Yield: " + ", ".join(parts)

