"""Unique bottles over a video stream, frame by frame: the algorithm for the phone.

For each frame:
1. Motion. Lucas-Kanade flow of corners on the bottles of the previous frame, then a
   homography of the current frame into the previous one. Cheap enough for a phone.
2. Place on the shelf map: a pose graph of keyframes (posegraph.py). The frame holds its
   homography P into its reference keyframe (the chain of motions since that keyframe),
   so H = G_ref @ P. A registration to another keyframe adds a loop edge; when the edge
   disagrees with the graph, the graph is optimised and the drift spreads over the path.
   Each bottle lives in the coordinates of the keyframe that saw it first and moves with
   it, so a place exists once in the map, not once per visit.
3. Association with the known bottles, whose centres are projected into the frame:
   first the bottles seen a moment ago (tracking), then the bottles that left the view or
   were not seen for a while (re-identification); a detection left over starts a new
   bottle.
4. State. A bottle is new during its first appearance. After it left the view and came
   back it is returning.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from time import perf_counter

import cv2
import numpy as np

from .associate import AssociationConfig, box_corners, hungarian
from .detect import boxes_mask
from .features import FeatureConfig, FrameFeatures, extract, match
from .homography import HomographyConfig, Registration, check, corners, coverage, estimate, project
from .posegraph import Edge, PoseGraph
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
    # Of the frame width: a box this close to an edge is cut. A box cut by a side of the
    # frame is dropped (the user's rule: no box without a small margin from the side); a
    # box cut by the top or bottom only continues a track.
    edge_margin: float = 0.02
    leave_margin: float = 0.5        # bottle widths outside the frame: the bottle left the view
    settle_hits: int = 5             # the map box follows the first N whole observations
    keyframe_overlap: float = 0.6    # a new keyframe when no keyframe shares this much
    reloc_every: int = 5             # steps between keyframe registrations
    # Registration to keyframes. The chain drifts about a frame width in half a minute, so
    # the keyframes are searched around the predicted place; those that overlap the frame
    # most are tried first. Keyframes and bottles younger than `recent_steps` belong to
    # this visit (see `trust_steps`).
    recent_steps: int = 50
    search_radius: float = 1.5       # frame widths around the predicted place
    loop_candidates: int = 3
    min_loop_inliers: int = 40
    min_loop_coverage: float = 0.2
    small_correction: float = 0.15   # frame widths: a loop edge this close is taken at once
    max_jump: float = 2.0            # frame widths: a loop edge farther off is refused
    # A registration this strong is taken at once; a weaker one that disagrees with the
    # graph waits for a second registration that agrees.
    strong_inliers: int = 80
    strong_coverage: float = 0.3
    loop_weight: float = 2.0         # a registration is surer than a chain of motions
    chain_weight: float = 0.5        # an edge through the chain of motions
    fresh_steps: int = 10            # a chain this short MAY make an edge
    optimize_above: float = 30.0     # map pixels: a loop edge this far off optimises the graph
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
    # A jump. When the motion of the camera between two frames is not found (the optical
    # flow fails: a frame of another place, a whip, a covered lens), the place of the
    # frame is lost: the tracks end (their bottles have left the view), nothing is given
    # by place, no new bottle starts (the boxes wait, white), the labels wait, and every
    # step registers the frame to all the keyframes until a registration is strong
    # (`strong_inliers`, `strong_coverage`). After `max_wait` lost steps the place is new
    # ground: a keyframe of its own, away from the map. The search near the predicted
    # place (`search_radius`) never tries the keyframes of a far place: four frames of the
    # video fed after its end took the ids of the place where the video ended, red.
    # Bottles are compared by the projected centre alone, across the shelf, in widths of the
    # detection, and in one row (each centre inside the other's vertical span). Not by the
    # projected box: a bottle is a cylinder, not a part of the shelf plane, so a homography
    # from an oblique keyframe to a frontal frame stretches its box (1.7-1.9 times the width
    # at 1:10) while its centre stays right. Normalised by the detection, not by the
    # projection, an inflated projection does not bring a neighbour close either.
    # Young duplicates. A bottle started in the last `young_steps` that turns out to stand
    # where an older bottle stands (column distance below `merge_distance`, one row) is a
    # duplicate: it is merged into the older bottle, which keeps its id.
    young_steps: int = 30
    # Neighbour history. The bottles of a shelf keep their order, so the bottles seen side
    # by side in one row (centres within `adjacent_gap` bottle widths, nothing between) are
    # counted as neighbours over the frames. A bottle has a habitual neighbour on a side
    # when that one stood there in at least `habit_count` frames and `habit_share` of them.
    # A re-identification is vetoed when a neighbour of the box has a habitual neighbour on
    # that side other than the bottle (bottle 11 of the first frame "found" next to 108,
    # whose neighbours were 8 and 13). A box left without a bottle takes the habitual
    # neighbour of its neighbour, when that bottle is free in the frame and projects within
    # `habit_reach` bottle widths.
    adjacent_gap: float = 1.6
    habit_count: int = 3
    habit_share: float = 0.6
    habit_reach: float = 3.0
    # Neighbour rescue. A tracked bottle that found no detection gets a second try at its
    # prediction moved by the median offset of the matched bottles around it (within
    # `rescue_radius` bottle widths, at least `rescue_support` of them): when the bottles
    # around keep their ids, the bottle among them keeps its id too.
    # Visual confirmation. An old bottle is re-identified only where the frame has seen
    # its place: a registration to its anchor keyframe, or to a keyframe at most
    # `anchor_window` keyframes from it (made right before or after it, so tied to it by
    # direct registrations), in the last `trust_steps`. The map alone is not enough: at
    # 37 s the chain had carried the first keyframe next to the current view, and bottle
    # 11 of the first frame was "found" next to bottle 108.
    anchor_window: int = 2
    rescue_radius: float = 3.0
    rescue_support: int = 2
    rescue_distance: float = 0.5
    # The map of ids keeps the label of each bottle: the SIFT descriptors inside its box
    # from its first `label_views` whole views on its first pass (frames with keypoints,
    # `label_gap` steps apart at least; at most `label_size` descriptors a view). On a
    # frame with keypoints each descriptor of a box votes for the bottle of its nearest
    # label descriptor among the bottles of the map within `label_reach` bottle widths of
    # the box (half a bottle height up or down), when it passes the ratio test
    # `label_ratio` against the nearest descriptor of another of them: two bottles of one
    # wine side by side cancel each other, and the place decides between them. The label
    # of a box names a bottle with `label_votes` votes for it and `label_margin` times
    # more than for any other.
    # The check of the rows (the ideas of the user: no cell of the frame may contradict
    # the map; a row holds different wines, so its labelled cells at both ends anchor
    # it). The ids are given as before (tracking, place, neighbours); then in each row of
    # the frame the anchors are the boxes whose labels name a bottle. An anchor that
    # names a bottle other than the one its box holds counts only when the held bottle
    # has a label (a new bottle has none: its label votes for a bottle of its wine
    # nearby), and is not a twin of it: two bottles whose labels share `label_twins` of
    # their descriptors (Lowe matches, the smaller share of the two ways) are one wine,
    # and the label does not tell them apart (random pairs of the video 0.022 at the
    # median and 0.094 at p99; two halves of the views of one bottle 0.25 at p10; 39 and
    # 46, which a check of single cells swapped back and forth at 15-16 s, 0.156; 28 and
    # 30, 0.27). The shift of an anchor is its box against the place of its bottle in
    # the map; the shift that most anchors of the row agree on (within
    # `label_tolerance` widths; a tie goes to the anchors that agree with their boxes)
    # wins. When an anchor of the winning group disagrees with its box and the group has
    # `label_support` anchors, the row is off: the anchors take their bottles, and the
    # other boxes of the row the bottles at their places moved by the shift (the bottles
    # of the keyframes of the anchors, within `anchor_window`: the map MAY hold two rows
    # of one frame two bottles apart, 67 s, while the bottles of this pass stand in
    # place). A single cell would leave the twins: at 67 s it gave 32, 34, 36, 40 for 32,
    # 34, 36, 38 (36 and 38 are both Fiore). The boxes that lose their bottles are left
    # free, and the free boxes take the released bottles by place. Two guards, from a row
    # of six Abrau-Durso 1870 at 20.7 s of 115301, which the check moved two bottles off
    # while the tracks held it right (a box with no id named 121, a label of 1870, that
    # another box held): a bottle that two boxes of the row name is a twin, and neither
    # box is an anchor; a box whose label confirms its bottle keeps it (121, 110 votes).
    # (A third, no row off by boxes with no id alone, also refused the right names of
    # the upper row of the first rack at 39.1 s of 115611.) With `label_fix` off the
    # check only logs.
    label_views: int = 3
    label_gap: int = 5
    label_size: int = 200
    label_ratio: float = 0.8
    label_votes: int = 8
    label_margin: float = 2.0
    label_reach: float = 3.0
    label_support: int = 2
    label_tolerance: float = 0.35
    label_twins: float = 0.12
    label_fix: bool = True
    association: AssociationConfig = field(default_factory=AssociationConfig)
    features: FeatureConfig = field(default_factory=lambda: FeatureConfig(max_side=1280))
    homography: HomographyConfig = field(default_factory=HomographyConfig)


@dataclass
class Bottle:
    """A bottle of the map. Its place is the quadrilateral of its box corners in the pixels
    of its anchor keyframe: it moves with that keyframe when the graph is optimised. A
    quadrilateral, not an axis-aligned box: the axis-aligned box of a sheared
    quadrilateral projects back into a frame 2-4 times too wide."""

    id: int
    anchor: int                      # the keyframe of the coordinates of `quad`
    quad: np.ndarray                 # (4, 2) box corners in the anchor keyframe
    first_frame: int                 # the source frame number of the first sight
    last_seen: int                   # the tracker step of the last sight
    first_step: int = 0              # the tracker step of the first sight
    appearance: int = 1
    left: bool = False
    hits: int = 1
    # The last box of the bottle and the chain of camera motions at that frame: a tracked
    # bottle is predicted from its last box moved by the motions of the camera since, not
    # from the map, whose box MAY carry an early bad box (a neck of a bottle behind in
    # it), and not through the graph: at 71.4 s the frame passed from keyframe 21 to
    # keyframe 4, which the graph holds one bottle apart, every tracked bottle of the
    # upper row moved one box to the right, and 30 left its box to a new 121.
    last_box: Box | None = None
    last_M: np.ndarray | None = None
    label: list[np.ndarray] = field(default_factory=list)   # descriptors, one array a view
    labelled: int = -10 ** 9         # the step of the last view of the label


@dataclass
class Keyframe:
    """A keyframe; its pose is node `index` of the graph."""

    frame: int
    step: int                        # the tracker step of the keyframe
    features: FrameFeatures


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
        self.graph = PoseGraph(size)
        self.keyframes: list[Keyframe] = []
        self.ref: int | None = None      # the reference keyframe of the frame
        self.P = np.eye(3)               # frame -> reference keyframe
        self.M = np.eye(3)               # frame -> first frame by the motions alone
        self.anchored = 0                # the step since which P chains
        self.dropped_edges = 0
        self.rescued = 0
        self.verified: dict[int, int] = {}  # keyframe -> the step of its last registration
        self.waited = 0                     # steps in a row with boxes waiting for a place
        self.right: dict[int, dict[int, int]] = {}   # a -> {b: frames b stood right of a}
        self.left: dict[int, dict[int, int]] = {}    # b -> {a: frames a stood left of b}
        self.vetoed = 0
        self.suggested = 0
        self.wanted: set[int] = set()       # the keyframes of the waiting bottles
        self.need_registration = False
        self.bottles: list[Bottle] = []
        self.next_id = 0
        self.previous: tuple[np.ndarray, list[Box]] | None = None
        self.count = 0
        self.corrections: list[tuple[int, float]] = []
        # (frame, loop edge error in frame widths, largest edge error before and after the
        # optimisation in map pixels, merged bottles)
        self.loops: list[tuple[int, float, float, float, int]] = []
        self.pending: tuple[int, int, float] | None = None   # (step, keyframe, error)
        self.localized = -10 ** 9        # the step of the last registration to a keyframe
        self.untrusted = 0               # untrusted steps in a row
        self.lost = False                # the place of the frame is lost (see `max_wait`)
        self.lost_steps = 0
        self.jumps = 0
        self.found = 0                   # places found again after a jump
        self.new_grounds = 0
        self.merged_young = 0
        self.trusted = True
        self.poses: dict[int, np.ndarray] = {}   # source frame number -> H (frame -> map)
        self.bottle_height: float | None = None  # the running bottle height in pixels
        self.bottle_width: float | None = None
        self.dropped = 0
        self.lost_motion = 0
        self.timings: dict[str, float] = {}
        self.votes: dict[int, dict[int, int]] = {}   # box -> {bottle index: votes} of this frame
        # The check of the frames: (frame, box, id held or None, id named, votes for the
        # named, votes for the held, outcome: fixed | lone | outvoted | logged).
        self.contradictions: list[tuple] = []
        self.label_checks = 0               # boxes compared with the label of their bottle
        self.label_confirmed = 0
        self.conflicted = 0                 # steps in a row with boxes in conflict with the map
        self.conflicts = 0
        self.closed = 0

    # ------------------------------------------------------------------ geometry

    @property
    def H(self) -> np.ndarray:
        """The homography of the frame into the map."""
        return self.P if self.ref is None else self.graph.poses[self.ref] @ self.P

    def _keyframe_quad(self, index: int) -> np.ndarray:
        return project(self.graph.poses[index], corners(self.size))

    def _points(self, bottles: list[Bottle]) -> tuple[np.ndarray, np.ndarray]:
        """The centres of the bottles in the current frame, and their vertical spans."""
        inverse = np.linalg.inv(self.H)
        into: dict[int, np.ndarray] = {}
        centres = np.zeros((len(bottles), 2))
        spans = np.zeros((len(bottles), 2))
        for k, bottle in enumerate(bottles):
            if bottle.anchor not in into:
                into[bottle.anchor] = inverse @ self.graph.poses[bottle.anchor]
            quad = project(into[bottle.anchor], bottle.quad)
            centres[k] = project(into[bottle.anchor], bottle.quad.mean(0, keepdims=True))[0]
            spans[k] = quad[:, 1].min(), quad[:, 1].max()
        return centres, spans

    def _tracked_points(self, bottles: list[Bottle]) -> tuple[np.ndarray, np.ndarray]:
        """The centres and vertical spans of the last boxes of the bottles, moved into the
        current frame. A bottle with no last box gets its map projection."""
        centres, spans = self._points(bottles)
        inverse = np.linalg.inv(self.M)
        for k, bottle in enumerate(bottles):
            if bottle.last_box is None:
                continue
            quad = project(inverse @ bottle.last_M, box_corners(bottle.last_box))
            centres[k] = quad.mean(0)
            spans[k] = quad[:, 1].min(), quad[:, 1].max()
        return centres, spans

    def _rows_of(self, boxes: list[Box]) -> list[list[int]]:
        """The rows of the boxes (box indices, by the bottom edge), each left to right."""
        height = self.bottle_height or 0.25 * self.size[1]
        order = sorted(range(len(boxes)), key=lambda i: boxes[i][3])
        rows: list[list[int]] = []
        for i in order:
            if rows and boxes[i][3] - boxes[rows[-1][-1]][3] <= self.cfg.row_gap * height:
                rows[-1].append(i)
            else:
                rows.append([i])
        return [sorted(row, key=lambda i: boxes[i][0] + boxes[i][2]) for row in rows]

    def _neighbours(self, boxes: list[Box]) -> dict[int, tuple[int | None, int | None]]:
        """The left and right neighbour (box indices) of each box in its row."""
        result: dict[int, tuple[int | None, int | None]] = {i: (None, None) for i in range(len(boxes))}
        centre = lambda i: (boxes[i][0] + boxes[i][2]) / 2
        for row in self._rows_of(boxes):
            for a, b in zip(row, row[1:]):
                width = max(boxes[a][2] - boxes[a][0], boxes[b][2] - boxes[b][0], 0.8 * self._width())
                if centre(b) - centre(a) <= self.cfg.adjacent_gap * width:
                    result[a] = (result[a][0], b)
                    result[b] = (a, result[b][1])
        return result

    def _place_confirmed(self, bottle: Bottle) -> bool:
        """Whether the frame has recently registered to the anchor keyframe of the bottle
        or to one at most `anchor_window` keyframes from it."""
        cfg = self.cfg
        return any(abs(bottle.anchor - k) <= cfg.anchor_window
                   and self.count - step <= cfg.trust_steps for k, step in self.verified.items())

    def _contradicted(self, bottle_id: int, left: int | None, right: int | None) -> bool:
        """Whether the habits of the neighbours (bottle ids) deny the bottle its place."""
        return ((left is not None and self._habit(self.right, left) not in (None, bottle_id))
                or (right is not None and self._habit(self.left, right) not in (None, bottle_id)))

    def _habit(self, table: dict[int, dict[int, int]], bottle: int) -> int | None:
        """The habitual neighbour of a bottle on one side, or None."""
        counts = table.get(bottle)
        if not counts:
            return None
        top, count = max(counts.items(), key=lambda item: item[1])
        if count >= self.cfg.habit_count and count >= self.cfg.habit_share * sum(counts.values()):
            return top
        return None

    def _rename(self, old: int, new: int) -> None:
        """Move the neighbour history of a merged bottle to the bottle it merged into."""
        for table in (self.right, self.left):
            counts = table.pop(old, {})
            mine = table.setdefault(new, {})
            for other, count in counts.items():
                if other != new:
                    mine[other] = mine.get(other, 0) + count
            for owner, counts in table.items():
                if old in counts:
                    count = counts.pop(old)
                    if owner != new:
                        counts[new] = counts.get(new, 0) + count

    def _width(self) -> float:
        return self.bottle_width or 0.1 * self.size[0]

    def _point_distance(self, boxes: list[Box], centres: np.ndarray,
                        spans: np.ndarray) -> np.ndarray:
        """The distances of boxes to bottle centres across the shelf, in widths of the box
        (at least 0.8 of the bottle width: a box cut or half hidden is narrow); inf where
        the centre is not in the row of the box."""
        distance = np.full((len(boxes), len(centres)), np.inf)
        if not len(centres):
            return distance
        for i, (x1, y1, x2, y2) in enumerate(boxes):
            middle = (y1 + y2) / 2
            row = ((centres[:, 1] >= y1) & (centres[:, 1] <= y2)
                   & (spans[:, 0] <= middle) & (spans[:, 1] >= middle))
            width = max(x2 - x1, 0.8 * self._width())
            distance[i, row] = np.abs(centres[row, 0] - (x1 + x2) / 2) / width
        return distance

    def _same_place(self, one: list[Bottle], two: list[Bottle]) -> np.ndarray:
        """The distances between two lists of bottles, as `_point_distance`, in bottle
        widths."""
        c1, s1 = self._points(one)
        c2, s2 = self._points(two)
        distance = np.full((len(one), len(two)), np.inf)
        for i in range(len(one)):
            row = ((c2[:, 1] >= s1[i, 0]) & (c2[:, 1] <= s1[i, 1])
                   & (s2[:, 0] <= c1[i, 1]) & (s2[:, 1] >= c1[i, 1]))
            distance[i, row] = np.abs(c2[row, 0] - c1[i, 0]) / self._width()
        return distance

    def _in_view(self, centres: np.ndarray, margin: float = 0.0) -> np.ndarray:
        w, h = self.size
        return ((centres[:, 0] >= -margin) & (centres[:, 0] < w + margin)
                & (centres[:, 1] >= -margin) & (centres[:, 1] < h + margin))

    def _local_quad(self, box: Box, anchor: int) -> np.ndarray:
        """The quadrilateral of a frame box in the pixels of keyframe `anchor`."""
        to_anchor = np.linalg.inv(self.graph.poses[anchor]) @ self.H
        return project(to_anchor, box_corners(box))

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
        whole = [d for d in detections if margin <= d.box[0] and d.box[2] <= self.size[0] - margin]
        self.dropped += len(detections) - len(whole)
        detections = whole
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

    def _registrations(self, features: FrameFeatures, candidates: list[int]):
        """Register the frame to each candidate keyframe. Return [(keyframe, R frame ->
        keyframe, strong)] of the good ones."""
        cfg = self.cfg
        good = []
        for index in candidates:
            points_k, points_f = match(self.keyframes[index].features, features, cfg.features)
            registration = self._register(points_k, points_f)
            if (registration.ok and registration.inliers >= cfg.min_loop_inliers
                    and registration.coverage >= cfg.min_loop_coverage):
                strong = (registration.inliers >= cfg.strong_inliers
                          and registration.coverage >= cfg.strong_coverage)
                good.append((index, registration.H, strong, registration.inliers))
                self.verified[index] = self.count
        return good

    def _relocalize(self, number: int, features: FrameFeatures) -> None:
        """Register the frame to the keyframes near its predicted place (the most
        overlapping first), make the best one the reference, and add loop edges between
        the keyframes that registered: an edge from two fresh registrations of one frame
        has no chain in it. An edge through the chain P is added only while P is fresh."""
        cfg = self.cfg
        quad = self._quad()
        centre = quad.mean(0)
        width = float(np.linalg.norm(quad[1] - quad[0]))
        candidates = []
        for index in range(len(self.keyframes)):
            other = self._keyframe_quad(index)
            if np.linalg.norm(other.mean(0) - centre) <= cfg.search_radius * width:
                candidates.append((_shared(quad, other), index))
        order = [index for _, index in sorted(candidates, reverse=True)[:cfg.loop_candidates]]
        order += [k for k in sorted(self.wanted) if k not in order][:cfg.loop_candidates]
        self.wanted = set()
        good = self._registrations(features, order)
        if not good:
            return
        best, R_best, strong_best, _ = max(good, key=lambda g: g[3])
        edges = []
        for index, R, strong, _ in good:
            if index != best:
                T = R @ np.linalg.inv(R_best)          # keyframe best -> keyframe index
                edges.append((Edge(index, best, T / T[2, 2], cfg.loop_weight, "loop"),
                              strong and strong_best))
        if self.ref not in [g[0] for g in good] and self.count - self.anchored <= cfg.fresh_steps:
            T = R_best @ np.linalg.inv(self.P)         # old reference -> keyframe best
            edges.append((Edge(best, self.ref, T / T[2, 2], cfg.chain_weight, "chain"),
                          strong_best))
        worst = 0.0
        for edge, strong in edges:
            error = self.graph.error(edge) / self.size[0]
            if error > cfg.max_jump or (error > cfg.small_correction and not strong):
                continue
            self.graph.replace(edge)
            worst = max(worst, error)
        self.ref, self.P = best, R_best
        self.anchored = self.localized = self.count
        self.corrections.append((number, worst))
        if worst * self.size[0] > cfg.optimize_above:
            before, after, dropped = self.graph.optimize_robust()
            self.dropped_edges += dropped
            merged = self._merge_duplicates()
            self.loops.append((number, worst, before, after, merged))

    def _merge_duplicates(self) -> int:
        """After an optimisation, merge the bottles that now stand on one place: a later
        bottle into the earlier one, which keeps its id. A duplicate starts after its
        original was last seen; two bottles seen together are two bottles (neighbours MAY
        land close after an optimisation)."""
        cfg = self.cfg
        centres, _ = self._points(self.bottles)
        seen = [b for b, inside in zip(self.bottles, self._in_view(centres)) if inside]
        if len(seen) < 2:
            return 0
        distance = self._same_place(seen, seen)
        pairs = []
        for a, one in enumerate(seen):
            for b, two in enumerate(seen):
                if (one.id < two.id and distance[a, b] <= cfg.merge_distance
                        and two.first_step > one.last_seen and self._place_confirmed(one)):
                    pairs.append((distance[a, b], a, b))
        gone: set[int] = set()
        for _, a, b in sorted(pairs):
            if seen[a].id in gone or seen[b].id in gone:
                continue
            self._absorb(seen[a], seen[b])
            self._rename(seen[b].id, seen[a].id)
            gone.add(seen[b].id)
        self.bottles = [b for b in self.bottles if b.id not in gone]
        return len(gone)

    def _absorb(self, earlier: Bottle, later: Bottle) -> None:
        """Make `earlier` take the place of its duplicate `later`."""
        if later.last_seen > earlier.last_seen:
            if earlier.left or self.count - earlier.last_seen > self.cfg.track_gap:
                earlier.appearance += 1
            earlier.left = later.left
            earlier.last_seen = later.last_seen

    def _needs_keyframe(self) -> bool:
        """A keyframe where no keyframe covers the frame enough, and only where the place
        of the frame is trusted."""
        if not self.keyframes:
            return True
        quad = self._quad()
        return self.trusted and max(_shared(quad, self._keyframe_quad(k))
                                    for k in range(len(self.keyframes))) < self.cfg.keyframe_overlap

    def _add_keyframe(self, number: int, features: FrameFeatures) -> None:
        """The frame becomes a keyframe and the reference. Its edge from the old reference
        is a direct registration of the two keyframes when they register (no chain in
        it); else the chain P since the old reference, with less weight."""
        cfg = self.cfg
        T, weight, kind = self.P.copy(), cfg.chain_weight, "chain"
        if self.ref is not None:
            good = self._registrations(features, [self.ref])
            if good:
                T, weight, kind = good[0][1], cfg.loop_weight, "odometry"
        pose = T if self.ref is None else self.graph.poses[self.ref] @ T
        index = self.graph.add(pose)
        self.keyframes.append(Keyframe(number, self.count, features))
        if self.ref is not None:
            self.graph.connect(self.ref, index, T, weight, kind)
        self.ref, self.P = index, np.eye(3)
        self.anchored = self.count
        self.verified[index] = self.count

    def _jump(self) -> None:
        """The place of the frame is lost (see `max_wait`)."""
        self.lost = True
        self.lost_steps = 0
        self.jumps += 1
        self.anchored = self.localized = -10 ** 9   # P is no chain of motions any more
        self.verified = {}
        self.wanted = set()
        self.need_registration = False
        for bottle in self.bottles:
            bottle.left = True

    def _find(self, number: int, features: FrameFeatures) -> None:
        """Look for the lost frame among all the keyframes; after `max_wait` lost steps
        the place is new ground."""
        cfg = self.cfg
        verified = dict(self.verified)
        good = [g for g in self._registrations(features, list(range(len(self.keyframes))))
                if g[2]]
        if good:
            best, R, _, _ = max(good, key=lambda g: g[3])
            self.ref, self.P = best, R
            self.anchored = self.localized = self.count
            self.lost = False
            self.found += 1
            return
        self.verified = verified
        self.lost_steps += 1
        if self.lost_steps > cfg.max_wait:
            # New ground: a keyframe of its own, to the right of the whole map.
            right = max(self._keyframe_quad(k)[:, 0].max() for k in range(len(self.keyframes)))
            index = self.graph.add(np.array([[1, 0, right + self.size[0]], [0, 1, 0], [0, 0, 1]], float))
            self.keyframes.append(Keyframe(number, self.count, features))
            self.ref, self.P = index, np.eye(3)
            self.anchored = self.localized = self.count
            self.verified[index] = self.count
            self.lost = False
            self.new_grounds += 1

    def _near_old_keyframe(self) -> bool:
        """Whether an old keyframe (not of this visit) lies near the predicted place."""
        cfg = self.cfg
        quad = self._quad()
        centre = quad.mean(0)
        width = float(np.linalg.norm(quad[1] - quad[0]))
        return any(self.count - kf.step > cfg.recent_steps
                   and np.linalg.norm(self._keyframe_quad(k).mean(0) - centre)
                   <= cfg.search_radius * width
                   for k, kf in enumerate(self.keyframes))

    def _trusted(self) -> bool:
        """Whether the place of the frame is trusted (see `trust_steps`)."""
        cfg = self.cfg
        if self.lost:
            return False
        if self.count - self.localized <= cfg.trust_steps or not self._near_old_keyframe():
            self.untrusted = 0
            return True
        self.untrusted += 1
        return self.untrusted > cfg.max_wait

    # ------------------------------------------------------------------ association

    def _associate(self, number: int, detections: list[Detection],
                   trusted: bool = True) -> list[Shown]:
        cfg = self.cfg
        centres, spans = self._points(self.bottles)
        in_view = self._in_view(centres)
        tracked = [k for k, b in enumerate(self.bottles)
                   if in_view[k] and not b.left and self.count - b.last_seen <= cfg.track_gap]
        confirmed = {k for k, step in self.verified.items()
                     if self.count - step <= cfg.trust_steps}
        old = [k for k, b in enumerate(self.bottles) if in_view[k] and k not in set(tracked)]
        near = [k for k in old
                if any(abs(self.bottles[k].anchor - c) <= cfg.anchor_window for c in confirmed)]
        unconfirmed = [k for k in old if k not in set(near)]
        boxes = [d.box for d in detections]

        def assign(pool, free, limit, points=(centres, spans)):
            if not pool or not free:
                return {}
            distance = self._point_distance([boxes[i] for i in free], points[0][pool],
                                            points[1][pool])
            return {free[i]: pool[j] for i, j in hungarian(distance, limit).items()}

        free = list(range(len(detections)))
        last = self._tracked_points(self.bottles)
        first = assign(tracked, free, cfg.track_distance, last)
        first.update(self._rescue(boxes, [i for i in free if i not in first],
                                  [k for k in tracked if k not in first.values()], first, last))
        # A box cut by the top or bottom of the frame is not re-identified: it waits to be
        # whole.
        free = [i for i in free if i not in first and not self._cut(boxes[i])]
        second = assign(near, free, cfg.reid_distance) if trusted else {}
        matched = {**first, **second}
        # A box at the place of an old bottle whose place the frame has not confirmed yet
        # waits (no new bottle) and asks for a registration; after `max_wait` such steps in
        # a row it starts a bottle: the place is new after all.
        free = [i for i in free if i not in second]
        maybe = assign(unconfirmed, free, cfg.reid_distance) if trusted else {}
        waiting = set(maybe)
        self.wanted |= {self.bottles[k].anchor for k in maybe.values()}
        self.waited = self.waited + 1 if waiting else 0
        if self.waited > cfg.max_wait:
            waiting = set()
        if waiting:
            self.need_registration = True

        neighbours = self._neighbours(boxes)
        ids = {i: self.bottles[k].id for i, k in matched.items()}
        # Veto the re-identifications that the history of the neighbours contradicts.
        for i, k in second.items():
            left, right = neighbours[i]
            if self._contradicted(ids[i], ids.get(left), ids.get(right)):
                del matched[i], ids[i]
                self.vetoed += 1
        # Suggest the habitual neighbours of the neighbours to the boxes left over.
        index_of = {b.id: k for k, b in enumerate(self.bottles)}
        for _ in range(3):
            taken = set(matched.values())
            changed = False
            for i in range(len(detections)):
                if i in matched or self._cut(boxes[i]):
                    continue
                left, right = neighbours[i]
                from_left = self._habit(self.right, ids[left]) if left in ids else None
                from_right = self._habit(self.left, ids[right]) if right in ids else None
                if from_left is not None and from_right is not None and from_left != from_right:
                    continue
                suggestion = from_left if from_left is not None else from_right
                k = index_of.get(suggestion)
                x1, _, x2, _ = boxes[i]
                if (k is None or k in taken or abs(centres[k][0] - (x1 + x2) / 2)
                        > cfg.habit_reach * self._width()):
                    continue
                matched[i], ids[i] = k, suggestion
                taken.add(k)
                waiting.discard(i)
                self.suggested += 1
                changed = True
            if not changed:
                break
        # Check every row against the labels of its boxes; the boxes left free take the
        # released bottles by place.
        released = set() if self.lost else self._check_rows(number, boxes, matched, centres, spans)
        if released:
            owned = set(matched.values())
            free = [i for i in range(len(detections)) if i not in matched and not self._cut(boxes[i])]
            pool = sorted(released | {k for k in near if k not in owned})
            matched.update(assign([k for k in pool if k not in owned], free, cfg.reid_distance))
            ids = {i: self.bottles[k].id for i, k in matched.items()}
            waiting -= set(matched)
        conflicts, closed = self._conflicts(boxes, matched, ids, neighbours, centres, spans,
                                            in_view)

        shown = []
        count_before = len(self.bottles)
        for i, det in enumerate(detections):
            cut = self._cut(det.box)
            if i in matched:
                bottle = self.bottles[matched[i]]
                if bottle.left:
                    bottle.appearance += 1
                    bottle.left = False
                bottle.last_seen = self.count
                bottle.last_box, bottle.last_M = boxes[i], self.M.copy()
                if not cut and bottle.hits < cfg.settle_hits:
                    self._observe(bottle, det.box)
                status = "new" if bottle.appearance == 1 else "returning"
                shown.append(Shown(det.box, status, bottle.id))
            elif i in closed:
                shown.append(Shown(det.box, "ignored"))
            elif not cut and det.score >= cfg.new_score and (not trusted or i in waiting
                                                             or i in conflicts):
                shown.append(Shown(det.box, "pending"))
            elif not cut and det.score >= cfg.new_score:
                bottle = Bottle(self.next_id, self.ref, project(self.P, box_corners(det.box)),
                                number, self.count, first_step=self.count,
                                last_box=det.box, last_M=self.M.copy())
                self.next_id += 1
                self.bottles.append(bottle)
                shown.append(Shown(det.box, "new", bottle.id))
            else:
                shown.append(Shown(det.box, "ignored"))

        # A bottle whose centre is now clearly outside the frame has left the view. The
        # bottles that this frame started are in view.
        inside = self._in_view(centres, cfg.leave_margin * self._width())
        for k in range(count_before):
            if not inside[k]:
                self.bottles[k].left = True
        shown = self._merge_young(shown, neighbours)
        for i, (_, right) in neighbours.items():
            a, b = shown[i].bottle, shown[right].bottle if right is not None else None
            if a is not None and b is not None and a != b:
                self.right.setdefault(a, {})[b] = self.right.get(a, {}).get(b, 0) + 1
                self.left.setdefault(b, {})[a] = self.left.get(b, {}).get(a, 0) + 1
        return shown

    def _box_descriptors(self, features: FrameFeatures | None, boxes: list[Box]) -> list:
        """The descriptors of the keypoints inside each box (None for a cut box)."""
        out: list = [None] * len(boxes)
        if features is None or features.descriptors is None or not len(features.points):
            return out
        x, y = features.points[:, 0], features.points[:, 1]
        for i, (x1, y1, x2, y2) in enumerate(boxes):
            if not self._cut(boxes[i]):
                out[i] = features.descriptors[(x >= x1) & (x <= x2) & (y >= y1) & (y <= y2)]
        return out

    def _label_votes(self, descriptors: list, boxes: list[Box]) -> dict[int, dict[int, int]]:
        """The votes of the descriptors of each box for the labels of the bottles of the
        map near it (see `label_views`): box -> {bottle index: votes}."""
        cfg = self.cfg
        out: dict[int, dict[int, int]] = {}
        labelled = [k for k, b in enumerate(self.bottles) if b.label]
        if not labelled or not any(d is not None and len(d) for d in descriptors):
            return out
        centres, _ = self._points(self.bottles)
        width = self._width()
        height = self.bottle_height or 0.25 * self.size[1]
        matcher = cv2.BFMatcher(cv2.NORM_L2)
        for i, query in enumerate(descriptors):
            if query is None or len(query) < cfg.label_votes:
                continue
            x1, y1, x2, y2 = boxes[i]
            near = [k for k in labelled
                    if abs(centres[k, 0] - (x1 + x2) / 2) <= cfg.label_reach * width
                    and abs(centres[k, 1] - (y1 + y2) / 2) <= 0.5 * height]
            if not near:
                continue
            train = np.concatenate([np.concatenate(self.bottles[k].label) for k in near])
            owner = np.concatenate([np.full(sum(len(v) for v in self.bottles[k].label), k)
                                    for k in near])
            votes: dict[int, int] = {}
            for candidates in matcher.knnMatch(query, train, k=min(8, len(train))):
                if not candidates:
                    continue
                best = candidates[0]
                other = next((m for m in candidates[1:]
                              if owner[m.trainIdx] != owner[best.trainIdx]), None)
                if other is None or best.distance < cfg.label_ratio * other.distance:
                    k = int(owner[best.trainIdx])
                    votes[k] = votes.get(k, 0) + 1
            out[i] = votes
        return out

    def _says(self, votes: dict[int, int] | None) -> int | None:
        """The bottle that the label of a box names, if any (see `label_votes`)."""
        if not votes:
            return None
        ranked = sorted(votes.values(), reverse=True)
        best = max(votes, key=votes.get)
        if ranked[0] >= self.cfg.label_votes and (
                len(ranked) == 1 or ranked[0] >= self.cfg.label_margin * ranked[1]):
            return best
        return None

    def _twins(self, a: int, b: int) -> bool:
        """Whether the labels of bottles a and b (indices) are of one wine (see
        `label_twins`)."""
        one, two = self.bottles[a].label, self.bottles[b].label
        if not one or not two:
            return False
        one, two = np.concatenate(one), np.concatenate(two)
        matcher = cv2.BFMatcher(cv2.NORM_L2)

        def share(x, y):
            pairs = matcher.knnMatch(x, y, k=2)
            good = sum(len(c) == 2 and c[0].distance < self.cfg.label_ratio * c[1].distance
                       for c in pairs)
            return good / max(len(x), 1)

        return min(share(one, two), share(two, one)) >= self.cfg.label_twins

    def _check_rows(self, number: int, boxes: list[Box], matched: dict[int, int],
                    centres: np.ndarray, spans: np.ndarray) -> set[int]:
        """The check of the rows (see `label_fix`). Change `matched` in place; return the
        bottles released by the boxes that took other bottles."""
        cfg = self.cfg
        votes = self.votes
        width = self._width()
        height = self.bottle_height or 0.25 * self.size[1]
        says = {i: self._says(v) for i, v in votes.items() if not self._cut(boxes[i])}
        for i, k in matched.items():
            if i in votes and self.bottles[k].label:
                self.label_checks += 1
                self.label_confirmed += says.get(i) == k
        middle = lambda i: np.array([(boxes[i][0] + boxes[i][2]) / 2, (boxes[i][1] + boxes[i][3]) / 2])
        released: set[int] = set()

        def log(i, k, outcome):
            held = matched.get(i)
            self.contradictions.append((
                number, i, None if held is None else self.bottles[held].id, self.bottles[k].id,
                votes.get(i, {}).get(k, 0), 0 if held is None else votes.get(i, {}).get(held, 0),
                outcome))

        for row in self._rows_of(boxes):
            named = Counter(says[i] for i in row if says.get(i) is not None)
            confirmed = {i for i in row if says.get(i) is not None and matched.get(i) == says[i]}
            kept = {matched[i] for i in confirmed}
            anchors = {}
            for i in row:
                k, held = says.get(i), matched.get(i)
                if k is None or named[k] > 1 or (held is not None and held != k and (
                        not self.bottles[held].label or self._twins(held, k))):
                    continue
                anchors[i] = k
            if all(matched.get(i) == k for i, k in anchors.items()):
                continue                      # the labels of the row agree with its ids
            shifts = {i: middle(i) - centres[k] for i, k in anchors.items()}

            def agreeing(i):
                return [j for j in shifts
                        if abs(shifts[j][0] - shifts[i][0]) <= cfg.label_tolerance * width
                        and abs(shifts[j][1] - shifts[i][1]) <= 0.3 * height]

            best = max(shifts, key=lambda i: (len(agreeing(i)),
                                              sum(matched.get(j) == anchors[j] for j in agreeing(i))))
            group = agreeing(best)
            wrong = [i for i in group if matched.get(i) != anchors[i]]
            outvoted = [i for i in anchors if i not in group and matched.get(i) != anchors[i]]
            for i in outvoted:
                log(i, anchors[i], "outvoted")
            if not wrong:
                continue
            if len(group) < cfg.label_support:
                for i in wrong:
                    log(i, anchors[i], "lone")
                continue
            shift = np.median([shifts[i] for i in group], axis=0)
            target = {i: anchors[i] for i in group}
            keyframes = {self.bottles[k].anchor for k in target.values()}
            others = [i for i in row if i not in target and i not in confirmed
                      and not self._cut(boxes[i])]
            pool = [k for k, b in enumerate(self.bottles)
                    if k not in set(target.values()) and k not in kept
                    and any(abs(b.anchor - a) <= cfg.anchor_window for a in keyframes)]
            if others and pool:
                distance = self._point_distance([boxes[i] for i in others], centres[pool] + shift,
                                                spans[pool] + shift[1])
                target.update({others[a]: pool[b]
                               for a, b in hungarian(distance, cfg.reid_distance).items()})
            changes = [i for i in row if i in target and matched.get(i) != target[i]
                       and i not in confirmed and target[i] not in kept - {matched.get(i)}]
            for i in changes:
                log(i, target[i], "fixed" if cfg.label_fix else "logged")
            if not cfg.label_fix:
                continue
            owner = {k: j for j, k in matched.items()}
            for i in changes:
                k = target[i]
                holder = owner.get(k)
                if holder is not None and holder not in target:
                    del matched[holder]       # the box loses its bottle
                held = matched.get(i)
                if held is not None and held not in target.values():
                    released.add(held)
                matched[i] = k
                owner[k] = i
                released.discard(k)
        return released

    def _learn_labels(self, shown: list[Shown], descriptors: list) -> None:
        """Keep the label of each bottle from its first whole views (see `label_views`)."""
        cfg = self.cfg
        index_of = {b.id: k for k, b in enumerate(self.bottles)}
        for item, query in zip(shown, descriptors):
            k = index_of.get(item.bottle)
            if k is None or query is None or not len(query):
                continue
            bottle = self.bottles[k]
            if (bottle.appearance == 1 and len(bottle.label) < cfg.label_views
                    and self.count - bottle.labelled >= cfg.label_gap):
                bottle.label.append(query[:cfg.label_size])
                bottle.labelled = self.count

    def _conflicts(self, boxes: list[Box], matched: dict[int, int], ids: dict[int, int],
                   neighbours: dict, centres: np.ndarray, spans: np.ndarray,
                   in_view: np.ndarray) -> tuple[set[int], set[int]]:
        """The boxes left without a bottle that a new bottle would put in conflict with the
        map. A box between two bottles that are habitual neighbours of each other is
        closed: the map has no place between them (90 s: a bottle deep in the gap between
        69 and 68). A box that stands on the place of a bottle (within `reid_distance`), or
        where the habitual neighbour of its neighbour stands, while another box of the
        frame has taken that bottle, is in conflict: it waits, and after `max_wait` steps
        in a row with conflicts it starts a bottle (the map MAY be wrong there)."""
        cfg = self.cfg
        owner = {k: i for i, k in matched.items()}
        index_of = {b.id: k for k, b in enumerate(self.bottles)}
        free = [i for i in range(len(boxes)) if i not in matched and not self._cut(boxes[i])]
        conflicts, closed = set(), set()
        for i in free:
            left, right = neighbours[i]
            if (left in ids and right in ids
                    and (self._habit(self.right, ids[left]) == ids[right]
                         or self._habit(self.left, ids[right]) == ids[left])):
                closed.add(i)
        free = [i for i in free if i not in closed]
        if free and owner:
            distance = self._point_distance([boxes[i] for i in free], centres, spans)
            for a, i in enumerate(free):
                on = [int(k) for k in np.flatnonzero(distance[a] <= cfg.reid_distance) if in_view[k]]
                left, right = neighbours[i]
                for table, side in ((self.right, left), (self.left, right)):
                    habit = self._habit(table, ids[side]) if side in ids else None
                    if habit in index_of:
                        on.append(index_of[habit])
                if any(k in owner and owner[k] != i for k in on):
                    conflicts.add(i)
        self.conflicted = self.conflicted + 1 if conflicts else 0
        if self.conflicted > cfg.max_wait:
            conflicts = set()
        self.conflicts += len(conflicts)
        self.closed += len(closed)
        return conflicts, closed

    def _rescue(self, boxes: list[Box], free: list[int], lost: list[int],
                matched: dict[int, int], points: tuple[np.ndarray, np.ndarray]) -> dict[int, int]:
        """The neighbour rescue (see `rescue_radius`): match the lost tracked bottles to
        the free boxes at their predictions moved by the offsets of the matched bottles
        around them. The row test is lenient: the box of a bottle MAY have grown or shrunk
        (a neck behind it in or out)."""
        cfg = self.cfg
        if not free or not lost or len(matched) < cfg.rescue_support:
            return {}
        centres, _ = points
        width = self._width()
        pairs = [(k, np.array([(boxes[i][0] + boxes[i][2]) / 2, (boxes[i][1] + boxes[i][3]) / 2])
                  - centres[k]) for i, k in matched.items()]
        distance = np.full((len(free), len(lost)), np.inf)
        for b, k in enumerate(lost):
            near = [offset for m, offset in pairs
                    if np.linalg.norm(centres[m] - centres[k]) <= cfg.rescue_radius * width]
            if len(near) < cfg.rescue_support:
                continue
            x, y = centres[k] + np.median(near, axis=0)
            for a, i in enumerate(free):
                x1, y1, x2, y2 = boxes[i]
                slack = 0.25 * (y2 - y1)
                if y1 - slack <= y <= y2 + slack:
                    distance[a, b] = abs((x1 + x2) / 2 - x) / max(x2 - x1, 0.8 * width)
        found = {free[a]: lost[b] for a, b in hungarian(distance, cfg.rescue_distance).items()}
        self.rescued += len(found)
        return found

    def _merge_young(self, shown: list[Shown], neighbours: dict) -> list[Shown]:
        """Merge the young bottles that stand where an older bottle stands (see
        `young_steps`). Two bottles both detected now, or seen together before, are two.
        The older bottle passes the tests of a re-identification: its place is confirmed,
        and the neighbours of the young one do not deny it (an unchecked merge gave the
        first frame's bottle 18 to a box next to 108 at 36.7 s)."""
        cfg = self.cfg
        # Not the bottles of this step: the association has just refused them an old bottle.
        young = [b for b in self.bottles if 0 < self.count - b.first_step <= cfg.young_steps]
        old = [b for b in self.bottles if self.count - b.first_step > cfg.young_steps
               and self._place_confirmed(b)]
        at = {item.bottle: i for i, item in enumerate(shown) if item.bottle is not None}
        def sides(bottle_id):
            i = at.get(bottle_id)
            if i is None:
                return None, None
            left, right = neighbours.get(i, (None, None))
            return (shown[left].bottle if left is not None else None,
                    shown[right].bottle if right is not None else None)
        if not young or not old:
            return shown
        distance = self._same_place(young, old)
        detected = {s.bottle for s in shown if s.bottle is not None}
        for i, a in enumerate(young):
            for j, b in enumerate(old):
                if ((a.id in detected and b.id in detected) or a.first_step <= b.last_seen
                        or self._contradicted(b.id, *sides(a.id))):
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
        for young_id, target in into.items():
            self._rename(young_id, target.id)
        self.merged_young += len(into)
        return shown

    def _observe(self, bottle: Bottle, box: Box) -> None:
        weight = 1.0 / (bottle.hits + 1)
        bottle.quad = (1 - weight) * bottle.quad + weight * self._local_quad(box, bottle.anchor)
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
                self._jump()
            else:
                self.P = self.P @ H_step
                self.M = self.M @ H_step
        times["motion"] = perf_counter() - started

        started = perf_counter()
        features = None
        if not self.keyframes:                # the first frame anchors the map
            features = self._features(frame, detections)
            self._add_keyframe(number, features)
        elif self.lost:
            features = self._features(frame, detections)
            self._find(number, features)
        elif self.count % cfg.reloc_every == 0 or not self.trusted or self.need_registration:
            self.need_registration = False
            features = self._features(frame, detections)
            self._relocalize(number, features)
        times["relocalize"] = perf_counter() - started

        started = perf_counter()
        descriptors = self._box_descriptors(features, [d.box for d in detections])
        self.votes = {} if self.lost else self._label_votes(descriptors, [d.box for d in detections])
        times["labels"] = perf_counter() - started

        started = perf_counter()
        self.trusted = self._trusted()
        shown = self._associate(number, detections, self.trusted)
        self._learn_labels(shown, descriptors)
        times["associate"] = perf_counter() - started

        started = perf_counter()
        if self._needs_keyframe():
            self._add_keyframe(number, features or self._features(frame, detections))
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
