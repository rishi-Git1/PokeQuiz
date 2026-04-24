from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

from pokequiz.data import _fetch_json, normalize_name
from pokequiz.models import Pokemon


@dataclass(frozen=True, slots=True)
class OddOneOutChallenge:
    names: list[str]
    odd_index: int
    trait_explanation: str


@dataclass(frozen=True, slots=True)
class TraitOption:
    code: str
    description: str
    key_fn: Callable[[Pokemon], str]
    explain_fn: Callable[[str], str]
    expensive: bool = False


def _primary_type(mon: Pokemon) -> str:
    return mon.types[0] if mon.types else "none"


def _secondary_type(mon: Pokemon) -> str:
    return mon.types[1] if len(mon.types) > 1 else "none"


def _typing_arity(mon: Pokemon) -> str:
    return "dual-type" if len(mon.types) > 1 else "mono-type"


def _bst_band(mon: Pokemon) -> str:
    v = mon.bst
    if v < 400:
        return "<400"
    if v < 500:
        return "400-499"
    if v < 600:
        return "500-599"
    return "600+"


def _speed_band(mon: Pokemon) -> str:
    v = mon.speed
    if v < 60:
        return "<60"
    if v < 100:
        return "60-99"
    return "100+"


def _weight_band(mon: Pokemon) -> str:
    v = mon.weight_hg
    if v < 1000:
        return "light"
    if v < 3000:
        return "midweight"
    return "heavy"


def _height_band(mon: Pokemon) -> str:
    v = mon.height_dm
    if v < 10:
        return "short"
    if v < 20:
        return "medium"
    return "tall"


def _starts_with(mon: Pokemon) -> str:
    return mon.name[0] if mon.name else "?"


def _ends_with(mon: Pokemon) -> str:
    return mon.name[-1] if mon.name else "?"


def _name_length(mon: Pokemon) -> str:
    return str(len(mon.name))


@lru_cache(maxsize=4096)
def _pokemon_payload(name: str) -> dict:
    return _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{normalize_name(name)}")


@lru_cache(maxsize=4096)
def _species_payload(name: str) -> dict:
    return _fetch_json(f"https://pokeapi.co/api/v2/pokemon-species/{normalize_name(name)}")


def _primary_ability(mon: Pokemon) -> str:
    try:
        payload = _pokemon_payload(mon.name)
    except Exception:
        return "unknown-ability"
    for entry in payload.get("abilities", []):
        if entry.get("is_hidden"):
            continue
        if int(entry.get("slot", 0) or 0) == 1:
            name = entry.get("ability", {}).get("name")
            if name:
                return str(name)
    return "unknown-ability"


def _egg_group_signature(mon: Pokemon) -> str:
    try:
        payload = _species_payload(mon.name)
    except Exception:
        return "unknown-egg-group"
    groups = [g.get("name") for g in payload.get("egg_groups", []) if g.get("name")]
    if not groups:
        return "unknown-egg-group"
    return "|".join(sorted(str(g) for g in groups))


def _capture_rate_band(mon: Pokemon) -> str:
    try:
        payload = _species_payload(mon.name)
    except Exception:
        return "unknown-capture-rate"
    v = int(payload.get("capture_rate", -1))
    if v < 0:
        return "unknown-capture-rate"
    if v < 50:
        return "very-low"
    if v < 100:
        return "low"
    if v < 150:
        return "medium"
    return "high"


