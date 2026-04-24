from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name


@dataclass(frozen=True, slots=True)
class AbilityProfile:
    ability_1: str | None
    ability_2: str | None
    hidden_ability: str | None


def display_ability_name(slug: str) -> str:
    return slug.replace("-", " ").title()


@lru_cache(maxsize=4096)
def ability_profile_for_name(name: str) -> AbilityProfile:
    payload = _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{normalize_name(name)}")
    a1: str | None = None
    a2: str | None = None
    hidden: str | None = None
    for item in payload.get("abilities", []):
        ab = item.get("ability", {}).get("name")
        if not ab:
            continue
        if item.get("is_hidden"):
            hidden = str(ab)
            continue
        slot = int(item.get("slot", 0) or 0)
        if slot == 1:
            a1 = str(ab)
        elif slot == 2:
            a2 = str(ab)
    return AbilityProfile(ability_1=a1, ability_2=a2, hidden_ability=hidden)


def profile_matches(profile: AbilityProfile, *, ability_1: str | None, ability_2: str | None, hidden_ability: str | None) -> bool:
    return (
        profile.ability_1 == ability_1
        and profile.ability_2 == ability_2
        and profile.hidden_ability == hidden_ability
    )

