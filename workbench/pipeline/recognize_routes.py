"""The routes of the Recognize page of the lab server (plan 55).

    GET  /recognize                                the page
    GET  /api/recognize                            the pipelines of the backend
                                                   `embedding`, runnable or not
    POST /api/recognize?pipeline=<name>&name=<file name>
                                                   recognize one photo: the body is the
                                                   image; the answer is the step view
    GET  /recognize/photo/<sha256>.<ext>           an uploaded photo

The POST writes the photo to `work/recognize/<sha256>.<ext>` and starts
`recognize.py` with `embedding_python` (`run_jobs.interpreter`), one process for each
photo (owner answer of 2026-09-26T22:37:00+0300). The script builds the backend of the
pipeline and asks it one time. The route makes the rounds and the steps of the answer
with `run_steps.embedding_rounds`, as the step popup of `/runs` does (plan 41). The
answer has the keys of `/api/run-steps`, and in addition `pipeline`, `sha256`, `answer`,
`build_ms`, and `process_ms`.

The module writes no file other than the upload, deletes no upload, and changes no row
of the lab database. Read docs/plans/55_recognize-page.md.
"""
import hashlib
import io
import json
import os
import re
import sqlite3
import subprocess
import time
import urllib.parse
from contextlib import closing
from pathlib import Path

from PIL import Image

import embeddings
import lab_pages
import pipelines
import run_jobs
import testsets

PAGE = "/recognize"
API = "/api/recognize"
PHOTO_PREFIX = "/recognize/photo/"
PHOTO_ROUTE = re.compile(r"^/recognize/photo/([0-9a-f]{64})\.([0-9a-z]{1,8})$")
UPLOAD_DIR = os.path.join(embeddings.ROOT, "work", "recognize")
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recognize.py")
# The wait for the script: a pipeline of the backend `local` loads its model first.
TIMEOUT_S = 300
MAX_NAME = 200
JSON_TYPE = "application/json; charset=utf-8"
HTML_TYPE = "text/html; charset=utf-8"
NO_STORE = "no-store"
# An upload never changes under its name, so a browser can keep it.
PHOTO_CACHE = "public, max-age=31536000, immutable"
# The Pillow format -> the extension of the upload file. Another format gets its name.
EXTENSIONS = {"JPEG": "jpg", "MPO": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif",
              "BMP": "bmp", "TIFF": "tiff"}
CONTENT_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp",
                 "gif": "image/gif", "bmp": "image/bmp", "tiff": "image/tiff"}
# The keys of the row of the answer, as in `/api/run-steps`.
ROW_KEYS = ("label", "outcome", "rank_of_truth", "truth", "slug", "latency_ms", "error",
            "image_path")


class RecognizeError(Exception):
    """The request cannot give an answer. `code` is the HTTP code."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def handles(route):
    """Answer whether `route` belongs to the Recognize page."""
    return route in (PAGE, API) or route.startswith(PHOTO_PREFIX)


def _json(code, value):
    return code, value, JSON_TYPE, NO_STORE


def _error(code, message):
    return _json(code, {"error": message})


def pipelines_view(config_path):
    """Return the answer of `GET /api/recognize`: each pipeline of the backend
    `embedding`, in the order of `config.yaml`. A pipeline with a configuration error
    stays in the list, not runnable, because its backend is not known."""
    settings = pipelines.load(config_path)
    out = []
    for name, pipeline, error in settings.entries:
        if pipeline is not None and pipeline.backend != pipelines.EMBEDDING_BACKEND:
            continue
        runnable, reason = run_jobs.runnable(pipeline, error, settings.db_path)
        out.append({"name": name, "embedding": pipeline.embedding if pipeline else None,
                    "barcode": bool(pipeline and pipeline.barcode is not None),
                    "rerank": bool(pipeline and pipeline.rerank is not None),
                    "runnable": runnable, "reason": reason})
    return {"pipelines": out}


def find_pipeline(config_path, name):
    """Return (the settings, the pipeline `name`). Raise `RecognizeError`."""
    settings = pipelines.load(config_path)
    try:
        pipeline = settings.find(name)
    except KeyError:
        raise RecognizeError(400, "config.yaml has no pipeline %s" % name)
    except embeddings.ConfigError as exc:
        raise RecognizeError(400, "the pipeline %s is not valid: %s" % (name, exc))
    if pipeline.backend != pipelines.EMBEDDING_BACKEND:
        raise RecognizeError(400, "the pipeline %s has the backend %s; this page runs the "
                                  "backend %s alone"
                             % (name, pipeline.backend, pipelines.EMBEDDING_BACKEND))
    runnable, reason = run_jobs.runnable(pipeline, None, settings.db_path)
    if not runnable:
        raise RecognizeError(400, "%s cannot run: %s" % (name, reason))
    return settings, pipeline


def store_upload(data, upload_dir=None):
    """Write the image `data` to `<upload_dir>/<sha256>.<ext>` and return (the sha256, the
    extension, the path). A file with the same name stays as it is. Raise
    `RecognizeError` when Pillow cannot read the image."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            image_format = image.format
            image.load()
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise RecognizeError(400, "the body is not an image that Pillow can read: %s" % exc)
    extension = EXTENSIONS.get(image_format, str(image_format or "bin").lower())
    digest = hashlib.sha256(data).hexdigest()
    directory = upload_dir or UPLOAD_DIR
    path = os.path.join(directory, "%s.%s" % (digest, extension))
    if not os.path.isfile(path):
        os.makedirs(directory, exist_ok=True)
        part = "%s.%d.part" % (path, os.getpid())
        with open(part, "wb") as fh:
            fh.write(data)
        os.replace(part, path)
    return digest, extension, path


