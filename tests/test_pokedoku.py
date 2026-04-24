from pokequiz.data import Dex
from pokequiz.games.pokedoku import Constraint, custom_constraints, format_pokedoku_grid, validate_grid_answers
from pokequiz.models import GameSettings, Pokemon


def test_duplicate_answers_rejected():
    dex = Dex(
        [
            Pokemon(6, "charizard", 1, ("fire", "flying"), 78, 84, 78, 109, 85, 100, 17, 905),
            Pokemon(59, "arcanine", 1, ("fire",), 90, 110, 80, 100, 80, 95, 19, 1550),
        ]
    )
    rows = [Constraint("type", "fire") for _ in range(3)]
    cols = [Constraint("generation", 1) for _ in range(3)]
    answers = [
        ["charizard", "charizard", "arcanine"],
        ["arcanine", "charizard", "arcanine"],
        ["charizard", "arcanine", "charizard"],
    ]
    score, marks, warning = validate_grid_answers(dex, rows, cols, answers, GameSettings())
    assert score < 9
    assert warning == "Duplicate answers are not allowed."
    assert any(not c for row in marks for c in row)


def test_name_normalization_allows_spaces_and_case():
    dex = Dex([
        Pokemon(1004, "ting-lu", 9, ("dark", "ground"), 155, 110, 125, 55, 80, 45, 27, 6997, aliases=("ting lu",)),
    ])
    rows = [Constraint("type", "dark")]
    cols = [Constraint("generation", 9)]
    score, _, _ = validate_grid_answers(dex, rows, cols, [["Ting Lu"]], GameSettings())
    assert score == 1


def test_format_pokedoku_grid_includes_labels_and_cells():
    rows = [Constraint("type", "fire"), Constraint("type", "water"), Constraint("type", "grass")]
    cols = [Constraint("generation", 1), Constraint("generation", 2), Constraint("generation", 3)]
    answers = [["a", "", "c"], ["", "b", ""], ["x", "y", "z"]]
    text = format_pokedoku_grid(rows, cols, answers)
    assert "type:fire" in text
    assert "generation:1" in text
    assert "a" in text and "b" in text and "-" in text


def test_custom_constraints_new_kinds_parse_and_match():
    rows, cols = custom_constraints(
        ["secondary_type-none", "first-letter:c", "bst-over:500"],
        ["last-letter:r", "height-under:10", "weight-over:500"],
    )
    assert rows[0].kind == "secondary_type-none"
    assert rows[0].value is None
    assert rows[1].kind == "first-letter" and rows[1].value == "c"
    assert cols[0].kind == "last-letter" and cols[0].value == "r"

    charizard = Pokemon(6, "charizard", 1, ("fire", "flying"), 78, 84, 78, 109, 85, 100, 17, 905)
    cinderace = Pokemon(815, "cinderace", 8, ("fire",), 80, 116, 75, 65, 75, 119, 14, 330)
    assert rows[0].matches(cinderace) is True
    assert rows[0].matches(charizard) is False
    assert rows[1].matches(charizard) is True
    assert rows[2].matches(charizard) is True
