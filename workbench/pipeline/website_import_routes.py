"""The routes of the website import of the Dataset page of the lab server.

`lab_server.py` sends each route that `handles` accepts to `respond`, and sends the
answer. A compare or an apply runs as a separate process, `import_website.py` with
`--prepare` or `--apply`. Its stdout and stderr go to `run.log` in the run directory
`work/website-import/<run>/`. `job.json` in `work/website-import/` names the present job,
so a restart of the server does not lose it. One job runs at a time. Read
docs/plans/21_website-import-ui.md.

The owner disabled the compare in the code on 2026-09-29: `import_website.COMPARE_ENABLED`
is False. `start` answers 403 and starts no process. The dialog script hides the button
`Import from website`.

    GET  /api/website-import                              the state of the newest run and
                                                          `compare_enabled`
    POST /api/website-import/start                        start a compare (`--prepare`);
                                                          403 while the compare is disabled
    POST /api/website-import/stop                         stop the job (SIGTERM)
    GET  /api/website-import/<run>/diff                   `diff.json` of a run, with `renames`
    POST /api/website-import/<run>/apply                  write `choices.json`, start `--apply`
    GET  /website-import/<run>/images/<sha256>.<ext>      a website image of a run
    GET  /website-import.js                               the script of the dialog
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

import import_website

API = "/api/website-import"
IMAGES = "/website-import/"
SCRIPT_ROUTE = "/website-import.js"
SCRIPT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages",
                           "website_import.js")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "work", "website-import")
JOB_FILE = "job.json"
LOG_FILE = "run.log"
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "import_website.py")
RUN_PATTERN = r"\d{8}T\d{6}"
RUN_ROUTE = re.compile(r"^%s/(%s)/(diff|apply)$" % (API, RUN_PATTERN))
IMAGE_ROUTE = re.compile(r"^%s(%s)/images/([0-9a-f]{64})\.([0-9a-z]+)$"
                         % (IMAGES, RUN_PATTERN))
CONTENT_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                 "webp": "image/webp", "gif": "image/gif", "avif": "image/avif"}
JSON = "application/json; charset=utf-8"
NO_STORE = "no-store"
# A run directory never changes an image, so an image of a run can stay in a cache.
IMAGE_CACHE = "public, max-age=31536000, immutable"
# The largest body of an apply: one choice for each conflict and each change.
BODY_LIMIT = 4 * 1024 * 1024
# The progress lines of `import_website.py`.
PROGRESS = re.compile(r"^(list|images): ")

# run directory -> the process that this server started. The server reaps it.
_PROCESSES = {}
_START = threading.Lock()


def handles(route):
    """Tell whether a route belongs to the website import."""
    return (route in (API, SCRIPT_ROUTE) or route.startswith(API + "/")
            or route.startswith(IMAGES))


def _json(code, value):
    return code, value, JSON, NO_STORE


def _error(code, message):
    return _json(code, {"error": message})


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _running():
    """Return the present job, or None. A job whose process ended is not running."""
    for directory, process in list(_PROCESSES.items()):
        if process.poll() is not None:
            del _PROCESSES[directory]
    job = _read_json(os.path.join(WORK, JOB_FILE))
    if not isinstance(job, dict) or not isinstance(job.get("pid"), int):
        return None
    directory = os.path.join(WORK, job.get("run", ""))
    process = _PROCESSES.get(directory)
    if process is not None:
        return job
    return job if _alive(job["pid"]) else None


def _runs():
    try:
        names = [name for name in os.listdir(WORK) if re.fullmatch(RUN_PATTERN, name)]
    except FileNotFoundError:
        return []
    return sorted(names)


def _tail(path, limit=64 * 1024):
    """Return the lines of the end of a log file."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - limit))
            return fh.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return []


def _counts(diff):
    kinds = {}
    for entry in diff["changes"]:
        kinds[entry["kind"]] = kinds.get(entry["kind"], 0) + 1
    return {"conflicts": len(diff["conflicts"]), "changes": kinds,
            "refused": diff.get("refused", 0), "website": diff.get("website", 0)}


def run_state(run):
    """Return the state of one run: `running`, `prepared`, `applied`, or `failed`."""
    directory = os.path.join(WORK, run)
    job = _running()
    lines = _tail(os.path.join(directory, LOG_FILE))
    progress = next((line for line in reversed(lines) if PROGRESS.match(line)), None)
    out = {"run": run, "progress": progress}
    if job is not None and job.get("run") == run:
        return dict(out, state="running", phase=job.get("phase"), pid=job["pid"],
                    started_at=job.get("started_at"))
    result = _read_json(os.path.join(directory, import_website.RESULT_FILE))
    diff = _read_json(os.path.join(directory, import_website.DIFF_FILE))
    errors = [line[len("error: "):] for line in lines if line.startswith("error: ")]
    if isinstance(result, dict):
        if result.get("ok"):
            return dict(out, state="applied", phase="apply", result=result)
        return dict(out, state="failed", phase="apply", error=result.get("error"),
                    counts=_counts(diff) if isinstance(diff, dict) else None)
    if isinstance(diff, dict):
        return dict(out, state="prepared", phase="prepare", counts=_counts(diff),
                    created_at=diff.get("created_at"))
    return dict(out, state="failed", phase="prepare",
                error="\n".join(errors) or "the compare ended with no diff; read %s"
                % os.path.join(directory, LOG_FILE))


