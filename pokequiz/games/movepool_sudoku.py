"""Move-Pool Sudoku: fill a type grid with row/column uniqueness constraints."""

from __future__ import annotations

import random
from dataclasses import dataclass

from pokequiz.models import Pokemon


@dataclass(frozen=True, slots=True)
class MovePoolSudokuChallenge:
    size: int
    type_cycle: tuple[str, ...]  # selected type slugs used in this puzzle
    solution: tuple[tuple[str, ...], ...]  # [row][col] -> type slug
    clues: dict[tuple[int, int], str]  # (row, col) -> pokemon name


def display_type_name(type_slug: str) -> str:
    return type_slug.replace("-", " ").title()


def parse_type_guess(raw: str, allowed_types: tuple[str, ...]) -> str | None:
    s = (raw or "").strip().casefold().replace(" ", "-").replace("_", "-")
    if not s:
        return None
    for t in allowed_types:
        if s == t or s == t.replace("-", ""):
            return t
    return None


def _build_diagonal_solution(
    type_cycle: tuple[str, ...], *, max_attempts: int = 24
) -> tuple[tuple[str, ...], ...] | None:
    """
    Build a row/column/diagonal-unique square using backtracking.
    Each row is a permutation of all types.
    """
    n = len(type_cycle)
    symbols = list(type_cycle)

    for _ in range(max_attempts):
        col_used: list[set[str]] = [set() for _ in range(n)]
        diag_main_used: set[str] = set()
        diag_anti_used: set[str] = set()
        rows: list[list[str]] = []

        def fill_row(r: int) -> bool:
            if r == n:
                return True

            # Build row via column-by-column assignment from remaining symbols.
            row: list[str] = [""] * n
            remaining = set(symbols)
            col_order = list(range(n))
            random.shuffle(col_order)

            def fill_col(k: int) -> bool:
                if k == n:
                    return True
                c = col_order[k]
                candidates = [s for s in remaining if s not in col_used[c]]
                if r == c:
                    candidates = [s for s in candidates if s not in diag_main_used]
                if r + c == n - 1:
                    candidates = [s for s in candidates if s not in diag_anti_used]
                random.shuffle(candidates)
                for s in candidates:
                    row[c] = s
                    remaining.remove(s)
                    col_used[c].add(s)
                    took_main = False
                    took_anti = False
                    if r == c:
                        diag_main_used.add(s)
                        took_main = True
                    if r + c == n - 1:
                        diag_anti_used.add(s)
                        took_anti = True
                    if fill_col(k + 1):
                        return True
                    if took_main:
                        diag_main_used.remove(s)
                    if took_anti:
                        diag_anti_used.remove(s)
                    col_used[c].remove(s)
                    remaining.add(s)
                    row[c] = ""
                return False

            if not fill_col(0):
                return False
            rows.append(row.copy())
            if fill_row(r + 1):
                return True
            rows.pop()
            for c in range(n):
                s = row[c]
                if s:
                    col_used[c].remove(s)
                    if r == c:
                        diag_main_used.remove(s)
                    if r + c == n - 1:
                        diag_anti_used.remove(s)
            return False

        if fill_row(0):
            return tuple(tuple(r) for r in rows)
    return None


def build_challenge(pool: list[Pokemon], size: int, *, max_type_set_tries: int = 80) -> MovePoolSudokuChallenge | None:
    if size < 4 or size > 8 or not pool:
        return None

    buckets: dict[str, list[Pokemon]] = {}
    for mon in pool:
        for t in mon.types:
            buckets.setdefault(t, []).append(mon)
    eligible_types = [t for t, mons in buckets.items() if mons]
    if len(eligible_types) < size:
        return None

    # Retry multiple type sets because some combinations are harder to solve.
    type_cycle: tuple[str, ...] | None = None
    solution: tuple[tuple[str, ...], ...] | None = None
    for _ in range(max_type_set_tries):
        candidate = tuple(random.sample(eligible_types, size))
        solved = _build_diagonal_solution(candidate)
        if solved is None:
            continue
        type_cycle = candidate
        solution = solved
        break
    if type_cycle is None or solution is None:
        return None

    cells = [(r, c) for r in range(size) for c in range(size)]
    random.shuffle(cells)
    clue_count = min(size + 2, size * size - 1)  # leave at least one fillable cell
    clue_cells = set(cells[:clue_count])
    used_names: set[str] = set()
    clues: dict[tuple[int, int], str] = {}

    for r, c in clue_cells:
        need_type = solution[r][c]
        options = [m for m in buckets[need_type] if m.name not in used_names]
        if not options:
            options = buckets[need_type]
        if not options:
            return None
        pick = random.choice(options)
        used_names.add(pick.name)
        clues[(r, c)] = pick.name

    return MovePoolSudokuChallenge(
        size=size,
        type_cycle=type_cycle,
        solution=solution,
        clues=clues,
    )
