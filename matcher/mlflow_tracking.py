"""Export saved experiment results. Keep MLflow optional and local results intact."""

import argparse
from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.parse import urlsplit, urlunsplit
import uuid


REDACTED = "<redacted>"
SECRET = re.compile(r"password|passwd|secret|authorization|api.?key|access.?key|cookie|credential"
                    r"|(?:^|[_-])token(?:$|[_-])", re.I)
OMIT = {"trace", "group", "raw", "body", "image_url", "image_base64", "image_b64",
        "mask_png_b64", "messages", "headers"}
FORMATS = {
    "workbench": ("run.json", "metrics.json"),
    "matcher": ("provenance.json", "summary.json"),
    "arcface": ("training-snapshot.json", "report.json"),
}


def sanitize(value):
    """Remove secret fields, transport payloads, and URL credentials recursively."""
    if isinstance(value, dict):
        return {str(k): (REDACTED if SECRET.search(re.sub(r"([a-z])([A-Z])", r"\1_\2", str(k))) else
                        bool(v) if str(k) == "error" else sanitize(v))
                for k, v in value.items() if str(k).lower() not in OMIT
                and not re.search(r"base64|_b64$", str(k), re.I)}
    if isinstance(value, (list, tuple)):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        if value.startswith("data:"):
            return REDACTED
        value = re.sub(r"(?i)\b(Bearer|Basic)\s+[^\s,;]+", r"\1 <redacted>", value)
        def clean_url(match):
            parts = urlsplit(match.group())
            return urlunsplit((parts.scheme, parts.netloc.rsplit("@", 1)[-1],
                               parts.path, "", ""))
        return re.sub(r"https?://[^\s\"<>]+", clean_url, value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                       allow_nan=False) + "\n").encode()


def digest(body):
    return hashlib.sha256(body).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path, value):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(encoded(value))
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def flat(value, prefix=""):
    """Flatten dictionaries. Encode changed keys to prevent metric-name collisions."""
    if isinstance(value, dict):
        for key, item in sorted(value.items()):
            clean = re.sub(r"[^A-Za-z0-9_-]", "_", str(key))
            if clean != str(key):
                clean += "_" + digest(str(key).encode())[:8]
            yield from flat(item, (prefix + "." if prefix else "") + clean)
    else:
        key = prefix if len(prefix) <= 250 else prefix[:233] + "_" + digest(prefix.encode())[:16]
        yield key, value


def snapshot(directory, kind):
    """Read a fixed artifact allowlist. Never follow artifact symlinks."""
    if kind == "auto":
        kinds = [k for k, names in FORMATS.items() if all((directory / n).is_file() for n in names)]
        if len(kinds) != 1:
            raise ValueError("select a supported, complete experiment directory")
        kind = kinds[0]
    meta_name, metrics_name = FORMATS[kind]
    names = [meta_name, metrics_name]
    if kind == "workbench":
        names += [n for n in ("queries.jsonl", "predictions.jsonl", "results.jsonl")
                  if (directory / n).is_file()]
    elif kind == "matcher":
        summary = read_json(directory / metrics_name)
        for cell in sorted(summary["runs"]):
            if Path(cell).name != cell or cell in (".", ".."):
                raise ValueError("invalid evaluation cell name")
            names += [cell + "/" + n for n in ("config.yaml", "predictions.jsonl", "results.jsonl")
                      if (directory / cell / n).is_file()]
    elif (directory / "config.yaml").is_file():
        names.append("config.yaml")
    artifacts = {}
    for name in names:
        path = directory / name
        if path.is_symlink() or directory not in path.resolve().parents:
            raise ValueError("artifact symlinks are not supported")
        if path.suffix == ".yaml":
            import yaml
            artifacts[name + ".json"] = encoded(sanitize(yaml.safe_load(path.read_text())))
        elif path.suffix == ".jsonl":
            artifacts[name] = b"".join(json.dumps(sanitize(json.loads(line)), sort_keys=True,
                                                   ensure_ascii=False, allow_nan=False).encode() + b"\n"
                                       for line in path.read_text().splitlines() if line.strip())
        else:
            artifacts[name] = encoded(sanitize(read_json(path)))
    meta = json.loads(artifacts[meta_name])
    metrics = json.loads(artifacts[metrics_name])
    manifest = {name: {"sha256": digest(body), "bytes": len(body)}
                for name, body in sorted(artifacts.items())}
    payload_hash = digest(encoded(manifest))
    artifacts["manifest.json"] = encoded({"format": 1, "kind": kind, "files": manifest})
    params = {"kind": kind}
    for name in ("options", "backend", "configuration", "use_cache", "use_barcode", "embeddings"):
        if name in meta:
            params[name] = meta[name]
    if kind == "arcface":
        params["settings"] = metrics.get("settings", {})
    if kind == "matcher":
        params["cells"] = {name.split("/")[0]: json.loads(body)
                           for name, body in artifacts.items() if name.endswith("/config.yaml.json")}
    for name in ("archive_sha256", "expected_sha256", "features_sha256"):
        if name in meta:
            params[name] = meta[name]
    if "queries.jsonl" in artifacts:
        params["queries_sha256"] = digest(artifacts["queries.jsonl"])
    return kind, meta, metrics, params, artifacts, payload_hash


