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
EVIDENCE = EXPERIMENT / "internal/patch-retrieval-20261014/full-gallery"
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
            command = [worker_python, "-m", "patch_pipeline.full_inspection", "--gallery", str(EVIDENCE),
                       "--prepared", str(sidecar), "--output", str(directory),
                       "--selection", str(EVIDENCE / "selection.lock.json")]
            with (directory / "worker.log").open("wb") as log:
                process = subprocess.run(command, cwd=EXPERIMENT, env=environment,
                                         stdout=log, stderr=log, timeout=600)
            if process.returncode:
                raise RuntimeError("Local patch computation failed. Read the local worker log.")
        except Exception as exc:
            (directory / "error.json").write_text(json.dumps({"status": "failed", "error": str(exc)}))


def _viewer_row(source_sha):
    """Read a stored viewer mask without changing the frozen benchmark inputs."""
    path = EVIDENCE / "viewer-queries" / source_sha / "prepared.json"
    if not path.is_file():
        return None
    row = json.loads(path.read_text())
    if row.get("source_sha256") != source_sha:
        raise ValueError("stored viewer mask source hash differs from the query")
    return row


def _sidecar(photo, spec, directory):
    """Use approved masks or existing local cuts. Never request SAM3 inference."""
    import run_steps
    import derive
    from PIL import Image
    import embeddings
    source_sha = hashlib.sha256(Path(photo.path).read_bytes()).hexdigest()
    viewer = _viewer_row(source_sha)
    if viewer is not None:
        sidecar = directory / "prepared.json"
        sidecar.write_text(json.dumps(dict(viewer, image=photo.path)))
        return sidecar
    for item in json.loads((EVIDENCE / "queries.json").read_text())["items"]:
        if item["source_sha256"] == source_sha:
            sidecar = directory / "prepared.json"
            sidecar.write_text(json.dumps(dict(item, image=photo.path)))
            return sidecar
    sam3 = spec.get("sam3") or {}
    endpoint = sam3.get("endpoint") or derive.SAM3_ENDPOINT
    cuts = {}
    for target in ("package", "label"):
        options = {"label_mask_union": sam3.get("label_mask_union", True),
                   "label_focus": sam3.get("label_focus") == "main"}
        supported = inspect.signature(run_steps._cut).parameters
        options = {key: value for key, value in options.items() if key in supported}
        box, cut, _reason, _result = run_steps._cut(photo, target, endpoint,
                                                  spec.get("scene_selection", False), **options)
        if box is not None and cut is not None:
            cuts[target] = (list(map(int, box)), cut.convert("RGBA"))
    if "package" not in cuts:
        raise ValueError("The standard bottle cut is absent from the local cache. No model request was sent.")
    box, package = cuts["package"]
    gallery = json.loads((EVIDENCE / "gallery.json").read_text())
    steps = gallery["config"]["views"]["full"]
    pixels = embeddings.apply_steps(photo.image, steps, box, lambda: package)
    bottle = package.getchannel("A").resize(pixels.size, Image.Resampling.BOX)
    label = Image.new("L", photo.image.size, 0)
    if "label" in cuts:
        label_box, label_cut = cuts["label"]
        label.paste(label_cut.getchannel("A"), (label_box[0], label_box[1]))
    label = label.crop(box).resize(pixels.size, Image.Resampling.BOX)
    for name, image in (("input", pixels), ("bottle", bottle), ("label", label),
                        ("occlusion", Image.new("L", pixels.size, 0))):
        image.save(directory / (name+".png"))
    package.save(directory / "rotation-base.png")
    row = {"key": "viewer-"+source_sha, "image": photo.path, "source_sha256": source_sha,
           "source_size": list(photo.image.size), "package_box": box,
           "package_source": "standard cached package cut", "label_source": "cached full-label cut" if "label" in cuts else "unknown full-label region"}
    row.update({name: str(directory / (name+".png")) for name in ("input", "bottle", "label", "occlusion")})
    row["rotation_base"] = str(directory / "rotation-base.png")
    sidecar = directory / "prepared.json"
    sidecar.write_text(json.dumps(row))
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
        index = EVIDENCE / "gallery.json"
        selection = EVIDENCE / "selection.lock.json"
        if not index.is_file() or not selection.is_file():
            return 503, {"error": "The full-gallery comparison is not available."}, JSON_TYPE
        digest = hashlib.sha256(Path(photo.path).read_bytes())
        viewer = _viewer_row(digest.hexdigest())
        if viewer is not None:
            digest.update(json.dumps(viewer, sort_keys=True).encode())
            for role in ("input", "bottle", "label", "occlusion", "rotation_base"):
                digest.update(Path(viewer[role]).read_bytes())
        for item in [index, selection, EVIDENCE / "queries.json", Path(__file__), *sorted((EXPERIMENT / "patch_pipeline").glob("*.py"))]:
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
                panel = _one(query, "panel") if "panel" in query else "reference"
                if panel not in ("reference", "query", "reference_weights", "query_weights"):
                    raise ValueError("unknown patch image panel")
                image = directory / result["candidates"][number]["images"][panel]
                return 200, image.read_bytes(), "image/png"
            result["cache_key"] = key
            for number, candidate in enumerate(result["candidates"]):
                candidate["images"] = {panel: "/api/run-patches?" + urllib.parse.urlencode(
                    {"id":run,"query":identity,"candidate":number,"panel":panel}) for panel in candidate["images"]}
            return 200, result, JSON_TYPE
        if (directory / "error.json").exists():
            return 200, json.loads((directory / "error.json").read_text()), JSON_TYPE
        with _LOCK:
            if key not in _JOBS and query.get("start") == ["1"]:
                directory.mkdir(parents=True, exist_ok=True)
                sidecar = _sidecar(photo, spec, directory)
                prepared = json.loads(sidecar.read_text())
                prepared["expected"] = row.get("slug")
                sidecar.write_text(json.dumps(prepared))
                thread = threading.Thread(target=_run,args=(directory,photo.path,sidecar),daemon=True)
                _JOBS[key] = thread
                thread.start()
            started = key in _JOBS
        return 200, {"status": "running" if started else "idle", "notice": "Local computation. No model-service request."}, JSON_TYPE
    except run_steps.StepError as exc:
        return exc.code, {"error": str(exc)}, JSON_TYPE
    except (ValueError, OSError, sqlite3.Error) as exc:
        return 400, {"error": str(exc)}, JSON_TYPE
