"""Check lossless artifact PNG content and the JPEG encoding contract."""

import io
import random

import pytest
from PIL import Image

from chto_za_vino_core.pipeline_artifacts import _encode


@pytest.mark.parametrize("mode", ["RGB", "RGBA", "L"])
def test_png_preserves_all_pixels(mode):
    image = Image.frombytes(mode, (127, 101), random.Random(81).randbytes(127 * 101 * len(mode)))
    body = _encode(image, "image/png")
    with Image.open(io.BytesIO(body)) as decoded:
        assert decoded.mode == image.mode
        assert decoded.size == image.size
        assert decoded.tobytes() == image.tobytes()


def test_jpeg_bytes_preserve_the_existing_contract():
    image = Image.frombytes("RGBA", (127, 101), random.Random(81).randbytes(127 * 101 * 4))
    expected = io.BytesIO()
    image.convert("RGB").save(expected, "JPEG", quality=92, optimize=True)
    assert _encode(image, "image/jpeg") == expected.getvalue()
