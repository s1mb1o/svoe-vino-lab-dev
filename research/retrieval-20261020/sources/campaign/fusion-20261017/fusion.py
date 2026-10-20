"""Combine fixed per-wine scores from the bottle and label spaces."""
import numpy as np


def order(scores, slugs):
    found = np.flatnonzero(np.isfinite(scores))
    return sorted(found.tolist(), key=lambda i: (-float(scores[i]), slugs[i]))


def gap(scores, slugs):
    ranked = order(scores, slugs)
    return float(scores[ranked[0]] - scores[ranked[1]]) if len(ranked) >= 2 else None


def merge(bottle, label, slugs, rule):
    available = np.isfinite(bottle).astype(int) + np.isfinite(label).astype(int)
    result = np.full(len(slugs), -np.inf, dtype=np.float64)
    if rule == "mean":
        present = available > 0
        total = np.where(np.isfinite(bottle), bottle, 0.) + np.where(np.isfinite(label), label, 0.)
        result[present] = total[present] / available[present]
    elif rule == "max":
        result = np.maximum(bottle, label).astype(np.float64)
    elif rule == "rrf":
        # Use all wine ranks. Each space contributes at most one rank per wine.
        for values in (bottle, label):
            for rank, number in enumerate(order(values, slugs), 1):
                if not np.isfinite(result[number]):
                    result[number] = 0.
                result[number] += 1. / (60. + rank)
    else:
        raise ValueError(rule)
    return result


def choose(bottle, label, slugs, condition):
    b_order, l_order = order(bottle, slugs), order(label, slugs)
    b_gap, l_gap = gap(bottle, slugs), gap(label, slugs)
    threshold = condition.get("threshold")
    b_confident = threshold is not None and b_gap is not None and b_gap >= threshold
    l_confident = threshold is not None and l_gap is not None and l_gap >= threshold
    conflict = bool(b_confident and l_confident and b_order[0] != l_order[0])
    trace = {"bottle_gap": b_gap, "label_gap": l_gap, "threshold": threshold,
             "bottle_confident": bool(b_confident), "label_confident": bool(l_confident),
             "confident_conflict": conflict,
             "bottle_top1": slugs[b_order[0]] if b_order else None,
             "label_top1": slugs[l_order[0]] if l_order else None}
    selected = None
    if not l_order:
        selected = "bottle"
        trace["reason"] = "missing_label"
    elif not b_order:
        selected = "label"
        trace["reason"] = "missing_bottle"
    elif conflict and condition.get("conflict_fallback"):
        trace["reason"] = "confident_winners_disagree"
    elif b_confident or l_confident:
        selected = "bottle" if b_confident and (not l_confident or b_gap >= l_gap) else "label"
        trace["reason"] = "larger_gap" if b_confident and l_confident else "one_confident_space"
    else:
        trace["reason"] = "no_gap_gate" if threshold is None else "neither_space_confident"
    trace["selected"] = selected or condition["merge"]
    result = bottle.copy() if selected == "bottle" else label.copy() if selected == "label" else merge(bottle, label, slugs, condition["merge"])
    return result, trace


def checks():
    slugs = ["a", "b", "c", "d"]
    cases = []
    b = np.array([.9, .7, .6, .5])
    l = np.array([.6, .601, .602, .603])
    value, trace = choose(b, l, slugs, {"merge": "mean", "threshold": .01})
    assert trace["selected"] == "bottle" and np.array_equal(value, b)
    cases.append("one confident bottle space keeps every original score")
    value, trace = choose(l, b, slugs, {"merge": "max", "threshold": .01})
    assert trace["selected"] == "label" and np.array_equal(value, b)
    cases.append("one confident label space keeps every original score")
    l = np.array([.6, .95, .5, .4])
    value, trace = choose(b, l, slugs, {"merge": "mean", "threshold": .01})
    assert trace["selected"] == "label" and trace["confident_conflict"]
    cases.append("two confident spaces use the larger gap")
    value, trace = choose(b, l, slugs, {"merge": "mean", "threshold": .01, "conflict_fallback": True})
    assert trace["selected"] == "mean" and np.allclose(value, (b + l) / 2)
    cases.append("conflict fallback uses the declared merge")
    l = np.full(4, -np.inf)
    value, trace = choose(b, l, slugs, {"merge": "rrf", "threshold": None})
    assert trace["selected"] == "bottle" and np.array_equal(value, b)
    cases.append("a missing label keeps the bottle list")
    l = np.array([.8, .9, .6, -np.inf])
    value = merge(b, l, slugs, "mean")
    assert np.allclose(value, [.85, .8, .6, .5])
    cases.append("mean uses available complete-space scores for each wine")
    value = merge(b, l, slugs, "max")
    assert np.array_equal(value, np.maximum(b, l))
    cases.append("unchanged merge keeps the larger original score per wine")
    value = merge(b, l, slugs, "rrf")
    assert value[0] == value[1] and order(value, slugs)[0] == 0
    cases.append("rank fusion uses stable slug order for a tie")
    value = merge(b, np.array([.8, .6, .9, .4]), slugs, "mean")
    assert order(value, slugs)[0] == 0
    cases.append("fusion does not truncate individual spaces before scoring")
    return {"passed": True, "cases": cases}
