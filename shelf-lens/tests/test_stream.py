import numpy as np

from shelfreid import synth
from shelfreid.stream import ShelfTracker


def pan(scene, lefts, window=(900.0, 1200.0), size=(450, 600)):
    """Frames of a camera that moves along the shelf to the given window positions."""
    rng = np.random.default_rng(0)
    for left in lefts:
        image, detections, _ = synth._view(scene, rng, left, window, size, jitter=0.0)
        yield image, detections


def test_a_pan_there_and_back_finds_each_bottle_once_and_marks_the_return():
    rng = np.random.default_rng(3)
    scene = synth.shelf_scene(rng, width=3200, height=1300)
    forward = np.arange(0, 2200, 40.0)
    tracker = ShelfTracker((450, 600))
    seen_ids = set()
    returning = shown_back = 0
    for step, (image, dets) in enumerate(pan(scene, list(forward) + list(forward[::-1]))):
        shown = tracker.step(step, image, dets)
        seen_ids |= {d.id for d in dets}
        if step >= len(forward) + 15:          # well into the way back
            active = [s for s in shown if s.status != "ignored"]
            shown_back += len(active)
            returning += sum(s.status == "returning" for s in active)
    assert len(tracker.bottles) <= 1.1 * len(seen_ids)
    assert returning >= 0.8 * shown_back
