from pathlib import Path

from PIL import Image


def test_rejection_illustration_is_a_640_square_png():
    path = Path(__file__).parents[1] / "assets" / "content-rejected-monkey-640x640.png"

    with Image.open(path) as image:
        assert image.format == "PNG"
        assert image.size == (640, 640)
