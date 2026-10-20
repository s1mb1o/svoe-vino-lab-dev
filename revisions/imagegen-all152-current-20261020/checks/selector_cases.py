"""Declared geometry fixtures, not photographs or model predictions.

Expected winners are fixed examples of the product policy, never selector outputs.
The same inputs feed unit tests and an explicitly separate HTML fixture cohort.
"""

import base64
from io import BytesIO

from PIL import Image, ImageDraw


def bottle(box, mask_box=None, score=0.9):
    return dict(label="wine bottle", box=box, mask_box=mask_box or box, score=score)


SCENARIOS = [
    dict(
        id="center-mask",
        title="Mask at photo center beats a nearer box center",
        items=[bottle((110, 40, 210, 200)), bottle((50, 40, 119, 200))],
        winner=0,
        reason="fallback_center_contains",
    ),
    dict(
        id="nearest",
        title="No center coverage: nearest bottle center",
        items=[bottle((10, 20, 70, 220)), bottle((140, 20, 200, 220))],
        winner=1,
        reason="fallback_nearest_center",
    ),
    dict(
        id="left",
        title="Equal distances: left wins despite detector order",
        items=[bottle((155, 20, 225, 220)), bottle((15, 20, 85, 220))],
        winner=1,
        reason="fallback_leftmost",
    ),
    dict(
        id="upper",
        title="Equal distance and x: upper wins",
        items=[bottle((100, 150, 140, 230)), bottle((100, 10, 140, 90))],
        winner=1,
        reason="fallback_uppermost",
    ),
    dict(
        id="overlap",
        title="Two masks cover the center: nearest box center wins",
        items=[bottle((110, 40, 190, 200)), bottle((65, 40, 145, 200))],
        winner=1,
        reason="fallback_nearest_center",
    ),
    dict(
        id="stable-id",
        title="Identical box centers: stable response ID",
        items=[
            bottle((80, 40, 160, 200), (80, 40, 105, 200)),
            bottle((80, 40, 160, 200), (135, 40, 160, 200)),
        ],
        winner=0,
        reason="fallback_stable_id",
    ),
    dict(
        id="pixel-distance",
        title="Non-square photo: Euclidean pixel distance",
        size=(400, 200),
        items=[bottle((270, 70, 330, 130)), bottle((170, 0, 230, 60))],
        winner=1,
        reason="fallback_nearest_center",
    ),
    dict(
        id="no-candidates",
        title="No candidate: unchanged full image",
        items=[],
        winner=None,
        reason="fallback_original_frame",
    ),
    dict(
        id="low-confidence",
        title="Only rejected low-confidence detection: full image",
        items=[bottle((70, 10, 170, 235), score=0.39)],
        winner=None,
        reason="fallback_original_frame",
    ),
    dict(
        id="tap-miss",
        title="Unresolved tap: still return a crop",
        items=[bottle((155, 20, 225, 220)), bottle((15, 20, 85, 220))],
        interaction=dict(tap=(0, 0)),
        winner=1,
        reason="fallback_leftmost",
    ),
    dict(
        id="reticle-unresolved",
        title="Unresolved reticle: fallback uses photo center",
        items=[bottle((60, 20, 120, 220)), bottle((160, 20, 220, 220))],
        interaction=dict(aim=(0.95, 0)),
        winner=0,
        reason="fallback_nearest_center",
    ),
]


def region(label, box, **options):
    return dict(bottle(box, **options), label=label)


