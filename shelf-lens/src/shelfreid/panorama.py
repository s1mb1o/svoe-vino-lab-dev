"""A panorama of keyframes joined by chained homographies, to check a registration by eye."""

from __future__ import annotations

import cv2
import numpy as np

from .homography import corners, project


def chain(steps: list[np.ndarray]) -> list[np.ndarray]:
    """Given H_i that maps keyframe i+1 into keyframe i, return the maps of each keyframe
    into keyframe 0 (the first map is the identity)."""
    maps = [np.eye(3)]
    for H in steps:
        maps.append(maps[-1] @ H)
    return maps


def compose(frames: list[np.ndarray], maps: list[np.ndarray], scale: float = 0.25,
            strip: float = 0.5) -> np.ndarray:
    """Warp the frames into the plane of keyframe 0. Each frame gives its central vertical
    strip of `strip` of its width, where the residual lens distortion is smallest; a later
    frame covers an earlier one."""
    height, width = frames[0].shape[:2]
    S = np.diag([scale, scale, 1.0])
    quads = np.vstack([project(S @ M, corners((width, height))) for M in maps])
    x0, y0 = np.floor(quads.min(0)).astype(int)
    x1, y1 = np.ceil(quads.max(0)).astype(int)
    T = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]], float)
    size = (int(x1 - x0), int(y1 - y0))
    canvas = np.full((size[1], size[0], 3), 255, np.uint8)
    mask = np.zeros((height, width), np.uint8)
    left = int(width * (1 - strip) / 2)
    mask[:, left:width - left] = 255
    for frame, M in zip(frames, maps):
        warp = T @ S @ M
        image = cv2.warpPerspective(frame, warp, size)
        region = cv2.warpPerspective(mask, warp, size) > 127
        canvas[region] = image[region]
    return canvas
