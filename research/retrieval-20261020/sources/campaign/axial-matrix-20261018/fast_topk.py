"""Select the same lexical Top-10 with less temporary memory."""
import numpy as np


def topk(scores, k=10):
    scores = np.asarray(scores)
    numbers = np.argpartition(scores, -k, axis=1)[:, -k:]
    values = np.take_along_axis(scores, numbers, axis=1)
    cutoff = values.min(1)
    # A partition can select an arbitrary member of a boundary tie.
    boundary = (scores == cutoff[:, None]).sum(1) > (values == cutoff[:, None]).sum(1)
    for row in np.flatnonzero(boundary):
        better = np.flatnonzero(scores[row] > cutoff[row])
        ties = np.flatnonzero(scores[row] == cutoff[row])
        numbers[row] = np.r_[better, ties[:k-len(better)]]
    numbers.sort(axis=1)
    values = np.take_along_axis(scores, numbers, axis=1)
    order = np.argsort(-values, axis=1, kind="stable")
    numbers = np.take_along_axis(numbers, order, axis=1)
    values = np.take_along_axis(values, order, axis=1)
    numbers[~np.isfinite(values)] = -1
    return numbers.astype(np.int16), values


if __name__ == "__main__":
    import sys
    import time
    from settings import ROOT, HERE, dump
    sys.path.insert(0, str(ROOT / "my-matrix-20261017"))
    import core
    rng = np.random.default_rng(1008)
    tests = [rng.normal(size=(3031, 2274)), np.ones((30, 2274)), rng.integers(0, 20, (200, 2274)).astype(float), np.full((3, 2274), -np.inf)]
    tests += [np.load(ROOT / "my-matrix-20261017/components" / name) for name in ("b-6b-mean-iou-rot5.npy", "l-7g-rot5.npy")]
    timings = []
    for scores in tests:
        began = time.monotonic()
        expected = core.topk(scores)
        old_time = time.monotonic()-began
        began = time.monotonic()
        actual = topk(scores)
        new_time = time.monotonic()-began
        assert all(np.array_equal(a, b) for a, b in zip(expected, actual))
        timings.append(dict(shape=list(scores.shape), old_seconds=old_time, new_seconds=new_time))
    dump(HERE / "topk-controls.json", dict(passed=True, tests=timings, tie_rule="Ascending wine_slug", note="Partition is followed by explicit boundary tie repair."))
    print(timings)
