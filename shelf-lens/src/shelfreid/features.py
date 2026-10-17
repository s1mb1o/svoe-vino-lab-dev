"""Keypoints of a frame and the matching of two frames."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


LEARNED = ("aliked", "disk")   # learned keypoints matched by LightGlue (deep.py)


@dataclass(frozen=True)
class FeatureConfig:
    method: str = "sift"     # sift | orb | akaze | aliked | disk
    max_side: int = 1600     # the long side of the copy that the detector reads
    max_features: int = 4000
    ratio: float = 0.75      # the Lowe ratio test
    mutual: bool = True      # keep only mutual nearest neighbours
    rootsift: bool = False   # RootSIFT: L1 norm and square root of each SIFT descriptor


@dataclass(frozen=True)
class FrameFeatures:
    """The keypoints of one frame, in pixels of the full-resolution frame."""

    size: tuple[int, int]    # (width, height)
    points: np.ndarray       # (N, 2) float32
    descriptors: np.ndarray | None
    method: str


def _detector(cfg: FeatureConfig):
    if cfg.method == "sift":
        return cv2.SIFT_create(nfeatures=cfg.max_features)
    if cfg.method == "orb":
        return cv2.ORB_create(nfeatures=cfg.max_features)
    if cfg.method == "akaze":
        if not hasattr(cv2, "AKAZE_create"):
            raise ValueError("this OpenCV build has no AKAZE (OpenCV 5 moved it out)")
        return cv2.AKAZE_create()
    raise ValueError(f"unknown feature method {cfg.method!r}")


def extract(image: np.ndarray, cfg: FeatureConfig = FeatureConfig(),
            mask: np.ndarray | None = None) -> FrameFeatures:
    """Detect the keypoints of one BGR or gray frame. `mask` (uint8, frame size) MAY
    exclude regions, for example a hand."""
    height, width = image.shape[:2]
    if cfg.method in LEARNED:
        from . import deep

        points, descriptors = deep.extract(image, cfg.method, cfg.max_features, cfg.max_side)
        if mask is not None and len(points):
            x = np.clip(points[:, 0].astype(int), 0, width - 1)
            y = np.clip(points[:, 1].astype(int), 0, height - 1)
            keep = mask[y, x] > 0
            points, descriptors = points[keep], descriptors[keep]
        return FrameFeatures((width, height), points, descriptors, cfg.method)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    scale = min(1.0, cfg.max_side / max(width, height))
    if scale < 1.0:
        size = (round(width * scale), round(height * scale))
        gray = cv2.resize(gray, size, interpolation=cv2.INTER_AREA)
        if mask is not None:
            mask = cv2.resize(mask, size, interpolation=cv2.INTER_NEAREST)
    keypoints, descriptors = _detector(cfg).detectAndCompute(gray, mask)
    if len(keypoints) > cfg.max_features:
        keep = np.argsort([-kp.response for kp in keypoints])[:cfg.max_features]
        keypoints = [keypoints[i] for i in keep]
        descriptors = descriptors[keep]
    if cfg.rootsift and descriptors is not None and descriptors.dtype == np.float32:
        descriptors = np.sqrt(descriptors / (descriptors.sum(1, keepdims=True) + 1e-7))
    points = np.array([kp.pt for kp in keypoints], np.float32).reshape(-1, 2) / scale
    return FrameFeatures((width, height), points, descriptors, cfg.method)


def match(a: FrameFeatures, b: FrameFeatures,
          cfg: FeatureConfig = FeatureConfig()) -> tuple[np.ndarray, np.ndarray]:
    """Return the matched points (points of A, points of B), row by row.

    The ratio test drops a point whose two best candidates are alike. On a shelf this
    removes most matches between repeated labels of one wine."""
    empty = np.empty((0, 2), np.float32)
    if a.descriptors is None or b.descriptors is None or len(a.points) < 2 or len(b.points) < 2:
        return empty, empty
    if a.method in LEARNED:
        from . import deep

        index_a, index_b = deep.match(a.points, a.descriptors, a.size, b.points, b.descriptors,
                                      b.size, a.method, cfg.max_features)
        return a.points[index_a], b.points[index_b]
    norm = cv2.NORM_HAMMING if a.descriptors.dtype == np.uint8 else cv2.NORM_L2
    matcher = cv2.BFMatcher(norm)
    pairs = {}
    for candidates in matcher.knnMatch(b.descriptors, a.descriptors, k=2):
        if len(candidates) == 2 and candidates[0].distance < cfg.ratio * candidates[1].distance:
            pairs[candidates[0].queryIdx] = candidates[0].trainIdx
    if cfg.mutual and pairs:
        back = {m.queryIdx: m.trainIdx for m in matcher.match(a.descriptors, b.descriptors)}
        pairs = {ib: ia for ib, ia in pairs.items() if back.get(ia) == ib}
    if not pairs:
        return empty, empty
    index_b = np.fromiter(pairs.keys(), int, len(pairs))
    index_a = np.fromiter(pairs.values(), int, len(pairs))
    return a.points[index_a], b.points[index_b]
