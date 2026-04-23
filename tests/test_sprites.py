import io

import pytest


def test_png_to_ascii_art_non_empty() -> None:
    pytest.importorskip("PIL")
    from PIL import Image

    from pokequiz.sprites import png_to_ascii_art

    img = Image.new("RGB", (24, 24), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    art = png_to_ascii_art(buf.getvalue(), width=12)
    assert art
    assert len(art.splitlines()) >= 4
