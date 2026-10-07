"""Select the main package of a query photo with an explainable scene score.

The catalogue-image processor keeps the bottle-first rule of `derive.package_instance`.
Configured recognition pipelines use this module for query photos. SAM3 detects package
instances and hands in one request. The selector gives no package class a fixed priority.
Read `docs/plans/69_main-scene-ranking.md`.
"""
import base64
import io
import math

import numpy as np
from PIL import Image, ImageChops

import derive

VERSION = 3
MIN_MASK_FILL = 0.05
MIN_FRAME_COVER = 0.95
MAX_FRAME_MASK_FILL = 0.25
CONFIDENCE_GAP_LIMIT = 0.50
TEXTS = derive.SAM3_TEXTS + ", hand"
HAND_LABEL = "hand"
PACKAGE_LABELS = frozenset((derive.BOTTLE_LABEL, "bottle", "can", "packet", "box"))

HAND_WEIGHTS = {
    "hand_contact": 0.40,
    "area": 0.22,
    "center": 0.14,
    "sharpness": 0.08,
    "confidence": 0.06,
    "mask_fill": 0.04,
    "shelf_isolation": 0.04,
    "edge_visibility": 0.02,
}
SCENE_WEIGHTS = {
    "area": 0.28,
    "center": 0.24,
    "confidence": 0.14,
    "sharpness": 0.12,
    "shelf_isolation": 0.10,
    "mask_fill": 0.08,
    "edge_visibility": 0.04,
}
SETTINGS_V1 = ("SAM3 %r; hybrid main-scene selector v%d; no package-class priority; "
            "hand weights %r; no-hand weights %r; mask blur %s of the long side, "
            "keep >= %d/255; edge blur %s px"
            % (TEXTS, 1, HAND_WEIGHTS, SCENE_WEIGHTS, derive.MASK_BLUR,
               derive.MASK_KEEP, derive.EDGE_BLUR))
SETTINGS_V2 = SETTINGS_V1.replace("selector v1", "selector v2") + (
    "; reject package mask fill < %s; preserve photo context when the package box "
    "covers >= %s of each image side and mask fill < %s; "
    "use white-border crop when no valid package remains"
    % (MIN_MASK_FILL, MIN_FRAME_COVER, MAX_FRAME_MASK_FILL))
SETTINGS = SETTINGS_V2.replace("selector v2", "selector v%d" % VERSION) + (
    "; without hands, reject a package detector score >= %s below the strongest "
    "detector score of the same package class" % CONFIDENCE_GAP_LIMIT)
SETTINGS_REJECTED = ("white < %d, opening %d px; main-scene selector v%d rejected "
                     "all package masks with fill < %s"
                     % (derive.WHITE_LEVEL, derive.OPEN_SIZE, VERSION, MIN_MASK_FILL))
SETTINGS_CONTEXT = ("white < %d, opening %d px; main-scene selector v%d preserves "
                    "photo context for a full-frame package with mask fill < %s"
                    % (derive.WHITE_LEVEL, derive.OPEN_SIZE, VERSION, MAX_FRAME_MASK_FILL))


def selector_version(version):
    """Use the current selector for True and the saved selector for a version number."""
    version = VERSION if version is True else version
    if version not in (1, 2, VERSION):
        raise ValueError("unsupported main-scene selector version: %r" % version)
    return version


def settings_for(version):
    """Return the settings text of the saved selector version."""
    return {1: SETTINGS_V1, 2: SETTINGS_V2, VERSION: SETTINGS}[selector_version(version)]


def _clip(value):
    return max(0.0, min(1.0, float(value)))


def _box(item, width, height):
    """Return the clamped float box of one SAM3 instance, or None."""
    box = item.get("box")
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        return None
    try:
        x1, y1, x2, y2 = (float(value) for value in box)
    except (TypeError, ValueError):
        return None
    x1, x2 = sorted((max(0.0, min(width, x1)), max(0.0, min(width, x2))))
    y1, y2 = sorted((max(0.0, min(height, y1)), max(0.0, min(height, y2))))
    return (x1, y1, x2, y2) if x2 > x1 and y2 > y1 else None


