"""Bottle-level accuracy of two-frame decisions on a video, against tracks of short steps.

The reference identity of a bottle comes from tracking: the detections of consecutive chain
frames (every `--step` frames) are associated with the chained short-step homography,
where the motion is small and the association is unambiguous; a track that breaks for up
to `--bridge` steps (a missed detection) is joined again. For a pair of distant frames
(A, B), a bottle of B is truly "seen" when its track has a detection in A.

Errors per bottle of B:
- false seen: the bottle is new, but the decision says seen (or names the wrong bottle of
  A). The bottle would never be recognised.
- missed: the bottle is in A, but the decision says new. A duplicate recognition.

    uv run --extra deep python scripts/eval_bottles.py VIDEO --chain out/.../chain.npz
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from shelfreid.associate import associate
from shelfreid.detect import CocoDetector, boxes_mask, clean_bottles
from shelfreid.features import FeatureConfig, extract
from shelfreid.homography import overlaps
from shelfreid.pair import PairConfig, match_pair
from shelfreid.types import Detection
from shelfreid.video import LENTA_ROBOT, Video

CONFIGS = {
    "sift": FeatureConfig(),
    "aliked-lg": FeatureConfig(method="aliked", max_features=4096, max_side=1024),
    "disk-lg": FeatureConfig(method="disk", max_features=4096, max_side=1024),
}


def detections(video: Video, frames: list[int], cache: Path) -> list[list[Detection]]:
    if cache.exists():
        data = json.loads(cache.read_text())
        return [[Detection(tuple(d["box"]), score=d["score"]) for d in row] for row in data]
    detector = CocoDetector(threshold=0.3)
    rows = [clean_bottles(detector(video.index(n))) for n in frames]
    cache.write_text(json.dumps([[{"box": d.box, "score": d.score} for d in row] for row in rows]))
    return rows


class Tracks:
    """Union-find over (chain index, detection index)."""

    def __init__(self):
        self.parent = {}

    def find(self, key):
        self.parent.setdefault(key, key)
        while self.parent[key] != key:
            self.parent[key] = self.parent[self.parent[key]]
            key = self.parent[key]
        return key

    def union(self, a, b):
        self.parent[self.find(a)] = self.find(b)


def build_tracks(dets, steps, size, bridge: int) -> Tracks:
    tracks = Tracks()
    outgoing, incoming = set(), set()
    for i in range(len(dets) - 1):
        for decision in associate(dets[i], dets[i + 1], steps[i], size, size):
            if decision.status == "seen":
                tracks.union((i, decision.match), (i + 1, decision.index))
                outgoing.add((i, decision.match))
                incoming.add((i + 1, decision.index))
    # Join the tracks that a missed detection broke: only ends to starts.
    for gap in range(2, bridge + 1):
        for i in range(len(dets) - gap):
            H = np.eye(3)
            for k in range(i, i + gap):
                H = H @ steps[k]
            ends = [j for j in range(len(dets[i])) if (i, j) not in outgoing]
            starts = [k for k in range(len(dets[i + gap])) if (i + gap, k) not in incoming]
            if not ends or not starts:
                continue
            for decision in associate([dets[i][j] for j in ends],
                                      [dets[i + gap][k] for k in starts], H, size, size):
                if decision.status == "seen":
                    a, b = (i, ends[decision.match]), (i + gap, starts[decision.index])
                    tracks.union(a, b)
                    outgoing.add(a)
                    incoming.add(b)
    return tracks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("--chain", required=True, help="chain.npz of eval_overlap.py")
    parser.add_argument("--every", type=int, default=8)
    parser.add_argument("--overlaps", default="0.7,0.5,0.4,0.3")
    parser.add_argument("--bridge", type=int, default=3)
    parser.add_argument("--configs", default=",".join(CONFIGS))
    parser.add_argument("--out", default="out/eval-bottles")
    args = parser.parse_args()

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    video = Video(args.video, LENTA_ROBOT)
    data = np.load(args.chain)
    frames, steps = [int(n) for n in data["frames"]], list(data["H"])
    first = video.index(0)
    size = (first.shape[1], first.shape[0])
    dets = detections(video, frames, out / "detections.json")
    tracks = build_tracks(dets, steps, size, args.bridge)
    lengths = {}
    for i, row in enumerate(dets):
        for j in range(len(row)):
            root = tracks.find((i, j))
            lengths[root] = lengths.get(root, 0) + 1
    print(f"{sum(map(len, dets))} detections in {len(frames)} frames, {len(lengths)} tracks,"
          f" median track length {np.median(list(lengths.values())):.0f} frames")

    pairs = []
    for target in map(float, args.overlaps.split(",")):
        for i in range(0, len(frames) - 1, args.every):
            H = np.eye(3)
            for j in range(i, len(steps)):
                H = H @ steps[j]
                if overlaps(H, size, size)[0] <= target:
                    pairs.append((target, i, j + 1))
                    break

    images = {}
    report = {}
    for name in args.configs.split(","):
        for masked in (False, True):
            fc = CONFIGS[name]
            cfg = PairConfig(features=fc)
            label = name + ("+bottles" if masked else "")
            features = {}
            rows = []
            for target, i, j in pairs:
                for k in (i, j):
                    if k not in features:
                        if frames[k] not in images:
                            images[frames[k]] = video.index(frames[k])
                        mask = boxes_mask(size, dets[k]) if masked else None
                        features[k] = extract(images[frames[k]], fc, mask)
                result = match_pair(features[i], dets[i], features[j], dets[j], cfg)
                in_a = {tracks.find((i, a)) for a in range(len(dets[i]))}
                counts = {"bottles": len(dets[j]), "right": 0, "false_seen": 0, "missed": 0}
                for decision in result.decisions:
                    truth = tracks.find((j, decision.index))
                    seen = truth in in_a
                    said = decision.status == "seen"
                    if said and seen and tracks.find((i, decision.match)) == truth:
                        counts["right"] += 1
                    elif said:
                        counts["false_seen"] += 1
                    elif seen:
                        counts["missed"] += 1
                    else:
                        counts["right"] += 1
                rows.append({"target": target, "a": frames[i], "b": frames[j],
                             "linked": result.registration.ok, **counts})
            report[label] = rows
            line = []
            for target in sorted({p[0] for p in pairs}, reverse=True):
                sub = [r for r in rows if r["target"] == target]
                total = sum(r["bottles"] for r in sub)
                line.append(f"{target:.0%}: linked {sum(r['linked'] for r in sub)}/{len(sub)},"
                            f" right {sum(r['right'] for r in sub) / total:.0%},"
                            f" false seen {sum(r['false_seen'] for r in sub) / total:.1%},"
                            f" missed {sum(r['missed'] for r in sub) / total:.0%}")
            print(f"{label:18} " + " | ".join(line), flush=True)
    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
