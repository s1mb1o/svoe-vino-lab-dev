"""Inspect or dispatch ONE authorized internal profile through the existing lab API.

Default: read-only inspection. --profile adds a current input fingerprint.
--execute --profile NAME --gate FILE saves intent, then makes at most one POST.
--reconcile --profile NAME records observed progress or validates completion.
An existing attempt always suppresses another POST. This helper never retries a
launch, stops a service, or loops over profiles. The parent owns retry decisions.

The parent MUST finish comparisons, reconcile processes, check live memory and
services, read the GPU rules, and register the workload before recording a gate.
Gate JSON schema:
  recorded_at: ISO-8601 time with timezone, no more than 600 seconds old
  queue: absolute queue path; profile: selected name; set: my
  identity_sha256: the current fingerprint printed by --profile
  comparisons_complete, no_active_measurements, index_ready, query_files_verified,
  memory_preflight_passed, services_ready, workload_registered, gpu_rules_read: true
  memory: {available_gib: number, additional_required_gib: number, margin_gib: 20}
  evidence: nonempty list of existing absolute parent evidence file paths
For a local model, local_weights_ready MUST also be true. The memory budget MUST
cover additional_required_gib plus margin_gib. No availability probe loads a model.

Execution uses the fixed local API and project configuration. The gate binds all
current input identities. Inspection reads indexes and metadata but no image pixels.
Source-byte validation is the parent's query_files_verified attestation. The helper
holds the shared measurement lock during dispatch or reconciliation. A live or
uncertain queue attempt blocks later dispatches. Keep other launchers idle. The API
has no atomic global queue lock or idempotency key. The parent MUST not edit the
queue concurrently. A lost response is reconciled, never retried automatically.
"""
import argparse
import contextlib
import datetime
import fcntl
import hashlib
import http.client
import ipaddress
import json
import math
import os
import shlex
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import barcode
import benchmark
import derive
import embedding_run
import embeddings
import pipelines
import run_jobs
import vlm_config
from benchmark_barcode_crops import measurement_lock
from benchmark_bulk_cache import catalogue_identity, index_identity, query_identity

DEFAULT_QUEUE = ROOT / "docs/reports/2026-09-27_all-profile-rerun/queue.json"
DEFAULT_BASELINE = ROOT / "runs/2026-09-26T213857Z-lab-barcode-rerank-siglip2-512-crop-my"
DEFAULT_STAGE1 = ROOT / "docs/reports/2026-09-27_barcode-variants/stage1"
TERMINAL = {"done", "failed", "stopped", "invalid_completion", "rejected"}
FORBIDDEN = "vino-svoe-search-by-photo"
FLAGS = ("comparisons_complete", "no_active_measurements", "index_ready",
         "query_files_verified", "memory_preflight_passed", "services_ready",
         "workload_registered", "gpu_rules_read")


