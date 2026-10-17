"""Run the stream tracker on a video with cached detections and write an annotated video.

Green: a bottle in its first appearance. Red: a bottle that left the view and came back.
Grey: a detection that is ignored (cut by the frame edge, or too weak to start a bottle).

    uv run python scripts/run_stream.py VIDEO --dets out/x-dets.jsonl --out out/x.mp4
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np

from shelfreid.detect import clean_bottles
from shelfreid.stream import ShelfTracker, StreamConfig, draw
from shelfreid.types import Detection
from shelfreid.video import Preprocess, Video


def read_detections(path: str, min_score: float) -> dict[int, list[Detection]]:
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        raw = [Detection(tuple(b[:4]), score=b[4]) for b in row["boxes"]]
        out[row["frame"]] = clean_bottles(raw, min_score=min_score)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("--dets", required=True)
    parser.add_argument("--every", type=int, default=3, help="the frame step of the detections")
    parser.add_argument("--out", required=True)
    parser.add_argument("--scale", type=float, default=0.5, help="the scale of the output video")
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--stop", type=float, default=None)
    args = parser.parse_args()

    cfg = StreamConfig()
    video = Video(args.video, Preprocess())
    detections = read_detections(args.dets, cfg.min_score)
    start = round(args.start * video.fps / args.every) * args.every
    stop = video.frames if args.stop is None else round(args.stop * video.fps)
    first = video.index(start)
    size = (first.shape[1], first.shape[0])
    tracker = ShelfTracker(size, cfg)
    out_size = (round(size[0] * args.scale), round(size[1] * args.scale))
    writer = cv2.VideoWriter(args.out, cv2.VideoWriter_fourcc(*"mp4v"), video.fps / args.every,
                             out_size)
    history = []
    step_ms = []
    for number, frame in video.stream(start=start, stop=stop, step=args.every):
        if number not in detections:
            print(f"no detections for frame {number}; stop")
            break
        started = perf_counter()
        shown = tracker.step(number, frame, detections[number])
        step_ms.append((perf_counter() - started) * 1000)
        new = sum(s.status == "new" for s in shown)
        returning = sum(s.status == "returning" for s in shown)
        text = (f"{number / video.fps:5.1f}s  bottles {len(tracker.bottles)}  "
                f"new {new}  returning {returning}")
        writer.write(cv2.resize(draw(frame, shown, text), out_size, interpolation=cv2.INTER_AREA))
        history.append({"frame": number, "bottles": len(tracker.bottles), "new": new,
                        "returning": returning, "keyframes": len(tracker.keyframes)})
    writer.release()

    appearances = [b.appearance for b in tracker.bottles]
    steps = len(step_ms)
    summary = {
        "steps": steps,
        "bottles": len(tracker.bottles),
        "bottle_ids_issued": tracker.next_id,
        "bottles_returned": int(sum(a > 1 for a in appearances)),
        "returns": int(sum(a - 1 for a in appearances)),
        "keyframes": len(tracker.keyframes),
        "corrections": len(tracker.corrections),
        "loops": [tuple(round(v, 2) if isinstance(v, float) else v for v in loop) for loop in tracker.loops],
        "correction_median": float(np.median([c[1] for c in tracker.corrections])) if tracker.corrections else None,
        "lost_motion": tracker.lost_motion,
        "dropped_low_boxes": tracker.dropped,
        "ms_per_step": {k: round(v / steps * 1000, 1) for k, v in tracker.timings.items()},
        "ms_per_step_total_p50_p95": [round(float(np.percentile(step_ms, q)), 1) for q in (50, 95)],
    }
    Path(args.out).with_suffix(".json").write_text(
        json.dumps({"summary": summary, "history": history}, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    print(f"video: {args.out}")


if __name__ == "__main__":
    main()
