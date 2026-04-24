# PokeQuiz

PokeQuiz is a terminal-based, multi-mode Pokemon quiz game powered by PokeAPI data (with `pokebase` support and robust fallbacks).

## Game Modes

- **Pokedoku (3x3)**  
  Fill a 3x3 board where each cell must satisfy one row constraint and one column constraint.
- **Squirdle-style guessing**  
  Guess the target Pokemon with directional feedback (generation, height, weight, BST) plus slot-based type feedback.
- **Stat Identity Quiz**  
  Guess the Pokemon from base stats with progressive hinting.
- **Statle Builder**  
  Six rounds, one revealed Pokemon per round, pick one unused stat each round, then see your final score and the mathematically optimal score/path.

## Data Loading

`load_dex()` uses this order:

1. Existing local cache (`.cache/pokemon_minidex.json`) if it is large enough.
2. `pokebase` bulk fetch.
3. Direct PokeAPI fetch (with a custom User-Agent).
4. Tiny emergency fallback list.

Notes:

- Tiny fallback data is **not** persisted as a cache.
- Name matching is forgiving (case/spacing/punctuation tolerant; e.g. `Ting Lu` matches `ting-lu`).
- Unknown guesses are echoed back to the player in guessing modes.

## Install

Python 3.11+ is required.

```bash
python -m pip install -e .
```

Dependencies include:

- `pokebase`
- `pillow` (used for Statle ASCII sprite rendering)

## Run

```bash
python -m pokequiz.cli
```

or via script entrypoint:

```bash
pokequiz
```

## Pokedoku

### Board Input Commands

During board entry:

- `<row> <col> <pokemon name>`: set/replace a cell
- `clear <row> <col>` (also `c` or `x`): clear a cell
- `done`: score board
- `help` or `syntax`: show command and constraint syntax

The board is re-rendered before each input, with row/column constraints and current answers.

### Custom Constraint Syntax

Provide 3 row constraints and 3 column constraints.

- Standard format: `kind:value`
- Special no-value format: `secondary_type-none`

Supported kinds:

- `type` (example: `type:fire`)
- `generation` (example: `generation:4`)
- `bst-over` / `bst-under` (example: `bst-over:500`)
- `height-over` / `height-under` (example: `height-under:15`)
- `weight-over` / `weight-under` (example: `weight-over:1000`)
- `first-letter` / `last-letter` (single letter; example: `first-letter:c`)
- `secondary_type-none`

Scoring rules:

- Duplicate Pokemon answers in the same board are not allowed.
- Answers must satisfy both intersecting constraints and current game filters.

## Squirdle Feedback

Each valid guess returns:

- Generation: `higher` / `lower` / `equal`
- Height: `higher` / `lower` / `equal`
- Weight: `higher` / `lower` / `equal`
- BST: `higher` / `lower` / `equal`
- Type slot 1: `correct` / `incorrect` + guessed slot value
- Type slot 2: `correct` / `incorrect` + guessed slot value (`none` for mono-type)
- Cross-slot hints when relevant:
  - guessed type 2 matches answer type 1
  - guessed type 1 matches answer type 2

## Statle Sprites

Statle attempts to render each round's Pokemon sprite as ASCII art.

If sprites do not appear, install Pillow into the same interpreter used to run the game:

```bash
python -m pip install pillow
```

(If using a virtual environment, run that command with the venv's Python executable.)

