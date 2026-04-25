"""Nature-Flavor Matrix: map nature likes/dislikes to berry flavors."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from pokequiz.data import _fetch_json


@dataclass(frozen=True, slots=True)
class NatureFlavorChallenge:
    nature_name: str
    ask_likes: bool
    answer_flavor: str


_STAT_TO_FLAVOR: dict[str, str] = {
    "attack": "spicy",
    "defense": "sour",
    "special-attack": "dry",
    "special-defense": "bitter",
    "speed": "sweet",
}


def display_flavor_name(slug: str) -> str:
    return slug.replace("-", " ").title()


def build_challenge(*, max_attempts: int = 80) -> NatureFlavorChallenge | None:
    """Pick a non-neutral nature and ask likes/dislikes flavor."""
    for _ in range(max_attempts):
        try:
            payload = _fetch_json(f"https://pokeapi.co/api/v2/nature/{random.randint(1, 25)}")
        except Exception:
            continue
        nature_name = payload.get("name")
        if not isinstance(nature_name, str) or not nature_name:
            continue
        inc = (payload.get("increased_stat") or {}).get("name")
        dec = (payload.get("decreased_stat") or {}).get("name")
        if not isinstance(inc, str) or not isinstance(dec, str):
            continue
        if inc == dec:
            continue
        likes = _STAT_TO_FLAVOR.get(inc)
        dislikes = _STAT_TO_FLAVOR.get(dec)
        if not likes or not dislikes:
            continue
        ask_likes = random.choice((True, False))
        return NatureFlavorChallenge(
            nature_name=nature_name.title(),
            ask_likes=ask_likes,
            answer_flavor=likes if ask_likes else dislikes,
        )
    return None


def parse_flavor_guess(raw: str) -> str | None:
    s = re.sub(r"[^a-z]+", "", (raw or "").casefold())
    aliases = {
        "spicy": "spicy",
        "hot": "spicy",
        "sour": "sour",
        "dry": "dry",
        "bitter": "bitter",
        "sweet": "sweet",
    }
    return aliases.get(s)
