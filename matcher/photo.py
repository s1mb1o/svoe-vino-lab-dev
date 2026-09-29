"""The CPU image operations of the backend `cascade`.

The request photo is decoded one time. The other images are made from it: the SAM3
copy, the request PNGs of the scanner, SigLIP2, and the VLM, and the crops of the
package and of its label. The refined mask box is the rule of the lab
(`workbench/pipeline/main_scene.py` `cut` and `workbench/pipeline/derive.py`
`refine_mask`). Each function is safe to call from a worker thread: it does not change
its input image.
"""

import base64
import binascii
from dataclasses import dataclass
from io import BytesIO
import math

from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError

from .group import GroupMatchError
from .protection import ImageRejected


# The SAM3 copy of `group._normalize_image`.
SAM3_MAX_SIDE = 1600
SAM3_JPEG_QUALITY = 86
# The scan image of the lab barcode step: the long side 1600 px, scaled up or down.
SCAN_SIDE = 1600
# The mask rule of `workbench/pipeline/derive.py`.
MASK_BLUR = 0.005
MASK_KEEP = 64
EDGE_BLUR = 1.0
MASK_THRESHOLD = 128
# PNG is lossless; level 1 gives the same pixels as the default level with less CPU.
PNG_LEVEL = 1


@dataclass(frozen=True)
class Sam3Copy:
    """The image that SAM3 gets, its JPEG bytes, and the scale back to the photo."""

    image: Image.Image
    jpeg: bytes
    scale_x: float
    scale_y: float


def decode(body: bytes) -> Image.Image:
    """Return the RGB image of the first frame, upright, with transparency on white.

    These are the first steps of `siglip2.model_input`. A damaged file raises
    `ImageRejected` with HTTP status 422.
    """
    try:
        with Image.open(BytesIO(body)) as opened:
            opened.seek(0)
            image = ImageOps.exif_transpose(opened)
            alpha = image.mode in ("RGBA", "LA", "PA") or (
                image.mode == "P" and "transparency" in image.info)
            image = image.convert("RGBA" if alpha else "RGB")
    except (OSError, SyntaxError, ValueError) as exc:
        raise ImageRejected(422, "image file is invalid or damaged") from exc
    if image.mode == "RGBA":
        white = Image.new("RGBA", image.size, (255, 255, 255, 255))
        image = Image.alpha_composite(white, image).convert("RGB")
    return image


def sam3_copy(image: Image.Image) -> Sam3Copy:
    """Return the SAM3 copy: the long side at most 1600 px (LANCZOS), JPEG quality 86."""
    copy = image
    if max(image.size) > SAM3_MAX_SIDE:
        scale = SAM3_MAX_SIDE / max(image.size)
        size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        copy = image.resize(size, Image.Resampling.LANCZOS)
    output = BytesIO()
    copy.save(output, "JPEG", quality=SAM3_JPEG_QUALITY)
    return Sam3Copy(copy, output.getvalue(),
                    image.width / copy.width, image.height / copy.height)


def png(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, "PNG", compress_level=PNG_LEVEL)
    return output.getvalue()


def scaled_png(image: Image.Image, side: int = SCAN_SIDE) -> bytes:
    """Return the scan PNG: the long side scaled down (BICUBIC) or up (LANCZOS) to `side`.

    This is `workbench/pipeline/barcode.py` `Decoder.scaled` with `max_side` 1600 and
    `upscale: true`.
    """
    width, height = image.size
    scale = side / float(max(width, height))
    if scale < 1.0:
        image = image.resize((max(1, int(width * scale)), max(1, int(height * scale))),
                             Image.Resampling.BICUBIC)
    elif scale > 1.0:
        image = image.resize((round(width * scale), round(height * scale)),
                             Image.Resampling.LANCZOS)
    return png(image)


def side_png(image: Image.Image, side: int) -> bytes:
    """Return the PNG of an RGB image scaled up or down to the long side `side`.

    This is `workbench/pipeline/cluster_rerank.py` `png_of` for an image on white.
    """
    if max(image.size) != side:
        scale = side / max(image.size)
        image = image.resize((max(1, round(image.width * scale)),
                              max(1, round(image.height * scale))),
                             Image.Resampling.LANCZOS)
    return png(image)


