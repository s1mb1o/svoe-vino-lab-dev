"""The stream tracker in two loops, as on a phone: a fast loop each frame and a slow loop in
the background. The synchronous tracker (stream.py) stays the reference.

The fast loop, each frame: the optical flow, the tracks, the boxes against the map (the
poses of the keyframes and the places of the bottles as the slow loop left them), the
habits and the conflicts, new and waiting boxes. It never registers a frame.

The slow loop takes one frame at a time (a snapshot: the image, the boxes and their ids,
the pose, and the chain of motions M of that frame t), when it is free and the frame asks
for it (every `reloc_every` steps, an untrusted or lost place, waiting boxes, a keyframe
due). It computes the keypoints, the registrations to the keyframes, the keyframe of the
frame, the labels, and the check of the rows, all on the state of frame t. Its result
lands `latency` steps later (a background thread of bounded latency, made deterministic
for tests):

- the pose: a registration R of frame t moves to the current frame along the motions since,
  P = R · M(t)⁻¹ · M(now);
- the graph with the loop edges, optimised in the slow loop on a copy (the fast loop does
  not change the graph while a result is in flight), and the merge of duplicates;
- the keyframe of frame t, which becomes the reference: P = M(t)⁻¹ · M(now);
- the confirmations of keyframes, stamped with t;
- the labels learnt on frame t;
- the corrections of the check of the rows, as tracks: the bottle a box should carry takes
  over the track of the bottle the box carried at t (its last box and motion), and the
  bottle the box carried loses its track; a young bottle that loses its track so (started
  within `young_steps` of frame t) and that no box should carry is a false new one of the
  latency, and joins the bottle that took its track (at 39 s, 61 s and 67 s of 115611 the
  fast loop started 109-116, 124-127 and 128-130 for bottles of the first visit while the
  check of their rows was in flight).

A new bottle is provisional until a slow result has seen it: the fast loop starts it and
tracks it, but shows it waiting (white), and the check of the rows treats its box as a box
with no bottle, as the synchronous tracker does in the frame where it would start it. When
the result lands, a provisional bottle that the labels named an older bottle joins it, and
the others become new (green). Without this the fast loop started bottles for a row of the
first visit (39 s of 115611: 109-112 for 24-32, whose places in the map lay two bottles
off), and the check passed them over: a box whose bottle has no label yet is not checked.
A frame with provisional bottles in view asks for the slow loop.

A jump (the flow fails) drops the results in flight: their frames lie before the jump.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from time import perf_counter

import cv2
import numpy as np

from .features import FrameFeatures, match
from .homography import corners, project
from .posegraph import Edge
from .stream import Keyframe, ShelfTracker, Shown, StreamConfig, _shared
from .types import Detection


@dataclass
class Snapshot:
    number: int
    count: int
    frame: np.ndarray
    detections: list[Detection]
    shown: list[Shown]
    ref: int
    P: np.ndarray
    M: np.ndarray
    anchored: int
    lost: bool
    trusted: bool
    wanted: set[int]


@dataclass
class SlowResult:
    due: int
    snap: Snapshot
    found: tuple[int, np.ndarray] | None = None        # keyframe, R: frame t -> keyframe
    good: list[int] = field(default_factory=list)       # the keyframes that registered
    edges: list[tuple[Edge, bool]] = field(default_factory=list)
    graph: object | None = None                         # the graph with the edges, optimised
    worst: float = 0.0
    optimised: tuple | None = None                      # (before, after, dropped)
    new_ground: bool = False
    keyframe: tuple | None = None                       # features, ref, T, weight, kind
    labels: list[tuple[int, np.ndarray]] = field(default_factory=list)   # bottle id, descriptors
    moves: list[tuple[int, int | None, int]] = field(default_factory=list)  # box, id held at t, id due
    confirmed: set[int] = field(default_factory=set)    # provisional bottles seen and kept
    seconds: float = 0.0


class RealtimeTracker(ShelfTracker):
    def __init__(self, size: tuple[int, int], cfg: StreamConfig = StreamConfig(), latency: int = 3):
        super().__init__(size, cfg)
        self.latency = latency
        self.inflight: SlowResult | None = None
        self.lost_since = 0
        self.provisional: set[int] = set()        # bottle ids no slow result has seen yet
        self.clock = {"fast": [], "slow": []}

    # ------------------------------------------------------------------ the fast loop

    def step(self, number: int, frame: np.ndarray, detections: list[Detection]) -> list[Shown]:
        cfg = self.cfg
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
                self.lost_since = self.count
                self.inflight = None              # its frame lies before the jump
            else:
                self.P = self.P @ H_step
                self.M = self.M @ H_step
        if not self.keyframes:                    # the first frame anchors the map at once
            self._add_keyframe(number, self._features(frame, detections))
        self._land()
        self.trusted = self._trusted()
        self.votes = {}                           # the labels are the slow loop's
        before = self.next_id
        shown = self._associate(number, detections, self.trusted)
        self.provisional |= set(range(before, self.next_id))
        self.provisional &= {b.id for b in self.bottles}
        for item in shown:
            if item.bottle in self.provisional:
                item.status = "pending"
        self.previous = (gray, [d.box for d in detections])
        self.poses[number] = self.H.copy()
        self.clock["fast"].append(perf_counter() - started)
        if self.inflight is None and self._asks():
            snap = Snapshot(number, self.count, frame, detections, shown, self.ref, self.P.copy(),
                            self.M.copy(), self.anchored, self.lost, self.trusted, set(self.wanted))
            self.wanted = set()
            self.need_registration = False
            started = perf_counter()
            self.inflight = self._slow(snap)
            self.inflight.seconds = perf_counter() - started
            self.clock["slow"].append(self.inflight.seconds)
        self.count += 1
        if self.latency == 0:
            self._land()
        return shown

    def _asks(self) -> bool:
        return (self.lost or not self.trusted or self.need_registration or bool(self.provisional)
                or self.count % self.cfg.reloc_every == 0 or self._needs_keyframe())

    def _land(self) -> None:
        """Apply the result in flight when it is due."""
        result = self.inflight
        if result is None or result.due > self.count:
            return
        self.inflight = None
        self._apply(result)

    # ------------------------------------------------------------------ the slow loop

    def _register_to(self, features: FrameFeatures, index: int):
        cfg = self.cfg
        points_k, points_f = match(self.keyframes[index].features, features, cfg.features)
        registration = self._register(points_k, points_f)
        if not (registration.ok and registration.inliers >= cfg.min_loop_inliers
                and registration.coverage >= cfg.min_loop_coverage):
            return None
        strong = (registration.inliers >= cfg.strong_inliers
                  and registration.coverage >= cfg.strong_coverage)
        return index, registration.H, strong, registration.inliers

    def _slow(self, snap: Snapshot) -> SlowResult:
        """Everything of frame t that needs its keypoints, on the state of frame t."""
        cfg = self.cfg
        result = SlowResult(snap.count + self.latency, snap)
        features = self._features(snap.frame, snap.detections)
        H_t = self.graph.poses[snap.ref] @ snap.P
        if snap.lost:
            order = list(range(len(self.keyframes)))
        else:
            quad = project(H_t, corners(self.size))
            centre = quad.mean(0)
            width = float(np.linalg.norm(quad[1] - quad[0]))
            candidates = [(_shared(quad, self._keyframe_quad(k)), k) for k in range(len(self.keyframes))
                          if np.linalg.norm(self._keyframe_quad(k).mean(0) - centre)
                          <= cfg.search_radius * width]
            order = [k for _, k in sorted(candidates, reverse=True)[:cfg.loop_candidates]]
            order += [k for k in sorted(snap.wanted) if k not in order][:cfg.loop_candidates]
        good = [g for g in (self._register_to(features, k) for k in order) if g is not None]
        if snap.lost:
            good = [g for g in good if g[2]]
        result.good = [g[0] for g in good]
        if good:
            best, R_best, strong_best, _ = max(good, key=lambda g: g[3])
            result.found = (best, R_best)
            if not snap.lost:
                for index, R, strong, _ in good:
                    if index != best:
                        T = R @ np.linalg.inv(R_best)
                        result.edges.append((Edge(index, best, T / T[2, 2], cfg.loop_weight, "loop"),
                                             strong and strong_best))
                if snap.ref not in result.good and snap.count - snap.anchored <= cfg.fresh_steps:
                    T = R_best @ np.linalg.inv(snap.P)
                    result.edges.append((Edge(best, snap.ref, T / T[2, 2], cfg.chain_weight, "chain"),
                                         strong_best))
        elif snap.lost:
            result.new_ground = snap.count - self.lost_since > cfg.max_wait
        if result.edges:
            graph = copy.deepcopy(self.graph)
            for edge, strong in result.edges:
                error = graph.error(edge) / self.size[0]
                if error > cfg.max_jump or (error > cfg.small_correction and not strong):
                    continue
                graph.replace(edge)
                result.worst = max(result.worst, error)
            if result.worst * self.size[0] > cfg.optimize_above:
                result.optimised = graph.optimize_robust()
            result.graph = graph
        # The pose of frame t as this result leaves it, for the keyframe and the labels.
        ref, P = (result.found if result.found else (snap.ref, snap.P))
        saved = self.ref, self.P, self.trusted
        self.ref, self.P, self.trusted = ref, P, snap.trusted and not snap.lost
        try:
            if not snap.lost and self._needs_keyframe():
                if result.found:
                    T, weight, kind = result.found[1], cfg.loop_weight, "odometry"
                else:
                    direct = self._register_to(features, snap.ref)
                    T, weight, kind = ((direct[1], cfg.loop_weight, "odometry") if direct
                                       else (snap.P.copy(), cfg.chain_weight, "chain"))
                result.keyframe = (features, ref, T, weight, kind)
            if not snap.lost:
                self._slow_labels(snap, features, result)
        finally:
            self.ref, self.P, self.trusted = saved
        if result.new_ground:
            result.keyframe = (features, None, None, 0.0, "new ground")
        return result

    def _slow_labels(self, snap: Snapshot, features: FrameFeatures, result: SlowResult) -> None:
        cfg = self.cfg
        boxes = [d.box for d in snap.detections]
        descriptors = self._box_descriptors(features, boxes)
        index_of = {b.id: k for k, b in enumerate(self.bottles)}
        for item, query in zip(snap.shown, descriptors):
            k = index_of.get(item.bottle)
            if k is None or query is None or not len(query) or item.bottle in self.provisional:
                continue
            bottle = self.bottles[k]
            if (bottle.appearance == 1 and len(bottle.label) < cfg.label_views
                    and snap.count - bottle.labelled >= cfg.label_gap):
                result.labels.append((bottle.id, query[:cfg.label_size]))
        self.votes = self._label_votes(descriptors, boxes)
        matched = {i: index_of[s.bottle] for i, s in enumerate(snap.shown)
                   if s.bottle in index_of and s.bottle not in self.provisional}
        before = dict(matched)
        centres, spans = self._points(self.bottles)
        self._check_rows(snap.number, boxes, matched, centres, spans)
        self.votes = {}
        moved = set()
        for i, k in matched.items():
            if before.get(i) != k:
                held = before.get(i)
                held_id = self.bottles[held].id if held is not None else snap.shown[i].bottle
                result.moves.append((i, held_id, self.bottles[k].id))
                moved.add(held_id)
        result.confirmed = {s.bottle for s in snap.shown if s.bottle in self.provisional} - moved

    # ------------------------------------------------------------------ landing

    def _apply(self, result: SlowResult) -> None:
        cfg = self.cfg
        snap = result.snap
        chain = np.linalg.inv(snap.M) @ self.M        # the current frame -> frame t
        for index in result.good:
            self.verified[index] = snap.count
        if result.found:
            best, R = result.found
            if result.graph is not None:
                self.graph = result.graph
            self.ref, self.P = best, R @ chain
            self.anchored = self.localized = snap.count
            if snap.lost:
                self.lost = False
                self.found += 1
            self.corrections.append((snap.number, result.worst))
            if result.optimised:
                before, after, dropped = result.optimised
                self.dropped_edges += dropped
                merged = self._merge_duplicates()
                self.loops.append((snap.number, result.worst, before, after, merged))
        if result.keyframe is not None:
            features, ref, T, weight, kind = result.keyframe
            if kind == "new ground":
                right = max(self._keyframe_quad(k)[:, 0].max() for k in range(len(self.keyframes)))
                index = self.graph.add(np.array([[1, 0, right + self.size[0]], [0, 1, 0], [0, 0, 1]], float))
                self.lost = False
                self.new_grounds += 1
            else:
                index = self.graph.add(self.graph.poses[ref] @ T)
                self.graph.connect(ref, index, T, weight, kind)
            self.keyframes.append(Keyframe(snap.number, snap.count, features))
            self.ref, self.P = index, chain
            self.anchored = self.localized = snap.count
            self.verified[index] = snap.count
        by_id = {b.id: b for b in self.bottles}
        for bottle_id, descriptors in result.labels:
            bottle = by_id.get(bottle_id)
            if bottle is not None and len(bottle.label) < cfg.label_views:
                bottle.label.append(descriptors)
                bottle.labelled = snap.count
        self.provisional -= result.confirmed
        # A provisional bottle that left the view before a slow result saw it stays new.
        self.provisional -= {b.id for b in self.bottles
                             if b.id in self.provisional and b.left and b.first_step <= snap.count}
        if result.moves:
            # Each bottle that a box should carry takes over the track the box had.
            tracks = {b.id: (b.last_box, b.last_M, b.last_seen) for b in self.bottles}
            held_ids = {held for _, held, _ in result.moves if held is not None}
            given = set()
            for box, held, target in result.moves:
                bottle = by_id.get(target)
                if bottle is None:
                    continue
                if held is not None and held in tracks and tracks[held][0] is not None:
                    bottle.last_box, bottle.last_M, bottle.last_seen = tracks[held]
                else:                             # the box had no bottle: its box at t
                    bottle.last_box, bottle.last_M = snap.detections[box].box, snap.M.copy()
                    bottle.last_seen = snap.count
                if bottle.left:
                    bottle.appearance += 1
                    bottle.left = False
                given.add(target)
            took = {held: target for _, held, target in result.moves if held is not None}
            gone = set()
            for held in held_ids - given:
                bottle = by_id.get(held)
                if bottle is None:
                    continue
                bottle.last_box = None
                bottle.left = True
                if bottle.first_step >= snap.count - cfg.young_steps and took.get(held) in by_id:
                    self._rename(held, took[held])
                    gone.add(held)
            if gone:
                self.bottles = [b for b in self.bottles if b.id not in gone]
                self.merged_young += len(gone)
                self.provisional -= gone