def run_script(python, config_path, name, photo, timeout=TIMEOUT_S):
    """Run `recognize.py` for one photo. Return (its answer, the wall time in ms). Raise
    `RecognizeError` when the script gives no answer."""
    command = [python, SCRIPT, "--config", config_path, "--name", name, "--photo", photo]
    started = time.perf_counter()
    try:
        done = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=timeout, cwd=embeddings.ROOT)
    except subprocess.TimeoutExpired:
        raise RecognizeError(503, "the pipeline %s gave no answer in %d s" % (name, timeout))
    except OSError as exc:
        raise RecognizeError(503, "cannot start %s: %s" % (python, exc))
    process_ms = round((time.perf_counter() - started) * 1000, 1)
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    try:
        answer = json.loads(lines[-1]) if lines else None
    except ValueError:
        answer = None
    if not isinstance(answer, dict):
        tail = done.stderr.strip().splitlines()[-3:]
        raise RecognizeError(503, "recognize.py wrote no answer (exit status %s): %s"
                             % (done.returncode, " | ".join(tail) or "no output"))
    if done.returncode != 0 or "trace" not in answer:
        raise RecognizeError(503, str(answer.get("error") or "recognize.py failed with the "
                                      "exit status %s" % done.returncode))
    return answer, process_ms


def _run_steps():
    import run_steps  # noqa: E402  (PIL, numpy, and the SAM3 cuts, on demand)
    return run_steps


def upload_photo_class():
    """Return the photo class of an upload: a `run_steps.Photo` that reads a file of
    `work/recognize/` in place of the lab image store."""
    run_steps = _run_steps()
    import derive  # noqa: E402  (here alone, as run_steps)

    class UploadPhoto(run_steps.Photo):
        def __init__(self, path, url, extension):  # noqa: D401 - no call of the base
            self.path, self.url, self.extension = path, url, extension
            self.image, self.error = None, None
            try:
                self.image, _icc = derive.open_image(path)
            except OSError as exc:
                self.error = "Pillow cannot read the photo: %s" % exc

    return UploadPhoto


class Context:
    """The context of `run_steps.embedding_rounds` for one upload."""

    def __init__(self, db_path, conn, row, spec, photo, card_images):
        self.db_path, self.conn, self.row, self.spec = db_path, conn, row, spec
        self.kind = "embedding"
        self.photo = photo
        self.lists = _run_steps().Lists(conn, row, card_images)
        self.notes = []


