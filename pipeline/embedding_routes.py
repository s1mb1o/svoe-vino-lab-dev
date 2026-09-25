"""The routes of the Embeddings page of the lab server.

`lab_server.py` sends each route that `handles` accepts to `respond`, and sends the
answer. The routes read `config.yaml` at each request, so a new entry appears with no
restart. A build runs as a separate process, `build_embeddings.py`. Its stdout and
stderr go to `build.log` in the directory of the entry. The job state comes from
`build.lock` and `build.log`, so a restart of the server does not lose a running build.
Read docs/plans/10_embeddings-page.md.

    GET  /embedding                                   the page
    GET  /api/embeddings                              each entry, its counts, its job
    GET  /api/embeddings/<name>                       the wines and the cells of one entry
    POST /api/embeddings/<name>/build                 start a build
    POST /api/embeddings/<name>/stop                  stop a build (SIGTERM)
    POST /api/embeddings/<name>/open                  open the directory in Finder
    GET  /api/embeddings/<name>/log                   the text of `build.log`
    GET  /api/embedding-jobs                          the job of each entry
    GET  /embeddings/<name>/images/<sha256>_<view>.png  one prepared image
"""
import collections
import os
import re
import signal
import subprocess
import sys
import threading
import urllib.parse
from contextlib import closing

import numpy as np

import embeddings
import lab_pages

PAGE = "/embedding"
API_LIST = "/api/embeddings"
API_JOBS = "/api/embedding-jobs"
ENTRY_ROUTE = re.compile(r"^/api/embeddings/(%s)(/build|/stop|/open|/log)?$"
                         % embeddings.NAME_PATTERN)
# The command that opens a directory in Finder. The lab server runs on the Mac of the
# owner, so the window opens there.
OPEN_COMMAND = ("open",)
IMAGE_ROUTE = re.compile(r"^/embeddings/(%s)/images/([0-9a-f]{64})_(%s)\.png$"
                         % (embeddings.NAME_PATTERN, "|".join(embeddings.VIEWS)))
BUILD_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            embeddings.BUILD_SCRIPT_NAME)
JSON = "application/json; charset=utf-8"
HTML = "text/html; charset=utf-8"
NO_STORE = "no-store"
# The URL of a prepared image holds its embedding hash, so a new image gets a new URL.
IMAGE_CACHE = "public, max-age=31536000, immutable"
STATUSES = ("current", "stale", "missing", "failed")

# entry directory -> the build process that this server started. The server reaps it.
_PROCESSES = {}
_START = threading.Lock()


def handles(route):
    """Tell whether a route belongs to the Embeddings page."""
    return (route in (PAGE, API_LIST, API_JOBS) or route.startswith(API_LIST + "/")
            or route.startswith("/embeddings/"))


def _json(code, value):
    return code, value, JSON, NO_STORE


def _error(code, message):
    return _json(code, {"error": message})


def respond(server, method, path):
    """Return (HTTP code, body, content type, cache) of one request. A dict or a list
    body is JSON."""
    route = urllib.parse.urlsplit(path).path
    config_path = getattr(server, "config_path", None) or embeddings.CONFIG_PATH
    if route == PAGE:
        if method not in ("GET", "HEAD"):
            return _error(405, "use GET")
        return 200, lab_pages.page("embedding.html"), HTML, NO_STORE
    try:
        settings = embeddings.load_settings(config_path)
    except embeddings.ConfigError as exc:
        return _error(503, str(exc))
    image = IMAGE_ROUTE.match(route)
    if image:
        if method not in ("GET", "HEAD"):
            return _error(405, "use GET")
        return _image(settings, *image.groups())
    try:
        if route == API_LIST:
            if method not in ("GET", "HEAD"):
                return _error(405, "use GET")
            return _json(200, list_view(settings))
        if route == API_JOBS:
            if method not in ("GET", "HEAD"):
                return _error(405, "use GET")
            return _json(200, {"jobs": jobs_view(settings)})
        entry = ENTRY_ROUTE.match(route)
        if not entry:
            return _error(404, "not found")
        name, action = entry.groups()
        if action is None:
            if method not in ("GET", "HEAD"):
                return _error(405, "use GET")
            return entry_view(settings, name)
        if action == "/log":
            if method not in ("GET", "HEAD"):
                return _error(405, "use GET")
            return build_log(settings, name)
        if method != "POST":
            return _error(405, "use POST")
        return {"/build": start, "/stop": stop, "/open": open_directory}[action](
            settings, name)
    except embeddings.ConfigError as exc:
        return _error(503, str(exc))


