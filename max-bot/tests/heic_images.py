"""HEIC test images. The same helpers are in im-core/tests/test_moderation.py."""

import io

from PIL import Image


def heic_bytes() -> bytes:
    """A 40 by 20 HEIC image, left half red, with EXIF rotation 6 and a GPS tag."""
    image = Image.new("RGB", (40, 20), "white")
    image.paste((255, 0, 0), (0, 0, 20, 20))
    exif = Image.Exif()
    exif[0x0112] = 6
    exif[0x8825] = {2: (55.0, 45.0, 0.0)}
    buffer = io.BytesIO()
    image.save(buffer, format="HEIF", exif=exif.tobytes())
    return buffer.getvalue()


def noisy_heic_bytes(size: tuple[int, int] = (300, 300)) -> bytes:
    """A HEIC image whose JPEG copy is larger than the HEIC file."""
    image = Image.frombytes("RGB", size, bytes((index * 7919) % 251 for index in range(size[0] * size[1] * 3)))
    buffer = io.BytesIO()
    image.save(buffer, format="HEIF")
    return buffer.getvalue()