REVIEW_SCENARIOS = [
    dict(
        id="missed-tap-hand",
        title="Missed tap continues to the unique hand rule",
        items=[
            bottle((15, 20, 85, 230)),
            bottle((100, 60, 140, 200)),
            region("hand", (40, 80, 60, 190)),
        ],
        interaction=dict(tap=(0.98, 0.02)),
        winner=0,
        reason="unique_visible_hand_contact",
    ),
    dict(
        id="missed-tap-single",
        title="Missed tap continues to the single candidate",
        items=[bottle((70, 10, 170, 235))],
        interaction=dict(tap=(0, 0)),
        winner=0,
        reason="only_credible_subject",
    ),
    dict(
        id="missed-tap-reticle",
        title="Missed tap continues to the explicit reticle",
        items=[bottle((15, 20, 85, 230)), bottle((155, 20, 225, 230))],
        interaction=dict(tap=(0, 0), aim=(0.8, 0.5)),
        winner=1,
        reason="explicit_capture_reticle",
    ),
    dict(
        id="mask-tap-over-label-box",
        title="A real mask hit beats another label's rectangle",
        items=[
            bottle((10, 20, 80, 230)),
            bottle((100, 20, 124, 230)),
            bottle((125, 20, 195, 230)),
            region("wine label", (20, 100, 135, 180), mask_box=(20, 100, 75, 180)),
        ],
        interaction=dict(tap=(0.54, 0.6)),
        winner=2,
        reason="explicit_tap",
    ),
    dict(
        id="multi-hit-pool",
        title="An ambiguous tap cannot select an untapped center candidate",
        items=[
            bottle((10, 20, 150, 230)),
            bottle((100, 20, 124, 230)),
            bottle((130, 20, 230, 230)),
        ],
        interaction=dict(tap=(0.58, 0.6)),
        winner=0,
        reason="fallback_center_contains",
        mode="fallback",
        tap_ids=["d0", "d2"],
    ),
    dict(
        id="tiny-hand-distractor",
        title="A small contacted can cannot cancel a larger grip",
        items=[
            bottle((20, 20, 90, 230)),
            bottle((140, 20, 210, 230)),
            region("hand", (90, 80, 110, 190)),
            region("can", (110, 100, 120, 120)),
        ],
        winner=0,
        reason="unique_visible_hand_contact",
    ),
    dict(
        id="secondary-label-hole",
        title="An undetected secondary label survives a bottle-mask hole",
        items=[
            dict(bottle((70, 10, 170, 235)), holes=[(95, 30, 145, 60)]),
            region("wine label", (75, 100, 165, 200)),
        ],
        source_patches=[((95, 30, 145, 60), "#f4e7c9")],
        preserve_points=[(120, 45)],
        winner=0,
        reason="only_credible_subject",
        scope="subject_region",
    ),
    dict(
        id="label-context",
        title="Label-only evidence keeps the full context despite a distractor",
        items=[
            region("wine label", (60, 40, 180, 200)),
            region("packet", (190, 100, 235, 160)),
        ],
        winner=0,
        reason="dominant_foreground_subject",
        scope="context_frame",
    ),
    dict(
        id="unequal-two-grips",
        title="Small grip-support differences do not invent unique intent",
        items=[
            bottle((15, 20, 85, 230)),
            bottle((155, 20, 225, 230)),
            region("hand", (85, 80, 115, 190)),
            region("hand", (125, 80, 155, 165)),
        ],
        winner=0,
        reason="fallback_leftmost",
        mode="fallback",
    ),
]


