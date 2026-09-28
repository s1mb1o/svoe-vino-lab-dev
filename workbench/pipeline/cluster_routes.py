"""Routes of the embedding-dependent Clusters page.

    GET  /clusters
    GET  /api/clusters
    GET  /api/clusters/<name>
    POST /api/clusters/build-all
    POST /api/clusters/<name>/build
    POST /api/clusters/<name>/note

Read `docs/plans/30_embedding-clusters.md`. A note write also starts the rebuild of the
label rule of the cluster (plan 45).

`Build all clusters` (plan 65) is a queue of the server: a thread builds the clusters of
each entry, one at a time, in the order of `config.yaml`. `GET /api/clusters` holds the
queue. A restart of the server ends the queue.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse

import clusters
import embeddings
import lab_pages

PAGE = "/clusters"
API = "/api/clusters"
# Only a POST goes to the queue, so a GET of this path stays the detail of an entry
# `build-all`, as in plan 60.
API_BUILD_ALL = API + "/build-all"
ENTRY_ROUTE = re.compile(r"^/api/clusters/(%s)(/build|/note)?$"
                         % embeddings.NAME_PATTERN)
JSON_TYPE = "application/json; charset=utf-8"
HTML_TYPE = "text/html; charset=utf-8"
NO_STORE = "no-store"
MAX_BODY = 32768
# The rebuild of a label rule after a note change (plan 45; owner answer of
# 2026-09-26T11:11:00+0300). The command runs as a separate process, as an embedding
# build does, and waits for a running rule build. Its output goes to this file of the
# embedding directory. The page polls the rule until it is current.
REBUILD_COMMAND = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "build_label_rules.py")
REBUILD_LOG = "label-rules.log"
# The queue of `Build all clusters`: None, or the dict of `queue_view`. `_run_queue`
# runs it.
_QUEUE = None
_QUEUE_LOCK = threading.Lock()
# The wait of the queue before the next try of an entry that is busy.
QUEUE_POLL_SECONDS = 1


def start_rule_rebuild(config_path, name, directory, cluster):
    """Start the rebuild of the label rule of the `combined` cluster that holds the first
    card of `cluster`. Return `{started, pid, log}`, or `{started: False, error}`. A
    failure to start does not fail the note write."""
    log_path = os.path.join(directory, REBUILD_LOG)
    command = [sys.executable, REBUILD_COMMAND, "--config", config_path, "--name", name,
               "--cluster", cluster["slugs"][0], "--wait"]
    try:
        with open(log_path, "ab") as log:
            log.write(("%s note of %s: %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                                                cluster["key"], " ".join(command)))
                      .encode("utf-8"))
            log.flush()
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                       stderr=log, cwd=embeddings.ROOT,
                                       start_new_session=True)
    except OSError as exc:
        return {"started": False, "error": str(exc)}
    return {"started": True, "pid": process.pid, "log": log_path}


def handles(route):
    return route == PAGE or route == API or route.startswith(API + "/")


def _json(code, value):
    return code, value, JSON_TYPE, NO_STORE


def _error(code, message):
    return _json(code, {"error": message})


def _body(read_body):
    raw = read_body(MAX_BODY)
    if raw is None:
        return {}
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise clusters.ClusterError("the body MUST be one JSON object") from exc
    if not isinstance(value, dict):
        raise clusters.ClusterError("the body MUST be one JSON object")
    return value


def _known(settings, name):
    for label, embedding, error in settings.entries:
        if label == name:
            if error:
                return None, _error(400, "embedding %s: %s" % (name, error))
            return embedding, None
    return None, _error(404, "config.yaml has no embedding %s" % name)


def list_view(settings):
    entries = []
    for name, embedding, error in settings.entries:
        record = {"name": name, "error": error}
        if embedding is not None:
            directory = embeddings.entry_dir(settings.db_path, name)
            artifact = clusters.load_artifact(directory)
            record.update(directory=directory, exists=artifact is not None)
            if artifact is not None:
                record.update(
                    built_at=artifact.get("built_at"), settings=artifact.get("settings") or {},
                    counts={space: ((artifact.get("spaces") or {}).get(space) or {}).get(
                        "counts") or {} for space in clusters.SPACES})
                try:
                    status = clusters.artifact_status(settings, name)
                except clusters.ClusterError as exc:
                    record.update(stale=True, status_error=str(exc))
                else:
                    record.update(stale=status.get("stale"),
                                  status_error=status.get("current_error"))
        entries.append(record)
    return {"database_file": settings.db_path, "config_file": settings.config_path,
            "embeddings": entries, "queue": queue_view()}


def queue_view():
    """Return a copy of the queue of `Build all clusters`, or None. `state` is `running`,
    `done`, or `failed`. `index` is the position of `current` in `names`. `waiting` tells
    why the build of `current` waits, or is None. `results` holds one
    `{name, state, counts, message}` for each entry that ended; `state` is `done`,
    `skipped`, or `failed`."""
    with _QUEUE_LOCK:
        if _QUEUE is None:
            return None
        return dict(_QUEUE, names=list(_QUEUE["names"]),
                    results=[dict(result) for result in _QUEUE["results"]])


def build_all(settings):
    """Start the queue of `Build all clusters`: the clusters of each entry with no
    configuration error, one at a time, in the order of `config.yaml`. HTTP 409 when a
    queue runs."""
    global _QUEUE
    names = [name for name, embedding, _ in settings.entries if embedding is not None]
    if not names:
        return _error(400, "each embedding of config.yaml has a configuration error")
    with _QUEUE_LOCK:
        if _QUEUE is not None and _QUEUE["state"] == "running":
            return _error(409, "Build all clusters runs: %s, %d of %d" % (
                _QUEUE["current"], _QUEUE["index"] + 1, len(_QUEUE["names"])))
        _QUEUE = {"state": "running", "names": names, "index": 0, "current": names[0],
                  "waiting": None, "results": [], "started_t": time.time(),
                  "ended_t": None, "message": None}
    threading.Thread(target=_run_queue, args=(settings.config_path, names),
                     name="build-all-clusters", daemon=True).start()
    return _json(202, {"queue": queue_view()})


def _update_queue(**fields):
    with _QUEUE_LOCK:
        _QUEUE.update(fields)
        if fields.get("state", "running") != "running":
            _QUEUE["ended_t"] = time.time()


def _build_one(config_path, name):
    """Build the clusters of one entry, as `POST /api/clusters/<name>/build` does. Return
    its result, or None when `config.yaml` cannot be read. A busy entry (its embedding
    build, or another cluster build) is waited for."""
    while True:
        try:
            settings = embeddings.load_settings(config_path)
        except embeddings.ConfigError as exc:
            _update_queue(state="failed", message="config.yaml: %s" % exc)
            return None
        try:
            artifact = clusters.build_to_directory(settings, name)
        except clusters.Busy as exc:
            _update_queue(waiting=str(exc))
            time.sleep(QUEUE_POLL_SECONDS)
            continue
        except clusters.ClusterError as exc:
            return {"name": name, "state": "skipped", "counts": None, "message": str(exc)}
        except (OSError, ValueError) as exc:
            return {"name": name, "state": "failed", "counts": None, "message": str(exc)}
        return {"name": name, "state": "done", "message": None,
                "counts": {space: artifact["spaces"][space]["counts"]
                           for space in clusters.SPACES}}


def _run_queue(config_path, names):
    """The thread of `Build all clusters`. It reads `config.yaml` again for each entry.
    A skipped or failed entry does not stop the queue."""
    try:
        for index, name in enumerate(names):
            _update_queue(index=index, current=name, waiting=None)
            result = _build_one(config_path, name)
            if result is None:
                return
            with _QUEUE_LOCK:
                _QUEUE["results"].append(result)
                _QUEUE["waiting"] = None
        _update_queue(state="done")
    except Exception as exc:  # noqa: BLE001  (a queue that stays `running` blocks the button)
        _update_queue(state="failed", message="%s: %s" % (type(exc).__name__, exc))


def respond(server, method, path, read_body):
    """Return `(code, body, content type, cache)` for one request."""
    route = urllib.parse.urlsplit(path).path
    if route == PAGE:
        if method not in ("GET", "HEAD"):
            return _error(405, "use GET")
        return 200, lab_pages.page("clusters.html"), HTML_TYPE, NO_STORE
    config_path = getattr(server, "config_path", None) or embeddings.CONFIG_PATH
    try:
        settings = embeddings.load_settings(config_path)
    except embeddings.ConfigError as exc:
        return _error(503, str(exc))
    if route == API:
        if method not in ("GET", "HEAD"):
            return _error(405, "use GET")
        try:
            return _json(200, list_view(settings))
        except clusters.ClusterError as exc:
            return _error(503, str(exc))
    if route == API_BUILD_ALL and method == "POST":
        return build_all(settings)
    match = ENTRY_ROUTE.match(route)
    if not match:
        return _error(404, "not found")
    name, action = match.groups()
    _, answer = _known(settings, name)
    if answer:
        return answer
    if action is None:
        if method not in ("GET", "HEAD"):
            return _error(405, "use GET")
        try:
            return _json(200, clusters.detail(settings, name))
        except clusters.ClusterError as exc:
            return _error(409, str(exc))
    if method != "POST":
        return _error(405, "use POST")
    try:
        body = _body(read_body)
        if action == "/build":
            # The owner chose on 2026-09-26 that the page sets no threshold.
            if "full_threshold" in body or "label_threshold" in body:
                raise clusters.ClusterError(
                    "the thresholds come from the block `clusters` of config.yaml")
            artifact = clusters.build_to_directory(settings, name)
            return _json(201, {
                "embedding": name, "built_at": artifact["built_at"],
                "settings": artifact["settings"],
                "counts": {space: artifact["spaces"][space]["counts"]
                           for space in clusters.SPACES},
                "file": os.path.join(embeddings.entry_dir(settings.db_path, name),
                                     clusters.CLUSTERS_FILE),
            })
        directory = embeddings.entry_dir(settings.db_path, name)
        artifact = clusters.load_artifact(directory)
        if artifact is None:
            return _error(409, "embedding %s has no clusters; build them first" % name)
        space = body.get("space")
        key = body.get("key")
        if not isinstance(key, str):
            raise clusters.ClusterError("key MUST be a string")
        cluster = clusters.cluster_in(artifact, space, key)
        if cluster is None:
            return _error(404, "the cluster is not in the current artifact")
        note = clusters.set_note(directory, cluster, body.get("text"))
        rebuild = start_rule_rebuild(config_path, name, directory, cluster)
        return _json(200, {"embedding": name, "space": space, "key": key,
                           "note": note, "rule_rebuild": rebuild})
    except clusters.Busy as exc:
        return _error(409, str(exc))
    except clusters.ClusterError as exc:
        return _error(400, str(exc))
    except (OSError, ValueError) as exc:
        return _error(500, str(exc))