def _area(item, box):
    try:
        value = float(item.get("area") or 0)
    except (TypeError, ValueError):
        value = 0.0
    return max(1.0, value or ((box[2] - box[0]) * (box[3] - box[1])))


def _intersection_share(inner, outer):
    width = max(0.0, min(inner[2], outer[2]) - max(inner[0], outer[0]))
    height = max(0.0, min(inner[3], outer[3]) - max(inner[1], outer[1]))
    own = max(1.0, (inner[2] - inner[0]) * (inner[3] - inner[1]))
    return width * height / own


def _original_box(box, scale, image):
    factor = 1.0 / scale if scale > 0 else 1.0
    return [
        max(0, min(image.width, int(math.floor(box[0] * factor)))),
        max(0, min(image.height, int(math.floor(box[1] * factor)))),
        max(0, min(image.width, int(math.ceil(box[2] * factor)))),
        max(0, min(image.height, int(math.ceil(box[3] * factor)))),
    ]


def _sharpness(image, box):
    """Return the grayscale gradient energy of an original-image box."""
    if box[2] <= box[0] or box[3] <= box[1]:
        return 0.0
    crop = image.crop(tuple(box)).convert("L")
    crop.thumbnail((256, 256), Image.Resampling.LANCZOS)
    values = np.asarray(crop, dtype=np.float32)
    if min(values.shape) < 2:
        return 0.0
    horizontal = np.abs(np.diff(values, axis=1)).mean()
    vertical = np.abs(np.diff(values, axis=0)).mean()
    return float(horizontal + vertical)


def _normalize(values):
    """Return min-max-normalized values. An equal non-empty group gets 0.5."""
    if not values:
        return []
    low, high = min(values), max(values)
    if high <= low:
        return [0.5] * len(values)
    return [(value - low) / (high - low) for value in values]


def _peer_count(candidate, packages, height):
    """Count similar packages in the horizontal shelf band of `candidate`."""
    label = derive.BOTTLE_LABEL if candidate["label"] == "bottle" else candidate["label"]
    center_y = (candidate["box"][1] + candidate["box"][3]) / 2
    peers = 0
    for other in packages:
        if other is candidate:
            continue
        other_label = derive.BOTTLE_LABEL if other["label"] == "bottle" else other["label"]
        if other_label != label:
            continue
        ratio = other["area_raw"] / candidate["area_raw"]
        other_y = (other["box"][1] + other["box"][3]) / 2
        if 0.5 <= ratio <= 2.0 and abs(other_y - center_y) <= 0.18 * height:
            peers += 1
    return peers