REVIEW_SCENARIOS += [
    dict(
        id="box-around-hand",
        title="A background carton surrounding a hand cannot steal the held bottle",
        items=[
            bottle((110, 100, 130, 230)),
            dict(
                region("box", (90, 50, 150, 110)),
                holes=[(100, 60, 140, 100), (110, 100, 130, 110)],
            ),
            region("hand", (100, 60, 140, 100)),
        ],
        winner=0,
        reason="unique_visible_hand_contact",
    ),
    dict(
        id="body-grip-enclosure",
        title="A real bottle body grip remains valid when its box encloses the hand",
        items=[
            bottle((15, 20, 85, 230)),
            bottle((155, 20, 225, 230)),
            region("hand", (25, 80, 75, 150)),
        ],
        winner=0,
        reason="unique_visible_hand_contact",
    ),
    dict(
        id="different-hands-unequal",
        title="Different hands holding two bottles cannot manufacture a unique grip",
        items=[
            bottle((15, 20, 85, 230)),
            bottle((155, 20, 225, 230)),
            region("hand", (85, 80, 115, 190)),
            region("hand", (125, 130, 155, 160)),
        ],
        winner=0,
        reason="fallback_leftmost",
        mode="fallback",
    ),
    dict(
        id="two-hands-one-subject",
        title="Two hands may support the same physical bottle",
        items=[
            bottle((15, 20, 85, 230)),
            bottle((155, 20, 225, 230)),
            region("hand", (85, 80, 115, 190)),
            region("hand", (0, 80, 15, 190)),
        ],
        winner=0,
        reason="unique_visible_hand_contact",
    ),
    dict(
        id="unlabeled-strip-conflict",
        title="An unlabeled held strip cannot confidently override a much larger centered labeled bottle",
        items=[
            bottle((80, 10, 160, 230)),
            region("wine label", (90, 100, 150, 190)),
            bottle((5, 30, 75, 42)),
            region("hand", (5, 42, 75, 65)),
        ],
        winner=0,
        reason="fallback_center_contains",
        mode="fallback",
    ),
    dict(
        id="exterior-label-strip",
        title="Secondary label pixels touching the silhouette edge survive",
        items=[
            dict(bottle((70, 10, 170, 235)), holes=[(70, 30, 110, 60)]),
            region("wine label", (90, 100, 150, 190)),
        ],
        source_patches=[((70, 30, 110, 60), "#f4e7c9")],
        preserve_points=[(80, 45)],
        winner=0,
        reason="only_credible_subject",
        scope="subject_region",
    ),
    dict(
        id="label-gap-tap",
        title="A tap on white paper missing from the bottle mask resolves through unique label context",
        items=[
            dict(bottle((15, 20, 85, 230)), holes=[(15, 100, 85, 160)]),
            bottle((155, 20, 225, 230)),
            region("wine label", (20, 105, 80, 155)),
        ],
        interaction=dict(tap=(0.20, 0.50)),
        winner=0,
        reason="explicit_tap",
        tap_ids=["d0"],
    ),
    dict(
        id="three-foreground",
        title="Three bottles: off-center foreground beats two near-center backgrounds",
        items=[
            bottle((0, 0, 70, 240)),
            bottle((100, 65, 155, 215)),
            bottle((165, 65, 220, 215)),
        ],
        winner=0,
        reason="foreground_scale_and_lower_base",
    ),
    dict(
        id="three-weak-depth",
        title="Three similar bottles: uncertain depth uses center fallback",
        items=[
            bottle((5, 30, 65, 220)),
            bottle((90, 30, 150, 220)),
            bottle((175, 30, 235, 220)),
        ],
        winner=1,
        reason="fallback_center_contains",
        mode="fallback",
    ),
    dict(
        id="background-magnum",
        title="A larger background magnum is not proof of camera proximity",
        items=[
            bottle((5, 70, 65, 235)),
            bottle((80, 10, 160, 215)),
            bottle((180, 70, 230, 215)),
        ],
        winner=1,
        reason="fallback_center_contains",
        mode="fallback",
    ),
    dict(
        id="three-tap-background",
        title="An explicit background tap overrides foreground prominence",
        items=[
            bottle((0, 0, 70, 240)),
            bottle((100, 65, 155, 215)),
            bottle((165, 65, 220, 215)),
        ],
        interaction=dict(tap=(0.53, 0.50)),
        winner=1,
        reason="explicit_tap",
        tap_ids=["d1"],
    ),
    dict(
        id="held-carton-only",
        title="A held carton remains a valid package when there is no competing bottle",
        items=[region("box", (40, 20, 180, 230)), region("hand", (50, 80, 130, 140))],
        winner=0,
        reason="unique_visible_hand_contact",
    ),
]


