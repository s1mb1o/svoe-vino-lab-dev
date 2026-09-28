"""The self-test of one embedding (plan 67): each image of the dataset is one query, and
the query must find its own wine in the view `full` of the index.

Usage:
    python3 pipeline/selftest.py --embedding <name>
        [--workers N] [--limit N] [--label TEXT] [--top-k N]

`<name>` is an entry of the key `embeddings` of `config.yaml` with the backend `openai`
or `local`, and that entry MUST have its index: build it on `/embedding` first. An entry
of the backend `local` needs `torch`, so run it with `embedding_python`. The button
`Selftest` of `/embedding` starts the same work as a job: `run_job.py --selftest --name
<name>`. Read docs/plans/67_embedding-selftest.md.

The rules (owner messages of 2026-09-27T23:58:00+0300 and 2026-09-28T00:00:00+0300,
answers of 00:04:00):
- Each `wine_image` row of an Active wine is one query: `main`, `main_patched`,
  `full_front`, `full_back`, `label_front`, and `label_back`. The `main` of a wine with a
  `main_patched` stays a query. A file of two wines gives one query for each wine.
- The truth of a query is the `wine_slug` of its row. The test set of the run is
  `dataset`, and its configuration is `selftest-<name>`.
- A full image goes the path of a test photo (`embedding_run.EmbeddingBackend`): the SAM3
  package cut, then the steps of the view `full`. A label close-up goes in as it is, with
  no step and no SAM3 request, as a close-up of the catalogue goes in.
- Each query searches the `full` vectors of the index alone. The run has no barcode step.
  With the key `rebuild_embeddings_on_run` of `config.yaml` true, the self-test first
  updates the index (`rebuild_on_run.py`, plan 59).
"""
import argparse
import collections
import os
import sqlite3
import sys

import benchmark  # also puts scripts/ on sys.path
import build_embeddings
import embedding_run
import embeddings
import imagestore
import labdb
import match_backends
import rebuild_on_run

# The `backend` of `Entry`, for `run_job.build`.
BACKEND = "selftest"
SET_NAME = "dataset"
PREFIX = "selftest-"
VIEW = "full"
DEFAULT_WORKERS = 4


def job_name(embedding):
    """Return the configuration of the self-test of `embedding`: the name of its job and
    the key `configuration` of its `run.json`."""
    return PREFIX + embedding


def build_queries(conn, db_path):
    """Return (rows, left out counts) of the dataset, in the form of
    `benchmark.build_queries`. A row also holds `image_type`."""
    rows, skipped = [], collections.Counter()
    for slug, state, image_type, digest, folder, extension in conn.execute(
            "SELECT w.wine_slug, w.state, wi.image_type, wi.sha256, i.folder, i.extension "
            "FROM wine_image wi JOIN wine_catalog w ON w.wine_slug = wi.wine_slug "
            "JOIN image i ON i.sha256 = wi.sha256"):
        if image_type not in embeddings.ROLES:
            skipped["image type %s" % image_type] += 1
        elif state != "Active":
            skipped["%s wine" % state.lower()] += 1
        else:
            rows.append({
                "image_path": "%s/%s-%s.%s" % (slug, image_type, digest[:12], extension),
                "abs_path": os.path.join(imagestore.folder_of(db_path, folder),
                                         "%s.%s" % (digest, extension)),
                "image_sha256": digest, "slug": slug, "image_type": image_type,
                "label": "positive", "truth": [slug]})
    rows.sort(key=lambda r: r["image_path"])
    for i, row in enumerate(rows, 1):
        row["query_id"] = "q-%06d" % i
    return rows, skipped


def read_queries(db_path):
    """Return `build_queries` of the database at `db_path`. Raise BenchmarkError."""
    conn = benchmark.open_database(db_path)
    try:
        return build_queries(conn, db_path)
    finally:
        conn.close()


class Entry:
    """The self-test of one embedding as an entry of `run_job.py`: `name` is the
    configuration, `embedding` the entry of `embeddings`, and `queries` the answer of
    `build_queries`. It has no barcode step."""

    backend = BACKEND
    barcode = None

    def __init__(self, embedding, queries):
        self.name = job_name(embedding)
        self.embedding = embedding
        self.queries = queries


