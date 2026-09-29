"""Make one run of a pipeline of the backend `svoe-vino-ru`: each photo of one test set
goes to a remote matcher, for example the official recognizer of vino-svoe.ru.

Usage:
    python3 pipeline/remote_run.py --name vino-svoe-search-by-photo --set my
        [--workers N] [--limit N] [--label TEXT] [--device-ip ADDRESS]

The pipeline is an entry of the key `pipeline` of `config.yaml` with
`backend: svoe-vino-ru` (`pipelines.py`). Its request keys (`url`, `field`, `response`,
`query`, `top_k`, `timeout_s`, `workers`, `headers`) have the meaning of the same keys of
`backends.yaml`. The photo goes to the matcher as it is: the bytes of the image store,
with no step. The owner chose this on 2026-09-25T20:39:30+0300. Read
docs/plans/31_remote-configuration.md and docs/plans/34_pipeline-section.md.

`benchmark.run_benchmark` writes the run files, so the files and the metrics are the files
and the metrics of a `benchmark.py` run. `run.json` holds `configuration: <name>`, and its
`backend` holds `kind: remote`.
"""
import argparse
import sqlite3
import sys

import benchmark  # also puts scripts/ on sys.path
import embeddings
import labdb
import match_backends
import pipelines


def find_entry(name, config_path=embeddings.CONFIG_PATH):
    """Return (the pipeline `name` of the backend svoe-vino-ru, the path of the
    database)."""
    settings = pipelines.load(config_path)
    try:
        entry = settings.find(name)
    except KeyError:
        raise embeddings.ConfigError("config.yaml has no pipeline %s" % name)
    if entry.backend != pipelines.REMOTE_BACKEND:
        raise embeddings.ConfigError("the pipeline %s has the backend %s; this script "
                                     "runs the backend %s alone"
                                     % (name, entry.backend, pipelines.REMOTE_BACKEND))
    return entry, settings.db_path


def build_backend(entry):
    """Return the HTTP backend of one remote pipeline, for `benchmark.run_benchmark`."""
    spec = {"id": entry.name, "kind": "remote",
            "label": "lab pipeline %s" % entry.name, **entry.remote}
    return match_backends.HttpMultipartBackend(spec)


def embeddings_state(entry):
    """Return the key `embeddings` of `run.json`. A remote matcher holds no vectors, so
    the run sends no request to `/v1/info` of the API."""
    return {"built_at": None,
            "reason": "the pipeline %s is a remote matcher; it holds no vectors"
                      % entry.name}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Send the photos of one test set to the remote matcher of one "
                    "pipeline (backend svoe-vino-ru), and write the run files.")
    parser.add_argument("--name", required=True, help="the name of the pipeline of config.yaml")
    parser.add_argument("--set", required=True, dest="set_name", help="the test set, for example my")
    parser.add_argument("--workers", type=int, default=None,
                        help="requests at a time; the default is `workers` of the entry")
    parser.add_argument("--limit", type=int, default=None, help="send the first N queries alone")
    parser.add_argument("--label", default=None, help="a suffix of the run id")
    parser.add_argument("--device-ip", default=None,
                        help="IPv4 address that replaces {device_ip} in a device pipeline")
    parser.add_argument("--config", default=embeddings.CONFIG_PATH, help="path of config.yaml")
    parser.add_argument("--runs-dir", default=benchmark.RUNS_DIR, help="the directory of the runs")
    args = parser.parse_args(argv)
    if args.workers is not None and args.workers < 1:
        parser.error("--workers MUST be 1 or more")

    def log(message):
        print(message, flush=True)

    try:
        entry, db_path = find_entry(args.name, args.config)
        pipelines.bind_device_ip(entry, args.device_ip)
        backend = build_backend(entry)
        run_dir, met = benchmark.run_benchmark(
            db_path, args.set_name, backend, args.runs_dir, workers=args.workers,
            limit=args.limit, label=args.label, embeddings=embeddings_state(entry),
            log=log, configuration=entry.name)
    except (benchmark.BenchmarkError, embeddings.ConfigError, match_backends.BackendError,
            labdb.SchemaError, sqlite3.Error, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    pos = met["positive"]
    print("positive: %d, recall@1 %s, recall@5 %s, mrr %s" % (
        pos["n"], pos["recall_at_1"], pos["recall_at_5"], pos["mrr"]))
    print("negative: %d, false match at 1: %d" % (
        met["negative"]["n"], met["negative"]["false_match_at_1"]))
    print("run: %s" % run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
