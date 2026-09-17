"""Score the output of `bench_vlm_models.py` against the manual labels.

Two decision rules are scored.

1. `same_wine`: the raw answer of the model to the identity question.
2. `accept`: the production rule of stage 5, `same_wine AND NOT studio AND front_label`.

The positive class is the label 'positive'. The labels 'negative' and 'unusable'
are the negative class. A parse failure counts as a negative answer, because
stage 4 stores no acceptance for such a call.

Usage:
    python3 scripts/bench_vlm_score.py [--in work/vlm_bench.jsonl] [--md report.md]
"""
import argparse
import collections
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def rates(tp, fp, tn, fn):
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    acc = (tp + tn) / (tp + fp + tn + fn) if tp + fp + tn + fn else 0.0
    return prec, rec, f1, acc


def score(rows, rule):
    tp = fp = tn = fn = 0
    per_label = collections.Counter()
    for r in rows:
        truth = r["label"] == "positive"
        p = r.get("parsed")
        if not p:
            pred = False
        elif rule == "same_wine":
            pred = bool(p["same"])
        else:
            pred = bool(p["same"]) and not p["studio"] and bool(p["front"])
        if truth and pred:
            tp += 1
        elif truth and not pred:
            fn += 1
        elif not truth and pred:
            fp += 1
        else:
            tn += 1
        if pred:
            per_label[r["label"]] += 1
    return tp, fp, tn, fn, per_label


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=str(ROOT / "work" / "vlm_bench.jsonl"))
    ap.add_argument("--md", default=None, help="also write a markdown report to this path")
    args = ap.parse_args()

    rows = [json.loads(l) for l in Path(args.inp).read_text().splitlines() if l.strip()]
    by_model = collections.defaultdict(list)
    for r in rows:
        by_model[r["model"]].append(r)

    counts = collections.Counter(r["label"] for r in by_model[next(iter(by_model))])
    out = []
    out.append("Pairs per model: %d  (positive %d, negative %d, unusable %d)"
               % (len(next(iter(by_model.values()))), counts["positive"],
                  counts["negative"], counts["unusable"]))
    out.append("")

    # The label 'unusable' is a fuzzy negative. A photo can show the correct wine
    # and still be unusable for the set. The headline tables therefore use the
    # clean identity task, 'positive' against 'negative'. The 'unusable' stratum
    # is reported on its own below.
    for scope in ("core", "all"):
        title = ("positive vs negative only" if scope == "core"
                 else "positive vs negative + unusable")
        out.append("# Scope: %s" % title)
        out.append("")
        for rule in ("same_wine", "accept"):
            out.append("## Rule: `%s`" % rule)
            out.append("")
            out.append("| Model | Prec | Recall | F1 | Acc | TP | FP | FN | TN |")
            out.append("|---|---|---|---|---|---|---|---|---|")
            ranked = []
            for m, rs in by_model.items():
                sub = [r for r in rs if scope == "all" or r["label"] != "unusable"]
                tp, fp, tn, fn, _ = score(sub, rule)
                prec, rec, f1, acc = rates(tp, fp, tn, fn)
                ranked.append((f1, m, prec, rec, f1, acc, tp, fp, fn, tn))
            for _, m, prec, rec, f1, acc, tp, fp, fn, tn in sorted(ranked, reverse=True):
                out.append("| `%s` | %.3f | %.3f | %.3f | %.3f | %d | %d | %d | %d |"
                           % (m, prec, rec, f1, acc, tp, fp, fn, tn))
            out.append("")

    out.append("## Error source (rule `accept`, share of each stratum accepted)")
    out.append("")
    out.append("| Model | positive accepted (want high) | negative accepted (want 0) "
               "| unusable accepted (want 0) |")
    out.append("|---|---|---|---|")
    for m, rs in by_model.items():
        _, _, _, _, per = score(rs, "accept")
        out.append("| `%s` | %d/%d | %d/%d | %d/%d |"
                   % (m, per["positive"], counts["positive"],
                      per["negative"], counts["negative"],
                      per["unusable"], counts["unusable"]))
    out.append("")

    out.append("## Cost and reliability")
    out.append("")
    out.append("| Model | Calls | Errors | Parse fail | Latency med | Latency p90 "
               "| Prompt tk | Completion tk |")
    out.append("|---|---|---|---|---|---|---|---|")
    for m, rs in by_model.items():
        ok = [r for r in rs if r.get("ok")]
        lat = sorted(r["latency_s"] for r in ok) or [0]
        p90 = lat[min(len(lat) - 1, int(0.9 * len(lat)))]
        pt = sum(r.get("usage", {}).get("prompt_tokens", 0) for r in ok)
        ct = sum(r.get("usage", {}).get("completion_tokens", 0) for r in ok)
        out.append("| `%s` | %d | %d | %d | %.1f s | %.1f s | %d | %d |"
                   % (m, len(rs), len(rs) - len(ok),
                      sum(1 for r in ok if not r.get("parsed")),
                      statistics.median(lat), p90, pt, ct))
    out.append("")
    total_pt = sum(r.get("usage", {}).get("prompt_tokens", 0) for r in rows if r.get("ok"))
    total_ct = sum(r.get("usage", {}).get("completion_tokens", 0) for r in rows if r.get("ok"))
    out.append("Total tokens: %d prompt, %d completion." % (total_pt, total_ct))

    text = "\n".join(out)
    print(text)
    if args.md:
        Path(args.md).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
