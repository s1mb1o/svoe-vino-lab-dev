"""Frames of a video, upright and undistorted."""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from .camera import DivisionModel, Undistorter

ROTATIONS = {0: None, 90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180,
             270: cv2.ROTATE_90_COUNTERCLOCKWISE}


@dataclass(frozen=True)
class Preprocess:
    """The steps of each frame: rotate (degrees clockwise), scale, undistort."""

    rotate: int = 0
    scale: float = 1.0           # applied after the rotation
    k: float = 0.0               # the division model of the lens; 0 is no undistortion
    zoom: float = 1.0            # the zoom of the undistorted frame; < 1 shows more border


@dataclass
class Video:
    path: str
    steps: Preprocess = field(default_factory=Preprocess)

    def __post_init__(self):
        self.capture = cv2.VideoCapture(self.path)
        if not self.capture.isOpened():
            raise OSError(f"cannot open the video {self.path}")
        self.fps = self.capture.get(cv2.CAP_PROP_FPS)
        self.frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self._undistort = None

    @property
    def duration(self) -> float:
        return self.frames / self.fps

    def _prepare(self, frame: np.ndarray) -> np.ndarray:
        if ROTATIONS[self.steps.rotate] is not None:
            frame = cv2.rotate(frame, ROTATIONS[self.steps.rotate])
        if self.steps.scale != 1.0:
            frame = cv2.resize(frame, None, fx=self.steps.scale, fy=self.steps.scale,
                               interpolation=cv2.INTER_AREA)
        if self.steps.k:
            if self._undistort is None:
                size = (frame.shape[1], frame.shape[0])
                self._undistort = Undistorter.build(DivisionModel(self.steps.k, size),
                                                    zoom=self.steps.zoom)
            frame = self._undistort(frame)
        return frame

    def at(self, seconds: float) -> np.ndarray:
        """The frame at `seconds`, prepared."""
        return self.index(round(seconds * self.fps))

    def index(self, number: int) -> np.ndarray:
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, number)
        ok, frame = self.capture.read()
        if not ok:
            raise IndexError(f"no frame {number} in {self.path}")
        return self._prepare(frame)

    def stream(self, start: int = 0, stop: int | None = None, step: int = 1):
        """Yield (frame number, prepared frame), reading the video in order."""
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, start)
        stop = self.frames if stop is None else min(stop, self.frames)
        number = start
        while number < stop:
            ok, frame = self.capture.read()
            if not ok:
                break
            if (number - start) % step == 0:
                yield number, self._prepare(frame)
            number += 1


# The robot video of the Lenta hackathon: shot on its side with a wide-angle lens.
# k is a plumb-line fit of long image edges and of the price-tag rows.
LENTA_ROBOT = Preprocess(rotate=270, scale=0.5, k=-0.47, zoom=0.7)
