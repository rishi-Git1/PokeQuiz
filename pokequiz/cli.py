from __future__ import annotations

import random

from pokequiz.data import load_dex
from pokequiz.games.ability_assessor import ability_profile_for_name, display_ability_name, profile_matches
from pokequiz.games.category_quiz import clue_lines as category_clue_lines
from pokequiz.games.category_quiz import matches_on_shown_clues as category_matches_on_shown_clues
from pokequiz.games.category_quiz import profile_for_name as category_profile_for_name
from pokequiz.games.daycare_detective import daycare_profile_for_name, gender_rate_label
from pokequiz.games.defensive_profile import defensive_types_for_name, grouped_multiplier_clues
from pokequiz.games.dexacted import dex_entries_for_name
from pokequiz.games.evolutionary_enigma import (
    build_challenge as build_evolution_enigma_challenge,
    details_signature as evolution_details_signature,
    guess_matches_signature,
)
from pokequiz.games.level_ladder import display_move_name as display_level_move_name
from pokequiz.games.level_ladder import level_up_moves_for_name
from pokequiz.games.level_race import build_challenge as build_level_race_challenge
from pokequiz.games.level_race import display_move_name as display_level_race_move_name
from pokequiz.games.movepool_madness import build_challenge, display_move_name, guess_satisfies_moves, legal_moves_for_name
from pokequiz.games.odd_one_out import build_challenge as build_odd_one_out_challenge
from pokequiz.games.pokedoku import (
    custom_constraints,
    format_pokedoku_grid,
    random_constraints,
    validate_grid_answers,
)
from pokequiz.games.safari_zone import encounter_clues_for_name
from pokequiz.games.squirdle import compare_guess, format_squirdle_feedback
from pokequiz.games.stat_quiz import is_correct_guess, prompt_for_mon
from pokequiz.games.thiefs_target import held_item_profile_for_name, profile_clues as thief_profile_clues
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


def run_defensive_profile(settings: GameSettings) -> None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return

    target = random.choice(pool)
    try:
        target_types = defensive_types_for_name(target.name)
        clues = grouped_multiplier_clues(target_types)
    except Exception:
        print("Could not load type-defense data right now (API issue).")
        return

    if not clues:
        print("No defensive clue data was available for this target. Try another round.")
        return

    max_guesses = _input_guess_count("How many guesses for Defensive Profile?", 5)
    print("Defensive Profile: guess a Pokémon that matches this defensive profile.")
    print("All clues are shown at the start.")
    for idx, clue in enumerate(clues, start=1):
        print(f"Clue {idx}: {clue}")

    seen_guesses: set[str] = set()
    turn = 1
    while turn <= max_guesses:
        raw = input(f"Guess {turn}/{max_guesses} (or 'quit'): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            print(
                "Leaving Defensive Profile. "
                f"One matching type combo was {'/'.join(t.title() for t in target_types)} "
                f"(example: {target.name})."
            )
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
            g_types = defensive_types_for_name(guess.name)
        except Exception:
            print("Could not validate that guess right now (API issue). Try again.")
            continue

        if g_types == target_types:
            print(f"Correct! {guess.name} matches this defensive profile.")
            return

        print("Nope.")
        turn += 1

    print(
        "Out of guesses. "
        f"One matching type combo was {'/'.join(t.title() for t in target_types)} "
        f"(example: {target.name})."
    )


