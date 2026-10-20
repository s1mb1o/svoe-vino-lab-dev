"""Optional input selection, shared by standalone and cascade matcher paths.

The policy consumes detector output. Only the standalone byte adapter requests
SAM3; cascade supplies its existing detections and their coordinate size.
"""

import base64
from dataclasses import dataclass
from io import BytesIO
import math

from PIL import Image

from .group import SAM3_TIMEOUT_SECONDS, _instance_mask
from .semantic_selector import NOUNS, VERSION, select_photo, select_variant


@dataclass(frozen=True)
class InputSelector:
    """An immutable optional step; disabled means no decoding or detector call."""

    enabled: bool = False
    variant: str = VERSION

    @property
    def nouns(self):
        return NOUNS

    def prepare(self, body, endpoint, *, timeout=SAM3_TIMEOUT_SECONDS):
        """Return bytes suitable for recognition, including the no-target crop."""
        if not self.enabled:
            return body
        return select_photo(body, endpoint, variant=self.variant, timeout=timeout).crop

    def select(self, image, instances, *, detection_size=None):
        """Select on aspect-correct pixels, reusing masks from a stretched detector.

        `image` is an oriented working copy (at most 1600 px in cascade). Boxes and
        masks are mapped together; detector inputs and dictionaries stay unchanged.
        """
        if not self.enabled:
            raise ValueError("input selector is disabled")
        if detection_size is not None and tuple(detection_size) != image.size:
            instances = _remap(instances, detection_size, image.size)
        return select_variant(image, instances, variant=self.variant)


def scale_box(box, source_size, target_size):
    """Map a complete rectangle outwards, retaining every covered source pixel."""
    sx, sy = target_size[0] / source_size[0], target_size[1] / source_size[1]
    return (max(0, math.floor(box[0] * sx)), max(0, math.floor(box[1] * sy)),
            min(target_size[0], math.ceil(box[2] * sx)),
            min(target_size[1], math.ceil(box[3] * sy)))


def _remap(instances, source_size, target_size):
    source = Image.new("RGB", source_size)
    result = []
    for item in instances:
        prepared = _instance_mask(source, item) if item.get("mask_png_b64") else None
        if prepared is None:
            # Preserve source indices even for unusable detections.
            result.append(dict(item, mask_png_b64=""))
            continue
        box, mask = prepared
        full = Image.new("L", source_size)
        full.paste(mask, box[:2])
        full = full.resize(target_size, Image.Resampling.NEAREST)
        output = BytesIO()
        full.save(output, "PNG")
        result.append(dict(item, box=scale_box(item["box"], source_size, target_size),
                           mask_png_b64=base64.b64encode(output.getvalue()).decode("ascii")))
    return result
