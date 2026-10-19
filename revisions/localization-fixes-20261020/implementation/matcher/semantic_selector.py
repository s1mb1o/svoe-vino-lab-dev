"""A conservative, label-preserving main-subject selector over existing detections.

The detector supplies visible masks, never ground-truth ownership or scene roles.
Selection scores describe framing, not identity confidence. Close contenders use
an explicit geometric fallback. Optional small-object recovery is bounded by the original request deadline.
"""

import base64
from dataclasses import dataclass, field
from io import BytesIO
import math
from time import monotonic

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .group import (
    DETECTION_THRESHOLD,
    SAM3_TIMEOUT_SECONDS,
    _data_url,
    _instance_mask,
    _normalize_image,
    _request_sam3,
    GroupMatchError,
)


VERSION = "semantic-v2"
IMPLEMENTATION_REVISION = "2026-10-20-neck-axis-and-small-object-localization"
NOUNS = ("wine bottle", "wine label", "hand", "can", "packet", "box", "price tag")
RECOVERY_NOUNS = ("bottle",)
PACKAGE_LABELS = frozenset(("wine bottle", "bottle", "can", "packet", "box"))
LABEL_LABELS = frozenset(
    ("wine label", "label", "label_front", "label_back", "label_other")
)
MIN_OWNER_CONTAINMENT = 0.65
MIN_OWNER_MARGIN = 0.12
MIN_SCENE_MARGIN = 0.10
GRID_SIDE = 256
PADDING = 0.04
MAX_LABEL_VIEWS = 8


@dataclass
class Selection:
    """One explainable decision; media coordinates refer to the oriented image."""

    status: str
    width: int
    height: int
    selected_id: str | None = None
    reason: str = ""
    candidates: list[dict] = field(default_factory=list)
    crop: bytes | None = None
    crop_box: tuple[int, int, int, int] | None = None
    keep_mask: Image.Image | None = None
    label_crops: list[bytes] = field(default_factory=list)
    label_boxes: list[tuple[int, int, int, int]] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)
    variant: str = VERSION
    label_views_truncated: bool = False
    selection_mode: str = "confident"
    fallback_trigger: str | None = None
    crop_scope: str = "subject_region"
    tap_candidate_ids: list[str] = field(default_factory=list)
    tap_status: str = "absent"
    detection_recovery: str | None = None
    detection_refinement: dict | None = None

    def as_dict(self, *, media=True):
        value = dict(
            variant=self.variant,
            implementation_revision=IMPLEMENTATION_REVISION
            if self.variant == VERSION
            else None,
            status=self.status,
            width=self.width,
            height=self.height,
            selected_id=self.selected_id,
            reason=self.reason,
            candidates=self.candidates,
            crop_box=self.crop_box,
            label_boxes=self.label_boxes,
            rejected=self.rejected,
            label_views_truncated=self.label_views_truncated,
            selection_mode=self.selection_mode,
            fallback_trigger=self.fallback_trigger,
            crop_scope=self.crop_scope,
            tap_candidate_ids=self.tap_candidate_ids,
            tap_status=self.tap_status,
            detection_recovery=self.detection_recovery,
            detection_refinement=self.detection_refinement,
        )
        if media:
            value["crop"] = _data_url("image/png", self.crop) if self.crop else None
            value["keep_mask"] = (
                _data_url("image/png", _png(self.keep_mask))
                if self.keep_mask is not None
                else None
            )
            value["label_crops"] = [
                _data_url("image/png", data) for data in self.label_crops
            ]
        return value


def _png(image):
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def _full_mask(size, prepared):
    box, mask = prepared
    full = Image.new("L", size)
    full.paste(mask, box[:2])
    return full


def _point(point, name):
    if point is None:
        return None
    if (
        not isinstance(point, (tuple, list))
        or len(point) != 2
        or any(
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not math.isfinite(v)
            or not 0 <= v <= 1
            for v in point
        )
    ):
        raise ValueError(
            "%s must contain two finite normalized coordinates in [0, 1]" % name
        )
    return tuple(float(v) for v in point)


def _iou(first, second):
    intersection = np.logical_and(first, second).sum()
    return float(intersection / max(1, np.logical_or(first, second).sum()))


def _read(image, instances):
    # Grid masks bound association/ranking work. Full-resolution masks remain the
    # source for cropping; grid masks are never enlarged into final crop masks.
    scale = min(1.0, GRID_SIDE / max(image.size))
    grid_size = tuple(max(1, round(v * scale)) for v in image.size)
    detections = []
    for index, item in enumerate(instances):
        if item.get("score", 0) < DETECTION_THRESHOLD or not item.get("mask_png_b64"):
            continue
        reported_box = item.get("primary_box", item["box"])
        item = _upright_bottle_geometry(image, _visible_bottle_geometry(image, item))
        prepared = _instance_mask(image, item)
        if prepared is None:
            continue
        full = _full_mask(image.size, prepared)
        # Actual visible pixels, not untrusted detector area, drive the score.
        grid = np.asarray(full.resize(grid_size, Image.Resampling.NEAREST)) > 0
        if not grid.any():
            continue
        detections.append(
            dict(
                id="d%d" % index,
                source_index=index,
                label=item["label"],
                box=prepared[0],
                reported_box=list(reported_box),
                geometry_source=item.get(
                    "geometry_source",
                    (
                        "visible_mask"
                        if tuple(item["box"]) != tuple(reported_box)
                        else "detector_box"
                    ),
                ),
                instance=item,
                grid=grid,
                area=full.histogram()[255],
                confidence=float(item["score"]),
                labels=[],
            )
        )
    return detections


def _visible_bottle_geometry(image, item):
    """Reconcile small box/mask disagreement without fitting an amodal outline.

    SAM3 supplies independent boxes and full-image masks. Clipping a mask to a
    slightly different box loses visible pixels and shifts center calculations.
    Use its tight visible bounds only for small localization disagreements.
    A substantially occluded mask cannot replace a larger declared object box.
    No target, other candidate, center distance or tie tolerance is consulted.
    """
    if item["label"] not in ("bottle", "wine bottle"):
        return item
    # Validate using the shared decoder first, including nonempty intersection
    # with the declared box; invalid/outside detections must remain unusable.
    if _instance_mask(image, item) is None:
        return item
    with Image.open(
        BytesIO(base64.b64decode(item["mask_png_b64"], validate=True))
    ) as opened:
        mask = opened.convert("L").point(lambda value: 255 if value >= 128 else 0)
    bounds = mask.getbbox()
    if bounds is None:
        return item
    box = item["box"]
    limit = max(2, min(box[2] - box[0], box[3] - box[1]) * 0.05)
    if any(abs(a - b) > limit for a, b in zip(box, bounds)):
        return item
    return dict(item, box=bounds)


