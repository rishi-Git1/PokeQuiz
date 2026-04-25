# PokeQuiz

PokeQuiz is a terminal-based collection of Pokemon quiz and deduction modes powered by PokeAPI (with `pokebase` support and local caching).

## Requirements

- Python `>=3.11`
- Internet access for live API-backed modes

## Install

```bash
python -m pip install -e .
```

This installs the project plus runtime dependencies:

- `pokebase`
- `pillow` (for ASCII sprite rendering)

## Run

Use either command:

```bash
python -m pokequiz.cli
```

or:

```bash
pokequiz
```

## Main Menu Notes

- Global filters (megas, regionals, generations) are shared by all modes.
- At the main prompt:
  - type `settings` to edit filters
  - type `quit` to exit

## Data Notes

Dex loading order:

1. local cache (`.cache/pokemon_minidex.json`) if large enough
2. `pokebase` bulk fetch
3. direct PokeAPI fallback
4. tiny emergency fallback list

Name matching is tolerant of punctuation/case/spacing in most guess-based modes.

## Game Modes

### 1) Pokedoku
Build or auto-generate a 3x3 constraint grid and fill each cell with a valid Pokemon. Supports command-driven board editing and custom constraints (`type`, `generation`, BST/height/weight bounds, first/last letter, `secondary_type-none`).

### 2) Squirdle
Guess the target with directional comparisons (generation/height/weight/BST) plus positional type-slot feedback and cross-slot type hints.

### 3) Pokedentities
Guess the Pokemon from base stats. Guess count is configurable per run.

### 4) Statle
Choose one unused stat per round across six revealed Pokemon, then compare your total to the optimal assignment. Includes optional ASCII sprite rendering.

### 5) Who's that Pokemon!?
Sprite-first guessing mode: identify the hidden Pokemon from its rendered sprite.

### 6) Dexacted
Guess from Pokédex flavor text entries. Entries can be revealed one-by-one, and the target name is redacted with fixed `-------`.

### 7) Movepool Madness
Given four moves, guess any Pokemon that can legally learn all four (level-up, machine, or egg).

### 8) Daycare Detective
Deduce from breeding/species metadata: egg groups, gender ratio, hatch counter, capture rate.

### 9) Evolutionary Enigma
Guess from evolution trigger conditions (item/time/location/happiness/etc.). Clues are user-revealed; any guess matching the condition signature is accepted.

### 10) Ability Assessor
Guess based on Ability 1 / Ability 2 / Hidden Ability combination. Clues are manually revealed.

### 11) Level Ladder
Deduce from a Pokemon’s level-up learnset sequence. Includes normal and reverse progression modes with manual clue reveal.

### 12) Defensive Profile
Guess from full defensive multiplier grouping (immunities, 4x/2x weaknesses, 0.5x/0.25x resistances). All clues shown up front.

### 13) Safari Zone
Guess from wild encounter location+method clues (`encounters` endpoint). Clues are revealed on request.

### 14) Thief's Target
Guess from wild held-item drop profile and rarity percentages. All clues shown up front.

### 15) Ugly Ducklett
Odd-one-out logic puzzle: one listed Pokemon does not share the hidden trait. Supports variable list size and many trait families (typing, stats, naming, ability, egg groups, capture-rate band).

### 16) Category Quiz
Anchored on Pokédex species category/genus plus user-selected clue fields (color, egg groups, type, generation, ability, etc.). Clues are manually chosen by the player.

### 17) Stat Sorter
Sort 3-8 randomly selected Pokemon by a random stat in descending order using one-line order input.

### 18) Level Race
Given one move and 2-5 Pokemon options, submit the correct full order by lowest level learned to highest.

### 19) Missing Link
One move is redacted from a level-up table; guess the missing move. Optional manual clues: type, damage class, then power (if damaging).

### 20) EV Forensic
Deduce the species from EV yields shown up front, plus optional manually chosen species clues (generation, types, evolution stage, color, egg groups, primary ability, capture-rate band).

### 21) International Names
Guess the English species name from PokéAPI `ja-roma` (romanized Japanese), with optional one-at-a-time name clues in other languages.

### 22) Growth Rate Guesstimate
Three species are shown as A/B/C. Each round asks you to order them either **slowest → fastest** or **fastest → slowest** leveling, using total experience at level 100 from PokéAPI growth-rate data. Submit **one line with all three** (e.g. `B C A`, or three names/letters), with no mid-round hints.

### 23) EXP Yield
You choose how many species to compare (2–8, capped by your current filter). Each round asks which gives the **most** or **least** base experience when defeated, using the PokéAPI **base_experience** field (in-game reward scales with level). All listed species have distinct base experience so there is a single correct answer. No mid-round hints.

## Audio (optional)

Sound uses **pygame** (`pip install pygame`). Place files under `pokequiz/assets/` (or point env vars at your own paths). In **settings**, you can mute background music, input blip, completion fanfare, and last-guess warning independently.

**Menu and modes**

- **Menu / win BGM** — default filenames `littleroot.ogg`, `littleroot.mp3`, or `littleroot.wav`. After you **win** a mode and return to the hub, this loop plays again. Override: `POKEQUIZ_BGM`. Volume: `POKEQUIZ_BGM_VOLUME` (default `0.35`).
- **Post-loss / quit BGM** — default `loser.ogg`, `loser.mp3`, or `loser.wav`. When you **lose** or **quit** a mode, menu BGM stops and this loop plays if present (otherwise BGM stays off until you win again). Override: `POKEQUIZ_LOSER_BGM`.

**Sound effects**

- **Input blip** (each line submitted) — `pokedex_select.wav` / `.ogg` / `.mp3`. Override: `POKEQUIZ_INPUT_SFX`. Volume: `POKEQUIZ_INPUT_SFX_VOLUME`.
- **Win / completion** — `completion.wav` / `.ogg` / `.mp3`. Override: `POKEQUIZ_COMPLETION_SFX`. Volume: `POKEQUIZ_COMPLETION_SFX_VOLUME`.
- **Last-guess warning** — `low_health.wav` / `.ogg` / `.mp3`. Override: `POKEQUIZ_LOW_HEALTH_SFX`. Volume: `POKEQUIZ_LOW_HEALTH_SFX_VOLUME`.
- **Shiny menu jingle** — `shiny_jingle.wav` / `.ogg` / `.mp3`; on startup, a random “shiny” colored menu and this jingle can trigger (~1 in 10) when the file exists (there is no separate mute for it in settings). Override: `POKEQUIZ_SHINY_JINGLE_SFX`. Volume: `POKEQUIZ_SHINY_JINGLE_VOLUME`.

