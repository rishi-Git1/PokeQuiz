from __future__ import annotations

from functools import lru_cache

from pokequiz.data import _fetch_json, normalize_name

# Manual clues only: English is the answer; ja-roma is always shown at start.
CLUE_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("fr", "French"),
    ("de", "German"),
    ("ko", "Korean"),
    ("zh-hans", "Chinese (Simplified)"),
    ("zh-hant", "Chinese (Traditional)"),
    ("ja-hrkt", "Japanese (kana)"),
    ("ja", "Japanese (default script)"),
)


@lru_cache(maxsize=4096)
def _species_payload(api_name: str) -> dict:
    return _fetch_json(f"https://pokeapi.co/api/v2/pokemon-species/{normalize_name(api_name)}")


def names_by_language(api_name: str) -> dict[str, str]:
    payload = _species_payload(api_name)
    out: dict[str, str] = {}
    for entry in payload.get("names", []) or []:
        lang = entry.get("language", {}) or {}
        code = lang.get("name")
        nm = entry.get("name")
        if code and nm is not None and str(nm).strip():
            out[str(code).casefold()] = str(nm).strip()
    return out


def romanized_japanese_name(api_name: str) -> str | None:
    names = names_by_language(api_name)
    return names.get("ja-roma")