def _upright_bottle_geometry(image, item):
    """Fit a conservative upright outline around a stable narrow neck axis.

    A narrow, straight upper profile plus visible broad body supports a bottle
    axis even when a hand/paper occludes part of the body. Expand at most 5% of
    the short side to restore bilateral extent; never shrink or move vertically.
    No other candidate, photo-center distance, target or tie tolerance is used.
    """
    if item["label"] not in ("bottle", "wine bottle"):
        return item
    m = (
        np.asarray(
            Image.open(BytesIO(base64.b64decode(item["mask_png_b64"]))).convert("L")
        )
        >= 128
    )
    bounds = Image.fromarray(m).getbbox()
    if bounds is None:
        return item
    left, top, right, bottom = bounds
    width, height = right - left, bottom - top
    box = item["box"]
    if height < 80 or width < 20 or not 2.5 < height / width < 6:
        return item
    if max(abs(a - edge) for a, edge in zip(bounds, box)) > max(2, width * 0.05):
        return item
    centers = []
    widths = []
    for row in m[top + max(2, round(height * 0.02)) : top + round(height * 0.15)]:
        xs = np.flatnonzero(row)
        if len(xs):
            centers.append(int(xs[0] + xs[-1] + 1))
            widths.append(int(xs[-1] - xs[0] + 1))
    if len(centers) < 5 or not 0.2 * width <= np.median(widths) <= 0.65 * width:
        return item
    axis = int(round(float(np.median(centers))))
    if np.percentile(np.abs(np.asarray(centers) - axis), 90) > max(2, width * 0.06):
        return item
    # Require visible broad body support, including partially occluded bottles.
    bodies = []
    for row in m[top + round(height * 0.25) : top + round(height * 0.95)]:
        xs = np.flatnonzero(row)
        if len(xs):
            bodies.append(int(xs[-1] - xs[0] + 1))
    if (
        len(bodies) < height * 0.1
        or sum(v >= width * 0.75 for v in bodies) < height * 0.1
    ):
        return item
    new_left = min(left, axis - right)
    new_right = max(right, axis - left)
    if (
        max(left - new_left, new_right - right) > max(2, width * 0.05)
        or new_left < 0
        or new_right > image.width
    ):
        return item
    return dict(
        item,
        box=(new_left, top, new_right, bottom),
        geometry_source="neck_axis"
        if (new_left, new_right) != (left, right)
        else item.get("geometry_source", "visible_mask"),
    )


def _deduplicate(items):
    kept = []
    for item in sorted(
        items, key=lambda x: (-x["area"], -x["confidence"], x["source_index"])
    ):
        if not any(_iou(item["grid"], other["grid"]) >= 0.85 for other in kept):
            kept.append(item)
    return kept


def _associate(labels, packages):
    orphans = []
    for label in labels:
        owners = []
        for package in packages:
            share = np.logical_and(label["grid"], package["grid"]).sum() / max(
                1, label["grid"].sum()
            )
            if share >= MIN_OWNER_CONTAINMENT:
                owners.append((float(share), package))
        owners.sort(key=lambda pair: (-pair[0], pair[1]["source_index"]))
        if not owners:
            # Missing white paper may be connected to the mask exterior. A
            # unique enclosing package rectangle is conservative ownership
            # evidence; overlapping rectangles remain explicitly unresolved.
            a = label["box"]
            enclosing = [
                p
                for p in packages
                if p["box"][0] <= a[0]
                and p["box"][1] <= a[1]
                and p["box"][2] >= a[2]
                and p["box"][3] >= a[3]
            ]
            if len(enclosing) == 1:
                owners = [(1.0, enclosing[0])]
        if not owners:
            # Attached tags and peeling paper can extend beyond a detector's
            # bottle box. Require mask/rectangle overlap, bounded paper extent,
            # and a unique lead; do this before rejecting standalone price cards.
            a = label["box"]
            for package in packages:
                b = package["box"]
                width, height = b[2] - b[0], b[3] - b[1]
                share = float(
                    np.logical_and(label["grid"], package["grid"]).sum()
                    / max(1, label["grid"].sum())
                )
                rectangle_share = (
                    max(0, min(a[2], b[2]) - max(a[0], b[0]))
                    * max(0, min(a[3], b[3]) - max(a[1], b[1]))
                    / max(1, (a[2] - a[0]) * (a[3] - a[1]))
                )
                share = max(share, rectangle_share)
                if (
                    share >= 0.20
                    and label["area"] <= width * height * 0.5
                    and max(a[2] - a[0], a[3] - a[1]) <= max(width, height) * 0.5
                    and a[0] >= b[0] - min(width, height) * 1.25
                    and a[2] <= b[2] + min(width, height) * 1.25
                    and a[1] >= b[1] - min(width, height) * 1.25
                    and a[3] <= b[3] + min(width, height) * 1.25
                ):
                    owners.append((share, package))
            owners.sort(key=lambda pair: (-pair[0], pair[1]["source_index"]))
        if owners and (
            len(owners) == 1 or owners[0][0] - owners[1][0] >= MIN_OWNER_MARGIN
        ):
            owners[0][1]["labels"].append(label)
        else:
            orphans.append(label)
    return orphans


def _complete_labels(labels):
    """Prefer a complete enclosing label over a nested artwork/code prediction."""
    kept = []
    for label in sorted(
        labels, key=lambda x: -(x["box"][2] - x["box"][0]) * (x["box"][3] - x["box"][1])
    ):
        a = label["box"]
        if any(
            parent["box"][0] <= a[0]
            and parent["box"][1] <= a[1]
            and parent["box"][2] >= a[2]
            and parent["box"][3] >= a[3]
            for parent in kept
        ):
            continue
        kept.append(label)
    return kept


