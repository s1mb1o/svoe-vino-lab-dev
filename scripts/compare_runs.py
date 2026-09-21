"""Compare two or more runs on the photos they share.

The test set grows while the work goes on, so two runs rarely hold the same
photos. A difference in R@1 between a run of 1,553 photos and a run of 1,881
photos says nothing by itself: the two numbers come from two different sets.
This tool pairs the runs on the photos that all of them answered, and reports
the difference on that shared set alone.

Run:

    python3 scripts/compare_runs.py <baseline-run> <run> [<run> ...]

A run is a directory under `runs/`, or its `results.jsonl`.

Photos are paired by `image_path`, which is `<slug>/<file name>` and does not
change when a run is repeated. `image_sha256` is compared as a check: a pair
whose bytes differ is dropped and counted, because the same name then held two
different images and the pair would compare two different questions.

Positive and negative photos are reported apart, because they ask opposite
questions. A positive photo is answered when its own slug comes back at rank 1.
A negative photo shows a different wine, so it is answered when its slug does
NOT come back at rank 1.

The reported test is the exact McNemar test: the two-sided binomial test over
the discordant pairs alone, the photos one run answered and the other did not.
Concordant pairs carry no information about a difference.

A photo that returned an error or no answer counts as NOT answered. This is
conservative: it never credits a run for failing to reply.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

# What `match_run.py` writes when the run answered the photo correctly at
# rank 1. Every other outcome, including `no_answer`, counts as not answered.
ANSWERED = {"positive": "hit", "negative": "other_slug_at_1"}


def load_run(path: str) -> tuple[str, dict[str, dict]]:
    """Return (run_id, {image_path: row}) for one run."""
    if path.endswith("results.jsonl"):
        run_dir = os.path.dirname(os.path.normpath(path))
    else:
        run_dir = os.path.normpath(path)
    results = os.path.join(run_dir, "results.jsonl")
    if not os.path.exists(results):
        sys.exit(f"error: no results.jsonl in {run_dir}")
    run_id = os.path.basename(run_dir)
    meta = os.path.join(run_dir, "run.json")
    if os.path.exists(meta):
        with open(meta, encoding="utf-8") as fh:
            run_id = json.load(fh).get("run_id", run_id)
    rows: dict[str, dict] = {}
    with open(results, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            rows[row["image_path"]] = row
    return run_id, rows


def answered(row: dict) -> bool:
    return row.get("outcome") == ANSWERED.get(row.get("label"))


def exact_mcnemar(wins: int, losses: int) -> float:
    """Two-sided exact McNemar p over the discordant pairs."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2.0 ** n)
    return min(1.0, 2.0 * tail)


def report(title: str, keys: list[str], loaded: list[tuple[str, dict]],
           rate_name: str) -> None:
    if not keys:
        print("%s: no photo of this kind is shared\n" % title)
        return
    base_id, base_rows = loaded[0]
    base_ok = {k: answered(base_rows[k]) for k in keys}
    base_rate = sum(base_ok.values()) / len(keys)

    print("%s — %d shared photos" % (title, len(keys)))
    print("%-44s %9s %9s %6s %7s %10s" %
          ("run", rate_name, "delta", "wins", "losses", "exact p"))
    print("-" * 90)
    print("%-44s %9.4f %9s %6s %7s %10s"
          % (base_id[:44], base_rate, "baseline", "", "", ""))
    for run_id, rows in loaded[1:]:
        ok = {k: answered(rows[k]) for k in keys}
        rate = sum(ok.values()) / len(keys)
        wins = sum(1 for k in keys if ok[k] and not base_ok[k])
        losses = sum(1 for k in keys if base_ok[k] and not ok[k])
        print("%-44s %9.4f %+9.4f %6d %7d %10.3g"
              % (run_id[:44], rate, rate - base_rate, wins, losses,
                 exact_mcnemar(wins, losses)))
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description="Compare runs on the photos they share")
    ap.add_argument("runs", nargs="+", metavar="RUN",
                    help="the baseline first, then every run to compare with it")
    ap.add_argument("--title", default="", help="a title for the report")
    args = ap.parse_args()
    if len(args.runs) < 2:
        sys.exit("error: name at least two runs")

    loaded = [load_run(p) for p in args.runs]
    shared = set(loaded[0][1])
    for _, rows in loaded[1:]:
        shared &= set(rows)

    # Drop any photo whose bytes differ between the runs. The name then held
    # two different images and the pair would compare two different questions.
    mismatched = {k for k in shared
                  if len({rows[k].get("image_sha256") for _, rows in loaded} - {None}) > 1}
    shared -= mismatched
    if not shared:
        sys.exit("error: the runs share no photo")

    keys = sorted(shared)
    if args.title:
        print(args.title)
        print()
    for run_id, rows in loaded:
        print("  %-52s %5d photos" % (run_id, len(rows)))
    print("shared photos   : %d" % len(keys))
    if mismatched:
        print("dropped         : %d photo(s) whose bytes differ between the runs"
              % len(mismatched))
    for run_id, rows in loaded:
        n = sum(1 for k in keys if rows[k].get("error"))
        if n:
            print("errors          : %d in %s (each counts as not answered)"
                  % (n, run_id))
    print()

    pos = [k for k in keys if loaded[0][1][k].get("label") == "positive"]
    neg = [k for k in keys if loaded[0][1][k].get("label") == "negative"]
    report("POSITIVE photos: the wine of the slug", pos, loaded, "R@1")
    report("NEGATIVE photos: a different wine, so rank 1 MUST NOT be the slug",
           neg, loaded, "rejected")


if __name__ == "__main__":
    main()
