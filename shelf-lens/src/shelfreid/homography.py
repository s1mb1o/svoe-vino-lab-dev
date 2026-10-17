"""The homography that joins frame B to frame A, and its checks.

The shelf front is close to a plane, so two photos of it are related by a homography
p_A ~ H p_B. MAGSAC drops the wrong matches; the checks drop a homography that no
real camera motion gives.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import cv2
import numpy as np


@dataclass(frozen=True)
class HomographyConfig:
    # The inlier threshold, as a share of the diagonal of frame A. Loose on purpose:
    # bottles stand out of the shelf plane, so a close photo has parallax.
    ransac_threshold: float = 0.005
    min_inliers: int = 25
    min_inlier_ratio: float = 0.15
    max_scale: float = 4.0       # the largest zoom between the two frames
    max_w_ratio: float = 3.0     # the largest perspective stretch over frame B
    # The least share of the overlap (in frame B) that the convex hull of the inliers
    # covers. A repeated banner or one price tag can carry a wrong homography with all
    # its inliers in a thin strip: 0.03 on such a pair, 0.46-0.76 on right real pairs.
    min_coverage: float = 0.10


@dataclass(frozen=True)
class Registration:
    ok: bool
    reason: str
    H: np.ndarray | None         # maps pixels of frame B to pixels of frame A
    matches: int
    inliers: int
    inlier_mask: np.ndarray | None = None
    overlap_a: float = 0.0       # the share of frame A that frame B covers
    overlap_b: float = 0.0       # the share of frame B that lies inside frame A
    coverage: float = 0.0        # the share of the overlap that the inliers span


def corners(size: tuple[float, float]) -> np.ndarray:
    width, height = size
    return np.array([[0, 0], [width, 0], [width, height], [0, height]], np.float64)


def project(H: np.ndarray, points) -> np.ndarray:
    """Map (N, 2) points with the homography H."""
    pts = np.asarray(points, np.float64).reshape(-1, 2)
    mapped = np.c_[pts, np.ones(len(pts))] @ H.T
    return mapped[:, :2] / mapped[:, 2:3]


def check(H: np.ndarray, size_b: tuple[int, int], cfg: HomographyConfig) -> str | None:
    """Return why H is not a plausible camera motion, or None."""
    H = H / H[2, 2]
    quad = corners(size_b)
    w = np.c_[quad, np.ones(4)] @ H[2]
    if np.any(w <= 0):
        return "frame B crosses the horizon"
    if w.max() / w.min() > cfg.max_w_ratio:
        return f"perspective stretch {w.max() / w.min():.1f}"
    det = float(np.linalg.det(H[:2, :2]))
    if det <= 0:
        return "mirrored"
    scale = math.sqrt(det)
    if not 1 / cfg.max_scale <= scale <= cfg.max_scale:
        return f"scale {scale:.2f}"
    if not cv2.isContourConvex(project(H, quad).astype(np.float32)):
        return "frame B is not convex in frame A"
    return None


def overlaps(H: np.ndarray, size_a, size_b) -> tuple[float, float]:
    """Return (the share of frame A covered by frame B, the share of frame B in frame A)."""
    quad = project(H, corners(size_b)).astype(np.float32)
    area, _ = cv2.intersectConvexConvex(quad, corners(size_a).astype(np.float32))
    quad_area = abs(cv2.contourArea(quad))
    return area / (size_a[0] * size_a[1]), (area / quad_area if quad_area else 0.0)


def coverage(H: np.ndarray, inliers_b: np.ndarray, size_a, size_b) -> float:
    """Return the share of the overlap, in frame B, that the convex hull of the inlier
    points of frame B covers."""
    if len(inliers_b) < 3:
        return 0.0
    a_in_b = project(np.linalg.inv(H), corners(size_a)).astype(np.float32)
    area, _ = cv2.intersectConvexConvex(corners(size_b).astype(np.float32), a_in_b)
    if area <= 0:
        return 0.0
    hull = cv2.convexHull(np.asarray(inliers_b, np.float32))
    return min(1.0, cv2.contourArea(hull) / area)


def estimate(points_a: np.ndarray, points_b: np.ndarray, size_a: tuple[int, int],
             size_b: tuple[int, int], cfg: HomographyConfig = HomographyConfig()) -> Registration:
    """Estimate and check the homography B -> A from matched points."""
    count = len(points_a)
    if count < max(4, cfg.min_inliers):
        return Registration(False, f"{count} matches", None, count, 0)
    threshold = cfg.ransac_threshold * math.hypot(*size_a)
    H, mask = cv2.findHomography(points_b, points_a, cv2.USAC_MAGSAC, threshold,
                                 maxIters=10000, confidence=0.999)
    if H is None:
        return Registration(False, "no homography", None, count, 0)
    mask = mask.ravel().astype(bool)
    inliers = int(mask.sum())
    H = H / H[2, 2]
    reason = None
    if inliers < cfg.min_inliers:
        reason = f"{inliers} inliers"
    elif inliers < cfg.min_inlier_ratio * count:
        reason = f"inlier ratio {inliers / count:.2f}"
    else:
        reason = check(H, size_b, cfg)
    overlap_a = overlap_b = spread = 0.0
    if reason is None:
        overlap_a, overlap_b = overlaps(H, size_a, size_b)
        if overlap_a == 0.0:
            reason = "no overlap"
    if reason is None:
        spread = coverage(H, points_b[mask], size_a, size_b)
        if spread < cfg.min_coverage:
            reason = f"inliers cover {spread:.0%} of the overlap"
    return Registration(reason is None, reason or "ok", H, count, inliers, mask,
                        overlap_a, overlap_b, spread)
