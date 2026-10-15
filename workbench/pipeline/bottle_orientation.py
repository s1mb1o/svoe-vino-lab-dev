"""Align a segmented query bottle before resize and embedding.

The enclosing rectangle contains the complete mask. Its IoU is therefore the
mask area divided by the rectangle area. Minimize that area, then put the long
axis in portrait orientation. The mask width profile resolves the remaining
180 degree ambiguity only when one end has a clear neck.
"""

import numpy as np
from PIL import Image

VERSION = 1
MIN_ASPECT = 1.35
NECK_RATIO = 0.72
INFO_KEY = "bottle_orientation"


def _hull(mask):
    """Return the convex hull of foreground pixel centres, without sampling."""
    rows = np.flatnonzero(mask.any(axis=1))
    if not len(rows):
        return np.empty((0, 2))
    left = mask[rows].argmax(axis=1)
    right = mask.shape[1] - 1 - mask[rows, ::-1].argmax(axis=1)
    points = sorted(set(zip(left.tolist(), rows.tolist())) |
                    set(zip(right.tolist(), rows.tolist())))

    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])

    def half(values):
        result = []
        for point in values:
            while len(result) >= 2 and cross(result[-2], result[-1], point) <= 0:
                result.pop()
            result.append(point)
        return result

    hull = half(points)[:-1] + half(points[::-1])[:-1] if len(points) > 1 else points
    return np.asarray(hull, dtype=np.float64) + 0.5


def _bounds(hull, angles):
    radians = np.deg2rad(angles)
    cosine, sine = np.cos(radians), np.sin(radians)
    # PIL rotates counterclockwise in image coordinates, where y grows down.
    x = hull[:, 0, None]*cosine + hull[:, 1, None]*sine
    y = -hull[:, 0, None]*sine + hull[:, 1, None]*cosine
    # Include the complete unit square of each pixel, not only its centre.
    extent = np.abs(cosine) + np.abs(sine)
    return np.ptp(x, axis=0) + extent, np.ptp(y, axis=0) + extent


def _angle(hull):
    coarse = np.arange(0, 90, 0.5)
    width, height = _bounds(hull, coarse)
    best = float(coarse[np.argmin(width*height)])
    angles = np.unique(np.r_[0.0, (best + np.arange(-0.5, 0.501, 0.05)) % 90])
    width, height = _bounds(hull, angles)
    areas = width*height
    # Keep 0 degrees when its area is equal. Avoid an unnecessary interpolation.
    index = int(np.argmin(areas))
    if areas[0] <= areas[index]*(1 + 1e-8):
        index = 0
    angle = float(angles[index]) + (90.0 if width[index] > height[index] else 0.0)
    return (angle+90) % 180 - 90, float(max(width[index], height[index]) /
                                                   min(width[index], height[index]))


def _neck(mask):
    """Return the neck end and its width ratio. A symmetric crop has no neck."""
    box = mask.getbbox()
    mask = mask.crop(box)
    mask.thumbnail((512, 512), Image.Resampling.NEAREST)
    pixels = np.asarray(mask) > 0
    occupied = pixels.any(axis=1)
    if not occupied.all() or mask.height < 16 or mask.height < MIN_ASPECT*mask.width:
        return None, None
    left = pixels.argmax(axis=1)
    right = mask.width - pixels[:, ::-1].argmax(axis=1)
    widths = right-left
    height = mask.height
    # Ignore the cap rim and the rounded bottom edge. Both bands must have
    # stable widths. A hand gap or a single thin row is not neck evidence.
    top = widths[round(.08*height):round(.32*height)]
    bottom = widths[round(.68*height):round(.92*height)]
    top_width, bottom_width = float(np.median(top)), float(np.median(bottom))
    smaller, larger = min(top_width, bottom_width), max(top_width, bottom_width)
    ratio = smaller/max(1.0, larger)
    if ratio > NECK_RATIO or larger < .65*mask.width:
        return None, ratio
    narrow = top if top_width < bottom_width else bottom
    if np.quantile(narrow, .8) > NECK_RATIO*larger:
        return None, ratio
    return "top" if top_width < bottom_width else "bottom", ratio