def _hand_contacts(package, hands):
    """Visible-mask adjacency is evidence of contact, not proof of a grip."""
    bottle = package["grid"]
    support = {}
    for hand in hands:
        dilated = (
            np.asarray(
                Image.fromarray(hand["grid"].astype("uint8") * 255).filter(
                    ImageFilter.MaxFilter(7)
                )
            )
            > 0
        )
        near = np.logical_and(bottle, dilated).sum()
        # Every candidate touching this hand uses the same denominator. Dividing
        # by each object's area and capping at 1 let tiny fragments tie a grip.
        # This is unbounded geometric support, not an identity probability.
        support[hand["id"]] = float(near / max(1, math.sqrt(hand["grid"].sum()) * 1.7))
    return support


def _front_wrap(package, hand):
    """Positive wrap evidence; its absence does not prove that a hand is behind.

    Real pouring grips can have no front-surface pixels. Do not reject those
    grips using this test; use front wrapping only to resolve competing contact.
    """
    cache = package.setdefault("hand_wrap", {})
    if hand["id"] in cache:
        return cache[hand["id"]]
    body, skin = package["grid"], hand["grid"]
    interior = np.zeros_like(body)
    spans = False
    for row_index, row in enumerate(body):
        indices = np.flatnonzero(row)
        if len(indices) > 1:
            interior[row_index, indices[0] + 1 : indices[-1]] = True
            spans |= bool(
                skin[row_index, : indices[0]].any()
                and skin[row_index, indices[-1] + 1 :].any()
            )
    for column_index, column in enumerate(body.T):
        indices = np.flatnonzero(column)
        if len(indices) > 1:
            interior[indices[0] + 1 : indices[-1], column_index] = True
            spans |= bool(
                skin[: indices[0], column_index].any()
                and skin[indices[-1] + 1 :, column_index].any()
            )
    cache[hand["id"]] = bool(spans and (skin & interior).any())
    return cache[hand["id"]]


def _held_subject(pool, hands):
    """Resolve each hand independently before aggregating physical subjects.

    A larger contact band from another hand cannot erase a second grip. Boxes
    enclosing a hand are occlusion alternatives when a bottle also contacts it;
    this exception does not reject legitimate bottle body grips.
    """
    owners = set()
    uncertain = False
    for package in pool:
        package["ambiguous_hand_contact"] = False
        package["confirmed_hand_owner"] = False
    for hand in hands:
        a = hand["box"]
        touched = [p for p in pool if p["hand_contacts"].get(hand["id"], 0) >= 0.25]
        bottles = [p for p in touched if p["label"] in ("bottle", "wine bottle")]
        alternatives = [
            p
            for p in touched
            if not (
                bottles
                and p["label"] in ("box", "packet")
                and (
                    p["box"][0] <= a[0]
                    and p["box"][1] <= a[1]
                    and p["box"][2] >= a[2]
                    and p["box"][3] >= a[3]
                )
            )
        ]
        ranked = sorted(
            alternatives, key=lambda p: -p["hand_contacts"].get(hand["id"], 0)
        )
        if not ranked:
            continue
        first = ranked[0]["hand_contacts"][hand["id"]]
        second = ranked[1]["hand_contacts"][hand["id"]] if len(ranked) > 1 else 0
        # Wrapping breaks unresolved contact ties; it cannot erase a stronger
        # established grip (including valid pouring grips with no front pixels).
        if not (first - second >= 0.20 and first >= second * 1.5):
            wrapped = sorted(
                (
                    p
                    for p in alternatives
                    if p["hand_contacts"][hand["id"]] >= first * 0.5
                    and _front_wrap(p, hand)
                ),
                key=lambda p: -p["hand_contacts"][hand["id"]],
            )
            if wrapped:
                ranked = wrapped
                first = ranked[0]["hand_contacts"][hand["id"]]
                second = (
                    ranked[1]["hand_contacts"][hand["id"]] if len(ranked) > 1 else 0
                )
        if first - second >= 0.20 and first >= second * 1.5:
            owners.add(ranked[0]["id"])
        else:
            uncertain = True
            for package in alternatives:
                package["ambiguous_hand_contact"] = True
    for package in pool:
        package["confirmed_hand_owner"] = package["id"] in owners
    if len(owners) > 1:
        for package in pool:
            if package["id"] in owners:
                package["ambiguous_hand_contact"] = True
    if len(owners) == 1 and not uncertain:
        return next(p for p in pool if p["id"] in owners), None
    return None, "multiple_hand_subjects" if len(
        owners
    ) > 1 else "hand_contact_has_no_unique_owner" if uncertain else None


def _silhouette_frame(item, size):
    """Estimate a bottle's longitudinal axis and wider base from visible pixels.

    Coordinates are in oriented photo pixels. Taper gives the sign; a symmetric
    vertical silhouette retains the conventional downward assumption. This is
    a shared-support heuristic, not gravity or camera-depth reconstruction.
    """
    if "_frame" in item:
        return item["_frame"]
    y, x = np.nonzero(item["grid"])
    if len(x) < 3:
        return None
    points = np.column_stack(
        (
            (x + 0.5) * size[0] / item["grid"].shape[1],
            (y + 0.5) * size[1] / item["grid"].shape[0],
        )
    )
    centered = points - points.mean(axis=0)
    values, vectors = np.linalg.eigh(centered.T @ centered / len(points))
    if values[-1] < values[0] * 1.8:
        item["_frame"] = None
        return None
    axis = vectors[:, -1]
    along = points @ axis
    across = points @ np.array([-axis[1], axis[0]])
    span = float(np.ptp(along))
    widths = [
        float(np.ptp(across[along <= along.min() + span * 0.25])),
        float(np.ptp(across[along >= along.max() - span * 0.25])),
    ]
    if widths[0] > widths[1] * 1.1 or (
        max(widths) <= min(widths) * 1.1 and axis[1] < 0
    ):
        axis = -axis
    item["_frame"] = dict(points=points, axis=axis)
    return item["_frame"]


