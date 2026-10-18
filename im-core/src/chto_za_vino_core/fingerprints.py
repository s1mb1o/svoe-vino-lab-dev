from __future__ import annotations

import io
import math

from PIL import Image, ImageOps


def _image(body: bytes, size: tuple[int, int]) -> Image.Image:
    with Image.open(io.BytesIO(body)) as source:
        return (
            ImageOps.exif_transpose(source)
            .convert("L")
            .resize(
                size,
                Image.Resampling.LANCZOS,
            )
        )


def difference_hash(body: bytes) -> str:
    return _difference_hash(_image(body, (9, 8)))


def _difference_hash(image: Image.Image) -> str:
    pixels = list(image.get_flattened_data())
    bits = 0
    for row in range(8):
        offset = row * 9
        for column in range(8):
            bits = (bits << 1) | int(pixels[offset + column] > pixels[offset + column + 1])
    return f"{bits:016x}"


def perceptual_hash(body: bytes) -> str:
    return _perceptual_hash(_image(body, (32, 32)))


def _perceptual_hash(image: Image.Image) -> str:
    size = 32
    values = list(image.get_flattened_data())
    cosines = [
        [
            math.cos(math.pi * (2 * position + 1) * frequency / (2 * size))
            for position in range(size)
        ]
        for frequency in range(8)
    ]
    horizontal_sums = [
        [
            sum(values[y * size + x] * cosines[horizontal][x] for x in range(size))
            for y in range(size)
        ]
        for horizontal in range(8)
    ]
    coefficients: list[float] = []
    for vertical in range(8):
        for horizontal in range(8):
            value = 0.0
            for y in range(size):
                vertical_weight = cosines[vertical][y]
                value += vertical_weight * horizontal_sums[horizontal][y]
            coefficients.append(value)
    median_values = sorted(coefficients[1:])
    median = median_values[len(median_values) // 2]
    bits = 0
    for coefficient in coefficients:
        bits = (bits << 1) | int(coefficient > median)
    return f"{bits:016x}"


def image_hashes(body: bytes) -> tuple[str, str]:
    """Return the perceptual hash and difference hash after one image decode."""
    with Image.open(io.BytesIO(body)) as source:
        gray = ImageOps.exif_transpose(source).convert("L")
    phash = _perceptual_hash(gray.resize((32, 32), Image.Resampling.LANCZOS))
    dhash = _difference_hash(gray.resize((9, 8), Image.Resampling.LANCZOS))
    return phash, dhash