def run_safari_zone(settings: GameSettings) -> None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return

    candidates = pool[:]
    random.shuffle(candidates)
    target = None
    target_clues: list[str] = []
    for mon in candidates:
        try:
            clues = list(encounter_clues_for_name(mon.name))
        except Exception:
            continue
        if clues:
            target = mon
            target_clues = clues
            break
    if target is None:
        print("Could not find encounter/location clue data for this filter set.")
        return

    random.shuffle(target_clues)
    max_guesses = _input_guess_count("How many guesses for Safari Zone?", 5)
    print("Safari Zone: guess a Pokémon from wild encounter location/method clues.")
    print("Commands: clue (reveal next clue), quit")
    revealed = 1
    print(f"\nClue 1/{len(target_clues)}: {target_clues[0]}")

    seen_guesses: set[str] = set()
    turn = 1
    revealed_set = set(target_clues[:revealed])
    while turn <= max_guesses:
        raw = input(f"Guess {turn}/{max_guesses} (or command): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        cmd = raw.casefold()
        if cmd in {"quit", "q", "exit"}:
            print(f"Leaving Safari Zone. One matching answer was {target.name}.")
            return
        if cmd in {"clue", "c", "hint"}:
            if revealed >= len(target_clues):
                print("No more clues to reveal.")
            else:
                print(f"Clue {revealed + 1}/{len(target_clues)}: {target_clues[revealed]}")
                revealed += 1
                revealed_set = set(target_clues[:revealed])
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
            guess_clues = set(encounter_clues_for_name(guess.name))
        except Exception:
            print("Could not validate that guess right now (API issue). Try again.")
            continue

        if revealed_set.issubset(guess_clues):
            print(f"Correct! {guess.name} matches the revealed Safari Zone clues.")
            return

        print("Nope.")
        turn += 1

    print(f"Out of guesses. One matching answer was {target.name}.")


def run_thiefs_target(settings: GameSettings) -> None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return

    candidates = pool[:]
    random.shuffle(candidates)
    target = None
    profile: tuple[tuple[str, int], ...] = tuple()
    for mon in candidates:
        try:
            p = held_item_profile_for_name(mon.name)
        except Exception:
            continue
        if p:
            target = mon
            profile = p
            break
    if target is None:
        print("Could not find held-item data for this filter set.")
        return

    clues = thief_profile_clues(profile)
    max_guesses = _input_guess_count("How many guesses for Thief's Target?", 5)
    print("Thief's Target: guess a Pokémon matching this wild held-item profile.")
    print("All clues are shown at the start.")
    for idx, clue in enumerate(clues, start=1):
        print(f"Clue {idx}: {clue}")

    seen_guesses: set[str] = set()
    turn = 1
    while turn <= max_guesses:
        raw = input(f"Guess {turn}/{max_guesses} (or 'quit'): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            print(f"Leaving Thief's Target. One matching answer was {target.name}.")
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
            guess_profile = held_item_profile_for_name(guess.name)
        except Exception:
            print("Could not validate that guess right now (API issue). Try again.")
            continue
        if guess_profile == profile:
            print(f"Correct! {guess.name} matches this held-item profile.")
            return

        print("Nope.")
        turn += 1

    print(f"Out of guesses. One matching answer was {target.name}.")


def run_odd_one_out(settings: GameSettings) -> None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if len(pool) < 3:
        print("Not enough Pokémon in current filter for Ugly Ducklett.")
        return

    while True:
        raw_count = input("How many Pokémon in this round? (min 3, max 8, default 4): ").strip()
        if not raw_count:
            total_choices = 4
            break
        if raw_count.isdigit() and 3 <= int(raw_count) <= 8:
            total_choices = int(raw_count)
            break
        print("Enter a whole number from 3 to 8.")

    max_guesses = _input_guess_count("How many guesses for Ugly Ducklett?", 1)
    try:
        challenge = build_odd_one_out_challenge(pool, total_choices=total_choices)
    except ValueError as err:
        print(err)
        return

    print("Ugly Ducklett: exactly one Pokémon does NOT share the hidden trait.")
    print("Pick by number or by Pokémon name. Commands: quit")
    for i, name in enumerate(challenge.names, start=1):
        print(f"{i}) {name}")

    seen_choices: set[int] = set()
    turn = 1
    while turn <= max_guesses:
        raw = input(f"Pick odd one out ({turn}/{max_guesses}): ").strip()
        if not raw:
            print("Input cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            odd_name = challenge.names[challenge.odd_index]
            print(f"Leaving Ugly Ducklett. Odd one was {odd_name}. Shared trait was {challenge.trait_explanation}.")
            return

        picked_index: int | None = None
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(challenge.names):
                picked_index = idx
            else:
                print(f"Pick a number from 1 to {len(challenge.names)}.")
                continue
        else:
            guessed = dex.by_name(raw)
            if not guessed:
                print(f'Unknown Pokémon: "{raw}"')
                continue
            try:
                picked_index = challenge.names.index(guessed.name)
            except ValueError:
                print(f'"{guessed.name}" is not one of the listed options.')
                continue

        if picked_index in seen_choices:
            print("You already picked that option. Try a different one.")
            continue
        seen_choices.add(picked_index)

        if picked_index == challenge.odd_index:
            odd_name = challenge.names[challenge.odd_index]
            print(f"Correct! Odd one was {odd_name}. The others shared: {challenge.trait_explanation}.")
            return

        print("Nope.")
        turn += 1

    odd_name = challenge.names[challenge.odd_index]
    print(f"Out of guesses. Odd one was {odd_name}. Shared trait was {challenge.trait_explanation}.")


def run_category_quiz(settings: GameSettings) -> None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return

    target = random.choice(pool)
    try:
        target_profile = category_profile_for_name(target.name)
    except Exception:
        print("Could not load category/species data right now (API issue).")
        return

    clue_map = {
        "color": f"Color: {target_profile.color}" if target_profile.color else None,
        "egg_groups": f"Egg Groups: {', '.join(target_profile.egg_groups)}" if target_profile.egg_groups else None,
        "types": f"Type(s): {', '.join(target_profile.types)}" if target_profile.types else None,
        "generation": f"Generation: {target_profile.generation}" if target_profile.generation is not None else None,
        "primary_ability": f"Primary Ability: {target_profile.primary_ability}" if target_profile.primary_ability else None,
        "capture_rate_band": f"Capture Rate Band: {target_profile.capture_rate_band}" if target_profile.capture_rate_band else None,
        "weight_band": f"Weight Class: {target_profile.weight_band}" if target_profile.weight_band else None,
        "height_band": f"Height Class: {target_profile.height_band}" if target_profile.height_band else None,
        "starts_with": f"Name starts with: {target_profile.starts_with.upper()}",
        "ends_with": f"Name ends with: {target_profile.ends_with.upper()}",
    }
    revealable_fields = [k for k, v in clue_map.items() if v]
    random.shuffle(revealable_fields)
    shown_fields: set[str] = {"category"}
    shown_clues = [f'Category: "{target_profile.category}"']

    max_guesses = _input_guess_count("How many guesses for Category Quiz?", 5)
    print("Category Quiz: guess a Pokémon from category/species clues.")
    print("Category is always shown. Use 'clue' to pick additional clues manually.")
    print(f"Clue 1: {shown_clues[0]}")

    seen_guesses: set[str] = set()
    turn = 1
    while turn <= max_guesses:
        raw = input(f"Guess {turn}/{max_guesses} (or 'quit'): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            print(f"Leaving Category Quiz. One matching answer was {target.name}.")
            return
        if raw.casefold() in {"clue", "c", "hint"}:
            remaining = [f for f in revealable_fields if f not in shown_fields]
            if not remaining:
                print("No more clues available.")
                continue
            print("Choose a clue to reveal:")
            for idx, field in enumerate(remaining, start=1):
                print(f"{idx}) {field.replace('_', ' ')}")
            pick = input("> ").strip()
            if not pick.isdigit() or not (1 <= int(pick) <= len(remaining)):
                print("Invalid clue selection.")
                continue
            chosen = remaining[int(pick) - 1]
            shown_fields.add(chosen)
            shown_clues.append(str(clue_map[chosen]))
            print(f"Clue {len(shown_clues)}: {clue_map[chosen]}")
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
            g_profile = category_profile_for_name(guess.name)
        except Exception:
            print("Could not validate that guess right now (API issue). Try again.")
            continue

        if category_matches_on_shown_clues(g_profile, target_profile, shown_fields):
            print(f"Correct! {guess.name} fits the shown Category Quiz clues.")
            return

        print("Nope.")
        turn += 1

    print(f"Out of guesses. One matching answer was {target.name}.")


def run_stat_sorter(settings: GameSettings) -> None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if len(pool) < 3:
        print("Not enough Pokémon in current filter for Stat Sorter.")
        return

    max_size = min(8, len(pool))
    while True:
        raw_count = input(f"How many Pokémon to sort? (min 3, max {max_size}, default 3): ").strip()
        if not raw_count:
            pick_count = 3
            break
        if raw_count.isdigit() and 3 <= int(raw_count) <= max_size:
            pick_count = int(raw_count)
            break
        print(f"Enter a whole number from 3 to {max_size}.")

    stat_key_map = {
        "hp": "HP",
        "attack": "Attack",
        "defense": "Defense",
        "special_attack": "Special Attack",
        "special_defense": "Special Defense",
        "speed": "Speed",
    }
    stat_key = random.choice(list(stat_key_map.keys()))
    mons = random.sample(pool, k=pick_count)
    random.shuffle(mons)
    max_guesses = _input_guess_count("How many guesses for Stat Sorter?", 3)

    print(f"Stat Sorter: order these Pokémon by {stat_key_map[stat_key]} (highest to lowest).")
    print("Enter either numbers or names in order, separated by commas/spaces (e.g. '2,1,3').")
    for idx, mon in enumerate(mons, start=1):
        print(f"{idx}) {mon.name}")

    correct_sorted = sorted(mons, key=lambda m: getattr(m, stat_key), reverse=True)
    correct_names = [m.name for m in correct_sorted]
    valid_names = {m.name for m in mons}

    seen_submissions: set[tuple[str, ...]] = set()
    turn = 1
    while turn <= max_guesses:
        raw = input(f"Order guess {turn}/{max_guesses} (or 'quit'): ").strip()
        if not raw:
            print("Input cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            pretty = " -> ".join(f"{m.name} ({getattr(m, stat_key)})" for m in correct_sorted)
            print(f"Leaving Stat Sorter. Correct order was: {pretty}")
            return

        parts = [p for p in raw.replace(",", " ").split() if p]
        if len(parts) != len(mons):
            print(f"Enter exactly {len(mons)} entries.")
            continue

        chosen_names: list[str] = []
        bad = False
        for p in parts:
            if p.isdigit():
                idx = int(p)
                if not (1 <= idx <= len(mons)):
                    print(f"Index out of range: {p}")
                    bad = True
                    break
                chosen_names.append(mons[idx - 1].name)
            else:
                guessed = dex.by_name(p)
                if not guessed:
                    print(f'Unknown Pokémon: "{p}"')
                    bad = True
                    break
                if guessed.name not in valid_names:
                    print(f'"{guessed.name}" is not one of the listed Pokémon.')
                    bad = True
                    break
                chosen_names.append(guessed.name)
        if bad:
            continue
        if len(set(chosen_names)) != len(chosen_names):
            print("Do not repeat entries; use each listed Pokémon exactly once.")
            continue

        submission = tuple(chosen_names)
        if submission in seen_submissions:
            print("You already tried that exact order. Try a different one.")
            continue
        seen_submissions.add(submission)

        # Accept ties in any order by checking non-increasing stat values.
        if set(chosen_names) == valid_names:
            vals = [getattr(dex.by_name(n), stat_key) for n in chosen_names]  # type: ignore[arg-type]
            if all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1)):
                pretty = " -> ".join(f"{n} ({getattr(dex.by_name(n), stat_key)})" for n in chosen_names)  # type: ignore[arg-type]
                print(f"Correct! {pretty}")
                return

        print("Nope.")
        turn += 1

    pretty = " -> ".join(f"{m.name} ({getattr(m, stat_key)})" for m in correct_sorted)
    print(f"Out of guesses. Correct order was: {pretty}")


def run_level_race(settings: GameSettings) -> None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if len(pool) < 2:
        print("Not enough Pokémon in current filter for Level Race.")
        return

    max_options = min(5, len(pool))
    while True:
        raw_count = input(f"How many options in Level Race? (min 2, max {max_options}, default 3): ").strip()
        if not raw_count:
            option_count = 3 if max_options >= 3 else max_options
            break
        if raw_count.isdigit() and 2 <= int(raw_count) <= max_options:
            option_count = int(raw_count)
            break
        print(f"Enter a whole number from 2 to {max_options}.")

    try:
        move_name, options = build_level_race_challenge(pool, option_count=option_count)
    except ValueError as err:
        print(err)
        return

    max_guesses = _input_guess_count("How many guesses for Level Race?", 3)
    print("Level Race (Move Learnsets): order these Pokémon by learn level (lowest to highest).")
    print("Enter numbers or names in one line, separated by commas/spaces (e.g. '2,1,3').")
    print(f"Move: {display_level_race_move_name(move_name)}")
    for idx, (mon, _) in enumerate(options, start=1):
        print(f"{idx}) {mon.name}")

    correct_sorted = sorted(options, key=lambda x: x[1])  # low -> high
    correct_names = [m.name for m, _ in correct_sorted]
    option_name_set = {m.name for m, _ in options}
    seen_submissions: set[tuple[str, ...]] = set()

    turn = 1
    while turn <= max_guesses:
        raw = input(f"Order guess {turn}/{max_guesses} (or 'quit'): ").strip()
        if not raw:
            print("Input cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            details = " -> ".join(f"{m.name} (L{lvl})" for m, lvl in correct_sorted)
            print(f"Leaving Level Race. Correct order was: {details}")
            return

        parts = [p for p in raw.replace(",", " ").split() if p]
        if len(parts) != len(options):
            print(f"Enter exactly {len(options)} entries.")
            continue

        chosen_names: list[str] = []
        bad = False
        for p in parts:
            if p.isdigit():
                idx = int(p)
                if not (1 <= idx <= len(options)):
                    print(f"Index out of range: {p}")
                    bad = True
                    break
                chosen_names.append(options[idx - 1][0].name)
            else:
                guessed = dex.by_name(p)
                if not guessed:
                    print(f'Unknown Pokémon: "{p}"')
                    bad = True
                    break
                if guessed.name not in option_name_set:
                    print(f'"{guessed.name}" is not one of the listed options.')
                    bad = True
                    break
                chosen_names.append(guessed.name)
        if bad:
            continue
        if len(set(chosen_names)) != len(chosen_names):
            print("Do not repeat entries; use each listed Pokémon exactly once.")
            continue

        submission = tuple(chosen_names)
        if submission in seen_submissions:
            print("You already tried that exact order. Try a different one.")
            continue
        seen_submissions.add(submission)

        # Accept ties in any order by checking non-decreasing levels.
        if set(chosen_names) == option_name_set:
            lookup = {m.name: lvl for m, lvl in options}
            levels = [lookup[n] for n in chosen_names]
            if all(levels[i] <= levels[i + 1] for i in range(len(levels) - 1)):
                details = " -> ".join(f"{n} (L{lookup[n]})" for n in chosen_names)
                print(f"Correct! {details}")
                return

        print("Nope.")
        turn += 1

    details = " -> ".join(f"{m.name} (L{lvl})" for m, lvl in correct_sorted)
    print(f"Out of guesses. Correct order was: {details}")


def main() -> None:
    settings = GameSettings()
    while True:
        print("\n=== PokeQuiz ===")
        print(f"Global settings: {_settings_summary(settings)}")
        print("Note: type 'settings' to edit filters, or 'quit' to exit.")
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
        print("12) Defensive Profile")
        print("13) Safari Zone")
        print("14) Thief's Target")
        print("15) Ugly Ducklett")
        print("16) Category Quiz")
        print("17) Stat Sorter")
        print("18) Level Race")
        choice = input("> ").strip()
        cmd = choice.casefold()
        if cmd in {"settings", "s"}:
            settings = _settings_menu()
            print(f"Updated settings: {_settings_summary(settings)}")
            continue
        if cmd in {"quit", "q", "exit"}:
            break
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
            run_defensive_profile(settings)
        elif choice == "13":
            run_safari_zone(settings)
        elif choice == "14":
            run_thiefs_target(settings)
        elif choice == "15":
            run_odd_one_out(settings)
        elif choice == "16":
            run_category_quiz(settings)
        elif choice == "17":
            run_stat_sorter(settings)
        elif choice == "18":
            run_level_race(settings)
        else:
            print("Unknown choice.")


if __name__ == "__main__":
    main()
