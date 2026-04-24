from __future__ import annotations

import random

from pokequiz.data import load_dex
from pokequiz.games.pokedoku import (
    custom_constraints,
    format_pokedoku_grid,
    random_constraints,
    validate_grid_answers,
)
from pokequiz.games.squirdle import compare_guess, format_squirdle_feedback
from pokequiz.games.stat_quiz import is_correct_guess, prompt_for_mon
from pokequiz.sprites import print_statle_sprite
from pokequiz.games.statle import (
    STAT_LABELS,
    format_optimal_statle_summary,
    optimal_statle_assignment,
    remaining_stats,
    resolve_turn,
    total_score,
)
from pokequiz.models import GameSettings, Pokemon

LAST_STAT_QUIZ: str | None = None


POKEDOKU_CUSTOM_CONSTRAINT_HELP = (
    "Custom constraint syntax:\n"
    "  kind:value\n"
    "Kinds:\n"
    "  type, generation,\n"
    "  bst-over, bst-under,\n"
    "  height-over, height-under,\n"
    "  weight-over, weight-under,\n"
    "  first-letter, last-letter,\n"
    "  secondary_type-none   (no :value)\n"
    "Examples:\n"
    "  type:fire\n"
    "  generation:3\n"
    "  bst-over:500\n"
    "  first-letter:c\n"
    "  secondary_type-none"
)

POKEDOKU_COMMAND_HELP = (
    "Pokedoku commands:\n"
    "  <row> <col> <name>   set/replace a cell (e.g. 2 3 pikachu)\n"
    "  clear <row> <col>    clear a cell\n"
    "  done                 score the board\n"
    "  help / syntax        show command + constraint syntax"
)


def _input_bool(prompt: str, default: bool = True) -> bool:
    while True:
        raw = input(f"{prompt} [y/n]: ").strip().lower()
        if not raw:
            print("Please enter y/yes or n/no.")
            continue
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Please enter y/yes or n/no.")


def _input_guess_count(prompt: str, default: int) -> int:
    while True:
        raw = input(f"{prompt} [default={default}]: ").strip()
        if not raw:
            return default
        if raw.isdigit() and int(raw) > 0:
            return int(raw)
        print("Please enter a positive whole number.")


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
        print("Enter 3 row constraints and 3 column constraints.")
        print(POKEDOKU_CUSTOM_CONSTRAINT_HELP)
        rows = [input(f"Row {i+1}: ") for i in range(3)]
        cols = [input(f"Col {i+1}: ") for i in range(3)]
        row_constraints, col_constraints = custom_constraints(rows, cols)
    else:
        try:
            row_constraints, col_constraints = random_constraints(dex, settings)
        except ValueError as err:
            print(err)
            return

    answers: list[list[str]] = [["" for _ in range(3)] for _ in range(3)]

    print("\nFill the 3x3 grid. Commands (row and column are 1-3):")
    print(POKEDOKU_COMMAND_HELP)

    while True:
        print()
        print(format_pokedoku_grid(row_constraints, col_constraints, answers))
        raw = input("Pokedoku> ").strip()
        if not raw:
            continue
        parts = raw.split()
        low0 = parts[0].casefold()
        if low0 in ("help", "syntax"):
            print(POKEDOKU_COMMAND_HELP)
            print()
            print(POKEDOKU_CUSTOM_CONSTRAINT_HELP)
            continue
        if low0 == "done":
            break
        if low0 in ("clear", "c", "x") and len(parts) >= 3:
            try:
                r, c = int(parts[1]), int(parts[2])
            except ValueError:
                print("Use: clear <row> <col> with numbers 1-3.")
                continue
            if not (1 <= r <= 3 and 1 <= c <= 3):
                print("Row and column must be between 1 and 3.")
                continue
            answers[r - 1][c - 1] = ""
            continue
        if len(parts) >= 3:
            try:
                r, c = int(parts[0]), int(parts[1])
            except ValueError:
                print("Use: <row> <col> <pokemon name>, or clear/done.")
                continue
            if not (1 <= r <= 3 and 1 <= c <= 3):
                print("Row and column must be between 1 and 3.")
                continue
            name = " ".join(parts[2:]).strip()
            if not name:
                print("Enter a Pokemon name after the row and column.")
                continue
            if not dex.by_name(name):
                print(f'Unknown Pokémon: "{name}"')
                continue
            answers[r - 1][c - 1] = name
            continue
        print("Unrecognized input. Try: 2 1 charizard  |  clear 2 1  |  done")

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
    max_guesses = _input_guess_count("How many guesses for Squirdle?", 8)
    target = random.choice(pool)
    print(f"Guess the Pokémon. You get {max_guesses} guesses.")
    for turn in range(1, max_guesses + 1):
        while True:
            guess_name = input(f"Guess {turn}: ").strip()
            if not guess_name:
                print("Guess cannot be blank.")
                continue
            guess = dex.by_name(guess_name)
            if not guess:
                print(f'Unknown Pokémon: "{guess_name}"')
                continue
            if not settings.accepts(guess):
                print("That Pokémon is outside your current generation/variant filters.")
                continue
            break
        if guess.name == target.name:
            print("Correct!")
            return
        feedback = compare_guess(target, guess)
        print(format_squirdle_feedback(feedback))
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
    max_guesses = _input_guess_count("How many guesses for Stat identity quiz?", 3)

    print("Identify this Pokémon from stats:")
    print(prompt_for_mon(mon))
    hint_turn = max_guesses - 1 if max_guesses > 1 else None
    for tries in range(1, max_guesses + 1):
        while True:
            guess = input(f"Guess {tries}/{max_guesses}: ").strip()
            if not guess:
                print("Guess cannot be blank.")
                continue
            guessed_mon = dex.by_name(guess)
            if not guessed_mon:
                print(f'Unknown Pokémon: "{guess}"')
                continue
            break
        if is_correct_guess(mon, guess):
            print("Correct!")
            return
        if hint_turn is not None and tries == hint_turn:
            print(f"Hint: types={','.join(mon.types)} generation={mon.generation}")
    print(f"Nope. It was {mon.name}.")