def rank(image, instances, scale, version=VERSION):
    """Return `(selected instance, audit)` for the SAM3 `instances` of `image`."""
    version = selector_version(version)
    sent_width = max(1, round(image.width * scale))
    sent_height = max(1, round(image.height * scale))
    hands = []
    packages = []
    rejected = []
    for source_index, item in enumerate(instances):
        label = str(item.get("label") or "").strip().lower()
        box = _box(item, sent_width, sent_height)
        if box is None:
            continue
        if label == HAND_LABEL:
            hands.append(box)
        elif label in PACKAGE_LABELS and item.get("mask_png_b64"):
            original = _original_box(box, scale, image)
            area = _area(item, box)
            # SAM3 reports foreground pixels in the sent image. A zero-area mask
            # MUST NOT use the box area as evidence that it contains a package.
            if version >= 2 and item.get("area") == 0:
                area = 0.0
            fill = area / ((box[2] - box[0]) * (box[3] - box[1]))
            if version >= 2 and fill < MIN_MASK_FILL:
                rejected.append({"source_index": source_index, "label": label,
                                 "box": original, "detector_score": item.get("score"),
                                 "mask_fill": round(fill, 6),
                                 "reason": "mask_fill_below_minimum"})
                continue
            packages.append({"source_index": source_index, "instance": item, "label": label,
                             "box": box, "original_box": original,
                             "area_raw": area})
    weights = HAND_WEIGHTS if hands else SCENE_WEIGHTS
    audit = {"version": version, "mode": "hand" if hands else "scene", "texts": TEXTS,
             "image_size": [image.width, image.height],
             "sam3_size": [sent_width, sent_height], "hands": len(hands),
             "weights": dict(weights), "candidates": [], "selected": None}
    if version >= 2:
        audit.update(min_mask_fill=MIN_MASK_FILL, min_frame_cover=MIN_FRAME_COVER,
                     max_frame_mask_fill=MAX_FRAME_MASK_FILL, rejected=rejected)
    if version >= 3:
        audit["confidence_gap_limit"] = CONFIDENCE_GAP_LIMIT
    if not packages:
        return None, audit

    maximum_area = max(item["area_raw"] for item in packages)
    sharpness_raw = [_sharpness(image, item["original_box"]) for item in packages]
    sharpness = _normalize(sharpness_raw)
    half_diagonal = math.hypot(sent_width, sent_height) / 2
    image_center = (sent_width / 2, sent_height / 2)
    for item, sharp, sharp_raw in zip(packages, sharpness, sharpness_raw):
        box = item["box"]
        box_area = max(1.0, (box[2] - box[0]) * (box[3] - box[1]))
        relative_area = item["area_raw"] / maximum_area
        overlap = max((_intersection_share(box, hand) for hand in hands), default=0.0)
        # The area gate prevents a small shelf bottle inside a large hand box from
        # getting a strong hand-contact signal.
        hand_contact = min(1.0, 1.5 * overlap) * min(1.0, relative_area / 0.4)
        center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
        distance = math.hypot(center[0] - image_center[0], center[1] - image_center[1])
        touched = sum((box[0] <= 0.01 * sent_width, box[1] <= 0.01 * sent_height,
                       box[2] >= 0.99 * sent_width, box[3] >= 0.99 * sent_height))
        peers = _peer_count(item, packages, sent_height)
        signals = {
            "hand_contact": _clip(hand_contact),
            "area": _clip(math.sqrt(relative_area)),
            "center": _clip(1.0 - distance / max(1.0, half_diagonal)),
            "sharpness": _clip(sharp),
            "confidence": _clip(item["instance"].get("score") or 0),
            "mask_fill": _clip(item["area_raw"] / box_area),
            "shelf_isolation": _clip(1.0 - peers / 4.0),
            "edge_visibility": _clip(1.0 - touched / 4.0),
        }
        contributions = {name: signals[name] * weight for name, weight in weights.items()}
        item.update(signals=signals, contributions=contributions, peers=peers,
                    sharpness_raw=sharp_raw, scene_score=sum(contributions.values()))

    if version >= 3 and not hands:
        # Apply eligibility after signal calculation. A rejected secondary detection
        # MUST NOT change the scene scores of the other candidates.
        strongest = {}
        for item in packages:
            label = derive.BOTTLE_LABEL if item["label"] == "bottle" else item["label"]
            confidence = item["signals"]["confidence"]
            strongest[label] = max(strongest.get(label, 0.0), confidence)
        eligible = []
        for item in packages:
            label = derive.BOTTLE_LABEL if item["label"] == "bottle" else item["label"]
            confidence = item["signals"]["confidence"]
            gap = strongest[label] - confidence
            if gap >= CONFIDENCE_GAP_LIMIT:
                rejected.append({"source_index": item["source_index"], "label": item["label"],
                                 "box": item["original_box"], "detector_score": confidence,
                                 "scene_score": round(item["scene_score"], 6),
                                 "strongest_detector_score": strongest[label],
                                 "confidence_gap": round(gap, 6),
                                 "reason": "detector_confidence_gap"})
            else:
                eligible.append(item)
        packages = eligible

    packages.sort(key=lambda item: (item["scene_score"], item["area_raw"],
                                    item["signals"]["confidence"], -item["source_index"]),
                  reverse=True)
    for position, item in enumerate(packages, 1):
        selected = position == 1
        record = {
            "rank": position,
            "selected": selected,
            "label": item["label"],
            "box": item["original_box"],
            "detector_score": round(item["signals"]["confidence"], 6),
            "scene_score": round(item["scene_score"], 6),
            "shelf_peers": item["peers"],
            "sharpness_raw": round(item["sharpness_raw"], 4),
            "signals": {key: round(value, 6) for key, value in item["signals"].items()},
            "contributions": {key: round(value, 6)
                              for key, value in item["contributions"].items()},
        }
        audit["candidates"].append(record)
        if selected:
            audit["selected"] = {"rank": position, "label": item["label"],
                                 "scene_score": record["scene_score"],
                                 "box": item["original_box"]}
    return packages[0]["instance"], audit


