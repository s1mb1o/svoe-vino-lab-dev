"""Visible finger direction and display-panel evidence for subject selection."""

from collections import deque

import numpy as np
from PIL import Image, ImageFilter


def _components(mask):
    remaining = mask.copy()
    height, width = remaining.shape
    while remaining.any():
        y, x = np.argwhere(remaining)[0]
        queue = deque([(int(y), int(x))])
        remaining[y, x] = False
        points = []
        while queue:
            cy, cx = queue.popleft()
            points.append((cx, cy))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < height and 0 <= nx < width and remaining[ny, nx]:
                        remaining[ny, nx] = False
                        queue.append((ny, nx))
        if len(points) >= 6:
            yield np.asarray(points, dtype=float)


def _pointing_at_scale(hand, candidates, size, kernel):
    """Find a narrow finger extending beyond the broad palm toward one bottle.

    A hand rectangle, mere adjacency, or the principal axis of a forearm is not
    a pointing gesture. Morphological opening removes narrow extensions; only
    a coherent elongated residual with a distal endpoint away from the palm
    can cast a short ray toward a visible candidate mask.
    """
    skin = hand["grid"]
    y, x = np.nonzero(skin)
    if len(x) < 24:
        return []
    image = Image.fromarray(skin.astype("uint8") * 255)
    palm = (
        np.asarray(
            image.filter(ImageFilter.MinFilter(kernel)).filter(
                ImageFilter.MaxFilter(kernel)
            )
        )
        > 0
    )
    if palm.sum() < skin.sum() * 0.35:
        return []
    py, px = np.nonzero(palm)
    center = np.array([float(px.mean()), float(py.mean())])
    height, width = skin.shape
    scale = np.array([size[0] / width, size[1] / height])
    findings = []
    for points in _components(skin & ~palm):
        centered = points - points.mean(axis=0)
        values, vectors = np.linalg.eigh(centered.T @ centered / len(points))
        if values[-1] < max(1.0, values[0]) * 5:
            continue
        axis = vectors[:, -1]
        along = points @ axis
        length = float(np.ptp(along))
        across = float(np.ptp(points @ np.array([-axis[1], axis[0]])))
        if length < kernel * 1.2 or length < max(2.5, across * 2.5):
            continue
        ends = [
            points[along <= along.min() + 1].mean(axis=0),
            points[along >= along.max() - 1].mean(axis=0),
        ]
        tip = max(ends, key=lambda p: float(np.linalg.norm(p - center)))
        base = min(ends, key=lambda p: float(np.linalg.norm(p - center)))
        if min(tip[0], tip[1], width - 1 - tip[0], height - 1 - tip[1]) < 2:
            continue
        direction = (tip - base) * scale
        norm = float(np.linalg.norm(direction))
        if norm < 1:
            continue
        direction /= norm
        # The distal extension must continue outward rather than run around a palm edge.
        radial = (tip - center) * scale
        if float(np.dot(radial, direction)) < float(np.linalg.norm(radial)) * 0.70:
            continue
        hits = []
        for candidate in candidates:
            if candidate["label"] not in ("wine bottle", "bottle"):
                continue
            # A finger can align with a tiny shelf fragment behind the gesture.
            # Such a region does not resolve the gesture at the hand's scale.
            if candidate["grid"].sum() < skin.sum() * 0.10:
                continue
            cy, cx = np.nonzero(candidate["grid"])
            pixels = (np.column_stack((cx, cy)) - tip) * scale
            forward = pixels @ direction
            lateral = np.abs(pixels @ np.array([-direction[1], direction[0]]))
            corridor = max(2 * max(scale), across * max(scale) * 0.65)
            reach = max(size) * 0.18
            # A bottle crossed by the finger is behind its distal endpoint,
            # not the subject of the outward ray.
            valid = (forward >= 0) & (forward <= reach) & (lateral <= corridor)
            if valid.any():
                distance = max(0.0, float(forward[valid].min()))
                hits.append((distance, candidate["source_index"], candidate))
        if not hits:
            continue
        hits.sort(key=lambda item: item[:2])
        # A hand projected along a neck/base is not a side-directed index cue.
        # A detached ray can still point toward an end from a visible gap.
        chosen = hits[0][2]
        by, bx = np.nonzero(chosen["grid"])
        body_points = np.column_stack((bx, by)) * scale
        centered_body = body_points - body_points.mean(axis=0)
        _, body_vectors = np.linalg.eigh(centered_body.T @ centered_body)
        if (
            hits[0][0] <= max(scale) * 2
            and abs(float(body_vectors[:, -1] @ direction)) > 0.85
        ):
            continue
        if len(hits) > 1 and hits[1][0] - hits[0][0] < max(scale) * 3:
            continue
        findings.append(
            {
                "candidate_id": hits[0][2]["id"],
                "hand_id": hand["id"],
                "finger_tip": ((tip + 0.5) * scale).tolist(),
                "direction": direction.tolist(),
                "distance_px": round(hits[0][0], 3),
                "extension_length_px": round(norm, 3),
            }
        )
    return findings


