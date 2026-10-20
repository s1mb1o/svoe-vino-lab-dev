"""A COCO dataset of bottles for training the phone detector.

Video clips are labelled by the teacher: the cached Faster R-CNN detections, cleaned as
the tracker cleans them (clean_bottles, then the whole-bottle filter without the frame
edge rule: a bottle cut by the frame is still a bottle to find). A clip gives the frames
of its cached steps, every `--stride`-th (or the STRIDE of its spec).

A labeling folder (scripts/label_server.py) gives its photos with the reviewed boxes:
the teacher's boxes less the rejected ones plus the added ones. Its photos are split in
time: the first `--photo-train` share of each kind (shelf photos, others) trains, the rest
validates, so near copies of one shelf do not land on both sides.

    uv run python scripts/make_detector_dataset.py OUT \
        --train-video VIDEO.mp4:DETS.jsonl[:STRIDE] --val-video VIDEO.mp4:DETS.jsonl \
        --photos LABELING_DIR

OUT gets images/{train,val}/ (resized to `--width` px wide) with YOLO labels in
labels/{train,val}/ and bottle.yaml (Ultralytics), COCO annotations/{train,val}.json
(YOLOX; link train2017 and val2017 to the image folders), and the reviewed photos of val
alone as val_photos.txt, bottle_photos.yaml and annotations/val_photos.json.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import cv2

from shelfreid.detect import clean_bottles
from shelfreid.stream import ShelfTracker, StreamConfig
from shelfreid.types import Detection
from shelfreid.video import Preprocess, Video

WHOLE = replace(StreamConfig(), edge_margin=0.0)


def teacher_boxes(raw: list[Detection], size: tuple[int, int]) -> list[tuple]:
    kept = clean_bottles(raw, min_score=0.4)
    return [d.box for d in ShelfTracker(size, WHOLE)._whole_bottles(kept)]


def video_items(spec: str, stride: int):
    video, dets, *rest = spec.split(":")
    stride = int(rest[0]) if rest else stride
    cached = {r["frame"]: r["boxes"] for r in map(json.loads, open(dets))}
    wanted = set(sorted(cached)[::stride])
    for number, frame in Video(video, Preprocess()).stream(step=3):
        if number not in wanted:
            continue
        raw = [Detection(box=tuple(b[:4]), score=b[4]) for b in cached[number]]
        yield f"{Path(video).stem}_{number:06d}", frame, teacher_boxes(raw, (frame.shape[1], frame.shape[0]))


def photo_items(folder: str, train_share: float):
    """(train, val) lists of photos with their reviewed boxes."""
    root = Path(folder)
    boxes = json.load(open(root / "boxes.json"))
    reviews = json.load(open(root / "reviews.json"))
    kinds: dict[bool, list[str]] = {}
    for name in sorted(boxes):
        kinds.setdefault(name[13:15] == "21", []).append(name)   # shelf photos: from 21:00
    train, val = [], []
    for names in kinds.values():
        cut = round(len(names) * train_share)
        for k, name in enumerate(names):
            review = reviews.get(name, {})
            rejected = set(review.get("rejected", boxes[name].get("auto", [])))
            labels = [tuple(b[:4]) for i, b in enumerate(boxes[name]["boxes"]) if i not in rejected]
            labels += [tuple(b) for b in review.get("added", [])]
            item = (f"photo_{Path(name).stem}", cv2.imread(str(root / "images" / name)), labels)
            (train if k < cut else val).append(item)
    return train, val


def add(split: dict, out: Path, name: str, items, width: int) -> list[str]:
    """Write the images and their YOLO labels; return the image paths written."""
    (out / "images" / name).mkdir(parents=True, exist_ok=True)
    (out / "labels" / name).mkdir(parents=True, exist_ok=True)
    written = []
    for stem, frame, boxes in items:
        scale = width / frame.shape[1]
        frame = cv2.resize(frame, (width, round(frame.shape[0] * scale)), interpolation=cv2.INTER_AREA)
        h, w = frame.shape[:2]
        cv2.imwrite(str(out / "images" / name / f"{stem}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        image_id = len(split["images"]) + 1
        split["images"].append({"id": image_id, "file_name": f"{stem}.jpg", "width": w, "height": h})
        lines = []
        for x1, y1, x2, y2 in boxes:
            x1, y1, x2, y2 = (min(max(v * scale, 0.0), lim) for v, lim in ((x1, w), (y1, h), (x2, w), (y2, h)))
            if x2 - x1 < 2 or y2 - y1 < 2:
                continue
            split["annotations"].append({"id": len(split["annotations"]) + 1, "image_id": image_id, "category_id": 1,
                                         "bbox": [round(x1, 1), round(y1, 1), round(x2 - x1, 1), round(y2 - y1, 1)],
                                         "area": round((x2 - x1) * (y2 - y1), 1), "iscrowd": 0})
            lines.append(f"0 {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} {(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}")
        (out / "labels" / name / f"{stem}.txt").write_text("".join(line + "\n" for line in lines))
        written.append(f"./images/{name}/{stem}.jpg")
    return written


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--train-video", action="append", default=[], help="VIDEO:DETS.jsonl")
    parser.add_argument("--val-video", action="append", default=[], help="VIDEO:DETS.jsonl")
    parser.add_argument("--photos", action="append", default=[], help="a reviewed labeling folder")
    parser.add_argument("--photo-train", type=float, default=0.5)
    parser.add_argument("--stride", type=int, default=2, help="every n-th cached step of a video")
    parser.add_argument("--width", type=int, default=720)
    args = parser.parse_args()

    out = Path(args.out)
    (out / "annotations").mkdir(parents=True, exist_ok=True)
    photos = {"train": [], "val": []}
    for folder in args.photos:
        train, val = photo_items(folder, args.photo_train)
        photos["train"] += train
        photos["val"] += val
    splits = {}
    photo_paths = []
    for name, specs in (("train", args.train_video), ("val", args.val_video)):
        split = {"images": [], "annotations": [], "categories": [{"id": 1, "name": "bottle"}]}
        for spec in specs:
            add(split, out, name, video_items(spec, args.stride), args.width)
        paths = add(split, out, name, photos[name], args.width)
        if name == "val":
            photo_paths = paths
        (out / "annotations" / f"{name}.json").write_text(json.dumps(split))
        splits[name] = split
        print(f"{name}: {len(split['images'])} images, {len(split['annotations'])} boxes")
    (out / "bottle.yaml").write_text("train: images/train\nval: images/val\nnames:\n  0: bottle\n")
    if photo_paths:
        # The reviewed photos alone: the honest check (the video labels are the teacher's).
        (out / "val_photos.txt").write_text("".join(p + "\n" for p in photo_paths))
        (out / "bottle_photos.yaml").write_text("train: images/train\nval: val_photos.txt\nnames:\n  0: bottle\n")
        files = {p.rsplit("/", 1)[1] for p in photo_paths}
        val = splits["val"]
        images = [i for i in val["images"] if i["file_name"] in files]
        ids = {i["id"] for i in images}
        gt = {"images": images, "annotations": [a for a in val["annotations"] if a["image_id"] in ids],
              "categories": val["categories"]}
        (out / "annotations" / "val_photos.json").write_text(json.dumps(gt))
        print(f"val_photos: {len(gt['images'])} images, {len(gt['annotations'])} boxes")


if __name__ == "__main__":
    main()
