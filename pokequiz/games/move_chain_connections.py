"""Move-Chain Connections: build 4x4 move group puzzle."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MoveConnectionGroup:
    key: str
    label: str
    moves: tuple[str, str, str, str]  # move slugs


@dataclass(frozen=True, slots=True)
class MoveConnectionsChallenge:
    groups: tuple[MoveConnectionGroup, MoveConnectionGroup, MoveConnectionGroup, MoveConnectionGroup]
    grid_moves: tuple[str, ...]  # 16 move slugs in display order


def display_move_name(slug: str) -> str:
    return slug.replace("-", " ").title()


# Curated pools for reliable 4x4 generation.
# Constraint: a move must appear in only one category in this file.
_GROUP_POOLS: tuple[MoveConnectionGroup, ...] = (
    MoveConnectionGroup(
        key="flinch10_a",
        label="10% flinch chance moves",
        moves=("bite", "rock-slide", "headbutt", "extrasensory"),
    ),
    MoveConnectionGroup(
        key="flinch10_b",
        label="10% flinch chance moves",
        moves=("waterfall", "stomp", "steamroller", "needle-arm"),
    ),
    MoveConnectionGroup(
        key="multihit25_a",
        label="Hit 2-5 times",
        moves=("bullet-seed", "icicle-spear", "tail-slap", "fury-attack"),
    ),
    MoveConnectionGroup(
        key="multihit25_b",
        label="Hit 2-5 times",
        moves=("pin-missile", "rock-blast", "arm-thrust", "double-slap"),
    ),
    MoveConnectionGroup(
        key="punch_a",
        label='Moves with "Punch" in the name',
        moves=("fire-punch", "ice-punch", "thunder-punch", "drain-punch"),
    ),
    MoveConnectionGroup(
        key="punch_b",
        label='Moves with "Punch" in the name',
        moves=("focus-punch", "comet-punch", "dizzy-punch", "shadow-punch"),
    ),
    MoveConnectionGroup(
        key="selfdrop_a",
        label="Lower user's stats",
        moves=("overheat", "close-combat", "leaf-storm", "draco-meteor"),
    ),
    MoveConnectionGroup(
        key="selfdrop_b",
        label="Lower user's stats",
        moves=("superpower", "hammer-arm", "v-create", "psycho-boost"),
    ),
    MoveConnectionGroup(
        key="priority_a",
        label="Positive-priority moves",
        moves=("quick-attack", "aqua-jet", "mach-punch", "vacuum-wave"),
    ),
    MoveConnectionGroup(
        key="priority_b",
        label="Positive-priority moves",
        moves=("shadow-sneak", "bullet-punch", "ice-shard", "sucker-punch"),
    ),
    MoveConnectionGroup(
        key="status100",
        label="100% status infliction moves",
        moves=("thunder-wave", "will-o-wisp", "toxic", "spore"),
    ),
    MoveConnectionGroup(
        key="power80_a",
        label="Base power 80",
        moves=("dark-pulse", "shadow-ball", "iron-head", "x-scissor"),
    ),
    MoveConnectionGroup(
        key="water_type",
        label="Water-type moves",
        moves=("hydro-pump", "surf", "water-pulse", "aqua-tail"),
    ),
    MoveConnectionGroup(
        key="same_status_para_a",
        label="Can paralyze the target",
        moves=("nuzzle", "zap-cannon", "body-slam", "force-palm"),
    ),
    MoveConnectionGroup(
        key="same_status_para_b",
        label="Can paralyze the target",
        moves=("stun-spore", "glare", "thunder-fang", "dragon-breath"),
    ),
    MoveConnectionGroup(
        key="status_chance_30_a",
        label="30% chance to inflict a status",
        moves=("scald", "poison-jab", "discharge", "spark"),
    ),
    MoveConnectionGroup(
        key="status_chance_30_b",
        label="30% chance to inflict a status",
        moves=("sludge-bomb", "lava-plume", "tri-attack", "cross-poison"),
    ),
    MoveConnectionGroup(
        key="dragon_type_a",
        label="Dragon-type moves",
        moves=("dragon-claw", "dragon-pulse", "dragon-rush", "outrage"),
    ),
    MoveConnectionGroup(
        key="dragon_type_b",
        label="Dragon-type moves",
        moves=("twister", "dragon-tail", "breaking-swipe", "dual-chop"),
    ),
    MoveConnectionGroup(
        key="gen6_intro_a",
        label="Introduced in Generation 6",
        moves=("moonblast", "dazzling-gleam", "play-rough", "draining-kiss"),
    ),
    MoveConnectionGroup(
        key="gen6_intro_b",
        label="Introduced in Generation 6",
        moves=("spiky-shield", "oblivion-wing", "thousand-arrows", "thousand-waves"),
    ),
    MoveConnectionGroup(
        key="self_raises_a",
        label="Raises the user's stats",
        moves=("calm-mind", "bulk-up", "agility", "amnesia"),
    ),
    MoveConnectionGroup(
        key="self_raises_b",
        label="Raises the user's stats",
        moves=("swords-dance", "nasty-plot", "iron-defense", "quiver-dance"),
    ),
    MoveConnectionGroup(
        key="spread_moves_a",
        label="Spread moves in doubles/triples",
        moves=("heat-wave", "muddy-water", "blizzard", "struggle-bug"),
    ),
    MoveConnectionGroup(
        key="spread_moves_b",
        label="Spread moves in doubles/triples",
        moves=("earthquake", "icy-wind", "swift", "snarl"),
    ),
    MoveConnectionGroup(
        key="pp5_a",
        label="Base PP 5",
        moves=("fire-blast", "thunder", "megahorn", "hyper-beam"),
    ),
    MoveConnectionGroup(
        key="pp5_b",
        label="Base PP 5",
        moves=("mega-kick", "mega-punch", "high-jump-kick", "jump-kick"),
    ),
)


def _validate_unique_moves() -> None:
    seen: dict[str, str] = {}
    for g in _GROUP_POOLS:
        for m in g.moves:
            if m in seen:
                raise ValueError(f"Move '{m}' appears in both '{seen[m]}' and '{g.key}'.")
            seen[m] = g.key


_validate_unique_moves()


def build_challenge(*, max_attempts: int = 200) -> MoveConnectionsChallenge:
    pools = list(_GROUP_POOLS)
    for _ in range(max_attempts):
        random.shuffle(pools)
        chosen: list[MoveConnectionGroup] = []
        used: set[str] = set()
        for g in pools:
            ms = set(g.moves)
            if ms & used:
                continue
            chosen.append(g)
            used |= ms
            if len(chosen) == 4:
                break
        if len(chosen) < 4:
            continue
        all_moves: list[str] = []
        for g in chosen:
            all_moves.extend(g.moves)
        random.shuffle(all_moves)
        return MoveConnectionsChallenge(
            groups=(chosen[0], chosen[1], chosen[2], chosen[3]),
            grid_moves=tuple(all_moves),
        )
    # Fallback to deterministic first four groups if disjoint search fails.
    chosen = list(_GROUP_POOLS[:4])
    all_moves = [m for g in chosen for m in g.moves]
    random.shuffle(all_moves)
    return MoveConnectionsChallenge(
        groups=(chosen[0], chosen[1], chosen[2], chosen[3]),
        grid_moves=tuple(all_moves),
    )
