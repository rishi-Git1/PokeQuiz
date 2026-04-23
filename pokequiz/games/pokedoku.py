from __future__ import annotations

import random
from dataclasses import dataclass

from pokequiz.data import Dex
from pokequiz.models import GameSettings, Pokemon


@dataclass(slots=True)
class Constraint:
    kind: str
    value: str | int | bool

    def matches(self, mon: Pokemon) -> bool:
        if self.kind == "type":
            return str(self.value) in mon.types
        if self.kind == "generation":
            return int(self.value) == mon.generation
        if self.kind == "mega":
            required = bool(self.value)
            return mon.is_mega == required
        if self.kind == "regional":
            required = bool(self.value)
            return mon.is_regional_variant == required
        return False

    @property
    def label(self) -> str:
        return f"{self.kind}:{self.value}"


def random_constraints(dex: Dex, settings: GameSettings) -> tuple[list[Constraint], list[Constraint]]:
    mons = dex.filtered(settings)
    types = sorted({t for m in mons for t in m.types})
    gens = sorted({m.generation for m in mons})
    if not types or not gens:
        raise ValueError("No Pokémon match your filters; cannot build a random Pokedoku grid.")

    def pick_three(values: list) -> list:
        # Grids are always 3×3; with a small dex there may be fewer than three distinct types or gens.
        if len(values) >= 3:
            return random.sample(values, k=3)
        return random.choices(values, k=3)

    row = [Constraint("type", v) for v in pick_three(types)]
    col = [Constraint("generation", v) for v in pick_three(gens)]
    return row, col


def custom_constraints(rows: list[str], cols: list[str]) -> tuple[list[Constraint], list[Constraint]]:
    def parse(raw: str) -> Constraint:
        kind, value = [r.strip() for r in raw.split(":", maxsplit=1)]
        if kind == "generation":
            return Constraint(kind, int(value))
        if kind in {"mega", "regional"}:
            return Constraint(kind, value.casefold() in {"1", "true", "yes", "y"})
        return Constraint(kind, value.casefold())

    return [parse(r) for r in rows], [parse(c) for c in cols]


def format_pokedoku_grid(
    row_constraints: list[Constraint],
    col_constraints: list[Constraint],
    answers: list[list[str]],
    *,
    col_width: int = 16,
    label_col_width: int = 18,
) -> str:
    """ASCII table: column categories across the top, row categories down the left, 3×3 answers."""
    lines: list[str] = []

    def trunc(s: str, w: int) -> str:
        s = s.strip()
        if len(s) <= w:
            return s
        return s[: w - 2] + ".."

    def cell_display(raw: str) -> str:
        raw = raw.strip()
        return trunc(raw, col_width) if raw else "-"

    col_heads = [trunc(c.label, col_width) for c in col_constraints]
    corner = "".ljust(label_col_width)
    top = corner + "".join(f"| {h.center(col_width)} " for h in col_heads) + "|"
    lines.append(top)

    data_lines: list[str] = []
    for r_idx, r in enumerate(row_constraints):
        row_label = trunc(r.label, label_col_width).ljust(label_col_width)
        parts = [row_label]
        for c_idx in range(3):
            parts.append(f"| {cell_display(answers[r_idx][c_idx]).center(col_width)} ")
        parts.append("|")
        data_lines.append("".join(parts))

    width = max(len(top), *(len(dl) for dl in data_lines))
    lines.append("-" * width)
    lines.extend(data_lines)

    return "\n".join(lines)


def validate_grid_answers(
    dex: Dex,
    row_constraints: list[Constraint],
    col_constraints: list[Constraint],
    answers: list[list[str]],
    settings: GameSettings,
) -> tuple[int, list[list[bool]], str | None]:
    seen: set[str] = set()
    marks: list[list[bool]] = []
    score = 0
    had_duplicate = False

    for r_idx, r in enumerate(row_constraints):
        row_marks: list[bool] = []
        for c_idx, c in enumerate(col_constraints):
            name = answers[r_idx][c_idx].strip()
            mon = dex.by_name(name)
            duplicate = bool(mon and mon.name in seen)
            valid = bool(
                mon
                and settings.accepts(mon)
                and r.matches(mon)
                and c.matches(mon)
                and not duplicate
            )
            if duplicate:
                had_duplicate = True
            if valid and mon:
                seen.add(mon.name)
                score += 1
            row_marks.append(valid)
        marks.append(row_marks)

    if had_duplicate:
        return score, marks, "Duplicate answers are not allowed."
    return score, marks, None
