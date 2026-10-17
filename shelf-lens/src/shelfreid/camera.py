"""Lens distortion: the one-parameter division model, its fit, and the undistortion maps.

The division model maps a distorted point p_d to an undistorted point
p_u = c + (p_d - c) / (1 + k * r_d^2), where r_d is the distance from the centre c in
units of the half diagonal. A wide-angle lens with barrel distortion has k < 0. One
parameter is enough for a moderate fisheye and keeps the fit stable with few points.

The fit uses lines that are straight in the world, for example the price tags of one shelf
edge: after the right undistortion their points are collinear.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import cv2
import numpy as np
from scipy.optimize import minimize_scalar


@dataclass(frozen=True)
class DivisionModel:
    k: float
    size: tuple[int, int]                 # (width, height) of the distorted frame
    center: tuple[float, float] | None = None

    @property
    def c(self) -> np.ndarray:
        if self.center is not None:
            return np.asarray(self.center, np.float64)
        return np.array([self.size[0] / 2, self.size[1] / 2], np.float64)

    @property
    def unit(self) -> float:
        return math.hypot(*self.size) / 2

    def undistort_points(self, points) -> np.ndarray:
        """Distorted pixels -> undistorted pixels (same centre, same unit)."""
        p = (np.asarray(points, np.float64).reshape(-1, 2) - self.c) / self.unit
        r2 = (p ** 2).sum(1, keepdims=True)
        return p / (1 + self.k * r2) * self.unit + self.c

    def distort_points(self, points) -> np.ndarray:
        """Undistorted pixels -> distorted pixels: the inverse of `undistort_points`."""
        p = (np.asarray(points, np.float64).reshape(-1, 2) - self.c) / self.unit
        ru = np.linalg.norm(p, axis=1, keepdims=True)
        if abs(self.k) < 1e-12:
            rd = ru
        else:
            # k * ru * rd^2 - rd + ru = 0, the root that tends to ru when k -> 0.
            disc = np.clip(1 - 4 * self.k * ru ** 2, 0, None)
            with np.errstate(divide="ignore", invalid="ignore"):
                rd = np.where(ru > 1e-12, (1 - np.sqrt(disc)) / (2 * self.k * ru), 0.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            scale = np.where(ru > 1e-12, rd / ru, 1.0)
        return p * scale * self.unit + self.c


@dataclass(frozen=True)
class Undistorter:
    """cv2.remap maps from the distorted frame to an undistorted frame of `out_size`.
    `zoom` < 1 shows more of the stretched border."""

    model: DivisionModel
    out_size: tuple[int, int]
    zoom: float
    map_x: np.ndarray
    map_y: np.ndarray

    @classmethod
    def build(cls, model: DivisionModel, out_size=None, zoom: float = 1.0) -> "Undistorter":
        out_size = out_size or model.size
        xs, ys = np.meshgrid(np.arange(out_size[0], dtype=np.float64),
                             np.arange(out_size[1], dtype=np.float64))
        out_c = np.array([out_size[0] / 2, out_size[1] / 2])
        undistorted = (np.c_[xs.ravel(), ys.ravel()] - out_c) / zoom + model.c
        distorted = model.distort_points(undistorted)
        shape = (out_size[1], out_size[0])
        return cls(model, out_size, zoom, distorted[:, 0].reshape(shape).astype(np.float32),
                   distorted[:, 1].reshape(shape).astype(np.float32))

    def __call__(self, image: np.ndarray) -> np.ndarray:
        return cv2.remap(image, self.map_x, self.map_y, cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_CONSTANT)

    def points(self, points) -> np.ndarray:
        """Distorted pixels -> pixels of the undistorted output frame."""
        undistorted = self.model.undistort_points(points)
        out_c = np.array([self.out_size[0] / 2, self.out_size[1] / 2])
        return (undistorted - self.model.c) * self.zoom + out_c


def line_residual(points: np.ndarray) -> float:
    """The RMS distance of points to their best line, over the RMS spread along it."""
    centred = points - points.mean(0)
    values = np.linalg.eigvalsh(centred.T @ centred / len(points))
    return math.sqrt(max(values[0], 0.0) / max(values[1], 1e-12))


def fit_division(lines: list[np.ndarray], size: tuple[int, int],
                 bounds: tuple[float, float] = (-0.6, 0.3)) -> tuple[DivisionModel, float, float]:
    """Fit k so that each group of points (one straight line in the world) is collinear.
    Return (the model, the mean residual before, the mean residual after)."""
    lines = [np.asarray(line, np.float64) for line in lines if len(line) >= 3]
    if not lines:
        raise ValueError("the fit needs at least one line of three points")

    def cost(k):
        model = DivisionModel(k, size)
        return float(np.mean([line_residual(model.undistort_points(line)) for line in lines]))

    best = minimize_scalar(cost, bounds=bounds, method="bounded", options={"xatol": 1e-4})
    return DivisionModel(float(best.x), size), cost(0.0), float(best.fun)
