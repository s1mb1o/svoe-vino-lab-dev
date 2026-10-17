"""Unique bottles over a video stream, frame by frame: the algorithm for the phone.

For each frame:
1. Motion. Lucas-Kanade flow of corners on the bottles of the previous frame, then a
   homography of the current frame into the previous one. Cheap enough for a phone.
2. Place on the shelf map. The chain of motions gives H (frame -> map); the map is the
   plane of the first frame. The chain drifts, so from time to time the frame is
   registered directly to an older keyframe that overlaps it, and H is reset from there.
3. Association with the known bottles, whose map boxes are projected into the frame:
   first the bottles seen a moment ago (tracking), then the bottles that left the view or
   were not seen for a while (re-identification); a detection left over starts a new
   bottle.
4. State. A bottle is new during its first appearance. After it left the view and came
   back it is returning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

import cv2
import numpy as np

from .associate import AssociationConfig, bbox_of, box_corners, clip, distance_matrix, hungarian
from .detect import boxes_mask
from .features import FeatureConfig, FrameFeatures, extract, match
from .homography import HomographyConfig, Registration, check, corners, coverage, estimate, project
from .types import Box, Detection


@dataclass(frozen=True)
class StreamConfig:
    flow_scale: float = 0.5          # the optical flow runs on a copy of this scale
    # The model of one step of motion: homography | affine | similarity. On the phone video
    # (no relocalisation, 33 s) the chain of homographies drifted 590-690 px and 1.23-1.28
    # in scale: the perspective terms pile up and inflate the map. Affine steps drifted
    # 200-285 px and 0.92-0.93; similarity steps 515-600 px and 0.83.
    # But the tracker did worse with affine steps (more bottles lost and started again):
    # an affine step fits a tilting handheld frame worse inside the frame.
    motion_model: str = "homography"
    # The model of a registration to a keyframe: homography | affine.
    reloc_model: str = "homography"
    max_corners: int = 600
    min_flow_points: int = 30
    track_gap: int = 10              # frames: a bottle unseen longer is no longer tracked
    track_distance: float = 0.5      # bottle widths, tracking
    reid_distance: float = 0.6       # bottle widths, re-identification
    min_score: float = 0.4           # a detection below this is ignored
    new_score: float = 0.6           # a detection below this starts no new bottle
    # Whole bottles only. The bottles of one shelf stand on one line, so the boxes are
    # grouped in rows by their bottom edge (a gap above `row_gap` of the bottle height
    # starts a new row). A box lower than `min_height` of its row is dropped (a bottle cut
    # by the frame); so is a row whose height is below `min_row_height` of the bottle
    # height (necks above the front bottles, the tops of the next shelf at the frame
    # bottom), and a lone box lower than `min_height` of the bottle height (the neck of a
    # bottle behind). The bottle height is a running 75th percentile of the boxes away
    # from the top and bottom edges: necks are up to 40% of the boxes of a frame.
    min_height: float = 0.75
    min_row_height: float = 0.6
    row_gap: float = 0.2
    # Likewise a box narrower than this share of the running bottle width, unless the side
    # of the frame cuts it: a sliver between two bottles (1.6% of the tall boxes).
    min_width: float = 0.6
    height_rate: float = 0.2         # the update rate of the running bottle size
    edge_margin: float = 0.02        # of the frame width: a box this close to an edge is cut
    leave_margin: float = 0.5        # bottle widths outside the frame: the bottle left the view
    settle_hits: int = 5             # the map box follows the first N whole observations
    keyframe_overlap: float = 0.6    # a new keyframe when no keyframe shares this much
    reloc_every: int = 5             # steps between keyframe registrations
    # Loop closure. The chain drifts about a frame width in half a minute, so the old
    # keyframes of a place are searched around the predicted place, not only where the
    # prediction overlaps them. Keyframes and bottles younger than `recent_steps` belong
    # to this visit: they drift with the chain and are corrected with it.
    recent_steps: int = 50
    search_radius: float = 1.5       # frame widths around the predicted place
    loop_candidates: int = 3
    min_loop_inliers: int = 40
    min_loop_coverage: float = 0.2
    small_correction: float = 0.15   # frame widths: applied at once
    max_jump: float = 2.0            # frame widths: a larger correction is refused
    # A registration this strong makes a jump at once; a weaker one waits for a second
    # registration that agrees.
    strong_inliers: int = 80
    strong_coverage: float = 0.3
    same_place: float = 0.3          # frame widths: keyframes this close show one place
    likely_overlap: float = 0.15     # the predicted overlap of a keyframe worth a try first
    merge_distance: float = 0.5      # bottle widths: a bottle of this visit is an old one
    # Two boxes in one column of one row are one bottle; the weaker box is dropped.
    duplicate_overlap: float = 0.6   # of the narrower width
    # Trust. On a revisit the chain is off by up to 2-3 bottles until a registration to an
    # old keyframe; old bottles then project to wrong places and take wrong detections,
    # and the leftovers start duplicates. While the place is not trusted (an old keyframe
    # is near, and no registration to an old keyframe for `trust_steps`), the tracker
    # keeps only its tracks: no re-identification, no new bottles (the boxes wait, grey),
    # and it tries a registration every step. After `max_wait` untrusted steps it goes on
    # anyway: the ground is new after all.
    trust_steps: int = 30
    max_wait: int = 30
    # A projected bottle and a detection MUST be alike in size: an inflated projection takes
    # the detection of a neighbour. A turn of the camera stretches the map across the
    # shelf alone (the width doubles, the height stays), so both sides are checked.
    max_height_ratio: float = 1.35
    max_width_ratio: float = 1.6
    # But a projection of another size whose centre stands right on the detection (within
    # `reid_tight` of the detection width) is the bottle: near the edge of the registered
    # region the homography stretches the projection (0.7 of the height at 1:11), and the
    # neighbour that an inflated projection takes stands about half a bottle off.
    reid_tight: float = 0.2
    # Young duplicates. A bottle started in the last `young_steps` that turns out to stand
    # where an older bottle stands (column distance below `merge_distance`, one row) is a
    # duplicate: it is merged into the older bottle, which keeps its id.
    young_steps: int = 30
    association: AssociationConfig = field(default_factory=AssociationConfig)
    features: FeatureConfig = field(default_factory=lambda: FeatureConfig(max_side=1280))
    homography: HomographyConfig = field(default_factory=HomographyConfig)


@dataclass
class Bottle:
    """A bottle of the map. Its place is the quadrilateral of its box corners in the map,
    not an axis-aligned box: far from the first frame the map plane is stretched and
    sheared, and the axis-aligned box of a sheared quadrilateral projects back into a
    frame 2-4 times too wide, so the bottle stops matching its own detections."""

    id: int
    quad: np.ndarray                 # (4, 2) map coordinates of the box corners
    first_frame: int                 # the source frame number of the first sight
    last_seen: int                   # the tracker step of the last sight
    first_step: int = 0              # the tracker step of the first sight
    appearance: int = 1
    left: bool = False
    hits: int = 1


@dataclass
class Keyframe:
    frame: int
    step: int                        # the tracker step of the keyframe
    H: np.ndarray                    # keyframe -> map
    features: FrameFeatures
    quad: np.ndarray                 # the frame outline in the map


@dataclass
class Shown:
    """One detection of the current frame and what it is."""

    box: Box
    status: str                      # new | returning | pending (waits for a trusted place) | ignored
    bottle: int | None = None


def _area(quad: np.ndarray) -> float:
    return abs(cv2.contourArea(quad.astype(np.float32)))


def _shared(quad_a: np.ndarray, quad_b: np.ndarray) -> float:
    """The share of quad_a that quad_b covers."""
    area, _ = cv2.intersectConvexConvex(quad_a.astype(np.float32), quad_b.astype(np.float32))
    return area / max(_area(quad_a), 1e-6)


class ShelfTracker:
    def __init__(self, size: tuple[int, int], cfg: StreamConfig = StreamConfig()):
        self.size = size
        self.cfg = cfg
        self.H = np.eye(3)
        self.bottles: list[Bottle] = []
        self.next_id = 0
        self.keyframes: list[Keyframe] = []
        self.previous: tuple[np.ndarray, list[Box]] | None = None
        self.count = 0
        self.corrections: list[tuple[int, float]] = []
        self.loops: list[tuple[int, float, int]] = []   # (frame, shift, merged bottles)
        self.pending: tuple[int, int, float] | None = None   # (step, keyframe, shift)
        self.localized = -10 ** 9        # the step of the last registration to an old keyframe
        self.untrusted = 0               # untrusted steps in a row
        self.merged_young = 0
        self.distorted = False           # a box waits for a registration (see _associate)
        self.trusted = True
        self.poses: dict[int, np.ndarray] = {}   # source frame number -> H (frame -> map)
        self.bottle_height: float | None = None  # the running bottle height in pixels
        self.bottle_width: float | None = None
        self.dropped = 0
        self.lost_motion = 0
        self.timings: dict[str, float] = {}

    # ------------------------------------------------------------------ geometry

    def _to_map(self, box: Box) -> np.ndarray:
        """The map quadrilateral of a frame box."""
        return project(self.H, box_corners(box))

    @staticmethod
    def _to_frame(quad: np.ndarray, inverse: np.ndarray) -> Box:
        """The frame box of a map quadrilateral."""
        return bbox_of(project(inverse, quad))

    def _quad(self) -> np.ndarray:
        return project(self.H, corners(self.size))

    def _cut(self, box: Box) -> bool:
        margin = self.cfg.edge_margin * self.size[0]
        return (box[0] < margin or box[1] < margin or box[2] > self.size[0] - margin
                or box[3] > self.size[1] - margin)

    def _running(self, value: float | None, samples: list[float], q: float = 50) -> float | None:
        if len(samples) < 3:
            return value
        sample = float(np.percentile(samples, q))
        rate = self.cfg.height_rate
        return sample if value is None else (1 - rate) * value + rate * sample

    def _rows(self, detections: list[Detection]) -> list[list[Detection]]:
        """Group the boxes in rows by their bottom edge."""
        order = sorted(detections, key=lambda d: d.box[3])
        rows: list[list[Detection]] = []
        for det in order:
            if rows and det.box[3] - rows[-1][-1].box[3] <= self.cfg.row_gap * self.bottle_height:
                rows[-1].append(det)
            else:
                rows.append([det])
        return rows

    def _whole_bottles(self, detections: list[Detection]) -> list[Detection]:
        """Drop the boxes that are not whole bottles (`min_height`, `min_row_height`,
        `min_width`)."""
        cfg = self.cfg
        margin = cfg.edge_margin * self.size[0]
        self.bottle_height = self._running(self.bottle_height, [
            d.box[3] - d.box[1] for d in detections
            if d.box[1] > margin and d.box[3] < self.size[1] - margin], q=75)
        if self.bottle_height is None or not detections:
            return detections
        kept = []
        for row in self._rows(detections):
            heights = [d.box[3] - d.box[1] for d in row]
            if len(row) == 1:
                reference = self.bottle_height
            else:
                reference = float(np.percentile(heights, 75))
                if reference < cfg.min_row_height * self.bottle_height:
                    continue
            kept += [d for d, h in zip(row, heights) if h >= cfg.min_height * reference]
        inner = [d for d in kept if d.box[0] > margin and d.box[2] < self.size[0] - margin]
        self.bottle_width = self._running(self.bottle_width, [d.width for d in inner])
        if self.bottle_width is not None:
            kept = [d for d in kept if d.width >= cfg.min_width * self.bottle_width
                    or d.box[0] <= margin or d.box[2] >= self.size[0] - margin]
        # One box per bottle: of two boxes in one column of one row, keep the stronger.
        unique: list[Detection] = []
        for det in sorted(kept, key=lambda d: -d.score):
            height = det.box[3] - det.box[1]
            if not any(min(det.box[2], u.box[2]) - max(det.box[0], u.box[0])
                       >= cfg.duplicate_overlap * min(det.width, u.width)
                       and min(det.box[3], u.box[3]) - max(det.box[1], u.box[1])
                       >= 0.5 * max(height, u.box[3] - u.box[1])
                       for u in unique):
                unique.append(det)
        self.dropped += len(detections) - len(unique)
        return unique

    # ------------------------------------------------------------------ motion

    def _flow(self, gray_prev, gray, boxes_prev) -> np.ndarray | None:
        """The homography of the current frame into the previous one, full resolution."""
        s = self.cfg.flow_scale
        mask = np.zeros_like(gray_prev)
        for x1, y1, x2, y2 in boxes_prev:
            mask[int(y1 * s):int(y2 * s), int(x1 * s):int(x2 * s)] = 255
        points = None
        if mask.any():
            points = cv2.goodFeaturesToTrack(gray_prev, self.cfg.max_corners, 0.01, 7, mask=mask)
        if points is None or len(points) < self.cfg.min_flow_points:
            points = cv2.goodFeaturesToTrack(gray_prev, self.cfg.max_corners, 0.01, 7)
        if points is None or len(points) < self.cfg.min_flow_points:
            return None
        lk = dict(winSize=(21, 21), maxLevel=4,
                  criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
        moved, status, _ = cv2.calcOpticalFlowPyrLK(gray_prev, gray, points, None, **lk)
        back, status_back, _ = cv2.calcOpticalFlowPyrLK(gray, gray_prev, moved, None, **lk)
        good = (status.ravel() == 1) & (status_back.ravel() == 1) & (
            np.linalg.norm((back - points).reshape(-1, 2), axis=1) < 1.0)
        if good.sum() < self.cfg.min_flow_points:
            return None
        if self.cfg.motion_model == "homography":
            H, inliers = cv2.findHomography(moved[good], points[good], cv2.USAC_MAGSAC, 2.0)
        else:
            estimator = (cv2.estimateAffine2D if self.cfg.motion_model == "affine"
                         else cv2.estimateAffinePartial2D)
            A, inliers = estimator(moved[good], points[good], method=cv2.RANSAC,
                                   ransacReprojThreshold=2.0)
            H = None if A is None else np.vstack([A, [0.0, 0.0, 1.0]])
        if H is None or inliers.sum() < self.cfg.min_flow_points:
            return None
        S = np.diag([s, s, 1.0])
        H = np.linalg.inv(S) @ H @ S
        H /= H[2, 2]
        return None if check(H, self.size, self.cfg.homography) else H

    # ------------------------------------------------------------------ keyframes

    def _register(self, points_k: np.ndarray, points_f: np.ndarray) -> Registration:
        """The registration of the frame to a keyframe with the model `reloc_model`."""
        cfg = self.cfg
        if cfg.reloc_model == "homography":
            return estimate(points_k, points_f, self.size, self.size, cfg.homography)
        count = len(points_k)
        if count < max(4, cfg.homography.min_inliers):
            return Registration(False, f"{count} matches", None, count, 0)
        threshold = cfg.homography.ransac_threshold * float(np.hypot(*self.size))
        A, mask = cv2.estimateAffine2D(points_f, points_k, method=cv2.RANSAC,
                                       ransacReprojThreshold=threshold)
        if A is None:
            return Registration(False, "no affine", None, count, 0)
        H = np.vstack([A, [0.0, 0.0, 1.0]])
        mask = mask.ravel().astype(bool)
        inliers = int(mask.sum())
        reason = check(H, self.size, cfg.homography)
        if reason is None and inliers < cfg.homography.min_inliers:
            reason = f"{inliers} inliers"
        spread = coverage(H, points_f[mask], self.size, self.size) if reason is None else 0.0
        return Registration(reason is None, reason or "ok", H, count, inliers, mask,
                            coverage=spread)

    def _features(self, frame, detections) -> FrameFeatures:
        return extract(frame, self.cfg.features, boxes_mask(self.size, detections))

    def _relocalize(self, number: int, features: FrameFeatures) -> None:
        """Register the frame to old keyframes near the predicted place. A small correction
        is applied at once; a jump only when two registrations in a row agree."""
        cfg = self.cfg
        quad = self._quad()
        centre = quad.mean(0)
        width = float(np.linalg.norm(quad[1] - quad[0]))
        # Every keyframe near the predicted place, of any age: on the first pass the recent
        # keyframes keep the frame registered (small corrections, a trusted place).
        nearby = [(float(np.linalg.norm(kf.quad.mean(0) - centre)), index)
                  for index, kf in enumerate(self.keyframes)]
        nearby = [c for c in nearby if c[0] <= cfg.search_radius * width]
        # One keyframe per place, the oldest: the place of the old bottles is the place of
        # its first keyframe. A later keyframe of the same place MAY carry the drift of the
        # visit that made it.
        layer: list[tuple[float, int]] = []
        for distance, index in sorted(nearby, key=lambda c: self.keyframes[c[1]].step):
            if all(np.linalg.norm(self.keyframes[index].quad.mean(0)
                                  - self.keyframes[other].quad.mean(0)) > cfg.same_place * width
                   for _, other in layer):
                layer.append((distance, index))
        grid = np.array([[x, y] for x in np.linspace(0.2, 0.8, 4) * self.size[0]
                         for y in np.linspace(0.2, 0.8, 4) * self.size[1]])
        # The oldest first among the keyframes that likely overlap the frame: drift MAY put
        # a later keyframe of the place farther than `same_place` from its first keyframe,
        # and a registration to the later one keeps the frame in the drifted layer, away
        # from the old bottles of the place (their projections twice too wide at 1:10).
        order = sorted(layer, key=lambda c: (_shared(quad, self.keyframes[c[1]].quad)
                                              < cfg.likely_overlap,
                                              self.keyframes[c[1]].step))
        for _, index in order[:cfg.loop_candidates]:
            keyframe = self.keyframes[index]
            points_k, points_f = match(keyframe.features, features, cfg.features)
            registration = self._register(points_k, points_f)
            if (not registration.ok or registration.inliers < cfg.min_loop_inliers
                    or registration.coverage < cfg.min_loop_coverage):
                continue
            H_new = keyframe.H @ registration.H
            shift = np.linalg.norm(project(H_new, grid) - project(self.H, grid), axis=1).max()
            shift = float(shift / self.size[0])
            if shift <= cfg.small_correction:
                self.H = H_new
                self.corrections.append((number, shift))
                self.pending = None
                self.localized = self.count
                return
            if shift > cfg.max_jump:
                continue
            strong = (registration.inliers >= cfg.strong_inliers
                      and registration.coverage >= cfg.strong_coverage)
            if strong or (self.pending is not None and self.pending[1] == index
                          and self.count - self.pending[0] <= 2 * cfg.reloc_every
                          and abs(self.pending[2] - shift) <= 0.1):
                self.localized = self.count
                merged = self._close_loop(H_new)
                self.loops.append((number, shift, merged))
                self.corrections.append((number, shift))
                self.pending = None
            else:
                self.pending = (self.count, index, shift)
            return

    def _close_loop(self, H_new: np.ndarray) -> int:
        """Move the map of this visit by the correction, and merge the bottles of this
        visit that land on old bottles. Return the number of merged bottles."""
        cfg = self.cfg
        C = H_new @ np.linalg.inv(self.H)
        self.H = H_new
        for kf in self.keyframes:
            if self.count - kf.step <= cfg.recent_steps:
                kf.H = C @ kf.H
                kf.quad = project(C, kf.quad)
        recent = [b for b in self.bottles if self.count - b.first_step <= cfg.recent_steps]
        old = [b for b in self.bottles if self.count - b.first_step > cfg.recent_steps]
        for bottle in recent:
            bottle.quad = project(C, bottle.quad)
        # Compare in the current frame, where the map distortion does not matter.
        inverse = np.linalg.inv(self.H)
        frame: Box = (0.0, 0.0, float(self.size[0]), float(self.size[1]))
        recent_boxes = [self._to_frame(b.quad, inverse) for b in recent]
        old_boxes = [self._to_frame(b.quad, inverse) for b in old]
        recent = [b for b, box in zip(recent, recent_boxes) if clip(box, frame) is not None]
        recent_boxes = [box for box in recent_boxes if clip(box, frame) is not None]
        old = [b for b, box in zip(old, old_boxes) if clip(box, frame) is not None]
        old_boxes = [box for box in old_boxes if clip(box, frame) is not None]
        if not recent or not old:
            return 0
        distance = distance_matrix([clip(box, frame) for box in recent_boxes],
                                   [clip(box, frame) for box in old_boxes],
                                   [box[2] - box[0] for box in recent_boxes],
                                   [box[2] - box[0] for box in old_boxes], cfg.association)
        merged = set()
        for i, j in hungarian(distance, cfg.merge_distance).items():
            young, earlier = recent[i], old[j]
            if earlier.left or self.count - earlier.last_seen > cfg.track_gap:
                earlier.appearance += 1
            earlier.left = False
            earlier.last_seen = max(earlier.last_seen, young.last_seen)
            merged.add(young.id)
        self.bottles = [b for b in self.bottles if b.id not in merged]
        return len(merged)

    def _needs_keyframe(self) -> bool:
        """A keyframe where no keyframe covers the frame enough, and only where the place
        of the frame is trusted. Otherwise a revisit before its loop closure would store a
        second, drifted keyframe of the place."""
        quad = self._quad()
        return self.trusted and (not self.keyframes or max(
            _shared(quad, kf.quad) for kf in self.keyframes) < self.cfg.keyframe_overlap)

    def _near_old_keyframe(self) -> bool:
        """Whether an old keyframe (not of this visit) lies near the predicted place."""
        cfg = self.cfg
        quad = self._quad()
        centre = quad.mean(0)
        width = float(np.linalg.norm(quad[1] - quad[0]))
        return any(self.count - kf.step > cfg.recent_steps
                   and np.linalg.norm(kf.quad.mean(0) - centre) <= cfg.search_radius * width
                   for kf in self.keyframes)

    def _trusted(self) -> bool:
        """Whether the place of the frame is trusted (see `trust_steps`)."""
        cfg = self.cfg
        if self.count - self.localized <= cfg.trust_steps or not self._near_old_keyframe():
            self.untrusted = 0
            return True
        self.untrusted += 1
        return self.untrusted > cfg.max_wait

    # ------------------------------------------------------------------ association

    def _associate(self, number: int, detections: list[Detection],
                   trusted: bool = True) -> list[Shown]:
        cfg = self.cfg
        frame: Box = (0.0, 0.0, float(self.size[0]), float(self.size[1]))
        inverse = np.linalg.inv(self.H)
        projected = [self._to_frame(b.quad, inverse) for b in self.bottles]
        in_view = [clip(box, frame) is not None for box in projected]

        tracked = [k for k, b in enumerate(self.bottles)
                   if in_view[k] and not b.left and self.count - b.last_seen <= cfg.track_gap]
        others = [k for k, b in enumerate(self.bottles) if in_view[k] and k not in set(tracked)]
        boxes = [d.box for d in detections]
        widths = [d.width for d in detections]

        blocked: set[int] = set()

        def assign(pool, free, limit, gate):
            if not pool or not free:
                return {}
            cut = [clip(projected[k], frame) for k in pool]
            distance = distance_matrix([boxes[i] for i in free], cut,
                                       [widths[i] for i in free],
                                       [projected[k][2] - projected[k][0] for k in pool],
                                       cfg.association)
            for a, i in enumerate(free if gate else []):
                height = boxes[i][3] - boxes[i][1]
                for b, box in enumerate(cut):
                    if box is None or distance[a, b] > limit:
                        continue
                    ratio_h = (box[3] - box[1]) / max(height, 1e-6)
                    full = projected[pool[b]]
                    ratio_w = (full[2] - full[0]) / max(widths[i], 1e-6)
                    if (not 1 / cfg.max_height_ratio <= ratio_h <= cfg.max_height_ratio
                            or not 1 / cfg.max_width_ratio <= ratio_w <= cfg.max_width_ratio):
                        offset = abs((boxes[i][0] + boxes[i][2]) - (full[0] + full[2])) / 2
                        offset /= max(widths[i], 1e-6)
                        if offset <= cfg.reid_tight:
                            distance[a, b] = offset
                        else:
                            distance[a, b] = np.inf
                            blocked.add(i)
            return {free[i]: pool[j] for i, j in hungarian(distance, limit).items()}

        free = list(range(len(detections)))
        # The size check only for re-identification: a tracked bottle projects well, and
        # the box of a tracked bottle changes width when a neighbour hides a part of it.
        first = assign(tracked, free, cfg.track_distance, gate=False)
        # A box cut by the frame edge is not re-identified: its size says nothing, and an
        # inflated projection at the edge would take it. It waits to be whole.
        free = [i for i in free if i not in first and not self._cut(boxes[i])]
        second = assign(others, free, cfg.reid_distance, gate=True) if trusted else {}
        matched = {**first, **second}
        # An old bottle at the place of a box, but of another size: the map is distorted
        # here now. The box waits (no new bottle), and the next step registers the frame.
        blocked -= set(second)
        if blocked:
            self.distorted = True

        shown = []
        for i, det in enumerate(detections):
            cut = self._cut(det.box)
            if i in matched:
                bottle = self.bottles[matched[i]]
                if bottle.left:
                    bottle.appearance += 1
                    bottle.left = False
                bottle.last_seen = self.count
                if not cut and bottle.hits < cfg.settle_hits:
                    self._observe(bottle, det.box)
                status = "new" if bottle.appearance == 1 else "returning"
                shown.append(Shown(det.box, status, bottle.id))
            elif not cut and det.score >= cfg.new_score and (not trusted or i in blocked):
                shown.append(Shown(det.box, "pending"))
            elif not cut and det.score >= cfg.new_score:
                bottle = Bottle(self.next_id, self._to_map(det.box), number, self.count,
                                first_step=self.count)
                self.next_id += 1
                self.bottles.append(bottle)
                shown.append(Shown(det.box, "new", bottle.id))
            else:
                shown.append(Shown(det.box, "ignored"))

        # A bottle that is now clearly outside the frame has left the view. The bottles
        # that this frame started are in view.
        for k, bottle in enumerate(self.bottles[:len(projected)]):
            x1, y1, x2, y2 = projected[k]
            margin = cfg.leave_margin * (x2 - x1)
            if (x2 < -margin or x1 > self.size[0] + margin or y2 < -margin
                    or y1 > self.size[1] + margin):
                bottle.left = True
        return self._merge_young(shown)

    def _merge_young(self, shown: list[Shown]) -> list[Shown]:
        """Merge the young bottles that stand where an older bottle stands (see
        `young_steps`). Two bottles that both have a detection now are two bottles."""
        cfg = self.cfg
        # Not the bottles of this step: the association has just refused them an old bottle.
        young = [b for b in self.bottles if 0 < self.count - b.first_step <= cfg.young_steps]
        old = [b for b in self.bottles if self.count - b.first_step > cfg.young_steps]
        if not young or not old:
            return shown
        frame: Box = (0.0, 0.0, float(self.size[0]), float(self.size[1]))
        inverse = np.linalg.inv(self.H)
        box_y = [self._to_frame(b.quad, inverse) for b in young]
        box_o = [self._to_frame(b.quad, inverse) for b in old]
        distance = distance_matrix([clip(b, frame) for b in box_y], [clip(b, frame) for b in box_o],
                                   [b[2] - b[0] for b in box_y], [b[2] - b[0] for b in box_o],
                                   cfg.association)
        detected = {s.bottle for s in shown if s.bottle is not None}
        for i, a in enumerate(young):
            for j, b in enumerate(old):
                ratio_w = (box_y[i][2] - box_y[i][0]) / max(box_o[j][2] - box_o[j][0], 1e-6)
                ratio_h = (box_y[i][3] - box_y[i][1]) / max(box_o[j][3] - box_o[j][1], 1e-6)
                if ((a.id in detected and b.id in detected)
                        or not 1 / cfg.max_width_ratio <= ratio_w <= cfg.max_width_ratio
                        or not 1 / cfg.max_height_ratio <= ratio_h <= cfg.max_height_ratio):
                    distance[i, j] = np.inf
        into = {young[i].id: old[j] for i, j in hungarian(distance, cfg.merge_distance).items()}
        if not into:
            return shown
        for item in shown:
            target = into.get(item.bottle)
            if target is None:
                continue
            if target.left or self.count - target.last_seen > cfg.track_gap:
                target.appearance += 1
            target.left = False
            target.last_seen = self.count
            item.bottle = target.id
            item.status = "new" if target.appearance == 1 else "returning"
        self.bottles = [b for b in self.bottles if b.id not in into]
        self.merged_young += len(into)
        return shown

    def _observe(self, bottle: Bottle, box: Box) -> None:
        weight = 1.0 / (bottle.hits + 1)
        bottle.quad = (1 - weight) * bottle.quad + weight * self._to_map(box)
        bottle.hits += 1

    # ------------------------------------------------------------------ the step

    def step(self, number: int, frame: np.ndarray, detections: list[Detection]) -> list[Shown]:
        cfg = self.cfg
        times = {}
        started = perf_counter()
        small = cv2.resize(frame, None, fx=cfg.flow_scale, fy=cfg.flow_scale,
                           interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        detections = self._whole_bottles([d for d in detections if d.score >= cfg.min_score])
        if self.previous is not None:
            H_step = self._flow(self.previous[0], gray, self.previous[1])
            if H_step is None:
                self.lost_motion += 1
            else:
                self.H = self.H @ H_step
        times["motion"] = perf_counter() - started

        started = perf_counter()
        features = None
        if self.keyframes and (self.count % cfg.reloc_every == 0 or not self.trusted
                               or self.distorted):
            self.distorted = False
            features = self._features(frame, detections)
            self._relocalize(number, features)
        times["relocalize"] = perf_counter() - started

        started = perf_counter()
        self.trusted = self._trusted()
        shown = self._associate(number, detections, self.trusted)
        times["associate"] = perf_counter() - started

        started = perf_counter()
        if self._needs_keyframe():
            self.keyframes.append(Keyframe(number, self.count, self.H.copy(),
                                           features or self._features(frame, detections),
                                           self._quad()))
        times["keyframe"] = perf_counter() - started

        self.previous = (gray, [d.box for d in detections])
        self.poses[number] = self.H.copy()
        self.count += 1
        for key, value in times.items():
            self.timings[key] = self.timings.get(key, 0.0) + value
        return shown


COLORS = {"new": (60, 200, 60), "returning": (40, 40, 235), "ignored": (160, 160, 160),
          "pending": (230, 230, 230)}


def draw(frame: np.ndarray, shown: list[Shown], text: str = "") -> np.ndarray:
    out = frame.copy()
    for item in shown:
        x1, y1, x2, y2 = map(int, item.box)
        thick = 2 if item.status == "ignored" else 5
        cv2.rectangle(out, (x1, y1), (x2, y2), COLORS[item.status], thick)
        if item.bottle is not None:
            cv2.putText(out, str(item.bottle), (x1 + 4, y1 + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        COLORS[item.status], 2, cv2.LINE_AA)
    if text:
        cv2.rectangle(out, (0, 0), (out.shape[1], 44), (255, 255, 255), -1)
        cv2.putText(out, text, (10, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 20), 2, cv2.LINE_AA)
    return out
