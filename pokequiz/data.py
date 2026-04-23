from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path

from pokequiz.models import GameSettings, Pokemon

CACHE_PATH = Path(".cache/pokemon_minidex.json")

GEN_LOOKUP = {
    "generation-i": 1,
    "generation-ii": 2,
    "generation-iii": 3,
    "generation-iv": 4,
    "generation-v": 5,
    "generation-vi": 6,
    "generation-vii": 7,
    "generation-viii": 8,
    "generation-ix": 9,
}

REGIONAL_KEYWORDS = {
    "-alola": (7, "alola"),
    "-galar": (8, "galar"),
    "-hisui": (8, "hisui"),
    "-paldea": (9, "paldea"),
}

NAME_ALIASES: dict[str, set[str]] = {
    "mr-mime": {"mr mime", "mrmime"},
    "mime-jr": {"mime jr", "mimejr"},
    "nidoran-f": {"nidoran♀", "nidoran f", "nidoran female"},
    "nidoran-m": {"nidoran♂", "nidoran m", "nidoran male"},
    "farfetchd": {"farfetch'd", "farfetchd"},
    "sirfetchd": {"sirfetch'd", "sirfetchd"},
    "type-null": {"type null", "typenull"},
    "jangmo-o": {"jangmo o"},
    "hakamo-o": {"hakamo o"},
    "kommo-o": {"kommo o"},
    "wo-chien": {"wo chien"},
    "chien-pao": {"chien pao"},
    "ting-lu": {"ting lu"},
    "chi-yu": {"chi yu"},
}


class Dex:
    def __init__(self, pokemon: list[Pokemon]):
        self.pokemon = pokemon
        self._by_name: dict[str, Pokemon] = {}
        for mon in pokemon:
            for nm in mon.all_names:
                self._by_name[normalize_name(nm)] = mon

    def names(self) -> list[str]:
        return [m.name for m in self.pokemon]

    def by_name(self, name: str) -> Pokemon | None:
        normalized = normalize_name(name)
        found = self._by_name.get(normalized)
        if found:
            return found

        # Fallback: try pokebase live so Squirdle can accept full dex guesses.
        mon = fetch_one_by_name(name)
        if mon:
            self.pokemon.append(mon)
            for nm in mon.all_names:
                self._by_name[normalize_name(nm)] = mon
        return mon

    def filtered(self, settings: GameSettings) -> list[Pokemon]:
        return [p for p in self.pokemon if settings.accepts(p)]


def normalize_name(name: str) -> str:
    cleaned = name.casefold().strip()
    cleaned = cleaned.replace("♀", "-f").replace("♂", "-m")
    cleaned = cleaned.replace("'", "")
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned


def _introduced_gen(name: str, default_generation: int) -> tuple[bool, bool, int, str | None]:
    if "-mega" in name:
        return True, False, 6, None
    for suffix, (gen, region) in REGIONAL_KEYWORDS.items():
        if suffix in name:
            return False, True, gen, region
    return False, False, default_generation, None


def _aliases_for_name(name: str) -> tuple[str, ...]:
    aliases = {name, name.replace("-", " ")}
    aliases.update(NAME_ALIASES.get(name, set()))
    return tuple(sorted(aliases))


def _to_pokemon(p, species, *, force_name: str | None = None, force_gen: int | None = None) -> Pokemon:
    default_gen = GEN_LOOKUP.get(species.generation.name, 1)
    name = force_name or p.name
    is_mega, is_regional, introduced_gen, region = _introduced_gen(name, default_gen)
    if force_gen is not None:
        introduced_gen = force_gen
    types = tuple(sorted(t.type.name for t in p.types))
    stats = {s.stat.name: s.base_stat for s in p.stats}

    return Pokemon(
        dex_number=species.id,
        name=name,
        generation=introduced_gen,
        introduced_generation=introduced_gen,
        types=types,
        hp=stats.get("hp", 0),
        attack=stats.get("attack", 0),
        defense=stats.get("defense", 0),
        special_attack=stats.get("special-attack", 0),
        special_defense=stats.get("special-defense", 0),
        speed=stats.get("speed", 0),
        height_dm=p.height,
        weight_hg=p.weight,
        is_mega=is_mega,
        is_regional_variant=is_regional,
        variant_region=region,
        aliases=_aliases_for_name(name),
    )