REVIEW_SCENARIOS += [
    dict(
        id="orphan-label-beside-bottle",
        title="An off-center orphan cannot win passive dominance over a physical bottle",
        items=[bottle((150, 30, 190, 230)), region("wine label", (0, 50, 110, 190))],
        winner=0,
        reason="fallback_nearest_center",
        mode="fallback",
        scope="context_frame",
    ),
    dict(
        id="centered-label-closeup-with-bottle",
        title="A centered label close-up survives a small background bottle",
        items=[region("wine label", (40, 20, 200, 220)), bottle((205, 100, 235, 230))],
        winner=0,
        reason="dominant_foreground_subject",
        scope="context_frame",
    ),
    dict(
        id="tap-orphan-label",
        title="An explicit tap can select an off-center unowned label",
        items=[bottle((150, 30, 190, 230)), region("wine label", (0, 50, 110, 190))],
        interaction=dict(tap=(0.2, 0.5)),
        winner=1,
        reason="explicit_tap",
        scope="context_frame",
        tap_ids=["d1"],
    ),
    dict(
        id="dominant-label-price-conflict",
        title="A dominant real label also classified as price tag keeps full context",
        items=[
            region("wine label", (60, 40, 180, 200)),
            region("packet", (190, 100, 235, 160)),
            region("price tag", (60, 40, 180, 200)),
        ],
        winner=0,
        reason="fallback_center_contains",
        mode="fallback",
        scope="context_frame",
    ),
    dict(
        id="separate-shelf-levels",
        title="A larger bottle on a lower shelf is not proof of camera proximity",
        items=[
            bottle((20, 10, 50, 90)),
            bottle((190, 10, 220, 90)),
            bottle((100, 130, 140, 235)),
        ],
        winner=2,
        reason="fallback_nearest_center",
        mode="fallback",
    ),
    dict(
        id="truncated-background-peer",
        title="A truncated background silhouette cannot establish a foreground size ratio",
        items=[
            bottle((0, 0, 70, 240)),
            bottle((100, 0, 145, 150)),
            bottle((165, 65, 220, 215)),
        ],
        winner=1,
        reason="fallback_center_contains",
        mode="fallback",
    ),
    dict(
        id="bystander-hand-three",
        title="An ambiguous hand touching only background bottles cannot suppress a clear foreground",
        items=[
            bottle((0, 0, 70, 240)),
            bottle((100, 65, 155, 215)),
            bottle((165, 65, 220, 215)),
            region("hand", (150, 100, 170, 180)),
        ],
        winner=0,
        reason="foreground_scale_and_lower_base",
    ),
    dict(
        id="held-unlabelled-carton",
        title="Wine label presence cannot override stronger contact with an unlabelled held carton",
        items=[
            bottle((15, 20, 85, 230)),
            region("wine label", (20, 100, 80, 180)),
            region("box", (80, 65, 155, 170)),
            region("hand", (85, 80, 115, 190)),
        ],
        winner=2,
        reason="unique_visible_hand_contact",
    ),
]


REVIEW_SCENARIOS.append(
    dict(
        id="lying-foreground-three",
        title="A lying foreground bottle survives two upright bottles near center",
        items=[
            bottle((10, 180, 230, 230)),
            bottle((95, 60, 125, 140)),
            bottle((150, 50, 180, 130)),
        ],
        winner=0,
        reason="foreground_scale_and_lower_base",
    )
)


REVIEW_SCENARIOS.append(
    dict(
        id="unowned-label-logo-mask",
        title="A large unowned label extent is preserved when its mask collapses to a small logo",
        items=[
            bottle((180, 30, 230, 230)),
            region("wine label", (0, 0, 170, 240), mask_box=(0, 0, 20, 40)),
        ],
        source_patches=[((0, 0, 170, 240), "#f4e7c9")],
        preserve_points=[(100, 180)],
        winner=0,
        reason="fallback_nearest_center",
        mode="fallback",
        scope="context_frame",
    )
)