def read_json(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(value):
    return embeddings.sha256_json(value)


def atomic_json(path, value):
    """Persist intent before dispatch, including the replacement directory entry."""
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def profile_row(queue, name):
    matches = [row for row in queue["profiles"] if row["name"] == name]
    if len(matches) != 1:
        raise ValueError("queue MUST contain the selected profile exactly once")
    row = matches[0]
    if name == FORBIDDEN or row.get("authorized_to_start") is not True or row.get("backend") != "embedding":
        raise ValueError("profile is outside the authorized internal/local queue")
    return row


def internal_url(url):
    """Allow literal loopback or RFC1918 addresses. Do not resolve a DNS name."""
    parts = urlsplit(url or "")
    try:
        address = ipaddress.ip_address(parts.hostname or "")
        port = parts.port
    except ValueError as exc:
        raise ValueError("backend URL MUST use a literal internal IP address") from exc
    networks = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
    private = address.is_loopback or any(address in ipaddress.ip_network(n) for n in networks)
    if (parts.scheme not in ("http", "https") or not private or parts.username
            or parts.password or parts.query or parts.fragment or port == 0):
        raise ValueError("backend URL is not an authorized internal HTTP endpoint")
    return url.rstrip("/")


def snapshot(queue, name, config, baseline):
    """Read metadata and hash inputs. Do not construct any inference backend."""
    row = profile_row(queue, name)
    config = Path(config).resolve()
    if digest(config) != queue["config_sha256_at_queue_time"]:
        raise ValueError("configuration differs from the authorized queue snapshot")
    settings = embeddings.load_settings(str(config))
    pipeline = pipelines.load(str(config)).find(name)
    if pipeline.backend != "embedding" or pipeline.embedding != row.get("embedding"):
        raise ValueError("current profile differs from queue backend or embedding")
    entry = settings.find(pipeline.embedding)
    workers = 1 if entry.backend == "local" else 4
    if (entry.backend not in ("local", "openai") or row.get("model_backend") != entry.backend
            or row.get("workers") != workers or row.get("use_cache") is not True
            or row.get("use_barcode") is not True):
        raise ValueError("queue MUST retain cache/barcode and remote-4/local-1 worker policy")
    if not embedding_run.index_ready(settings.db_path, entry.name):
        raise ValueError("selected embedding index is not ready")
    build_lock = Path(embeddings.entry_dir(settings.db_path, entry.name)) / embeddings.LOCK
    if build_lock.exists() and pid_state(read_json(build_lock).get("pid"))["state"] != "absent":
        raise ValueError("selected embedding index has a live or uncertain build")
    python = run_jobs.interpreter(pipelines.load(str(config)), pipeline)
    endpoints = {}
    if entry.backend == "openai":
        endpoints["embedding"] = internal_url(entry.base_url)
    views = pipeline.views if pipeline.views is not None else entry.views
    if pipeline.rerank or any(s["step"] == "segment" for steps in views.values() for s in steps):
        configured = derive.configured_endpoint(derive.SAM3_ENDPOINT, str(config)).rstrip("/")
        environment = os.environ.get("SAM3_ENDPOINT", "").rstrip("/")
        if not environment or configured != environment or configured != derive.SAM3_ENDPOINT.rstrip("/"):
            raise ValueError("SAM3_ENDPOINT MUST equal the actual production client default")
        endpoints["sam3"] = internal_url(configured)
    rule_files = {}
    if pipeline.rerank:
        _, raw, _ = embeddings.read_config(str(config))
        endpoints["rerank"] = internal_url(vlm_config.entry(raw, pipeline.rerank["vlm"]).endpoint)
        rules = Path(embeddings.entry_dir(settings.db_path, pipeline.rerank["rules"]))
        rule_files = {str((rules / n).resolve()): digest(rules / n)
                      for n in ("clusters.json", "cluster-rules.json")}
    with contextlib.closing(embeddings.open_database(settings.db_path)) as conn:
        current, _ = benchmark.build_queries(conn, settings.db_path, queue["set"])
    queries = query_identity(current)
    baseline_queries = [json.loads(line) for line in (Path(baseline) / "queries.jsonl").read_text().splitlines()]
    if (queries != query_identity(baseline_queries) or len(queries) != queue["query_count_at_queue_time"]
            or len({r["query_id"] for r in queries}) != len(queries)):
        raise ValueError("current photos or labels differ from the complete baseline query set")
    identity = {"profile": name, "set": queue["set"], "config": str(config),
        "config_sha256": digest(config), "database": str(Path(settings.db_path).resolve()),
        "model_backend": entry.backend, "model": entry.model, "embedding": entry.name,
        "workers": workers, "has_barcode": pipeline.barcode is not None, "python": python,
        "endpoints": endpoints, "queries": queries,
        "baseline_queries_sha256": digest(Path(baseline) / "queries.jsonl"),
        "catalogue": catalogue_identity(settings.db_path, queue["set"]),
        "index": index_identity(embeddings.entry_dir(settings.db_path, entry.name)),
        "rule_files": rule_files,
        "lookup": [[kind, code, slugs] for (kind, code), slugs in
                   sorted(barcode.CodeLookup.load(settings.db_path).values.items())],
        "sources": {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / "pipeline").glob("*.py"))}}
    return identity


