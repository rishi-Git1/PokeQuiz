from __future__ import annotations

import builtins
from typing import Any, Callable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from functools import lru_cache
import random
import re

from pokequiz import bgm
from pokequiz.data import _fetch_json, load_dex, normalize_name
from pokequiz.games.ability_assessor import ability_profile_for_name, display_ability_name, profile_matches
from pokequiz.games.category_quiz import clue_lines as category_clue_lines
from pokequiz.games.category_quiz import matches_on_shown_clues as category_matches_on_shown_clues
from pokequiz.games.category_quiz import profile_for_name as category_profile_for_name
from pokequiz.games.daycare_detective import daycare_profile_for_name, gender_rate_label
from pokequiz.games.defensive_profile import defensive_types_for_name, grouped_multiplier_clues
from pokequiz.games.dexacted import dex_entries_for_name
from pokequiz.games.ev_forensic import ev_yield_line as ev_forensic_ev_yield_line
from pokequiz.games.ev_forensic import profile_for_name as ev_forensic_profile_for_name
from pokequiz.games.dexit import is_correct_guess as dex_it_is_correct
from pokequiz.games.dexit import parse_higher_lower, pick_next_guess, pick_target_and_guess
from pokequiz.games.power_levels import is_correct_guess as power_levels_is_correct
from pokequiz.games.power_levels import pick_next_guess as power_levels_pick_next
from pokequiz.games.power_levels import pick_target_and_guess as power_levels_pick_pair
from pokequiz.games.ability_effects import ability_slug_from_user_guess, build_challenge as build_ability_effects_challenge
from pokequiz.games.ability_effects import ensure_ability_guess_index, redact_for_ability
from pokequiz.games.item_lore import build_challenge as build_item_lore_challenge
from pokequiz.games.item_lore import (
    display_item_name,
    ensure_item_guess_index,
    item_slug_from_user_guess,
    redact_for_item,
)
from pokequiz.games.move_match import (
    build_challenge as build_move_match_challenge,
    display_move_name as display_move_match_name,
    ensure_move_guess_index,
    move_slug_from_user_guess,
    redact_for_move,
)
from pokequiz.games.machine_serial import build_challenge as build_machine_serial_challenge
from pokequiz.games.fling_force import (
    build_challenge as build_fling_force_challenge,
    clue_line as fling_force_clue_line,
    parse_guess as fling_force_parse_guess,
    reveal_answer_line as fling_force_reveal_answer_line,
)
from pokequiz.games.all_natural import (
    build_challenge as build_all_natural_challenge,
    display_berry_name,
    display_type_name as display_natural_gift_type_name,
    parse_guess as all_natural_parse_guess,
)
from pokequiz.games.environment_map import (
    build_challenge as build_environment_map_challenge,
    parse_guess as environment_map_parse_guess,
    reveal_answer_line as environment_map_reveal_answer_line,
)
from pokequiz.games.method_man import (
    build_challenge as build_method_man_challenge,
    display_method_name as display_method_man_method_name,
    parse_method_guess as method_man_parse_method_guess,
)
from pokequiz.games.exp_yield import build_challenge as build_exp_yield_challenge
from pokequiz.games.exp_yield import letter_labels, pick_help_line, prompt_line as exp_yield_prompt_line
from pokequiz.games.exp_yield import resolve_pick as exp_yield_resolve_pick
from pokequiz.games.exp_yield import reveal_line as exp_yield_reveal_line
from pokequiz.games.growth_rate_guess import build_challenge as build_growth_rate_challenge
from pokequiz.games.growth_rate_guess import (
    describe_order,
    format_option_summary,
    parse_ranking_line,
    question_line,
)
from pokequiz.games.evolutionary_enigma import (
    build_challenge as build_evolution_enigma_challenge,
    details_signature as evolution_details_signature,
    guess_matches_signature,
)
from pokequiz.games.international_names import CLUE_LANGUAGES, names_by_language, romanized_japanese_name
from pokequiz.games.level_ladder import display_move_name as display_level_move_name
from pokequiz.games.level_ladder import level_up_moves_for_name
from pokequiz.games.level_race import build_challenge as build_level_race_challenge
from pokequiz.games.level_race import display_move_name as display_level_race_move_name
from pokequiz.games.missing_link import build_challenge as build_missing_link_challenge
from pokequiz.games.missing_link import move_info as missing_link_move_info
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
# Best correct streak in DexIt (mode 24) for this process; resets when the app exits.
_DEX_IT_SESSION_BEST: int = 0
# Best correct streak in Power Levels (mode 25) for this process; resets when the app exits.
_POWER_LEVELS_SESSION_BEST: int = 0
_TYPE_COLOR_PATCHED = False
_PLAIN_TERMINAL_PRINT: Callable[..., None] = builtins.print

_MENU_RESET = "\x1b[0m"

# When False, patched print skips type coloring and _color_move_name returns plain text.
# Use in modes whose strings are locations, dex flavor, items, etc. (not type/move trivia).
_GAME_OUTPUT_COLORS: ContextVar[bool] = ContextVar("game_output_colors", default=True)


def _game_output_colors_enabled() -> bool:
    return _GAME_OUTPUT_COLORS.get()


@contextmanager
def _plain_game_output():
    token = _GAME_OUTPUT_COLORS.set(False)
    try:
        yield
    finally:
        _GAME_OUTPUT_COLORS.reset(token)