def normalize(image, alpha=None):
    """Return (a tight RGBA crop, audit) with a vertical bottle axis.

    Use an explicit mask or the RGBA alpha channel. Estimate geometry from alpha
    >= 128. Preserve the complete soft alpha when transforming and cropping.
    No mask, an empty mask, or a broad close-up preserves the input pixels.
    The output info records the rotation. Source-image boxes stay in source
    coordinates; they MUST NOT be used as bounds of the rotated image.
    """
    audit = {"version": VERSION, "angle_degrees": 0.0, "neck": "unknown",
             "applied": False, "input_size": list(image.size)}
    if alpha is None:
        if image.mode != "RGBA":
            audit["reason"] = "no_mask"
            return image, audit
        alpha = image.getchannel("A")
    if alpha.size != image.size:
        raise ValueError("bottle image and mask sizes differ")
    alpha = alpha.convert("L")
    core = np.asarray(alpha) >= 128
    hull = _hull(core)
    if len(hull) < 3 or np.count_nonzero(core) < 16:
        audit["reason"] = "empty_or_tiny_mask"
        return image, audit
    angle, aspect = _angle(hull)
    audit["axis_aspect"] = round(aspect, 6)
    if aspect < MIN_ASPECT:
        audit["reason"] = "broad_or_partial_mask"
        return image, audit
    # Test direction on a small mask. Resample source pixels only once below.
    probe = Image.fromarray(core.astype(np.uint8)*255)
    probe.thumbnail((512, 512), Image.Resampling.NEAREST)
    probe = probe.rotate(angle, Image.Resampling.NEAREST, expand=True, fillcolor=0)
    neck, ratio = _neck(probe)
    if neck == "bottom":
        angle = (angle+180+180) % 360 - 180
    audit["neck"] = "top" if neck is not None else "unknown"
    audit["neck_width_ratio"] = None if ratio is None else round(ratio, 6)
    audit["direction_confident"] = neck is not None
    angle = round(angle, 6)
    cut = image.convert("RGBA")
    cut.putalpha(alpha)
    source_box = alpha.getbbox()
    cut = cut.crop(source_box)
    # Pillow uses premultiplied alpha for RGBA interpolation. Background colour
    # cannot bleed into the bottle edge. Expand retains all foreground pixels.
    if angle:
        cut = cut.rotate(angle, Image.Resampling.BICUBIC, expand=True,
                         fillcolor=(255, 255, 255, 0))
    cut = cut.crop(cut.getchannel("A").getbbox())
    before = float(np.count_nonzero(core)/max(1, image.width*image.height))
    after = float(np.count_nonzero(np.asarray(cut.getchannel("A")) >= 128) /
                  (cut.width*cut.height))
    # Soft alpha may make a crop slightly wider than the binary geometry.
    # Keep the existing pixels if rasterization loses the expected area gain.
    if cut.width*cut.height > image.width*image.height and angle:
        # Keep a required neck-up half turn even if a tiny tilt increases the
        # soft-alpha bounds. Quarter turns keep the original pixels losslessly.
        angle = (round(angle/90)*90+180) % 360-180
        cut = image.convert("RGBA")
        cut.putalpha(alpha)
        cut = cut.crop(source_box)
        if angle:
            cut = cut.rotate(angle, Image.Resampling.BICUBIC, expand=True,
                             fillcolor=(255, 255, 255, 0))
        audit["angle_adjustment"] = "nearest_quarter_turn_preserves_crop_area"
        after = float(np.count_nonzero(np.asarray(cut.getchannel("A")) >= 128) /
                      (cut.width*cut.height))
    audit.update(applied=True, angle_degrees=angle, output_size=list(cut.size),
                 mask_crop_iou_before=round(before, 6),
                 mask_crop_iou_after=round(after, 6),
                 crop_area_ratio=round(cut.width*cut.height/(image.width*image.height), 6))
    cut.info[INFO_KEY] = audit
    return cut, audit


def embedding_source(image, steps, box, processed):
    """Use the rotated local canvas for a masked embedding view.

    A rectangle-only view keeps the source crop. A normalized masked view uses
    its local bounds so the standard segment/remove_background steps retain
    the new aspect ratio. Resize and embedding run after these steps.
    """
    audit = processed.info.get(INFO_KEY)
    if (isinstance(audit, dict) and audit.get("applied") is True and
            any(step["step"] == "remove_background" for step in steps)):
        return processed, (0, 0, processed.width, processed.height)
    return image, box
