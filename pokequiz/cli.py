from __future__ import annotations

import random

from pokequiz.data import load_dex
from pokequiz.games.ability_assessor import ability_profile_for_name, display_ability_name, profile_matches
from pokequiz.games.daycare_detective import daycare_profile_for_name, gender_rate_label
from pokequiz.games.dexacted import dex_entries_for_name
from pokequiz.games.evolutionary_enigma import (
    build_challenge as build_evolution_enigma_challenge,
    details_signature as evolution_details_signature,
    guess_matches_signature,
)
from pokequiz.games.level_ladder import display_move_name as display_level_move_name
from pokequiz.games.level_ladder import level_up_moves_for_name
from pokequiz.games.movepool_madness import build_challenge, display_move_name, guess_satisfies_moves, legal_moves_for_name
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


def _settings_summary(settings: GameSettings) -> str:
    gens = "all" if settings.allowed_generations is None else ",".join(str(g) for g in sorted(settings.allowed_generations))
    return f"megas={'on' if settings.allow_megas else 'off'} | regionals={'on' if settings.allow_regionals else 'off'} | gens={gens}"


def run_pokedoku(settings: GameSettings) -> None:
    dex = load_dex()
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


def run_squirdle(settings: GameSettings) -> None:
    dex = load_dex()
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


def run_stat_quiz(settings: GameSettings) -> None:
    global LAST_STAT_QUIZ

    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return

    mon = random.choice(pool)
    if LAST_STAT_QUIZ and len(pool) > 1 and mon.name == LAST_STAT_QUIZ:
        alternatives = [p for p in pool if p.name != LAST_STAT_QUIZ]
        mon = random.choice(alternatives)
    LAST_STAT_QUIZ = mon.name
    max_guesses = _input_guess_count("How many guesses for Pokedentities?", 3)

    print("Pokedentities: identify this Pokémon from stats:")
    print(prompt_for_mon(mon))
    seen_guesses: set[str] = set()
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
            if guessed_mon.name in seen_guesses:
                print(f'You already guessed "{guessed_mon.name}". Try a different Pokémon.')
                continue
            seen_guesses.add(guessed_mon.name)
            break
        if is_correct_guess(mon, guess):
            print("Correct!")
            return
        if hint_turn is not None and tries == hint_turn:
            print(f"Hint: types={','.join(mon.types)} generation={mon.generation}")
    print(f"Nope. It was {mon.name}.")


def run_whos_that_pokemon(settings: GameSettings) -> None:
    dex = load_dex()
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


def run_statle(settings: GameSettings) -> None:
    dex = load_dex()
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


def run_dexacted(settings: GameSettings) -> None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return

    target = random.choice(pool)
    entries = list(dex_entries_for_name(target.name))
    if not entries:
        print("No dex entries available for that Pokémon right now. Try another round.")
        return
    random.shuffle(entries)

    revealed = 1
    print("Dexacted mode: guess the Pokémon from Pokédex entries.")
    print("Commands: entry (reveal another entry), quit (leave game), or type a Pokémon guess.")
    print(f"\nEntry 1/{len(entries)}: {entries[0]}")

    while True:
        raw = input("Dexacted> ").strip()
        if not raw:
            print("Input cannot be blank.")
            continue
        command = raw.casefold()
        if command in {"quit", "q", "exit"}:
            print(f"Leaving Dexacted. The answer was {target.name}.")
            return
        if command in {"entry", "e", "next", "hint"}:
            if revealed >= len(entries):
                print("No more dex entries available.")
            else:
                print(f"Entry {revealed + 1}/{len(entries)}: {entries[revealed]}")
                revealed += 1
            continue

        guess = dex.by_name(raw)
        if not guess:
            print(f'Unknown Pokémon: "{raw}"')
            continue
        if guess.name == target.name:
            print("Correct!")
            return
        if revealed >= len(entries):
            print(f"Wrong guess and no entries left. You lose. It was {target.name}.")
            return
        print("Nope. Ask for another entry or guess again.")


