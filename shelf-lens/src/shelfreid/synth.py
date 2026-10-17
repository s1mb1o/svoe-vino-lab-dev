"""Synthetic shelves and pairs of views with a known answer.

A scene is a long shelf with runs of identical bottles (one wine stands side by side)
and a price tag under each run. Two views cut overlapping windows of the scene with a
random perspective, so the true homography and the true bottle identities are known.
The repeated labels make the scene hard in the same way as a real shelf.
"""

from __future__ import annotations

from dataclasses import dataclass
import string

import cv2
import numpy as np

from .associate import box_corners, bbox_of, clip
from .homography import project
from .types import Box, Detection


@dataclass
class Scene:
    image: np.ndarray
    boxes: list[Box]


@dataclass
class SynthPair:
    image_a: np.ndarray
    image_b: np.ndarray
    dets_a: list[Detection]
    dets_b: list[Detection]
    H: np.ndarray            # the true homography B -> A


def _color(rng, low=0, high=255):
    return tuple(int(c) for c in rng.integers(low, high, 3))


def _label(rng, width: int, height: int) -> np.ndarray:
    label = np.full((height, width, 3), _color(rng, 120, 255), np.uint8)
    for _ in range(rng.integers(1, 4)):
        y = int(rng.integers(0, height))
        cv2.rectangle(label, (0, y), (width, y + int(rng.integers(3, 12))), _color(rng), -1)
    cv2.circle(label, (int(rng.integers(0, width)), int(rng.integers(0, height // 2))),
               int(rng.integers(5, width // 3)), _color(rng), -1)
    word = "".join(rng.choice(list(string.ascii_uppercase), int(rng.integers(3, 7))))
    cv2.putText(label, word, (4, int(height * 0.7)), cv2.FONT_HERSHEY_SIMPLEX,
                width / 120, _color(rng, 0, 90), 2, cv2.LINE_AA)
    return label


def shelf_scene(rng: np.random.Generator, width: int = 3200, height: int = 1500,
                rows: int = 3, run: tuple[int, int] = (1, 5)) -> Scene:
    """Return a shelf with `rows` rows of bottles and the box of each bottle."""
    image = np.full((height, width, 3), 45, np.uint8)
    noise = rng.integers(-12, 12, (height // 8, width // 8, 1)).astype(np.int16)
    image = np.clip(image + cv2.resize(noise, (width, height))[..., None], 0, 255).astype(np.uint8)
    boxes: list[Box] = []
    row_height = height // rows
    for row in range(rows):
        bottom = (row + 1) * row_height - 60
        cv2.rectangle(image, (0, bottom), (width, bottom + 60), (205, 205, 200), -1)
        x = int(rng.integers(10, 40))
        while x < width - 160:
            bottle_width = int(rng.integers(70, 111))
            body = int(rng.integers(row_height - 230, row_height - 150))
            neck = int(rng.integers(60, 90))
            glass, cap = _color(rng, 10, 90), _color(rng)
            label = _label(rng, bottle_width - 10, int(body * 0.45))
            run_start = x
            for _ in range(int(rng.integers(run[0], run[1] + 1))):
                if x + bottle_width > width - 10:
                    break
                top = bottom - body
                cv2.rectangle(image, (x, top), (x + bottle_width, bottom), glass, -1)
                neck_x = x + bottle_width // 2 - bottle_width // 6
                cv2.rectangle(image, (neck_x, top - neck), (neck_x + bottle_width // 3, top),
                              glass, -1)
                cv2.rectangle(image, (neck_x, top - neck), (neck_x + bottle_width // 3,
                              top - neck + 25), cap, -1)
                label_top = top + int(body * 0.3)
                image[label_top:label_top + label.shape[0], x + 5:x + 5 + label.shape[1]] = label
                boxes.append((float(x), float(top - neck), float(x + bottle_width), float(bottom)))
                x += bottle_width + int(rng.integers(4, 15))
            tag = (run_start, bottom + 8, run_start + 95, bottom + 52)
            cv2.rectangle(image, tag[:2], tag[2:], (40, 220, 240) if rng.random() < 0.5
                          else (250, 250, 250), -1)
            cv2.putText(image, str(int(rng.integers(199, 2999))), (tag[0] + 6, tag[3] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 20), 2, cv2.LINE_AA)
            x += int(rng.integers(10, 40))
    return Scene(image, boxes)


def _view(scene: Scene, rng, left: float, window: tuple[float, float], size: tuple[int, int],
          jitter: float):
    """Cut one view: the window at `left` with each corner moved by up to `jitter`."""
    window_width, window_height = window
    top = (scene.image.shape[0] - window_height) / 2
    source = np.array([[left, top], [left + window_width, top],
                       [left + window_width, top + window_height], [left, top + window_height]],
                      np.float64)
    source += rng.uniform(-jitter, jitter, (4, 2)) * window_width
    target = np.array([[0, 0], [size[0], 0], [size[0], size[1]], [0, size[1]]], np.float64)
    H = cv2.getPerspectiveTransform(source.astype(np.float32), target.astype(np.float32))
    image = cv2.warpPerspective(scene.image, H, size, borderMode=cv2.BORDER_CONSTANT,
                                borderValue=(40, 40, 40))
    detections = []
    frame: Box = (0.0, 0.0, float(size[0]), float(size[1]))
    for number, box in enumerate(scene.boxes):
        mapped = bbox_of(project(H, box_corners(box)))
        visible = clip(mapped, frame)
        if visible is None:
            continue
        area = (mapped[2] - mapped[0]) * (mapped[3] - mapped[1])
        if (visible[2] - visible[0]) * (visible[3] - visible[1]) >= 0.6 * area:
            detections.append(Detection(visible, id=str(number)))
    return image, detections, H


def _photometric(image: np.ndarray, rng) -> np.ndarray:
    out = image.astype(np.float32) * rng.uniform(0.85, 1.15) + rng.uniform(-15, 15)
    out = cv2.GaussianBlur(out, (0, 0), rng.uniform(0.3, 1.0))
    out += rng.normal(0, 3, out.shape)
    return np.clip(out, 0, 255).astype(np.uint8)


def pair(scene: Scene, rng: np.random.Generator, overlap: float = 0.5,
         window_share: float = 0.4, view_width: int = 1200, jitter: float = 0.04) -> SynthPair:
    """Two views of `scene` whose windows overlap by `overlap` of the window width."""
    height, width = scene.image.shape[:2]
    window_width = width * window_share
    window = (window_width, height * 0.9)
    size = (view_width, round(view_width * window[1] / window_width))
    step = window_width * (1 - overlap)
    left = rng.uniform(0, width - window_width - step)
    image_a, dets_a, H_a = _view(scene, rng, left, window, size, jitter)
    image_b, dets_b, H_b = _view(scene, rng, left + step, window, size, jitter)
    return SynthPair(image_a, _photometric(image_b, rng), dets_a, dets_b, H_a @ np.linalg.inv(H_b))
