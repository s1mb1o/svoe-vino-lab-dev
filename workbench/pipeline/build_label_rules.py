#!/usr/bin/env python3
"""Build the label rules of the clusters of one lab embedding. Read
docs/plans/45_cluster-label-rules.md and the module `label_rules`.

Run:
    python3 pipeline/build_label_rules.py --name <embedding-name>
    python3 pipeline/build_label_rules.py --name <embedding-name> --stage describe
    python3 pipeline/build_label_rules.py --name <embedding-name> --cluster <slug>
    python3 pipeline/build_label_rules.py --name <embedding-name> --dry-run
    python3 pipeline/build_label_rules.py --name <embedding-name> --force
    python3 pipeline/build_label_rules.py --name <embedding-name> --cluster <slug> --wait

`--wait` waits for a running rule build of the same embedding. The note route of the
Clusters page starts the command with it after a note change (plan 45).

The settings come from the block `label_rules` of `config.yaml`. The command does only
the work that is not current, so a stopped run resumes. It writes
`data/catalog/embeddings/<name>/cluster-rules.json` and prints a JSON summary.

Exit status: 0 when every call gave a valid record, 1 when a record holds an error, 2
when the run cannot start or stops (for example, the service refuses the number of
images of one prompt).
"""
import argparse
import json
import sys

import clusters
import embeddings
import label_rules


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the label rules of one lab embedding")
    parser.add_argument("--config", default=embeddings.CONFIG_PATH)
    parser.add_argument("--name", required=True)
    parser.add_argument("--stage", choices=("describe", "rules", "all"), default="all")
    parser.add_argument("--cluster", metavar="SLUG", default=None,
                        help="build only the cluster of the view combined that holds SLUG")
    parser.add_argument("--force", action="store_true",
                        help="build again also a current description or rule")
    parser.add_argument("--dry-run", action="store_true",
                        help="list the work; make no call and no write")
    parser.add_argument("--wait", action="store_true",
                        help="wait for a running rule build of the embedding, then run "
                             "(the rebuild after a note change uses it)")
    args = parser.parse_args(argv)
    try:
        settings = embeddings.load_settings(args.config)
        summary = label_rules.run(settings, args.name, stage=args.stage,
                                  cluster_slug=args.cluster, force=args.force,
                                  dry_run=args.dry_run, wait_lock=args.wait)
    except (embeddings.ConfigError, label_rules.RuleError, clusters.ClusterError,
            OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False))
    if summary.get("stopped"):
        print("error: %s" % summary["stopped"], file=sys.stderr)
        return 2
    errors = summary["describe"]["errors"] + summary["rules"]["errors"]
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
