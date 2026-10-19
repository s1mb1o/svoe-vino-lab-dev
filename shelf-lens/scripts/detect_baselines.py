"""Detect bottles in the step frames of a video with a small pretrained detector (class
`bottle` of COCO), cached as JSON lines in the format of detect_video.py, with the time of
each frame. The candidates for the phone, all Apache-2.0:

    dfine-n       ustc-community/dfine-nano-coco (transformers)
    dfine-s       ustc-community/dfine-small-obj2coco
    rtdetrv2-r18  PekingU/rtdetr_v2_r18vd
    rfdetr-n      RF-DETR Nano (rfdetr)
    rfdetr-s      RF-DETR Small
    yolox-nano    YOLOX nano, 416 (ONNX of the YOLOX release)
    yolox-tiny    YOLOX tiny, 416
    yolox-s       YOLOX s, 640

    uv run --extra deep --extra detect python scripts/detect_baselines.py MODEL VIDEO --out out/detectors/MODEL/KEY-dets.jsonl
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

import cv2
import numpy as np

from shelfreid.video import Preprocess, Video

HF = {"dfine-n": "ustc-community/dfine-nano-coco", "dfine-s": "ustc-community/dfine-small-obj2coco",
      "rtdetrv2-r18": "PekingU/rtdetr_v2_r18vd"}
YOLOX = {"yolox-nano": ("yolox_nano", 416), "yolox-tiny": ("yolox_tiny", 416), "yolox-s": ("yolox_s", 640)}
YOLOX_URL = "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/{}.onnx"
COCO80_BOTTLE = 39


class HFDetector:
    def __init__(self, name: str, device: str):
        import torch
        from transformers import AutoImageProcessor, AutoModelForObjectDetection

        self.torch = torch
        self.processor = AutoImageProcessor.from_pretrained(HF[name])
        self.model = AutoModelForObjectDetection.from_pretrained(HF[name]).eval().to(device)
        self.device = device
        self.bottle = next(k for k, v in self.model.config.id2label.items() if v == "bottle")

    def __call__(self, bgr: np.ndarray, threshold: float):
        rgb = np.ascontiguousarray(bgr[..., ::-1])
        inputs = self.processor(images=rgb, return_tensors="pt").to(self.device)
        with self.torch.no_grad():
            outputs = self.model(**inputs)
        result = self.processor.post_process_object_detection(
            outputs, target_sizes=[bgr.shape[:2]], threshold=threshold)[0]
        keep = result["labels"].cpu().numpy() == self.bottle
        return result["boxes"].cpu().numpy()[keep], result["scores"].cpu().numpy()[keep]


class RFDetector:
    def __init__(self, name: str):
        from rfdetr import RFDETRNano, RFDETRSmall
        from rfdetr.assets.coco_classes import COCO_CLASSES

        self.model = (RFDETRNano if name == "rfdetr-n" else RFDETRSmall)()
        self.bottle = next(k for k, v in COCO_CLASSES.items() if v == "bottle")

    def __call__(self, bgr: np.ndarray, threshold: float):
        from PIL import Image

        found = self.model.predict(Image.fromarray(bgr[..., ::-1].copy()), threshold=threshold)
        keep = found.class_id == self.bottle
        return found.xyxy[keep], found.confidence[keep]


class YOLOXDetector:
    def __init__(self, name: str, cache: Path):
        import onnxruntime

        file, self.size = YOLOX[name]
        path = cache / f"{file}.onnx"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(YOLOX_URL.format(file), path)
        self.session = onnxruntime.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        grids, strides = [], []
        for stride in (8, 16, 32):
            side = self.size // stride
            yv, xv = np.meshgrid(np.arange(side), np.arange(side), indexing="ij")
            grids.append(np.stack((xv, yv), 2).reshape(-1, 2))
            strides.append(np.full((side * side, 1), stride))
        self.grids, self.strides = np.concatenate(grids), np.concatenate(strides)

    def __call__(self, bgr: np.ndarray, threshold: float):
        h, w = bgr.shape[:2]
        r = min(self.size / h, self.size / w)
        resized = cv2.resize(bgr, (int(w * r), int(h * r)), interpolation=cv2.INTER_LINEAR)
        padded = np.full((self.size, self.size, 3), 114, np.uint8)
        padded[:resized.shape[0], :resized.shape[1]] = resized
        x = padded.transpose(2, 0, 1)[None].astype(np.float32)
        out = self.session.run(None, {self.session.get_inputs()[0].name: x})[0][0]
        xy = (out[:, :2] + self.grids) * self.strides
        wh = np.exp(out[:, 2:4]) * self.strides
        scores = out[:, 4] * out[:, 5 + COCO80_BOTTLE]
        keep = scores >= threshold
        boxes = np.concatenate([xy - wh / 2, xy + wh / 2], 1)[keep] / r
        scores = scores[keep]
        if not len(boxes):
            return boxes, scores
        rects = np.c_[boxes[:, :2], boxes[:, 2:] - boxes[:, :2]].tolist()
        chosen = cv2.dnn.NMSBoxes(rects, scores.tolist(), threshold, 0.45)
        chosen = np.array(chosen).reshape(-1)
        return boxes[chosen], scores[chosen]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model", choices=[*HF, "rfdetr-n", "rfdetr-s", *YOLOX])
    parser.add_argument("video")
    parser.add_argument("--out", required=True)
    parser.add_argument("--every", type=int, default=3)
    parser.add_argument("--threshold", type=float, default=0.2)
    parser.add_argument("--device", default="mps")
    parser.add_argument("--limit", type=int, default=0, help="frames, for a smoke test")
    args = parser.parse_args()

    if args.model in HF:
        detector = HFDetector(args.model, args.device)
    elif args.model.startswith("rfdetr"):
        detector = RFDetector(args.model)
    else:
        detector = YOLOXDetector(args.model, Path("out/detectors/weights"))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    seconds = []
    with out.open("w", encoding="utf-8") as fh:
        for k, (number, frame) in enumerate(Video(args.video, Preprocess()).stream(step=args.every)):
            if args.limit and k >= args.limit:
                break
            started = time.perf_counter()
            boxes, scores = detector(frame, args.threshold)
            seconds.append(time.perf_counter() - started)
            fh.write(json.dumps({"frame": number, "boxes": [[*map(lambda v: round(float(v), 1), b),
                                                             round(float(s), 3)]
                                                            for b, s in zip(boxes, scores)]}) + "\n")
    seconds = np.array(seconds[3:]) * 1000   # without the warm-up
    print(f"{args.model} {Path(args.video).stem}: {len(seconds) + 3} frames, "
          f"{np.median(seconds):.0f} ms median ({args.device if args.model in HF else 'cpu' if 'yolox' in args.model else 'auto'})")


if __name__ == "__main__":
    main()