def check_gate(path, queue_path, identity, now=None):
    gate = read_json(path)
    current = now or datetime.datetime.now(datetime.timezone.utc)
    recorded = datetime.datetime.fromisoformat(gate["recorded_at"])
    if recorded.tzinfo is None or not -5 <= (current - recorded).total_seconds() <= 600:
        raise ValueError("parent gate is stale, future-dated, or lacks a timezone")
    expected = {"queue": str(Path(queue_path).resolve()), "profile": identity["profile"],
                "set": identity["set"], "identity_sha256": fingerprint(identity)}
    if any(gate.get(k) != v for k, v in expected.items()) or any(gate.get(k) is not True for k in FLAGS):
        raise ValueError("parent gate does not confirm this exact profile and all launch prerequisites")
    if identity["model_backend"] == "local" and gate.get("local_weights_ready") is not True:
        raise ValueError("local profile needs verified cached weights")
    memory = gate.get("memory", {})
    values = [memory.get(k) for k in ("available_gib", "additional_required_gib", "margin_gib")]
    if (any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values)
            or values[2] < 20 or values[0] < values[1] + values[2]):
        raise ValueError("parent gate does not retain the required memory margin")
    evidence = gate.get("evidence")
    if (not isinstance(evidence, list) or not evidence
            or any(not isinstance(p, str) or not Path(p).is_absolute() or not Path(p).is_file() for p in evidence)):
        raise ValueError("gate MUST reference existing absolute evidence files")
    return gate


