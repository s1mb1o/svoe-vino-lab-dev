#!/usr/bin/env python3
"""Build the cluster artifact of one lab embedding.

Run:
    python3 pipeline/build_clusters.py --name <embedding-name>
    python3 pipeline/build_clusters.py --name <embedding-name> \
        --full-threshold 0.95 --label-threshold 0.95

The thresholds and the limits come from the block `clusters` of `config.yaml`. An option
`--full-threshold` or `--label-threshold` replaces the value of that block for one build.
"""
import argparse
import json
import sys

import clusters
import embeddings


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build clusters of one lab embedding")
    parser.add_argument("--config", default=embeddings.CONFIG_PATH)
    parser.add_argument("--name", required=True)
    parser.add_argument("--full-threshold", type=float, default=None)
    parser.add_argument("--label-threshold", type=float, default=None)
    args = parser.parse_args(argv)
    try:
        settings = embeddings.load_settings(args.config)
        artifact = clusters.build_to_directory(
            settings, args.name, args.full_threshold, args.label_threshold)
    except (embeddings.ConfigError, clusters.ClusterError, OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    counts = {space: artifact["spaces"][space]["counts"] for space in clusters.SPACES}
    print(json.dumps({
        "embedding": artifact["embedding"], "built_at": artifact["built_at"],
        "file": clusters.CLUSTERS_FILE, "settings": artifact["settings"],
        "spaces": counts,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
