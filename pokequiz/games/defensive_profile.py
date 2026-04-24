from __future__ import annotations

from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name

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
def defensive_types_for_name(name: str) -> tuple[str, ...]:
    payload = _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{normalize_name(name)}")
    found = [t.get("type", {}).get("name") for t in payload.get("types", [])]
    cleaned = [str(t) for t in found if t]
    # Canonical order so matching is stable across forms/data sources.
    return tuple(sorted(cleaned))


@lru_cache(maxsize=64)
def _incoming_multiplier_vs_single(def_type: str, atk_type: str) -> float:
    payload = _fetch_json(f"https://pokeapi.co/api/v2/type/{def_type}")
    rel = payload.get("damage_relations", {})
    double_from = {x["name"] for x in rel.get("double_damage_from", [])}
    half_from = {x["name"] for x in rel.get("half_damage_from", [])}
    none_from = {x["name"] for x in rel.get("no_damage_from", [])}
    if atk_type in none_from:
        return 0.0
    mult = 1.0
    if atk_type in double_from:
        mult *= 2.0
    if atk_type in half_from:
        mult *= 0.5
    return mult


def defensive_multiplier_map(def_types: tuple[str, ...]) -> dict[str, float]:
    out: dict[str, float] = {}
    for atk in TYPE_NAMES:
        mult = 1.0
        for dt in def_types:
            mult *= _incoming_multiplier_vs_single(dt, atk)
        out[atk] = mult
    return out


def grouped_multiplier_clues(def_types: tuple[str, ...]) -> list[str]:
    mults = defensive_multiplier_map(def_types)
    groups: dict[float, list[str]] = {0.0: [], 4.0: [], 2.0: [], 0.5: [], 0.25: []}
    for atk, mult in mults.items():
        if mult in groups:
            groups[mult].append(_pretty(atk))

    labels = {
        0.0: "Immune to (0x)",
        4.0: "Weak to (4x)",
        2.0: "Weak to (2x)",
        0.5: "Resists (0.5x)",
        0.25: "Resists (0.25x)",
    }
    order = [0.0, 4.0, 2.0, 0.5, 0.25]
    clues: list[str] = []
    for m in order:
        vals = sorted(groups[m])
        if vals:
            clues.append(f"{labels[m]}: {', '.join(vals)}")
    return clues

