"""Run a trained bottle detector (ONNX, input 1x3x800x448) the way the phone will: the
frame fitted into the input without changing its proportions, then NMS. Ultralytics YOLO
(output 1x5xN: cx, cy, w, h, score) and YOLOX (output 1xNx6, raw: decoded here) share
everything else, so they compare on equal terms.

    uv run --extra detect python scripts/detect_onnx.py MODEL.onnx video VIDEO --out DETS.jsonl [--every 3]
    uv run --extra detect python scripts/detect_onnx.py MODEL.onnx coco ANNOTATIONS.json IMAGES_DIR --out RESULTS.json

`video` writes the detect_video.py format; `coco` writes COCO results for pycocotools.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime

from shelfreid.video import Preprocess, Video

NMS_IOU = 0.6


class Detector:
    def __init__(self, path: str, threads: int = 8):
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = threads
        self.session = onnxruntime.InferenceSession(path, options, providers=["CPUExecutionProvider"])
        inp = self.session.get_inputs()[0]
        self.name = inp.name
        self.h, self.w = inp.shape[2], inp.shape[3]
        out = self.session.get_outputs()[0].shape
        self.yolox = out[-1] == 6
        if self.yolox:
            grids, strides = [], []
            for s in (8, 16, 32):
                yv, xv = np.meshgrid(np.arange(self.h // s), np.arange(self.w // s), indexing="ij")
                grids.append(np.stack((xv, yv), 2).reshape(-1, 2))
                strides.append(np.full((grids[-1].shape[0], 1), s))
            self.grids, self.strides = np.concatenate(grids), np.concatenate(strides)

    def prepare(self, bgr: np.ndarray):
        """The input tensor of a frame, with the scale and the offset of the frame in it."""
        h, w = bgr.shape[:2]
        r = min(self.h / h, self.w / w)
        nh, nw = round(h * r), round(w * r)
        resized = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((self.h, self.w, 3), 114, np.uint8)
        if self.yolox:   # YOLOX: BGR 0..255, the image at the top left
            dx = dy = 0
            canvas[:nh, :nw] = resized
            x = canvas.transpose(2, 0, 1)[None].astype(np.float32)
        else:            # Ultralytics: RGB 0..1, the image centred
            dx, dy = (self.w - nw) // 2, (self.h - nh) // 2
            canvas[dy:dy + nh, dx:dx + nw] = resized
            x = canvas[..., ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0
        return x, r, dx, dy

    def __call__(self, bgr: np.ndarray, threshold: float = 0.05):
        h, w = bgr.shape[:2]
        x, r, dx, dy = self.prepare(bgr)
        out = self.session.run(None, {self.name: x})[0][0]
        if self.yolox:
            xy = (out[:, :2] + self.grids) * self.strides
            wh = np.exp(out[:, 2:4]) * self.strides
            scores = out[:, 4] * out[:, 5]
        else:
            out = out.T
            xy, wh, scores = out[:, :2], out[:, 2:4], out[:, 4]
        keep = scores >= threshold
        xy, wh, scores = xy[keep], wh[keep], scores[keep]
        boxes = np.concatenate([xy - wh / 2, xy + wh / 2], 1)
        boxes[:, [0, 2]] = (boxes[:, [0, 2]] - dx) / r
        boxes[:, [1, 3]] = (boxes[:, [1, 3]] - dy) / r
        boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, w)
        boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, h)
        if not len(boxes):
            return boxes, scores
        rects = np.c_[boxes[:, :2], boxes[:, 2:] - boxes[:, :2]].tolist()
        chosen = np.array(cv2.dnn.NMSBoxes(rects, scores.tolist(), threshold, NMS_IOU)).reshape(-1)
        return boxes[chosen], scores[chosen]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    sub = parser.add_subparsers(dest="mode", required=True)
    v = sub.add_parser("video")
    v.add_argument("video")
    v.add_argument("--every", type=int, default=3)
    v.add_argument("--out", required=True)
    c = sub.add_parser("coco")
    c.add_argument("annotations")
    c.add_argument("images")
    c.add_argument("--out", required=True)
    args = parser.parse_args()

    detector = Detector(args.model)
    seconds = []
    if args.mode == "video":
        with open(args.out, "w") as fh:
            for number, frame in Video(args.video, Preprocess()).stream(step=args.every):
                t = time.perf_counter()
                boxes, scores = detector(frame)
                seconds.append(time.perf_counter() - t)
                fh.write(json.dumps({"frame": number, "boxes": [[round(float(v), 1) for v in b] + [round(float(s), 3)]
                                                                for b, s in zip(boxes, scores)]}) + "\n")
    else:
        coco = json.load(open(args.annotations))
        results = []
        for image in coco["images"]:
            t = time.perf_counter()
            boxes, scores = detector(cv2.imread(str(Path(args.images) / image["file_name"])), threshold=0.001)
            seconds.append(time.perf_counter() - t)
            results += [{"image_id": image["id"], "category_id": 1, "score": round(float(s), 4),
                         "bbox": [round(float(b[0]), 1), round(float(b[1]), 1),
                                  round(float(b[2] - b[0]), 1), round(float(b[3] - b[1]), 1)]}
                        for b, s in zip(boxes, scores)]
        json.dump(results, open(args.out, "w"))
    print(f"{Path(args.model).stem}: {len(seconds)} images, {1000 * np.median(seconds):.0f} ms median on the CPU")


if __name__ == "__main__":
    main()