def _lookup(settings, name):
    """Return (embedding, None) or (None, an answer)."""
    try:
        return settings.find(name), None
    except KeyError:
        return None, _error(404, "config.yaml has no embedding %s" % name)
    except embeddings.ConfigError as exc:
        return None, _error(400, "embedding %s: %s" % (name, exc))


def _reap():
    for directory, process in list(_PROCESSES.items()):
        if process.poll() is not None:
            del _PROCESSES[directory]


def job(directory):
    """Return the job of one entry. A process that this server started a moment ago
    is `running` before it takes its lock."""
    _reap()
    state = embeddings.job_state(directory)
    process = _PROCESSES.get(directory)
    if process is not None and state["state"] not in ("running", "stopping"):
        state.update(state="running", pid=process.pid, message="starting",
                     todo=None, done=0, built=0, failed=0)
    return state


def _read(directory):
    """Return the index of an entry, the names of its images, and an error or None."""
    try:
        return embeddings.read_index(directory) or {}, embeddings.image_names(directory), None
    except (ValueError, OSError) as exc:
        return {}, set(), "the index cannot be read: %s" % exc


def _vector_rows(directory, index):
    """Return the number of rows of the vectors file that the index names, or 0. The file
    is mapped, not read."""
    name = index.get("vectors_file")
    if not name or not embeddings.VECTORS_RE.match(name):
        return 0
    try:
        vectors = np.load(os.path.join(directory, name), mmap_mode="r", allow_pickle=False)
    except (OSError, ValueError):
        return 0
    return int(vectors.shape[0]) if vectors.ndim == 2 else 0


def _inputs(settings):
    with closing(embeddings.open_database(settings.db_path)) as conn:
        return embeddings.read_inputs(conn, settings.db_path)


def list_view(settings):
    """Return each entry with its settings, its counts, and its job."""
    _, sources = _inputs(settings)
    out = []
    for name, embedding, error in settings.entries:
        record = {"name": name, "error": error}
        if embedding is not None:
            directory = embeddings.entry_dir(settings.db_path, name)
            items = embeddings.plan_items(embedding, sources)
            index, names, index_error = _read(directory)
            status = embeddings.item_status(items, index, names)
            counts = collections.Counter(state for state, _ in status.values())
            record.update(embedding.summary(), items=len(items),
                          counts={state: counts.get(state, 0) for state in STATUSES},
                          dim=index.get("dim"), updated_at=index.get("updated_at"),
                          index_error=index_error, job=job(directory))
        out.append(record)
    return {"database_file": settings.db_path, "config_file": settings.config_path,
            "embeddings": out}


def image_url(name, source_sha256, view, embedding_hash):
    return "/embeddings/%s/images/%s?v=%s" % (
        name, embeddings.image_name(source_sha256, view), embedding_hash[:16])


def entry_view(settings, name):
    """Return the wines of one entry. Each column of a wine is one source image, with a
    cell for each view."""
    embedding, answer = _lookup(settings, name)
    if answer:
        return answer
    wines, sources = _inputs(settings)
    directory = embeddings.entry_dir(settings.db_path, name)
    items = embeddings.plan_items(embedding, sources)
    index, names, index_error = _read(directory)
    rows = _vector_rows(directory, index)
    status = embeddings.item_status(items, index, names)
    records = []
    for wine in wines:
        columns = []
        for image_type, digest in wine["columns"]:
            source = sources[digest]
            cells = {}
            for view in embedding.views:
                key = (digest, view)
                if key not in items:
                    continue
                state, record = status[key]
                cell = {"status": state, "hash": items[key]["embedding_hash"]}
                if embeddings.image_name(*key) in names:
                    shown = record["embedding_hash"] if state in ("current", "stale") \
                        else items[key]["embedding_hash"]
                    cell["url"] = image_url(name, digest, view, shown)
                if record and state in ("current", "stale"):
                    cell.update(width=record.get("width"), height=record.get("height"))
                    # `vector`: the vectors file holds the row of this item. A stale item
                    # keeps the vector of its old hash.
                    row = record.get("row")
                    if isinstance(row, int) and 0 <= row < rows:
                        cell["vector"] = True
                if state == "failed":
                    cell["error"] = record.get("error")
                cells[view] = cell
            columns.append({"image_type": image_type, "role": source["role"],
                            "sha256": digest, "original_url": source["url"],
                            "cells": cells})
        records.append({"slug": wine["slug"], "name": wine["name"],
                        "producer": wine["producer"], "category": wine["category"],
                        "region": wine["region"], "columns": columns})
    counts = collections.Counter(state for state, _ in status.values())
    return _json(200, {
        "embedding": dict(embedding.summary(), items=len(items),
                          counts={state: counts.get(state, 0) for state in STATUSES},
                          dim=index.get("dim"), updated_at=index.get("updated_at"),
                          software=index.get("software"), index_error=index_error,
                          directory=directory, job=job(directory)),
        "records": records})


