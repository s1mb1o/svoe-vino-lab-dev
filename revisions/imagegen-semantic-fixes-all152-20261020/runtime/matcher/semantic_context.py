"""Image-only context masks; no targets, identities or crop scores are consumed."""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

CONTEXT_NOUNS = (
    "poster",
    "screen",
    "mirror",
    "bottle held in hand",
    "transparent wrapping",
    "empty gift bag",
)


def _share(first, second):
    return float((first & second).sum()) / max(1, int(first.sum()))


def _iou(first, second):
    return float((first & second).sum()) / max(1, int((first | second).sum()))


def _rectangle_share(first, second):
    a, b, c, d = first
    x, y, X, Y = second
    return (
        max(0, min(c, X) - max(a, x))
        * max(0, min(d, Y) - max(b, y))
        / max(1, (c - a) * (d - b))
    )


def _frame_interior(grid):
    """Include display contents omitted as holes by a visible-frame mask."""
    im = Image.fromarray(grid.astype("uint8") * 255)
    padded = Image.new("L", (im.width + 2, im.height + 2))
    padded.paste(im, (1, 1))
    ImageDraw.floodfill(padded, (0, 0), 128)
    return grid | (np.asarray(padded)[1:-1, 1:-1] == 0)


def contextual_packages(packages, labels, contexts, hands, rejected):
    """Separate display imagery and transparent wrapper aliases from bottles.

    A framed display can have a hole where its depicted bottle was segmented.
    Enclosed depictions require an independent physical bottle outside the
    frame and no visible hand contact with the enclosed object.
    Held-bottle text detections only supply supporting evidence: they never
    establish a grip without independently measured hand/body contact.
    """
    excluded = set()
    paper_excluded = set()
    for package in packages:
        package["held_context_support"] = max(
            (
                _iou(package["grid"], c["grid"])
                for c in contexts
                if c["label"] == "bottle held in hand" and c["confidence"] >= 0.6
            ),
            default=0.0,
        )
        package["wrapping_context_support"] = max(
            (
                _share(package["grid"], c["grid"])
                for c in contexts
                if c["label"] == "transparent wrapping" and c["confidence"] >= 0.65
            ),
            default=0.0,
        )
    for context in contexts:
        if (
            context["label"] not in ("poster", "screen", "mirror")
            or context["confidence"] < 0.6
        ):
            continue
        if context["grid"].mean() < 0.015:
            continue
        inside = _frame_interior(context["grid"])
        removed = []
        for package in packages:
            touching = any(
                _share(
                    package["grid"],
                    np.asarray(
                        Image.fromarray(h["grid"].astype("uint8") * 255).filter(
                            ImageFilter.MaxFilter(5)
                        )
                    )
                    > 0,
                )
                >= 0.01
                for h in hands
            )
            outside = any(
                p is not package
                and p["label"] in ("wine bottle", "bottle")
                and p["area"] >= package["area"] * 0.1
                and _rectangle_share(p["box"], context["box"]) < 0.1
                for p in packages
            )
            enclosed = (
                outside
                and not touching
                and (
                    _rectangle_share(package["box"], context["box"]) >= 0.95
                    or _share(package["grid"], inside) >= 0.95
                )
                and package["area"] < context["area"] * 0.85
            )
            if (
                _share(package["grid"], context["grid"]) >= 0.85 and not touching
            ) or enclosed:
                excluded.add(package["id"])
                removed.append(package)
                rejected.append(
                    dict(
                        id=package["id"],
                        reason="depiction_in_" + context["label"],
                        context_id=context["id"],
                    )
                )
        for paper in labels:
            if _share(paper["grid"], context["grid"]) >= 0.85 or any(
                _share(paper["grid"], p["grid"]) >= 0.65 for p in removed
            ):
                paper_excluded.add(paper["id"])
                rejected.append(
                    dict(
                        id=paper["id"],
                        reason="paper_in_" + context["label"],
                        context_id=context["id"],
                    )
                )
    packages = [p for p in packages if p["id"] not in excluded]
    bottles = [p for p in packages if p["label"] in ("wine bottle", "bottle")]
    for container in packages:
        if container["label"] not in ("box", "packet"):
            continue
        contents = [
            b
            for b in bottles
            if b["area"] < container["area"] * 0.95
            and (
                (
                    container["wrapping_context_support"] >= 0.6
                    and _share(b["grid"], container["grid"]) >= 0.65
                )
                or (
                    _rectangle_share(b["box"], container["box"]) >= 0.95
                    and _share(b["grid"], container["grid"]) <= 0.2
                    and b["area"] >= container["area"] * 0.15
                )
            )
        ]
        if len(contents) == 1:
            container["transparent_container"] = True
            contents[0]["carrier"] = container
            excluded.add(container["id"])
            rejected.append(
                dict(
                    id=container["id"],
                    reason="visible_container_of_physical_bottle",
                    bottle_id=contents[0]["id"],
                )
            )
    return (
        [p for p in packages if p["id"] not in excluded],
        [p for p in labels if p["id"] not in paper_excluded],
    )


def substantial_bottle(bottles, size):
    """A sole substantial bottle is distinct from tiny shelf/background regions.

    This supplies a framing decision, not an alternative geometric fallback.
    Comparable bottles, an unlabeled fragment and tiny all-scene detections do
    not qualify. Hand/interaction evidence retains its earlier priority.
    """
    if not bottles:
        return None
    first = max(bottles, key=lambda p: p["area"])
    width, height = first["box"][2] - first["box"][0], first["box"][3] - first["box"][1]
    if (
        first["area"] < size[0] * size[1] * 0.015
        or max(width, height) < max(size) * 0.25
        or not first["labels"]
    ):
        return None
    others = [p for p in bottles if p is not first]
    if any(
        p["area"] > first["area"] * 0.12
        or max(p["box"][2] - p["box"][0], p["box"][3] - p["box"][1])
        > max(width, height) * 0.45
        for p in others
    ):
        return None
    return first


def edge_label_context(selected, size):
    """A label-dominated, doubly clipped body needs its original photo context."""
    if selected["label"] not in ("wine bottle", "bottle") or not selected["labels"]:
        return False
    x, y, X, Y = selected["box"]
    labels = selected["labels"]
    a = min(p["box"][0] for p in labels)
    b = min(p["box"][1] for p in labels)
    c = max(p["box"][2] for p in labels)
    d = max(p["box"][3] for p in labels)
    dominance = max(
        (p["box"][2] - p["box"][0]) * (p["box"][3] - p["box"][1]) for p in labels
    ) / max(1, (X - x) * (Y - y))
    return dominance >= 0.45 and (
        (y <= 0 and Y >= size[1] and d - b >= size[1] * 0.6 and c - a >= size[0] * 0.3)
        or (
            x <= 0
            and X >= size[0]
            and c - a >= size[0] * 0.6
            and d - b >= size[1] * 0.3
        )
    )
