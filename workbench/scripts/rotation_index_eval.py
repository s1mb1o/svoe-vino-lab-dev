#!/usr/bin/env python3
"""Run a test set against the rotated catalogue vectors of `rotation_index_build.py`.

Owner message of 2026-09-29T02:02:13+0300 and the answers of 07:06:38: compare the usual
pipelines `siglip2-p512-crop` and `siglip2-p512-as-is` (no barcode, no rerank) with the
same query side against catalogues of rotated reference vectors.

1. Baseline: the script runs each pipeline through `benchmark.run_benchmark`, as
   `pipeline/embedding_run.py` does, with the lab index. On the way it keeps the query
   vector of each photo (`<out>/queries/<pipeline>.npz`). The run files go to
   `<out>/runs/`, not to the lab `runs/`.
2. Replay: for each angle set, a catalogue holds one row for each angle of each `full`
   image of the index, for each wine of the image (the rows of `Catalogue`, with more
   rows per image). `Catalogue.rank` takes the maximum over the rows of a wine, as for the
   lab index. `run_benchmark` then scores the saved query vectors, so each set gets the
   same queries and the same metrics code. The set `0:0:1` (the 0° vector alone) repeats
   the baseline and checks the replay.

The script does not change the lab index, config.yaml, or the lab `runs/`.

    python3 scripts/rotation_index_eval.py --sets 0:0:1 0:355:5 0:180:5
    python3 scripts/rotation_index_eval.py --replay-only --sets 0:359:1 0:180:1
"""

import argparse
import collections
import csv
import json
import os
import sys
import threading
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import benchmark  # noqa: E402
import embedding_run  # noqa: E402
import embeddings  # noqa: E402
import rotation_index_build  # noqa: E402

PIPELINES = ("siglip2-p512-crop", "siglip2-p512-as-is")
OUT = os.path.join(ROOT, "docs", "reports", "rotation-index-p512-2026-09-29")


class Capture:
    """A catalogue wrapper that keeps the query vector of each photo."""

    def __init__(self, catalogue):
        self.catalogue = catalogue
        self.local = threading.local()
        self.lock = threading.Lock()
        self.vectors, self.errors = {}, {}

    def rank(self, query, top_k, trace=None, first=None):
        if set(query) != {"full"}:
            raise embeddings.ConfigError("the query has the views %s; the replay needs the "
                                         "view full alone" % sorted(query))
        with self.lock:
            self.vectors[self.local.path] = np.asarray(query["full"], dtype=np.float32)
        return self.catalogue.rank(query, top_k, trace, first)

    def __getattr__(self, name):
        return getattr(self.catalogue, name)


class CapturingBackend:
    def __init__(self, backend):
        self.backend = backend
        self.capture = Capture(backend.catalogue)
        backend.catalogue = self.capture
        self.id, self.spec, self.top_k = backend.id, backend.spec, backend.top_k

    def ask(self, path, first=None):
        self.capture.local.path = path
        answer = self.backend.ask(path, first)
        if answer[3]:
            with self.capture.lock:
                self.capture.errors[path] = answer[3]
        return answer


class RotatedCatalogue(embedding_run.Catalogue):
    """The wines and the owners of a lab catalogue, with the rows of the rotated vectors."""

    def __init__(self, base, matrix, numbers, state):  # noqa: D107 - no parent __init__
        self.slugs = base.slugs
        self.views = {"full": (matrix, numbers)}
        self.items = {"full": []}
        self.rows_of = {"full": {}}
        self.angles = {}  # plan 82 Catalogue attribute; the replay records no angle
        self.dim = base.dim
        self.state = state

    def items_of(self, number, cosines):
        # The run files keep the score of each candidate; the list of its rows (plan 38)
        # would hold up to 360 rows for each image.
        return []


def owners_of(base):
    """sha256 -> the wine numbers of the rows of the view `full` of a lab catalogue, and
    sha256 -> its first row in the matrix (the fallback when no rotated file exists)."""
    matrix, numbers = base.views["full"]
    owners, first = collections.defaultdict(list), {}
    for position, (item, number) in enumerate(zip(base.items["full"], numbers.tolist())):
        digest = item["sha256"]
        if number not in owners[digest]:
            owners[digest].append(number)
        first.setdefault(digest, position)
    return owners, first


def rotated_catalogue(base, index_dir, angles, log):
    matrix, _ = base.views["full"]
    owners, first = owners_of(base)
    rows, numbers, missing, short = [], [], 0, 0
    wanted = set(angles)
    for digest, wines in owners.items():
        have, vectors = rotation_index_build.load_saved(
            os.path.join(index_dir, "vectors", digest + ".npz"))
        chosen = [i for i, angle in enumerate(have) if angle in wanted]
        if len(chosen) < len(wanted):
            short += 1
        if not chosen:
            missing += 1
            block = matrix[first[digest]][None, :]
        else:
            block = vectors[chosen]
        for number in wines:
            rows.append(block)
            numbers.extend([number] * len(block))
    matrix = np.ascontiguousarray(np.concatenate(rows), dtype=np.float32)
    numbers = np.asarray(numbers, dtype=np.int64)
    log("  %d images, %d rows; %d images with fewer angles than the set, %d with none "
        "(these keep the index vector)" % (len(owners), len(matrix), short, missing))
    state = dict(base.state, rotation={"angles": len(angles), "first": angles[0],
                                       "last": angles[-1], "rows": int(len(matrix)),
                                       "images_short": short, "images_missing": missing})
    return RotatedCatalogue(base, matrix, numbers, state)


