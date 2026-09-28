"""The key `rebuild_embeddings_on_run` of `config.yaml`: before a run of a pipeline of the
backend `embedding`, the run updates the index of the embedding of that pipeline. Read
docs/plans/59_rebuild-embeddings-on-run.md.

`run_job.py` (the button `Run>` of `/testset`) and `embedding_run.py` call `before_run`
before they read the index. With the key true, `before_run` starts
`build_embeddings.py --name <embedding>` as a separate process, as the button `Build` of
`/embedding` does, and waits for its end. The build does each item that is stale,
missing, or failed. An item whose hash did not change stays. So a build with no change
takes a few seconds, and the vectors are the vectors of a full build.

The output of the build goes to the end of `data/catalog/embeddings/<name>/build.log`, so
`/embedding` shows its progress. The run does not truncate the file: a truncation can
destroy the log of a build that started in the same second.

The run waits for a build of the same embedding that runs already. A build that ends with
an error, or that stops before its end, raises `embeddings.ConfigError`, and the run does
not start. A failed item does not stop the run. An embedding with no index gets no build:
the first build stays an action on `/embedding` (owner answers of
2026-09-27T08:53:00+0300).
"""
import json
import os
import subprocess
import sys
import time

import embeddings

KEY = "rebuild_embeddings_on_run"
BUILD_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            embeddings.BUILD_SCRIPT_NAME)
BUSY_EXIT = 3      # `build_embeddings.py`: another build of the embedding holds the lock
POLL_SECONDS = 2


def enabled(config_path):
    """Return the value of the key. A missing key or null is false. Raise ConfigError for
    a value that is not true or false."""
    _, config, _ = embeddings.read_config(config_path)
    value = config.get(KEY)
    if value is None:
        return False
    if not isinstance(value, bool):
        raise embeddings.ConfigError("%s MUST be true or false" % KEY)
    return value


def index_ready(directory):
    """Tell whether the directory of an embedding holds `index.json` and a vector file.
    This is the check of the dialog `Run>` (`embedding_run.index_ready`)."""
    try:
        names = {entry.name for entry in os.scandir(directory)}
    except (FileNotFoundError, NotADirectoryError):
        return False
    return embeddings.INDEX in names and any(embeddings.VECTORS_RE.match(n) for n in names)


def events_after(path, offset):
    """Return the JSON events of the file `path` after the byte `offset`."""
    try:
        with open(path, "rb") as fh:
            fh.seek(offset)
            data = fh.read()
    except OSError:
        return []
    events = []
    for line in data.decode("utf-8", "replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and isinstance(event.get("event"), str):
            events.append(event)
    return events


def wait_for_build(directory, name, log, sleep):
    """Wait while a build of the embedding runs."""
    pid = embeddings.running_pid(directory)
    if pid:
        log("a build of %s runs: PID %d; the run waits for its end" % (name, pid))
    while pid:
        sleep(POLL_SECONDS)
        pid = embeddings.running_pid(directory)


def run_build(command, path):
    """Start the build with its output at the end of `path`, and wait for its end. Return
    (the exit code, the events of the build). An interrupt (SIGTERM of the run, Ctrl+C)
    sends SIGTERM to the build and waits for it: the build stops after the present batch
    and keeps the finished items."""
    try:
        offset = os.path.getsize(path)
    except FileNotFoundError:
        offset = 0
    with open(path, "ab") as out:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out,
                                   stderr=subprocess.STDOUT, cwd=embeddings.ROOT,
                                   start_new_session=True)
    try:
        code = process.wait()
    except KeyboardInterrupt:
        process.terminate()
        process.wait()
        raise
    return code, events_after(path, offset)


def build(name, config_path, log, sleep=time.sleep):
    """Update the index of the embedding `name`. Return the final event `done` of the
    build, or None when the embedding has no index. Raise ConfigError when the build
    fails or stops."""
    settings = embeddings.load_settings(config_path)
    try:
        settings.find(name)
    except KeyError:
        raise embeddings.ConfigError("config.yaml has no embedding %s" % name)
    directory = embeddings.entry_dir(settings.db_path, name)
    if not index_ready(directory):
        log("the embedding %s has no index, so the run does not build it: build it on "
            "/embedding" % name)
        return None
    python = settings.python or sys.executable
    if not os.path.isfile(python):
        raise embeddings.ConfigError("embedding_python %s is not a file; create the venv "
                                     "with requirements-local.txt" % python)
    command = [python, BUILD_SCRIPT, "--config", settings.config_path, "--name", name]
    path = os.path.join(directory, embeddings.LOG)
    while True:
        wait_for_build(directory, name, log, sleep)
        log("%s: the build of %s starts" % (KEY, name))
        code, events = run_build(command, path)
        if code != BUSY_EXIT:
            break
        log("another build of %s took the lock first; the run waits for its end" % name)
    final = next((event for event in reversed(events)
                  if event["event"] in embeddings.FINAL_STATES), None)
    if code == 0 and final and final["event"] == "done":
        log("the build of %s ended: %s items were current, %s built, %s failed, %s "
            "removed, in %s s" % (name, final.get("current"), final.get("built"),
                                  final.get("failed"), final.get("pruned"),
                                  final.get("seconds")))
        return final
    if final and final["event"] == "stopped":
        raise embeddings.ConfigError("the build of %s stopped before its end; the run did "
                                     "not start" % name)
    if final is None:
        message = "exit code %s and no final line" % code
    else:
        message = final.get("message") or "exit code %s after the event %s" % (
            code, final["event"])
    raise embeddings.ConfigError("the build of %s failed: %s" % (name, message))


def before_run(pipeline, config_path, log, sleep=time.sleep):
    """Update the index of the embedding of `pipeline` before its run, when the key is
    true. Return the final event `done` of the build, or None when no build ran: the key
    is false, the pipeline has no embedding (the backend `svoe-vino-ru`), or the
    embedding has no index. `log(message)` gets one line for each state. Raise
    ConfigError."""
    name = getattr(pipeline, "embedding", None)
    if not name or not enabled(config_path):
        return None
    return build(name, config_path, log, sleep)