def _grip_evidence(package, hand, size):
    """Positive geometry for a grip; unique adjacency alone is insufficient.

    Front crossing, substantial front coverage, or extended opposed contact
    may support a grip. Contact confined to a neck/base can also be a hand
    behind the bottle. None of these measurements reconstructs physical depth.
    """
    body, skin = package["grid"], hand["grid"]
    interior = np.zeros_like(body)
    opposed = np.zeros_like(body)
    for rows, fingers, inside, both in (
        (body, skin, interior, opposed),
        (body.T, skin.T, interior.T, opposed.T),
    ):
        for index, row in enumerate(rows):
            positions = np.flatnonzero(row)
            if len(positions) > 1:
                lo, hi = positions[0], positions[-1]
                inside[index, lo + 1 : hi] = True
                if fingers[index, :lo].any() and fingers[index, hi + 1 :].any():
                    both[index, lo : hi + 1] = True
    front_pixels = int((skin & interior).sum())
    front_fraction = front_pixels / max(1, int(skin.sum()))
    front_body_fraction = front_pixels / max(1, int(body.sum()))
    dilated = (
        np.asarray(
            Image.fromarray(skin.astype("uint8") * 255).filter(ImageFilter.MaxFilter(7))
        )
        > 0
    )
    contact = body & dilated
    terminal_opposition = False
    contact_span = None
    frame = _silhouette_frame(package, size)
    if frame is not None and contact.any():
        y, x = np.nonzero(contact)
        points = np.column_stack(
            ((x + 0.5) * size[0] / body.shape[1], (y + 0.5) * size[1] / body.shape[0])
        )
        axis = frame["axis"]
        body_along, touch_along = frame["points"] @ axis, points @ axis
        span = float(np.ptp(body_along))
        contact_span = float(np.ptp(touch_along) / span) if span > 0 else None
        terminal_opposition = bool(
            span > 0
            and (
                touch_along.min() - body_along.min() <= span * 0.06
                or body_along.max() - touch_along.max() <= span * 0.06
            )
            and (contact & opposed).sum() >= max(2, contact.sum() * 0.20)
        )
    wrapped = _front_wrap(package, hand) and front_pixels >= 2
    # An extended arm can make front/hand area small even for a genuine body
    # grip. Localized front contact supplies a separate positive cue; a long
    # forearm crossing the bottle does not satisfy this route.
    localized_front_contact = bool(
        front_pixels >= 2
        and front_fraction >= 0.12
        and front_body_fraction <= 0.10
        and contact_span is not None
        and 0.10 <= contact_span <= 0.50
    )
    broad_front_contact = bool(
        front_pixels >= 2
        and front_fraction >= 0.25
        and (
            package["label"] not in ("wine bottle", "bottle")
            or front_body_fraction <= 0.25
        )
    )
    # Opposed skin at only the cap or base does not establish a grip. A genuine
    # pour with no front pixels may have contact along most of the remaining
    # visible bottle; retain that path without treating every end contact alike.
    extended_terminal_contact = bool(
        terminal_opposition and contact_span is not None and contact_span >= 0.50
    )
    slender_unlabelled_object = False
    if frame is not None and package["label"] in ("wine bottle", "bottle"):
        axis = frame["axis"]
        points = frame["points"]
        width = float(np.ptp(points @ np.array([-axis[1], axis[0]])))
        slender_unlabelled_object = bool(
            np.ptp(points @ axis) > max(1, width) * 8
            and not any(label["label"] in LABEL_LABELS for label in package["labels"])
        )
    return dict(
        front_wrap=wrapped,
        front_fraction=round(front_fraction, 6),
        front_body_fraction=round(front_body_fraction, 6),
        terminal_opposition=terminal_opposition,
        extended_terminal_contact=extended_terminal_contact,
        slender_unlabelled_object=slender_unlabelled_object,
        contact_span=round(contact_span, 6) if contact_span is not None else None,
        localized_front_contact=localized_front_contact,
        broad_front_contact=broad_front_contact,
        confirmed=bool(
            not slender_unlabelled_object
            and (
                wrapped
                or broad_front_contact
                or extended_terminal_contact
                or localized_front_contact
            )
        ),
    )


def _label_panels(packages, labels, rejected):
    """An outer paper mask containing a complete bottle is depiction context.

    Require visible-mask containment and margins on every side; a rectangle
    overlapping a real foreground bottle does not suffice. Keep the full panel,
    and do not claim that its nested bottle artwork is a separate physical wine.
    """
    embedded = []
    for paper in labels:
        a = paper["box"]
        margin = min(a[2] - a[0], a[3] - a[1]) * 0.03
        for package in packages:
            if package["label"] not in ("wine bottle", "bottle"):
                continue
            b = package["box"]
            contained = np.logical_and(paper["grid"], package["grid"]).sum() / max(
                1, package["grid"].sum()
            )
            if (
                contained >= 0.95
                and package["area"] <= paper["area"] * 0.65
                and b[0] >= a[0] + margin
                and b[1] >= a[1] + margin
                and b[2] <= a[2] - margin
                and b[3] <= a[3] - margin
            ):
                paper["panel_context"] = True
                embedded.append(package)
    for package in packages:
        if any(package is item for item in embedded):
            rejected.append(
                dict(id=package["id"], reason="bottle_depiction_in_label_panel")
            )
    panels = [p for p in labels if p.get("panel_context")]
    kept_labels = []
    for label in labels:
        if not label.get("panel_context") and any(
            np.logical_and(label["grid"], p["grid"]).sum() / max(1, label["grid"].sum())
            >= 0.95
            for p in panels
        ):
            rejected.append(dict(id=label["id"], reason="artwork_in_label_panel"))
        else:
            kept_labels.append(label)
    return [p for p in packages if not any(p is item for item in embedded)], kept_labels