def pointing_evidence(hand, candidates, size):
    """Use several palm widths, retaining the first unambiguous visible finger.

    Finger thickness varies with perspective. The broad palm must survive each
    opening; an edge-touching arm endpoint still cannot become a fingertip.
    """
    y, x = np.nonzero(hand["grid"])
    if len(x) < 24:
        return []
    short = min(int(np.ptp(x)) + 1, int(np.ptp(y)) + 1)
    base = max(5, min(19, int(round(short * 0.22)) | 1))
    kernels = sorted({base, min(31, (round(base * 1.5) | 1)), min(39, (base * 2 + 1))})
    for kernel in kernels:
        found = _pointing_at_scale(hand, candidates, size, kernel)
        if found:
            return found
    return []


def reject_display_panels(packages, labels, hands, rejected):
    """Prefer an independent bottle over an unattended panel and its bottle art.

    Require a substantial nested bottle with visible-mask overlap, a broad panel,
    and a separate substantial bottle outside that panel. A box rectangle alone
    never establishes depiction; an occluding physical bottle leaves a mask hole.
    Held packaging and scenes without a separate bottle retain their old policy.
    """
    excluded = set()
    excluded_paper = set()
    bottles = [p for p in packages if p["label"] in ("wine bottle", "bottle")]
    for panel in packages:
        if panel["label"] not in ("box", "packet"):
            continue
        x1, y1, x2, y2 = panel["box"]
        width, height = x2 - x1, y2 - y1
        if not 0.28 <= width / max(1, height) <= 2.5:
            continue
        # Strong hand proximity makes unattended-display interpretation unsafe.
        if any(
            (panel["grid"] & hand["grid"]).sum() / max(1, hand["grid"].sum()) >= 0.05
            for hand in hands
        ):
            continue
        nested = []
        outside = []
        for bottle in bottles:
            overlap = float((bottle["grid"] & panel["grid"]).sum()) / max(
                1, bottle["grid"].sum()
            )
            a, b, c, d = bottle["box"]
            bbox_share = (
                max(0, min(c, x2) - max(a, x1))
                * max(0, min(d, y2) - max(b, y1))
                / max(1, (c - a) * (d - b))
            )
            if (
                overlap >= 0.50
                and bbox_share >= 0.95
                and bottle["area"] <= panel["area"] * 0.80
            ):
                nested.append(bottle)
            elif overlap <= 0.05 and bottle["area"] >= panel["area"] * 0.10:
                outside.append(bottle)
        if not nested or not outside:
            continue
        excluded.add(panel["id"])
        rejected.append(
            {"id": panel["id"], "reason": "display_panel_beside_physical_bottle"}
        )
        for bottle in nested:
            excluded.add(bottle["id"])
            rejected.append(
                {"id": bottle["id"], "reason": "bottle_depiction_in_display_panel"}
            )
        for label in labels:
            share = (label["grid"] & panel["grid"]).sum() / max(1, label["grid"].sum())
            if share >= 0.50:
                excluded_paper.add(label["id"])
                rejected.append(
                    {"id": label["id"], "reason": "artwork_label_in_display_panel"}
                )
    return (
        [p for p in packages if p["id"] not in excluded],
        [p for p in labels if p["id"] not in excluded_paper],
    )
