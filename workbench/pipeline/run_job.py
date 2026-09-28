"""Run one pipeline of `config.yaml` (the key `pipeline`) on one test set, as a job of
the lab server.

Usage:
    python3 pipeline/run_job.py --name <pipeline> --set <set> [--limit N]
        [--workers N] [--no-cache] [--no-barcode] [--config PATH] [--jobs-dir DIR]
        [--runs-dir DIR]
    python3 pipeline/run_job.py --selftest --name <embedding> [--limit N] [--workers N]
        [--no-cache] [--config PATH] [--jobs-dir DIR] [--runs-dir DIR]

The button `Run>` of `/testset` starts this script through `run_jobs.start`. The output
is one JSON event on each line; the lab server writes it to
`work/run-jobs/<pipeline>/job.log`. The events: `start`, `progress` (after each
answer), `run_dir`, `log`, `stopping`, and one final event `done`, `stopped`, or
`failed`. Read docs/plans/32_testset-run-button.md and docs/plans/34_pipeline-section.md.

A pipeline of the backend `svoe-vino-ru` runs as `remote_run.py`, and the backend
`embedding` runs as `embedding_run.py` (plan 33). `benchmark.run_benchmark` writes the run
files, so the run is the same as a run of those scripts. SIGTERM stops the job as Ctrl+C stops those scripts: the files of the
answered photos are written, and the final event is `stopped`.

`--no-cache` is the checkbox `Use caches` of the dialog, off: the job reads no record of
`model_cache`, so each model call goes to its service and the latency is real time; the
fresh answers are stored. The event `start` and `run.json` hold `use_cache`. Read
docs/plans/39_use-caches-checkbox.md.

`--no-barcode` is the checkbox `Disable barcode fast path` of the dialog: a pipeline with
the key `barcode` runs with no barcode step (no decode, no lookup in `wine_code`), as its
twin with no key `barcode`. A pipeline with the key `barcode` writes `use_barcode` into the
event `start` and `run.json`; another pipeline ignores the flag and writes null into the
event `start` alone. Read docs/plans/53_disable-barcode-checkbox.md.

With the key `rebuild_embeddings_on_run` of `config.yaml` true, a pipeline of the backend
`embedding` first updates the index of its embedding: `rebuild_on_run.before_run` starts
`build_embeddings.py` and waits for its end. Its lines are events `log` before the event
`start`. A build that fails or stops fails the run. Read
docs/plans/59_rebuild-embeddings-on-run.md.

`--selftest` is the button `Selftest` of `/embedding`: `--name` names an entry of the key
`embeddings`, and no `--set` is given. Each dataset image is a query in the view `full`
of its index, with no barcode step (`selftest.py`). The job is `selftest-<embedding>`, and
the set of the run is `dataset`. Read docs/plans/67_embedding-selftest.md.
"""
import argparse
import json
import os
import signal
import sqlite3
import sys
import threading
import time
import traceback

import benchmark  # also puts scripts/ on sys.path
import embeddings
import labdb
import match_backends
import model_cache
import pipelines
import rebuild_on_run
import remote_run
import run_jobs


def _line(event, fields):
    record = {"event": event, "t": round(time.time(), 3), "time": embeddings.now()}
    record.update(fields)
    return json.dumps(record, ensure_ascii=False) + "\n"


def emit(event, **fields):
    sys.stdout.write(_line(event, fields))
    sys.stdout.flush()


class Counting:
    """A backend of `benchmark.run_benchmark` that writes a `progress` event after each
    answer. `benchmark.py` does not change."""

    def __init__(self, backend, todo):
        self.inner = backend
        self.id, self.spec, self.top_k = backend.id, backend.spec, backend.top_k
        self.todo = todo
        self.done = 0
        self.errors = 0
        self._lock = threading.Lock()

    def ask(self, path):
        answer = self.inner.ask(path)
        with self._lock:
            self.done += 1
            if answer[3]:
                self.errors += 1
            emit("progress", done=self.done, todo=self.todo, errors=self.errors)
        return answer


def build(entry, db_path, set_name, config_path):
    """Return (the backend, the key `embeddings` of run.json, the seed or None) of one
    pipeline."""
    if entry.backend == pipelines.REMOTE_BACKEND:
        return remote_run.build_backend(entry), remote_run.embeddings_state(entry), None
    if entry.backend == pipelines.EMBEDDING_BACKEND:
        import embedding_run  # noqa: E402  (the runner of plan 33, on demand)
        backend = embedding_run.build_pipeline_backend(entry, config_path)
        return backend, backend.catalogue.state, None
    if entry.backend == "selftest":  # `selftest.BACKEND`
        import selftest  # noqa: E402  (plan 67, on demand)
        backend = selftest.build_backend(entry.embedding, config_path, entry.queries[0])
        return backend, backend.catalogue.state, None
    raise embeddings.ConfigError("the pipeline %s has the backend %s, which has no runner"
                                 % (entry.name, entry.backend))