def _foreground_evidence(largest, peers, size):
    frame = _silhouette_frame(largest, size)
    if largest["label"] not in ("bottle", "wine bottle") or frame is None:
        return False
    axis = frame["axis"]
    # A bucket or price-card detection is not a bottle-scale/depth reference.
    # It remains a candidate for explicit selection and geometric fallback.
    peers = [p for p in peers if p["label"] in ("bottle", "wine bottle")]
    if not peers:
        return False
    complete = [p for p in peers if not _at_edge(p, size)]
    if len(complete) >= 2:
        # Several intact references can establish prominence despite small
        # cropped shelf distractors. A lone/truncated reference still cannot.
        peers = [
            p for p in peers if not _at_edge(p, size) or largest["area"] < p["area"] * 3
        ]
    peer_frames = [(p, _silhouette_frame(p, size)) for p in peers]
    bottle_frames = [
        f
        for p, f in peer_frames
        if p["label"] in ("wine bottle", "bottle") and f is not None
    ]
    if len(bottle_frames) >= 2 and all(
        abs(float(f["axis"] @ bottle_frames[0]["axis"])) >= 0.85 for f in bottle_frames
    ):
        reference = bottle_frames[0]["axis"]
        common = sum(
            (
                f["axis"] if f["axis"] @ reference >= 0 else -f["axis"]
                for f in bottle_frames
            ),
            np.zeros(2),
        )
        common /= np.linalg.norm(common)
        if abs(float(axis @ common)) < 0.85:
            axis = common
        elif float(axis @ common) < 0:
            # Occlusion can invert the taper sign without rotating the bottle.
            axis = -axis
    projected = frame["points"] @ axis
    longitudinal_span = np.ptp(frame["points"] @ frame["axis"])
    aligned = abs(float(frame["axis"] @ axis)) >= 0.85
    extent = abs(axis[0]) * size[0] + abs(axis[1]) * size[1]
    largest["foreground_axis"] = [float(v) for v in axis]
    for peer, other in peer_frames:
        if _at_edge(peer, size):
            return False
        if other is None or (
            peer["label"] in ("bottle", "wine bottle")
            and abs(float(other["axis"] @ axis)) < 0.85
        ):
            return False
        projection = other["points"] @ axis
        if (
            largest["area"] < peer["area"] * 1.45
            or longitudinal_span < np.ptp(other["points"] @ other["axis"]) * 1.2
            or projected.max() - projection.max() < extent * 0.025
            or (aligned and projection.max() < projected.min())
            # Borrowing upright peers' axes for a lying bottle does not prove
            # a common support plane across a large empty vertical gap.
            or (
                not aligned
                and projected.min() - projection.max()
                > np.ptp(other["points"] @ other["axis"]) * 0.65
            )
        ):
            return False
    return True


def _at_edge(item, size):
    x, y, X, Y = item["box"]
    return x <= 0 or y <= 0 or X >= size[0] or Y >= size[1]


def _edge_closeup(largest, peers, size):
    """Strong clipped framing is intent evidence, without claiming camera depth."""
    if (
        not _at_edge(largest, size)
        or largest["label"] not in ("wine bottle", "bottle")
        or not any(label["label"] in LABEL_LABELS for label in largest["labels"])
        or not peers
    ):
        return False
    frame = _silhouette_frame(largest, size)
    if frame is None:
        return False
    axis = frame["axis"]
    extent = abs(axis[0]) * size[0] + abs(axis[1]) * size[1]
    span = float(np.ptp(frame["points"] @ axis))
    return bool(
        span >= extent * 0.40
        and all(largest["area"] >= other["area"] * 3 for other in peers)
    )


def _focus(image, box):
    """Contrast-normalized tile gradients prevent one vivid logo dominating."""
    crop = image.crop(box).convert("L")
    crop.thumbnail((128, 128))
    array = np.asarray(crop, dtype=float)
    values = []
    for tile in [
        part
        for row in np.array_split(array, 3)
        for part in np.array_split(row, 3, axis=1)
    ]:
        if min(tile.shape) < 3:
            continue
        contrast = float(np.percentile(tile, 90) - np.percentile(tile, 10))
        if contrast > 5:
            gradient = (
                np.abs(np.diff(tile, axis=0)).mean()
                + np.abs(np.diff(tile, axis=1)).mean()
            )
            values.append(min(1.0, float(gradient / contrast)))
    return float(np.median(values)) if values else 0.0


def _box_distance(box, point, size):
    x, y = point[0] * size[0], point[1] * size[1]
    return math.hypot(
        (x - (box[0] + box[2]) / 2) / size[0], (y - (box[1] + box[3]) / 2) / size[1]
    )


def _mask_contains(item, point, size):
    x = min(size[0] - 1, int(point[0] * size[0]))
    y = min(size[1] - 1, int(point[1] * size[1]))
    box, mask = _instance_mask(Image.new("L", size), item["instance"])
    return (
        box[0] <= x < box[2]
        and box[1] <= y < box[3]
        and bool(mask.getpixel((x - box[0], y - box[1])))
    )


def _contains(item, point, size):
    x = min(size[0] - 1, int(point[0] * size[0]))
    y = min(size[1] - 1, int(point[1] * size[1]))
    return (
        _mask_contains(item, point, size)
        or (
            item["label"] in LABEL_LABELS
            and item["box"][0] <= x < item["box"][2]
            and item["box"][1] <= y < item["box"][3]
        )
        or any(
            label["box"][0] <= x < label["box"][2]
            and label["box"][1] <= y < label["box"][3]
            for label in item["labels"]
        )
    )


def _fallback(candidates, size):
    """Photo-center coverage, pixel distance, left, upper, stable numeric ID.

    Twice-center integer coordinates make exact distance ties independent of
    floating point and photo aspect ratio. Label rectangles do not count as
    visible bottle-mask coverage. Source IDs are stable within one response.
    """
    pool = [x for x in candidates if x["contains_photo_center"]]
    reason = "fallback_center_contains" if pool else "fallback_nearest_center"
    pool = pool or list(candidates)
    keys = (
        (
            lambda x: (
                (x["box"][0] + x["box"][2] - size[0]) ** 2
                + (x["box"][1] + x["box"][3] - size[1]) ** 2
            ),
            "fallback_nearest_center",
        ),
        (lambda x: x["box"][0] + x["box"][2], "fallback_leftmost"),
        (lambda x: x["box"][1] + x["box"][3], "fallback_uppermost"),
        (lambda x: x["source_index"], "fallback_stable_id"),
    )
    for key, tie_reason in keys:
        if len(pool) == 1:
            break
        minimum = min(key(x) for x in pool)
        narrowed = [x for x in pool if key(x) == minimum]
        if len(narrowed) < len(pool):
            reason = tie_reason
        pool = narrowed
    return pool[0], reason


def _original_frame(image, result):
    result.crop_scope = "original_frame"
    result.crop_box = (0, 0, *image.size)
    result.keep_mask = Image.new("L", image.size, 255)
    result.crop = _png(image)