def run_whos_that_pokemon() -> None:
    dex = load_dex()
    settings = _settings_menu()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return

    max_guesses = _input_guess_count("How many guesses for Who's that Pokemon!?", 3)
    target = random.choice(pool)

    print("Who's that Pokemon!?")
    print_statle_sprite(target)
    for turn in range(1, max_guesses + 1):
        while True:
            guess_name = input(f"Guess {turn}/{max_guesses}: ").strip()
            if not guess_name:
                print("Guess cannot be blank.")
                continue
            guess = dex.by_name(guess_name)
            if not guess:
                print(f'Unknown Pokémon: "{guess_name}"')
                continue
            break
        if guess.name == target.name:
            print("Correct!")
            return
        print("Nope, try again.")

    print(f"Out of guesses. It was {target.name}.")


def run_statle() -> None:
    dex = load_dex()
    settings = _settings_menu()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return

    picked_stats: list[str] = []
    results = []
    round_mons: list[Pokemon] = []
    print("Statle mode: each round a random Pokémon is shown; pick one unused stat to score.")
    while True:
        available = remaining_stats(picked_stats)
        if not available:
            break

        mon = random.choice(pool)
        round_mons.append(mon)
        round_no = len(picked_stats) + 1
        print(f"\nRound {round_no}/6: {mon.name}")
        print_statle_sprite(mon)
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

    final = total_score(results)
    print(f"\nFinal total: {final}")
    optimal_total, plan = optimal_statle_assignment(round_mons)
    print(format_optimal_statle_summary(round_mons, plan, optimal_total, your_total=final))


def main() -> None:
    while True:
        print("\n=== PokeQuiz ===")
        print("Choose quiz mode:")
        print("1) Pokedoku")
        print("2) Squirdle")
        print("3) Stat identity quiz")
        print("4) Statle builder")
        print("5) Who's that Pokemon!?")
        print("6) Quit")
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
            run_whos_that_pokemon()
        elif choice == "6":
            break
        else:
            print("Unknown choice.")


if __name__ == "__main__":
    main()