# Declared before the round-4 fixes; geometry controls, not extra photos.
REVIEW_SCENARIOS += [
    {
        "id": "weak-wrap-strong-grip",
        "title": "Weak incidental front wrap cannot steal a stronger grip",
        "items": [
            {
                "label": "wine bottle",
                "box": [15, 20, 85, 230],
                "mask_box": [15, 20, 85, 230],
                "score": 0.9,
            },
            {
                "label": "wine bottle",
                "box": [125, 90, 145, 125],
                "mask_box": [125, 90, 145, 125],
                "score": 0.9,
            },
            {
                "label": "hand",
                "box": [85, 80, 155, 190],
                "mask_box": [85, 80, 155, 190],
                "score": 0.9,
                "holes": [[100, 80, 155, 100], [100, 102, 155, 190]],
            },
        ],
        "winner": 0,
        "reason": "unique_visible_hand_contact",
    },
    {
        "id": "multiple-grips-unheld-foreground",
        "title": "Two confirmed grips block an unrelated unheld foreground bottle",
        "size": [640, 480],
        "items": [
            {
                "label": "wine bottle",
                "box": [100, 100, 160, 300],
                "mask_box": [100, 100, 160, 300],
                "score": 0.9,
            },
            {
                "label": "wine bottle",
                "box": [220, 100, 280, 300],
                "mask_box": [220, 100, 280, 300],
                "score": 0.9,
            },
            {
                "label": "wine bottle",
                "box": [400, 150, 520, 470],
                "mask_box": [400, 150, 520, 470],
                "score": 0.9,
            },
            {
                "label": "hand",
                "box": [160, 130, 180, 260],
                "mask_box": [160, 130, 180, 260],
                "score": 0.9,
            },
            {
                "label": "hand",
                "box": [280, 130, 300, 260],
                "mask_box": [280, 130, 300, 260],
                "score": 0.9,
            },
        ],
        "winner": 1,
        "reason": "fallback_nearest_center",
        "mode": "fallback",
    },
    {
        "id": "owner-and-uncertain-background",
        "title": "A confirmed grip plus another uncertain hand cannot promote an unheld "
        "bottle",
        "size": [640, 480],
        "items": [
            {
                "label": "wine bottle",
                "box": [100, 100, 160, 300],
                "mask_box": [100, 100, 160, 300],
                "score": 0.9,
            },
            {
                "label": "wine bottle",
                "box": [220, 100, 280, 300],
                "mask_box": [220, 100, 280, 300],
                "score": 0.9,
            },
            {
                "label": "wine bottle",
                "box": [300, 100, 360, 300],
                "mask_box": [300, 100, 360, 300],
                "score": 0.9,
            },
            {
                "label": "wine bottle",
                "box": [470, 150, 590, 470],
                "mask_box": [470, 150, 590, 470],
                "score": 0.9,
            },
            {
                "label": "hand",
                "box": [80, 140, 100, 260],
                "mask_box": [80, 140, 100, 260],
                "score": 0.9,
            },
            {
                "label": "hand",
                "box": [280, 140, 300, 260],
                "mask_box": [280, 140, 300, 260],
                "score": 0.9,
            },
        ],
        "winner": 2,
        "reason": "fallback_center_contains",
        "mode": "fallback",
    },
    {
        "id": "held-neck-dominant-paper",
        "title": "A held neck cannot discard an unowned complete label",
        "items": [
            {
                "label": "wine bottle",
                "box": [60, 10, 100, 100],
                "mask_box": [60, 10, 100, 100],
                "score": 0.9,
            },
            {
                "label": "wine label",
                "box": [10, 100, 160, 230],
                "mask_box": [10, 100, 160, 230],
                "score": 0.9,
            },
            {
                "label": "hand",
                "box": [100, 20, 125, 90],
                "mask_box": [100, 20, 125, 90],
                "score": 0.9,
            },
        ],
        "source_patches": [[[10, 100, 160, 230], "#f4e7c9"]],
        "preserve_points": [[80, 180]],
        "winner": 0,
        "reason": "unique_visible_hand_contact",
        "scope": "context_frame",
    },
    {
        "id": "held-neck-pending-logo",
        "title": "A held subject retains pending full paper even if its mask is only a logo",
        "items": [
            {
                "label": "wine bottle",
                "box": [180, 30, 230, 230],
                "mask_box": [180, 30, 230, 230],
                "score": 0.9,
            },
            {
                "label": "wine label",
                "box": [0, 0, 170, 240],
                "mask_box": [0, 0, 20, 40],
                "score": 0.9,
            },
            {
                "label": "hand",
                "box": [165, 70, 180, 190],
                "mask_box": [165, 70, 180, 190],
                "score": 0.9,
            },
        ],
        "source_patches": [[[0, 0, 170, 240], "#f4e7c9"]],
        "preserve_points": [[100, 180]],
        "winner": 0,
        "reason": "unique_visible_hand_contact",
        "scope": "context_frame",
    },
]


# Confidence policy v2: historical contact-only expectations remain explicit.
CONFIDENCE_CONTRACT_REVISION = "2026-10-19-positive-grip-and-panel"
CONTACT_ONLY_OVERRIDES = {
    "tiny-hand-distractor": {
        "winner": 3,
        "reason": "fallback_nearest_center",
        "mode": "fallback",
    },
    "box-around-hand": {
        "winner": 0,
        "reason": "fallback_center_contains",
        "mode": "fallback",
    },
    "two-hands-one-subject": {
        "winner": 0,
        "reason": "fallback_leftmost",
        "mode": "fallback",
    },
    "weak-wrap-strong-grip": {
        "winner": 1,
        "reason": "fallback_nearest_center",
        "mode": "fallback",
    },
    "held-neck-dominant-paper": {
        "winner": 1,
        "reason": "fallback_center_contains",
        "mode": "fallback",
    },
    "held-neck-pending-logo": {
        "winner": 0,
        "reason": "fallback_nearest_center",
        "mode": "fallback",
    },
}
for _spec in REVIEW_SCENARIOS:
    if _spec["id"] in CONTACT_ONLY_OVERRIDES:
        _spec["previous_contact_expectation"] = {
            key: _spec.get(key, "confident" if key == "mode" else None)
            for key in ("winner", "reason", "mode")
        }
        _spec.update(CONTACT_ONLY_OVERRIDES[_spec["id"]])
        _spec["confidence_contract_revision"] = CONFIDENCE_CONTRACT_REVISION
        _spec["title"] += " (contact alone is unconfirmed; use geometric fallback)"


