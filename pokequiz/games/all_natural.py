"""All Natural: guess Natural Gift type + power from a berry."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json


@dataclass(frozen=True, slots=True)
class AllNaturalChallenge:
    berry_slug: str
    natural_gift_type_slug: str
    natural_gift_power: int


def display_berry_name(slug: str) -> str:
    return slug.replace("-", " ").title()


def display_type_name(slug: str) -> str:
    return slug.replace("-", " ").title()


@lru_cache(maxsize=1)
def _berry_slugs() -> tuple[str, ...]:
    """All berry slugs from PokéAPI berry index."""
    out: list[str] = []
    url: str | None = "https://pokeapi.co/api/v2/berry?limit=200"
    while url:
        payload = _fetch_json(url)
        for r in payload.get("results") or []:
            n = r.get("name")
            if isinstance(n, str) and n:
                out.append(n)
        nxt = payload.get("next")
        url = nxt if isinstance(nxt, str) and nxt else None
    return tuple(out)


def build_challenge(*, random_item_tries: int = 220) -> AllNaturalChallenge | None:
    """Pick a berry that has Natural Gift type and power."""
    slugs = list(_berry_slugs())
    random.shuffle(slugs)
    for berry_name in slugs[: max(1, random_item_tries)]:
        try:
            payload = _fetch_json(f"https://pokeapi.co/api/v2/berry/{berry_name}")
        except Exception:
            continue
        item_slug = (payload.get("item") or {}).get("name")
        if not isinstance(item_slug, str) or not item_slug.endswith("-berry"):
            continue
        t = (payload.get("natural_gift_type") or {}).get("name")
        p = payload.get("natural_gift_power")
        if not isinstance(t, str) or not t:
            continue
        try:
            power = int(p)
        except (TypeError, ValueError):
            continue
        return AllNaturalChallenge(
            berry_slug=item_slug,
            natural_gift_type_slug=t,
            natural_gift_power=power,
        )
    return None


def _norm_text(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.casefold())


_TYPE_SLUGS: tuple[str, ...] = (
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
_TYPE_TEXT_TO_SLUG = {_norm_text(s): s for s in _TYPE_SLUGS}


def parse_guess(raw: str, ch: AllNaturalChallenge) -> tuple[bool, str, str | None]:
    """
    Parse "<type> <power>" or "<power> <type>".
    Returns (is_correct, canonical_key, error_message).
    Empty key means invalid format/type and should not consume a turn.
    """
    s = (raw or "").strip()
    if not s:
        return False, "", "Guess cannot be blank."
    nums = re.findall(r"\d+", s)
    if len(nums) != 1:
        return False, "", f'Could not parse "{raw}". Use one type and one power number (example: Fire 80).'
    try:
        power = int(nums[0])
    except ValueError:
        return False, "", f'Could not parse "{raw}". Use one type and one power number (example: Fire 80).'

    # Remove the power token and normalize remaining text as type guess.
    type_part = re.sub(r"\d+", " ", s)
    guessed_type_text = type_part.strip()
    guessed_type = _norm_text(type_part)
    if not guessed_type:
        return False, "", f'Could not parse "{raw}". Include a type and power (example: Fire 80).'
    type_slug = _TYPE_TEXT_TO_SLUG.get(guessed_type)
    if type_slug is None:
        return False, "", f'Unknown type in guess: "{guessed_type_text}".'
    key = f"{type_slug}:{power}"
    want_type = _norm_text(ch.natural_gift_type_slug)
    ok = _norm_text(type_slug) == want_type and power == ch.natural_gift_power
    return ok, key, None