def _white_cut(image):
    rgb = np.asarray(image.convert("RGB"))
    full = (0, 0, image.width, image.height)
    box = derive.package_box((rgb < derive.WHITE_LEVEL).any(axis=2)) or full
    return "crop", derive.SETTINGS_WHITE, image.crop(box), box


def cut(image, segmenter, version=VERSION):
    """Return `(method, settings, processed, box, audit)` for one query photo."""
    version = selector_version(version)
    full = (0, 0, image.width, image.height)
    if derive.has_transparency(image):
        mask = np.asarray(image.getchannel("A")) > derive.ALPHA_THRESHOLD
        box = derive.package_box(mask) or full
        audit = {"version": version, "mode": "alpha", "texts": None,
                 "image_size": [image.width, image.height], "sam3_size": None,
                 "hands": 0, "weights": {}, "candidates": [], "selected": None}
        return "crop", derive.SETTINGS_ALPHA, image.crop(box), box, audit

    instances, scale = segmenter.instances(image, TEXTS)
    selected, audit = rank(image, instances, scale, version)
    if selected is None:
        audit["mode"] = "white"
        method, settings, processed, box = _white_cut(image)
        if audit.get("rejected"):
            audit["fallback_reason"] = "no_valid_package_mask"
            settings = SETTINGS_REJECTED.replace("selector v%d" % VERSION,
                                                 "selector v%d" % version)
        return method, settings, processed, box, audit

    if version >= 2:
        candidate = audit["candidates"][0]
        x1, y1, x2, y2 = candidate["box"]
        if ((x2 - x1) >= MIN_FRAME_COVER * image.width
                and (y2 - y1) >= MIN_FRAME_COVER * image.height
                and candidate["signals"]["mask_fill"] < MAX_FRAME_MASK_FILL):
            # A full-frame bottle detection can mask the glass and exclude its label.
            # Preserve the photo instead of removing most of its recognition context.
            audit["mask_policy"] = "preserve_context"
            audit["fallback_reason"] = "full_frame_low_mask_fill"
            method, _settings, processed, box = _white_cut(image)
            settings = SETTINGS_CONTEXT.replace("selector v%d" % VERSION,
                                                 "selector v%d" % version)
            return method, settings, processed, box, audit

    try:
        raw = base64.b64decode(selected["mask_png_b64"])
        with Image.open(io.BytesIO(raw)) as opened:
            mask = opened.convert("L")
    except (KeyError, ValueError, OSError) as exc:
        raise ValueError("SAM3 sent an invalid mask of the selected package: %s" % exc)
    if mask.size != image.size:
        mask = mask.resize(image.size, Image.Resampling.BILINEAR)
    mask = mask.point(lambda value: 255 if value >= 128 else 0)
    alpha = derive.refine_mask(mask)
    if image.mode == "RGBA":
        alpha = ImageChops.darker(alpha, image.getchannel("A"))
    box = alpha.point(lambda value: 255 if value > 0 else 0).getbbox() or full
    out = image.convert("RGBA")
    out.putalpha(alpha)
    return "seg", settings_for(version), out.crop(box), box, audit
