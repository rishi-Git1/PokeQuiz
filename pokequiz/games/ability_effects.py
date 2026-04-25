"""Ability Effects: guess the ability from redacted English effect_entries (PokéAPI)."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from pokequiz.data import _fetch_json
from pokequiz.games.ability_assessor import ability_profile_for_name, display_ability_name
from pokequiz.models import Pokemon


@dataclass(frozen=True, slots=True)
class AbilityEffectsChallenge:
    """Source species (for redaction) and ability slug; ordered English effect texts."""

    pokemon_name: str
    ability_slug: str
    descriptions: tuple[str, ...]


def english_ability_effect_texts(ability_slug: str) -> tuple[str, ...]:
    """English `effect` strings from effect_entries, unique and in API order."""
    try:
        payload = _fetch_json(f"https://pokeapi.co/api/v2/ability/{ability_slug}")
    except Exception:
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for e in payload.get("effect_entries", []) or []:
        if (e.get("language") or {}).get("name") != "en":
            continue
        raw = (e.get("effect") or "").replace("\f", " ")
        t = " ".join(raw.split())
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return tuple(out)


def redact_for_ability(text: str, *, ability_slug: str, pokemon_display: str) -> str:
    """Hide ability and Pokémon names in effect copy (best-effort word boundaries)."""
    t = text
    labels: list[str] = [
        display_ability_name(ability_slug),
        ability_slug.replace("-", " "),
        ability_slug,
    ]
    for p in (pokemon_display, pokemon_display.replace("-", " ")):
        if p and p not in labels:
            labels.append(p)
    for label in sorted({x for x in labels if len(x.strip()) >= 2}, key=len, reverse=True):
        lab = label.strip()
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9'\-. ]*", lab):
            t = re.sub(r"(?i)\b" + re.escape(lab) + r"\b", "???", t)
        else:
            t = re.sub(re.escape(lab), "???", t, flags=re.IGNORECASE)
    return t


def build_challenge(pool: list[Pokemon], *, max_attempts: int = 100) -> AbilityEffectsChallenge | None:
    """Pick a species from the pool and one of its abilities with at least one English effect entry."""
    if not pool:
        return None
    for _ in range(max_attempts):
        mon = random.choice(pool)
        try:
            prof = ability_profile_for_name(mon.name)
        except Exception:
            continue
        candidates = [x for x in (prof.ability_1, prof.ability_2, prof.hidden_ability) if x]
        if not candidates:
            continue
        slug = random.choice(candidates)
        texts = english_ability_effect_texts(slug)
        if not texts:
            continue
        return AbilityEffectsChallenge(
            pokemon_name=mon.name,
            ability_slug=slug,
            descriptions=texts,
        )
    return None


def ability_guess_matches(raw: str, ability_slug: str) -> bool:
    g = raw.strip().casefold().replace(" ", "-")
    if g == ability_slug.casefold():
        return True
    return raw.strip().casefold() == display_ability_name(ability_slug).casefold()


_ALL_ABILITY_SLUGS: frozenset[str] | None = None
_ABILITY_DISPLAY_TO_SLUG: dict[str, str] | None = None


def ensure_ability_guess_index() -> None:
    """Load all ability slugs from PokéAPI once (for validating guesses)."""
    global _ALL_ABILITY_SLUGS, _ABILITY_DISPLAY_TO_SLUG
    if _ALL_ABILITY_SLUGS is not None:
        return
    slugs: list[str] = []
    url: str | None = "https://pokeapi.co/api/v2/ability?limit=2000"
    while url:
        payload = _fetch_json(url)
        for r in payload.get("results") or []:
            n = r.get("name")
            if isinstance(n, str) and n:
                slugs.append(n)
        nxt = payload.get("next")
        url = nxt if isinstance(nxt, str) and nxt else None
    _ALL_ABILITY_SLUGS = frozenset(slugs)
    _ABILITY_DISPLAY_TO_SLUG = {
        display_ability_name(s).casefold(): s for s in _ALL_ABILITY_SLUGS
    }


def ability_slug_from_user_guess(raw: str) -> str | None:
    """Resolve user text to an official ability slug, or None if it is not a known ability."""
    ensure_ability_guess_index()
    assert _ALL_ABILITY_SLUGS is not None and _ABILITY_DISPLAY_TO_SLUG is not None
    s = raw.strip()
    if not s:
        return None
    hyphen = re.sub(r"[^a-z0-9\-]", "", s.casefold().replace(" ", "-"))
    while "--" in hyphen:
        hyphen = hyphen.replace("--", "-")
    if hyphen in _ALL_ABILITY_SLUGS:
        return hyphen
    return _ABILITY_DISPLAY_TO_SLUG.get(s.casefold())
