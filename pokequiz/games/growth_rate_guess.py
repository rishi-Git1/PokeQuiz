"""Growth Rate Guesstimate: compare total experience at level 100 via PokéAPI growth-rate data."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name
from pokequiz.models import Pokemon


def format_growth_label(slug: str) -> str:
    return slug.replace("-", " ").title()


@lru_cache(maxsize=2048)
def xp_and_growth_for_species(api_name: str) -> tuple[int, str] | None:
    """Return (total experience at level 100, growth-rate slug) for a species API name."""
    try:
        species = _fetch_json(f"https://pokeapi.co/api/v2/pokemon-species/{api_name}")
    except Exception:
        return None
    gr = species.get("growth_rate") or {}
    url = gr.get("url")
    slug = gr.get("name")
    if not url or not slug:
        return None
    try:
        payload = _fetch_json(str(url))
    except Exception:
        return None
    for row in payload.get("levels", []):
        if int(row.get("level", 0) or 0) == 100:
            xp = int(row.get("experience", 0) or 0)
            return (xp, str(slug))
    return None


@dataclass(frozen=True, slots=True)
class GrowthChallenge:
    """Three options A/B/C with distinct level-100 experience totals."""

    labels: tuple[str, str, str]
    xp_values: tuple[int, int, int]
    growth_slugs: tuple[str, str, str]
    ask_slowest: bool
    #: Indices 0=A, 1=B, 2=C in the order the player must submit (slowest→fastest or fastest→slowest).
    correct_order: tuple[int, int, int]


def build_challenge(pool: list[Pokemon], *, max_attempts: int = 150) -> GrowthChallenge | None:
    """Pick three species whose level-100 XP totals are all different."""
    if len(pool) < 3:
        return None
    for _ in range(max_attempts):
        trio = random.sample(pool, 3)
        rows: list[tuple[Pokemon, int, str]] = []
        bad = False
        for mon in trio:
            data = xp_and_growth_for_species(normalize_name(mon.name))
            if data is None:
                bad = True
                break
            rows.append((mon, data[0], data[1]))
        if bad:
            continue
        if len({r[1] for r in rows}) < 3:
            continue
        order = [0, 1, 2]
        random.shuffle(order)
        ordered = [rows[i] for i in order]
        xp_vals = tuple(r[1] for r in ordered)
        slugs = tuple(r[2] for r in ordered)
        labels = tuple(r[0].name for r in ordered)
        ask_slowest = random.choice((True, False))
        if ask_slowest:
            correct_order = tuple(sorted((0, 1, 2), key=lambda i: xp_vals[i], reverse=True))
        else:
            correct_order = tuple(sorted((0, 1, 2), key=lambda i: xp_vals[i]))
        return GrowthChallenge(
            labels=labels,
            xp_values=xp_vals,
            growth_slugs=slugs,
            ask_slowest=ask_slowest,
            correct_order=correct_order,
        )
    return None


def _resolve_option_token(token: str, dex, challenge: GrowthChallenge) -> int | None:
    """Map one token (A/B/C, 1/2/3, or a listed species) to option index 0..2."""
    line = token.strip()
    if not line:
        return None
    t = line.casefold()

    if t in {"a", "1"}:
        return 0
    if t in {"b", "2"}:
        return 1
    if t in {"c", "3"}:
        return 2

    if t[0] in "abc":
        rest = t[1:].strip(").: \t-_")
        if not rest:
            return ord(t[0]) - ord("a")
    if t[0] in "123" and len(t) == 1:
        return int(t[0]) - 1
    if len(t) >= 2 and t[0] in "123":
        rest = t[1:].strip(").: \t-_")
        if not rest:
            return int(t[0]) - 1

    for i, nm in enumerate(challenge.labels):
        if t == nm.casefold():
            return i

    guess = dex.by_name(line)
    if not guess:
        return None
    for i, nm in enumerate(challenge.labels):
        if guess.name.casefold() == nm.casefold():
            return i
    return None


def parse_ranking_line(raw: str, dex, challenge: GrowthChallenge) -> tuple[int, int, int] | None:
    """Parse one line with three tokens (whitespace or comma), each A–C / 1–3 / listed name; no duplicates."""
    line = (raw or "").strip()
    if not line:
        return None
    parts = [p for p in re.split(r"[\s,;]+", line) if p]
    if len(parts) != 3:
        return None
    mapped: list[int] = []
    for p in parts:
        idx = _resolve_option_token(p, dex, challenge)
        if idx is None:
            return None
        mapped.append(idx)
    if len(set(mapped)) != 3:
        return None
    return (mapped[0], mapped[1], mapped[2])


def describe_order(challenge: GrowthChallenge, order: tuple[int, int, int]) -> str:
    letters = ("A", "B", "C")
    return " → ".join(f"{letters[i]} ({challenge.labels[i]})" for i in order)


def question_line(challenge: GrowthChallenge) -> str:
    if challenge.ask_slowest:
        return (
            "Order all three from SLOWEST to fastest leveling (most total XP at level 100 first). "
            'One line with three entries, e.g. "B C A" or three species names.'
        )
    return (
        "Order all three from FASTEST to slowest leveling (least total XP at level 100 first). "
        'One line with three entries, e.g. "A B C" or three species names.'
    )


def format_option_summary(challenge: GrowthChallenge, index: int) -> str:
    slug = challenge.growth_slugs[index]
    xp = challenge.xp_values[index]
    return f"{challenge.labels[index]} — {format_growth_label(slug)} ({xp:,} XP at L100)"