def state_view():
    """Return the state of the newest run and `compare_enabled`. The dialog hides its
    button when the compare is disabled."""
    runs = _runs()
    view = {"state": "none"} if not runs else run_state(runs[-1])
    return dict(view, compare_enabled=import_website.COMPARE_ENABLED)


def _start(server, run, phase, extra=()):
    """Start `import_website.py` for one run. Return an answer."""
    directory = os.path.join(WORK, run)
    with _START:
        job = _running()
        if job is not None:
            return _error(409, "a website import runs: run %s, %s, PID %s"
                          % (job.get("run"), job.get("phase"), job.get("pid")))
        os.makedirs(directory, exist_ok=True)
        mode = "--prepare" if phase == "prepare" else "--apply"
        with open(os.path.join(directory, LOG_FILE), "ab") as log:
            process = subprocess.Popen(
                [sys.executable, SCRIPT, "--db", os.path.abspath(server.db_path), mode,
                 directory] + list(extra),
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT,
                start_new_session=True)
        _PROCESSES[directory] = process
        import_website.write_json(os.path.join(WORK, JOB_FILE), {
            "run": run, "phase": phase, "pid": process.pid,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    return _json(202, {"run": run, "phase": phase, "state": "running", "pid": process.pid})


def start(server):
    if not import_website.COMPARE_ENABLED:
        return _error(403, import_website.COMPARE_DISABLED)
    run = time.strftime("%Y%m%dT%H%M%S")
    if run in _runs():
        return _error(409, "a run %s exists; start again in one second" % run)
    return _start(server, run, "prepare")


def stop():
    job = _running()
    if job is None:
        return _error(409, "no website import runs")
    try:
        os.kill(job["pid"], signal.SIGTERM)
    except ProcessLookupError:
        return _error(409, "no website import runs")
    return _json(202, {"run": job.get("run"), "state": "stopping", "pid": job["pid"]})


def apply(server, run, read_body):
    directory = os.path.join(WORK, run)
    state = run_state(run)
    if state["state"] != "prepared" and not (state["state"] == "failed"
                                              and state["phase"] == "apply"):
        return _error(409, "run %s is %s; the dialog needs a prepared run" % (run, state["state"]))
    raw = read_body(BODY_LIMIT)
    if raw is None:
        return _error(400, "the body MUST be JSON of at most %d bytes" % BODY_LIMIT)
    try:
        choices = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return _error(400, "the body is not JSON")
    diff = _read_json(os.path.join(directory, import_website.DIFF_FILE))
    try:
        import_website.check_choices(diff, choices)
    except import_website.WebsiteError as exc:
        return _error(400, str(exc))
    for name in (import_website.RESULT_FILE,):
        try:
            os.unlink(os.path.join(directory, name))
        except FileNotFoundError:
            pass
    import_website.write_json(os.path.join(directory, import_website.CHOICES_FILE), choices)
    return _start(server, run, "apply")


def _image(run, digest, extension):
    path = os.path.join(WORK, run, import_website.IMAGES_DIR, "%s.%s" % (digest, extension))
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return _error(404, "run %s has no image %s.%s" % (run, digest, extension))
    return 200, data, CONTENT_TYPES.get(extension, "application/octet-stream"), IMAGE_CACHE


def respond(server, method, path, read_body):
    """Return (HTTP code, body, content type, cache) of one request. A dict body is JSON.
    `read_body(limit)` returns the bytes of the request body, or None when the body is
    empty or longer than `limit`."""
    route = urllib.parse.urlsplit(path).path
    if route == SCRIPT_ROUTE:
        if method not in ("GET", "HEAD"):
            return _error(405, "use GET")
        with open(SCRIPT_FILE, encoding="utf-8") as fh:
            return 200, fh.read(), "text/javascript; charset=utf-8", NO_STORE
    image = IMAGE_ROUTE.match(route)
    if image:
        if method not in ("GET", "HEAD"):
            return _error(405, "use GET")
        return _image(*image.groups())
    if route == API:
        if method not in ("GET", "HEAD"):
            return _error(405, "use GET")
        return _json(200, state_view())
    if route in (API + "/start", API + "/stop"):
        if method != "POST":
            return _error(405, "use POST")
        return start(server) if route.endswith("/start") else stop()
    match = RUN_ROUTE.match(route)
    if not match or not os.path.isdir(os.path.join(WORK, match.group(1))):
        return _error(404, "not found")
    run, action = match.groups()
    if action == "diff":
        if method not in ("GET", "HEAD"):
            return _error(405, "use GET")
        diff = _read_json(os.path.join(WORK, run, import_website.DIFF_FILE))
        if diff is None:
            return _error(404, "run %s has no diff" % run)
        return _json(200, dict(diff, run=run, renames=import_website.renames(diff)))
    if method != "POST":
        return _error(405, "use POST")
    return apply(server, run, read_body)