def crop(image: Image.Image, box, margin: float = 0.0) -> Image.Image:
    """Return the crop of `box` (photo pixels), grown by `margin` of its width and of its
    height on each side, and clamped to the photo."""
    left, top, right, bottom = box
    grow_x, grow_y = (right - left) * margin, (bottom - top) * margin
    bounds = (max(0, math.floor(left - grow_x)), max(0, math.floor(top - grow_y)),
              min(image.width, math.ceil(right + grow_x)),
              min(image.height, math.ceil(bottom + grow_y)))
    return image.crop(bounds)


def refine_mask(mask: Image.Image, long_side: int | None = None) -> Image.Image:
    """Smooth the edge of a 0/255 mask, grow it a little, and make the edge soft.

    This is `workbench/pipeline/derive.py` `refine_mask`. `long_side` is the long side of
    the whole photo when `mask` is a region of it; the blur depends on the photo size.
    """
    sigma = max(1.0, MASK_BLUR * (long_side or max(mask.size)))
    kept = mask.filter(ImageFilter.GaussianBlur(sigma)).point(
        lambda value: 255 if value >= MASK_KEEP else 0)
    return kept.filter(ImageFilter.GaussianBlur(EDGE_BLUR))


def _mask(mask_png_b64: str, size) -> Image.Image:
    try:
        raw = base64.b64decode(mask_png_b64, validate=True)
        with Image.open(BytesIO(raw)) as opened:
            if opened.format != "PNG" or opened.size != tuple(size):
                raise GroupMatchError(502, "SAM3 mask dimensions are invalid")
            return opened.convert("L")
    except (binascii.Error, OSError, UnidentifiedImageError) as exc:
        raise GroupMatchError(502, "SAM3 mask is not a valid PNG") from exc


def refined_region(instance: dict, copy: Sam3Copy, image: Image.Image):
    """Return (the region box, the refined alpha of the region) in photo pixels for one
    SAM3 instance, or None for an empty region.

    The lab resizes the whole mask to the photo (bilinear), keeps the pixels of at least
    128, and runs `refine_mask`. The same steps run here on the instance box plus a
    margin of 3 sigma, so the alpha inside the region is the same, and the cost does not
    grow with the photo size.
    """
    width, height = image.size
    long_side = max(width, height)
    sigma = max(1.0, MASK_BLUR * long_side)
    margin = math.ceil(3 * sigma + 3 * EDGE_BLUR) + 2
    box = instance["box"]
    left = max(0, math.floor(box[0] * copy.scale_x) - margin)
    top = max(0, math.floor(box[1] * copy.scale_y) - margin)
    right = min(width, math.ceil(box[2] * copy.scale_x) + margin)
    bottom = min(height, math.ceil(box[3] * copy.scale_y) + margin)
    if right <= left or bottom <= top:
        return None
    mask = _mask(instance["mask_png_b64"], copy.image.size)
    source = (left / copy.scale_x, top / copy.scale_y,
              right / copy.scale_x, bottom / copy.scale_y)
    region = mask.resize((right - left, bottom - top), Image.Resampling.BILINEAR,
                         box=source)
    region = region.point(lambda value: 255 if value >= MASK_THRESHOLD else 0)
    return (left, top, right, bottom), refine_mask(region, long_side)


def refined_box(instance: dict, copy: Sam3Copy, image: Image.Image):
    """Return the box of the refined mask of one SAM3 instance in photo pixels, or None
    for an empty mask. This is the crop box of the lab view `full` of a query photo."""
    result = refined_region(instance, copy, image)
    if result is None:
        return None
    (left, top, _, _), alpha = result
    inner = alpha.point(lambda value: 255 if value > 0 else 0).getbbox()
    if inner is None:
        return None
    return (left + inner[0], top + inner[1], left + inner[2], top + inner[3])


def masked_cut(instance: dict, copy: Sam3Copy, image: Image.Image):
    """Return (the cut on white, its box in photo pixels) of the refined mask of one
    instance, or None for an empty mask. Pixels outside the mask are white."""
    result = refined_region(instance, copy, image)
    if result is None:
        return None
    (left, top, right, bottom), alpha = result
    inner = alpha.point(lambda value: 255 if value > 0 else 0).getbbox()
    if inner is None:
        return None
    region = image.crop((left, top, right, bottom))
    white = Image.new("RGB", region.size, "white")
    cut = Image.composite(region, white, alpha).crop(inner)
    return cut, (left + inner[0], top + inner[1], left + inner[2], top + inner[3])
