"""Method Man: identify a move's primary learn method by generation."""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name
from pokequiz.models import Pokemon


@dataclass(frozen=True, slots=True)
class MethodManChallenge:
    pokemon_name: str
    generation: int
    move_slug: str
    primary_method: str  # level-up | machine | egg | tutor


_METHOD_PRIORITY: tuple[str, ...] = ("level-up", "machine", "egg", "tutor")
_METHOD_LABELS: dict[str, str] = {
    "level-up": "Level-up",
    "machine": "Machine",
    "egg": "Egg",
    "tutor": "Tutor",
}


def display_method_name(method_slug: str) -> str:
    return _METHOD_LABELS.get(method_slug, method_slug.replace("-", " ").title())


@lru_cache(maxsize=128)
def _generation_for_version_group(version_group_name: str) -> int | None:
    try:
        payload = _fetch_json(f"https://pokeapi.co/api/v2/version-group/{version_group_name}")
    except Exception:
        return None
    g = (payload.get("generation") or {}).get("name")
    if not isinstance(g, str):
        return None
    roman = g.replace("generation-", "").upper()
    values = {"I": 1, "V": 5, "X": 10}
    total = 0
    prev = 0
    for ch in reversed(roman):
        if ch not in values:
            return None
        v = values[ch]
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total if total > 0 else None


def _primary_method(methods: list[str]) -> str | None:
    uniq = set(methods)
    for m in _METHOD_PRIORITY:
        if m in uniq:
            return m
    return None


def build_challenge(pool: list[Pokemon], *, max_attempts: int = 140) -> MethodManChallenge | None:
    if not pool:
        return None
    for _ in range(max_attempts):
        mon = random.choice(pool)
        try:
            payload = _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{normalize_name(mon.name)}")
        except Exception:
            continue
        candidates: list[MethodManChallenge] = []
        for row in payload.get("moves", []) or []:
            move_slug = (row.get("move") or {}).get("name")
            if not isinstance(move_slug, str) or not move_slug:
                continue
            methods_by_gen: dict[int, list[str]] = {}
            for det in row.get("version_group_details", []) or []:
                vg = (det.get("version_group") or {}).get("name")
                method = (det.get("move_learn_method") or {}).get("name")
                if not isinstance(vg, str) or not vg or not isinstance(method, str) or not method:
                    continue
                gen = _generation_for_version_group(vg)
                if gen is None:
                    continue
                methods_by_gen.setdefault(gen, []).append(method)
            for gen, methods in methods_by_gen.items():
                primary = _primary_method(methods)
                if primary is None:
                    continue
                candidates.append(
                    MethodManChallenge(
                        pokemon_name=mon.name,
                        generation=gen,
                        move_slug=move_slug,
                        primary_method=primary,
                    )
                )
        if candidates:
            return random.choice(candidates)
    return None


def parse_method_guess(raw: str) -> str | None:
    s = (raw or "").strip().casefold().replace("_", "-").replace(" ", "-")
    aliases = {
        "level": "level-up",
        "levelup": "level-up",
        "lvlup": "level-up",
        "tm": "machine",
        "tr": "machine",
        "tm-tr": "machine",
        "eggmove": "egg",
        "egg-move": "egg",
        "breeding": "egg",
        "breed": "egg",
        "move-tutor": "tutor",
    }
    s = aliases.get(s, s)
    if s in {"level-up", "machine", "egg", "tutor"}:
        return s
    return None
