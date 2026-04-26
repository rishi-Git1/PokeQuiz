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

### 24) DexIt
A **higher / lower** run on **National Pokédex** numbers. You see a **Target** (with #) and a **Guess** (name only), and say whether the Guess’s Dex number is higher or lower than the Target’s. After a **correct** answer, the **Guess** becomes the next **Target**, and a new random species is drawn as the next **Guess** (so a correct call on Pikachu vs Dipplin leads into Dipplin vs the next Pokémon). A wrong answer breaks the chain and the next round starts from two fresh random species. A **session high score** (best correct streak) is shown when you open this mode. No “loser” BGM and no last-guess warning in this mode; completion SFX still plays on each correct answer (unless muted in settings).

### 25) Power Levels
Same **chained higher / lower** idea as DexIt, but using **base stat total (BST)** from the minidex (sum of base HP, Attack, Defense, Special Attack, Special Defense, and Speed). The Target shows **BST**; you compare the Guess’s BST to the Target’s. Session high score, audio behavior, and chain/reset rules match DexIt.

### 26) Ability Effects
Guess an **ability** from its English **mechanical effect** text (PokéAPI `effect_entries`). The first English description is shown with the **ability** and **source species** names redacted. Type **clue** (or `c` / `hint`) to reveal further English effect entries when more exist. Configurable guess count; **last-guess** warning and **loser** BGM follow the same rules as other guess modes.

### 27) Item Lore
Guess an **item** from English **flavor text** (PokéAPI `flavor_text_entries`). The first line is shown with the **item name** redacted; **clue** adds the next distinct English line when available. Configurable guess count; **last-guess** warning and **loser** BGM match other guess modes.

### 28) Move Match
Guess a **move** from redacted English move descriptions. The round starts with the move's **short effect**; `clue` reveals the **full effect** first, then additional Pokédex-style move flavor text lines when available. Move names are redacted in the clue text. Configurable guess count; invalid/repeat move guesses do not consume turns; last-guess warning and loser BGM match other guess modes.

### 29) Machine Serial
Guess a **move** from a machine prompt: **Generation + TM/TR code** (for example, `Generation 1, TM22`). The mode excludes HMs and includes TRs. Type `clue` to reveal manual clues in fixed order: move type, then move class (Physical/Special/Status), then move power (only for damaging moves). Configurable guess count; invalid/repeat move guesses do not consume turns; standard wrong/completion/last-guess audio behavior applies.

### 30) Fling Force
Given an **item**, guess either its **Fling Power** (integer) or its **Fling status effect** (when one exists). One manual `clue` is available and only indicates whether the interaction is **damage-only** or **status-oriented** (no exact value/effect reveal). Configurable guess count; invalid/repeat guesses do not consume turns; standard wrong/completion/last-guess audio behavior applies.

### 31) All Natural
Given a **Berry**, guess the move Natural Gift result as **Type + Base Power** in one line (for example, `Fire 80` or `80 Fire`). No clues in this mode. Configurable guess count; malformed input or unknown type text does not consume turns; repeated guesses are detected; standard wrong/completion/last-guess audio behavior applies.

### 32) Environment Map
Given a **generation + battle environment** (Nature Power context), guess the move Nature Power becomes in that scenario. Uses a curated internal mapping table (PokéAPI does not expose this mapping as a direct field). No clues in this mode. Configurable guess count; unknown move names and repeated guesses do not consume turns; standard wrong/completion/last-guess audio behavior applies.

### 33) Method Man
Given a **Pokémon**, **generation**, and **move**, guess the move's **primary learn method** in that generation (`Level-up`, `Machine`, `Egg`, or `Tutor`) using generation-specific learn-method data from move `version_group_details`. This mode is a **continuous run** with **1 guess per round** and a **session high streak** tracker (resets when app exits). No clues; unknown method text does not consume turns; standard wrong/completion audio behavior applies.

### 34) Characteristic Decoder
Given a Pokémon **Characteristic** (from the PokéAPI characteristic endpoint), guess which stat it maps to as that Pokémon's highest IV family (`HP`, `Attack`, `Defense`, `Special Attack`, `Special Defense`, or `Speed`). No clues in this mode. Configurable guess count (defaults to 2); unknown stat text and repeated guesses do not consume turns; standard wrong/completion/last-guess audio behavior applies.

### 35) "Z-Move" Signature
Given a **signature Z-Move** name, guess the Pokémon it belongs to (for example, `Oceanic Operetta` -> `Primarina`). No clues in this mode. Configurable guess count (defaults to 3); unknown or repeated guesses do not consume turns; standard wrong/completion/last-guess audio behavior applies.

### 36) Nature-Flavor Matrix
Given a **Nature**, answer which flavor the Pokémon **likes** or **dislikes** (Nature -> increased/decreased stat -> flavor mapping). No clues in this mode. Configurable guess count (defaults to 2); unknown flavor text and repeated guesses do not consume turns; standard wrong/completion/last-guess audio behavior applies.

### 37) Metronome Blacklist
Given a **move**, answer `Yes`/`No` on whether Metronome can call it. This mode is a **continuous run** with **1 guess per round** and a **session high streak** tracker (resets when app exits). Accepts `y/n` or `yes/no`. No clues; unknown input does not consume turns; standard wrong/completion audio behavior applies.

### 38) Stat Scramble
Given a **Pokémon** and its six base-stat values in scrambled order, answer which value corresponds to one requested stat (for example, Speed). This mode is a **continuous run** with **1 guess per round** and a **session high streak** tracker (resets when app exits). No clues; invalid numbers and values not in the shown set do not consume turns; standard wrong/completion audio behavior applies.

### 39) Catch & Hatch
Given a **Pokémon** and two values (`Capture Rate` and `Base Happiness`) in shuffled order, identify which value is the **Capture Rate**. This mode is a **continuous run** with **1 guess per round** and a **session high streak** tracker (resets when app exits). Invalid numbers or numbers outside the shown pair do not consume turns; standard wrong/completion audio behavior applies.

### 40) Selling Out
Given a shop-item **item**, answer its **sell price** (half of buy cost from PokéAPI `cost`). Item pools include Poké Balls, medicine/healing, status cures, revival, PP recovery, and vitamins; `Master Ball` and `Luxury Ball` are excluded. This mode is a **continuous run** with **1 guess per round** and a **session high streak** tracker (resets when app exits). No clues; invalid numeric input does not consume turns; standard wrong/completion audio behavior applies.

### 41) Mastermind
Guess a hidden **two-slot type combination** in **9 attempts**. Each guess returns exactly two feedback colors, prioritized as **Green**, then **Yellow**, then **Gray** (`Green` = right type/right slot, `Yellow` = right type/wrong slot, `Gray` = type not present). No clues in this mode. Illegal guesses (unknown type, duplicate type) and repeated guesses do not consume attempts; standard wrong/completion/last-guess audio behavior applies.

### 42) War
You and the CPU are each dealt **11 Pokémon cards** (from current filters). Each round randomly picks one base stat, then both sides play one unplayed card. Higher stat wins the round and takes both cards for scoring; ties are resolved by a **50/50 coin flip** and the winner takes both cards. Both your list and the CPU list are shown every round (CPU list in light red). No hints in this mode; no card can be played twice; standard wrong/completion audio behavior applies (loss/quit follows normal loser-music routing).

### 43) Stamina Hangman
Guess a hidden **move name** letter-by-letter with a user-chosen number of hearts (lives). At the start, the game tells you the move-name length. Input one letter per turn, or use `HINT` once to reveal the move type at a cost of **2 hearts**. You can also type `ANSWER` to attempt the full move name (case-insensitive); a failed full-answer attempt costs **2 hearts**. Wrong letter guesses cost 1 heart, repeated letters are blocked, and numeric move names are excluded from this mode.

### 44) Move-Chain Connections
A 4x4 grid of 16 move names is shown. Submit guesses as four numbers (for example, `4 5 10 13`) to find hidden groups of four connected by a shared move trait. You choose how many wrong guesses are allowed (default 4). Solved groups are shown in dark blue. If a guess is one off from a real group, you are told in orange. No repeat exact-set guesses; invalid formats do not consume attempts; standard wrong/completion/last-guess audio behavior applies.

### 45) Move-Pool Sudoku
Fill a **type grid** with row/column/diagonal uniqueness rules. Grid size is user-selected from **4x4 to 8x8** (default **4x4**). Some cells are fixed Pokémon clues; those slots are locked and consistent with a valid solved grid. You enter placements as `row col type` (or `row col type test` for a non-scoring pencil/test mark), can `clear row col`, and lose on too many wrong entries (configurable). Test entries do not count toward completion. Invalid input does not consume attempts; standard wrong/completion/last-guess audio behavior applies.

### 46) Pokemon Tetris
Single-type blocks fall in a **12x20** board and are rendered as **4x4** visual tiles. You choose drop speed (`slow` default; `medium`/`fast`) and move active blocks with arrow keys (`Left/Right`, `Down` to force drop). When blocks contact, they interact by type effectiveness (including special-case overrides like Water on Fire and Dragon on Fairy). The game ends on top-out when a new block cannot spawn at the top. Standard wrong/completion/loser-music routing applies.

## Audio (optional)

Sound uses **pygame** (`pip install pygame`). Place files under `pokequiz/assets/` (or point env vars at your own paths). In **settings**, you can mute background music, input blip, completion fanfare, and last-guess warning independently.

**Menu and modes**

- **Menu / win BGM** — default filenames `littleroot.ogg`, `littleroot.mp3`, or `littleroot.wav`. After you **win** a mode and return to the hub, this loop plays again. Override: `POKEQUIZ_BGM`. Volume: `POKEQUIZ_BGM_VOLUME` (default `0.35`).
- **Post-loss / quit BGM** — default `loser.ogg`, `loser.mp3`, or `loser.wav`. When you **lose** or **quit** a mode, menu BGM stops and this loop plays if present (otherwise BGM stays off until you win again). Override: `POKEQUIZ_LOSER_BGM`.

**Sound effects**

- **Input blip** (each line submitted) — `pokedex_select.wav` / `.ogg` / `.mp3`. Override: `POKEQUIZ_INPUT_SFX`. Volume: `POKEQUIZ_INPUT_SFX_VOLUME`.
- **Wrong guess** — `incorrect.wav` / `.ogg` / `.mp3`. Override: `POKEQUIZ_INCORRECT_SFX`. Volume: `POKEQUIZ_INCORRECT_SFX_VOLUME`.
- **Win / completion** — `completion.wav` / `.ogg` / `.mp3`. Override: `POKEQUIZ_COMPLETION_SFX`. Volume: `POKEQUIZ_COMPLETION_SFX_VOLUME`.
- **Last-guess warning** — `low_health.wav` / `.ogg` / `.mp3`. Override: `POKEQUIZ_LOW_HEALTH_SFX`. Volume: `POKEQUIZ_LOW_HEALTH_SFX_VOLUME`.
- **Shiny menu jingle** — `shiny_jingle.wav` / `.ogg` / `.mp3`; on startup, a random “shiny” colored menu and this jingle can trigger (~1 in 10) when the file exists (there is no separate mute for it in settings). Override: `POKEQUIZ_SHINY_JINGLE_SFX`. Volume: `POKEQUIZ_SHINY_JINGLE_VOLUME`.