class SelfTestBackend:
    """A backend of `benchmark.run_benchmark`: `id`, `spec`, `top_k`, and `ask(path)`.
    `full` answers a full image and `closeup` a label close-up. Both are
    `embedding_run.EmbeddingBackend` objects of one catalogue, one model, and one SAM3
    client. `roles` maps the path of a query to the role of its file."""

    def __init__(self, full, closeup, roles):
        self.full, self.closeup, self.roles = full, closeup, roles
        self.id, self.top_k, self.catalogue = full.id, full.top_k, full.catalogue
        self.spec = dict(full.spec, selftest={
            "set": SET_NAME, "view": VIEW,
            "steps": {"full": full.views[VIEW], "label": closeup.views[VIEW]}})
        self.spec["label"] = ("self-test of the embedding %s: each dataset image in the "
                              "view %s" % (full.embedding.name, VIEW))
        self.spec["workers"] = DEFAULT_WORKERS

    def ask(self, path):
        backend = self.closeup if self.roles.get(path) == "label" else self.full
        return backend.ask(path)


def build_backend(name, config_path=embeddings.CONFIG_PATH, rows=(),
                  top_k=embedding_run.DEFAULT_TOP_K,
                  make_model=build_embeddings.make_backend, segmenter=None):
    """Return the `SelfTestBackend` of the entry `name` of `embeddings` for the query rows
    `rows`. Raise `embeddings.ConfigError`: an unknown or invalid entry, an entry with no
    view `full`, or an entry with no index."""
    settings = embeddings.load_settings(config_path)
    try:
        entry = settings.find(name)
    except KeyError:
        raise embeddings.ConfigError("config.yaml has no embedding %s" % name)
    if VIEW not in entry.views:
        raise embeddings.ConfigError("the embedding %s has no view %s" % (name, VIEW))
    full = embedding_run.build_backend(entry, settings.db_path, top_k, make_model,
                                       segmenter, job_name(name), {VIEW: entry.views[VIEW]})
    closeup = embedding_run.EmbeddingBackend(entry, full.catalogue, full.model,
                                             full.segmenter, top_k, job_name(name),
                                             {VIEW: []})
    # The backend `local` takes one request at a time for the two objects together.
    closeup._lock = full._lock
    # A file that is a full image of one wine and a close-up of another wine is a full
    # image, as in `embeddings.read_inputs`.
    roles = {}
    for row in rows:
        if roles.get(row["abs_path"]) != "full":
            roles[row["abs_path"]] = embeddings.ROLES[row["image_type"]]
    return SelfTestBackend(full, closeup, roles)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Query each dataset image in the view full of the index of one "
                    "embedding of config.yaml, and write the run files (plan 67).")
    parser.add_argument("--embedding", required=True,
                        help="the name of an entry of the key embeddings")
    parser.add_argument("--workers", type=int, default=None,
                        help="photos at a time; the default is %d" % DEFAULT_WORKERS)
    parser.add_argument("--limit", type=int, default=None, help="send the first N queries alone")
    parser.add_argument("--label", default=None, help="a suffix of the run id")
    parser.add_argument("--top-k", type=int, default=embedding_run.DEFAULT_TOP_K,
                        help="the candidates of each photo")
    parser.add_argument("--config", default=embeddings.CONFIG_PATH, help="path of config.yaml")
    parser.add_argument("--runs-dir", default=benchmark.RUNS_DIR, help="the directory of the runs")
    args = parser.parse_args(argv)
    for value, what in ((args.workers, "--workers"), (args.limit, "--limit"),
                        (args.top_k, "--top-k")):
        if value is not None and value < 1:
            parser.error("%s MUST be 1 or more" % what)

    def log(message):
        print(message, flush=True)

    try:
        settings = embeddings.load_settings(args.config)
        entry = Entry(args.embedding, read_queries(settings.db_path))
        rebuild_on_run.before_run(entry, settings.config_path, log)  # plan 59
        backend = build_backend(args.embedding, settings.config_path, entry.queries[0],
                                args.top_k)
        items = backend.catalogue.state["items"]
        log("index %s: %d current items; %d stale, %d missing, %d failed items stay out"
            % (backend.catalogue.state["index_file"], items["current"], items["stale"],
               items["missing"], items["failed"]))
        run_dir, met = benchmark.run_benchmark(
            settings.db_path, SET_NAME, backend, args.runs_dir, workers=args.workers,
            limit=args.limit, label=args.label, embeddings=backend.catalogue.state,
            log=log, configuration=entry.name, use_barcode=False, queries=entry.queries)
    except ImportError as exc:
        print("error: %s; the backend local needs the packages of requirements-local.txt: "
              "run the script with embedding_python" % exc, file=sys.stderr)
        return 1
    except (benchmark.BenchmarkError, embeddings.ConfigError, build_embeddings.BackendError,
            match_backends.BackendError, labdb.SchemaError, sqlite3.Error, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    pos = met["positive"]
    print("images: %d, recall@1 %s, recall@5 %s, mrr %s" % (
        pos["n"], pos["recall_at_1"], pos["recall_at_5"], pos["mrr"]))
    print("run: %s" % run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
