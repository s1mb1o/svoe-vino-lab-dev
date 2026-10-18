"""Unique bottles over a series of photos: the stream tracker with each photo a jump.

The video tracker (stream.py) stays as it is; the photo tracker changes how a photo finds
its place and nothing else:

- Keypoints: ALIKED of the whole photo, matched by LightGlue. The steps between photos are
  wide; SIFT inside the bottle boxes (the video) registered 3 of 9 consecutive photos of
  one series, ALIKED of the whole photo all 9 (the shelf edges and the price tags lie in
  the shelf plane).
- The search: at most `tries` keyframes a photo, as a phone has a few seconds a photo (a
  search of all 29 keyframes took 8.3 s on a laptop). First the keyframe of the photo
  before, which overlaps a photo most often; a registration to it holds when it is good
  (`min_loop_inliers`, `min_loop_coverage`), not only strong: two consecutive photos of the
  racks from afar registered with 95 inliers at coverage 0.28 and 64 at 0.29. Then the
  keyframes most alike (`_alike`), whose registrations must be strong: with the newest
  keyframes instead, the first close-up of the racks shot from afar missed them, and its
  whole series came again, green. With no registration the photo is new ground at once: no
  other view of its place will come.
- Then the registration of the video (`_relocalize`): the keyframes that overlap the photo
  in the map, at most `loop_candidates`, confirm their bottles for this photo and add loop
  edges. Without it the bottles of an older series (the racks shot from afar) were not
  confirmed and came again, green, in the close-ups of the same racks.
- A confirmation holds for its photo alone (`trust_steps` 0), nothing waits (`max_wait` 0),
  and every photo is a keyframe (`keyframe_overlap` above 1).
- A registration of a pair is made once a photo (the keyframe of the photo reuses it).
"""

from __future__ import annotations

from dataclasses import replace
from time import perf_counter

import numpy as np

from .features import FeatureConfig, FrameFeatures, extract, match
from .stream import Keyframe, ShelfTracker, StreamConfig


def photo_config(long_side: int = 1440, points: int = 4000) -> StreamConfig:
    return replace(StreamConfig(), max_wait=0, trust_steps=0, keyframe_overlap=1.01,
                   features=FeatureConfig(method="aliked", max_side=long_side, max_features=points))


class PhotoTracker(ShelfTracker):
    def __init__(self, size: tuple[int, int], cfg: StreamConfig | None = None, tries: int = 3):
        super().__init__(size, cfg or photo_config())
        self.tries = tries
        self.cache: dict[tuple[int, int], list] = {}
        self.attempts: list[tuple[int, int, int, float, bool]] = []  # (step, keyframe, inliers, coverage, strong)
        self.clock = {"keypoints": 0.0, "registration": 0.0}
        self.matches = 0
        self.placed_on: int | None = None         # the keyframe the photo was found on
        self.prints: dict[int, np.ndarray] = {}   # keyframe -> descriptors for `_alike`
        self.clock["retrieval"] = 0.0

    def photo(self, number: int, image: np.ndarray, detections) -> list:
        """One photo: a jump from the photo before, then the step."""
        if self.keyframes:
            self._jump()
            self.previous = None
        self.placed_on = None
        return self.step(number, image, detections)

    def _features(self, frame, detections) -> FrameFeatures:
        started = perf_counter()
        features = extract(frame, self.cfg.features)
        self.clock["keypoints"] += perf_counter() - started
        return features

    def _registrations(self, features, candidates):
        """As the video, each pair once a photo, and every attempt logged."""
        cfg = self.cfg
        good = []
        for index in candidates:
            key = (self.count, index)
            if key not in self.cache:
                started = perf_counter()
                points_k, points_f = match(self.keyframes[index].features, features, cfg.features)
                registration = self._register(points_k, points_f)
                self.clock["registration"] += perf_counter() - started
                self.matches += 1
                ok = (registration.ok and registration.inliers >= cfg.min_loop_inliers
                      and registration.coverage >= cfg.min_loop_coverage)
                strong = ok and (registration.inliers >= cfg.strong_inliers
                                 and registration.coverage >= cfg.strong_coverage)
                self.attempts.append((self.count, index, registration.inliers,
                                      registration.coverage, strong))
                self.cache[key] = [(index, registration.H, strong, registration.inliers)] if ok else []
            good += self.cache[key]
            if self.cache[key]:
                self.verified[index] = self.count
        return good

    PRINT = 1024                                  # descriptors a keyframe keeps for `_alike`

    def _alike(self, features: FrameFeatures, candidates: list[int]) -> list[int]:
        """The candidates by how alike their views are to the photo: the mutual nearest
        neighbours between `PRINT` descriptors of each (one product of two matrices a
        keyframe, no LightGlue)."""
        started = perf_counter()
        query = features.descriptors[:self.PRINT]
        score = {}
        for index in candidates:
            if index not in self.prints:
                self.prints[index] = self.keyframes[index].features.descriptors[:self.PRINT]
            similar = query @ self.prints[index].T
            forward, backward = similar.argmax(1), similar.argmax(0)
            score[index] = int((backward[forward] == np.arange(len(query))).sum())
        self.clock["retrieval"] += perf_counter() - started
        return sorted(candidates, key=lambda k: -score[k])

    def _find(self, number: int, features: FrameFeatures) -> None:
        last = len(self.keyframes) - 1
        order = [last] + self._alike(features, list(range(last)))[:self.tries - 1]
        for index in order:
            good = self._registrations(features, [index])
            taken = [g for g in good if g[2] or index == last]
            if taken:
                self.ref, self.P = index, taken[0][1]
                self.anchored = self.localized = self.count
                self.lost = False
                self.found += 1
                self.placed_on = index
                # The keyframes that overlap the photo confirm their bottles (see above).
                self._relocalize(number, features)
                return
        # New ground: a keyframe of its own, to the right of the whole map.
        right = max(self._keyframe_quad(k)[:, 0].max() for k in range(len(self.keyframes)))
        index = self.graph.add(np.array([[1, 0, right + self.size[0]], [0, 1, 0], [0, 0, 1]], float))
        self.keyframes.append(Keyframe(number, self.count, features))
        self.ref, self.P = index, np.eye(3)
        self.anchored = self.localized = self.count
        self.verified = {index: self.count}
        self.lost = False
        self.new_grounds += 1

    def _needs_keyframe(self) -> bool:
        if self.keyframes and self.keyframes[-1].step == self.count:
            return False                          # new ground made the keyframe of the photo
        return super()._needs_keyframe()