TRAIT_OPTIONS: tuple[TraitOption, ...] = (
    TraitOption("generation", "same generation", lambda m: str(m.generation), lambda v: f"same generation ({v})"),
    TraitOption("primary_type", "same primary type", _primary_type, lambda v: f"same primary type ({v})"),
    TraitOption("secondary_type", "same secondary type", _secondary_type, lambda v: f"same secondary type ({v})"),
    TraitOption("typing_arity", "same mono/dual typing", _typing_arity, lambda v: f"same typing arity ({v})"),
    TraitOption("bst_band", "same BST band", _bst_band, lambda v: f"same BST band ({v})"),
    TraitOption("speed_band", "same speed band", _speed_band, lambda v: f"same speed band ({v})"),
    TraitOption("weight_band", "same weight class", _weight_band, lambda v: f"same weight class ({v})"),
    TraitOption("height_band", "same height class", _height_band, lambda v: f"same height class ({v})"),
    TraitOption("starts_with", "same first letter", _starts_with, lambda v: f"same first letter ({v})"),
    TraitOption("ends_with", "same last letter", _ends_with, lambda v: f"same last letter ({v})"),
    TraitOption("name_length", "same name length", _name_length, lambda v: f"same name length ({v})"),
    TraitOption(
        "primary_ability",
        "same primary ability",
        _primary_ability,
        lambda v: f"same primary ability ({v})",
        expensive=True,
    ),
    TraitOption(
        "egg_group",
        "same egg group combo",
        _egg_group_signature,
        lambda v: f"same egg group combo ({v})",
        expensive=True,
    ),
    TraitOption(
        "capture_rate_band",
        "same catch-rate band",
        _capture_rate_band,
        lambda v: f"same catch-rate band ({v})",
        expensive=True,
    ),
)


def _is_usable_key(key: str) -> bool:
    return bool(key and not key.startswith("unknown"))


def _try_build_for_trait(trait: TraitOption, pool: list[Pokemon], total_choices: int) -> OddOneOutChallenge | None:
    need_shared = total_choices - 1
    # Expensive traits hit API-backed key functions; cap evaluations for responsiveness.
    max_eval = min(len(pool), 180 if trait.expensive else len(pool))
    sample = pool[:]
    random.shuffle(sample)
    sample = sample[:max_eval]

    keyed: list[tuple[Pokemon, str]] = []
    groups: dict[str, list[Pokemon]] = {}
    for mon in sample:
        key = trait.key_fn(mon)
        if not _is_usable_key(key):
            continue
        keyed.append((mon, key))
        groups.setdefault(key, []).append(mon)

    keys = list(groups.keys())
    random.shuffle(keys)
    for key in keys:
        shared = groups[key]
        if len(shared) < need_shared:
            continue
        outsiders = [m for m, k in keyed if k != key]
        if not outsiders:
            continue

        picks = random.sample(shared, k=need_shared)
        odd = random.choice(outsiders)
        names = [m.name for m in picks] + [odd.name]
        random.shuffle(names)
        return OddOneOutChallenge(
            names=names,
            odd_index=names.index(odd.name),
            trait_explanation=trait.explain_fn(key),
        )
    return None


def build_challenge(pool: list[Pokemon], total_choices: int) -> OddOneOutChallenge:
    if total_choices < 3:
        raise ValueError("Odd One Out needs at least 3 choices.")
    if len(pool) < total_choices:
        raise ValueError("Not enough Pokémon in current filter for this game size.")

    # Try cheaper/local traits first for speed, then expensive API-backed traits.
    cheap_traits = [t for t in TRAIT_OPTIONS if not t.expensive]
    expensive_traits = [t for t in TRAIT_OPTIONS if t.expensive]
    random.shuffle(cheap_traits)
    random.shuffle(expensive_traits)
    trait_list = cheap_traits + expensive_traits

    for trait in trait_list:
        challenge = _try_build_for_trait(trait, pool, total_choices)
        if challenge is not None:
            return challenge

    # Fallback: if capped sampling missed a valid set, do one full pass on expensive traits.
    for trait in expensive_traits:
        full_attempt = _try_build_for_trait(
            TraitOption(trait.code, trait.description, trait.key_fn, trait.explain_fn, expensive=False),
            pool,
            total_choices,
        )
        if full_attempt is not None:
            return full_attempt

    raise ValueError("Could not build an Odd One Out set from current filters.")

