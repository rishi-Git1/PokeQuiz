"""Metronome Blacklist: determine if a move can be called by Metronome."""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json
from pokequiz.games.move_match import display_move_name


@dataclass(frozen=True, slots=True)
class MetronomeBlacklistChallenge:
    move_slug: str
    callable_by_metronome: bool


# Curated blacklist of moves Metronome cannot call (modern games).
# This intentionally targets known loop-breaking/special-case exclusions.
_BLACKLISTED_MOVE_SLUGS: frozenset[str] = frozenset(
    {
        "after-you",
        "assist",
        "beak-blast",
        "belch",
        "bestow",
        "celebrate",
        "chatter",
        "copycat",
        "counter",
        "covet",
        "crafty-shield",
        "destiny-bond",
        "detect",
        "diamond-storm",
        "endure",
        "feint",
        "focus-punch",
        "follow-me",
        "freeze-shock",
        "helping-hand",
        "hold-hands",
        "hyperspace-fury",
        "ice-burn",
        "kings-shield",
        "light-of-ruin",
        "mat-block",
        "me-first",
        "metronome",
        "mimic",
        "mirror-coat",
        "mirror-move",
        "nature-power",
        "origin-pulse",
        "precipice-blades",
        "protect",
        "rage-powder",
        "relic-song",
        "secret-sword",
        "shell-trap",
        "sketch",
        "sleep-talk",
        "snatch",
        "snore",
        "spiky-shield",
        "spotlight",
        "steam-eruption",
        "struggle",
        "thief",
        "transform",
        "v-create",
        "wide-guard",
    }
)


_SIGNATURE_ZMOVE_SLUGS: frozenset[str] = frozenset(
    {
        "catastropika",
        "sinister-arrow-raid",
        "malicious-moonsault",
        "oceanic-operetta",
        "soul-stealing-7-star-strike",
        "stoked-sparksurfer",
        "pulverizing-pancake",
        "extreme-evoboost",
        "genesis-supernova",
        "10-000-000-volt-thunderbolt",
        "light-that-burns-the-sky",
        "searing-sunraze-smash",
        "menacing-moonraze-maelstrom",
        "lets-snuggle-forever",
        "splintered-stormshards",
        "clangorous-soulblaze",
        "guardian-of-alola",
    }
)


def _is_z_move_slug(move_slug: str) -> bool:
    # Type-based Z-Moves in PokéAPI are split into --physical/--special variants.
    if move_slug.endswith("--physical") or move_slug.endswith("--special"):
        return True
    return move_slug in _SIGNATURE_ZMOVE_SLUGS


@lru_cache(maxsize=1)
def _all_move_slugs() -> tuple[str, ...]:
    out: list[str] = []
    url: str | None = "https://pokeapi.co/api/v2/move?limit=10000"
    while url:
        payload = _fetch_json(url)
        for r in payload.get("results") or []:
            n = r.get("name")
            if isinstance(n, str) and n:
                out.append(n)
        nxt = payload.get("next")
        url = nxt if isinstance(nxt, str) and nxt else None
    return tuple(out)


def build_challenge() -> MetronomeBlacklistChallenge:
    move = random.choice(_all_move_slugs())
    return MetronomeBlacklistChallenge(
        move_slug=move,
        callable_by_metronome=(move not in _BLACKLISTED_MOVE_SLUGS and not _is_z_move_slug(move)),
    )


def display_move_line(slug: str) -> str:
    return display_move_name(slug)


def parse_yes_no_guess(raw: str) -> bool | None:
    s = (raw or "").strip().casefold()
    if s in {"yes", "y", "true", "callable"}:
        return True
    if s in {"no", "n", "false", "blacklisted"}:
        return False
    return None
