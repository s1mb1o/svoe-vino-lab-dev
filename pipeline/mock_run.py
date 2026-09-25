"""Make one run of the lab configuration `mock`: random top-k candidates for each photo.

Usage:
    python3 pipeline/mock_run.py --set my [--top-k 10] [--seed N] [--limit N]

The owner uses the run to test the UI pipeline of the Runs page. The configuration
`mock` is the entry `name: mock`, `backend: mock` of the key `embeddings` of
`config.yaml`. It sends no request and builds no vectors. Read
`docs/plans/23_runs-page.md`.

The mock backend answers each photo of the test set with `top_k` distinct slugs of the
Active wines of `wine_catalog`, with random scores from high to low:
- Each place slug of the photo (the slug of a positive or a negative row of these
  bytes) gets a random rank from 1 to `top_k`, or no rank. So the page shows every
  state: correct at rank 1, a deeper rank, absent, a false match, and a negative above a
  positive.
- The other places hold random slugs. A place slug that got no rank does not appear.
- The latency is a random value from 50 to 4,000 ms. The script does not wait.
- The answer of one photo depends on the seed and on the SHA-256 of the photo alone.
  So a run with the same seed gives the same answers.

`benchmark.run_benchmark` writes the run files, so the files and the metrics are the
files and the metrics of a real run. `run.json` holds `configuration: "mock"`.
"""
import argparse
import collections
import random
import sqlite3
import sys

import benchmark
import embeddings
import labdb

NAME = "mock"
DEFAULT_TOP_K = 10
LATENCY_MS = (50, 4000)


class MockBackend:
    """A backend of `benchmark.run_benchmark` that answers at random. `places` maps the
    path of each photo to (its SHA-256, the place slugs of its rows)."""

    id = NAME

    def __init__(self, slugs, places, top_k, seed):
        if top_k < 1:
            raise ValueError("top_k MUST be 1 or more")
        self.slugs = sorted(slugs)
        self.places = places
        self.top_k = top_k
        self.seed = seed
        self.spec = {"id": NAME, "label": "Mock configuration: random top-%d" % top_k,
                     "top_k": top_k, "seed": seed, "url": None, "workers": 1}

    def ask(self, path):
        """Return `(candidates, latency_ms, http_status, error)`, as a real backend."""
        digest, place_slugs = self.places[path]
        rng = random.Random("%s:%s" % (self.seed, digest))
        chosen = [None] * self.top_k
        for slug in place_slugs:
            rank = rng.randrange(self.top_k + 1)  # the value top_k means no rank
            if rank < self.top_k and chosen[rank] is None:
                chosen[rank] = slug
        taken = set(place_slugs)
        free = [slug for slug in self.slugs if slug not in taken]
        fill = iter(rng.sample(free, min(len(free), chosen.count(None))))
        chosen = [slug if slug is not None else next(fill, None) for slug in chosen]
        scores = sorted((rng.random() for _ in chosen), reverse=True)
        cands = [{"slug": slug, "score": round(score, 4), "rank": rank}
                 for rank, (slug, score) in enumerate(
                     ((s, sc) for s, sc in zip(chosen, scores) if s is not None), 1)]
        return cands, rng.randint(*LATENCY_MS), 200, None


def check_configuration(config_path=embeddings.CONFIG_PATH):
    """Raise ConfigError unless `config.yaml` holds the entry `mock` of the backend mock."""
    settings = embeddings.load_settings(config_path)
    try:
        entry = settings.find(NAME)
    except KeyError:
        raise embeddings.ConfigError("config.yaml has no configuration %s; add the entry "
                                     "`name: mock`, `backend: mock` to `embeddings`" % NAME)
    if entry.backend != "mock":
        raise embeddings.ConfigError("the configuration %s MUST have `backend: mock`" % NAME)


def build_backend(db_path, set_name, top_k, seed, schema_dir=labdb.SCHEMA_DIR):
    """Return the mock backend of one test set of the database."""
    conn = benchmark.open_database(db_path, schema_dir)
    try:
        rows, _ = benchmark.build_queries(conn, db_path, set_name)
        slugs = [slug for (slug,) in conn.execute(
            "SELECT wine_slug FROM wine_catalog WHERE state = 'Active'")]
    finally:
        conn.close()
    found = collections.defaultdict(set)
    digests = {}
    for row in rows:
        digests[row["abs_path"]] = row["image_sha256"]
        if row["label"] in ("positive", "negative"):
            found[row["abs_path"]].add(row["slug"])
    places = {path: (digest, sorted(found[path])) for path, digest in digests.items()}
    return MockBackend(slugs, places, top_k, seed)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Make one run of the lab configuration mock: random top-k candidates "
                    "for each photo of one test set.")
    parser.add_argument("--set", required=True, dest="set_name", help="the test set, for example my")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="the candidates of each photo")
    parser.add_argument("--seed", type=int, default=None,
                        help="the seed of the answers; the default is a random seed")
    parser.add_argument("--limit", type=int, default=None, help="the first N queries alone")
    parser.add_argument("--config", default=embeddings.CONFIG_PATH, help="path of config.yaml")
    parser.add_argument("--runs-dir", default=benchmark.RUNS_DIR, help="the directory of the runs")
    args = parser.parse_args(argv)
    if args.top_k < 1:
        parser.error("--top-k MUST be 1 or more")
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(10 ** 9)

    def log(message):
        print(message, flush=True)

    try:
        check_configuration(args.config)
        db_path = embeddings.load_settings(args.config).db_path
        backend = build_backend(db_path, args.set_name, args.top_k, seed)
        run_dir, met = benchmark.run_benchmark(
            db_path, args.set_name, backend, args.runs_dir, workers=1, limit=args.limit,
            embeddings={"built_at": None,
                        "reason": "the configuration mock builds no vectors"},
            log=log, configuration=NAME)
    except (benchmark.BenchmarkError, embeddings.ConfigError, labdb.SchemaError,
            sqlite3.Error, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    pos = met["positive"]
    print("seed: %d" % seed)
    print("positive: %d, recall@1 %s, recall@5 %s" % (pos["n"], pos["recall_at_1"],
                                                      pos["recall_at_5"]))
    print("run: %s" % run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
