"""Item Lore: guess the item from redacted English flavor_text_entries (PokéAPI)."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from pokequiz.data import _fetch_json


# Competitive and story items with English flavor text on PokéAPI (subset; shuffled at runtime).
_POPULAR_ITEM_SLUGS: tuple[str, ...] = (
    "choice-band",
    "choice-scarf",
    "choice-specs",
    "leftovers",
    "life-orb",
    "assault-vest",
    "focus-sash",
    "eviolite",
    "rocky-helmet",
    "weakness-policy",
    "heavy-duty-boots",
    "light-clay",
    "mental-herb",
    "white-herb",
    "power-herb",
    "room-service",
    "master-ball",
    "ultra-ball",
    "great-ball",
    "poke-ball",
    "safari-ball",
    "rare-candy",
    "pp-up",
    "pp-max",
    "ether",
    "max-elixir",
    "amulet-coin",
    "luck-incense",
    "exp-share",
    "destiny-knot",
    "oval-charm",
    "silph-scope",
    "bicycle",
    "town-map",
    "dowsing-machine",
    "flame-orb",
    "toxic-orb",
    "black-sludge",
    "big-root",
    "shell-bell",
    "wise-glasses",
    "muscle-band",
    "expert-belt",
    "razor-claw",
    "razor-fang",
)


def display_item_name(slug: str) -> str:
    return slug.replace("-", " ").title()


@dataclass(frozen=True, slots=True)
class ItemLoreChallenge:
    item_slug: str
    descriptions: tuple[str, ...]


def _english_flavor_texts_from_payload(payload: dict) -> tuple[str, ...]:
    """English flavor lines from an item payload, unique text, first-seen order."""
    out: list[str] = []
    seen: set[str] = set()
    for e in payload.get("flavor_text_entries", []) or []:
        if (e.get("language") or {}).get("name") != "en":
            continue
        raw = (e.get("text") or "").replace("\f", " ")
        t = " ".join(raw.split())
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return tuple(out)


def english_item_flavor_texts(item_slug: str) -> tuple[str, ...]:
    """English flavor lines for an item slug."""
    try:
        payload = _fetch_json(f"https://pokeapi.co/api/v2/item/{item_slug}")
    except Exception:
        return ()
    return _english_flavor_texts_from_payload(payload)


def redact_for_item(text: str, *, item_slug: str) -> str:
    disp = display_item_name(item_slug)
    t = text
    labels = sorted(
        {item_slug, item_slug.replace("-", " "), disp},
        key=len,
        reverse=True,
    )
    for lab in labels:
        if len(lab) < 2:
            continue
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9'\-. ]*", lab):
            t = re.sub(r"(?i)\b" + re.escape(lab) + r"\b", "???", t)
        else:
            t = re.sub(re.escape(lab), "???", t, flags=re.IGNORECASE)
    return t


def build_challenge(*, random_item_tries: int = 120) -> ItemLoreChallenge | None:
    """Pick an item with at least one English flavor entry (known slugs first, then random ids)."""
    slugs = list(_POPULAR_ITEM_SLUGS)
    random.shuffle(slugs)
    for slug in slugs:
        texts = english_item_flavor_texts(slug)
        if texts:
            return ItemLoreChallenge(item_slug=slug, descriptions=texts)
    for _ in range(random_item_tries):
        try:
            payload = _fetch_json(f"https://pokeapi.co/api/v2/item/{random.randint(1, 2208)}/")
        except Exception:
            continue
        texts = _english_flavor_texts_from_payload(payload)
        slug = payload.get("name")
        if texts and isinstance(slug, str) and slug:
            return ItemLoreChallenge(item_slug=slug, descriptions=texts)
    return None


def item_guess_matches(raw: str, item_slug: str) -> bool:
    g = re.sub(r"[^a-z0-9-]", "", raw.strip().casefold().replace(" ", "-"))
    s = re.sub(r"[^a-z0-9-]", "", item_slug.casefold())
    if g == s:
        return True
    return raw.strip().casefold() == display_item_name(item_slug).casefold()


_ALL_ITEM_SLUGS: frozenset[str] | None = None
_ITEM_DISPLAY_TO_SLUG: dict[str, str] | None = None


def ensure_item_guess_index() -> None:
    """Load all item slugs from PokéAPI once (for validating guesses)."""
    global _ALL_ITEM_SLUGS, _ITEM_DISPLAY_TO_SLUG
    if _ALL_ITEM_SLUGS is not None:
        return
    slugs: list[str] = []
    url: str | None = "https://pokeapi.co/api/v2/item?limit=5000"
    while url:
        payload = _fetch_json(url)
        for r in payload.get("results") or []:
            n = r.get("name")
            if isinstance(n, str) and n:
                slugs.append(n)
        nxt = payload.get("next")
        url = nxt if isinstance(nxt, str) and nxt else None
    _ALL_ITEM_SLUGS = frozenset(slugs)
    _ITEM_DISPLAY_TO_SLUG = {display_item_name(s).casefold(): s for s in _ALL_ITEM_SLUGS}


def item_slug_from_user_guess(raw: str) -> str | None:
    """Resolve user text to an official item slug, or None if it is not a known item."""
    ensure_item_guess_index()
    assert _ALL_ITEM_SLUGS is not None and _ITEM_DISPLAY_TO_SLUG is not None
    s = raw.strip()
    if not s:
        return None
    hyphen = re.sub(r"[^a-z0-9-]", "", s.casefold().replace(" ", "-"))
    while "--" in hyphen:
        hyphen = hyphen.replace("--", "-")
    if hyphen in _ALL_ITEM_SLUGS:
        return hyphen
    return _ITEM_DISPLAY_TO_SLUG.get(s.casefold())
