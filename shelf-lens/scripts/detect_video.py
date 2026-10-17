"""Detect bottles in every N-th frame of a video and cache them as JSON lines.

Each line: {"frame": n, "boxes": [[x1, y1, x2, y2, score], ...]} with the raw detections
of the COCO detector at `--threshold`; cleaning happens later, so it can be tuned.

    uv run --extra deep python scripts/detect_video.py VIDEO --every 3 --out out/x.jsonl
"""

from __future__ import annotations

import argparse
import json
import time

from shelfreid.detect import CocoDetector
from shelfreid.video import Preprocess, Video


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("--every", type=int, default=3)
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    video = Video(args.video, Preprocess())
    detector = CocoDetector(threshold=args.threshold)
    started = time.time()
    with open(args.out, "w", encoding="utf-8") as out:
        for number, frame in video.stream(step=args.every):
            boxes = [[*map(lambda v: round(v, 1), d.box), round(d.score, 3)] for d in detector(frame)]
            out.write(json.dumps({"frame": number, "boxes": boxes}) + "\n")
            if number % 300 == 0:
                print(f"frame {number}/{video.frames}, {time.time() - started:.0f} s", flush=True)
    print(f"done in {time.time() - started:.0f} s")


if __name__ == "__main__":
    main()
