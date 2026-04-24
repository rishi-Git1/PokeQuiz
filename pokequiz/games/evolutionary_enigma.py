from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name


@dataclass(frozen=True, slots=True)
class EvolutionEdge:
    from_name: str
    to_name: str
    details: dict


def _pretty(slug: str) -> str:
    return slug.replace("-", " ").title()


def _nested_name(d: dict, key: str) -> str | None:
    value = d.get(key)
    if isinstance(value, dict):
        name = value.get("name")
        return str(name) if name else None
    return None


def _walk_edges(node: dict) -> list[EvolutionEdge]:
    current = str(node.get("species", {}).get("name", ""))
    out: list[EvolutionEdge] = []
    for child in node.get("evolves_to", []):
        to_name = str(child.get("species", {}).get("name", ""))
        details_list = child.get("evolution_details", [])
        details = details_list[0] if details_list else {}
        if current and to_name:
            out.append(EvolutionEdge(from_name=current, to_name=to_name, details=details))
        out.extend(_walk_edges(child))
    return out


def _canonical_field(value):
    if isinstance(value, dict):
        name = value.get("name")
        return str(name) if name else None
    if isinstance(value, list):
        return tuple(_canonical_field(v) for v in value)
    return value


def details_signature(details: dict) -> tuple[tuple[str, object], ...]:
    """Comparable signature for matching equivalent evolution conditions."""
    pairs: list[tuple[str, object]] = []
    for key, value in details.items():
        cv = _canonical_field(value)
        if cv in (None, "", False, (), []):
            continue
        pairs.append((key, cv))
    return tuple(sorted(pairs))


@lru_cache(maxsize=2048)
def edges_for_species(name: str) -> tuple[EvolutionEdge, ...]:
    species = _fetch_json(f"https://pokeapi.co/api/v2/pokemon-species/{normalize_name(name)}")
    chain_url = str(species.get("evolution_chain", {}).get("url", ""))
    if not chain_url:
        return tuple()
    chain = _fetch_json(chain_url)
    root = chain.get("chain", {})
    return tuple(_walk_edges(root))


def clues_for_edge(edge: EvolutionEdge) -> list[str]:
    d = edge.details
    clues: list[str] = []
    trigger = str(d.get("trigger", {}).get("name", "") or "")
    min_level = d.get("min_level")

    # Special rule: if level-up is the only condition, keep as one clue.
    non_empty_keys = {
        k
        for k, v in d.items()
        if v not in (None, "", False, [], {}) and k not in {"trigger", "min_level"}
    }
    only_level = trigger == "level-up" and min_level is not None and not non_empty_keys
    if only_level:
        clues.append(f"Evolution Trigger: Level Up at level {int(min_level)}")
    else:
        if trigger:
            clues.append(f"Evolution Trigger: {_pretty(trigger)}")
        if min_level is not None:
            clues.append(f"Minimum Level: {int(min_level)}")

    held_item = _nested_name(d, "held_item")
    if held_item:
        clues.append(f"Held Item Required: {_pretty(held_item)}")

    evo_item = _nested_name(d, "item")
    if evo_item:
        clues.append(f"Evolution Item: {_pretty(evo_item)}")

    time_of_day = str(d.get("time_of_day", "") or "")
    if time_of_day:
        clues.append(f"Time of Day: {_pretty(time_of_day)}")

    location = _nested_name(d, "location")
    if location:
        clues.append(f"Location: {_pretty(location)}")

    move = _nested_name(d, "known_move")
    if move:
        clues.append(f"Known Move Required: {_pretty(move)}")

    move_type = _nested_name(d, "known_move_type")
    if move_type:
        clues.append(f"Known Move Type Required: {_pretty(move_type)}")

    party_species = _nested_name(d, "party_species")
    if party_species:
        clues.append(f"Party Species Required: {_pretty(party_species)}")

    party_type = _nested_name(d, "party_type")
    if party_type:
        clues.append(f"Party Type Required: {_pretty(party_type)}")

    trade_species = _nested_name(d, "trade_species")
    if trade_species:
        clues.append(f"Trade With Species: {_pretty(trade_species)}")

    gender = d.get("gender")
    if gender is not None:
        gender_label = {1: "Female", 2: "Male"}.get(int(gender), f"Code {gender}")
        clues.append(f"Required Gender: {gender_label}")

    for raw_key, label in (
        ("min_happiness", "Minimum Happiness"),
        ("min_affection", "Minimum Affection"),
        ("min_beauty", "Minimum Beauty"),
    ):
        if d.get(raw_key) is not None:
            clues.append(f"{label}: {int(d[raw_key])}")

    if d.get("needs_overworld_rain"):
        clues.append("Overworld Condition: Rain required")
    if d.get("turn_upside_down"):
        clues.append("Special Condition: Device turned upside down")

    rel = d.get("relative_physical_stats")
    if rel is not None:
        text = {1: "Attack > Defense", 0: "Attack = Defense", -1: "Attack < Defense"}.get(int(rel), str(rel))
        clues.append(f"Stat Relationship: {text}")

    if not clues:
        clues.append("Evolution data exists, but no specific conditions were provided by the API.")
    return clues


def build_challenge(pool_names: list[str]) -> tuple[EvolutionEdge, list[str]]:
    candidates = pool_names[:]
    random.shuffle(candidates)
    for name in candidates:
        try:
            edges = list(edges_for_species(name))
        except Exception:
            continue
        if not edges:
            continue
        edge = random.choice(edges)
        clues = clues_for_edge(edge)
        if clues:
            random.shuffle(clues)
            return edge, clues
    raise ValueError("Could not find evolution-chain data for this filter set.")


def valid_answer_names_for_signature(pool_names: list[str], signature: tuple[tuple[str, object], ...]) -> set[str]:
    names: set[str] = set()
    for name in pool_names:
        try:
            edges = edges_for_species(name)
        except Exception:
            continue
        for edge in edges:
            if details_signature(edge.details) == signature:
                names.add(edge.from_name)
                names.add(edge.to_name)
    return names


def guess_matches_signature(name: str, signature: tuple[tuple[str, object], ...]) -> bool:
    """Fast per-guess check: does this species chain contain any edge with the same condition signature?"""
    try:
        edges = edges_for_species(name)
    except Exception:
        return False
    return any(details_signature(edge.details) == signature for edge in edges)

