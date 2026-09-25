"""Send the photos of one test set of the lab database to one match backend.

Usage:
    python3 pipeline/benchmark.py --db data/lab.sqlite3 --set my --backend svm-siglip2-448

The runner writes the run files of `scripts/match_run.py` to `runs/<run id>/`:
`run.json`, `queries.tsv`, `queries.jsonl`, `predictions.jsonl`, `results.jsonl`,
`metrics.json`, and `summary.md`. The judgement and the metrics come from
`scripts/match_scoring.py`, the same code as `match_run.py`. Read
`docs/plans/12_testsets-benchmark.md`.

The query set follows `build_queries` of `match_run.py` with its defaults
(`--variants off`, `--only all`):
- A photo with the label `positive` or `negative` enters. Its place is its slug.
- A photo stays out when its place is excluded, when its label is `unusable`, `variant`,
  or NULL, or when it is marked for deletion.
- A photo of `__null__` enters with the label `no_match` and no truth, unless it is
  `unusable`, marked for deletion, or `__null__` is excluded.
- The rows are in the order of `<place>/<file name>`, and the query ids follow it.
"""
import argparse
import collections
import concurrent.futures
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.join(ROOT, "scripts"))
import imagestore  # noqa: E402
import labdb  # noqa: E402
import match_backends  # noqa: E402
from match_scoring import (  # noqa: E402
    LABELS_IN_SET, NO_MATCH, NULL_SLUG, judge, metrics_of, write_summary)

BACKENDS_FILE = os.path.join(ROOT, "backends.yaml")
RUNS_DIR = os.path.join(ROOT, "runs")
TOOL = "pipeline/benchmark.py"


class BenchmarkError(Exception):
    """The set or the backend does not allow the run."""


def build_queries(conn, db_path, set_name):
    """Return (rows, left out counts) of the set, as `build_queries` of match_run.py."""
    if conn.execute("SELECT 1 FROM test_set WHERE set_name = ?", (set_name,)).fetchone() is None:
        raise BenchmarkError("the database holds no test set %r" % set_name)
    excluded = {slug for (slug,) in conn.execute(
        "SELECT wine_slug FROM test_excluded WHERE set_name = ?", (set_name,))}
    rows, skipped = [], collections.Counter()
    for place, name, digest, label, delete, folder, extension in conn.execute(
            "SELECT p.place, p.file_name, p.sha256, p.label, p.marked_delete, i.folder, "
            "i.extension FROM test_photo p JOIN image i ON i.sha256 = p.sha256 "
            "WHERE p.set_name = ? ORDER BY p.place, p.file_name", (set_name,)):
        # A photo whose bytes `image` held before the import keeps the folder of that file.
        row = {"image_path": "%s/%s" % (place, name),
               "abs_path": os.path.join(imagestore.folder_of(db_path, folder),
                                        "%s.%s" % (digest, extension)),
               "image_sha256": digest, "slug": place}
        if place == NULL_SLUG:
            if NULL_SLUG in excluded:
                skipped["excluded slug"] += 1
            elif label == "unusable":
                skipped["unusable"] += 1
            elif delete:
                skipped["marked for deletion"] += 1
            else:
                rows.append({**row, "label": NO_MATCH, "truth": []})
            continue
        if place in excluded:
            skipped["excluded slug"] += 1
        elif label not in LABELS_IN_SET:
            skipped["no label" if not label else label] += 1
        elif delete:
            skipped["marked for deletion"] += 1
        elif label == "variant":
            skipped["variant"] += 1
        else:
            rows.append({**row, "label": label,
                         "truth": [place] if label == "positive" else []})
    rows.sort(key=lambda r: r["image_path"])
    for i, row in enumerate(rows, 1):
        row["query_id"] = "q-%06d" % i
    return rows, skipped


def load_groups(conn, set_name):
    """Return slug -> the set of the slugs of its variant group, in the set."""
    members = collections.defaultdict(set)
    rows = conn.execute("SELECT wine_slug, group_no FROM test_variant WHERE set_name = ?",
                        (set_name,)).fetchall()
    for slug, number in rows:
        members[number].add(slug)
    return {slug: members[number] for slug, number in rows}


def open_database(db_path, schema_dir=labdb.SCHEMA_DIR):
    """Open the database read-only. Its schema version MUST equal the schema files."""
    if not os.path.isfile(db_path):
        raise BenchmarkError("no database at %s" % db_path)
    conn = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    expected = len(labdb.schema_files(schema_dir))
    if version != expected:
        conn.close()
        raise BenchmarkError("the database has schema version %d and this code needs "
                             "version %d; run `python3 pipeline/labdb.py %s`"
                             % (version, expected, db_path))
    return conn


