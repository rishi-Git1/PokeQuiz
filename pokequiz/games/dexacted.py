from __future__ import annotations

import re
from functools import lru_cache

from pokequiz.data import _fetch_json


def _clean_entry_text(text: str) -> str:
    return " ".join(text.replace("\n", " ").replace("\f", " ").split())


def _redacted_name_variants(name: str) -> tuple[str, ...]:
    raw = name.strip().casefold()
    variants = {
        raw,
        raw.replace("-", " "),
        raw.replace("-", ""),
    }
    return tuple(v for v in sorted(variants) if v)


def _redact_target_name(text: str, target_name: str) -> str:
    redacted = text
    for variant in _redacted_name_variants(target_name):
        pattern = re.compile(re.escape(variant), flags=re.IGNORECASE)
        redacted = pattern.sub("-------", redacted)
    return redacted


@lru_cache(maxsize=2048)
def dex_entries_for_name(name: str) -> tuple[str, ...]:
    """Return unique English dex flavor entries for a Pokemon species name."""
    species = _fetch_json(f"https://pokeapi.co/api/v2/pokemon-species/{name}")
    seen: set[str] = set()
    entries: list[str] = []
    for item in species.get("flavor_text_entries", []):
        lang = item.get("language", {}).get("name")
        if lang != "en":
            continue
        text = _clean_entry_text(str(item.get("flavor_text", "")))
        text = _redact_target_name(text, name)
        if not text or text in seen:
            continue
        seen.add(text)
        entries.append(text)
    return tuple(entries)