def _fill_interior_holes(mask):
    """Restore original photo pixels in enclosed holes, never outside the outline."""
    padded = Image.new("L", (mask.width + 2, mask.height + 2))
    padded.paste(mask, (1, 1))
    ImageDraw.floodfill(padded, (0, 0), 128)
    holes = np.asarray(padded)[1:-1, 1:-1] == 0
    return Image.fromarray(np.where(holes, 255, np.asarray(mask)).astype("uint8"))


def _pad(box, size):
    dx = max(2, round((box[2] - box[0]) * PADDING))
    dy = max(2, round((box[3] - box[1]) * PADDING))
    return (
        max(0, box[0] - dx),
        max(0, box[1] - dy),
        min(size[0], box[2] + dx),
        min(size[1], box[3] + dy),
    )


def _crops(image, selected, result):
    labels = selected["labels"]
    if selected["label"] in LABEL_LABELS:
        # A lone label prediction could itself be a misclassified logo. Without a
        # trustworthy enclosing bottle, the original frame is the safe context.
        keep = Image.new("L", image.size, 255)
        box = (0, 0, image.width, image.height)
        labels = [selected]
        result.crop_scope = "context_frame"
    else:
        prepared_box, mask = _instance_mask(image, selected["instance"])
        # An omitted secondary label can leave a hole even when the main label
        # was detected. Restore observed pixels in every enclosed hole first.
        keep = _full_mask(image.size, (prepared_box, _fill_interior_holes(mask)))
        box = selected["box"]
        preserve = selected["instance"].get("preserve_box")
        if preserve is not None:
            box = (
                min(box[0], preserve[0]),
                min(box[1], preserve[1]),
                max(box[2], preserve[2]),
                max(box[3], preserve[3]),
            )
        # A missing paper strip can connect to the silhouette exterior, so hole
        # filling cannot recover it. Preserve source RGB throughout the subject
        # rectangle, including unobserved secondary paper and direct glass ink.
        # This deliberately trades some isolation for complete visible labels.
        keep.paste(255, box)
        for label in labels:
            # Preserve blank paper, text and artwork even when the label mask has
            # holes or has collapsed to artwork inside its detector box.
            keep.paste(255, _pad(label["box"], image.size))
            box = (
                min(box[0], label["box"][0]),
                min(box[1], label["box"][1]),
                max(box[2], label["box"][2]),
                max(box[3], label["box"][3]),
            )
    box = _pad(box, image.size)
    result.crop_box = box
    result.keep_mask = keep
    result.crop = _png(
        Image.composite(image, Image.new("RGB", image.size, "white"), keep).crop(box)
    )
    result.label_views_truncated = len(labels) > MAX_LABEL_VIEWS
    for label in sorted(labels, key=lambda x: -x["area"])[:MAX_LABEL_VIEWS]:
        label_box = _pad(label["box"], image.size)
        bottle_box = selected["box"]
        label_area = (label["box"][2] - label["box"][0]) * (
            label["box"][3] - label["box"][1]
        )
        bottle_area = (bottle_box[2] - bottle_box[0]) * (bottle_box[3] - bottle_box[1])
        if selected["label"] in LABEL_LABELS:
            label_box = (0, 0, image.width, image.height)
        elif label_area < 0.05 * bottle_area:
            label_box = _pad(bottle_box, image.size)
        result.label_boxes.append(label_box)
        result.label_crops.append(_png(image.crop(label_box)))


