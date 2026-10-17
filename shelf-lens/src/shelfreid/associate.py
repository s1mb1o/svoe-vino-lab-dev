"""Compare the bottles of frame B with the bottles of frame A by position.

Each bottle of B is mapped into frame A with the homography. The anchor of a bottle is
a point near the label centre, which lies close to the shelf plane; the neck stands out
of the plane and moves with parallax. Both frames are cut to the region they share, so a
bottle cut by the edge of one frame gets the same cut in the other frame. The Hungarian
method gives a one-to-one assignment: a greedy nearest neighbour can give one bottle of A
to two identical neighbours of B.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.optimize import linear_sum_assignment

from .homography import corners, project
from .types import Box, Decision, Detection

_FAR = 1e6


@dataclass(frozen=True)
class AssociationConfig:
    # column: the distance of the box centres across the shelf, and the boxes MUST share
    #   `min_vertical_overlap` of the taller height (one shelf row, and alike in height:
    #   the neck of a bottle behind lies inside the box of the bottle in front and MUST
    #   NOT take its track). A box cut by the frame edge is cut alike in both, because
    #   both are clipped to the shared region first.
    # anchor: the distance of the anchor points (`anchor_y` of the height from the top).
    metric: str = "column"
    anchor_y: float = 0.6
    min_vertical_overlap: float = 0.5
    # The largest distance of one bottle, in bottle widths. Neighbours stand at least one
    # width apart, so 0.5 keeps them apart.
    max_distance: float = 0.5


def anchor(box: Box, anchor_y: float) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2, y1 + anchor_y * (y2 - y1)


def bbox_of(points: np.ndarray) -> Box:
    return (float(points[:, 0].min()), float(points[:, 1].min()),
            float(points[:, 0].max()), float(points[:, 1].max()))


def clip(box: Box, region: Box) -> Box | None:
    x1, y1 = max(box[0], region[0]), max(box[1], region[1])
    x2, y2 = min(box[2], region[2]), min(box[3], region[3])
    return (x1, y1, x2, y2) if x2 > x1 and y2 > y1 else None


def box_corners(box: Box) -> np.ndarray:
    x1, y1, x2, y2 = box
    return np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], np.float64)


def distance_matrix(boxes_b: list[Box | None], boxes_a: list[Box | None],
                    widths_b: list[float], widths_a: list[float],
                    cfg: AssociationConfig) -> np.ndarray:
    """The distances of boxes in one frame, in bottle widths; inf where the boxes are not
    comparable. A None box is not compared. The widths are the uncut bottle widths: a box
    cut by a frame edge understates the width."""
    distance = np.full((len(boxes_b), len(boxes_a)), np.inf)
    for i, box_b in enumerate(boxes_b):
        if box_b is None:
            continue
        xb, yb = anchor(box_b, cfg.anchor_y)
        for j, box_a in enumerate(boxes_a):
            if box_a is None:
                continue
            xa, ya = anchor(box_a, cfg.anchor_y)
            width = max(widths_b[i], widths_a[j], 1e-6)
            if cfg.metric == "column":
                common = min(box_a[3], box_b[3]) - max(box_a[1], box_b[1])
                taller = max(box_a[3] - box_a[1], box_b[3] - box_b[1])
                if common < cfg.min_vertical_overlap * taller:
                    continue
                distance[i, j] = abs(xb - xa) / width
            else:
                distance[i, j] = math.hypot(xb - xa, yb - ya) / width
    return distance


def hungarian(distance: np.ndarray, max_distance: float) -> dict[int, int]:
    """The one-to-one assignment of rows to columns with the least total distance; only
    pairs closer than `max_distance` count."""
    matched: dict[int, int] = {}
    if distance.size:
        cost = np.where(distance <= max_distance, distance, _FAR)
        for i, j in zip(*linear_sum_assignment(cost)):
            if cost[i, j] < _FAR:
                matched[int(i)] = int(j)
    return matched


def associate(dets_a: list[Detection], dets_b: list[Detection], H: np.ndarray,
              size_a: tuple[int, int], size_b: tuple[int, int],
              cfg: AssociationConfig = AssociationConfig()) -> list[Decision]:
    """Return one decision for each bottle of frame B. H maps B to A."""
    frame_a: Box = (0.0, 0.0, float(size_a[0]), float(size_a[1]))
    shared = clip(bbox_of(project(H, corners(size_b))), frame_a)
    if shared is None:
        return [Decision(i, "new") for i in range(len(dets_b))]

    mapped = [bbox_of(project(H, box_corners(d.box))) for d in dets_b]
    inside = []
    for box in mapped:
        x, y = anchor(box, cfg.anchor_y)
        inside.append(frame_a[0] <= x < frame_a[2] and frame_a[1] <= y < frame_a[3])
    # A bottle of B is compared when any part of it lies in the shared region: frame A
    # MAY hold only a sliver of it, and then its anchor lies outside frame A.
    distance = distance_matrix([clip(box, shared) for box in mapped],
                               [clip(d.box, shared) for d in dets_a],
                               [box[2] - box[0] for box in mapped], [d.width for d in dets_a],
                               cfg)
    matched = hungarian(distance, cfg.max_distance)

    decisions = []
    for i in range(len(dets_b)):
        if i in matched:
            j = matched[i]
            decisions.append(Decision(i, "seen", j, float(distance[i, j])))
        elif inside[i]:
            decisions.append(Decision(i, "new_in_overlap"))
        else:
            decisions.append(Decision(i, "new"))
    return decisions