def run_movepool_madness(settings: GameSettings) -> None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return

    try:
        target, required_moves = build_challenge(pool)
    except ValueError as err:
        print(err)
        return

    max_guesses = _input_guess_count("How many guesses for Movepool Madness?", 5)
    print("Movepool Madness: name any Pokémon that can legally learn ALL four moves.")
    print("(Legal methods: level-up, TM/machine, or egg/breeding.)")
    for idx, move in enumerate(required_moves, start=1):
        print(f"{idx}) {display_move_name(move)}")

    seen_guesses: set[str] = set()
    turn = 1
    while turn <= max_guesses:
        raw = input(f"Guess {turn}/{max_guesses} (or 'quit'): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            print(f"Leaving Movepool Madness. One valid answer was {target.name}.")
            return

        guess = dex.by_name(raw)
        if not guess:
            print(f'Unknown Pokémon: "{raw}"')
            continue
        if not settings.accepts(guess):
            print("That Pokémon is outside your current generation/variant filters.")
            continue
        if guess.name in seen_guesses:
            print(f'You already guessed "{guess.name}". Try a different Pokémon.')
            continue
        seen_guesses.add(guess.name)

        try:
            if guess_satisfies_moves(guess.name, required_moves):
                print(f"Correct! {guess.name} can learn all four.")
                return
            learned = set(legal_moves_for_name(guess.name))
            missing = [display_move_name(m) for m in required_moves if m not in learned]
            if missing:
                print(f"Nope. {guess.name} is missing: {', '.join(missing)}")
            else:
                print(f"Nope. {guess.name} does not satisfy the four-move requirement.")
            turn += 1
        except Exception:
            print("Could not validate that guess right now (API issue). Try again.")

    print(f"Out of guesses. One valid answer was {target.name}.")


def run_daycare_detective(settings: GameSettings) -> None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return

    target = random.choice(pool)
    try:
        profile = daycare_profile_for_name(target.name)
    except Exception:
        print("Could not load daycare profile data right now (API issue).")
        return

    max_guesses = _input_guess_count("How many guesses for Daycare Detective?", 5)
    print("Daycare Detective: identify the Pokémon from breeding/species profile data.")
    print(f"Clue 1 - Egg Groups: {', '.join(profile.egg_groups) if profile.egg_groups else 'Unknown'}")
    print(f"Clue 2 - Gender Ratio: {gender_rate_label(profile.gender_rate)}")
    print(f"Clue 3 - Hatch Counter: {profile.hatch_counter}")
    print(f"Clue 4 - Capture Rate: {profile.capture_rate}")

    seen_guesses: set[str] = set()
    turn = 1
    while turn <= max_guesses:
        raw = input(f"Guess {turn}/{max_guesses} (or 'quit'): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            print(f"Leaving Daycare Detective. The answer was {target.name}.")
            return

        guess = dex.by_name(raw)
        if not guess:
            print(f'Unknown Pokémon: "{raw}"')
            continue
        if not settings.accepts(guess):
            print("That Pokémon is outside your current generation/variant filters.")
            continue
        if guess.name in seen_guesses:
            print(f'You already guessed "{guess.name}". Try a different Pokémon.')
            continue
        seen_guesses.add(guess.name)

        if guess.name == target.name:
            print("Correct!")
            return
        print("Nope.")
        turn += 1

    print(f"Out of guesses. It was {target.name}.")


def run_evolutionary_enigma(settings: GameSettings) -> None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return

    try:
        edge, clues = build_evolution_enigma_challenge([p.name for p in pool])
    except ValueError as err:
        print(err)
        return
    signature = evolution_details_signature(edge.details)

    max_guesses = _input_guess_count("How many guesses for Evolutionary Enigma?", 5)
    print("Evolutionary Enigma: deduce the evolution pair from trigger clues.")
    print("You can answer with either the Pokémon evolving from this condition OR evolving into it.")
    print("Commands: clue (reveal next clue), quit")

    revealed = 1
    print(f"\nClue 1/{len(clues)}: {clues[0]}")
    seen_guesses: set[str] = set()
    turn = 1
    while turn <= max_guesses:
        raw = input(f"Guess {turn}/{max_guesses} (or command): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        cmd = raw.casefold()
        if cmd in {"quit", "q", "exit"}:
            print(f"Leaving Evolutionary Enigma. This clue profile included {edge.from_name} -> {edge.to_name}.")
            return
        if cmd in {"clue", "c", "hint"}:
            if revealed >= len(clues):
                print("No more clues to reveal.")
            else:
                print(f"Clue {revealed + 1}/{len(clues)}: {clues[revealed]}")
                revealed += 1
            continue

        guess = dex.by_name(raw)
        if not guess:
            print(f'Unknown Pokémon: "{raw}"')
            continue
        if not settings.accepts(guess):
            print("That Pokémon is outside your current generation/variant filters.")
            continue
        if guess.name in seen_guesses:
            print(f'You already guessed "{guess.name}". Try a different Pokémon.')
            continue
        seen_guesses.add(guess.name)

        if guess_matches_signature(guess.name, signature):
            print(f"Correct! This clue describes {edge.from_name} evolving into {edge.to_name}.")
            return

        print("Nope.")
        turn += 1

    print(f"Out of guesses. This clue profile included {edge.from_name} -> {edge.to_name}.")


def run_ability_assessor(settings: GameSettings) -> None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return

    target = random.choice(pool)
    try:
        profile = ability_profile_for_name(target.name)
    except Exception:
        print("Could not load ability data right now (API issue).")
        return

    # Build clue set from available abilities only, then reveal one-by-one.
    clues: list[str] = []
    if profile.ability_1:
        clues.append(f"Ability 1: {display_ability_name(profile.ability_1)}")
    if profile.hidden_ability:
        clues.append(f"Hidden Ability: {display_ability_name(profile.hidden_ability)}")
    if profile.ability_2:
        clues.append(f"Ability 2: {display_ability_name(profile.ability_2)}")
    if not clues:
        print("This Pokémon has no usable ability profile for this mode. Try again.")
        return
    random.shuffle(clues)

    max_guesses = _input_guess_count("How many guesses for Ability Assessor?", 5)
    print("Ability Assessor: guess a Pokémon matching this ability combination.")
    print("Commands: clue (reveal next clue), quit")
    revealed = 1
    print(f"\nClue 1/{len(clues)}: {clues[0]}")

    seen_guesses: set[str] = set()
    turn = 1
    while turn <= max_guesses:
        raw = input(f"Guess {turn}/{max_guesses} (or command): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        cmd = raw.casefold()
        if cmd in {"quit", "q", "exit"}:
            print(
                "Leaving Ability Assessor. One matching profile was: "
                f"{target.name} ({', '.join(clues)})."
            )
            return
        if cmd in {"clue", "c", "hint"}:
            if revealed >= len(clues):
                print("No more clues to reveal.")
            else:
                print(f"Clue {revealed + 1}/{len(clues)}: {clues[revealed]}")
                revealed += 1
            continue

        guess = dex.by_name(raw)
        if not guess:
            print(f'Unknown Pokémon: "{raw}"')
            continue
        if not settings.accepts(guess):
            print("That Pokémon is outside your current generation/variant filters.")
            continue
        if guess.name in seen_guesses:
            print(f'You already guessed "{guess.name}". Try a different Pokémon.')
            continue
        seen_guesses.add(guess.name)

        try:
            g_profile = ability_profile_for_name(guess.name)
        except Exception:
            print("Could not validate that guess right now (API issue). Try again.")
            continue

        if profile_matches(
            g_profile,
            ability_1=profile.ability_1,
            ability_2=profile.ability_2,
            hidden_ability=profile.hidden_ability,
        ):
            print(f"Correct! {guess.name} matches this ability profile.")
            return

        print("Nope.")
        turn += 1

    print(f"Out of guesses. One matching profile was {target.name}.")


def run_level_ladder(settings: GameSettings) -> None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return

    # Find a target that has enough level-up moves to make clue progression meaningful.
    candidates = pool[:]
    random.shuffle(candidates)
    target = None
    moves: list[tuple[int, str]] = []
    for mon in candidates:
        try:
            lm = list(level_up_moves_for_name(mon.name))
        except Exception:
            continue
        if len(lm) >= 3:
            target = mon
            moves = lm
            break
    if target is None:
        print("Could not find enough level-up learnset data for this filter set.")
        return

    reverse_mode = _input_bool("Use reverse mode (show highest-level moves first)?", False)
    ordered = list(reversed(moves)) if reverse_mode else moves
    clues = [f"Level {lvl}: {display_level_move_name(move)}" for lvl, move in ordered]

    max_guesses = _input_guess_count("How many guesses for Level Ladder?", 5)
    print("Level Ladder: deduce the Pokémon from its level-up learnset clues.")
    print("Commands: clue (reveal next clue), quit")
    print(f"\nHint 1/{len(clues)}: {clues[0]}")
    revealed = 1

    seen_guesses: set[str] = set()
    turn = 1
    while turn <= max_guesses:
        raw = input(f"Guess {turn}/{max_guesses} (or command): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        cmd = raw.casefold()
        if cmd in {"quit", "q", "exit"}:
            print(f"Leaving Level Ladder. The answer was {target.name}.")
            return
        if cmd in {"clue", "c", "hint"}:
            if revealed >= len(clues):
                print("No more hints to reveal.")
            else:
                print(f"Hint {revealed + 1}/{len(clues)}: {clues[revealed]}")
                revealed += 1
            continue

        guess = dex.by_name(raw)
        if not guess:
            print(f'Unknown Pokémon: "{raw}"')
            continue
        if not settings.accepts(guess):
            print("That Pokémon is outside your current generation/variant filters.")
            continue
        if guess.name in seen_guesses:
            print(f'You already guessed "{guess.name}". Try a different Pokémon.')
            continue
        seen_guesses.add(guess.name)

        try:
            guess_moves = list(level_up_moves_for_name(guess.name))
        except Exception:
            print("Could not validate that guess right now (API issue). Try again.")
            continue
        guess_ordered = list(reversed(guess_moves)) if reverse_mode else guess_moves
        target_revealed = ordered[:revealed]
        guess_revealed = guess_ordered[:revealed]
        if len(guess_revealed) == len(target_revealed) and guess_revealed == target_revealed:
            print(f"Correct! {guess.name} matches the revealed Level Ladder sequence.")
            return
        print("Nope.")
        turn += 1

    print(f"Out of guesses. It was {target.name}.")


def main() -> None:
    settings = GameSettings()
    while True:
        print("\n=== PokeQuiz ===")
        print(f"Global settings: {_settings_summary(settings)}")
        print("Choose quiz mode:")
        print("1) Pokedoku")
        print("2) Squirdle")
        print("3) Pokedentities")
        print("4) Statle")
        print("5) Who's that Pokemon!?")
        print("6) Dexacted")
        print("7) Movepool Madness")
        print("8) Daycare Detective")
        print("9) Evolutionary Enigma")
        print("10) Ability Assessor")
        print("11) Level Ladder")
        print("12) Settings")
        print("13) Quit")
        choice = input("> ").strip()
        if choice == "1":
            run_pokedoku(settings)
        elif choice == "2":
            run_squirdle(settings)
        elif choice == "3":
            run_stat_quiz(settings)
        elif choice == "4":
            run_statle(settings)
        elif choice == "5":
            run_whos_that_pokemon(settings)
        elif choice == "6":
            run_dexacted(settings)
        elif choice == "7":
            run_movepool_madness(settings)
        elif choice == "8":
            run_daycare_detective(settings)
        elif choice == "9":
            run_evolutionary_enigma(settings)
        elif choice == "10":
            run_ability_assessor(settings)
        elif choice == "11":
            run_level_ladder(settings)
        elif choice == "12":
            settings = _settings_menu()
            print(f"Updated settings: {_settings_summary(settings)}")
        elif choice == "13":
            break
        else:
            print("Unknown choice.")


if __name__ == "__main__":
    main()
