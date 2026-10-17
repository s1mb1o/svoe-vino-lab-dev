import numpy as np

from shelfreid.associate import associate
from shelfreid.types import Detection

SIZE = (1000, 500)


def row(count, x0=50.0, step=100.0, width=60.0):
    return [Detection((x0 + i * step, 100.0, x0 + i * step + width, 400.0), id=str(i))
            for i in range(count)]


def shift(dx, dy=0.0):
    """The homography of frame B to frame A when frame B lies `dx` px right of frame A."""
    return np.array([[1, 0, dx], [0, 1, dy], [0, 0, 1]], float)


def statuses(decisions):
    return [(d.status, d.match) for d in decisions]


def test_half_overlap_marks_the_shared_half_as_seen():
    # Frame B starts in the middle of frame A: bottle i of B is bottle i + 5 of A.
    decisions = associate(row(10), row(10), shift(500), SIZE, SIZE)
    assert statuses(decisions) == [("seen", i + 5) for i in range(5)] + [("new", None)] * 5


def test_identity_matches_every_bottle_to_itself():
    decisions = associate(row(10), row(10), shift(0), SIZE, SIZE)
    assert statuses(decisions) == [("seen", i) for i in range(10)]


def test_a_shift_of_half_a_step_matches_no_neighbour():
    # 50 px is 0.83 of a bottle width: no bottle of B is a bottle of A.
    decisions = associate(row(10), row(10), shift(50), SIZE, SIZE)
    assert {d.status for d in decisions if d.index < 9} == {"new_in_overlap"}


def test_one_bottle_of_a_takes_one_bottle_of_b():
    dets_a = [Detection((500.0, 100.0, 560.0, 400.0))]
    dets_b = [Detection((500.0, 100.0, 560.0, 400.0)), Detection((524.0, 100.0, 584.0, 400.0))]
    decisions = associate(dets_a, dets_b, shift(0), SIZE, SIZE)
    assert statuses(decisions) == [("seen", 0), ("new_in_overlap", None)]


def test_a_bottle_cut_by_the_edge_of_a_is_seen():
    # The bottle spans 980..1080 in frame A; frame A shows only 980..1000.
    dets_a = [Detection((980.0, 100.0, 1000.0, 400.0))]
    dets_b = [Detection((480.0, 100.0, 580.0, 400.0))]
    decisions = associate(dets_a, dets_b, shift(500), SIZE, SIZE)
    assert statuses(decisions) == [("seen", 0)]


def test_frames_without_overlap_give_only_new_bottles():
    decisions = associate(row(3), row(3), shift(2000), SIZE, SIZE)
    assert {d.status for d in decisions} == {"new"}
