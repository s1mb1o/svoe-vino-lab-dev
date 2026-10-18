from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener

# Pillow opens HEIC and HEIF files only through this plugin. detect_image_type still rejects them,
# so each path converts them with heif_to_jpeg first.
register_heif_opener()


class UnsupportedImage(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ImageType:
    format: str
    mime_type: str
    extension: str


# The major brands of an ISO BMFF `ftyp` box for a HEIC or HEIF still image.
HEIF_BRANDS = frozenset({b"heic", b"heix", b"heim", b"heis", b"mif1"})
HEIF_JPEG_QUALITY = 92
# A 48 MP HEIC can give a JPEG larger than BOT_MAX_IMAGE_BYTES. Recognition needs no more pixels.
HEIF_MAX_SIDE = 4096

SUPPORTED_IMAGE_TYPES = {
    "JPEG": ImageType("JPEG", "image/jpeg", "jpg"),
    "PNG": ImageType("PNG", "image/png", "png"),
    "WEBP": ImageType("WEBP", "image/webp", "webp"),
}


def detect_image_type(body: bytes) -> ImageType:
    try:
        with Image.open(io.BytesIO(body)) as source:
            # Moderation sees only the first frame. An image file can be an animated PNG or WebP.
            animated = getattr(source, "n_frames", 1) > 1
            source.verify()
            image_type = SUPPORTED_IMAGE_TYPES.get(source.format or "")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnsupportedImage("image is invalid") from exc
    if image_type is None:
        raise UnsupportedImage("image format must be JPEG, PNG, or WebP")
    if animated:
        raise UnsupportedImage("image must have one frame")
    return image_type


def is_heif(body: bytes) -> bool:
    return len(body) >= 12 and body[4:8] == b"ftyp" and body[8:12] in HEIF_BRANDS


def heif_to_jpeg(body: bytes) -> bytes:
    """Return a JPEG copy of a HEIC or HEIF image. Return another image unchanged.

    An iPhone saves photos as HEIC, and a HEIC file sent as a document keeps this format.
    The plugin applies the HEIF rotation when it opens the file. The copy uses only the primary
    image of the file and has no EXIF data, so it has no location. Its longest side is at most
    HEIF_MAX_SIDE.
    """
    if not is_heif(body):
        return body
    try:
        with Image.open(io.BytesIO(body)) as source:
            if source.format != "HEIF":
                raise UnsupportedImage("image is not a HEIF image")
            image = source.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnsupportedImage("HEIF image is invalid") from exc
    image.thumbnail((HEIF_MAX_SIDE, HEIF_MAX_SIDE), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=HEIF_JPEG_QUALITY)
    return output.getvalue()
