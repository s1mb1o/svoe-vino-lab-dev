from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError


class UnsupportedImage(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ImageType:
    format: str
    mime_type: str
    extension: str


SUPPORTED_IMAGE_TYPES = {
    "JPEG": ImageType("JPEG", "image/jpeg", "jpg"),
    "PNG": ImageType("PNG", "image/png", "png"),
    "WEBP": ImageType("WEBP", "image/webp", "webp"),
}


def detect_image_type(body: bytes) -> ImageType:
    try:
        with Image.open(io.BytesIO(body)) as source:
            source.verify()
            image_type = SUPPORTED_IMAGE_TYPES.get(source.format or "")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnsupportedImage("image is invalid") from exc
    if image_type is None:
        raise UnsupportedImage("image format must be JPEG, PNG, or WebP")
    return image_type
