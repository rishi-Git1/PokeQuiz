from __future__ import annotations

import random

from pokequiz.data import load_dex
from pokequiz.games.pokedoku import custom_constraints, random_constraints, validate_grid_answers
from pokequiz.games.squirdle import compare_guess
from pokequiz.games.stat_quiz import is_correct_guess, prompt_for_mon
from pokequiz.games.statle import STAT_LABELS, remaining_stats, resolve_turn, total_score
from pokequiz.models import GameSettings

LAST_STAT_QUIZ: str | None = None


def _input_bool(prompt: str, default: bool = True) -> bool:
    raw = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes"}


def _settings_menu() -> GameSettings:
    allow_megas = _input_bool("Allow Mega forms? (count as Gen 6)", True)
    allow_regionals = _input_bool("Allow regional variants? (count as their debut gen)", True)
    gens_raw = input("Allowed generations (comma-separated, blank=all): ").strip()
    gens = None
    if gens_raw:
        gens = {int(g.strip()) for g in gens_raw.split(",") if g.strip()}
    return GameSettings(allow_megas=allow_megas, allow_regionals=allow_regionals, allowed_generations=gens)


def run_pokedoku() -> None:
    dex = load_dex()
    settings = _settings_menu()
    custom = _input_bool("Build a custom Pokedoku grid?", False)
    if custom:
        print("Enter 3 row constraints and 3 column constraints as kind:value (kind in type,generation,mega,regional).")
        rows = [input(f"Row {i+1}: ") for i in range(3)]
        cols = [input(f"Col {i+1}: ") for i in range(3)]
        row_constraints, col_constraints = custom_constraints(rows, cols)
    else:
        row_constraints, col_constraints = random_constraints(dex, settings)

    print("Rows:", [r.label for r in row_constraints])
    print("Cols:", [c.label for c in col_constraints])

    answers: list[list[str]] = []
    for r_idx in range(3):
        row: list[str] = []
        for c_idx in range(3):
            row.append(input(f"Cell ({r_idx+1},{c_idx+1}): "))
        answers.append(row)

    score, marks, warning = validate_grid_answers(dex, row_constraints, col_constraints, answers, settings)
    print(f"Score: {score}/9")
    for row in marks:
        print(" ".join("✅" if m else "❌" for m in row))
    if warning:
        print(warning)


def run_squirdle() -> None:
    dex = load_dex()
    settings = _settings_menu()
    pool = dex.filtered(settings)
    target = random.choice(pool)
    print("Guess the Pokémon. You get 8 guesses.")
    for turn in range(1, 9):
        guess_name = input(f"Guess {turn}: ").strip()
        guess = dex.by_name(guess_name)
        if not guess:
            print("Unknown Pokémon.")
            continue
        if not settings.accepts(guess):
            print("That Pokémon is outside your current generation/variant filters.")
            continue
        if guess.name == target.name:
            print("Correct!")
            return
        feedback = compare_guess(target, guess)
        print(feedback)
    print(f"Out of guesses. Target was {target.name}.")


def run_stat_quiz() -> None:
    global LAST_STAT_QUIZ

    dex = load_dex()
    settings = _settings_menu()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return

    mon = random.choice(pool)
    if LAST_STAT_QUIZ and len(pool) > 1 and mon.name == LAST_STAT_QUIZ:
        alternatives = [p for p in pool if p.name != LAST_STAT_QUIZ]
        mon = random.choice(alternatives)
    LAST_STAT_QUIZ = mon.name

    print("Identify this Pokémon from stats:")
    print(prompt_for_mon(mon))
    for tries in range(1, 4):
        guess = input(f"Guess {tries}/3: ")
        if is_correct_guess(mon, guess):
            print("Correct!")
            return
        if tries == 2:
            print(f"Hint: types={','.join(mon.types)} generation={mon.generation}")
    print(f"Nope. It was {mon.name}.")


def run_statle() -> None:
    dex = load_dex()
    settings = _settings_menu()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return

    picked_stats: list[str] = []
    results = []
    print("Statle mode: each round a random Pokémon is shown; pick one unused stat to score.")
    while True:
        available = remaining_stats(picked_stats)
        if not available:
            break

        mon = random.choice(pool)
        round_no = len(picked_stats) + 1
        print(f"\nRound {round_no}/6: {mon.name}")
        print("Choose one remaining stat:")
        for idx, stat in enumerate(available, start=1):
            print(f"{idx}) {STAT_LABELS[stat]}")

        raw_pick = input("> ").strip()
        if raw_pick.isdigit() and 1 <= int(raw_pick) <= len(available):
            stat = available[int(raw_pick) - 1]
        else:
            stat = raw_pick.casefold().replace(" ", "_")
            if stat not in available:
                print(f"Invalid or already-used stat; defaulting to {STAT_LABELS[available[0]]}.")
                stat = available[0]

        picked_stats.append(stat)
        result = resolve_turn(mon, stat)
        results.append(result)
        print(f"{STAT_LABELS[result.stat]} = {result.value}")
        print(f"Running total: {total_score(results)}")

    print(f"\nFinal total: {total_score(results)}")


def main() -> None:
    while True:
        print("\n=== PokeQuiz ===")
        print("Choose quiz mode:")
        print("1) Pokedoku")
        print("2) Squirdle")
        print("3) Stat identity quiz")
        print("4) Statle builder")
        print("5) Quit")
        choice = input("> ").strip()
        if choice == "1":
            run_pokedoku()
        elif choice == "2":
            run_squirdle()
        elif choice == "3":
            run_stat_quiz()
        elif choice == "4":
            run_statle()
        elif choice == "5":
            break
        else:
            print("Unknown choice.")


if __name__ == "__main__":
    main()
