"""The run jobs of the lab server: a run of one pipeline of `config.yaml` (the key
`pipeline`, `pipelines.py`) on one test set, started with the button `Run>` of
`/testset`. Read docs/plans/32_testset-run-button.md and
docs/plans/34_pipeline-section.md.

    GET  /api/run-configurations?set=<set>   each pipeline, runnable or not, and the
                                             count of the queries of the set
    GET  /api/run-jobs                       the job of each pipeline
    POST /api/run-jobs                       start a job: {"configuration", "set",
                                             "limit", "workers", "use_cache"}
    POST /api/run-jobs/<name>/stop           stop a job (SIGTERM)

The routes and the key `configuration` keep their names; `configuration` names the
pipeline (owner answer of 2026-09-25T23:55:27+0300).

A job runs `run_job.py` as a separate process. Its output goes to
`work/run-jobs/<name>/job.log`, one JSON event on each line, and `job.lock` holds its
PID. The job state comes from these two files, so a restart of the server does not lose
a running job. One pipeline runs one job at a time.
"""
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.parse

import benchmark
import embeddings
import pipelines

JOBS_DIR = os.path.join(embeddings.ROOT, "work", "run-jobs")
RUNNER_NAME = "run_job.py"
RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), RUNNER_NAME)
LOCK = "job.lock"
LOG = "job.log"
API_CONFIGURATIONS = "/api/run-configurations"
API_JOBS = "/api/run-jobs"
STOP_ROUTE = re.compile(r"^/api/run-jobs/(%s)/stop$" % embeddings.NAME_PATTERN)
FINAL = ("done", "stopped", "failed")
ACTIVE = ("running", "stopping")
MAX_WORKERS = 32
BODY_LIMIT = 4096
JSON = "application/json; charset=utf-8"
NO_STORE = "no-store"

# job directory -> the runner process that this server started. The server reaps it.
_PROCESSES = {}
_START = threading.Lock()


def job_dir(jobs_dir, name):
    return os.path.join(jobs_dir, name)


def read_lock(directory):
    """Return the content of `job.lock`, or None."""
    try:
        with open(os.path.join(directory, LOCK), encoding="utf-8") as fh:
            lock = json.load(fh)
    except (OSError, ValueError):
        return None
    return lock if isinstance(lock, dict) else None


