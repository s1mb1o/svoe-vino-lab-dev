"""How a detector serves the tracker, against the reference run (cached Faster R-CNN):

- recall: the share of the boxes that the reference tracker carried (boxes with an id)
  that the detector finds (IoU >= 0.5) at each least score;
- the tracker on the detector's boxes (a replay dump): bottles, ids, and how its ids agree
  with the reference ids, box to box through the best mapping of ids (boxes paired by IoU).

    uv run python scripts/eval_detector.py REF_DUMP DETS.jsonl [RUN_DUMP]
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict

import numpy as np
from scipy.optimize import linear_sum_assignment


def iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if not len(a) or not len(b):
        return np.zeros((len(a), len(b)))
    x1 = np.maximum(a[:, None, 0], b[None, :, 0]); y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2]); y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area = lambda r: (r[:, 2] - r[:, 0]) * (r[:, 3] - r[:, 1])
    return inter / (area(a)[:, None] + area(b)[None, :] - inter)


def pairs(a: np.ndarray, b: np.ndarray, least: float = 0.5) -> list[tuple[int, int]]:
    iou = iou_matrix(a, b)
    if not iou.size:
        return []
    rows, cols = linear_sum_assignment(-iou)
    return [(r, c) for r, c in zip(rows, cols) if iou[r, c] >= least]


def main():
    ref = {r[0]: r[1] for r in map(json.loads, open(sys.argv[1]))}
    dets = {r["frame"]: r["boxes"] for r in map(json.loads, open(sys.argv[2]))}
    carried = {n: np.array([x[:4] for x in s if x[5] is not None], float).reshape(-1, 4) for n, s in ref.items()}
    total = sum(len(v) for v in carried.values())
    line = []
    for least in (0.2, 0.3, 0.4, 0.5):
        found = 0
        count = 0
        for n, boxes in carried.items():
            mine = np.array([b[:4] for b in dets.get(n, []) if b[4] >= least], float).reshape(-1, 4)
            count += len(mine)
            found += len(pairs(boxes, mine))
        line.append(f"recall@{least} {found / total:.3f} ({count / len(carried):.0f}/frame)")
    print(f"carried boxes {total} ({total / len(carried):.0f}/frame) | " + ", ".join(line))
    if len(sys.argv) > 3:
        run = {r[0]: r[1] for r in map(json.loads, open(sys.argv[3]))}
        counts = Counter()
        for n in sorted(set(ref) & set(run)):
            a = [x for x in ref[n] if x[5] is not None]
            b = [x for x in run[n] if x[5] is not None]
            for i, j in pairs(np.array([x[:4] for x in a], float).reshape(-1, 4),
                              np.array([x[:4] for x in b], float).reshape(-1, 4)):
                counts[(b[j][5], a[i][5])] += 1
        best = {}
        for (m, t), c in counts.most_common():
            best.setdefault(m, t)
        agree = sum(c for (m, t), c in counts.items() if best[m] == t) / max(sum(counts.values()), 1)
        splits = Counter(best.values())
        owners = defaultdict(set)
        for (m, t), c in counts.items():
            if c >= 3:
                owners[m].add(t)
        ref_ids = {x[5] for s in ref.values() for x in s if x[5] is not None}
        run_ids = {x[5] for s in run.values() for x in s if x[5] is not None}
        covered = len(set(best.values())) / max(len(ref_ids), 1)
        print(f"tracker: ids shown {len(run_ids)} (reference {len(ref_ids)}), reference bottles covered {covered:.3f}, "
              f"ids agree {agree:.3f}, extra ids {sum(v - 1 for v in splits.values() if v > 1)}, "
              f"ids over two {sum(1 for ts in owners.values() if len(ts) > 1)}")


if __name__ == "__main__":
    main()
