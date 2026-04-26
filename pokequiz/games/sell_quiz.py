"""Sell: identify an item's sell price from PokéAPI item cost."""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json


@dataclass(frozen=True, slots=True)
class SellChallenge:
    item_slug: str
    buy_cost: int
    sell_price: int


_QUIZ_CATEGORIES: tuple[str, ...] = (
    "standard-balls",
    "special-balls",
    "apricorn-balls",
    "medicine",
    "healing",
    "status-cures",
    "revival",
    "pp-recovery",
    "vitamins",
)
_EXCLUDED_SLUGS: frozenset[str] = frozenset({"luxury-ball", "master-ball"})


def display_item_name(slug: str) -> str:
    return slug.replace("-", " ").title()


@lru_cache(maxsize=1)
def _candidate_item_slugs() -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for category in _QUIZ_CATEGORIES:
        payload = _fetch_json(f"https://pokeapi.co/api/v2/item-category/{category}")
        for row in payload.get("items", []) or []:
            name = row.get("name")
            if not isinstance(name, str) or not name or name in seen:
                continue
            seen.add(name)
            out.append(name)
    return tuple(out)


def build_challenge(*, max_attempts: int = 80) -> SellChallenge | None:
    slugs = [s for s in _candidate_item_slugs() if s not in _EXCLUDED_SLUGS]
    if not slugs:
        return None
    random.shuffle(slugs)
    for slug in slugs[:max_attempts]:
        try:
            payload = _fetch_json(f"https://pokeapi.co/api/v2/item/{slug}")
        except Exception:
            continue
        raw = payload.get("cost")
        try:
            cost = int(raw)
        except (TypeError, ValueError):
            continue
        if cost <= 0:
            continue
        return SellChallenge(item_slug=slug, buy_cost=cost, sell_price=cost // 2)
    return None