def api(method, path, body=None):
    """One fixed loopback request. No redirects and no automatic retry."""
    connection = http.client.HTTPConnection("127.0.0.1", 8168, timeout=30)
    try:
        connection.request(method, path, None if body is None else json.dumps(body),
                           {"Content-Type": "application/json"})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def pid_state(pid):
    """Return absent, live, or unknown. Confirmed zombies are terminated.

    The lab server can retain an unreaped child. Its PID still exists, but the
    child cannot execute. Completion still requires matching saved artifacts.
    An unavailable or malformed ps result fails closed.
    """
    if type(pid) is not int or pid <= 0:
        return {"state": "unknown", "command": None}
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return {"state": "absent", "command": None}
    except PermissionError:
        return {"state": "unknown", "command": None}
    try:
        result = subprocess.run(["ps", "-o", "stat=,command=", "-p", str(pid)],
                                text=True, capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return {"state": "unknown", "command": None}
    if result.returncode or not result.stdout.strip():
        return {"state": "unknown", "command": None}
    lines = result.stdout.strip().splitlines()
    if len(lines) != 1:
        return {"state": "unknown", "command": None}
    fields = lines[0].split(None, 1)
    if len(fields) != 2:
        return {"state": "unknown", "command": None}
    status, command = fields
    if status == "Z":
        return {"state": "absent", "command": command, "process_status": status,
                "termination_evidence": "zombie; process exited but parent has not reaped it"}
    if status.startswith("Z"):
        return {"state": "unknown", "command": command, "process_status": status}
    return {"state": "live", "command": command, "process_status": status}


def matching_command(command, attempt):
    try:
        tokens = shlex.split(command or "")
        arguments = dict(zip(tokens[2::2], tokens[3::2]))
        return (len(tokens) >= 2 and Path(tokens[1]).resolve() == (ROOT / "pipeline/run_job.py").resolve()
                and arguments.get("--name") == attempt["request"]["configuration"]
                and arguments.get("--set") == attempt["request"]["set"]
                and arguments.get("--config") == attempt["identity"]["config"]
                and arguments.get("--jobs-dir") == attempt["jobs_dir"]
                and arguments.get("--workers") == str(attempt["request"]["workers"])
                and "--no-cache" not in tokens and "--no-barcode" not in tokens
                and "--limit" not in tokens)
    except (ValueError, TypeError):
        return False


def no_active_jobs(queue, jobs_dir):
    for row in queue["profiles"]:
        for attempt in row.get("attempts", []):
            if attempt.get("state") not in TERMINAL:
                raise ValueError("reconcile the existing queue attempt before a new launch")
    for lock in Path(jobs_dir).glob("*/job.lock"):
        if pid_state(read_json(lock).get("pid"))["state"] != "absent":
            raise ValueError("a run-job lock still has a live or uncertain process")
    status, response = api("GET", "/api/run-jobs")
    jobs = response.get("jobs") if isinstance(response, dict) else None
    if status != 200 or not isinstance(jobs, list) or any(not isinstance(job, dict) for job in jobs):
        raise ValueError("cannot verify live API jobs")
    if any(job.get("state") in run_jobs.ACTIVE or job.get("pid") for job in jobs):
        raise ValueError("the API still reports an active job")


def persist(queue_path, queue, row, attempt):
    row["status"], row["run_id"] = attempt["state"], attempt.get("run_id")
    row["pid"] = attempt.get("pid")
    atomic_json(queue_path, queue)
    atomic_json(Path(attempt["archive"]) / "attempt.json", attempt)


def dispatch(queue_path, queue, identity, gate_path, jobs_dir, refresh_identity):
    """Save intent first. Any subsequent exception preserves an uncertain attempt."""
    row = profile_row(queue, identity["profile"])
    if row.get("attempts") or row.get("status") not in ("pending", "waiting_for_index"):
        raise ValueError("selected profile already has an attempt; reconcile it, never repeat POST")
    no_active_jobs(queue, jobs_dir)
    gate = check_gate(gate_path, queue_path, identity)
    directory = Path(jobs_dir) / row["name"]
    archive = Path(queue_path).parent / "attempts" / (row["name"] + "-" + uuid.uuid4().hex)
    archive.mkdir(parents=True, exist_ok=False)
    log = directory / run_jobs.LOG
    if log.exists():
        (archive / "previous-job.log").write_bytes(log.read_bytes())
    request = {"configuration": row["name"], "set": identity["set"], "workers": identity["workers"],
               "use_cache": True, "use_barcode": True}
    attempt = {"id": archive.name, "state": "launch_intent", "intent_t": time.time(),
               "request": request, "identity": identity, "identity_sha256": fingerprint(identity),
               "gate": gate, "pid": None, "run_id": None, "archive": str(archive.resolve()),
               "log": str(log.resolve()), "jobs_dir": str(Path(jobs_dir).resolve()),
               "previous_log_sha256": digest(log) if log.exists() else None}
    row.setdefault("attempts", []).append(attempt)
    persist(queue_path, queue, row, attempt)  # This durable boundary precedes the POST.
    try:
        if fingerprint(refresh_identity()) != attempt["identity_sha256"]:
            raise ValueError("inputs changed after launch preflight; no POST was sent")
        check_gate(gate_path, queue_path, identity)
        status, response = api("POST", "/api/run-jobs", request)
        attempt.update(http_status=status, response=response)
        pid = response.get("pid") if isinstance(response, dict) else None
        if status == 202 and type(pid) is int and pid > 0:
            attempt.update(state="starting", pid=pid)
        else:
            attempt["state"] = "launch_uncertain"
    except Exception as exc:
        attempt.update(state="launch_uncertain", error="%s: %s" % (type(exc).__name__, exc))
    persist(queue_path, queue, row, attempt)
    return attempt


def complete_artifacts(attempt, final, runs_dir):
    run_id = final.get("run_id")
    if not isinstance(run_id, str) or Path(run_id).name != run_id or run_id in ("", ".", ".."):
        raise ValueError("final event has no safe run_id")
    directory = Path(runs_dir) / run_id
    meta, metrics = read_json(directory / "run.json"), read_json(directory / "metrics.json")
    queries = [json.loads(x) for x in (directory / "queries.jsonl").read_text().splitlines()]
    results = [json.loads(x) for x in (directory / "results.jsonl").read_text().splitlines()]
    predictions = [json.loads(x) for x in (directory / "predictions.jsonl").read_text().splitlines()]
    expected = attempt["identity"]["queries"]
    options = meta.get("options", {})
    if (meta.get("run_id") != run_id or metrics.get("run_id") != run_id
            or meta.get("configuration") != attempt["request"]["configuration"]
            or options.get("set") != attempt["request"]["set"]
            or options.get("workers") != attempt["request"]["workers"] or options.get("limit") is not None
            or options.get("database") != attempt["identity"]["database"]
            or meta.get("use_cache") is not True
            or (attempt["identity"]["has_barcode"] and meta.get("use_barcode") is not True)
            or not meta.get("finished") or meta.get("answered") != len(expected)
            or final.get("answered") != len(expected) or final.get("errors") != 0
            or query_identity(queries) != expected or query_identity(results) != expected
            or any(r.get("error") for r in results)):
        raise ValueError("terminal artifacts do not prove complete, error-free paired coverage")
    degraded = sum(any(s.get("error") or (s.get("out") or {}).get("error")
                       for s in (r.get("trace") or {}).get("steps", [])) for r in results)
    attempt["degraded_queries"] = degraded
    if degraded:
        raise ValueError("%d queries contain degraded trace steps" % degraded)
    prediction_keys = ("query_id", "image_path", "image_sha256", "predicted_slug", "latency_ms")
    if predictions != [{k: r[k] for k in prediction_keys} for r in results]:
        raise ValueError("saved predictions differ from the complete results")
    files = {name: digest(directory / name) for name in
             ("run.json", "metrics.json", "queries.jsonl", "results.jsonl", "predictions.jsonl")}
    return {"run_id": run_id, "run_dir": str(directory.resolve()), "run": meta,
            "metrics": metrics, "degraded_queries": degraded, "artifact_sha256": files}


def reconcile(attempt, runs_dir, current_identity=None):
    """Observe one attempt. No API request or inference occurs here."""
    if attempt.get("state") in TERMINAL:
        return attempt  # Preserve the archived outcome if a later UI run replaces the live log.
    events = run_jobs.read_events(attempt["jobs_dir"] + "/" + attempt["request"]["configuration"])
    fresh = [e for e in events if isinstance(e.get("t"), (int, float)) and e["t"] >= attempt["intent_t"]]
    starts = [e for e in fresh if e["event"] == "start"]
    if len(starts) > 1:
        attempt.update(state="launch_uncertain", error="multiple start events after intent")
        return attempt
    start = starts[0] if starts else None
    lock = run_jobs.read_lock(Path(attempt["jobs_dir"]) / attempt["request"]["configuration"])
    if attempt.get("pid") is None and start:
        attempt["pid"] = start.get("pid")
    if attempt.get("pid") is None and lock:
        try:
            fresh_lock = datetime.datetime.fromisoformat(lock["started_at"]).timestamp() >= math.floor(attempt["intent_t"])
        except (KeyError, ValueError, TypeError):
            fresh_lock = False
        candidate = pid_state(lock.get("pid"))
        if fresh_lock and candidate["state"] == "live" and matching_command(candidate["command"], attempt):
            attempt["pid"] = lock["pid"]
    process = pid_state(attempt.get("pid"))
    attempt["process"] = process
    attempt["observed_t"] = time.time()
    expected = dict(attempt["request"], pid=attempt["pid"], limit=None,
                    todo=len(attempt["identity"]["queries"]))
    if not attempt["identity"]["has_barcode"]:
        expected["use_barcode"] = None
    if start and any(start.get(k) != v for k, v in expected.items()):
        attempt.update(state="launch_uncertain", error="start event differs from launch intent")
        return attempt
    if start:
        named = [e.get("run_id") for e in fresh if e["event"] == "run_dir" and e["t"] >= start["t"]]
        if len(named) == 1:
            attempt["run_id"] = named[0]
        progress = [e for e in fresh if e["event"] == "progress" and e["t"] >= start["t"]]
        if progress:
            attempt["progress"] = progress[-1]
    if process["state"] != "absent":
        attempt["state"] = ("running" if process["state"] == "live" and matching_command(process["command"], attempt)
                            else "launch_uncertain")
        return attempt
    attempt["runner_exit_verified"] = True
    if not start:
        attempt.update(state="launch_uncertain", error="no matching start event; inspect startup failure manually")
        return attempt
    finals = [e for e in fresh if e["event"] in run_jobs.FINAL and e["t"] >= start["t"]]
    if len(finals) != 1:
        attempt.update(state="launch_uncertain", error="runner has no unambiguous final event")
        return attempt
    final = finals[0]
    if final["event"] == "done" and (len(named) != 1 or named[0] != final.get("run_id")):
        attempt.update(state="launch_uncertain", error="run directory and final event disagree")
        return attempt
    attempt.update(final_event=final, run_id=final.get("run_id"))
    log = Path(attempt["log"])
    (Path(attempt["archive"]) / "job.log").write_bytes(log.read_bytes())
    attempt["log_sha256"] = digest(log)
    if final["event"] != "done":
        attempt["state"] = final["event"]
        return attempt
    try:
        attempt.update(complete_artifacts(attempt, final, runs_dir))
        if current_identity is None or fingerprint(current_identity) != attempt["identity_sha256"]:
            raise ValueError("inputs changed since launch or cannot be verified")
    except (OSError, ValueError, KeyError) as exc:
        attempt.update(state="invalid_completion", error=str(exc))
    else:
        attempt["state"] = "done"
    return attempt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--profile")
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--baseline-run", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--stage1", type=Path, default=DEFAULT_STAGE1)
    parser.add_argument("--gate", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--reconcile", action="store_true")
    args = parser.parse_args(argv)
    try:
        queue = read_json(args.queue)
        if not args.execute and not args.reconcile:
            result = {"dry_run": True, "profiles": [{k: r.get(k) for k in
                      ("name", "status", "authorized_to_start", "workers", "pid", "run_id")}
                      for r in queue["profiles"]]}
            if args.profile:
                identity = snapshot(queue, args.profile, args.config, args.baseline_run)
                result.update(profile=args.profile, identity_sha256=fingerprint(identity),
                              queries=len(identity["queries"]), endpoints=identity["endpoints"])
            print(json.dumps(result, indent=2))
            return 0
        if not args.profile or (args.execute and not args.gate):
            raise ValueError("execution needs --profile and --gate; reconciliation needs --profile")
        if args.config.resolve() != (ROOT / "config.yaml").resolve():
            raise ValueError("the fixed lab API requires the project configuration")
        with measurement_lock(args.stage1), (args.queue.parent / "queue.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            queue = read_json(args.queue)
            row = profile_row(queue, args.profile)
            if args.execute:
                identity = snapshot(queue, args.profile, args.config, args.baseline_run)
                attempt = dispatch(args.queue, queue, identity, args.gate, run_jobs.JOBS_DIR,
                                   lambda: snapshot(queue, args.profile, args.config, args.baseline_run))
            else:
                if not row.get("attempts"):
                    raise ValueError("profile has no recorded attempt to reconcile")
                attempt = row["attempts"][-1]
                try:
                    identity = snapshot(queue, args.profile, args.config, args.baseline_run)
                except (OSError, ValueError, KeyError, embeddings.ConfigError) as exc:
                    identity = None
                    attempt["identity_check_error"] = str(exc)
                reconcile(attempt, benchmark.RUNS_DIR, identity)
                persist(args.queue, queue, row, attempt)
            print(json.dumps({k: attempt.get(k) for k in ("state", "pid", "run_id", "archive", "error")}, indent=2))
            return 0 if attempt["state"] in ("starting", "running", "done") else 1
    except (OSError, ValueError, KeyError, embeddings.ConfigError, benchmark.BenchmarkError) as exc:
        print("profile queue refused: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
