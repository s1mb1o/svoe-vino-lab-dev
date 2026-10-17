"""Check frozen hash values and the single-decode path."""

import io
import random
from unittest import mock

import pytest
from PIL import Image

from chto_za_vino_max_bot import fingerprints

CASES = [
    ("RGB", 0, "c02bc43bc77452d7", "9c4c565cb666695b"),
    ("RGB", 3, "a7498464aa795de9", "8833ada69259d293"),
    ("RGB", 19, "b479457b71cc2a2a", "6c634cd1b6529b53"),
    ("RGBA", 0, "c7757a7d100f25c2", "49f411236bb52e52"),
    ("RGBA", 3, "aa70ff2773788422", "a6d64e64b699d494"),
    ("RGBA", 19, "a1b28624527e35f7", "d634a6e6656d5825"),
    ("L", 0, "8e226c02f81becbf", "78129546121a8bd9"),
    ("L", 3, "9d7096293ab9720f", "ee59b3c48cea8d9b"),
    ("L", 19, "9357c78d5b28425e", "b7a16266aa2c8d3e"),
    ("P", 0, "d6956048ab58cf3e", "6a5b95ae929d6b92"),
    ("P", 3, "bbc0b4fdc2a0723a", "aaa9121496aae8c6"),
    ("P", 19, "8356f58e5f1f8007", "1b532ba69c586835"),
]


@pytest.mark.parametrize("mode,seed,phash,dhash", CASES)
def test_hashes_match_frozen_values(mode, seed, phash, dhash):
    image = Image.frombytes(mode, (37, 29), random.Random(seed).randbytes(37 * 29 * len(mode)))
    if mode == "P":
        image.putpalette(bytes(range(256)) * 3)
    output = io.BytesIO()
    image.save(output, "PNG")
    body = output.getvalue()
    assert fingerprints.perceptual_hash(body) == phash
    assert fingerprints.difference_hash(body) == dhash
    with mock.patch.object(fingerprints.Image, "open", wraps=Image.open) as decode:
        assert fingerprints.image_hashes(body) == (phash, dhash)
    assert decode.call_count == 1


@pytest.mark.parametrize("orientation", [1, 3, 6, 8])
def test_combined_hashes_preserve_exif_orientation(orientation):
    image = Image.frombytes("RGB", (31, 19), random.Random(99).randbytes(31 * 19 * 3))
    exif = Image.Exif()
    exif[274] = orientation
    output = io.BytesIO()
    image.save(output, "JPEG", exif=exif)
    body = output.getvalue()
    assert fingerprints.image_hashes(body) == (
        fingerprints.perceptual_hash(body),
        fingerprints.difference_hash(body),
    )