# Declared positive-grip / panel controls, separate from photo intent GT.
REVIEW_SCENARIOS += [
    {
        "id": "point-contact-near-center-bottle",
        "title": "Unverified side contact cannot outrank a central bottle",
        "items": [
            {
                "label": "wine bottle",
                "box": (15, 20, 85, 230),
                "mask_box": (15, 20, 85, 230),
                "score": 0.9,
            },
            {
                "label": "wine bottle",
                "box": (105, 20, 155, 230),
                "mask_box": (105, 20, 155, 230),
                "score": 0.9,
            },
            {
                "label": "hand",
                "box": (85, 90, 92, 160),
                "mask_box": (85, 90, 92, 160),
                "score": 0.9,
            },
        ],
        "winner": 1,
        "reason": "fallback_center_contains",
        "mode": "fallback",
    },
    {
        "id": "opposed-background-midbody",
        "title": "Opposed background skin without front or terminal evidence is not a grip",
        "items": [
            {
                "label": "wine bottle",
                "box": (70, 20, 140, 230),
                "mask_box": (70, 20, 140, 230),
                "score": 0.9,
            },
            {
                "label": "wine bottle",
                "box": (180, 20, 230, 230),
                "mask_box": (180, 20, 230, 230),
                "score": 0.9,
            },
            {
                "label": "hand",
                "box": (50, 80, 160, 140),
                "mask_box": (50, 80, 160, 140),
                "score": 0.9,
                "holes": [(70, 80, 140, 140)],
            },
        ],
        "winner": 0,
        "reason": "fallback_center_contains",
        "mode": "fallback",
    },
    {
        "id": "enclosing-label-panel",
        "title": "A complete panel encloses bottle artwork; preserve the panel context",
        "items": [
            {
                "label": "wine label",
                "box": (40, 10, 200, 230),
                "mask_box": (40, 10, 200, 230),
                "score": 0.9,
            },
            {
                "label": "wine bottle",
                "box": (90, 45, 150, 190),
                "mask_box": (90, 45, 150, 190),
                "score": 0.9,
            },
            {
                "label": "wine label",
                "box": (100, 120, 140, 160),
                "mask_box": (100, 120, 140, 160),
                "score": 0.9,
            },
        ],
        "source_patches": [((40, 10, 200, 230), "#eedabb")],
        "preserve_points": [(55, 200)],
        "winner": 0,
        "reason": "fallback_center_contains",
        "mode": "fallback",
        "scope": "context_frame",
    },
]


def materialize(spec):
    size = spec.get("size", (240, 240))
    image = Image.new("RGB", size, "#e7e6dc")
    draw = ImageDraw.Draw(image)
    detections = []
    masks = []
    for index, item in enumerate(spec["items"]):
        mask = Image.new("L", size)
        x, y, X, Y = item["mask_box"]
        ImageDraw.Draw(mask).rectangle((x, y, X - 1, Y - 1), fill=255)
        for x1, y1, x2, y2 in item.get("holes", []):
            ImageDraw.Draw(mask).rectangle((x1, y1, x2 - 1, y2 - 1), fill=0)
        image.paste(("#3a6752", "#8c5b51")[index % 2], (0, 0), mask)
        draw.text((x + 3, y + 3), "d%d" % index, fill="white")
        output = BytesIO()
        mask.save(output, "PNG")
        detections.append(
            dict(
                label=item["label"],
                box=list(item["box"]),
                score=item["score"],
                mask_png_b64=base64.b64encode(output.getvalue()).decode(),
            )
        )
        masks.append(mask)
    for (x, y, X, Y), color in spec.get("source_patches", []):
        draw.rectangle((x, y, X - 1, Y - 1), fill=color)
    # Crosshair is explanatory only; it is not a supplied detection or an aim.
    x, y = size[0] // 2, size[1] // 2
    draw.line((x - 5, y, x + 5, y), fill="#eeaf36", width=1)
    draw.line((x, y - 5, x, y + 5), fill="#eeaf36", width=1)
    return image, detections, masks
