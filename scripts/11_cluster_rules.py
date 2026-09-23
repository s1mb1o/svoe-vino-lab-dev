#!/usr/bin/env python3
"""Stage 11. Describe the labels of the catalogue clusters and write their rules.

Stage 1 asks the VLM to describe the label of each card of each cluster. Stage 2
asks the VLM where the labels of one cluster differ, and it writes the cluster rule.
The rule uses the note of the reviewer from the page `/clusters`. The module
`cluster_rules.py` holds the prompts and the rules. Read
`docs/plans/05_cluster-label-rules.md`.

The script does only the work that is not current. A description is current while
its picture and its prompt stay the same. A cluster rule is current while its slugs,
its card data, its descriptions, its note and its prompt stay the same. A stopped run
therefore resumes where it stopped.

Run:
    python3 scripts/11_cluster_rules.py
    python3 scripts/11_cluster_rules.py --stage describe
    python3 scripts/11_cluster_rules.py --cluster vinodelnya-vedernikov-fantom-3070-krasnostop-zolotovskiy-krasnoe-suhoe-145
    python3 scripts/11_cluster_rules.py --stage rules --force --limit 5
"""
import argparse
import collections
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cluster_rules as cr  # noqa: E402
import common  # noqa: E402
from common import log  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Describe the cluster labels and write the rules")
    ap.add_argument("--stage", choices=("describe", "rules", "all"), default="all")
    ap.add_argument("--cluster", action="append", default=[], metavar="SLUG",
                    help="only the cluster of this card. Repeat it for several clusters")
    ap.add_argument("--force", action="store_true",
                    help="call the VLM also for a current description or rule")
    ap.add_argument("--limit", type=int, default=0, help="at most this many clusters")
    ap.add_argument("--dry-run", action="store_true", help="count the work and call nothing")
    args = ap.parse_args()

    catalog = cr.load_catalog()
    clusters = cr.load_clusters()
    if not clusters:
        sys.exit("error: no clusters in %s. Run scripts/10_clusters.py first."
                 % common.CLUSTERS_FILE)
    targets = clusters
    if args.cluster:
        want = set(args.cluster)
        targets = [c for c in clusters if want & set(c["slugs"])]
        missing = want - {s for c in targets for s in c["slugs"]}
        if missing:
            sys.exit("error: in no cluster: %s" % ", ".join(sorted(missing)))
    if args.limit:
        targets = targets[:args.limit]

    picture_of = cr.picture_resolver(catalog)
    notes = cr.assign_notes(clusters, cr.load_notes())
    slugs = [s for c in targets for s in c["slugs"]]
    log("clusters: %d   cards: %d   notes: %d   model %s, thinking %s"
        % (len(targets), len(slugs), sum(len(v) for v in notes.values()), cr.MODEL, cr.THINKING))
    log("rules file: %s" % cr.RULES_FILE)

    if args.dry_run:
        data = cr.load_rules()
        todo = [s for s in slugs if args.force
                or not cr.description_current(data["cards"].get(s), picture_of(s))]
        stale = [c for c in targets if args.force or cr.rule_status(
            data["clusters"].get(cr.cluster_key(c["slugs"])),
            cr.rule_inputs_sha(c["slugs"], catalog, data["cards"],
                               cr.note_text(notes.get(cr.cluster_key(c["slugs"]), []))))
            != "current"]
        log("dry run: %d descriptions and at least %d rules to build" % (len(todo), len(stale)))
        return

    builder = cr.Builder(catalog, picture_of)
    t0 = time.time()
    if args.stage in ("describe", "all"):
        calls = 0
        for i, c in enumerate(targets, 1):
            calls += builder.describe_cards(c["slugs"], force=args.force)
            if i % 20 == 0:
                log("stage 1: %d of %d clusters, %d calls, %.0f s"
                    % (i, len(targets), calls, time.time() - t0))
        log("stage 1 done: %d calls, %d failed, mean %.0f ms"
            % (builder.vlm.calls, builder.vlm.failed,
               builder.vlm.total_ms / max(1, builder.vlm.calls)))

    if args.stage in ("rules", "all"):
        t1, built = time.time(), 0
        for i, c in enumerate(targets, 1):
            _, called = builder.build(c["slugs"], notes.get(cr.cluster_key(c["slugs"]), []),
                                      force=args.force)
            built += int(called)
            if i % 20 == 0:
                log("stage 2: %d of %d clusters, %d calls, %.0f s"
                    % (i, len(targets), built, time.time() - t1))

    data = cr.load_rules()
    modes = collections.Counter()
    for c in targets:
        rec = data["clusters"].get(cr.cluster_key(c["slugs"]))
        modes[(rec or {}).get("mode", "no rule") if not (rec or {}).get("error") else "error"] += 1
    failed = sum(1 for s in slugs if (data["cards"].get(s) or {}).get("error"))
    log("done in %.0f s. modes: %s. cards with an error: %d"
        % (time.time() - t0, ", ".join("%s %d" % kv for kv in sorted(modes.items())), failed))


if __name__ == "__main__":
    main()
