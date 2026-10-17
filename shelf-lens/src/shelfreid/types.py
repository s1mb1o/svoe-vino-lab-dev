"""Shared data types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# x1, y1, x2, y2 in pixels of the frame.
Box = tuple[float, float, float, float]


@dataclass(frozen=True)
class Detection:
    """One bottle of one frame."""

    box: Box
    id: str | None = None
    score: float = 1.0
    label: str = "bottle"

    @property
    def width(self) -> float:
        return self.box[2] - self.box[0]


# seen: the bottle is a bottle of frame A.
# new: the bottle lies outside frame A.
# new_in_overlap: the bottle lies inside frame A, but frame A has no bottle there
#   (a missed detection or an occluded bottle).
# unregistered: the frames could not be joined, so nothing is known.
Status = Literal["seen", "new", "new_in_overlap", "unregistered"]


@dataclass(frozen=True)
class Decision:
    """The decision for one bottle of frame B."""

    index: int
    status: Status
    match: int | None = None
    # The anchor distance to the matched bottle of frame A, in bottle widths.
    distance: float | None = None