class ReplayBackend:
    def __init__(self, base_backend, catalogue, vectors, errors, name, note):
        self.catalogue, self.vectors, self.errors = catalogue, vectors, errors
        self.id = name
        self.top_k = base_backend.top_k
        self.spec = dict(base_backend.spec, id=name, label=note, rotation=catalogue.state[
            "rotation"])

    def ask(self, path, first=None):
        vector = self.vectors.get(path)
        if vector is None:
            return [], 0, None, self.errors.get(path, "no query vector"), None
        started = time.time()
        cands = self.catalogue.rank({"full": vector}, self.top_k, None, first)
        return cands, int(round((time.time() - started) * 1000)), 200, None, None


def set_name(spec):
    start, end, step = (int(part) for part in spec.split(":"))
    return "rot-%03d-%03d-step%d" % (start, end, step)


def save_queries(path, vectors):
    paths = sorted(vectors)
    np.savez(path, paths=np.asarray(paths), vectors=np.asarray([vectors[p] for p in paths],
                                                               dtype=np.float32))


def load_queries(path):
    with np.load(path) as saved:
        return {str(p): v for p, v in zip(saved["paths"], saved["vectors"])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--pipelines", nargs="+", default=list(PIPELINES))
    parser.add_argument("--set", default="my", dest="set_name")
    parser.add_argument("--sets", nargs="+", required=True, help="start:end:step")
    parser.add_argument("--index-dir", default=None,
                        help="the output of rotation_index_build.py for the entry")
    parser.add_argument("--out", default=OUT)
    parser.add_argument("--workers", type=int, default=4, help="photos at a time (baseline)")
    parser.add_argument("--limit", type=int, default=None, help="the first N queries alone")
    parser.add_argument("--replay-only", action="store_true",
                        help="use the saved query vectors and baseline runs; send no request")
    args = parser.parse_args(argv)

    def log(message):
        print(message, flush=True)

    runs_dir = os.path.join(args.out, "runs")
    os.makedirs(os.path.join(args.out, "queries"), exist_ok=True)
    os.makedirs(runs_dir, exist_ok=True)
    state_path = os.path.join(args.out, "state.json")
    state = json.load(open(state_path, encoding="utf-8")) if os.path.exists(state_path) else {}
    for name in args.pipelines:
        pipeline, db_path = embedding_run.find_pipeline(name, embeddings.CONFIG_PATH)
        backend = embedding_run.build_pipeline_backend(pipeline, embeddings.CONFIG_PATH)
        base = backend.catalogue
        index_dir = args.index_dir or os.path.join(rotation_index_build.OUT,
                                                   base.state["index_file"].split("/")[0])
        queries_path = os.path.join(args.out, "queries", name + ".npz")
        errors_path = os.path.join(args.out, "queries", name + ".errors.json")
        if args.replay_only:
            vectors = load_queries(queries_path)
            with open(errors_path, encoding="utf-8") as fh:
                errors = json.load(fh)
            if state[name].get("index_file") != base.state["index_file"]:
                log("warning: the lab index is now %s; the baseline used %s"
                    % (base.state["index_file"], state[name].get("index_file")))
        else:
            log("%s: baseline run on %s, %s" % (name, args.set_name, base.state["index_file"]))
            capturing = CapturingBackend(backend)
            baseline_dir, met = benchmark.run_benchmark(
                db_path, args.set_name, capturing, runs_dir, workers=args.workers,
                limit=args.limit, label="baseline", embeddings=base.state, log=log, configuration=name)
            backend.catalogue = base
            vectors, errors = capturing.capture.vectors, capturing.capture.errors
            save_queries(queries_path, vectors)
            with open(errors_path, "w", encoding="utf-8") as fh:
                json.dump(errors, fh, ensure_ascii=False, indent=1)
            state.setdefault(name, {})["baseline"] = baseline_dir
            state[name]["index_file"] = base.state["index_file"]
            log("%s: baseline recall@1 %s, %d query vectors, %d errors"
                % (name, met["positive"]["recall_at_1"], len(vectors), len(errors)))
        for spec in args.sets:
            angles = rotation_index_build.parse_angles([spec])
            label = set_name(spec)
            log("%s: replay %s (%d angles)" % (name, label, len(angles)))
            catalogue = rotated_catalogue(base, index_dir, angles, log)
            replay = ReplayBackend(backend, catalogue, vectors, errors, name + "-" + label,
                                   "%s, catalogue rotated %s" % (name, spec))
            run_dir, met = benchmark.run_benchmark(
                db_path, args.set_name, replay, runs_dir, workers=1, limit=args.limit,
                label=None,
                embeddings=catalogue.state, log=lambda message: None,
                configuration=name)
            state.setdefault(name, {})[label] = run_dir
            log("  recall@1 %s, recall@5 %s, mrr %s, false match at 1 %s"
                % (met["positive"]["recall_at_1"], met["positive"]["recall_at_5"],
                   met["positive"]["mrr"], met["negative"]["false_match_at_1"]))
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
    write_summary(args.out, state)
    return 0


def write_summary(out, state):
    rows = []
    for name, runs in state.items():
        for label, run_dir in runs.items():
            if label == "index_file":
                continue
            with open(os.path.join(run_dir, "metrics.json"), encoding="utf-8") as fh:
                met = json.load(fh)
            pos, neg = met["positive"], met["negative"]
            rows.append({"pipeline": name, "catalogue": label, "positive": pos["n"],
                         "recall_at_1": pos["recall_at_1"], "recall_at_5": pos["recall_at_5"],
                         "recall_at_10": pos["recall_at_10"], "mrr": pos["mrr"],
                         "negative": neg["n"], "false_match_at_1": neg["false_match_at_1"],
                         "errors": pos["errors"] + neg["errors"],
                         "run": os.path.basename(run_dir)})
    with open(os.path.join(out, "summary.csv"), "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %s" % os.path.join(out, "summary.csv"), flush=True)


if __name__ == "__main__":
    sys.exit(main())
