"""Run the photo tracker (photos.py) on photos in one session, one map, and write each
photo with its boxes, plus one sheet of them all. Red: a bottle of an earlier photo;
green: a new one. Each photo prints how it found its place, and the time of its keypoints,
its registrations, and the rest.

    uv run --extra deep python scripts/run_photos.py IMG1.jpg IMG2.jpg ... --out out/photos/a
"""

from __future__ import annotations

import argparse
import json
from time import perf_counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from shelfreid.detect import clean_bottles
from shelfreid.photos import PhotoTracker, photo_config
from shelfreid.stream import draw
from shelfreid.types import Detection


def load(path: str, width: int) -> np.ndarray:
    image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    height = round(bgr.shape[0] * width / bgr.shape[1])
    return cv2.resize(bgr, (width, height), interpolation=cv2.INTER_AREA)


DETECT_WIDTH = 1080   # the detector reads the photos at this width; the cache keeps its boxes


def detections(paths: list[str], cache: Path) -> list[list]:
    """The raw boxes of each photo at `DETECT_WIDTH`, cached by file name."""
    rows = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    missing = [i for i, p in enumerate(paths) if Path(p).name not in rows]
    if missing:
        from shelfreid.detect import CocoDetector

        detector = CocoDetector(threshold=0.3)
        for i in missing:
            rows[Path(paths[i]).name] = [[*map(lambda v: round(v, 1), d.box), round(d.score, 3)]
                                         for d in detector(load(paths[i], DETECT_WIDTH))]
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(rows), encoding="utf-8")
    return [rows[Path(p).name] for p in paths]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("photos", nargs="+")
    parser.add_argument("--out", required=True, help="a directory for the annotated photos")
    parser.add_argument("--dets", default="out/photos/dets.json", help="the detection cache")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--long-side", type=int, default=1440, help="of the keypoint image")
    parser.add_argument("--points", type=int, default=4000, help="keypoints a photo")
    parser.add_argument("--tries", type=int, default=3, help="keyframes a photo, newest first")
    args = parser.parse_args()

    cfg = photo_config(args.long_side, args.points)
    images = [load(p, args.width) for p in args.photos]
    raw = detections(args.photos, Path(args.dets))
    k = args.width / DETECT_WIDTH
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    size = (images[0].shape[1], images[0].shape[0])
    tracker = PhotoTracker(size, cfg, tries=args.tries)
    tiles = []
    for i, (path, image, boxes) in enumerate(zip(args.photos, images, raw)):
        dets = clean_bottles([Detection(tuple(v * k for v in b[:4]), score=b[4]) for b in boxes],
                             min_score=cfg.min_score)
        found, new_ground = tracker.found, tracker.new_grounds
        clock, matches, attempts = dict(tracker.clock), tracker.matches, len(tracker.attempts)
        started = perf_counter()
        shown = tracker.photo(i, image, dets)
        total = perf_counter() - started
        confirmed = sorted(k for k, step in tracker.verified.items() if step == tracker.count - 1)
        how = ("first" if i == 0 else f"found on {tracker.placed_on}, confirmed {confirmed}"
               if tracker.found > found else "new ground")
        count = {s: sum(x.status == s for x in shown) for s in ("returning", "new", "pending")}
        text = (f"{i + 1}. {Path(path).stem[13:]}  {how}  red {count['returning']} "
                f"green {count['new']} white {count['pending']}")
        spent = {k: tracker.clock[k] - clock[k] for k in tracker.clock}
        tried = [f"{k}:{n}/{c:.2f}{'*' if st else ''}" for _, k, n, c, st in tracker.attempts[attempts:]]
        print(f"{text}  | {total:.2f} s: keypoints {spent['keypoints']:.2f}, "
              f"{tracker.matches - matches} registrations {spent['registration']:.2f}, "
              f"rest {total - sum(spent.values()):.2f} | {' '.join(tried)}")
        annotated = draw(image, shown)
        annotated = cv2.resize(annotated, (1080, round(size[1] * 1080 / size[0])))
        cv2.rectangle(annotated, (0, 0), (1080, 56), (30, 30, 30), -1)
        cv2.putText(annotated, text, (12, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.imwrite(str(out / f"{i + 1:02d}-{Path(path).stem}.jpg"), annotated)
        tiles.append(cv2.resize(annotated, (540, annotated.shape[0] // 2)))
    per = 5
    while len(tiles) % per:
        tiles.append(np.full_like(tiles[0], 255))
    gap = np.full((tiles[0].shape[0], 10, 3), 255, np.uint8)
    rows = [np.hstack([x for t in tiles[j:j + per] for x in (t, gap)][:-1])
            for j in range(0, len(tiles), per)]
    line = np.full((10, rows[0].shape[1], 3), 255, np.uint8)
    cv2.imwrite(str(out / "sheet.jpg"), np.vstack([x for r in rows for x in (r, line)][:-1]))
    print(f"bottles {len(tracker.bottles)}, ids {tracker.next_id}, keyframes {len(tracker.keyframes)}")


if __name__ == "__main__":
    main()
