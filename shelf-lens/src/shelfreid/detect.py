"""Bottle detectors. Each returns a list of Detection in pixels of the given frame.

`CocoDetector` is the zero-training baseline: a torchvision detector trained on COCO and
its class `bottle`. torch and torchvision are optional; they are imported on first use.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .types import Detection

COCO_BOTTLE = 44


def boxes_mask(size: tuple[int, int], detections: list[Detection]) -> np.ndarray:
    """A uint8 mask (height, width) that is 255 inside the boxes: the keypoints of the
    bottles alone, for a homography of the bottle plane."""
    mask = np.zeros((size[1], size[0]), np.uint8)
    for det in detections:
        x1, y1, x2, y2 = (int(round(v)) for v in det.box)
        mask[max(0, y1):max(0, y2), max(0, x1):max(0, x2)] = 255
    return mask


def clean_bottles(detections: list[Detection], min_score: float = 0.6,
                  max_aspect: float = 1.0, min_aspect: float = 0.15,
                  contained: float = 0.5) -> list[Detection]:
    """Drop weak boxes, boxes that are wider than tall (a standing bottle is tall; a
    whole shelf is not), thin slivers (a gap between two bottles, the edge of a bottle
    behind), and boxes that lie mostly inside a larger kept box (a neck or a half of a
    bottle)."""
    kept: list[Detection] = []
    candidates = [d for d in detections
                  if d.score >= min_score
                  and min_aspect * (d.box[3] - d.box[1]) <= d.width <= max_aspect * (d.box[3] - d.box[1])]
    for det in sorted(candidates, key=lambda d: -(d.width * (d.box[3] - d.box[1]))):
        x1, y1, x2, y2 = det.box
        area = (x2 - x1) * (y2 - y1)
        inside = False
        for other in kept:
            ix = max(0.0, min(x2, other.box[2]) - max(x1, other.box[0]))
            iy = max(0.0, min(y2, other.box[3]) - max(y1, other.box[1]))
            if ix * iy >= contained * area:
                inside = True
                break
        if not inside:
            kept.append(det)
    return kept


@dataclass
class CocoDetector:
    model_name: str = "fasterrcnn_resnet50_fpn_v2"
    threshold: float = 0.4
    device: str | None = None
    _model: object = field(default=None, init=False, repr=False)

    def _load(self):
        import torch
        import torchvision

        if self.device is None:
            self.device = "mps" if torch.backends.mps.is_available() else (
                "cuda" if torch.cuda.is_available() else "cpu")
        builder = getattr(torchvision.models.detection, self.model_name)
        model = builder(weights="DEFAULT", box_detections_per_img=300)
        self._model = model.eval().to(self.device)

    def __call__(self, image_bgr: np.ndarray) -> list[Detection]:
        import torch

        if self._model is None:
            self._load()
        rgb = np.ascontiguousarray(image_bgr[..., ::-1])
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).float().div(255).to(self.device)
        with torch.no_grad():
            output = self._model([tensor])[0]
        boxes = output["boxes"].cpu().numpy()
        labels = output["labels"].cpu().numpy()
        scores = output["scores"].cpu().numpy()
        keep = (labels == COCO_BOTTLE) & (scores >= self.threshold)
        return [Detection(tuple(map(float, box)), score=float(score))
                for box, score in zip(boxes[keep], scores[keep])]
