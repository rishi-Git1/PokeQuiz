from __future__ import annotations

from pokequiz.models import Pokemon

# Sentinel for "no second type" so primary/secondary slots are always comparable.
_NO_SECONDARY = "__none__"


def type_slot(mon: Pokemon, slot: int) -> str:
    """Primary (0) or secondary (1). Missing second type uses its own category (not equal to any real type)."""
    if slot == 0:
        return mon.types[0] if mon.types else _NO_SECONDARY
    if len(mon.types) >= 2:
        return mon.types[1]
    return _NO_SECONDARY


def type_label(slot_value: str) -> str:
    return "none" if slot_value == _NO_SECONDARY else slot_value


def compare_guess(target: Pokemon, guess: Pokemon) -> dict[str, str]:
    def cmp_numeric(g: int, t: int) -> str:
        if g == t:
            return "equal"
        return "higher" if g < t else "lower"

    t1, t2 = type_slot(target, 0), type_slot(target, 1)
    g1, g2 = type_slot(guess, 0), type_slot(guess, 1)

    return {
        "generation": cmp_numeric(guess.generation, target.generation),
        "height": cmp_numeric(guess.height_dm, target.height_dm),
        "weight": cmp_numeric(guess.weight_hg, target.weight_hg),
        "bst": cmp_numeric(guess.bst, target.bst),
        "type_1": "correct" if g1 == t1 else "incorrect",
        "type_2": "correct" if g2 == t2 else "incorrect",
        "guess_type_1": type_label(g1),
        "guess_type_2": type_label(g2),
        "type_2_matches_answer_type_1": "yes" if g2 != _NO_SECONDARY and g2 == t1 else "no",
        "type_1_matches_answer_type_2": "yes" if t2 != _NO_SECONDARY and g1 == t2 else "no",
    }


def format_squirdle_feedback(feedback: dict[str, str]) -> str:
    lines = [
        f"Generation: {feedback['generation']}",
        f"Height: {feedback['height']}",
        f"Weight: {feedback['weight']}",
        f"BST: {feedback['bst']}",
        f"Type (1st slot): {feedback['type_1']} (you guessed: {feedback['guess_type_1']})",
        f"Type (2nd slot): {feedback['type_2']} (you guessed: {feedback['guess_type_2']})",
    ]
    if feedback.get("type_2_matches_answer_type_1") == "yes":
        lines.append("Hint: your 2nd type matches the answer's 1st type.")
    if feedback.get("type_1_matches_answer_type_2") == "yes":
        lines.append("Hint: your 1st type matches the answer's 2nd type.")
    return "\n".join(lines)