def _fetch_with_pokebase() -> list[Pokemon]:
    import pokebase as pb  # type: ignore

    mons: list[Pokemon] = []
    # Species are the canonical pokedex entries (solves evo-line generation issue).
    for dex_no in range(1, 1026):
        p = pb.pokemon(dex_no)
        species = pb.pokemon_species(dex_no)
        mons.append(_to_pokemon(p, species))

    # Add major alternate forms (megas/regionals) by explicit form names.
    extra_forms = [
        "charizard-mega-x",
        "charizard-mega-y",
        "mewtwo-mega-x",
        "mewtwo-mega-y",
        "gengar-mega",
        "kangaskhan-mega",
        "garchomp-mega",
        "lucario-mega",
        "salamence-mega",
        "latias-mega",
        "latios-mega",
        "rayquaza-mega",
        "beedrill-mega",
        "pidgeot-mega",
        "slowbro-mega",
        "steelix-mega",
        "sceptile-mega",
        "swampert-mega",
        "sableye-mega",
        "mawile-mega",
        "aggron-mega",
        "medicham-mega",
        "manectric-mega",
        "sharpedo-mega",
        "camerupt-mega",
        "altaria-mega",
        "glalie-mega",
        "absol-mega",
        "audino-mega",
        "diancie-mega",
        "venusaur-mega",
        "blastoise-mega",
        "alakazam-mega",
        "pinsir-mega",
        "gyarados-mega",
        "aerodactyl-mega",
        "ampharos-mega",
        "scizor-mega",
        "heracross-mega",
        "houndoom-mega",
        "tyranitar-mega",
        "blaziken-mega",
        "gardevoir-mega",
        "banette-mega",
        "lopunny-mega",
        "gallade-mega",
        "metagross-mega",
        "abomasnow-mega",
        "slowbro-galar",
        "slowking-galar",
        "ponyta-galar",
        "rapidash-galar",
        "farfetchd-galar",
        "weezing-galar",
        "mr-mime-galar",
        "corsola-galar",
        "zigzagoon-galar",
        "linoone-galar",
        "darumaka-galar",
        "darmanitan-galar-standard",
        "yamask-galar",
        "stunfisk-galar",
        "meowth-galar",
        "sandshrew-alola",
        "sandslash-alola",
        "vulpix-alola",
        "ninetales-alola",
        "diglett-alola",
        "dugtrio-alola",
        "meowth-alola",
        "persian-alola",
        "geodude-alola",
        "graveler-alola",
        "golem-alola",
        "grimer-alola",
        "muk-alola",
        "rattata-alola",
        "raticate-alola",
    ]

    for form_name in extra_forms:
        try:
            p = pb.pokemon(form_name)
            species = pb.pokemon_species(p.species.name)
            mons.append(_to_pokemon(p, species, force_name=form_name))
        except Exception:
            continue

    return mons


def fetch_one_by_name(name: str) -> Pokemon | None:
    try:
        import pokebase as pb  # type: ignore

        normalized = normalize_name(name)
        p = pb.pokemon(normalized)
        species = pb.pokemon_species(p.species.name)
        return _to_pokemon(p, species, force_name=normalized)
    except Exception:
        return None



def _fetch_json(url: str) -> dict:
    from urllib.request import urlopen

    with urlopen(url, timeout=20) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _fetch_with_pokeapi() -> list[Pokemon]:
    mons: list[Pokemon] = []

    for dex_no in range(1, 1026):
        p = _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{dex_no}")
        species = _fetch_json(f"https://pokeapi.co/api/v2/pokemon-species/{dex_no}")

        pseudo_p = type("P", (), {})()
        pseudo_p.name = p["name"]
        pseudo_p.types = [type("PT", (), {"type": type("T", (), {"name": t["type"]["name"]})()})() for t in p["types"]]
        pseudo_p.stats = [type("PS", (), {"stat": type("S", (), {"name": st["stat"]["name"]})(), "base_stat": st["base_stat"]})() for st in p["stats"]]
        pseudo_p.height = p["height"]
        pseudo_p.weight = p["weight"]

        pseudo_species = type("SP", (), {})()
        pseudo_species.id = species["id"]
        pseudo_species.generation = type("G", (), {"name": species["generation"]["name"]})()

        mons.append(_to_pokemon(pseudo_p, pseudo_species))

    return mons

def _fallback_data() -> list[Pokemon]:
    return [
        Pokemon(1, "bulbasaur", 1, ("grass", "poison"), 45, 49, 49, 65, 65, 45, 7, 69, aliases=("bulbasaur",)),
        Pokemon(6, "charizard", 1, ("fire", "flying"), 78, 84, 78, 109, 85, 100, 17, 905, aliases=("charizard",)),
        Pokemon(6, "charizard-mega-x", 6, ("dragon", "fire"), 78, 130, 111, 130, 85, 100, 17, 1105, is_mega=True, aliases=("charizard mega x", "charizard-mega-x")),
        Pokemon(25, "pikachu", 1, ("electric",), 35, 55, 40, 50, 50, 90, 4, 60, aliases=("pikachu",)),
        Pokemon(52, "meowth-galar", 8, ("steel",), 50, 65, 55, 40, 40, 40, 4, 75, is_regional_variant=True, variant_region="galar", aliases=("meowth galar", "meowth-galar")),
        Pokemon(94, "gengar", 1, ("ghost", "poison"), 60, 65, 60, 130, 75, 110, 15, 405, aliases=("gengar",)),
        Pokemon(150, "mewtwo", 1, ("psychic",), 106, 110, 90, 154, 90, 130, 20, 1220, aliases=("mewtwo",)),
        Pokemon(197, "umbreon", 2, ("dark",), 95, 65, 110, 60, 130, 65, 10, 270, aliases=("umbreon",)),
        Pokemon(448, "lucario", 4, ("fighting", "steel"), 70, 110, 70, 115, 70, 90, 12, 540, aliases=("lucario",)),
        Pokemon(635, "hydreigon", 5, ("dark", "dragon"), 92, 105, 90, 125, 90, 98, 18, 1600, aliases=("hydreigon",)),
        Pokemon(815, "cinderace", 8, ("fire",), 80, 116, 75, 65, 75, 119, 14, 330, aliases=("cinderace",)),
        Pokemon(1004, "ting-lu", 9, ("dark", "ground"), 155, 110, 125, 55, 80, 45, 27, 6997, aliases=("ting lu", "ting-lu")),
    ]


def load_dex(force_refresh: bool = False) -> Dex:
    if CACHE_PATH.exists() and not force_refresh:
        raw = json.loads(CACHE_PATH.read_text())
        mons = [Pokemon(**item) for item in raw]
        # Auto-refresh old tiny caches from earlier builds so quizzes use broad dex data.
        if len(mons) >= 500:
            return Dex(mons)

    try:
        mons = _fetch_with_pokebase()
    except Exception:
        try:
            mons = _fetch_with_pokeapi()
        except Exception:
            mons = _fallback_data()

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps([asdict(m) for m in mons], indent=2, default=list))
    return Dex(mons)
