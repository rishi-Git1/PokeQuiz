"""Z-Move Signature: map signature Z-Move names to their Pokémon."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ZMoveSignatureChallenge:
    zmove_name: str
    pokemon_name: str


# Curated signature Z-Move -> Pokémon mapping (Gen 7).
_ZMOVE_SIGNATURES: tuple[ZMoveSignatureChallenge, ...] = (
    ZMoveSignatureChallenge("Catastropika", "pikachu"),
    ZMoveSignatureChallenge("Sinister Arrow Raid", "decidueye"),
    ZMoveSignatureChallenge("Malicious Moonsault", "incineroar"),
    ZMoveSignatureChallenge("Oceanic Operetta", "primarina"),
    ZMoveSignatureChallenge("Soul-Stealing 7-Star Strike", "marshadow"),
    ZMoveSignatureChallenge("Stoked Sparksurfer", "raichu-alola"),
    ZMoveSignatureChallenge("Pulverizing Pancake", "snorlax"),
    ZMoveSignatureChallenge("Extreme Evoboost", "eevee"),
    ZMoveSignatureChallenge("Genesis Supernova", "mew"),
    ZMoveSignatureChallenge("10,000,000 Volt Thunderbolt", "pikachu"),
    ZMoveSignatureChallenge("Light That Burns the Sky", "necrozma"),
    ZMoveSignatureChallenge("Searing Sunraze Smash", "necrozma-dusk-mane"),
    ZMoveSignatureChallenge("Menacing Moonraze Maelstrom", "necrozma-dawn-wings"),
    ZMoveSignatureChallenge("Let's Snuggle Forever", "mimikyu"),
    ZMoveSignatureChallenge("Splintered Stormshards", "lycanroc"),
    ZMoveSignatureChallenge("Clangorous Soulblaze", "kommo-o"),
)


def build_challenge() -> ZMoveSignatureChallenge:
    return random.choice(_ZMOVE_SIGNATURES)


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.casefold())


def parse_guess(raw: str, ch: ZMoveSignatureChallenge) -> tuple[bool, str, str | None]:
    """
    Returns (is_correct, canonical_guess_key, error_message).
    Empty key means invalid format.
    """
    s = (raw or "").strip()
    if not s:
        return False, "", "Guess cannot be blank."
    key = _normalize(s)
    if not key:
        return False, "", f'Could not parse "{raw}".'

    target = _normalize(ch.pokemon_name)
    # Small alias support for common regional form text.
    aliases: dict[str, set[str]] = {
        "raichualola": {"alolanraichu"},
        "necrozmaduskmane": {"duskmane", "duskmane necrozma"},
        "necrozmadawnwings": {"dawnwings", "dawnwings necrozma"},
    }
    ok = key == target or key in aliases.get(target, set())
    return ok, key, None
