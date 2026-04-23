from __future__ import annotations

from pokequiz.models import Pokemon


def prompt_for_mon(mon: Pokemon) -> str:
    return (
        f"HP:{mon.hp} Atk:{mon.attack} Def:{mon.defense} "
        f"SpA:{mon.special_attack} SpD:{mon.special_defense} Spe:{mon.speed} BST:{mon.bst}"
    )


def is_correct_guess(mon: Pokemon, guess: str) -> bool:
    return guess.casefold().strip() in mon.all_names