def jobs_view(settings):
    out = []
    for name, embedding, _ in settings.entries:
        if embedding is not None:
            out.append(dict(job(embeddings.entry_dir(settings.db_path, name)), name=name))
    return out


def start(settings, name):
    """Start a build of one entry. HTTP 409 when a build of it runs."""
    embedding, answer = _lookup(settings, name)
    if answer:
        return answer
    python = settings.python or sys.executable
    if not os.path.isfile(python):
        return _error(400, "embedding_python %s is not a file; create the venv with "
                           "requirements-local.txt" % python)
    directory = embeddings.entry_dir(settings.db_path, name)
    with _START:
        state = job(directory)
        if state["state"] in ("running", "stopping"):
            return _error(409, "a build of %s runs: PID %s" % (name, state["pid"]))
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, embeddings.LOG), "wb") as log:
            process = subprocess.Popen(
                [python, BUILD_SCRIPT, "--config", settings.config_path, "--name", name],
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                cwd=embeddings.ROOT, start_new_session=True)
        _PROCESSES[directory] = process
    return _json(202, {"name": name, "state": "running", "pid": process.pid})


def stop(settings, name):
    """Send SIGTERM to the build of one entry. HTTP 409 when no build runs."""
    embedding, answer = _lookup(settings, name)
    if answer:
        return answer
    directory = embeddings.entry_dir(settings.db_path, name)
    pid = embeddings.running_pid(directory)
    if pid is None:
        process = _PROCESSES.get(directory)
        if process is None or process.poll() is not None:
            return _error(409, "no build of %s runs" % name)
        pid = process.pid
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return _error(409, "no build of %s runs" % name)
    return _json(202, {"name": name, "state": "stopping", "pid": pid})


def open_directory(settings, name):
    """Open the directory of one entry in Finder. The route opens no other path. HTTP 404
    when the directory is not on disk yet, 500 when the command fails."""
    embedding, answer = _lookup(settings, name)
    if answer:
        return answer
    directory = embeddings.entry_dir(settings.db_path, name)
    if not os.path.isdir(directory):
        return _error(404, "the directory of %s is not on disk yet: %s" % (name, directory))
    try:
        subprocess.run(OPEN_COMMAND + (directory,), check=True, timeout=10,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except (OSError, subprocess.SubprocessError) as exc:
        return _error(500, "cannot open %s: %s" % (directory, exc))
    return _json(200, {"name": name, "opened": directory})


def build_log(settings, name):
    """Return the text of `build.log` of one entry. HTTP 404 when no build wrote it yet."""
    embedding, answer = _lookup(settings, name)
    if answer:
        return answer
    path = os.path.join(embeddings.entry_dir(settings.db_path, name), embeddings.LOG)
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except FileNotFoundError:
        return _error(404, "%s has no build log yet" % name)
    return _json(200, {"name": name, "file": path, "text": text})


def _image(settings, name, digest, view):
    path = os.path.join(embeddings.entry_dir(settings.db_path, name), embeddings.IMAGES,
                        embeddings.image_name(digest, view))
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return 404, "not found", "text/plain; charset=utf-8", NO_STORE
    return 200, data, "image/png", IMAGE_CACHE
