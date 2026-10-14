"""Compute local patch diagnostics for a saved query. Keep historical results unchanged."""

from contextlib import closing
import hashlib
import inspect
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import urllib.parse

_JOBS = {}
_LOCK = threading.Lock()
_WORKER_LOCK = threading.Lock()
ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT if (ROOT / "patch_pipeline").is_dir() else ROOT.parent / "svoe-vino-lab-experiments"
EVIDENCE = EXPERIMENT / "internal/patch-retrieval-20261014"
JSON_TYPE = "application/json; charset=utf-8"


def _one(query, key):
    values = query.get(key, [])
    if len(values) != 1 or not values[0]:
        raise ValueError("one %s is required" % key)
    return values[0]


def _run(directory, photo, sidecar):
    with _WORKER_LOCK:
        try:
            environment = dict(os.environ, PYTHONPATH=str(EXPERIMENT))
            worker_python = os.environ.get("PATCH_INSPECTION_PYTHON") or str(Path.home()/".venvs/svoe-vino-lab/bin/python")
            if not Path(worker_python).is_file():
                worker_python = sys.executable
            command = [worker_python, "-m", "patch_pipeline.inspection", "--index", str(EVIDENCE / "index-tuned"),
                       "--image", photo, "--annotation", str(sidecar), "--output", str(directory),
                       "--selection", str(EVIDENCE / "tuning/selected.json")]
            with (directory / "worker.log").open("wb") as log:
                process = subprocess.run(command, cwd=EXPERIMENT, env=environment,
                                         stdout=log, stderr=log, timeout=240)
            if process.returncode:
                raise RuntimeError("Local patch computation failed. Read the local worker log.")
        except Exception as exc:
            (directory / "error.json").write_text(json.dumps({"status": "failed", "error": str(exc)}))


def _sidecar(photo, spec, directory):
    """Use approved masks or existing local cuts. Never request SAM3 inference."""
    import run_steps
    import derive
    from PIL import Image
    for name in ("queries-fresh.json", "references-fresh.json"):
        for item in json.loads((EVIDENCE / name).read_text())["items"]:
            if Path(item["image"]).name == Path(photo.path).name and item.get("annotation"):
                return Path(item["annotation"])
    masks = {}
    sam3 = spec.get("sam3") or {}
    endpoint = sam3.get("endpoint") or derive.SAM3_ENDPOINT
    for role, target in (("bottle", "package"), ("label", "label")):
        options = {"label_mask_union": sam3.get("label_mask_union", True),
                   "label_focus": sam3.get("label_focus") == "main"}
        supported = inspect.signature(run_steps._cut).parameters
        options = {key: value for key, value in options.items() if key in supported}
        box, cut, _reason, _result = run_steps._cut(photo, target, endpoint,
                                                  spec.get("scene_selection", False), **options)
        if box is not None and cut is not None:
            mask = Image.new("L", photo.image.size, 0)
            mask.paste(cut.convert("RGBA").getchannel("A"), (int(box[0]), int(box[1])))
            mask.save(directory / (role + ".png"))
            masks[role] = role + ".png"
    sidecar = directory / "annotation.json"
    sidecar.write_text(json.dumps({"size": list(photo.image.size), "masks": masks,
                       "provenance": {"scope": "Existing local SAM3 cache only. Hand and finger masks are unavailable for this photo."}}))
    return sidecar


def respond(db_path, path, runs_dir=None):
    import run_steps
    import run_routes
    try:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
        run, identity = _one(query, "id"), _one(query, "query")
        row, _meta, spec = run_steps._run_data(runs_dir or run_routes.RUNS_DIR, run, identity)
        with closing(sqlite3.connect(Path(db_path).resolve().as_uri()+"?mode=ro", uri=True)) as connection:
            photo = run_steps.Photo(connection, db_path, row)
        if not photo.path or photo.image is None:
            return 404, {"error": "The saved query image is unavailable."}, JSON_TYPE
        index = EVIDENCE / "index-tuned/index.json"
        selection = EVIDENCE / "tuning/selected.json"
        if not index.is_file() or not selection.is_file():
            return 503, {"error": "The tuned patch index is not available."}, JSON_TYPE
        digest = hashlib.sha256(Path(photo.path).read_bytes())
        for item in [index, selection, Path(__file__), *sorted((EXPERIMENT / "patch_pipeline").glob("*.py"))]:
            digest.update(item.read_bytes())
        digest.update(json.dumps([run,identity],ensure_ascii=False).encode())
        key = digest.hexdigest()
        directory = Path(db_path).resolve().parent.parent / "cache/patch-inspection" / key
        ready = directory / "inspection.json"
        if ready.is_file():
            result = json.loads(ready.read_text())
            picture = query.get("candidate", [None])[0]
            if picture is not None:
                number = int(picture)
                if number < 0 or number >= len(result["candidates"]):
                    raise ValueError("unknown candidate")
                image = directory / result["candidates"][number]["image"]
                return 200, image.read_bytes(), "image/png"
            result["cache_key"] = key
            for number, candidate in enumerate(result["candidates"]):
                candidate["src"] = "/api/run-patches?" + urllib.parse.urlencode({"id":run,"query":identity,"candidate":number})
            return 200, result, JSON_TYPE
        if (directory / "error.json").exists():
            return 200, json.loads((directory / "error.json").read_text()), JSON_TYPE
        with _LOCK:
            if key not in _JOBS and query.get("start") == ["1"]:
                directory.mkdir(parents=True, exist_ok=True)
                sidecar = _sidecar(photo, spec, directory)
                thread = threading.Thread(target=_run,args=(directory,photo.path,sidecar),daemon=True)
                _JOBS[key] = thread
                thread.start()
            started = key in _JOBS
        return 200, {"status": "running" if started else "idle", "notice": "Local computation. No model-service request."}, JSON_TYPE
    except run_steps.StepError as exc:
        return exc.code, {"error": str(exc)}, JSON_TYPE
    except (ValueError, OSError, sqlite3.Error) as exc:
        return 400, {"error": str(exc)}, JSON_TYPE