def runner_alive(pid):
    """Tell whether the process `pid` runs `run_job.py`. A stale lock can name a PID that
    the system gave to another process later."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    try:
        command = subprocess.run(["ps", "-o", "command=", "-p", str(pid)],
                                 capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return True
    return any(os.path.basename(token) == RUNNER_NAME for token in command.split())


def running_pid(directory):
    """Return the PID of the runner that holds the lock, or None."""
    lock = read_lock(directory)
    pid = lock.get("pid") if lock else None
    return pid if runner_alive(pid) else None


def acquire_lock(directory):
    """Take `job.lock` for this process. A lock of a dead process is removed. Raise
    embeddings.Busy when a live runner holds the lock."""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, LOCK)
    for _ in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            pid = running_pid(directory)
            if pid:
                raise embeddings.Busy("another run of this pipeline runs: PID %d" % pid)
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"pid": os.getpid(), "started_at": embeddings.now()}, fh)
        return
    raise embeddings.Busy("cannot take %s" % path)


def release_lock(directory):
    lock = read_lock(directory)
    if lock and lock.get("pid") == os.getpid():
        try:
            os.remove(os.path.join(directory, LOCK))
        except FileNotFoundError:
            pass


def read_events(directory):
    """Return the JSON events of `job.log`. A line that is not an event is skipped."""
    try:
        with open(os.path.join(directory, LOG), encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return []
    events = []
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and isinstance(event.get("event"), str):
            events.append(event)
    return events


def job_state(directory):
    """Return the job of one pipeline from `job.lock` and `job.log`.

    `state` is None (no job yet), `running`, `stopping`, `done`, `stopped`, or
    `failed`. A runner that ended with no final event is `failed`."""
    events = read_events(directory)
    starts = [number for number, event in enumerate(events) if event["event"] == "start"]
    run = events[starts[-1]:] if starts else events
    start = run[0] if run and run[0]["event"] == "start" else {}
    progress = next((e for e in reversed(run) if e["event"] == "progress"), {})
    final = next((e for e in reversed(run) if e["event"] in FINAL), {})
    named = next((e for e in reversed(run) if e["event"] == "run_dir"), {})
    pid = running_pid(directory)
    job = {"state": None, "pid": pid, "set": start.get("set"),
           "todo": progress.get("todo", start.get("todo")), "done": progress.get("done", 0),
           "errors": progress.get("errors", 0), "limit": start.get("limit"),
           "workers": start.get("workers"), "started_t": start.get("t"),
           "started_at": start.get("time"), "ended_t": final.get("t"),
           "run_id": final.get("run_id") or named.get("run_id"),
           "message": final.get("message")}
    if pid and start.get("pid") == pid:
        job["state"] = ("stopping" if any(e["event"] == "stopping" for e in run)
                        else "running")
    elif final:
        # A runner that failed before its `start` event, for example on a wrong option,
        # has a final event too.
        job["state"] = final["event"]
    elif start:
        job["state"] = "failed"
        job["message"] = "the runner ended with no final event"
    return job


def _reap():
    for directory, process in list(_PROCESSES.items()):
        if process.poll() is not None:
            del _PROCESSES[directory]


def job(jobs_dir, name):
    """Return the job of one pipeline. A process that this server started a moment
    ago is `running` before it writes its first event."""
    _reap()
    directory = job_dir(jobs_dir, name)
    state = job_state(directory)
    process = _PROCESSES.get(directory)
    if process is not None and state["state"] not in ACTIVE:
        state.update(state="running", pid=process.pid, message="starting", done=0,
                     errors=0, ended_t=None, run_id=None)
    return dict(state, name=name)


def runnable(pipeline, error, db_path):
    """Return (True, None), or (False, the reason why the pipeline cannot run). A pipeline
    of the backend `embedding` needs the built index of its `embeddings` entry."""
    if error:
        return False, "configuration error: %s" % error
    if pipeline.backend == pipelines.EMBEDDING_BACKEND:
        import embedding_run  # noqa: E402  (the runner of plan 33, on demand)
        if not embedding_run.index_ready(db_path, pipeline.embedding):
            return False, embedding_run.NO_INDEX
    return True, None


def interpreter(settings, pipeline):
    """Return the Python interpreter of the job of one pipeline. A pipeline of the backend
    `embedding` runs with `embedding_python`, as a build does (`embedding_routes.start`),
    because the backend `local` needs `torch`. Raise ConfigError when that path is not a
    file."""
    if pipeline.backend != pipelines.EMBEDDING_BACKEND:
        return sys.executable
    python = embeddings.load_settings(settings.config_path).python or sys.executable
    if not os.path.isfile(python):
        raise embeddings.ConfigError("embedding_python %s is not a file; create the venv "
                                     "with requirements-local.txt" % python)
    return python


def default_workers(pipeline):
    if pipeline is None:
        return None
    if pipeline.remote is not None:
        return pipeline.remote["workers"]
    return 1


def query_count(db_path, set_name):
    """Return the count of the queries of a set. Raise BenchmarkError for an unknown set."""
    conn = benchmark.open_database(db_path)
    try:
        rows, _ = benchmark.build_queries(conn, db_path, set_name)
    finally:
        conn.close()
    return len(rows)


def configurations_view(settings, jobs_dir, set_name):
    """Return each pipeline of `settings` (`pipelines.Pipelines`) with its job, and the
    count of the queries of the set."""
    out = []
    for name, pipeline, error in settings.entries:
        can, reason = runnable(pipeline, error, settings.db_path)
        out.append({"name": name, "backend": pipeline.backend if pipeline else None,
                    "runnable": can, "reason": reason,
                    "workers": default_workers(pipeline), "job": job(jobs_dir, name)})
    return {"set": set_name, "queries": query_count(settings.db_path, set_name),
            "configurations": out}


def jobs_view(jobs_dir):
    """Return the job of each pipeline that has a job directory, by name."""
    try:
        names = sorted(entry.name for entry in os.scandir(jobs_dir)
                       if entry.is_dir() and embeddings.NAME_RE.match(entry.name))
    except FileNotFoundError:
        names = []
    names += sorted({os.path.basename(d) for d in _PROCESSES} - set(names))
    return [job(jobs_dir, name) for name in names]


def _whole(value, low, high, what):
    """Return None for an empty value, else an integer from `low` to `high`."""
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError("%s MUST be an integer from %d to %d" % (what, low, high))
    return value


def start(settings, jobs_dir, body, runs_dir=None):
    """Start a run job. Return (HTTP code, answer). `runs_dir` is the directory of the
    runs of the Runs page; None keeps the default of `run_job.py`, `runs/`."""
    name, set_name = body.get("configuration"), body.get("set")
    if not isinstance(name, str) or not isinstance(set_name, str) or not set_name:
        return 400, {"error": "the body MUST name the configuration and the set"}
    try:
        limit = _whole(body.get("limit"), 1, 10 ** 7, "limit")
        workers = _whole(body.get("workers"), 1, MAX_WORKERS, "workers")
    except ValueError as exc:
        return 400, {"error": str(exc)}
    # The checkbox `Use caches` of the dialog; a missing key is the default, on. Off gives
    # `--no-cache` (owner answers of 2026-09-26T01:32:00+0300, plan 39).
    use_cache = body.get("use_cache")
    if use_cache is None:
        use_cache = True
    if not isinstance(use_cache, bool):
        return 400, {"error": "use_cache MUST be true or false"}
    try:
        pipeline = settings.find(name)
    except KeyError:
        return 404, {"error": "config.yaml has no pipeline %s" % name}
    except embeddings.ConfigError as exc:
        return 400, {"error": "pipeline %s: %s" % (name, exc)}
    can, reason = runnable(pipeline, None, settings.db_path)
    if not can:
        return 400, {"error": "%s (backend %s): %s" % (name, pipeline.backend, reason)}
    try:
        python = interpreter(settings, pipeline)
    except embeddings.ConfigError as exc:
        return 400, {"error": str(exc)}
    try:
        if not query_count(settings.db_path, set_name):
            return 400, {"error": "the set %s gives no query" % set_name}
    except benchmark.BenchmarkError as exc:
        return 404, {"error": str(exc)}
    directory = job_dir(jobs_dir, name)
    command = [python, RUNNER, "--config", settings.config_path, "--name", name,
               "--set", set_name, "--jobs-dir", jobs_dir]
    if limit:
        command += ["--limit", str(limit)]
    if workers:
        command += ["--workers", str(workers)]
    if not use_cache:
        command.append("--no-cache")
    if runs_dir:
        command += ["--runs-dir", runs_dir]
    with _START:
        state = job(jobs_dir, name)
        if state["state"] in ACTIVE:
            return 409, {"error": "a run of %s runs: PID %s" % (name, state["pid"])}
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, LOG), "wb") as log:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                       stderr=subprocess.STDOUT, cwd=embeddings.ROOT,
                                       start_new_session=True)
        _PROCESSES[directory] = process
    return 202, {"name": name, "set": set_name, "state": "running", "pid": process.pid}


def stop(jobs_dir, name):
    """Send SIGTERM to the runner of one pipeline. Return (HTTP code, answer)."""
    directory = job_dir(jobs_dir, name)
    pid = running_pid(directory)
    if pid is None:
        process = _PROCESSES.get(directory)
        if process is None or process.poll() is not None:
            return 409, {"error": "no run of %s runs" % name}
        pid = process.pid
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return 409, {"error": "no run of %s runs" % name}
    return 202, {"name": name, "state": "stopping", "pid": pid}


def handles(route):
    """Tell whether a route belongs to the run jobs."""
    return route in (API_CONFIGURATIONS, API_JOBS) or bool(STOP_ROUTE.match(route))


def respond(server, method, path, read_body):
    """Return (HTTP code, body, content type, cache) of one request."""
    parts = urllib.parse.urlsplit(path)
    route, query = parts.path, urllib.parse.parse_qs(parts.query)
    config_path = getattr(server, "config_path", None) or embeddings.CONFIG_PATH
    jobs_dir = getattr(server, "run_jobs_dir", None) or JOBS_DIR
    try:
        settings = pipelines.load(config_path)
    except embeddings.ConfigError as exc:
        return 503, {"error": str(exc)}, JSON, NO_STORE

    def answer(code, value):
        return code, value, JSON, NO_STORE

    if route == API_CONFIGURATIONS:
        if method not in ("GET", "HEAD"):
            return answer(405, {"error": "use GET"})
        set_name = (query.get("set") or [""])[0]
        if not set_name:
            return answer(400, {"error": "name the set: ?set=<set>"})
        try:
            return answer(200, configurations_view(settings, jobs_dir, set_name))
        except benchmark.BenchmarkError as exc:
            return answer(404, {"error": str(exc)})
    if route == API_JOBS:
        if method in ("GET", "HEAD"):
            return answer(200, {"jobs": jobs_view(jobs_dir), "now": time.time()})
        if method != "POST":
            return answer(405, {"error": "use GET or POST"})
        raw = read_body(BODY_LIMIT)
        try:
            body = json.loads(raw) if raw else None
        except (UnicodeDecodeError, ValueError):
            body = None
        if not isinstance(body, dict):
            return answer(400, {"error": "the body MUST be one JSON object"})
        return answer(*start(settings, jobs_dir, body, getattr(server, "runs_dir", None)))
    if method != "POST":
        return answer(405, {"error": "use POST"})
    return answer(*stop(jobs_dir, STOP_ROUTE.match(route).group(1)))
