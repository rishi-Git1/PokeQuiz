# PokeQuiz

PokeQuiz is a multi-mode Pokémon quiz project using PokeAPI data through **pokebase** (with an offline fallback mini-dex for local development).

## Included quiz modes

- **Pokedoku** grid mode with random or fully custom row/column constraints.
- **Squirdle-inspired** comparison guessing game.
- **Stat identity quiz** (guess the Pokémon from base stats).
- **Statle-inspired** per-Pokémon stat-pick mode (choose one stat from each revealed Pokémon, and each stat can only be chosen once per run).

## Rules implemented from your requirements

- Mega forms are treated as **Generation 6** entries.
- Regional variants are treated as the generation they debuted.
- No duplicate answers allowed in a Pokedoku grid, with duplicate feedback shown.
- Evolutions are represented by their own introduction generation (species-level generation), not by their evolutionary line start.
- Players can choose which quiz to play from the main menu.
- Players can make custom Pokedoku grids.

## Run

```bash
python -m pokequiz.cli
```

or after install:

```bash
pip install -e .
pokequiz
```

## Pokedoku custom constraint format

Use `kind:value` for each row/column item.

Supported `kind` values:

- `type` (example: `type:fire`)
- `generation` (example: `generation:4`)
- `mega` (example: `mega:true`)
- `regional` (example: `regional:true`)


## Notes

- Name matching is forgiving (case-insensitive and punctuation/space tolerant, e.g. `Ting Lu` matches `ting-lu`).
- Squirdle guesses can live-fetch Pokémon not yet in local cache through pokebase.
- If pokebase bulk loading fails, the loader attempts direct PokeAPI fetch before using local fallback data.
