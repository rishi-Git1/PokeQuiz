"""Power Levels: higher/lower on base stat totals (BST), with chained rounds like DexIt."""

from __future__ import annotations

import random

from pokequiz.models import Pokemon


def pick_target_and_guess(pool: list[Pokemon], *, max_attempts: int = 200) -> tuple[Pokemon, Pokemon] | None:
    """Two species with different base stat totals (start of a chain or after a reset)."""
    if len(pool) < 2:
        return None
    for _ in range(max_attempts):
        a, b = random.sample(pool, 2)
        if a.bst != b.bst:
            return (a, b)
    return None


def pick_next_guess(anchor: Pokemon, pool: list[Pokemon]) -> Pokemon | None:
    """A new species: not the anchor, and a different BST."""
    candidates = [p for p in pool if p.name != anchor.name and p.bst != anchor.bst]
    if not candidates:
        return None
    return random.choice(candidates)


def is_correct_guess(user_says_higher: bool, target: Pokemon, guess: Pokemon) -> bool:
    """True if the user’s higher/lower call matches the order of base stat totals."""
    truth_higher = guess.bst > target.bst
    return user_says_higher == truth_higher
