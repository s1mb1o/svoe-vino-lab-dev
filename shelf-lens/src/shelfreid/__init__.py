"""Find the unique bottles of a shelf over several photos or video frames.

The identity of a bottle is its place on the shelf, not its look: bottles of one wine
stand side by side and look the same. Two frames are joined by a homography of the shelf
front, and the bottles of the new frame are compared with the known bottles by position.
"""

from .types import Decision, Detection
from .pair import PairConfig, PairResult, match_pair

__all__ = ["Decision", "Detection", "PairConfig", "PairResult", "match_pair"]
