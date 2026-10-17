"""Command line: `shelfreid register`, `shelfreid pair`, `shelfreid synth`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from . import synth, viz
from .features import FeatureConfig
from .homography import corners, project
from .pair import PairConfig, match_pair, register
from .types import Detection


def read_image(path: str) -> np.ndarray:
    image = cv2.imread(path, cv2.IMREAD_COLOR)  # applies the EXIF orientation
    if image is None:
        raise SystemExit(f"cannot read the image {path}")
    return image


def read_detections(path: str) -> list[Detection]:
    """A JSON list of {"box": [x1, y1, x2, y2], "id": ..., "score": ...}, or
    {"detections": [...]}."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data["detections"] if isinstance(data, dict) else data
    return [Detection(tuple(map(float, item["box"])), item.get("id"), item.get("score", 1.0))
            for item in items]


def _config(args) -> PairConfig:
    return PairConfig(features=FeatureConfig(method=args.method, max_side=args.max_side))


def _save(path: str | None, image: np.ndarray):
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(path, image)
        print(f"picture: {path}")


def cmd_register(args):
    image_a, image_b = read_image(args.a), read_image(args.b)
    registration, points_a, points_b, timings, _, _ = register(image_a, image_b, _config(args))
    print(f"{registration.reason}: matches {registration.matches}, inliers {registration.inliers},"
          f" B covers {registration.overlap_a:.1%} of A, {registration.overlap_b:.1%} of B is in A,"
          f" inliers span {registration.coverage:.0%} of the overlap")
    print("timings ms: " + ", ".join(f"{k} {v:.0f}" for k, v in timings.items()))
    _save(args.out, viz.draw_registration(image_a, image_b, registration, points_a, points_b))


def cmd_pair(args):
    image_a, image_b = read_image(args.a), read_image(args.b)
    dets_a, dets_b = read_detections(args.dets_a), read_detections(args.dets_b)
    result = match_pair(image_a, dets_a, image_b, dets_b, _config(args))
    for d in result.decisions:
        print(f"B[{d.index}] {d.status}" + (f" = A[{d.match}] ({d.distance:.2f} w)"
                                            if d.match is not None else ""))
    if args.json:
        Path(args.json).write_text(json.dumps(
            {"registration": result.registration.reason, "inliers": result.registration.inliers,
             "decisions": [d.__dict__ for d in result.decisions]}, indent=2), encoding="utf-8")
    _save(args.out, viz.draw_pair(image_a, image_b, dets_a, dets_b, result))


def evaluate_synth(seed: int, overlap: float, cfg: PairConfig = PairConfig()):
    """Run one synthetic pair. Return (the pair, the result, the corner error in px,
    the number of right decisions)."""
    rng = np.random.default_rng(seed)
    case = synth.pair(synth.shelf_scene(rng), rng, overlap=overlap)
    result = match_pair(case.image_a, case.dets_a, case.image_b, case.dets_b, cfg)
    size_b = (case.image_b.shape[1], case.image_b.shape[0])
    error = float("inf")
    if result.registration.H is not None:
        error = float(np.abs(project(result.registration.H, corners(size_b))
                             - project(case.H, corners(size_b))).max())
    ids_a = [d.id for d in case.dets_a]
    right = 0
    for decision in result.decisions:
        truth = case.dets_b[decision.index].id
        if truth in ids_a:
            right += decision.status == "seen" and ids_a[decision.match or 0] == truth
        else:
            right += decision.status != "seen"
    return case, result, error, right


def cmd_synth(args):
    out = Path(args.out)
    for seed in range(args.seed, args.seed + args.count):
        case, result, error, right = evaluate_synth(seed, args.overlap, _config(args))
        print(f"seed {seed}: {result.registration.reason}, inliers {result.registration.inliers},"
              f" corner error {error:.1f} px, right {right}/{len(case.dets_b)}")
        _save(str(out / f"synth-{seed}.jpg"),
              viz.draw_pair(case.image_a, case.image_b, case.dets_a, case.dets_b, result))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="shelfreid")
    parser.add_argument("--method", default="sift", choices=["sift", "orb", "akaze"])
    parser.add_argument("--max-side", type=int, default=1600)
    commands = parser.add_subparsers(dest="command", required=True)

    p = commands.add_parser("register", help="join two frames; no detections needed")
    p.add_argument("a"); p.add_argument("b"); p.add_argument("--out")
    p.set_defaults(func=cmd_register)

    p = commands.add_parser("pair", help="which bottles of frame B were in frame A")
    p.add_argument("a"); p.add_argument("b")
    p.add_argument("--dets-a", required=True); p.add_argument("--dets-b", required=True)
    p.add_argument("--out"); p.add_argument("--json")
    p.set_defaults(func=cmd_pair)

    p = commands.add_parser("synth", help="synthetic pairs with a known answer")
    p.add_argument("--seed", type=int, default=0); p.add_argument("--count", type=int, default=3)
    p.add_argument("--overlap", type=float, default=0.5); p.add_argument("--out", default="out/synth")
    p.set_defaults(func=cmd_synth)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
