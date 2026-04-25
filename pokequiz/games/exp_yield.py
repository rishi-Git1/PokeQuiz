"""EXP Yield: compare base experience (defeat reward) from the Pokemon resource's base_experience field."""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name
from pokequiz.models import Pokemon


@lru_cache(maxsize=4096)
def base_experience_for_species(api_name: str) -> int | None:
    """PokéAPI `base_experience` for a Pokémon form (scaled by level in games)."""
    try:
        payload = _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{api_name}")
    except Exception:
        return None
    raw = payload.get("base_experience")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class ExpYieldChallenge:
    """N labeled options: which has highest or lowest base experience."""

    names: tuple[str, ...]
    base_xp: tuple[int, ...]
    ask_more: bool  # True = more base XP, False = less
    correct_index: int  # index into names (0 = A, ...)


def build_challenge(
    pool: list[Pokemon],
    n: int,
    *,
    max_attempts: int = 300,
) -> ExpYieldChallenge | None:
    """N species, all with distinct base_experience, random order, more/less question."""
    if n < 2 or len(pool) < n:
        return None
    for _ in range(max_attempts):
        picked = random.sample(pool, n)
        rows: list[tuple[str, int]] = []
        bad = False
        for mon in picked:
            x = base_experience_for_species(normalize_name(mon.name))
            if x is None:
                bad = True
                break
            rows.append((mon.name, x))
        if bad:
            continue
        if len({r[1] for r in rows}) < n:
            continue
        order = list(range(n))
        random.shuffle(order)
        shuffled = [rows[i] for i in order]
        names = tuple(r[0] for r in shuffled)
        xps = tuple(r[1] for r in shuffled)
        ask_more = random.choice((True, False))
        if ask_more:
            correct = max(range(n), key=lambda i: xps[i])
        else:
            correct = min(range(n), key=lambda i: xps[i])
        return ExpYieldChallenge(
            names=names,
            base_xp=xps,
            ask_more=ask_more,
            correct_index=correct,
        )
    return None


def prompt_line(c: ExpYieldChallenge) -> str:
    n = len(c.names)
    word = f" of these {n} species" if n > 2 else " of the two"
    if c.ask_more:
        return f"Which{word} gives the MOST base experience when defeated? (PokéAPI field: base_experience.)"
    return f"Which{word} gives the LEAST base experience when defeated? (PokéAPI field: base_experience.)"


def letter_labels(n: int) -> tuple[str, ...]:
    return tuple(chr(ord("A") + i) for i in range(n))


def pick_help_line(n: int) -> str:
    if n == 2:
        return "Answer with A / B, 1 / 2, or a listed species name."
    if n <= 8:
        last_letter = chr(ord("A") + n - 1)
        return f"Answer with A–{last_letter}, 1–{n}, or a listed species name."
    return f"Answer with 1–{n} or a listed species name."


def resolve_pick(raw: str, dex, c: ExpYieldChallenge) -> int | None:
    """Map input to 0..n-1, or None."""
    n = len(c.names)
    line = (raw or "").strip()
    if not line:
        return None
    t = line.casefold()

    for i in range(n):
        if t == chr(ord("a") + i) or t == str(i + 1):
            return i

    if t and t[0] in "abcdefghijklmnopqrstuvwxyz" and ord(t[0]) - ord("a") < n:
        rest = t[1:].strip(").: \t-_")
        if not rest:
            return ord(t[0]) - ord("a")

    for i, nm in enumerate(c.names):
        if t == nm.casefold():
            return i
    guess = dex.by_name(line)
    if not guess:
        return None
    g = guess.name.casefold()
    for i, nm in enumerate(c.names):
        if g == nm.casefold():
            return i
    return None


def reveal_line(c: ExpYieldChallenge, i: int) -> str:
    return f"{c.names[i]} — {c.base_xp[i]:,} base experience"
