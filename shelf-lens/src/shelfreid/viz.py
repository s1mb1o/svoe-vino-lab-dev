"""Pictures of a registration and of the decisions of a pair."""

from __future__ import annotations

import cv2
import numpy as np

from .associate import anchor
from .homography import Registration, corners, project
from .pair import PairResult
from .types import Detection

COLORS = {"seen": (60, 190, 60), "new": (50, 50, 235), "new_in_overlap": (0, 170, 255),
          "unregistered": (160, 160, 160)}
FRAME = (255, 220, 0)
GAP = 12


def _side_by_side(image_a, image_b, height):
    scale_a, scale_b = height / image_a.shape[0], height / image_b.shape[0]
    a = cv2.resize(image_a, (round(image_a.shape[1] * scale_a), height))
    b = cv2.resize(image_b, (round(image_b.shape[1] * scale_b), height))
    canvas = np.full((height + 40, a.shape[1] + GAP + b.shape[1], 3), 255, np.uint8)
    canvas[40:, :a.shape[1]] = a
    canvas[40:, a.shape[1] + GAP:] = b
    def to_a(x, y):
        return int(x * scale_a), int(y * scale_a) + 40
    def to_b(x, y):
        return int(x * scale_b) + a.shape[1] + GAP, int(y * scale_b) + 40
    return canvas, to_a, to_b


def _frame_outline(canvas, registration: Registration, size_b, to_a):
    if registration.H is None:
        return
    quad = project(registration.H, corners(size_b))
    points = np.array([to_a(x, y) for x, y in quad], np.int32)
    cv2.polylines(canvas, [points], True, FRAME, 3, cv2.LINE_AA)


def _header(canvas, text):
    cv2.putText(canvas, text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (20, 20, 20), 2,
                cv2.LINE_AA)


def draw_registration(image_a, image_b, registration: Registration, points_a, points_b,
                      height: int = 900, lines: int = 80) -> np.ndarray:
    """Frame B outlined in frame A, with a sample of the inlier matches."""
    canvas, to_a, to_b = _side_by_side(image_a, image_b, height)
    size_b = (image_b.shape[1], image_b.shape[0])
    _frame_outline(canvas, registration, size_b, to_a)
    if registration.inlier_mask is not None and len(points_a):
        inliers = np.flatnonzero(registration.inlier_mask)
        rng = np.random.default_rng(0)
        for i in rng.choice(inliers, min(lines, len(inliers)), replace=False):
            cv2.line(canvas, to_a(*points_a[i]), to_b(*points_b[i]), (0, 200, 0), 1, cv2.LINE_AA)
    _header(canvas, f"{registration.reason}: inliers {registration.inliers}/{registration.matches},"
                    f" B covers {registration.overlap_a:.0%} of A,"
                    f" inliers span {registration.coverage:.0%} of the overlap")
    return canvas


def draw_pair(image_a, image_b, dets_a: list[Detection], dets_b: list[Detection],
              result: PairResult, height: int = 900, anchor_y: float = 0.6) -> np.ndarray:
    """Bottles of A in grey; bottles of B coloured by decision, with a line to their match."""
    canvas, to_a, to_b = _side_by_side(image_a, image_b, height)
    _frame_outline(canvas, result.registration, (image_b.shape[1], image_b.shape[0]), to_a)
    for j, det in enumerate(dets_a):
        cv2.rectangle(canvas, to_a(*det.box[:2]), to_a(*det.box[2:]), (150, 150, 150), 2)
        cv2.putText(canvas, str(j), to_a(det.box[0] + 3, det.box[1] + 3), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (150, 150, 150), 1, cv2.LINE_AA)
    for decision in result.decisions:
        det = dets_b[decision.index]
        color = COLORS[decision.status]
        cv2.rectangle(canvas, to_b(*det.box[:2]), to_b(*det.box[2:]), color, 3)
        if decision.match is not None:
            start = to_b(*anchor(det.box, anchor_y))
            end = to_a(*anchor(dets_a[decision.match].box, anchor_y))
            cv2.line(canvas, start, end, color, 2, cv2.LINE_AA)
    counts = ", ".join(f"{s} {result.count(s)}" for s in COLORS if result.count(s))
    _header(canvas, f"{result.registration.reason}, inliers {result.registration.inliers} | {counts}")
    return canvas
