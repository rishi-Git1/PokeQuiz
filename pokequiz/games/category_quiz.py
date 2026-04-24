from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name


def _pretty(slug: str) -> str:
    return slug.replace("-", " ").title()


@dataclass(frozen=True, slots=True)
class CategoryProfile:
    category: str
    color: str | None
    egg_groups: tuple[str, ...]
    types: tuple[str, ...]
    generation: int | None
    primary_ability: str | None
    capture_rate_band: str | None
    weight_band: str | None
    height_band: str | None
    starts_with: str
    ends_with: str


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


def _weight_band(weight_hg: int | None) -> str | None:
    if weight_hg is None:
        return None
    if weight_hg < 1000:
        return "light"
    if weight_hg < 3000:
        return "midweight"
    return "heavy"


def _height_band(height_dm: int | None) -> str | None:
    if height_dm is None:
        return None
    if height_dm < 10:
        return "short"
    if height_dm < 20:
        return "medium"
    return "tall"


@lru_cache(maxsize=4096)
def profile_for_name(name: str) -> CategoryProfile:
    mon = _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{normalize_name(name)}")
    species = _fetch_json(f"https://pokeapi.co/api/v2/pokemon-species/{normalize_name(name)}")

    genus = None
    for g in species.get("genera", []):
        if g.get("language", {}).get("name") == "en":
            genus = g.get("genus")
            break
    if not genus:
        genus = "Unknown Pokémon"

    color = species.get("color", {}).get("name")
    egg_groups = tuple(sorted(_pretty(e["name"]) for e in species.get("egg_groups", []) if e.get("name")))
    types = tuple(sorted(_pretty(t.get("type", {}).get("name")) for t in mon.get("types", []) if t.get("type", {}).get("name")))

    gen_name = species.get("generation", {}).get("name")
    gen_map = {
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
    generation = gen_map.get(gen_name)

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
    capture_rate_band = _capture_rate_band(int(capture_rate) if capture_rate is not None else None)
    weight_band = _weight_band(int(mon.get("weight")) if mon.get("weight") is not None else None)
    height_band = _height_band(int(mon.get("height")) if mon.get("height") is not None else None)

    canon = normalize_name(name)
    return CategoryProfile(
        category=str(genus),
        color=_pretty(str(color)) if color else None,
        egg_groups=egg_groups,
        types=types,
        generation=generation,
        primary_ability=primary_ability,
        capture_rate_band=capture_rate_band,
        weight_band=weight_band,
        height_band=height_band,
        starts_with=canon[:1] if canon else "?",
        ends_with=canon[-1:] if canon else "?",
    )


def clue_lines(profile: CategoryProfile) -> list[str]:
    clues = [f'Category: "{profile.category}"']
    optional = []
    if profile.color:
        optional.append(f"Color: {profile.color}")
    if profile.egg_groups:
        optional.append(f"Egg Groups: {', '.join(profile.egg_groups)}")
    if profile.types:
        optional.append(f"Type(s): {', '.join(profile.types)}")
    if profile.generation is not None:
        optional.append(f"Generation: {profile.generation}")
    if profile.primary_ability:
        optional.append(f"Primary Ability: {profile.primary_ability}")
    if profile.capture_rate_band:
        optional.append(f"Capture Rate Band: {profile.capture_rate_band}")
    if profile.weight_band:
        optional.append(f"Weight Class: {profile.weight_band}")
    if profile.height_band:
        optional.append(f"Height Class: {profile.height_band}")
    optional.append(f"Name starts with: {profile.starts_with.upper()}")
    optional.append(f"Name ends with: {profile.ends_with.upper()}")
    random.shuffle(optional)
    # Show category + 3 more by default for readability.
    clues.extend(optional[:3])
    return clues


def matches_on_shown_clues(guess: CategoryProfile, shown: CategoryProfile, shown_fields: set[str]) -> bool:
    for field in shown_fields:
        if getattr(guess, field) != getattr(shown, field):
            return False
    return True

