from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name


@dataclass(frozen=True, slots=True)
class DaycareProfile:
    egg_groups: tuple[str, ...]
    hatch_counter: int
    gender_rate: int
    capture_rate: int


def _egg_group_label(slug: str) -> str:
    return slug.replace("-", " ").title()


def gender_rate_label(gender_rate: int) -> str:
    # PokeAPI scale: -1 genderless, 0..8 where female chance = value/8.
    if gender_rate == -1:
        return "Genderless"
    female = int(round((gender_rate / 8) * 100))
    male = 100 - female
    if male == 100:
        return "100% Male"
    if female == 100:
        return "100% Female"
    return f"{male}% Male / {female}% Female"


@lru_cache(maxsize=2048)
def daycare_profile_for_name(name: str) -> DaycareProfile:
    payload = _fetch_json(f"https://pokeapi.co/api/v2/pokemon-species/{normalize_name(name)}")
    egg_groups = tuple(sorted(_egg_group_label(g["name"]) for g in payload.get("egg_groups", [])))
    return DaycareProfile(
        egg_groups=egg_groups,
        hatch_counter=int(payload.get("hatch_counter", 0)),
        gender_rate=int(payload.get("gender_rate", -1)),
        capture_rate=int(payload.get("capture_rate", 0)),
    )