def timestamp(value, fallback):
    try:
        return int(datetime.fromisoformat(value).timestamp() * 1000)
    except (ValueError, TypeError):
        return fallback


def run_status(kind, meta, metrics):
    if kind == "workbench":
        if meta.get("answered", 0) < meta.get("query_set", {}).get("total", 0):
            return "KILLED"
        return "FINISHED"
    if kind == "matcher" and any(row.get("errors", 0) for row in metrics["runs"].values()):
        return "FAILED"
    return "FINISHED"


@contextmanager
def locked(path):
    with path.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def make_client(uri):
    # Do not load the SDK for normal matcher inference or disabled tracking.
    os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "5")
    os.environ.setdefault("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
    from mlflow import MlflowClient
    return MlflowClient(tracking_uri=uri)


def send(client, state, save, experiment, kind, meta, metrics, params, artifacts):
    from mlflow.entities import Metric, Param, RunTag

    found = client.get_experiment_by_name(experiment)
    if found is None:
        try:
            experiment_id = client.create_experiment(experiment)
        except Exception:
            # Another worker can create the experiment after the read.
            found = client.get_experiment_by_name(experiment)
            if found is None:
                raise
            experiment_id = found.experiment_id
    else:
        if found.lifecycle_stage != "active":
            raise ValueError("the MLflow experiment is deleted")
        experiment_id = found.experiment_id
    if not state.get("run_id"):
        # Recover a successful create_run whose response was lost.
        matches = client.search_runs([experiment_id],
                                     "tags.`svoe_vino.source_id` = '%s'" % state["source_id"],
                                     max_results=2)
        if len(matches) > 1:
            raise ValueError("more than one MLflow run has this source ID")
        run = matches[0] if matches else client.create_run(
            experiment_id, start_time=state["started_ms"],
            tags={"svoe_vino.source_id": state["source_id"],
                  "mlflow.runName": str(meta.get("run_id") or state["name"]),
                  "svoe_vino.component": kind})
        state["run_id"] = run.info.run_id
        state["experiment_id"] = experiment_id
        save()
    run_id = state["run_id"]
    run = client.get_run(run_id)
    if urlsplit(run.info.artifact_uri).scheme not in ("", "file", "mlflow-artifacts"):
        raise ValueError("use local artifacts or an MLflow artifact proxy")
    tags = [RunTag("svoe_vino.payload_sha256", state["payload_sha256"])]
    revision = meta.get("git_commit") or meta.get("commit")
    if revision:
        tags.append(RunTag("mlflow.source.git.commit", str(revision)))
    parameters = [Param(k, (json.dumps(v, sort_keys=True) if not isinstance(v, str) else v)[:1000])
                  for k, v in flat(params) if v is not None]
    numeric = [Metric(k, float(v), state["finished_ms"], 0)
               for k, v in flat(metrics) if type(v) in (int, float) and math.isfinite(v)]
    # Batch below MLflow's per-request limits. Use stable timestamps for retries.
    for offset in range(0, max(len(parameters), len(numeric), 1), 100):
        client.log_batch(run_id, params=parameters[offset:offset + 100],
                         metrics=numeric[offset:offset + 100], tags=tags if offset == 0 else [],
                         synchronous=True)
    if kind == "arcface":
        for row in metrics.get("history", []):
            client.log_batch(run_id, metrics=[
                Metric("history." + k, float(v), state["finished_ms"], int(row["epoch"]))
                for k, v in flat(row) if k != "epoch" and type(v) in (int, float)
                and math.isfinite(v)], synchronous=True)
    with tempfile.TemporaryDirectory(prefix="mlflow-export-") as temporary:
        for name, body in artifacts.items():
            checksum = digest(body)
            if state.setdefault("artifacts", {}).get(name) == checksum:
                continue
            path = Path(temporary) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            parent = str(Path(name).parent)
            client.log_artifact(run_id, str(path), None if parent == "." else parent)
            state["artifacts"][name] = checksum
            save()
    client.set_terminated(run_id, status=run_status(kind, meta, metrics), end_time=state["finished_ms"])


def export_run(directory, kind="auto", *, enabled=None, log=None):
    """Return export status. A tracking failure MUST NOT fail the experiment."""
    if enabled is None:
        enabled = os.environ.get("MLFLOW_TRACKING_ENABLED", "").lower() in ("1", "true", "yes")
    if not enabled:
        return {"status": "disabled"}
    log = log or (lambda message: print(message, file=sys.stderr))
    state = None
    save = None
    try:
        directory = Path(directory).resolve(strict=True)
        folder = directory / ".mlflow"
        folder.mkdir(exist_ok=True)
        with locked(folder / "export.lock"):
            path = folder / "state.json"
            states = read_json(path) if path.exists() else {"format": 1, "destinations": {}}
            uri = os.environ.get("MLFLOW_TRACKING_URI", "").strip()
            experiment = os.environ.get("MLFLOW_EXPERIMENT_NAME", "svoe-vino-lab").strip()
            destination = digest(encoded([uri, experiment]))
            state = states["destinations"].setdefault(destination, {
                "source_id": uuid.uuid4().hex, "name": directory.name,
                "started_ms": int(time.time() * 1000), "status": "pending"})
            def save():
                atomic_json(path, states)
            save()
            try:
                if not uri or not experiment:
                    raise ValueError("MLFLOW_TRACKING_URI and experiment name are required")
                kind, meta, metrics, params, artifacts, payload_hash = snapshot(directory, kind)
                if state.get("payload_sha256") not in (None, payload_hash):
                    raise ValueError("saved results changed; export a new run directory")
                if state["status"] == "synced":
                    return dict(state)
                state.update(payload_sha256=payload_hash, status="pending")
                state["started_ms"] = timestamp(meta.get("started") or meta.get("started_at"), state["started_ms"])
                state.setdefault("finished_ms", timestamp(meta.get("finished"), int(time.time() * 1000)))
                save()
                send(make_client(uri), state, save, experiment, kind, meta, metrics, params, artifacts)
                state.update(status="synced")
                state.pop("error", None)
                save()
            except Exception as exc:
                # SDK errors can contain credential-bearing URLs. Store the type alone.
                state.update(status="pending", error=type(exc).__name__)
                save()
                raise
    except Exception as exc:
        result = dict(state or {}, status="pending", error=type(exc).__name__)
        log("MLflow export pending (%s). Retry with matcher.mlflow_tracking." % type(exc).__name__)
        return result
    log("MLflow export synced: " + state["run_id"])
    return dict(state)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="one saved experiment directory")
    parser.add_argument("--kind", choices=("auto", *FORMATS), default="auto")
    args = parser.parse_args(argv)
    result = export_run(args.directory, args.kind, enabled=True)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "synced" else 1


if __name__ == "__main__":
    sys.exit(main())
