from __future__ import annotations

import io
import math

from PIL import Image, ImageOps


def _image(body: bytes, size: tuple[int, int]) -> Image.Image:
    with Image.open(io.BytesIO(body)) as source:
        return ImageOps.exif_transpose(source).convert("L").resize(
            size,
            Image.Resampling.LANCZOS,
        )


def difference_hash(body: bytes) -> str:
    pixels = list(_image(body, (9, 8)).get_flattened_data())
    bits = 0
    for row in range(8):
        offset = row * 9
        for column in range(8):
            bits = (bits << 1) | int(pixels[offset + column] > pixels[offset + column + 1])
    return f"{bits:016x}"


def perceptual_hash(body: bytes) -> str:
    size = 32
    values = list(_image(body, (size, size)).get_flattened_data())
    cosines = [
        [math.cos(math.pi * (2 * position + 1) * frequency / (2 * size)) for position in range(size)]
        for frequency in range(8)
    ]
    coefficients: list[float] = []
    for vertical in range(8):
        for horizontal in range(8):
            value = 0.0
            for y in range(size):
                row = y * size
                vertical_weight = cosines[vertical][y]
                value += vertical_weight * sum(
                    values[row + x] * cosines[horizontal][x] for x in range(size)
                )
            coefficients.append(value)
    median_values = sorted(coefficients[1:])
    median = median_values[len(median_values) // 2]
    bits = 0
    for coefficient in coefficients:
        bits = (bits << 1) | int(coefficient > median)
    return f"{bits:016x}"
