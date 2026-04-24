from __future__ import annotations

from functools import lru_cache

from pokequiz.data import _fetch_json


def _clean_entry_text(text: str) -> str:
    return " ".join(text.replace("\n", " ").replace("\f", " ").split())


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
        if not text or text in seen:
            continue
        seen.add(text)
        entries.append(text)
    return tuple(entries)
