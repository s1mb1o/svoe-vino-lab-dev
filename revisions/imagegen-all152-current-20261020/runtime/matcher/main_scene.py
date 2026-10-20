"""Select one package with the hand-aware scene score from workbench version 1.

This module has no workbench dependency. It shares the bounded SAM3 transport and
mask validation with the group path. Group matching MUST NOT call this selector.
Hand contact means box overlap. It is not a grip classifier.
"""

from io import BytesIO
import math

import numpy as np
from PIL import Image

from .group import (
    DETECTION_THRESHOLD, SAM3_TIMEOUT_SECONDS, _instance_mask, _normalize_image,
    _request_sam3,
)


NOUNS = ("wine bottle", "can", "packet", "box", "hand")
TEXTS = ", ".join(NOUNS)
PACKAGE_LABELS = frozenset(("wine bottle", "bottle", "can", "packet", "box"))
HAND_WEIGHTS = {
    "hand_contact": 0.40, "area": 0.22, "center": 0.14, "sharpness": 0.08,
    "confidence": 0.06, "mask_fill": 0.04, "shelf_isolation": 0.04,
    "edge_visibility": 0.02,
}
SCENE_WEIGHTS = {
    "area": 0.28, "center": 0.24, "confidence": 0.14, "sharpness": 0.12,
    "shelf_isolation": 0.10, "mask_fill": 0.08, "edge_visibility": 0.04,
}


def select_main_package(image_bytes: bytes, endpoint: str | None,
                        timeout: float = SAM3_TIMEOUT_SECONDS, opener=None) -> bytes:
    """Return the selected masked crop, or the original bytes when no package exists."""
    image, jpeg = _normalize_image(image_bytes)
    instances = _request_sam3(
        jpeg, image.width, image.height, endpoint, timeout, opener=opener, nouns=NOUNS)
    for instance in rank_packages(image, instances):
        prepared = _instance_mask(image, instance)
        if prepared is None:
            continue
        box, mask = prepared
        crop = image.crop(box)
        crop = Image.composite(crop, Image.new("RGB", crop.size, "white"), mask)
        output = BytesIO()
        crop.save(output, "PNG")
        return output.getvalue()
    return image_bytes


def rank_packages(image: Image.Image, instances: list[dict]) -> list[dict]:
    """Rank validated SAM3 packages. Hands affect scores but are never candidates."""
    hands, packages = [], []
    width, height = image.size
    for index, instance in enumerate(instances):
        if instance["score"] < DETECTION_THRESHOLD:
            continue
        raw = instance["box"]
        box = (max(0.0, min(width, raw[0])), max(0.0, min(height, raw[1])),
               max(0.0, min(width, raw[2])), max(0.0, min(height, raw[3])))
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        label = instance["label"]
        if label == "hand":
            hands.append(box)
        elif label in PACKAGE_LABELS and instance["mask_png_b64"]:
            area = max(1.0, instance.get("area") or _box_area(box))
            packages.append({"instance": instance, "index": index, "box": box,
                             "label": "wine bottle" if label == "bottle" else label,
                             "area": area})
    if not packages:
        return []
    weights = HAND_WEIGHTS if hands else SCENE_WEIGHTS
    maximum_area = max(item["area"] for item in packages)
    sharpness = [_sharpness(image, item["box"]) for item in packages]
    low, high = min(sharpness), max(sharpness)
    half_diagonal = max(1.0, math.hypot(width, height) / 2)
    for item, sharp in zip(packages, sharpness):
        box = item["box"]
        relative_area = item["area"] / maximum_area
        overlap = max((_intersection_share(box, hand) for hand in hands), default=0.0)
        # Reduce hand contact for small background packages inside a large hand box.
        contact = min(1.0, 1.5 * overlap) * min(1.0, relative_area / 0.4)
        distance = math.hypot((box[0] + box[2] - width) / 2,
                              (box[1] + box[3] - height) / 2)
        touched = sum((box[0] <= 0.01 * width, box[1] <= 0.01 * height,
                       box[2] >= 0.99 * width, box[3] >= 0.99 * height))
        signals = {
            "hand_contact": contact,
            "area": math.sqrt(relative_area),
            "center": 1.0 - distance / half_diagonal,
            "sharpness": (sharp - low) / (high - low) if high > low else 0.5,
            "confidence": item["instance"]["score"],
            "mask_fill": item["area"] / max(1.0, _box_area(box)),
            "shelf_isolation": 1.0 - _peer_count(item, packages, height) / 4.0,
            "edge_visibility": 1.0 - touched / 4.0,
        }
        item["scene_score"] = sum(
            max(0.0, min(1.0, signals[name])) * weight
            for name, weight in weights.items())
    packages.sort(key=lambda item: (
        item["scene_score"], item["area"], item["instance"]["score"], -item["index"]),
        reverse=True)
    return [item["instance"] for item in packages]


def _box_area(box):
    return (box[2] - box[0]) * (box[3] - box[1])


def _intersection_share(package, hand):
    width = max(0.0, min(package[2], hand[2]) - max(package[0], hand[0]))
    height = max(0.0, min(package[3], hand[3]) - max(package[1], hand[1]))
    return width * height / max(1.0, _box_area(package))


def _sharpness(image, box):
    bounds = (math.floor(box[0]), math.floor(box[1]),
              math.ceil(box[2]), math.ceil(box[3]))
    crop = image.crop(bounds).convert("L")
    crop.thumbnail((256, 256), Image.Resampling.LANCZOS)
    values = np.asarray(crop, dtype=np.float32)
    if min(values.shape) < 2:
        return 0.0
    return float(np.abs(np.diff(values, axis=1)).mean()
                 + np.abs(np.diff(values, axis=0)).mean())


def _peer_count(candidate, packages, height):
    center_y = (candidate["box"][1] + candidate["box"][3]) / 2
    peers = 0
    for other in packages:
        if other is candidate or other["label"] != candidate["label"]:
            continue
        ratio = other["area"] / candidate["area"]
        other_y = (other["box"][1] + other["box"][3]) / 2
        if 0.5 <= ratio <= 2.0 and abs(other_y - center_y) <= 0.18 * height:
            peers += 1
    return peers
