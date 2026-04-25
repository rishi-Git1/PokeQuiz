"""Characteristic Decoder: map Pokémon characteristic text to its stat."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json


@dataclass(frozen=True, slots=True)
class CharacteristicChallenge:
    characteristic_text: str
    stat_slug: str


_STAT_LABELS: dict[str, str] = {
    "hp": "HP",
    "attack": "Attack",
    "defense": "Defense",
    "special-attack": "Special Attack",
    "special-defense": "Special Defense",
    "speed": "Speed",
}


def display_stat_name(stat_slug: str) -> str:
    return _STAT_LABELS.get(stat_slug, stat_slug.replace("-", " ").title())


@lru_cache(maxsize=1)
def _characteristic_ids() -> tuple[int, ...]:
    """All characteristic IDs available in PokéAPI."""
    payload = _fetch_json("https://pokeapi.co/api/v2/characteristic?limit=1000")
    ids: list[int] = []
    for row in payload.get("results", []) or []:
        url = str(row.get("url") or "")
        m = re.search(r"/characteristic/(\d+)/?$", url)
        if m:
            ids.append(int(m.group(1)))
    return tuple(ids)


def build_challenge(*, max_attempts: int = 100) -> CharacteristicChallenge | None:
    ids = list(_characteristic_ids())
    if not ids:
        return None
    random.shuffle(ids)
    for cid in ids[: max_attempts]:
        try:
            payload = _fetch_json(f"https://pokeapi.co/api/v2/characteristic/{cid}")
        except Exception:
            continue
        stat_slug = (payload.get("highest_stat") or {}).get("name")
        if not isinstance(stat_slug, str) or not stat_slug:
            continue
        text = None
        for d in payload.get("descriptions", []) or []:
            if (d.get("language") or {}).get("name") == "en":
                raw = str(d.get("description") or "").strip()
                if raw:
                    text = " ".join(raw.split())
                    break
        if not text:
            continue
        return CharacteristicChallenge(characteristic_text=text, stat_slug=stat_slug)
    return None


def parse_stat_guess(raw: str) -> str | None:
    s = (raw or "").strip().casefold()
    if not s:
        return None
    norm = re.sub(r"[^a-z0-9]+", "", s)
    aliases = {
        "hp": "hp",
        "health": "hp",
        "attack": "attack",
        "atk": "attack",
        "defense": "defense",
        "def": "defense",
        "specialattack": "special-attack",
        "spattack": "special-attack",
        "spatk": "special-attack",
        "spa": "special-attack",
        "specialatk": "special-attack",
        "specialdefense": "special-defense",
        "spdefense": "special-defense",
        "spdef": "special-defense",
        "spd": "special-defense",
        "specialdef": "special-defense",
        "speed": "speed",
        "spe": "speed",
    }
    return aliases.get(norm)
