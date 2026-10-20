"""The label of the selected package in one SAM3 answer of the backend `cascade`.

This module ports the label rule of `workbench/pipeline/alternatives.py`
(`_label_candidates`, `_centre_on`, `body_labels`, `label_box_cut`, `label_cut`): of two
instances of one region the larger one stays; a label that is the package is not a
label; the largest mask wins; other body labels on the package give the box around all
of them, with no mask. The lab finds the package through the noun `bottle`. Here the
selected package box plays that role, and only a label whose centre lies on that package
counts. With no package (a label close-up), the largest label wins with no package test.
The boxes of the SAM3 answer are in the pixels of the SAM3 copy.
"""

from dataclasses import dataclass
import math

from . import photo


LABEL_NOUN = "label"
BOTTLE_IOU, BOTTLE_COVER, BOTTLE_COVER_IOU = 0.80, 0.80, 0.40
DUPLICATE_IOU = 0.90
MIN_BOX_SIDE = 8
INSIDE = 0.02
BODY_AREA, BODY_WIDTH, PART_COVER = 0.25, 0.60, 0.80


@dataclass(frozen=True)
class LabelChoice:
    """The main label instance and the other body labels that count next to it."""

    main: dict
    others: tuple


def _box(item):
    box = item.get("box")
    if not box or len(box) != 4:
        return None
    return tuple(float(value) for value in box)


def _area(box):
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _iou(a, b):
    inter = _area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))
    union = _area(a) + _area(b) - inter
    return inter / union if union > 0 else 0.0


def _covers(a, b):
    """Return the share of `b` that lies inside `a`."""
    inter = _area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))
    return inter / _area(b) if _area(b) > 0 else 0.0


def _centre_on(box, package, width, height):
    """Tell whether the centre of `box` lies on `package`, with the tolerance `INSIDE`
    of the copy of `width` × `height` pixels."""
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return (package[0] - INSIDE * width <= cx <= package[2] + INSIDE * width
            and package[1] - INSIDE * height <= cy <= package[3] + INSIDE * height)


def _larger_first(item):
    """The sort key of the rule: the larger mask first, then the higher score."""
    return (-int(item.get("area") or 0), -float(item["score"]))


def candidates(instances, package, width, height):
    """Return the labels of the rule, the largest first. `package` is the box of the
    selected package, or None for a close-up."""
    labels = []
    for item in instances:
        box = _box(item)
        if not box or item.get("score") is None:
            continue
        if box[2] - box[0] < MIN_BOX_SIDE or box[3] - box[1] < MIN_BOX_SIDE:
            continue
        if item.get("label") == LABEL_NOUN and item.get("mask_png_b64"):
            labels.append(item)
    unique = []
    for item in sorted(labels, key=_larger_first):
        if all(_iou(_box(item), _box(kept)) <= DUPLICATE_IOU for kept in unique):
            unique.append(item)
    if package is None:
        return unique
    on_package = [item for item in unique
                  if _centre_on(_box(item), package, width, height)]
    kept = [item for item in on_package
            if not (_iou(_box(item), package) > BOTTLE_IOU
                    or (_covers(_box(item), package) > BOTTLE_COVER
                        and _iou(_box(item), package) > BOTTLE_COVER_IOU))]
    return kept or on_package


def choose(instances, package, width, height):
    """Return the `LabelChoice` of the SAM3 `instances`, or None when no label counts.

    `package` is the box of the selected package in copy pixels, or None."""
    found = candidates(instances, package, width, height)
    if not found:
        return None
    main = found[0]
    main_box, main_area = _box(main), float(main.get("area") or 0)
    others = tuple(
        item for item in found[1:]
        if (float(item.get("area") or 0) >= BODY_AREA * main_area
            and _box(item)[2] - _box(item)[0] >= BODY_WIDTH * (main_box[2] - main_box[0])
            and _covers(main_box, _box(item)) < PART_COVER
            and (package is None or _centre_on(_box(item), package, width, height))))
    return LabelChoice(main, others)


def cut(choice, copy, image):
    """Return (the label cut on white, its box in photo pixels), or None.

    One label gets its refined mask (lab method `seg`). A label with other body labels
    gets the box around all of them, with no mask (lab method `crop`)."""
    if choice.others:
        boxes = [_box(item) for item in (choice.main,) + choice.others]
        box = (max(0, math.floor(min(b[0] for b in boxes) * copy.scale_x)),
               max(0, math.floor(min(b[1] for b in boxes) * copy.scale_y)),
               min(image.width, math.ceil(max(b[2] for b in boxes) * copy.scale_x)),
               min(image.height, math.ceil(max(b[3] for b in boxes) * copy.scale_y)))
        if box[2] <= box[0] or box[3] <= box[1]:
            return None
        return image.crop(box), box
    return photo.masked_cut(choice.main, copy, image)