def query_total(db_path, set_name, limit):
    total = run_jobs.query_count(db_path, set_name)
    return min(total, limit) if limit else total


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run one pipeline of config.yaml on one test set, as a job of the "
                    "lab server. The output is one JSON event on each line.")
    parser.add_argument("--name", required=True,
                        help="the name of the pipeline; with --selftest, of the embedding")
    parser.add_argument("--set", default=None, dest="set_name",
                        help="the test set; required without --selftest")
    parser.add_argument("--selftest", action="store_true",
                        help="the self-test of the embedding --name: each dataset image is "
                             "a query (plan 67); no --set")
    parser.add_argument("--limit", type=int, default=None, help="the first N queries alone")
    parser.add_argument("--workers", type=int, default=None,
                        help="requests at a time; the default is the value of the entry")
    parser.add_argument("--no-cache", dest="use_cache", action="store_false",
                        help="read no answer of data/cache/: each model call goes to its "
                             "service, so the latency is real time; the fresh answers are "
                             "stored")
    parser.add_argument("--no-barcode", dest="use_barcode", action="store_false",
                        help="skip the barcode step of a pipeline with the key `barcode`: "
                             "each photo goes to the embedding; another pipeline ignores "
                             "the flag")
    parser.add_argument("--config", default=embeddings.CONFIG_PATH, help="path of config.yaml")
    parser.add_argument("--jobs-dir", default=run_jobs.JOBS_DIR, help="the directory of the jobs")
    parser.add_argument("--runs-dir", default=benchmark.RUNS_DIR, help="the directory of the runs")
    args = parser.parse_args(argv)
    for value, what in ((args.limit, "--limit"), (args.workers, "--workers")):
        if value is not None and value < 1:
            emit("failed", message="%s MUST be 1 or more" % what)
            return 2
    if args.selftest == bool(args.set_name):
        emit("failed", message="--selftest takes no --set" if args.selftest
             else "--set is required")
        return 2
    if args.selftest:
        import selftest  # noqa: E402  (plan 67, on demand)
    set_name = selftest.SET_NAME if args.selftest else args.set_name
    # The configuration of the run and the name of the job.
    name = selftest.job_name(args.name) if args.selftest else args.name

    directory = run_jobs.job_dir(args.jobs_dir, name)
    try:
        run_jobs.acquire_lock(directory)
    except embeddings.Busy as exc:
        emit("failed", message=str(exc))
        return 3
    stopped = threading.Event()

    def on_term(signum, frame):
        # The first SIGTERM stops the run; a later one waits for the files. The line goes
        # out with one system call, because the signal can come in the middle of `emit`.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        stopped.set()
        os.write(sys.stdout.fileno(), _line("stopping", {"signal": "SIGTERM"}).encode())
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, on_term)
    run_id = None
    try:
        settings = pipelines.load(args.config)
        queries = None
        if args.selftest:
            queries = selftest.read_queries(settings.db_path)
            entry = selftest.Entry(args.name, queries)
        else:
            try:
                entry = settings.find(args.name)
            except KeyError:
                raise embeddings.ConfigError("config.yaml has no pipeline %s" % args.name)
        # None: the pipeline has no barcode step, so the run records nothing about it.
        use_barcode = args.use_barcode if run_jobs.has_barcode(entry) else None
        if use_barcode is False:
            entry.barcode = None  # `build` then puts no `barcode.CodeFirst` around it
        if queries is not None:
            # The self-test has no barcode step, and `run.json` says so (plan 67).
            use_barcode = False
            todo = min(len(queries[0]), args.limit) if args.limit else len(queries[0])
        else:
            todo = query_total(settings.db_path, args.set_name, args.limit)
        # Plan 59: the key `rebuild_embeddings_on_run` updates the index of the embedding
        # before `build` reads it. The check of the set comes first.
        rebuild_on_run.before_run(entry, settings.config_path,
                                  lambda message: emit("log", message=message))
        # Before the backend exists, so that each client of `model_cache` follows it.
        model_cache.READ = args.use_cache
        backend, state, seed = build(entry, settings.db_path, set_name,
                                     settings.config_path)
        emit("start", pid=os.getpid(), configuration=name, set=set_name,
             todo=todo, limit=args.limit,
             workers=args.workers or int(backend.spec.get("workers") or 1), seed=seed,
             use_cache=args.use_cache, use_barcode=use_barcode)
        counting = Counting(backend, todo)

        def log(message):
            nonlocal run_id
            prefix = "run directory: "
            if message.startswith(prefix):
                run_id = os.path.basename(message[len(prefix):])
                emit("run_dir", run_id=run_id)
            else:
                emit("log", message=message.strip())

        run_dir, met = benchmark.run_benchmark(
            settings.db_path, set_name, counting, args.runs_dir, workers=args.workers,
            limit=args.limit, embeddings=state, log=log, configuration=name,
            use_cache=args.use_cache, use_barcode=use_barcode, queries=queries)
        run_id = os.path.basename(run_dir)
        pos = met["positive"]
        summary = {"answered": counting.done, "errors": counting.errors,
                   "recall_at_1": pos.get("recall_at_1"), "recall_at_5": pos.get("recall_at_5")}
        if stopped.is_set():
            emit("stopped", run_id=run_id, message="stopped after %d of %d photos"
                 % (counting.done, todo), **summary)
        else:
            emit("done", run_id=run_id, message="recall@1 %s, recall@5 %s"
                 % (pos.get("recall_at_1"), pos.get("recall_at_5")), **summary)
        return 0
    except KeyboardInterrupt:
        emit("stopped", run_id=run_id, message="stopped before the first answer")
        return 0
    except (benchmark.BenchmarkError, embeddings.ConfigError, match_backends.BackendError,
            labdb.SchemaError, sqlite3.Error, OSError) as exc:
        emit("failed", run_id=run_id, message=str(exc))
        return 1
    except Exception as exc:  # noqa: BLE001 - the page shows each fatal error
        traceback.print_exc()
        emit("failed", run_id=run_id, message="%s: %s" % (type(exc).__name__, exc))
        return 1
    finally:
        run_jobs.release_lock(directory)


if __name__ == "__main__":
    sys.exit(main())
