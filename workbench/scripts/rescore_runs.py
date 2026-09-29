"""Score the saved lab runs again with the dataset rule of plan 87.

A photo of a wine outside the dataset leaves the metrics: a `Removed` wine, a `Disabled`
wine, or a place that `wine_catalog` does not hold. An `Active` manual wine stays.
`benchmark.outside_dataset` states the rule; a new run applies it in
`benchmark.build_queries`. This tool applies it to the runs that were made before.

Run from the workbench root:

    python3 scripts/rescore_runs.py --dry-run     # print the change, write nothing
    python3 scripts/rescore_runs.py               # write the new metrics

The tool reads the runs of `pipeline/benchmark.py` alone, and not the self-tests of
`pipeline/selftest.py`. For each run it reads
`results.jsonl`, drops the rows of the wines outside the dataset, and writes
`metrics.json` and `summary.md` again. The backend answered each photo alone, so the
kept rows are the rows that a new run gives. `results.jsonl` does not change.

- The first write keeps the old files as `metrics.before-dataset-rule.json` and
  `summary.before-dataset-rule.md`. A later call reads the rows again and keeps these
  copies.
- A run with no dropped row does not change. A re-scored run whose wines are all back
  in the dataset gets its old files back.
- The wine states are the states of the database now, not of the day of the run.
- Before a write, the tool scores all rows of the run and compares the result with the
  old metrics. A run whose numbers differ stays as it is, and the tool reports it.
- `near_duplicate_confusion` uses the variant groups of the database now.

Read `docs/plans/87_benchmark-dataset-rule.md`.
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
sys.path.insert(1, HERE)
import benchmark  # noqa: E402
from match_scoring import metrics_of, write_summary  # noqa: E402

DB_FILE = os.path.join(ROOT, "data", "catalog", "catalog.sqlite3")
PLAN = "docs/plans/87_benchmark-dataset-rule.md"
OLD_METRICS = "metrics.before-dataset-rule.json"
OLD_SUMMARY = "summary.before-dataset-rule.md"
WINE_LABELS = ("positive", "negative", "variant")
# `selftest.SET_NAME`: a self-test asks the catalogue images, not the test photos, and it
# gives its own rows to `run_benchmark`, so the rule does not apply to it.
SELFTEST_SET = "dataset"
# The numbers that the check compares: the full rows MUST give the old values.
CHECKED = ("n", "answered", "recall_at_1", "recall_at_5", "recall_at_10", "mrr")


class Backend:
    """The one attribute of a backend that `metrics_of` reads."""

    def __init__(self, backend_id):
        self.id = backend_id


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_rows(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def score(rows, old, meta, groups):
    options = meta.get("options") or {}
    return metrics_of(rows, Backend(old["backend"]), old["top_k"],
                      old.get("negative_strict", False), old.get("wall_s") or 0.0,
                      options.get("workers") or 1, groups=groups)


def differences(new, old):
    """Return the checked numbers where `new` and `old` differ."""
    out = []
    for key in CHECKED:
        if new["positive"].get(key) != old["positive"].get(key):
            out.append("positive.%s %s != %s" % (key, new["positive"].get(key),
                                                  old["positive"].get(key)))
    for key in ("f1_at_1", "f1_at_5"):
        a, b = new["positive"].get(key), old["positive"].get(key)
        if (a or {}).get("f1") != (b or {}).get("f1"):
            out.append("positive.%s %s != %s" % (key, (a or {}).get("f1"), (b or {}).get("f1")))
    if new["queries"] != old["queries"]:
        out.append("queries %s != %s" % (new["queries"], old["queries"]))
    return out


def f1_of(met, key):
    return ((met.get("positive") or {}).get(key) or {}).get("f1")


def rescore(run_dir, conn, states, dry_run):
    """Return (status, detail) of one run."""
    meta_path = os.path.join(run_dir, "run.json")
    results_path = os.path.join(run_dir, "results.jsonl")
    metrics_path = os.path.join(run_dir, "metrics.json")
    summary_path = os.path.join(run_dir, "summary.md")
    old_metrics_path = os.path.join(run_dir, OLD_METRICS)
    old_summary_path = os.path.join(run_dir, OLD_SUMMARY)
    if not (os.path.exists(meta_path) and os.path.exists(results_path)
            and os.path.exists(metrics_path)):
        return "skip", "no run.json, results.jsonl, or metrics.json"
    meta = read_json(meta_path)
    if meta.get("tool") != benchmark.TOOL:
        return "skip", "not a run of %s" % benchmark.TOOL
    if (meta.get("options") or {}).get("set") == SELFTEST_SET:
        return "skip", "a self-test of catalogue images"
    has_copy = os.path.exists(old_metrics_path)
    old = read_json(old_metrics_path if has_copy else metrics_path)
    if old.get("unlabelled"):
        return "skip", "a run of a photos directory"
    rows = read_rows(results_path)
    if not rows:
        return "skip", "no rows"
    set_name = (meta.get("options") or {}).get("set")
    try:
        groups = benchmark.load_groups(conn, set_name) if set_name else {}
    except sqlite3.Error:
        groups = {}

    diff = differences(score(rows, old, meta, groups), old)
    if diff:
        return "mismatch", "; ".join(diff)

    left_out = {}
    kept = []
    for row in rows:
        reason = (benchmark.outside_dataset(row["slug"], states)
                  if row.get("label") in WINE_LABELS else None)
        if reason:
            left_out[reason] = left_out.get(reason, 0) + 1
        else:
            kept.append(row)

    if not left_out:
        if not has_copy:
            return "same", ""
        if not dry_run:
            shutil.copyfile(old_metrics_path, metrics_path)
            shutil.copyfile(old_summary_path, summary_path)
            os.remove(old_metrics_path)
            os.remove(old_summary_path)
        return "restored", "every wine is in the dataset again"

    met = score(kept, old, meta, groups)
    met["run_id"] = old.get("run_id") or meta.get("run_id")
    met["dataset_rule"] = {
        "plan": PLAN,
        "left_out": dict(sorted(left_out.items())),
        "rows_of_the_run": len(rows),
        "rescored_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "old_metrics": OLD_METRICS,
    }
    detail = "left out %s; F1@1 %s -> %s; F1@5 %s -> %s" % (
        dict(sorted(left_out.items())), f1_of(old, "f1_at_1"), f1_of(met, "f1_at_1"),
        f1_of(old, "f1_at_5"), f1_of(met, "f1_at_5"))
    if dry_run:
        return "rescored", detail
    if not has_copy:
        shutil.copyfile(metrics_path, old_metrics_path)
        shutil.copyfile(summary_path, old_summary_path)
    with open(metrics_path, "w", encoding="utf-8") as fh:
        json.dump(met, fh, ensure_ascii=False, indent=2, sort_keys=True)
    write_summary(summary_path, meta, met)
    with open(summary_path, "a", encoding="utf-8") as fh:
        fh.write("\n".join([
            "",
            "## Dataset rule",
            "",
            "This summary was scored again on %s with the rule of `%s`. The photos of"
            % (met["dataset_rule"]["rescored_at"], PLAN),
            "a wine outside the dataset left the metrics: %s."
            % ", ".join("%s %d" % item for item in sorted(left_out.items())),
            "The run asked %d photos. `%s` holds the old numbers."
            % (len(rows), OLD_SUMMARY),
            "",
        ]))
    return "rescored", detail


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs-dir", default=benchmark.RUNS_DIR)
    parser.add_argument("--db", default=DB_FILE)
    parser.add_argument("--run", default=None, help="only the runs whose name holds this text")
    parser.add_argument("--dry-run", action="store_true", help="write nothing")
    parser.add_argument("--verbose", action="store_true", help="also print the unchanged runs")
    args = parser.parse_args(argv)

    conn = sqlite3.connect("file:%s?mode=ro" % os.path.abspath(args.db), uri=True)
    try:
        states = benchmark.wine_states(conn)
        counts = {}
        for name in sorted(os.listdir(args.runs_dir)):
            run_dir = os.path.join(args.runs_dir, name)
            if not os.path.isdir(run_dir) or (args.run and args.run not in name):
                continue
            status, detail = rescore(run_dir, conn, states, args.dry_run)
            counts[status] = counts.get(status, 0) + 1
            if status in ("rescored", "restored", "mismatch") or args.verbose:
                print("%-9s %s  %s" % (status, name, detail))
    finally:
        conn.close()
    print("%s: %s" % ("dry run" if args.dry_run else "done",
                      ", ".join("%s %d" % item for item in sorted(counts.items()))))
    return 1 if counts.get("mismatch") else 0


if __name__ == "__main__":
    sys.exit(main())
