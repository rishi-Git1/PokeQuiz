"""Move Match: guess the move from redacted English effect + flavor text (PokéAPI)."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from pokequiz.data import _fetch_json


@dataclass(frozen=True, slots=True)
class MoveMatchChallenge:
    move_slug: str
    descriptions: tuple[str, ...]


def display_move_name(slug: str) -> str:
    return slug.replace("-", " ").title()


def _english_effect_texts_from_payload(payload: dict) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    chance_raw = payload.get("effect_chance")
    try:
        effect_chance = int(chance_raw) if chance_raw is not None else None
    except (TypeError, ValueError):
        effect_chance = None
    def _sanitize_effect_text(text: str, *, effect_chance: int | None) -> str:
        t = " ".join(text.replace("\f", " ").split())
        if not t:
            return ""
        if effect_chance is not None:
            t = t.replace("$effect_chance", str(effect_chance))
        t = re.sub(r"\$[a-z_]+%?", "???", t, flags=re.IGNORECASE)
        t = re.sub(r"\d+", "?", t)
        return t

    for e in payload.get("effect_entries", []) or []:
        if (e.get("language") or {}).get("name") != "en":
            continue
        # Show short effect first, then full effect as clue 1.
        short = _sanitize_effect_text(str(e.get("short_effect") or ""), effect_chance=effect_chance)
        full = _sanitize_effect_text(str(e.get("effect") or ""), effect_chance=effect_chance)
        for t in (short, full):
            if not t or t in seen:
                continue
            seen.add(t)
            out.append(t)
    return tuple(out)


def _english_flavor_texts_from_payload(payload: dict) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for e in payload.get("flavor_text_entries", []) or []:
        if (e.get("language") or {}).get("name") != "en":
            continue
        raw = str(e.get("flavor_text") or "")
        t = " ".join(raw.replace("\f", " ").replace("\n", " ").split())
        if not t:
            continue
        # Keep move-match clues number-agnostic.
        t = re.sub(r"\d+", "?", t)
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return tuple(out)


def english_move_effect_texts(move_slug: str) -> tuple[str, ...]:
    try:
        payload = _fetch_json(f"https://pokeapi.co/api/v2/move/{move_slug}")
    except Exception:
        return ()
    effects = _english_effect_texts_from_payload(payload)
    flavors = _english_flavor_texts_from_payload(payload)
    # Requested clue flow: short_effect first, full effect clue 1, then move flavor text clues.
    return effects + tuple(x for x in flavors if x not in effects)


def redact_for_move(text: str, *, move_slug: str) -> str:
    disp = display_move_name(move_slug)
    t = text
    labels = sorted(
        {move_slug, move_slug.replace("-", " "), disp},
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


def build_challenge(*, random_move_tries: int = 140) -> MoveMatchChallenge | None:
    for _ in range(random_move_tries):
        try:
            payload = _fetch_json(f"https://pokeapi.co/api/v2/move/{random.randint(1, 1000)}/")
        except Exception:
            continue
        effects = _english_effect_texts_from_payload(payload)
        flavors = _english_flavor_texts_from_payload(payload)
        texts = effects + tuple(x for x in flavors if x not in effects)
        slug = payload.get("name")
        if texts and isinstance(slug, str) and slug:
            return MoveMatchChallenge(move_slug=slug, descriptions=texts)
    return None


_ALL_MOVE_SLUGS: frozenset[str] | None = None
_MOVE_DISPLAY_TO_SLUG: dict[str, str] | None = None


def ensure_move_guess_index() -> None:
    """Load all move slugs from PokéAPI once (for validating guesses)."""
    global _ALL_MOVE_SLUGS, _MOVE_DISPLAY_TO_SLUG
    if _ALL_MOVE_SLUGS is not None:
        return
    slugs: list[str] = []
    url: str | None = "https://pokeapi.co/api/v2/move?limit=10000"
    while url:
        payload = _fetch_json(url)
        for r in payload.get("results") or []:
            n = r.get("name")
            if isinstance(n, str) and n:
                slugs.append(n)
        nxt = payload.get("next")
        url = nxt if isinstance(nxt, str) and nxt else None
    _ALL_MOVE_SLUGS = frozenset(slugs)
    _MOVE_DISPLAY_TO_SLUG = {display_move_name(s).casefold(): s for s in _ALL_MOVE_SLUGS}


def move_slug_from_user_guess(raw: str) -> str | None:
    """Resolve user text to an official move slug, or None if unknown."""
    ensure_move_guess_index()
    assert _ALL_MOVE_SLUGS is not None and _MOVE_DISPLAY_TO_SLUG is not None
    s = raw.strip()
    if not s:
        return None
    hyphen = re.sub(r"[^a-z0-9-]", "", s.casefold().replace(" ", "-"))
    while "--" in hyphen:
        hyphen = hyphen.replace("--", "-")
    if hyphen in _ALL_MOVE_SLUGS:
        return hyphen
    return _MOVE_DISPLAY_TO_SLUG.get(s.casefold())
