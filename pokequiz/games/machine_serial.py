"""Machine Serial: guess move names from generation-specific TM/TR codes."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from functools import lru_cache

from pokequiz.data import _fetch_json


@dataclass(frozen=True, slots=True)
class MachineSerialChallenge:
    generation: int
    machine_code: str  # e.g., TM22 or TR00
    move_slug: str
    move_type: str
    damage_class: str
    power: int | None


def display_move_name(slug: str) -> str:
    return slug.replace("-", " ").title()


def _pretty(slug: str) -> str:
    return slug.replace("-", " ").title()


def _parse_machine_code(item_slug: str) -> str | None:
    m = re.fullmatch(r"(tm|tr|hm)(\d+)", item_slug.casefold())
    if not m:
        return None
    prefix, num = m.groups()
    if prefix == "hm":
        return None
    return f"{prefix.upper()}{num}"


@lru_cache(maxsize=128)
def _generation_for_version_group(version_group_name: str) -> int | None:
    try:
        payload = _fetch_json(f"https://pokeapi.co/api/v2/version-group/{version_group_name}")
    except Exception:
        return None
    g = (payload.get("generation") or {}).get("name")
    if not isinstance(g, str):
        return None
    m = re.fullmatch(r"generation-([ivx]+)", g)
    if not m:
        return None
    roman = m.group(1).upper()
    values = {"I": 1, "V": 5, "X": 10}
    total = 0
    prev = 0
    for ch in reversed(roman):
        v = values[ch]
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total if total > 0 else None


def build_challenge(*, max_attempts: int = 180) -> MachineSerialChallenge | None:
    """Pick a random move + machine mapping that is TM/TR (excluding HM)."""
    for _ in range(max_attempts):
        try:
            move_payload = _fetch_json(f"https://pokeapi.co/api/v2/move/{random.randint(1, 1000)}/")
        except Exception:
            continue
        move_slug = move_payload.get("name")
        if not isinstance(move_slug, str) or not move_slug:
            continue
        machines = list(move_payload.get("machines") or [])
        random.shuffle(machines)
        if not machines:
            continue
        for row in machines:
            vg = (row.get("version_group") or {}).get("name")
            m_url = ((row.get("machine") or {}).get("url") or "").strip()
            if not isinstance(vg, str) or not vg or not m_url:
                continue
            try:
                machine_payload = _fetch_json(m_url)
            except Exception:
                continue
            item_slug = (machine_payload.get("item") or {}).get("name")
            if not isinstance(item_slug, str):
                continue
            code = _parse_machine_code(item_slug)
            if code is None:
                continue
            gen = _generation_for_version_group(vg)
            if gen is None:
                continue
            move_type = (move_payload.get("type") or {}).get("name")
            move_class = (move_payload.get("damage_class") or {}).get("name")
            power = move_payload.get("power")
            try:
                pwr = int(power) if power is not None else None
            except (TypeError, ValueError):
                pwr = None
            return MachineSerialChallenge(
                generation=gen,
                machine_code=code,
                move_slug=move_slug,
                move_type=_pretty(str(move_type)) if move_type else "Unknown",
                damage_class=_pretty(str(move_class)) if move_class else "Unknown",
                power=pwr,
            )
    return None