def steps_answer(db_path, name, file_name, digest, extension, path, answer, card_images):
    """Return the step view of one recognized photo."""
    run_steps = _run_steps()
    row = {"image_path": file_name, "image_sha256": digest, "label": None,
           "outcome": None, "rank_of_truth": None, "truth": [], "slug": None,
           "candidates": answer.get("candidates") or [],
           "latency_ms": answer.get("latency_ms"), "http_status": answer.get("http_status"),
           "error": answer.get("error"), "trace": answer.get("trace")}
    spec = answer.get("spec") if isinstance(answer.get("spec"), dict) else {}
    photo = upload_photo_class()(path, "%s%s.%s" % (PHOTO_PREFIX, digest, extension),
                                 extension)
    try:
        conn = sqlite3.connect(Path(os.path.abspath(db_path)).as_uri() + "?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise RecognizeError(503, "cannot read the lab database: %s" % exc)
    with closing(conn):
        ctx = Context(db_path, conn, row, spec, photo, card_images)
        rounds, number = [], 0
        for n, (note, steps) in enumerate(run_steps.embedding_rounds(ctx)):
            for part in steps:
                part["n"] = number
                number += 1
            rounds.append({"n": n, "title": "Round %d" % n, "note": note, "steps": steps})
        ctx.lists.finish(rounds)
    names = {item["slug"]: item.get("name") for one in rounds for part in one["steps"]
             for group in part["lists"] for item in group["items"]}
    return {
        "pipeline": name, "kind": "embedding", "configuration": name, "sha256": digest,
        "photo": photo.head(row), "row": {key: row.get(key) for key in ROW_KEYS},
        "recorded": isinstance(row["trace"], dict), "rounds": rounds, "notes": ctx.notes,
        "answer": [{"slug": c.get("slug"), "name": names.get(c.get("slug")),
                    "rank": c.get("rank"), "score": c.get("score"), "code": c.get("code")}
                   for c in row["candidates"]],
        "build_ms": answer.get("build_ms"),
    }


def recognize(server, query, read_body, card_images, run=None):
    """Answer `POST /api/recognize`. Raise `RecognizeError`. `run` replaces `run_script`
    in a test."""
    fields = {key: values[0] for key, values in urllib.parse.parse_qs(query).items()}
    name = fields.get("pipeline") or ""
    if not name:
        raise RecognizeError(400, "the query holds no pipeline")
    file_name = (fields.get("name") or "photo")[:MAX_NAME]
    config_path = getattr(server, "config_path", None) or embeddings.CONFIG_PATH
    settings, pipeline = find_pipeline(config_path, name)
    data = read_body(testsets.UPLOAD_MAX)
    if not data:
        raise RecognizeError(400, "the body MUST be an image of 1 to %d bytes"
                             % testsets.UPLOAD_MAX)
    digest, extension, path = store_upload(data, getattr(server, "recognize_dir", None))
    try:
        python = run_jobs.interpreter(settings, pipeline)
    except embeddings.ConfigError as exc:
        raise RecognizeError(503, str(exc))
    answer, process_ms = (run or run_script)(python, settings.config_path, name, path)
    out = steps_answer(server.db_path, name, file_name, digest, extension, path, answer,
                       card_images)
    out["process_ms"] = process_ms
    return out


def photo(server, route):
    """Answer `GET /recognize/photo/<sha256>.<ext>`."""
    match = PHOTO_ROUTE.match(route)
    if not match:
        return _error(404, "no such photo")
    directory = getattr(server, "recognize_dir", None) or UPLOAD_DIR
    try:
        with open(os.path.join(directory, "%s.%s" % match.groups()), "rb") as fh:
            data = fh.read()
    except OSError:
        return _error(404, "no such photo")
    ctype = CONTENT_TYPES.get(match.group(2), "application/octet-stream")
    return 200, data, ctype, PHOTO_CACHE


def respond(server, method, path, read_body, card_images):
    """Answer one request. Return (HTTP code, body, content type, Cache-Control). A dict
    body is JSON. `card_images(conn)` is `lab_server.card_images`."""
    parts = urllib.parse.urlsplit(path)
    route = parts.path
    if route == API and method == "POST":
        try:
            return _json(200, recognize(server, parts.query, read_body, card_images))
        except RecognizeError as exc:
            return _error(exc.code, str(exc))
    if method not in ("GET", "HEAD"):
        return _error(405, "the route %s answers GET alone" % route)
    if route == PAGE:
        return 200, lab_pages.page("recognize.html"), HTML_TYPE, NO_STORE
    if route == API:
        config_path = getattr(server, "config_path", None) or embeddings.CONFIG_PATH
        return _json(200, pipelines_view(config_path))
    return photo(server, route)
