from __future__ import annotations

import json
import sys
from io import BytesIO
from typing import TYPE_CHECKING

from pokequiz.data import POKEAPI_UA

if TYPE_CHECKING:
    from pokequiz.models import Pokemon

_sprite_url_ok: dict[str, str] = {}


def _request(url: str, *, expect_json: bool) -> bytes | dict:
    from urllib.request import Request, urlopen

    req = Request(url, headers={"User-Agent": POKEAPI_UA})
    with urlopen(req, timeout=25) as response:
        raw = response.read()
    if expect_json:
        return json.loads(raw.decode("utf-8"))
    return raw


def _front_sprite_url_for_api_name(api_name: str) -> str | None:
    if api_name in _sprite_url_ok:
        return _sprite_url_ok[api_name]
    try:
        payload = _request(f"https://pokeapi.co/api/v2/pokemon/{api_name}", expect_json=True)
        if not isinstance(payload, dict):
            return None
        sprites = payload.get("sprites") or {}
        url = sprites.get("front_default")
        if url:
            _sprite_url_ok[api_name] = str(url)
            return str(url)
    except Exception:
        pass
    return None


def _fetch_png(url: str) -> bytes | None:
    try:
        data = _request(url, expect_json=False)
        return data if isinstance(data, bytes) else None
    except Exception:
        return None


def png_to_ascii_art(png_bytes: bytes, *, width: int = 42) -> str | None:
    """Resize to a narrow grayscale ramp; height follows image aspect adjusted for tall terminal cells."""
    try:
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError:
        return None

    try:
        img = Image.open(BytesIO(png_bytes)).convert("RGB")
        w0, h0 = img.size
        if w0 <= 0 or h0 <= 0:
            return None

        target_w = max(8, min(width, w0))
        target_h = max(4, int(h0 * target_w / w0 / 2))
        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        gray = img.convert("L")

        # Invert: dark pixels (outlines) -> dense chars so sprites read on typical light terminal backgrounds.
        ramp = " .:-=+*#%@"
        lines: list[str] = []
        pixels = gray.load()
        for y in range(gray.height):
            row: list[str] = []
            for x in range(gray.width):
                lum = pixels[x, y] / 255.0
                v = 1.0 - lum
                idx = min(len(ramp) - 1, int(v * len(ramp)))
                row.append(ramp[idx])
            lines.append("".join(row))
        return "\n".join(lines)
    except Exception:
        return None


def format_pokemon_sprite_block(mon: "Pokemon", *, width: int = 42) -> str | None:
    """Return multi-line ASCII art, or None if unavailable."""
    url = _front_sprite_url_for_api_name(mon.name)
    if not url:
        return None
    png = _fetch_png(url)
    if not png:
        return None
    return png_to_ascii_art(png, width=width)


def _pillow_importable() -> bool:
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        return False
    return True


def print_statle_sprite(mon: "Pokemon", *, width: int = 42) -> None:
    """Best-effort sprite for Statle; never raises."""
    if not _pillow_importable():
        exe = sys.executable
        print(
            "Pillow is not installed for this Python interpreter (sprites need it in the same env you run PokeQuiz).",
            flush=True,
        )
        print(f"  Python: {exe}", flush=True)
        print(f'  Fix:    "{exe}" -m pip install pillow', flush=True)
        print(
            "  (If `pip install pillow` said it used a 'user' path, your venv still does not have Pillow.)",
            flush=True,
        )
        return

    art = format_pokemon_sprite_block(mon, width=width)
    if art:
        print(art, flush=True)
        return

    if not _front_sprite_url_for_api_name(mon.name):
        print("(No official front sprite for this form in the API.)", flush=True)
    else:
        print("(Could not download or decode sprite.)", flush=True)