def select(image, instances, *, tap=None, aim=None):
    """Select over caller-supplied detections, reusing their masks and coordinates.

    tap/aim are normalized in the oriented image. An explicit reticle (aim) carries
    more intent than an assumed optical center. No identity/OCR result is consumed.
    """
    tap, aim = _point(tap, "tap"), _point(aim, "aim")
    image = image.convert("RGB")
    result = Selection("no_target", *image.size, reason="no_credible_bottle_or_label")
    detections = _read(image, instances)
    packages = _deduplicate([x for x in detections if x["label"] in PACKAGE_LABELS])
    labels = _deduplicate([x for x in detections if x["label"] in LABEL_LABELS])
    hands = [x for x in detections if x["label"] == "hand"]
    price_tags = [x for x in detections if x["label"] == "price tag"]
    # Bottle pictures embedded in a detected carton are not independent physical
    # targets. Keep the carton as the package; never let its artwork beat it.
    embedded = []
    for item in packages:
        if item["label"] not in ("bottle", "wine bottle"):
            continue
        for container in packages:
            if container["label"] not in ("box", "packet"):
                continue
            share = np.logical_and(item["grid"], container["grid"]).sum() / max(
                1, item["grid"].sum()
            )
            if share > 0.95 and item["area"] < container["area"] * 0.8:
                embedded.append(item)
                result.rejected.append(
                    dict(id=item["id"], reason="embedded_in_packaging")
                )
                break
    packages = [x for x in packages if not any(x is item for item in embedded)]
    packages, labels = _label_panels(packages, labels, result.rejected)
    orphans = _associate(labels, packages)
    # Attached paper sometimes receives only the price-tag class. Protect its
    # pixels through the same bounded ownership checks; standalone shelf cards
    # never become candidates. Avoid duplicate views for the same paper.
    _associate(
        [
            tag
            for tag in price_tags
            if not any(_iou(tag["grid"], label["grid"]) >= 0.85 for label in labels)
        ],
        packages,
    )
    # A foreground label's enclosing rectangle may overlap a different bottle's
    # real label. Suppress nested graphics only within the same inferred owner.
    for package in packages:
        package["labels"] = _complete_labels(package["labels"])
    candidates = list(packages)
    pending_paper = any(label.get("panel_context") for label in labels)
    dominant_orphan_paper = False
    largest_region = max((x["area"] for x in packages + orphans), default=0)
    largest_extent = max(
        (
            (x["box"][2] - x["box"][0]) * (x["box"][3] - x["box"][1])
            for x in packages + orphans
        ),
        default=0,
    )
    has_bottle = any(x["label"] in ("wine bottle", "bottle") for x in packages)
    for label in orphans:
        dominant_paper = (
            label["area"] >= largest_region
            or (label["box"][2] - label["box"][0]) * (label["box"][3] - label["box"][1])
            >= largest_extent
        )
        dominant_orphan_paper |= dominant_paper
        price_conflict = any(
            np.logical_and(label["grid"], tag["grid"]).sum()
            / max(1, label["grid"].sum())
            >= 0.8
            for tag in price_tags
        )
        tapped = tap is not None and _contains(label, tap, image.size)
        if price_conflict and not dominant_paper and not tapped:
            result.rejected.append(dict(id=label["id"], reason="standalone_price_tag"))
            continue
        if (
            has_bottle
            and not _mask_contains(label, (0.5, 0.5), image.size)
            and not tapped
        ):
            result.rejected.append(
                dict(id=label["id"], reason="orphan_label_beside_bottle")
            )
            pending_paper |= dominant_paper
            continue
        if (
            packages
            and dominant_paper
            and not tapped
            and label["area"] < max(x["area"] for x in packages) * 0.75
        ):
            pending_paper = True
        if (
            tapped
            or not packages
            or label["area"] >= max(x["area"] for x in packages) * 0.75
        ):
            candidates.append(label)
            pending_paper |= price_conflict and not tapped
    if not candidates:
        result.selection_mode = "fallback"
        result.fallback_trigger = result.reason
        result.reason = "fallback_original_frame"
        _original_frame(image, result)
        return result
    maximum = max(x["area"] for x in candidates)
    for item in candidates:
        item["hand_contacts"] = (
            _hand_contacts(item, hands) if item["label"] in PACKAGE_LABELS else {}
        )
        item["contact"] = max(item["hand_contacts"].values(), default=0.0)
        item["relative_area"] = item["area"] / maximum
        item["distance"] = _box_distance(item["box"], aim or (0.5, 0.5), image.size)
        item["contains_photo_center"] = _mask_contains(item, (0.5, 0.5), image.size)
        item["photo_center_distance_px"] = math.hypot(
            (item["box"][0] + item["box"][2] - image.width) / 2,
            (item["box"][1] + item["box"][3] - image.height) / 2,
        )
        item["focus"] = _focus(image, item["box"])
        peers = sum(
            0.65 <= other["area"] / item["area"] <= 1.55
            and abs(
                (other["box"][1] + other["box"][3] - item["box"][1] - item["box"][3])
                / 2
            )
            < image.height * 0.18
            for other in candidates
            if other is not item
        )
        item["isolation"] = 1.0 / (1.0 + peers)
        item["prominence"] = min(
            1.0, math.sqrt(item["area"] / (image.width * image.height)) / 0.55
        )
        item["score"] = (
            0.55 * item["prominence"]
            + 0.35
            * max(0.0, 1.0 - _box_distance(item["box"], (0.5, 0.5), image.size) * 1.5)
            + 0.05 * item["focus"]
            + 0.05 * item["isolation"]
        )
    candidates.sort(key=lambda x: (-x["score"], x["source_index"]))
    selected = None
    pool = candidates
    unresolved = (
        "enclosing_label_panel"
        if any(p.get("panel_context") for p in labels)
        else "unresolved_dominant_paper"
        if pending_paper
        else "no_clear_main_subject"
    )
    if tap is not None:
        mask_hits = [x for x in candidates if _mask_contains(x, tap, image.size)]
        hits = mask_hits or [x for x in candidates if _contains(x, tap, image.size)]
        result.tap_candidate_ids = [x["id"] for x in hits]
        result.tap_status = (
            "resolved_mask"
            if len(mask_hits) == 1
            else "resolved_label_context"
            if len(hits) == 1
            else "multiple_hits"
            if hits
            else "missed"
        )
        if len(hits) == 1:
            selected, result.reason = hits[0], "explicit_tap"
        else:
            unresolved = "tap_has_no_unique_owner"
            # A miss does not bypass hand/aim/framing checks. Multiple hits
            # restrict every subsequent decision to the tapped alternatives.
            pool = hits or candidates
    if selected is None:
        held, hand_ambiguity = _held_subject(pool, hands)
        if held is not None:
            evidence = {
                hand["id"]: _grip_evidence(held, hand, image.size)
                for hand in hands
                if held["hand_contacts"].get(hand["id"], 0) >= 0.25
            }
            held["grip_evidence"] = evidence
            if not any(value["confirmed"] for value in evidence.values()):
                held["ambiguous_hand_contact"] = True
                held = None
                unresolved = hand_ambiguity = "hand_contact_not_confirmed"
        conflict = (
            held is not None
            and not any(label["label"] in LABEL_LABELS for label in held["labels"])
            and any(
                p is not held
                and p["contains_photo_center"]
                and p["area"] >= held["area"] * 2
                and any(label["label"] in LABEL_LABELS for label in p["labels"])
                for p in pool
            )
        )
        if conflict:
            unresolved = "unlabeled_hand_subject_conflicts_with_center"
            held = None
        if held is not None:
            selected, result.reason = held, "unique_visible_hand_contact"
        elif len(pool) == 1:
            if not pending_paper:
                selected, result.reason = pool[0], "only_credible_subject"
            else:
                result.reason = unresolved
        else:
            first, second = pool[:2]
            margin = first["score"] - second["score"]
            size_ratio = first["area"] / max(1, second["area"])
            if aim is not None:
                aimed = sorted(pool, key=lambda x: x["distance"])
                if (
                    aimed[0]["distance"] < 0.16
                    and aimed[1]["distance"] - aimed[0]["distance"] > 0.18
                ):
                    selected, result.reason = aimed[0], "explicit_capture_reticle"
            # Foreground prominence must survive center proximity. Scale plus a
            # lower projected base supports a nearer subject on the same plane;
            # a large background magnum alone cannot satisfy this check.
            bottles = [p for p in pool if p["label"] in ("wine bottle", "bottle")]
            largest = max(bottles or pool, key=lambda p: p["area"])
            peers = [p for p in pool if p is not largest]
            foreground = _foreground_evidence(largest, peers, image.size)
            other_owners = [p for p in peers if p.get("confirmed_hand_owner", False)]
            other_grips = any(
                _grip_evidence(p, hand, image.size)["confirmed"]
                for p in other_owners
                for hand in hands
                if p["hand_contacts"].get(hand["id"], 0) >= 0.25
            )
            if (
                selected is None
                and _edge_closeup(largest, peers, image.size)
                and not other_grips
                and not pending_paper
                and not conflict
            ):
                selected, result.reason = largest, "dominant_edge_subject"
            if (
                selected is None
                and foreground
                and (
                    not largest.get("ambiguous_hand_contact", False)
                    or sum(
                        not _at_edge(p, image.size)
                        for p in peers
                        if p["label"] in ("wine bottle", "bottle")
                    )
                    >= 2
                )
                and not other_owners
                and not conflict
                and not pending_paper
            ):
                selected, result.reason = largest, "foreground_scale_and_lower_base"
            if (
                selected is None
                and margin >= MIN_SCENE_MARGIN
                and size_ratio >= 1.45
                and first["label"] not in ("wine bottle", "bottle")
                and not hand_ambiguity
                and not conflict
                and not pending_paper
            ):
                selected, result.reason = first, "dominant_foreground_subject"
            elif selected is None:
                result.reason = hand_ambiguity or unresolved
    result.candidates = [
        dict(
            id=x["id"],
            source_index=x["source_index"],
            kind=x["label"],
            box=list(x["box"]),
            reported_box=x["reported_box"],
            geometry_source=x["geometry_source"],
            score=round(x["score"], 6),
            signals=dict(
                prominence=round(x["prominence"], 6),
                aim_distance=round(x["distance"], 6),
                hand_contact=round(x["contact"], 6),
                hand_contacts={
                    key: round(value, 6) for key, value in x["hand_contacts"].items()
                },
                isolation=round(x["isolation"], 6),
                focus=round(x["focus"], 6),
                foreground_axis=x.get("foreground_axis"),
                hand_wrap=x.get("hand_wrap", {}),
                ambiguous_hand_contact=x.get("ambiguous_hand_contact", False),
                confirmed_hand_owner=x.get("confirmed_hand_owner", False),
                grip_evidence=x.get("grip_evidence", {}),
                panel_context=x.get("panel_context", False),
                contains_photo_center=x["contains_photo_center"],
                photo_center_distance_px=round(x["photo_center_distance_px"], 6),
            ),
            label_ids=[label["id"] for label in x["labels"]],
            label_boxes=[list(label["box"]) for label in x["labels"]],
            eligible_for_selection=any(x is item for item in pool),
        )
        for x in candidates
    ]
    if selected is None:
        result.selection_mode = "fallback"
        result.fallback_trigger = result.reason
        selected, result.reason = _fallback(pool, image.size)
    result.status = "selected"
    result.selected_id = selected["id"]
    _crops(image, selected, result)
    # A hand or explicit interaction may establish the subject's identity while
    # its bottle mask covers only a neck. Unowned complete paper must survive
    # those paths too, not just geometric fallback.
    if pending_paper or dominant_orphan_paper:
        _original_frame(image, result)
        result.crop_scope = "context_frame"
    return result


