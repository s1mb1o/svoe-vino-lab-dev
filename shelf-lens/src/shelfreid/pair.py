"""Two frames: which bottles of frame B were already in frame A."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

import numpy as np

from .associate import AssociationConfig, associate
from .detect import boxes_mask
from .features import FeatureConfig, FrameFeatures, extract, match
from .homography import HomographyConfig, Registration, estimate
from .types import Decision, Detection


@dataclass(frozen=True)
class PairConfig:
    features: FeatureConfig = field(default_factory=FeatureConfig)
    homography: HomographyConfig = field(default_factory=HomographyConfig)
    association: AssociationConfig = field(default_factory=AssociationConfig)
    # Keypoints only inside the bottle boxes: the homography of the bottle plane. A close
    # shot has parallax between the bottles, the shelf edge, and the far ceiling; a
    # homography of all keypoints MAY follow the wrong one (docs/design.md).
    mask_bottles: bool = False


# DISK keypoints inside the bottle boxes, for close shots; needs `--extra deep`.
ROBUST = PairConfig(features=FeatureConfig(method="disk", max_features=4096, max_side=1024),
                    mask_bottles=True)


@dataclass
class PairResult:
    registration: Registration
    decisions: list[Decision]
    points_a: np.ndarray          # the matched keypoints, for drawing
    points_b: np.ndarray
    timings_ms: dict[str, float]

    def count(self, status: str) -> int:
        return sum(d.status == status for d in self.decisions)


def _features(frame, cfg: FeatureConfig) -> FrameFeatures:
    return frame if isinstance(frame, FrameFeatures) else extract(frame, cfg)


def register(frame_a, frame_b, cfg: PairConfig = PairConfig()):
    """Return (registration, points of A, points of B, timings, size of A, size of B). A
    frame is a BGR image or the FrameFeatures of one, so a keyframe is described once."""
    timings = {}
    started = perf_counter()
    features_a, features_b = _features(frame_a, cfg.features), _features(frame_b, cfg.features)
    timings["features"] = (perf_counter() - started) * 1000
    started = perf_counter()
    points_a, points_b = match(features_a, features_b, cfg.features)
    timings["match"] = (perf_counter() - started) * 1000
    started = perf_counter()
    registration = estimate(points_a, points_b, features_a.size, features_b.size,
                            cfg.homography)
    timings["homography"] = (perf_counter() - started) * 1000
    return registration, points_a, points_b, timings, features_a.size, features_b.size


def _masked(frame, dets: list[Detection], cfg: PairConfig):
    if not cfg.mask_bottles or isinstance(frame, FrameFeatures):
        return frame
    size = (frame.shape[1], frame.shape[0])
    return extract(frame, cfg.features, boxes_mask(size, dets))


def match_pair(frame_a, dets_a: list[Detection], frame_b, dets_b: list[Detection],
               cfg: PairConfig = PairConfig()) -> PairResult:
    """Decide for each bottle of frame B whether frame A already holds it. A frame is a
    BGR image or its FrameFeatures (then `mask_bottles` is the caller's business)."""
    frame_a, frame_b = _masked(frame_a, dets_a, cfg), _masked(frame_b, dets_b, cfg)
    registration, points_a, points_b, timings, size_a, size_b = register(frame_a, frame_b, cfg)
    started = perf_counter()
    if registration.ok:
        decisions = associate(dets_a, dets_b, registration.H, size_a, size_b, cfg.association)
    else:
        decisions = [Decision(i, "unregistered") for i in range(len(dets_b))]
    timings["associate"] = (perf_counter() - started) * 1000
    return PairResult(registration, decisions, points_a, points_b, timings)