def git_commit():
    try:
        out = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def run_benchmark(db_path, set_name, backend, runs_dir=RUNS_DIR, workers=None, limit=None,
                  label=None, embeddings=None, log=print, schema_dir=labdb.SCHEMA_DIR,
                  configuration=None):
    """Run the set against `backend`. Return (run directory, metrics).

    `backend` is a backend of `match_backends.build_backend`: it has `id`, `spec`,
    `top_k`, and `ask(path)`. `embeddings` is the index state of the backend; None asks
    the backend with `match_backends.embeddings_of`. The runner reads the database alone.
    `configuration` is the name of the lab configuration of the run (an entry of
    `embeddings` in `config.yaml`); `run.json` holds it under the key `configuration`.
    None writes no such key. Read `docs/plans/23_runs-page.md`.
    """
    conn = open_database(db_path, schema_dir)
    try:
        rows, skipped = build_queries(conn, db_path, set_name)
        groups = load_groups(conn, set_name)
    finally:
        conn.close()
    if limit:
        rows = rows[:limit]
    if not rows:
        raise BenchmarkError("the set %r gives no query" % set_name)
    workers = workers or int(backend.spec.get("workers") or 1)

    stamp = time.strftime("%Y-%m-%dT%H%M%SZ", time.gmtime())
    name = "-".join(x for x in (stamp, "lab", backend.id, set_name, label) if x)
    run_dir = os.path.join(runs_dir, name)
    os.makedirs(run_dir, exist_ok=True)
    log("run directory: %s" % run_dir)

    with open(os.path.join(run_dir, "queries.tsv"), "w", encoding="utf-8") as fh:
        fh.write("query_id\timage_path\n")
        for row in rows:
            fh.write("%s\t%s\n" % (row["query_id"], row["image_path"]))
    with open(os.path.join(run_dir, "queries.jsonl"), "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps({k: row[k] for k in (
                "query_id", "image_path", "image_sha256", "slug", "label", "truth")},
                ensure_ascii=False) + "\n")
    counts = collections.Counter(row["label"] for row in rows)
    meta = {
        "run_id": name,
        "tool": TOOL,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git_commit": git_commit(),
        "options": {
            "database": os.path.abspath(db_path), "set": set_name,
            "backend": backend.id, "limit": limit, "only": "all", "variants": "off",
            "negative_strict": False, "workers": workers, "dry_run": False,
            "photos_dir": None,
        },
        "backend": match_backends.redact(backend.spec),
        "embeddings": embeddings if embeddings is not None else match_backends.embeddings_of(backend),
        "config": {"database_file": os.path.abspath(db_path), "backends_file": BACKENDS_FILE},
        "query_set": {"total": len(rows), **{k: counts[k] for k in sorted(counts)}},
        "left_out": dict(skipped),
        "based_on": None,
    }
    if configuration is not None:
        meta["configuration"] = configuration

    results, lock, done = [], threading.Lock(), 0
    t_start = time.time()
    pred_fh = open(os.path.join(run_dir, "predictions.jsonl"), "w", encoding="utf-8")
    res_fh = open(os.path.join(run_dir, "results.jsonl"), "w", encoding="utf-8")

    def one(row):
        cands, ms, status, error = backend.ask(row["abs_path"])
        verdict = judge(row, cands, False)
        return {
            "query_id": row["query_id"], "image_path": row["image_path"],
            "image_sha256": row["image_sha256"], "slug": row["slug"],
            "label": row["label"], "truth": row["truth"],
            "candidates": cands, "predicted_slug": verdict["predicted_slug"],
            "rank_of_truth": verdict["rank_of_truth"], "outcome": verdict["outcome"],
            "latency_ms": ms, "http_status": status, "error": error,
        }

    def write(rec):
        pred_fh.write(json.dumps({
            "query_id": rec["query_id"], "image_path": rec["image_path"],
            "image_sha256": rec["image_sha256"],
            "predicted_slug": rec["predicted_slug"], "latency_ms": rec["latency_ms"],
        }, ensure_ascii=False) + "\n")
        res_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        pred_fh.flush()
        res_fh.flush()

    def keep(rec):
        nonlocal done
        results.append(rec)
        write(rec)
        done += 1
        if done % 25 == 0 or done == len(rows):
            log("  %d/%d  elapsed %.0f s" % (done, len(rows), time.time() - t_start))

    try:
        if workers > 1:
            with concurrent.futures.ThreadPoolExecutor(workers) as pool:
                for rec in pool.map(one, rows):
                    with lock:
                        keep(rec)
        else:
            for row in rows:
                keep(one(row))
    except KeyboardInterrupt:
        log("stopped by the user after %d photos" % done)
    finally:
        pred_fh.close()
        res_fh.close()

    wall = time.time() - t_start
    met = metrics_of(results, backend, backend.top_k, False, wall, workers, groups=groups)
    met["run_id"] = name
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    meta["wall_s"] = round(wall, 1)
    meta["answered"] = len(results)
    with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
    with open(os.path.join(run_dir, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(met, fh, ensure_ascii=False, indent=2, sort_keys=True)
    write_summary(os.path.join(run_dir, "summary.md"), meta, met)
    return run_dir, met


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Send the photos of one test set of the lab database to one match "
                    "backend, and write the run files of scripts/match_run.py.")
    parser.add_argument("--db", required=True, help="path of the lab database")
    parser.add_argument("--set", required=True, dest="set_name", help="the test set, for example my")
    parser.add_argument("--backend", required=True, help="an id of backends.yaml")
    parser.add_argument("--backends", default=BACKENDS_FILE, help="path of backends.yaml")
    parser.add_argument("--runs-dir", default=RUNS_DIR, help="the directory of the runs")
    parser.add_argument("--workers", type=int, default=None,
                        help="requests at a time; the default is `workers` of the backend")
    parser.add_argument("--limit", type=int, default=None, help="send the first N queries alone")
    parser.add_argument("--label", default=None, help="a suffix of the run id")
    args = parser.parse_args(argv)

    def log(message):
        print(message, flush=True)

    try:
        backend = match_backends.build_backend(args.backends, args.backend)
        run_dir, met = run_benchmark(args.db, args.set_name, backend, args.runs_dir,
                                     args.workers, args.limit, args.label, log=log)
    except (BenchmarkError, match_backends.BackendError, labdb.SchemaError,
            sqlite3.Error, OSError) as exc:
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