def select_photo(
    image_bytes,
    endpoint,
    *,
    instances=None,
    tap=None,
    aim=None,
    timeout=SAM3_TIMEOUT_SECONDS,
    opener=None,
    variant=VERSION,
):
    """Normalize once; retry an empty semantic input once with a broader noun.

    Recovery shares the original time budget. Supplied instances are an exact
    replay contract and never trigger requests. A failed optional recovery keeps
    the valid primary response's original-frame fallback.
    """
    image, jpeg = _normalize_image(image_bytes)
    recovery = None
    refinement = None
    live_inference = instances is None
    if instances is None:
        deadline = monotonic() + timeout
        instances = _request_sam3(
            jpeg, *image.size, endpoint, timeout, opener=opener, nouns=NOUNS
        )
        if variant == VERSION and not any(
            item["label"] in PACKAGE_LABELS | LABEL_LABELS
            for item in _read(image, instances)
        ):
            remaining = deadline - monotonic()
            if remaining <= 0:
                recovery = "budget_exhausted"
            else:
                try:
                    additional = _request_sam3(
                        jpeg,
                        *image.size,
                        endpoint,
                        remaining,
                        opener=opener,
                        nouns=RECOVERY_NOUNS,
                    )
                    instances = [*instances, *additional]
                    recovery = (
                        "generic_bottle_found" if additional else "generic_bottle_empty"
                    )
                except GroupMatchError:
                    recovery = "unavailable"
    if live_inference and variant == VERSION:
        from .selector_detection import enhance, request_optional, small_scene

        initial = select(image, instances, tap=tap, aim=aim)
        if small_scene(image, initial):
            instances, refinement = enhance(
                image,
                instances,
                initial,
                lambda crop, **kwargs: request_optional(
                    crop, endpoint, opener=opener, **kwargs
                ),
                deadline=deadline,
            )
    result = select_variant(image, instances, tap=tap, aim=aim, variant=variant)
    result.detection_recovery = recovery
    result.detection_refinement = refinement
    return result


def select_variant(image, instances, *, variant=VERSION, tap=None, aim=None):
    """Expose the unchanged scene-v1 ranker beside semantic-v2 for paired audits."""
    if variant == VERSION:
        return select(image, instances, tap=tap, aim=aim)
    if variant != "scene-v1":
        raise ValueError("unknown selector variant")
    from .main_scene import rank_packages

    result = Selection(
        "no_target",
        *image.size,
        reason="no_usable_package",
        variant=variant,
        selection_mode="legacy",
    )
    for item in rank_packages(image, instances):
        prepared = _instance_mask(image, item)
        if prepared is None:
            continue
        index = next(i for i, original in enumerate(instances) if original is item)
        result.candidates.append(
            dict(
                id="d%d" % index,
                source_index=index,
                kind=item["label"],
                box=list(prepared[0]),
            )
        )
        if result.selected_id is None:
            result.status = "selected"
            result.selected_id = "d%d" % index
            result.reason = "existing_scene_v1_rank"
            result.crop_box = prepared[0]
            result.keep_mask = _full_mask(image.size, prepared)
            result.crop = _png(
                Image.composite(
                    image, Image.new("RGB", image.size, "white"), result.keep_mask
                ).crop(prepared[0])
            )
    if result.selected_id is None:
        # Preserve the existing select_main_package whole-image fallback. It
        # still supplies no explicit selected subject and cannot report ambiguity.
        result.reason = "existing_original_frame_fallback"
        result.crop_scope = "original_frame"
        result.crop_box = (0, 0, image.width, image.height)
        result.keep_mask = Image.new("L", image.size, 255)
        result.crop = _png(image)
    return result