TYPE_HEX_COLORS = {
    "bug": "#94bc4a",
    "dark": "#736c75",
    "dragon": "#6a7baf",
    "electric": "#e5c531",
    "fairy": "#e397d1",
    "fighting": "#cb5f48",
    "fire": "#ea7a3c",
    "flying": "#7da6de",
    "ghost": "#846ab6",
    "grass": "#71c558",
    "ground": "#cc9f4f",
    "ice": "#70cbd4",
    "normal": "#aab09f",
    "poison": "#b468b7",
    "psychic": "#e5709b",
    "rock": "#b2a061",
    "steel": "#89a1b0",
    "water": "#539ae2",
}
_TYPE_PATTERN = re.compile(r"\b(" + "|".join(sorted(TYPE_HEX_COLORS.keys(), key=len, reverse=True)) + r")\b", re.IGNORECASE)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _colorize_types_in_text(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        raw = match.group(0)
        rgb = _hex_to_rgb(TYPE_HEX_COLORS[raw.casefold()])
        return f"\x1b[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m{raw}\x1b[0m"

    return _TYPE_PATTERN.sub(repl, text)


@lru_cache(maxsize=4096)
def _move_type_name(move_name: str) -> str | None:
    try:
        payload = _fetch_json(f"https://pokeapi.co/api/v2/move/{normalize_name(move_name)}")
        t = payload.get("type", {}).get("name")
        return str(t).casefold() if t else None
    except Exception:
        return None


def _color_move_name(move_display_name: str, *, move_slug: str | None = None) -> str:
    if not _game_output_colors_enabled():
        return move_display_name
    key = move_slug if move_slug else move_display_name
    t = _move_type_name(key)
    if not t or t not in TYPE_HEX_COLORS:
        return move_display_name
    r, g, b = _hex_to_rgb(TYPE_HEX_COLORS[t])
    return f"\x1b[38;2;{r};{g};{b}m{move_display_name}\x1b[0m"


def _enable_type_color_output() -> None:
    global _TYPE_COLOR_PATCHED, _PLAIN_TERMINAL_PRINT
    if _TYPE_COLOR_PATCHED:
        return

    original_print = builtins.print
    _PLAIN_TERMINAL_PRINT = original_print

    def color_print(*args, **kwargs):  # type: ignore[no-untyped-def]
        sep = kwargs.get("sep", " ")
        converted = []
        for arg in args:
            if isinstance(arg, str) and _game_output_colors_enabled():
                converted.append(_colorize_types_in_text(arg))
            else:
                converted.append(arg)
        if converted:
            first = converted[0]
            rest = converted[1:]
            if isinstance(first, str):
                out = first
                for item in rest:
                    out += sep + (item if isinstance(item, str) else str(item))
                original_print(out, **kwargs)
                return
        original_print(*converted, **kwargs)

    builtins.print = color_print
    _TYPE_COLOR_PATCHED = True


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


def _settings_menu(current: GameSettings) -> GameSettings:
    s = replace(current)
    while True:
        gens_disp = (
            "all"
            if s.allowed_generations is None
            else ",".join(str(g) for g in sorted(s.allowed_generations))
        )
        print("\n--- Settings ---")
        print("Enter a number to change an option, or 0 to return to the main menu.\n")
        print(f"1) Mega forms: {'ON' if s.allow_megas else 'OFF'}")
        print(f"2) Regional variants: {'ON' if s.allow_regionals else 'OFF'}")
        print(f"3) Allowed generations: {gens_disp}")
        print(f"4) Background music: {'MUTED' if s.mute_bgm else 'ON'}")
        print(f"5) Input sound (each Enter): {'MUTED' if s.mute_input_sfx else 'ON'}")
        print(f"6) Win / completion fanfare: {'MUTED' if s.mute_completion_sfx else 'ON'}")
        print(f"7) Last-guess warning sound: {'MUTED' if s.mute_low_health_sfx else 'ON'}")
        print("0) Done")
        raw = input("Settings> ").strip()
        if raw in {"0", "done", "back", "q", "quit"}:
            bgm.configure(s)
            return s
        if raw == "1":
            s.allow_megas = not s.allow_megas
        elif raw == "2":
            s.allow_regionals = not s.allow_regionals
        elif raw == "3":
            gens_raw = input("Generations (comma-separated, blank=all): ").strip()
            if not gens_raw:
                s.allowed_generations = None
            else:
                try:
                    s.allowed_generations = {int(x.strip()) for x in gens_raw.split(",") if x.strip()}
                except ValueError:
                    print("Invalid generations; value unchanged.")
        elif raw == "4":
            s.mute_bgm = not s.mute_bgm
        elif raw == "5":
            s.mute_input_sfx = not s.mute_input_sfx
        elif raw == "6":
            s.mute_completion_sfx = not s.mute_completion_sfx
        elif raw == "7":
            s.mute_low_health_sfx = not s.mute_low_health_sfx
        else:
            print("Unknown choice. Pick 0–7.")
            continue
        bgm.configure(s)


def _settings_summary(settings: GameSettings) -> str:
    gens = "all" if settings.allowed_generations is None else ",".join(str(g) for g in sorted(settings.allowed_generations))
    mus = "off" if settings.mute_bgm else "on"
    inp = "off" if settings.mute_input_sfx else "on"
    win = "off" if settings.mute_completion_sfx else "on"
    low = "off" if settings.mute_low_health_sfx else "on"
    return (
        f"megas={'on' if settings.allow_megas else 'off'} | regionals={'on' if settings.allow_regionals else 'off'} "
        f"| gens={gens} | music={mus} enter={inp} win={win} last={low}"
    )


def _last_guess_warning(turn: int, max_guesses: int) -> None:
    if max_guesses > 1 and turn == max_guesses:
        bgm.play_low_health_sound()


def _wrong_guess_feedback(message: str = "Nope.") -> None:
    print(message)
    bgm.play_incorrect_sound()


def _main_menu_print(active: bool, fg_ansi: str, *args: object, **kwargs: Any) -> None:
    """Main menu lines; optional shiny-style random color (bypasses type-color print patch)."""
    if not active:
        print(*args, **kwargs)
        return
    wrapped: list[object] = []
    for a in args:
        wrapped.append(fg_ansi + (a if isinstance(a, str) else str(a)) + _MENU_RESET)
    _PLAIN_TERMINAL_PRINT(*wrapped, **kwargs)


def run_pokedoku(settings: GameSettings) -> bool | None:
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
            return None

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
        if low0 in ("quit", "q", "exit"):
            print("Leaving Pokedoku.")
            return False
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
    if score == 9:
        bgm.play_completion_sound()
        return True
    return False


def run_squirdle(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    max_guesses = _input_guess_count("How many guesses for Squirdle?", 8)
    target = random.choice(pool)
    seen_guesses: set[str] = set()
    print(f"Guess the Pokémon. You get {max_guesses} guesses.")
    for turn in range(1, max_guesses + 1):
        _last_guess_warning(turn, max_guesses)
        while True:
            guess_name = input(f"Guess {turn}: ").strip()
            if not guess_name:
                print("Guess cannot be blank.")
                continue
            if guess_name.casefold() in {"quit", "q", "exit"}:
                print(f"Leaving Squirdle. Target was {target.name}.")
                return False
            guess = dex.by_name(guess_name)
            if not guess:
                print(f'Unknown Pokémon: "{guess_name}"')
                continue
            if not settings.accepts(guess):
                print("That Pokémon is outside your current generation/variant filters.")
                continue
            if guess.name in seen_guesses:
                print(f'You already guessed "{guess.name}". Try a different Pokémon.')
                continue
            seen_guesses.add(guess.name)
            break
        if guess.name == target.name:
            print("Correct!")
            bgm.play_completion_sound()
            return True
        feedback = compare_guess(target, guess)
        print(format_squirdle_feedback(feedback))
    print(f"Out of guesses. Target was {target.name}.")
    return False


def run_stat_quiz(settings: GameSettings) -> bool | None:
    global LAST_STAT_QUIZ

    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

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
        _last_guess_warning(tries, max_guesses)
        while True:
            guess = input(f"Guess {tries}/{max_guesses}: ").strip()
            if not guess:
                print("Guess cannot be blank.")
                continue
            if guess.casefold() in {"quit", "q", "exit"}:
                print(f"Leaving Pokedentities. It was {mon.name}.")
                return False
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
            bgm.play_completion_sound()
            return True
        if hint_turn is not None and tries == hint_turn:
            print(f"Hint: types={','.join(mon.types)} generation={mon.generation}")
    _wrong_guess_feedback(f"Nope. It was {mon.name}.")
    return False


def run_whos_that_pokemon(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

    max_guesses = _input_guess_count("How many guesses for Who's that Pokemon!?", 3)
    target = random.choice(pool)
    seen_guesses: set[str] = set()

    print("Who's that Pokemon!?")
    print_statle_sprite(target)
    for turn in range(1, max_guesses + 1):
        _last_guess_warning(turn, max_guesses)
        while True:
            guess_name = input(f"Guess {turn}/{max_guesses}: ").strip()
            if not guess_name:
                print("Guess cannot be blank.")
                continue
            if guess_name.casefold() in {"quit", "q", "exit"}:
                print(f"Leaving Who's that Pokemon!?. It was {target.name}.")
                return False
            guess = dex.by_name(guess_name)
            if not guess:
                print(f'Unknown Pokémon: "{guess_name}"')
                continue
            if guess.name in seen_guesses:
                print(f'You already guessed "{guess.name}". Try a different Pokémon.')
                continue
            seen_guesses.add(guess.name)
            break
        if guess.name == target.name:
            print("Correct!")
            bgm.play_completion_sound()
            return True
        print("Nope, try again.")

    print(f"Out of guesses. It was {target.name}.")
    return False


def run_statle(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

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
        while True:
            raw_pick = input("> ").strip()
            if not raw_pick:
                print("Input cannot be blank.")
                continue
            if raw_pick.casefold() in {"quit", "q", "exit"}:
                print("Leaving Statle.")
                return False
            if raw_pick.isdigit() and 1 <= int(raw_pick) <= len(available):
                stat = available[int(raw_pick) - 1]
                break
            stat = raw_pick.casefold().replace(" ", "_")
            if stat in available:
                break
            print("Invalid or already-used stat. Choose one of the remaining stats.")

        picked_stats.append(stat)
        result = resolve_turn(mon, stat)
        results.append(result)
        print(f"{STAT_LABELS[result.stat]} = {result.value}")
        print(f"Running total: {total_score(results)}")

    final = total_score(results)
    bgm.play_completion_sound()
    print(f"\nFinal total: {final}")
    optimal_total, plan = optimal_statle_assignment(round_mons)
    print(format_optimal_statle_summary(round_mons, plan, optimal_total, your_total=final))
    return True


def run_dexacted(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

    target = random.choice(pool)
    entries = list(dex_entries_for_name(target.name))
    if not entries:
        print("No dex entries available for that Pokémon right now. Try another round.")
        return None
    random.shuffle(entries)

    with _plain_game_output():
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
                return False
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
                bgm.play_completion_sound()
                return True
            if revealed >= len(entries):
                print(f"Wrong guess and no entries left. You lose. It was {target.name}.")
                return False
            _wrong_guess_feedback("Nope. Ask for another entry or guess again.")


def run_movepool_madness(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

    try:
        target, required_moves = build_challenge(pool)
    except ValueError as err:
        print(err)
        return None

    max_guesses = _input_guess_count("How many guesses for Movepool Madness?", 5)
    print("Movepool Madness: name any Pokémon that can legally learn ALL four moves.")
    print("(Legal methods: level-up, TM/machine, or egg/breeding.)")
    for idx, move in enumerate(required_moves, start=1):
        print(f"{idx}) {_color_move_name(display_move_name(move), move_slug=move)}")

    seen_guesses: set[str] = set()
    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Guess {turn}/{max_guesses} (or 'quit'): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            print(f"Leaving Movepool Madness. One valid answer was {target.name}.")
            return False

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
                bgm.play_completion_sound()
                return True
            learned = set(legal_moves_for_name(guess.name))
            missing = [_color_move_name(display_move_name(m), move_slug=m) for m in required_moves if m not in learned]
            if missing:
                _wrong_guess_feedback(f"Nope. {guess.name} is missing: {', '.join(missing)}")
            else:
                _wrong_guess_feedback(f"Nope. {guess.name} does not satisfy the four-move requirement.")
            turn += 1
        except Exception:
            print("Could not validate that guess right now (API issue). Try again.")

    print(f"Out of guesses. One valid answer was {target.name}.")
    return False


def run_daycare_detective(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

    target = random.choice(pool)
    try:
        profile = daycare_profile_for_name(target.name)
    except Exception:
        print("Could not load daycare profile data right now (API issue).")
        return None

    max_guesses = _input_guess_count("How many guesses for Daycare Detective?", 5)
    with _plain_game_output():
        print("Daycare Detective: identify the Pokémon from breeding/species profile data.")
        print(f"Clue 1 - Egg Groups: {', '.join(profile.egg_groups) if profile.egg_groups else 'Unknown'}")
        print(f"Clue 2 - Gender Ratio: {gender_rate_label(profile.gender_rate)}")
        print(f"Clue 3 - Hatch Counter: {profile.hatch_counter}")
        print(f"Clue 4 - Capture Rate: {profile.capture_rate}")

        seen_guesses: set[str] = set()
        turn = 1
        while turn <= max_guesses:
            _last_guess_warning(turn, max_guesses)
            raw = input(f"Guess {turn}/{max_guesses} (or 'quit'): ").strip()
            if not raw:
                print("Guess cannot be blank.")
                continue
            if raw.casefold() in {"quit", "q", "exit"}:
                print(f"Leaving Daycare Detective. The answer was {target.name}.")
                return False

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
                bgm.play_completion_sound()
                return True
            _wrong_guess_feedback()
            turn += 1

        print(f"Out of guesses. It was {target.name}.")
        return False


def run_evolutionary_enigma(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

    try:
        edge, clues = build_evolution_enigma_challenge([p.name for p in pool])
    except ValueError as err:
        print(err)
        return None
    signature = evolution_details_signature(edge.details)

    max_guesses = _input_guess_count("How many guesses for Evolutionary Enigma?", 5)
    with _plain_game_output():
        print("Evolutionary Enigma: deduce the evolution pair from trigger clues.")
        print("You can answer with either the Pokémon evolving from this condition OR evolving into it.")
        print("Commands: clue (reveal next clue), quit")

        revealed = 1
        print(f"\nClue 1/{len(clues)}: {clues[0]}")
        seen_guesses: set[str] = set()
        turn = 1
        while turn <= max_guesses:
            _last_guess_warning(turn, max_guesses)
            raw = input(f"Guess {turn}/{max_guesses} (or command): ").strip()
            if not raw:
                print("Guess cannot be blank.")
                continue
            cmd = raw.casefold()
            if cmd in {"quit", "q", "exit"}:
                print(f"Leaving Evolutionary Enigma. This clue profile included {edge.from_name} -> {edge.to_name}.")
                return False
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
                bgm.play_completion_sound()
                return True

            _wrong_guess_feedback()
            turn += 1

        print(f"Out of guesses. This clue profile included {edge.from_name} -> {edge.to_name}.")
        return False


def run_ability_assessor(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

    target = random.choice(pool)
    try:
        profile = ability_profile_for_name(target.name)
    except Exception:
        print("Could not load ability data right now (API issue).")
        return None

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
        return None
    random.shuffle(clues)

    max_guesses = _input_guess_count("How many guesses for Ability Assessor?", 5)
    print("Ability Assessor: guess a Pokémon matching this ability combination.")
    print("Commands: clue (reveal next clue), quit")
    revealed = 1
    print(f"\nClue 1/{len(clues)}: {clues[0]}")

    seen_guesses: set[str] = set()
    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
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
            return False
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
            bgm.play_completion_sound()
            return True

        _wrong_guess_feedback()
        turn += 1

    print(f"Out of guesses. One matching profile was {target.name}.")
    return False


def run_level_ladder(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

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
        return None

    reverse_mode = _input_bool("Use reverse mode (show highest-level moves first)?", False)
    ordered = list(reversed(moves)) if reverse_mode else moves
    clues = [f"Level {lvl}: {_color_move_name(display_level_move_name(move), move_slug=move)}" for lvl, move in ordered]

    max_guesses = _input_guess_count("How many guesses for Level Ladder?", 5)
    print("Level Ladder: deduce the Pokémon from its level-up learnset clues.")
    print("Commands: clue (reveal next clue), quit")
    print(f"\nHint 1/{len(clues)}: {clues[0]}")
    revealed = 1

    seen_guesses: set[str] = set()
    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Guess {turn}/{max_guesses} (or command): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        cmd = raw.casefold()
        if cmd in {"quit", "q", "exit"}:
            print(f"Leaving Level Ladder. The answer was {target.name}.")
            return False
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
            bgm.play_completion_sound()
            return True
        _wrong_guess_feedback()
        turn += 1

    print(f"Out of guesses. It was {target.name}.")
    return False


def run_defensive_profile(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

    dual_type_pool = [p for p in pool if len(p.types) >= 2]
    if not dual_type_pool:
        print("No dual-type Pokémon match your current filters for Defensive Profile.")
        return None

    target = random.choice(dual_type_pool)
    try:
        target_types = defensive_types_for_name(target.name)
        clues = grouped_multiplier_clues(target_types)
    except Exception:
        print("Could not load type-defense data right now (API issue).")
        return None

    if not clues:
        print("No defensive clue data was available for this target. Try another round.")
        return None

    max_guesses = _input_guess_count("How many guesses for Defensive Profile?", 5)
    print("Defensive Profile: guess a Pokémon that matches this defensive profile.")
    print("All clues are shown at the start.")
    for idx, clue in enumerate(clues, start=1):
        print(f"Clue {idx}: {clue}")

    seen_guesses: set[str] = set()
    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
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
            return False

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
            bgm.play_completion_sound()
            return True

        _wrong_guess_feedback()
        turn += 1

    print(
        "Out of guesses. "
        f"One matching type combo was {'/'.join(t.title() for t in target_types)} "
        f"(example: {target.name})."
    )
    return False


def run_safari_zone(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

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
        return None

    random.shuffle(target_clues)
    max_guesses = _input_guess_count("How many guesses for Safari Zone?", 5)
    with _plain_game_output():
        print("Safari Zone: guess a Pokémon from wild encounter location/method clues.")
        print("Commands: clue (reveal next clue), quit")
        revealed = 1
        print(f"\nClue 1/{len(target_clues)}: {target_clues[0]}")

        seen_guesses: set[str] = set()
        turn = 1
        revealed_set = set(target_clues[:revealed])
        while turn <= max_guesses:
            _last_guess_warning(turn, max_guesses)
            raw = input(f"Guess {turn}/{max_guesses} (or command): ").strip()
            if not raw:
                print("Guess cannot be blank.")
                continue
            cmd = raw.casefold()
            if cmd in {"quit", "q", "exit"}:
                print(f"Leaving Safari Zone. One matching answer was {target.name}.")
                return False
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
                bgm.play_completion_sound()
                return True

            _wrong_guess_feedback()
            turn += 1

        print(f"Out of guesses. One matching answer was {target.name}.")
        return False


def run_thiefs_target(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

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
        return None

    clues = thief_profile_clues(profile)
    max_guesses = _input_guess_count("How many guesses for Thief's Target?", 5)
    with _plain_game_output():
        print("Thief's Target: guess a Pokémon matching this wild held-item profile.")
        print("All clues are shown at the start.")
        for idx, clue in enumerate(clues, start=1):
            print(f"Clue {idx}: {clue}")

        seen_guesses: set[str] = set()
        turn = 1
        while turn <= max_guesses:
            _last_guess_warning(turn, max_guesses)
            raw = input(f"Guess {turn}/{max_guesses} (or 'quit'): ").strip()
            if not raw:
                print("Guess cannot be blank.")
                continue
            if raw.casefold() in {"quit", "q", "exit"}:
                print(f"Leaving Thief's Target. One matching answer was {target.name}.")
                return False

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
                bgm.play_completion_sound()
                return True

            _wrong_guess_feedback()
            turn += 1

        print(f"Out of guesses. One matching answer was {target.name}.")
        return False


def run_odd_one_out(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if len(pool) < 3:
        print("Not enough Pokémon in current filter for Ugly Ducklett.")
        return None

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
        return None

    print("Ugly Ducklett: exactly one Pokémon does NOT share the hidden trait.")
    print("Pick by number or by Pokémon name. Commands: quit")
    for i, name in enumerate(challenge.names, start=1):
        print(f"{i}) {name}")

    seen_choices: set[int] = set()
    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Pick odd one out ({turn}/{max_guesses}): ").strip()
        if not raw:
            print("Input cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            odd_name = challenge.names[challenge.odd_index]
            print(f"Leaving Ugly Ducklett. Odd one was {odd_name}. Shared trait was {challenge.trait_explanation}.")
            return False

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
            bgm.play_completion_sound()
            return True

        _wrong_guess_feedback()
        turn += 1

    odd_name = challenge.names[challenge.odd_index]
    print(f"Out of guesses. Odd one was {odd_name}. Shared trait was {challenge.trait_explanation}.")
    return False


def run_category_quiz(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

    target = random.choice(pool)
    try:
        target_profile = category_profile_for_name(target.name)
    except Exception:
        print("Could not load category/species data right now (API issue).")
        return None

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
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Guess {turn}/{max_guesses} (or 'quit'): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            print(f"Leaving Category Quiz. One matching answer was {target.name}.")
            return False
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
            bgm.play_completion_sound()
            return True

        _wrong_guess_feedback()
        turn += 1

    print(f"Out of guesses. One matching answer was {target.name}.")
    return False


def run_stat_sorter(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if len(pool) < 3:
        print("Not enough Pokémon in current filter for Stat Sorter.")
        return None

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
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Order guess {turn}/{max_guesses} (or 'quit'): ").strip()
        if not raw:
            print("Input cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            pretty = " -> ".join(f"{m.name} ({getattr(m, stat_key)})" for m in correct_sorted)
            print(f"Leaving Stat Sorter. Correct order was: {pretty}")
            return False

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
                bgm.play_completion_sound()
                return True

        _wrong_guess_feedback()
        turn += 1

    pretty = " -> ".join(f"{m.name} ({getattr(m, stat_key)})" for m in correct_sorted)
    print(f"Out of guesses. Correct order was: {pretty}")
    return False


def run_level_race(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if len(pool) < 2:
        print("Not enough Pokémon in current filter for Level Race.")
        return None

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
        return None

    max_guesses = _input_guess_count("How many guesses for Level Race?", 3)
    print("Level Race (Move Learnsets): order these Pokémon by learn level (lowest to highest).")
    print("Enter numbers or names in one line, separated by commas/spaces (e.g. '2,1,3').")
    print(f"Move: {_color_move_name(display_level_race_move_name(move_name), move_slug=move_name)}")
    for idx, (mon, _) in enumerate(options, start=1):
        print(f"{idx}) {mon.name}")

    correct_sorted = sorted(options, key=lambda x: x[1])  # low -> high
    correct_names = [m.name for m, _ in correct_sorted]
    option_name_set = {m.name for m, _ in options}
    seen_submissions: set[tuple[str, ...]] = set()

    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Order guess {turn}/{max_guesses} (or 'quit'): ").strip()
        if not raw:
            print("Input cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            details = " -> ".join(f"{m.name} (L{lvl})" for m, lvl in correct_sorted)
            print(f"Leaving Level Race. Correct order was: {details}")
            return False

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
                bgm.play_completion_sound()
                return True

        _wrong_guess_feedback()
        turn += 1

    details = " -> ".join(f"{m.name} (L{lvl})" for m, lvl in correct_sorted)
    print(f"Out of guesses. Correct order was: {details}")
    return False


def run_missing_link(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if len(pool) < 1:
        print("No Pokémon match your filter settings.")
        return None

    try:
        mon, moves, missing_idx, missing_move = build_missing_link_challenge(pool)
    except ValueError as err:
        print(err)
        return None

    info = missing_link_move_info(missing_move)
    if info is None:
        print("Could not load move clue data right now (API issue).")
        return None

    max_guesses = _input_guess_count("How many guesses for Missing Link?", 4)
    print("Missing Link: one level-up move is redacted. Guess the missing move.")
    print("Commands: clue (manual clue reveal), quit")
    print(f"Pokémon: {mon.name}")
    for idx, (lvl, mv) in enumerate(moves):
        if idx == missing_idx:
            print(f"Lv {lvl}: [ ??? ]")
        else:
            print(f"Lv {lvl}: {_color_move_name(display_level_move_name(mv), move_slug=mv)}")

    clue_stage = 0
    seen_guesses: set[str] = set()
    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Move guess {turn}/{max_guesses} (or command): ").strip()
        if not raw:
            print("Input cannot be blank.")
            continue
        cmd = raw.casefold()
        if cmd in {"quit", "q", "exit"}:
            print(
                "Leaving Missing Link. The move was "
                f"{_color_move_name(display_level_move_name(missing_move), move_slug=missing_move)}."
            )
            return False
        if cmd in {"clue", "c", "hint"}:
            if clue_stage == 0:
                print(f"Clue 1: Move type is {info['type']}.")
            elif clue_stage == 1:
                print(f"Clue 2: Move class is {info['damage_class']}.")
            elif clue_stage == 2:
                if info["damage_class"] in {"Physical", "Special"} and info["power"] is not None:
                    print(f"Clue 3: Move power is {info['power']}.")
                else:
                    print("Clue 3: This move does not have damage power (status move).")
            else:
                print("No more clues available.")
                continue
            clue_stage += 1
            continue

        guess_info = missing_link_move_info(raw)
        if guess_info is None:
            print(f'Unknown move: "{raw}"')
            continue
        guess_slug = str(guess_info["name"])
        if guess_slug in seen_guesses:
            print(
                f'You already guessed "{_color_move_name(display_level_move_name(guess_slug), move_slug=guess_slug)}". '
                "Try a different move."
            )
            continue
        seen_guesses.add(guess_slug)

        if guess_slug == missing_move:
            print("Correct!")
            bgm.play_completion_sound()
            return True

        _wrong_guess_feedback()
        turn += 1

    print(
        "Out of guesses. The move was "
        f"{_color_move_name(display_level_move_name(missing_move), move_slug=missing_move)}."
    )
    return False


def run_ev_forensic(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

    # Pick a target that actually yields EVs for meaningful core clue.
    candidates = pool[:]
    random.shuffle(candidates)
    target = None
    target_profile = None
    for mon in candidates:
        try:
            p = ev_forensic_profile_for_name(mon.name)
        except Exception:
            continue
        if p.ev_yields:
            target = mon
            target_profile = p
            break
    if target is None or target_profile is None:
        print("Could not find EV-yield data for this filter set.")
        return None

    clue_map = {
        "generation": f"Generation: {target_profile.generation}" if target_profile.generation is not None else None,
        "types": f"Type(s): {', '.join(target_profile.types)}" if target_profile.types else None,
        "evolution_stage": f"Evolution Stage: {target_profile.evolution_stage}" if target_profile.evolution_stage else None,
        "color": f"Color: {target_profile.color}" if target_profile.color else None,
        "egg_groups": f"Egg Groups: {', '.join(target_profile.egg_groups)}" if target_profile.egg_groups else None,
        "primary_ability": f"Primary Ability: {target_profile.primary_ability}" if target_profile.primary_ability else None,
        "capture_rate_band": f"Capture Rate Band: {target_profile.capture_rate_band}" if target_profile.capture_rate_band else None,
    }

    max_guesses = _input_guess_count("How many guesses for EV Forensic?", 5)
    print("EV Forensic: identify the Pokémon from EV yield and optional manual clues.")
    print(ev_forensic_ev_yield_line(target_profile))
    print("Commands: clue (choose a clue to reveal), quit")

    shown_fields: set[str] = {"ev_yields"}
    seen_guesses: set[str] = set()
    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Guess {turn}/{max_guesses} (or command): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        cmd = raw.casefold()
        if cmd in {"quit", "q", "exit"}:
            print(f"Leaving EV Forensic. One matching answer was {target.name}.")
            return False
        if cmd in {"clue", "c", "hint"}:
            remaining = [k for k, v in clue_map.items() if v and k not in shown_fields]
            if not remaining:
                print("No more clues available.")
                continue
            print("Choose a clue to reveal:")
            for idx, key in enumerate(remaining, start=1):
                print(f"{idx}) {key.replace('_', ' ')}")
            pick = input("> ").strip()
            if not pick.isdigit() or not (1 <= int(pick) <= len(remaining)):
                print("Invalid clue selection.")
                continue
            chosen = remaining[int(pick) - 1]
            shown_fields.add(chosen)
            print(clue_map[chosen])
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
            gp = ev_forensic_profile_for_name(guess.name)
        except Exception:
            print("Could not validate that guess right now (API issue). Try again.")
            continue

        # Multi-answer acceptance: any Pokémon matching currently shown fields is correct.
        ok = gp.ev_yields == target_profile.ev_yields
        if ok and "generation" in shown_fields:
            ok = gp.generation == target_profile.generation
        if ok and "types" in shown_fields:
            ok = gp.types == target_profile.types
        if ok and "evolution_stage" in shown_fields:
            ok = gp.evolution_stage == target_profile.evolution_stage
        if ok and "color" in shown_fields:
            ok = gp.color == target_profile.color
        if ok and "egg_groups" in shown_fields:
            ok = gp.egg_groups == target_profile.egg_groups
        if ok and "primary_ability" in shown_fields:
            ok = gp.primary_ability == target_profile.primary_ability
        if ok and "capture_rate_band" in shown_fields:
            ok = gp.capture_rate_band == target_profile.capture_rate_band

        if ok:
            print(f"Correct! {guess.name} fits the shown EV Forensic profile.")
            bgm.play_completion_sound()
            return True

        _wrong_guess_feedback()
        turn += 1

    print(f"Out of guesses. One matching answer was {target.name}.")
    return False


def run_international_names(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

    candidates = pool[:]
    random.shuffle(candidates)
    target = None
    romaji: str | None = None
    for mon in candidates:
        try:
            r = romanized_japanese_name(mon.name)
        except Exception:
            continue
        if r:
            target = mon
            romaji = r
            break

    if target is None or not romaji:
        print(
            "Could not find a species with a PokéAPI ja-roma (romanized Japanese) name "
            "in the current filter. Try again or widen filters."
        )
        return None

    try:
        name_map = names_by_language(target.name)
    except Exception:
        print("Could not load species name data right now (API issue).")
        return None

    max_guesses = _input_guess_count("How many guesses for International Names?", 5)
    optional_labels = ", ".join(label for _, label in CLUE_LANGUAGES)
    with _plain_game_output():
        print("International Names: guess the English species name.")
        print("Shown first: Japanese from PokéAPI language code ja-roma (romanized).")
        print(f"Optional clues (if present for this species): {optional_labels}.")
        print("Commands: clue (reveal one name in another language), quit")
        print(f"\nJapanese (romanized): {romaji}")

        shown_langs: set[str] = {"ja-roma"}
        seen_guesses: set[str] = set()
        turn = 1
        while turn <= max_guesses:
            _last_guess_warning(turn, max_guesses)
            raw = input(f"Guess {turn}/{max_guesses} (or command): ").strip()
            if not raw:
                print("Guess cannot be blank.")
                continue
            cmd = raw.casefold()
            if cmd in {"quit", "q", "exit"}:
                print(f"Leaving International Names. The English name was {target.name}.")
                return False
            if cmd in {"clue", "c", "hint"}:
                remaining: list[tuple[str, str, str]] = []
                for code, label in CLUE_LANGUAGES:
                    cf = code.casefold()
                    if cf in shown_langs:
                        continue
                    nm = name_map.get(cf)
                    if not nm:
                        continue
                    remaining.append((cf, label, nm))
                if not remaining:
                    print("No more optional name clues available for this Pokémon.")
                    continue
                print("Pick a language clue to reveal:")
                for idx, (_, label, _) in enumerate(remaining, start=1):
                    print(f"{idx}) {label}")
                pick = input("> ").strip()
                if not pick.isdigit() or not (1 <= int(pick) <= len(remaining)):
                    print("Invalid clue selection.")
                    continue
                cf, label, nm = remaining[int(pick) - 1]
                shown_langs.add(cf)
                print(f"{label}: {nm}")
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

            if guess.name == target.name:
                print("Correct!")
                bgm.play_completion_sound()
                return True

            _wrong_guess_feedback()
            turn += 1

        print(f"Out of guesses. The English name was {target.name}.")
        return False


def run_growth_rate_guesstimate(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if len(pool) < 3:
        print("Need at least three Pokémon in the current filter for Growth Rate Guesstimate.")
        return None

    challenge = build_growth_rate_challenge(pool)
    if challenge is None:
        print(
            "Could not build a round (need three species with different level-100 XP totals, "
            "or a network/API issue). Try again or widen filters."
        )
        return None

    max_guesses = _input_guess_count("How many guesses for Growth Rate Guesstimate?", 3)
    print()
    print("Growth Rate Guesstimate (no mid-round hints).")
    print(question_line(challenge))
    print("Each guess is one line with all three choices in order (letters, numbers, or names).")
    for letter, name in zip(("A", "B", "C"), challenge.labels, strict=True):
        print(f"  {letter}) {name}")
    print()

    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Order line {turn}/{max_guesses}: ")
        if not raw.strip():
            print("Enter three entries on one line (cannot be blank).")
            continue
        if raw.strip().casefold() in {"quit", "q", "exit"}:
            print(f"Leaving Growth Rate Guesstimate. Correct order was: {describe_order(challenge, challenge.correct_order)}")
            for i in range(3):
                print(f"  {format_option_summary(challenge, i)}")
            return False

        ranking = parse_ranking_line(raw, dex, challenge)
        if ranking is None:
            print('Need exactly three tokens (e.g. "B C A"), each A/B/C, 1/2/3, or one of the listed names, no repeats.')
            continue

        if ranking == challenge.correct_order:
            print("Correct!")
            print(f"  {describe_order(challenge, ranking)}")
            bgm.play_completion_sound()
            return True

        _wrong_guess_feedback()
        turn += 1

    print(f"Out of guesses. Correct order was: {describe_order(challenge, challenge.correct_order)}")
    for i in range(3):
        print(f"  {format_option_summary(challenge, i)}")
    return False


def run_exp_yield(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if len(pool) < 2:
        print("Need at least two Pokémon in the current filter for EXP Yield.")
        return None

    max_opts = min(8, len(pool))
    while True:
        raw = input(f"How many Pokémon choices? (2–{max_opts}, default 2): ").strip()
        if not raw:
            n_choices = 2
            break
        if raw.isdigit() and 2 <= int(raw) <= max_opts:
            n_choices = int(raw)
            break
        print(f"Enter a whole number from 2 to {max_opts}.")

    c = build_exp_yield_challenge(pool, n_choices)
    if c is None:
        print(
            "Could not build a round (API issue, or could not find that many species with "
            "distinct base experience). Try fewer choices or widen filters."
        )
        return None

    n = len(c.names)
    max_guesses = _input_guess_count("How many guesses for EXP Yield?", 3)
    print()
    print("EXP Yield (no mid-round hints).")
    print(exp_yield_prompt_line(c))
    print(pick_help_line(n))
    for letter, name in zip(letter_labels(n), c.names, strict=True):
        print(f"  {letter}) {name}")
    print()

    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Guess {turn}/{max_guesses}: ")
        if not raw.strip():
            print("Guess cannot be blank.")
            continue
        if raw.strip().casefold() in {"quit", "q", "exit"}:
            print(f"Leaving EXP Yield. Answer: {c.names[c.correct_index]}.")
            for i in range(n):
                print(f"  {exp_yield_reveal_line(c, i)}")
            return False

        idx = exp_yield_resolve_pick(raw, dex, c)
        if idx is None:
            print(f"Could not parse. {pick_help_line(n)}")
            continue

        if idx == c.correct_index:
            print("Correct!")
            for i in range(n):
                print(f"  {exp_yield_reveal_line(c, i)}")
            bgm.play_completion_sound()
            return True

        _wrong_guess_feedback()
        turn += 1

    print(f"Out of guesses. Answer: {c.names[c.correct_index]}.")
    for i in range(n):
        print(f"  {exp_yield_reveal_line(c, i)}")
    return False


def run_dex_it(settings: GameSettings) -> None:
    """DexIt: higher/lower on National Dex; chains so the last correct Guess becomes the next Target. No loser BGM, no last-guess SFX; not routed through `_route_bgm_after_game`."""
    global _DEX_IT_SESSION_BEST

    dex = load_dex()
    pool = dex.filtered(settings)
    if len(pool) < 2:
        print("Need at least two Pokémon in the current filter for DexIt.")
        return

    print()
    print("DexIt — is the Guess’s National Dex # higher or lower than the Target’s?")
    print("After a correct answer, the next round compares that Pokémon to a new random species.")
    print(f"Session high score (best streak this app run): {_DEX_IT_SESSION_BEST}")
    print("h = higher, l = lower, quit = main menu. (No last-guess warning in this mode.)")
    print()

    anchor: Pokemon | None = None
    streak = 0
    while True:
        if anchor is None:
            pair = pick_target_and_guess(pool)
            if pair is None:
                print("Could not build a round (need two species with different Dex numbers in the pool).")
                return
            target, guess = pair
        else:
            guess = pick_next_guess(anchor, pool)
            if guess is None:
                print("No other species in the current filter to chain; starting a fresh pair.")
                anchor = None
                continue
            target = anchor

        print(f"Target: {target.name} (#{target.dex_number})")
        print(f"Guess:  {guess.name}")
        print()
        print(f"Is {guess.name}'s National Dex number higher or lower than {target.name}'s?")

        while True:
            raw = input("Guess> ").strip()
            if not raw:
                print("Type h (higher) or l (lower), or quit to leave.")
                continue
            if raw.casefold() in {"quit", "q", "exit", "back"}:
                print("Leaving DexIt.")
                return
            answer = parse_higher_lower(raw)
            if answer is None:
                print("Type h (higher) or l (lower), or quit to leave.")
                continue
            break

        if dex_it_is_correct(answer, target, guess):
            streak += 1
            old_best = _DEX_IT_SESSION_BEST
            _DEX_IT_SESSION_BEST = max(_DEX_IT_SESSION_BEST, streak)
            if streak > old_best:
                print(f"Correct! New session high score: {_DEX_IT_SESSION_BEST}!")
            else:
                print(f"Correct! Streak: {streak}  |  Session high: {_DEX_IT_SESSION_BEST}")
            bgm.play_completion_sound()
            anchor = guess
        else:
            _wrong_guess_feedback(
                f"Wrong! {guess.name} is #{guess.dex_number}, {target.name} is #{target.dex_number}."
            )
            if streak > 0:
                print(f"Streak ended at {streak}. Session high: {_DEX_IT_SESSION_BEST}.")
            else:
                print(f"Session high: {_DEX_IT_SESSION_BEST}.")
            streak = 0
            anchor = None

        print()


def run_power_levels(settings: GameSettings) -> None:
    """Power Levels: higher/lower on BST; chains like DexIt. No loser BGM, no last-guess SFX; not routed through `_route_bgm_after_game`."""
    global _POWER_LEVELS_SESSION_BEST

    dex = load_dex()
    pool = dex.filtered(settings)
    if len(pool) < 2:
        print("Need at least two Pokémon in the current filter for Power Levels.")
        return

    print()
    print("Power Levels — is the Guess’s base stat total (BST) higher or lower than the Target’s?")
    print("After a correct answer, the next round compares that Pokémon to a new random species.")
    print(f"Session high score (best streak this app run): {_POWER_LEVELS_SESSION_BEST}")
    print("h = higher, l = lower, quit = main menu. (No last-guess warning in this mode.)")
    print()

    anchor: Pokemon | None = None
    streak = 0
    while True:
        if anchor is None:
            pair = power_levels_pick_pair(pool)
            if pair is None:
                print("Could not build a round (need two species with different base stat totals in the pool).")
                return
            target, guess = pair
        else:
            guess = power_levels_pick_next(anchor, pool)
            if guess is None:
                print("No other species in the current filter to chain; starting a fresh pair.")
                anchor = None
                continue
            target = anchor

        print(f"Target: {target.name} (BST {target.bst})")
        print(f"Guess:  {guess.name}")
        print()
        print(f"Is {guess.name}'s base stat total (BST) higher or lower than {target.name}'s?")

        while True:
            raw = input("Guess> ").strip()
            if not raw:
                print("Type h (higher) or l (lower), or quit to leave.")
                continue
            if raw.casefold() in {"quit", "q", "exit", "back"}:
                print("Leaving Power Levels.")
                return
            answer = parse_higher_lower(raw)
            if answer is None:
                print("Type h (higher) or l (lower), or quit to leave.")
                continue
            break

        if power_levels_is_correct(answer, target, guess):
            streak += 1
            old_best = _POWER_LEVELS_SESSION_BEST
            _POWER_LEVELS_SESSION_BEST = max(_POWER_LEVELS_SESSION_BEST, streak)
            if streak > old_best:
                print(f"Correct! New session high score: {_POWER_LEVELS_SESSION_BEST}!")
            else:
                print(f"Correct! Streak: {streak}  |  Session high: {_POWER_LEVELS_SESSION_BEST}")
            bgm.play_completion_sound()
            anchor = guess
        else:
            _wrong_guess_feedback(
                f"Wrong! {guess.name} has BST {guess.bst}, {target.name} has BST {target.bst}."
            )
            if streak > 0:
                print(f"Streak ended at {streak}. Session high: {_POWER_LEVELS_SESSION_BEST}.")
            else:
                print(f"Session high: {_POWER_LEVELS_SESSION_BEST}.")
            streak = 0
            anchor = None

        print()


def run_ability_effects(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None

    ch = build_ability_effects_challenge(pool)
    if ch is None:
        print("Could not build Ability Effects round (API issue or no English effect text). Try again.")
        return None

    max_guesses = _input_guess_count("How many guesses for Ability Effects?", 5)
    ensure_ability_guess_index()
    print()
    print("Ability Effects: name the ability from its English mechanical description.")
    print("The species and ability names are redacted in the text.")
    print("Commands: clue (next English effect entry, if any), quit")
    revealed_count = 0
    print(f"Effect {revealed_count + 1}/{len(ch.descriptions)}:")
    print(
        redact_for_ability(
            ch.descriptions[revealed_count],
            ability_slug=ch.ability_slug,
            pokemon_display=ch.pokemon_name,
        )
    )
    revealed_count = 1
    wrong_slugs: set[str] = set()

    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Ability ({turn}/{max_guesses}, or command): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            print(f"Leaving Ability Effects. The ability was {display_ability_name(ch.ability_slug)}.")
            return False
        if raw.casefold() in {"clue", "c", "hint"}:
            if revealed_count >= len(ch.descriptions):
                print("No more English effect descriptions available.")
            else:
                print(f"Effect {revealed_count + 1}/{len(ch.descriptions)}:")
                print(
                    redact_for_ability(
                        ch.descriptions[revealed_count],
                        ability_slug=ch.ability_slug,
                        pokemon_display=ch.pokemon_name,
                    )
                )
                revealed_count += 1
            continue

        canon = ability_slug_from_user_guess(raw)
        if canon is None:
            print("That doesn't match a known Pokédex ability (check spelling).")
            continue
        if canon == ch.ability_slug:
            print(f"Correct! It was {display_ability_name(ch.ability_slug)}.")
            bgm.play_completion_sound()
            return True
        if canon in wrong_slugs:
            print("You already guessed that ability.")
            continue
        wrong_slugs.add(canon)
        _wrong_guess_feedback()
        turn += 1

    print(f"Out of guesses. The ability was {display_ability_name(ch.ability_slug)}.")
    return False


def run_item_lore(_settings: GameSettings) -> bool | None:
    ch = build_item_lore_challenge()
    if ch is None:
        print("Could not build Item Lore round (API issue). Try again.")
        return None

    max_guesses = _input_guess_count("How many guesses for Item Lore?", 5)
    ensure_item_guess_index()
    print()
    print("Item Lore: name the item from its English flavor text.")
    print("The item name is redacted in the text.")
    print("Commands: clue (next English flavor line, if any), quit")
    revealed_count = 0
    print(f"Flavor {revealed_count + 1}/{len(ch.descriptions)}:")
    print(redact_for_item(ch.descriptions[revealed_count], item_slug=ch.item_slug))
    revealed_count = 1
    wrong_slugs: set[str] = set()

    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Item ({turn}/{max_guesses}, or command): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            print(f"Leaving Item Lore. The item was {display_item_name(ch.item_slug)}.")
            return False
        if raw.casefold() in {"clue", "c", "hint"}:
            if revealed_count >= len(ch.descriptions):
                print("No more English flavor lines available.")
            else:
                print(f"Flavor {revealed_count + 1}/{len(ch.descriptions)}:")
                print(redact_for_item(ch.descriptions[revealed_count], item_slug=ch.item_slug))
                revealed_count += 1
            continue

        canon = item_slug_from_user_guess(raw)
        if canon is None:
            print("That doesn't match a known Pokédex item (check spelling).")
            continue
        if canon == ch.item_slug:
            print(f"Correct! It was {display_item_name(ch.item_slug)}.")
            bgm.play_completion_sound()
            return True
        if canon in wrong_slugs:
            print("You already guessed that item.")
            continue
        wrong_slugs.add(canon)
        _wrong_guess_feedback()
        turn += 1

    print(f"Out of guesses. The item was {display_item_name(ch.item_slug)}.")
    return False


def run_move_match(_settings: GameSettings) -> bool | None:
    ch = build_move_match_challenge()
    if ch is None:
        print("Could not build Move Match round (API issue). Try again.")
        return None

    max_guesses = _input_guess_count("How many guesses for Move Match?", 5)
    ensure_move_guess_index()
    print()
    print("Move Match: name the move from its English mechanical description.")
    print("The move name is redacted in the text.")
    print("Commands: clue (next English effect entry, if any), quit")
    revealed_count = 0
    print(f"Effect {revealed_count + 1}/{len(ch.descriptions)}:")
    print(redact_for_move(ch.descriptions[revealed_count], move_slug=ch.move_slug))
    revealed_count = 1
    wrong_slugs: set[str] = set()

    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Move ({turn}/{max_guesses}, or command): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        if raw.casefold() in {"quit", "q", "exit"}:
            print(f"Leaving Move Match. The move was {display_move_match_name(ch.move_slug)}.")
            return False
        if raw.casefold() in {"clue", "c", "hint"}:
            if revealed_count >= len(ch.descriptions):
                print("No more English effect descriptions available.")
            else:
                print(f"Effect {revealed_count + 1}/{len(ch.descriptions)}:")
                print(redact_for_move(ch.descriptions[revealed_count], move_slug=ch.move_slug))
                revealed_count += 1
            continue

        canon = move_slug_from_user_guess(raw)
        if canon is None:
            print("That doesn't match a known Pokédex move (check spelling).")
            continue
        if canon == ch.move_slug:
            print(f"Correct! It was {display_move_match_name(ch.move_slug)}.")
            bgm.play_completion_sound()
            return True
        if canon in wrong_slugs:
            print("You already guessed that move.")
            continue
        wrong_slugs.add(canon)
        _wrong_guess_feedback()
        turn += 1

    print(f"Out of guesses. The move was {display_move_match_name(ch.move_slug)}.")
    return False


def run_machine_serial(_settings: GameSettings) -> bool | None:
    ch = build_machine_serial_challenge()
    if ch is None:
        print("Could not build Machine Serial round (API issue). Try again.")
        return None

    max_guesses = _input_guess_count("How many guesses for Machine Serial?", 5)
    ensure_move_guess_index()
    print()
    print("Machine Serial: name the move from generation + machine code.")
    print(f"Prompt: Generation {ch.generation}, {ch.machine_code}.")
    print("Commands: clue (manual clue reveal), quit")

    clue_order = [
        f"Clue 1: Move type is {ch.move_type}.",
        f"Clue 2: Move class is {ch.damage_class}.",
    ]
    if ch.damage_class in {"Physical", "Special"} and ch.power is not None:
        clue_order.append(f"Clue 3: Move power is {ch.power}.")
    clue_stage = 0

    wrong_slugs: set[str] = set()
    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Move ({turn}/{max_guesses}, or command): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        cmd = raw.casefold()
        if cmd in {"quit", "q", "exit"}:
            print(f"Leaving Machine Serial. The move was {display_move_match_name(ch.move_slug)}.")
            return False
        if cmd in {"clue", "c", "hint"}:
            if clue_stage >= len(clue_order):
                print("No more clues available.")
                continue
            print(clue_order[clue_stage])
            clue_stage += 1
            continue

        canon = move_slug_from_user_guess(raw)
        if canon is None:
            print("That doesn't match a known Pokédex move (check spelling).")
            continue
        if canon == ch.move_slug:
            print(f"Correct! It was {display_move_match_name(ch.move_slug)}.")
            bgm.play_completion_sound()
            return True
        if canon in wrong_slugs:
            print("You already guessed that move.")
            continue
        wrong_slugs.add(canon)
        _wrong_guess_feedback()
        turn += 1

    print(f"Out of guesses. The move was {display_move_match_name(ch.move_slug)}.")
    return False


def run_fling_force(_settings: GameSettings) -> bool | None:
    ch = build_fling_force_challenge()
    if ch is None:
        print("Could not build Fling Force round (API issue). Try again.")
        return None

    max_guesses = _input_guess_count("How many guesses for Fling Force?", 5)
    print()
    print("Fling Force: given an item, guess its Fling power or Fling status effect.")
    print(f"Item: {display_item_name(ch.item_slug)}")
    print("Commands: clue (single manual clue), quit")
    clue_revealed = False
    seen: set[str] = set()

    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Answer ({turn}/{max_guesses}, or command): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        cmd = raw.casefold()
        if cmd in {"quit", "q", "exit"}:
            print(
                "Leaving Fling Force. Accepted answer was "
                f"{fling_force_reveal_answer_line(ch)}."
            )
            return False
        if cmd in {"clue", "c", "hint"}:
            if clue_revealed:
                print("No more clues available.")
            else:
                print(fling_force_clue_line(ch))
                clue_revealed = True
            continue

        ok, key = fling_force_parse_guess(raw, ch)
        if not key:
            print("Enter either an integer power or a status/effect word.")
            continue
        if key in seen:
            print("You already guessed that.")
            continue
        seen.add(key)
        if ok:
            print(f"Correct! Accepted: {fling_force_reveal_answer_line(ch)}.")
            bgm.play_completion_sound()
            return True
        _wrong_guess_feedback()
        turn += 1

    print(f"Out of guesses. Accepted answer was {fling_force_reveal_answer_line(ch)}.")
    return False


def run_all_natural(_settings: GameSettings) -> bool | None:
    ch = build_all_natural_challenge()
    if ch is None:
        print("Could not build All Natural round (API issue). Try again.")
        return None

    max_guesses = _input_guess_count("How many guesses for All Natural?", 5)
    print()
    print("All Natural: given a Berry, guess Natural Gift Type and Base Power.")
    print(f"Berry: {display_berry_name(ch.berry_slug)}")
    print("Enter both in one line, e.g. Fire 80 (or 80 Fire).")
    print("Commands: quit")
    seen: set[str] = set()

    def _display_guess_from_key(key: str) -> str:
        try:
            t_slug, p = key.split(":", 1)
        except ValueError:
            return key
        return f"{display_natural_gift_type_name(t_slug)} {p}"

    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Answer ({turn}/{max_guesses}, or command): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        cmd = raw.casefold()
        if cmd in {"quit", "q", "exit"}:
            print(
                "Leaving All Natural. Answer was "
                f"{display_natural_gift_type_name(ch.natural_gift_type_slug)} {ch.natural_gift_power}."
            )
            return False

        ok, key, err = all_natural_parse_guess(raw, ch)
        if not key:
            print(err or "Enter both a type and a single power number (example: Fire 80).")
            continue
        if key in seen:
            print(f'You already guessed "{_display_guess_from_key(key)}".')
            continue
        seen.add(key)
        if ok:
            print(
                "Correct! It was "
                f"{display_natural_gift_type_name(ch.natural_gift_type_slug)} {ch.natural_gift_power}."
            )
            bgm.play_completion_sound()
            return True
        _wrong_guess_feedback()
        turn += 1

    print(
        "Out of guesses. Answer was "
        f"{display_natural_gift_type_name(ch.natural_gift_type_slug)} {ch.natural_gift_power}."
    )
    return False


def run_environment_map(_settings: GameSettings) -> bool | None:
    ch = build_environment_map_challenge()
    ensure_move_guess_index()
    max_guesses = _input_guess_count("How many guesses for Environment Map?", 5)
    print()
    print("Environment Map: given generation + area, name Nature Power's resulting move.")
    print(f"Generation: {ch.generation_label}")
    print(f"Environment: {ch.area_label}")
    print("Commands: quit")
    seen: set[str] = set()

    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Move ({turn}/{max_guesses}, or command): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        cmd = raw.casefold()
        if cmd in {"quit", "q", "exit"}:
            print(
                "Leaving Environment Map. Answer was "
                f"{environment_map_reveal_answer_line(ch)}."
            )
            return False

        canon = move_slug_from_user_guess(raw)
        ok, key, err = environment_map_parse_guess(canon, ch, raw)
        if not key:
            print(err or f'That does not match a known move: "{raw}".')
            continue
        if key in seen:
            print(f'You already guessed "{display_move_match_name(key)}".')
            continue
        seen.add(key)
        if ok:
            print(f"Correct! It was {environment_map_reveal_answer_line(ch)}.")
            bgm.play_completion_sound()
            return True
        _wrong_guess_feedback()
        turn += 1

    print(f"Out of guesses. Answer was {environment_map_reveal_answer_line(ch)}.")
    return False


def run_method_man(settings: GameSettings) -> bool | None:
    dex = load_dex()
    pool = dex.filtered(settings)
    if not pool:
        print("No Pokémon match your filter settings.")
        return None
    ch = build_method_man_challenge(pool)
    if ch is None:
        print("Could not build Method Man round (API issue). Try again.")
        return None

    max_guesses = _input_guess_count("How many guesses for Method Man?", 1)
    print()
    print("Method Man: identify the move's primary learn method for the shown generation.")
    print(f"Pokémon: {ch.pokemon_name}")
    print(f"Generation: {ch.generation}")
    print(f"Move: {display_move_match_name(ch.move_slug)}")
    print("Answer with one method: Level-up, Machine, Egg, or Tutor. Commands: quit")
    seen: set[str] = set()

    turn = 1
    while turn <= max_guesses:
        _last_guess_warning(turn, max_guesses)
        raw = input(f"Method ({turn}/{max_guesses}, or command): ").strip()
        if not raw:
            print("Guess cannot be blank.")
            continue
        cmd = raw.casefold()
        if cmd in {"quit", "q", "exit"}:
            print(
                "Leaving Method Man. Answer was "
                f"{display_method_man_method_name(ch.primary_method)}."
            )
            return False
        canon = method_man_parse_method_guess(raw)
        if canon is None:
            print(f'Unknown method: "{raw}". Use Level-up, Machine, Egg, or Tutor.')
            continue
        if canon in seen:
            print(f'You already guessed "{display_method_man_method_name(canon)}".')
            continue
        seen.add(canon)
        if canon == ch.primary_method:
            print(f"Correct! It was {display_method_man_method_name(ch.primary_method)}.")
            bgm.play_completion_sound()
            return True
        _wrong_guess_feedback()
        turn += 1

    print(
        "Out of guesses. Answer was "
        f"{display_method_man_method_name(ch.primary_method)}."
    )
    return False


def _route_bgm_after_game(result: bool | None) -> None:
    """Win restores menu BGM; loss or quitting a mode plays the loser theme (if configured)."""
    if result is True:
        bgm.switch_to_menu_bgm()
    elif result is False:
        bgm.switch_to_loser_bgm()


def main() -> None:
    _enable_type_color_output()
    settings = GameSettings()
    shiny_colored_menu = random.randint(1, 10) == 1
    shiny_menu_fg = ""
    if shiny_colored_menu:
        shiny_menu_fg = (
            f"\x1b[38;2;{random.randint(100, 255)};{random.randint(100, 255)};{random.randint(100, 255)}m"
        )
    bgm.setup_terminal_audio()
    bgm.configure(settings)
    if shiny_colored_menu:
        bgm.play_shiny_jingle()
    try:
        while True:
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "\n=== PokeQuiz ===")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, f"Global settings: {_settings_summary(settings)}")
            _main_menu_print(
                shiny_colored_menu,
                shiny_menu_fg,
                "Note: type 'settings' to edit filters, or 'quit' to exit.",
            )
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "Choose quiz mode:")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "1) Pokedoku")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "2) Squirdle")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "3) Pokedentities")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "4) Statle")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "5) Who's that Pokemon!?")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "6) Dexacted")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "7) Movepool Madness")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "8) Daycare Detective")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "9) Evolutionary Enigma")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "10) Ability Assessor")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "11) Level Ladder")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "12) Defensive Profile")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "13) Safari Zone")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "14) Thief's Target")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "15) Ugly Ducklett")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "16) Category Quiz")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "17) Stat Sorter")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "18) Level Race")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "19) Missing Link")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "20) EV Forensic")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "21) International Names")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "22) Growth Rate Guesstimate")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "23) EXP Yield")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "24) DexIt")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "25) Power Levels")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "26) Ability Effects")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "27) Item Lore")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "28) Move Match")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "29) Machine Serial")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "30) Fling Force")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "31) All Natural")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "32) Environment Map")
            _main_menu_print(shiny_colored_menu, shiny_menu_fg, "33) Method Man")
            choice = input("> ").strip()
            cmd = choice.casefold()
            if cmd in {"settings", "s"}:
                settings = _settings_menu(settings)
                _main_menu_print(shiny_colored_menu, shiny_menu_fg, f"Updated settings: {_settings_summary(settings)}")
                continue
            if cmd in {"quit", "q", "exit"}:
                break
            if choice == "1":
                _route_bgm_after_game(run_pokedoku(settings))
            elif choice == "2":
                _route_bgm_after_game(run_squirdle(settings))
            elif choice == "3":
                _route_bgm_after_game(run_stat_quiz(settings))
            elif choice == "4":
                _route_bgm_after_game(run_statle(settings))
            elif choice == "5":
                _route_bgm_after_game(run_whos_that_pokemon(settings))
            elif choice == "6":
                _route_bgm_after_game(run_dexacted(settings))
            elif choice == "7":
                _route_bgm_after_game(run_movepool_madness(settings))
            elif choice == "8":
                _route_bgm_after_game(run_daycare_detective(settings))
            elif choice == "9":
                _route_bgm_after_game(run_evolutionary_enigma(settings))
            elif choice == "10":
                _route_bgm_after_game(run_ability_assessor(settings))
            elif choice == "11":
                _route_bgm_after_game(run_level_ladder(settings))
            elif choice == "12":
                _route_bgm_after_game(run_defensive_profile(settings))
            elif choice == "13":
                _route_bgm_after_game(run_safari_zone(settings))
            elif choice == "14":
                _route_bgm_after_game(run_thiefs_target(settings))
            elif choice == "15":
                _route_bgm_after_game(run_odd_one_out(settings))
            elif choice == "16":
                _route_bgm_after_game(run_category_quiz(settings))
            elif choice == "17":
                _route_bgm_after_game(run_stat_sorter(settings))
            elif choice == "18":
                _route_bgm_after_game(run_level_race(settings))
            elif choice == "19":
                _route_bgm_after_game(run_missing_link(settings))
            elif choice == "20":
                _route_bgm_after_game(run_ev_forensic(settings))
            elif choice == "21":
                _route_bgm_after_game(run_international_names(settings))
            elif choice == "22":
                _route_bgm_after_game(run_growth_rate_guesstimate(settings))
            elif choice == "23":
                _route_bgm_after_game(run_exp_yield(settings))
            elif choice == "24":
                run_dex_it(settings)
            elif choice == "25":
                run_power_levels(settings)
            elif choice == "26":
                _route_bgm_after_game(run_ability_effects(settings))
            elif choice == "27":
                _route_bgm_after_game(run_item_lore(settings))
            elif choice == "28":
                _route_bgm_after_game(run_move_match(settings))
            elif choice == "29":
                _route_bgm_after_game(run_machine_serial(settings))
            elif choice == "30":
                _route_bgm_after_game(run_fling_force(settings))
            elif choice == "31":
                _route_bgm_after_game(run_all_natural(settings))
            elif choice == "32":
                _route_bgm_after_game(run_environment_map(settings))
            elif choice == "33":
                _route_bgm_after_game(run_method_man(settings))
            else:
                _main_menu_print(shiny_colored_menu, shiny_menu_fg, "Unknown choice.")
    finally:
        bgm.shutdown_terminal_audio()


if __name__ == "__main__":
    main()
