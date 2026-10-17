"""Link rate and accuracy of two-frame registration by overlap, on a video.

The reference is the chain of short steps (every `--step` frames), which links reliably;
over a few steps its product is accurate. The error of a direct registration is the
largest distance, in frame A, between its map and the chained map over a grid of points
of frame B that lie in the overlap and in the content band (`--band` of the height; the
frame corners of an undistorted frame are black and the scene is not one plane). A
registration counts as right when it passes the checks and the error is below
`--tolerance` of the frame width (half a bottle is about 0.04); as false when it passes
but the error is larger.

    uv run python scripts/eval_overlap.py VIDEO --preset lenta
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from shelfreid.features import FeatureConfig, extract
from shelfreid.homography import overlaps, project
from shelfreid.pair import PairConfig, register
from shelfreid.video import LENTA_ROBOT, Preprocess, Video

PRESETS = {"lenta": LENTA_ROBOT, "none": Preprocess()}
CONFIGS = {
    "sift": FeatureConfig(),
    "rootsift": FeatureConfig(rootsift=True),
    "rootsift-8k-r0.8": FeatureConfig(rootsift=True, max_features=8000, ratio=0.8, mutual=False),
    "rootsift-8k-r0.8-full": FeatureConfig(rootsift=True, max_features=8000, ratio=0.8,
                                           mutual=False, max_side=1920),
    "aliked-lg": FeatureConfig(method="aliked", max_features=4096, max_side=1024),
    "disk-lg": FeatureConfig(method="disk", max_features=4096, max_side=1024),
}


def fine_chain(video: Video, step: int, cache: Path):
    """The homographies H_i (frame i+1 -> frame i) of the frames 0, step, 2 step, ..."""
    if cache.exists():
        data = np.load(cache)
        return [int(n) for n in data["frames"]], list(data["H"])
    frames, steps, previous = [], [], None
    for number, frame in video.stream(step=step):
        features = extract(frame)
        if previous is not None:
            registration, *_ = register(previous, features)
            if not registration.ok:
                raise RuntimeError(f"the short step to frame {number} failed: {registration.reason}")
            steps.append(registration.H)
        frames.append(number)
        previous = features
    np.savez(cache, frames=np.array(frames), H=np.array(steps))
    return frames, steps


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("--preset", default="lenta", choices=PRESETS)
    parser.add_argument("--step", type=int, default=5)
    parser.add_argument("--every", type=int, default=8, help="a start pair every N chain steps")
    parser.add_argument("--overlaps", default="0.7,0.5,0.4,0.3")
    parser.add_argument("--tolerance", type=float, default=0.04)
    parser.add_argument("--band", type=float, default=0.8)
    parser.add_argument("--configs", default=",".join(CONFIGS))
    parser.add_argument("--out", default="out/eval-overlap")
    args = parser.parse_args()

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    video = Video(args.video, PRESETS[args.preset])
    frames, steps = fine_chain(video, args.step, out / "chain.npz")
    first = video.index(0)
    size = (first.shape[1], first.shape[0])

    # Pairs: from each start, the first chain frame whose chained overlap falls below
    # the target.
    pairs = []
    for target in map(float, args.overlaps.split(",")):
        for i in range(0, len(frames) - 1, args.every):
            H = np.eye(3)
            for j in range(i, len(steps)):
                H = H @ steps[j]
                if overlaps(H, size, size)[0] <= target:
                    pairs.append((target, frames[i], frames[j + 1], H.copy()))
                    break

    cache = {}
    def features(number, cfg):
        key = (number, cfg)
        if key not in cache:
            cache[key] = extract(video.index(number), cfg)
        return cache[key]

    margin = (1 - args.band) / 2 * size[1]
    gx, gy = np.meshgrid(np.linspace(0, size[0], 28), np.linspace(margin, size[1] - margin, 48))
    grid = np.c_[gx.ravel(), gy.ravel()]

    def error_px(H, H_ref):
        reference = project(H_ref, grid)
        inside = ((reference[:, 0] >= 0) & (reference[:, 0] < size[0])
                  & (reference[:, 1] >= margin) & (reference[:, 1] < size[1] - margin))
        if not inside.any():
            return float("inf")
        return float(np.linalg.norm(project(H, grid[inside]) - reference[inside], axis=1).max())

    report = {}
    tol = args.tolerance * size[0]
    for name in args.configs.split(","):
        cfg = PairConfig(features=CONFIGS[name])
        rows = []
        for target, a, b, H_ref in pairs:
            registration, *_ = register(features(a, cfg.features), features(b, cfg.features), cfg)
            error = None if registration.H is None else error_px(registration.H, H_ref)
            rows.append({"target": target, "a": a, "b": b, "ok": registration.ok,
                         "reason": registration.reason, "inliers": registration.inliers,
                         "error_px": error})
        report[name] = rows
        line = []
        for target in sorted({p[0] for p in pairs}, reverse=True):
            sub = [r for r in rows if r["target"] == target]
            right = sum(r["ok"] and r["error_px"] <= tol for r in sub)
            false = sum(r["ok"] and r["error_px"] > tol for r in sub)
            errors = [r["error_px"] for r in sub if r["ok"]]
            median = f" med {np.median(errors):.0f}px" if errors else ""
            line.append(f"{target:.0%}: right {right}/{len(sub)} false {false}{median}")
        print(f"{name:24} " + " | ".join(line))
        cache = {k: v for k, v in cache.items() if k[1] != cfg.features}
    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
