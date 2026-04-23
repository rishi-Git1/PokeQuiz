from __future__ import annotations

from pokequiz.models import Pokemon


def compare_guess(target: Pokemon, guess: Pokemon) -> dict[str, str]:
    def cmp_numeric(g: int, t: int) -> str:
        if g == t:
            return "equal"
        return "higher" if g < t else "lower"

    return {
        "generation": cmp_numeric(guess.generation, target.generation),
        "height": cmp_numeric(guess.height_dm, target.height_dm),
        "weight": cmp_numeric(guess.weight_hg, target.weight_hg),
        "bst": cmp_numeric(guess.bst, target.bst),
        "type_match": "yes" if any(t in target.types for t in guess.types) else "no",
    }
