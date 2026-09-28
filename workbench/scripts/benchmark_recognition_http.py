"""Measure sequential HTTP recognition through an isolated production lab handler.

The loopback request includes upload validation, upload storage, recognition, step
reconstruction, JSON serialization, and the complete response transfer. It excludes
browser rendering and a remote client network. The child uses the experimental CLI
wrapper. Its imports differ from the production recognize.py entry point.

Run only after stage 1 and service checks. The shared measurement lock excludes other
experiments. This script never starts the description watcher or restarts port 8168.
It binds an OS-assigned loopback port. It does not implement a hard 3-second timeout.
"""
import argparse
import contextlib
import hashlib
import http.client
import json
import os
import platform
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlencode

import benchmark_recognition_latency as cli

ROOT = cli.ROOT
REVISION = 1
SCOPE = "Loopback HTTP request through complete response; excludes browser rendering and remote client network"


class RouteAdapter:
    """Replace run_script only in this experiment process. Preserve its interface."""

    def __init__(self, mode, variant, options, output, factory=cli.Worker, clock=time.perf_counter):
        if mode not in cli.MODES or variant not in cli.VARIANTS:
            raise ValueError("invalid HTTP experiment mode or variant")
        self.mode, self.variant, self.options = mode, variant, options
        self.output, self.factory, self.clock = Path(output), factory, clock
        self.stem = mode + "-" + variant
        self.cache_boundary = cli.cache_directory(self.output / "cache" / self.stem)
        self.worker, self.active, self.telemetry = None, None, {}
        self.blocked = False

    def begin(self, row):
        if self.blocked or self.active is not None:
            raise RuntimeError("the previous request is active or failed")
        key = uuid.uuid4().hex
        upload = self.output / "uploads" / self.stem / key
        cache = cli.cache_directory(self.cache_boundary / key, self.cache_boundary)
        upload.mkdir(parents=True, exist_ok=False)
        cache.mkdir(parents=True, exist_ok=False)
        self.active = dict(row, request_key=key, upload_dir=str(upload.resolve()), cache_root=str(cache))
        self.telemetry = {}
        return self.active

    def finish(self):
        if self.active is None:
            raise RuntimeError("no active HTTP request")
        result = dict(self.telemetry)
        self.active = None
        return result

    def __call__(self, python, config_path, name, photo):
        import recognize_routes
        if (self.active is None or self.blocked or name != self.options["profile"]
                or Path(config_path).resolve() != Path(self.options["config"]).resolve()
                or Path(self.active["upload_dir"]) not in Path(photo).resolve().parents):
            raise recognize_routes.RecognizeError(503, "HTTP experiment request does not match its upload")
        started, startup = self.clock(), 0.0
        try:
            if self.worker is None:
                self.worker = self.factory(
                    dict(self.options, python=python, variant=self.variant,
                         cache_root=self.active["cache_root"], cache_boundary=str(self.cache_boundary)),
                    self.output / (self.stem + ".worker.log"), self.options["watchdog_s"])
                startup = self.worker.startup_ms
            ready = self.worker.ready
            raw, request_ms = self.worker.ask(dict(self.active, path=photo))
            if raw.get("cache_read") is not False or raw.get("cache_root") != self.active["cache_root"]:
                raise RuntimeError("child did not use this request's isolated cache with reads disabled")
            cleanup_started = self.clock()
            if self.mode == "process":
                self.worker.close()
                self.worker = None
            cleanup_ms = (self.clock() - cleanup_started) * 1000 if self.mode == "process" else 0.0
            process_ms = (self.clock() - started) * 1000
            answer = dict(raw, spec=ready["spec"], build_ms=ready["build_ms"] if startup else 0.0)
            self.telemetry.update(raw_answer=answer, process_ms=process_ms, startup_ms=startup,
                                  build_ms=answer["build_ms"],
                                  backend_initial_build_ms=ready["build_ms"],
                                  worker_import_ms=ready["worker_import_ms"],
                                  worker_python=ready.get("python", python),
                                  worker_zxing_version=ready.get("zxing_version"),
                                  worker_pillow_version=ready.get("pillow_version"),
                                  worker_request_ms=request_ms, cleanup_ms=cleanup_ms,
                                  ask_wall_ms=raw["ask_wall_ms"])
            return answer, process_ms
        except Exception as exc:
            self.blocked = True
            self.telemetry["adapter_error"] = "%s: %s" % (type(exc).__name__, exc)
            self.close(force=True)
            raise recognize_routes.RecognizeError(503, self.telemetry["adapter_error"]) from exc

    def close(self, force=False):
        worker = self.worker
        if worker is not None:
            worker.close(force=force)
            if self.worker is worker:
                self.worker = None


@contextlib.contextmanager
def isolated_server(adapter, server_factory=None, clock=time.perf_counter):
    """Use the production handler. Patch functions only in this benchmark process."""
    started = clock()
    import lab_server
    import model_cache
    import recognize_routes
    server_factory = server_factory or lab_server.make_server
    old = (recognize_routes.run_script, recognize_routes.store_upload,
           recognize_routes.steps_answer, model_cache.ROOT, model_cache.READ)
    server, thread, thread_started = None, None, False

    def store_upload(*args, **kwargs):
        start = clock()
        try:
            return old[1](*args, **kwargs)
        finally:
            adapter.telemetry["upload_ms"] = (clock() - start) * 1000

    def steps_answer(*args, **kwargs):
        if adapter.active is None:
            raise RuntimeError("step reconstruction has no active request")
        start = clock()
        previous = model_cache.ROOT, model_cache.READ
        model_cache.ROOT, model_cache.READ = adapter.active["cache_root"], True
        try:
            # run_steps._cut uses CachedSam3. A missing cache raises; it sends no request.
            return old[2](*args, **kwargs)
        finally:
            model_cache.ROOT, model_cache.READ = previous
            adapter.telemetry["steps_answer_ms"] = (clock() - start) * 1000

    failed = True
    try:
        model_cache.ROOT, model_cache.READ = str(adapter.cache_boundary), False
        recognize_routes.run_script = adapter
        recognize_routes.store_upload, recognize_routes.steps_answer = store_upload, steps_answer
        server = server_factory(adapter.options["database"], host="127.0.0.1", port=0,
                                config_path=adapter.options["config"])
        # Wait for request threads on shutdown. This changes shutdown only.
        server.daemon_threads = False
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05},
                                  name="recognition-benchmark-http", daemon=True)
        thread.start()
        thread_started = True
        setup_ms = (clock() - started) * 1000
        yield server, setup_ms
        failed = False
    finally:
        try:
            if server is not None and thread_started:
                server.shutdown()
                thread.join()
        finally:
            try:
                adapter.close(force=failed)
            finally:
                try:
                    if server is not None:
                        server.server_close()  # Join request threads before restoring global functions.
                finally:
                    try:
                        # A handler can finish constructing a worker after the first
                        # abort observed self.worker=None. The join makes it visible.
                        adapter.close(force=failed)
                    finally:
                        (recognize_routes.run_script, recognize_routes.store_upload,
                         recognize_routes.steps_answer, model_cache.ROOT, model_cache.READ) = old


def post_image(address, query, data, timeout, connection_factory=http.client.HTTPConnection,
               clock=time.perf_counter):
    """End HTTP wall timing after the complete body. Time JSON parsing separately."""
    connection = connection_factory(address[0], address[1], timeout=timeout)
    started = clock()
    try:
        connection.request("POST", "/api/recognize?" + urlencode(query), body=data,
                           headers={"Content-Type": "application/octet-stream"})
        response = connection.getresponse()
        body = response.read()
        wall_ms = (clock() - started) * 1000
        parse_started = clock()
        try:
            value = json.loads(body)
        except (ValueError, UnicodeError):
            value = {"error": "HTTP response is not JSON"}
        return {"http_status": response.status, "body": value, "response_bytes": len(body),
                "client_wall_ms": wall_ms, "json_parse_ms": (clock() - parse_started) * 1000}
    finally:
        connection.close()


def response_problems(response, raw, row):
    """Check the ordinary route shape without changing or trimming the response."""
    body = response["body"]
    if not isinstance(body, dict):
        return ["response is not an object"]
    if response["http_status"] != 200 or body.get("error"):
        return [str(body.get("error") or "HTTP %s" % response["http_status"])]
    problems = []
    if body.get("sha256") != row["image_sha256"]:
        problems.append("response photo digest differs")
    if [c.get("slug") for c in body.get("answer", [])] != [
            c.get("slug") for c in raw.get("candidates", [])]:
        problems.append("HTTP candidates differ from the backend answer")
    if (body.get("row") or {}).get("error") != raw.get("error"):
        problems.append("HTTP error differs from the backend answer")
    for group in body.get("rounds") or []:
        for step in group.get("steps") or []:
            if any(a.get("check") == "changed" for a in step.get("artifacts") or []):
                problems.append("reconstructed model input differs")
            if any("cut cannot be made again" in str(note).lower() for note in step.get("notes") or []):
                problems.append("fresh-response cache cannot reconstruct a cut")
    return problems


def http_summary(records):
    from benchmark_barcode_variants import distribution
    out = cli.summary(records)
    out.update(scope=SCOPE, http_statuses={str(status): sum(r["http_status"] == status for r in records)
                                        for status in sorted({r["http_status"] for r in records}, key=str)},
               transport_failures=sum(r.get("transport_error") is not None for r in records),
               censored_wall_rows=sum(r.get("latency_censored", False) for r in records),
               completed_http_wall_ms=distribution([r["client_wall_ms"] for r in records
                                                     if not r.get("latency_censored")]),
               latency_note="All-attempt wall statistics include censored waits after transport failure. Failed observations remain in the denominator on resume.",
               service_setups=[{"query_id": r["query_id"], "service_setup_ms": r["service_setup_ms"]}
                               for r in records if r["session_first"]],
               wrapper_note="Experimental child imports differ from recognize.py. Browser rendering and remote network are excluded.")
    return out


def worker_identity(config_path, profile):
    """Read library metadata with the configured worker interpreter. Load no models."""
    import pipelines
    import run_jobs
    settings = pipelines.load(str(config_path))
    python = run_jobs.interpreter(settings, settings.find(profile))
    code = ("import importlib.metadata as m, json, sys; "
            "print(json.dumps({'python': sys.executable, 'python_version': sys.version, "
            "'zxing': m.version('zxing-cpp'), 'pillow': m.version('Pillow')}))")
    done = subprocess.run([python, "-c", code], stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, timeout=30, cwd=ROOT)
    if done.returncode:
        raise ValueError("configured worker cannot report required library versions: %s" % done.stderr.strip())
    return json.loads(done.stdout)


def run_session(mode, variant, rows, options, output, resume, adapter_factory=RouteAdapter,
                server_context=isolated_server, post=post_image):
    import benchmark_barcode_variants as scans
    stem, output = mode + "-" + variant, Path(output)
    path = output / (stem + ".jsonl")
    saved = scans.records_for_resume(path) if resume else []
    done = {r["query_id"] for r in saved}
    selected = {r["query_id"] for r in rows}
    if len(done) != len(saved) or not done <= selected:
        raise ValueError("HTTP checkpoints do not match the selection")
    todo = [row for row in rows if row["query_id"] not in done]
    if not todo:
        return http_summary(saved)
    adapter = adapter_factory(mode, variant, options, output)
    new, current = [], None
    try:
        with server_context(adapter) as (server, setup_ms), path.open("a" if resume else "w") as stream:
            scans.save_json(output / (stem + ".service-%d.json" % time.time_ns()),
                            {"address": list(server.server_address), "setup_ms": setup_ms,
                             "scope": SCOPE, "watcher_started": False})
            for number, row in enumerate(todo):
                source_started = time.perf_counter()
                data = Path(row["path"]).read_bytes()
                source_ms = (time.perf_counter() - source_started) * 1000
                if hashlib.sha256(data).hexdigest() != row["image_sha256"]:
                    raise ValueError("source photo digest changed")
                current = adapter.begin(row)
                server.recognize_dir = current["upload_dir"]
                post_started, transport_error = time.perf_counter(), None
                try:
                    response = post(server.server_address,
                                    {"pipeline": options["profile"], "name": row["image_path"]},
                                    data, timeout=3 * options["watchdog_s"] + 60)
                except Exception as exc:
                    transport_error = "%s: %s" % (type(exc).__name__, exc)
                    adapter.blocked = True
                    # Keep active request context until shutdown joins its handler.
                    telemetry = dict(adapter.telemetry)
                    response = {"http_status": None, "body": {"error": transport_error},
                                "client_wall_ms": (time.perf_counter() - post_started) * 1000,
                                "response_bytes": None, "json_parse_ms": 0.0}
                else:
                    telemetry = adapter.finish()
                raw = telemetry.get("raw_answer") or {
                    "candidates": [], "http_status": None, "trace": None,
                    "error": telemetry.get("adapter_error") or "route produced no backend answer"}
                issues = response_problems(response, raw, row)
                judged = dict(raw)
                if issues:
                    judged["error"] = "; ".join(issues)
                wall = response["client_wall_ms"]
                response_path = None
                if transport_error is None:
                    response_path = output / "responses" / stem / (current["request_key"] + ".json")
                    response_path.parent.mkdir(parents=True, exist_ok=True)
                    scans.save_json(response_path, response["body"])
                record = {"query_id": row["query_id"], "image_sha256": row["image_sha256"],
                          "label": row.get("label"), "truth": row.get("truth"),
                          "selection_reasons": row["selection_reasons"], "mode": mode,
                          "variant": variant, "scope": SCOPE, "session_first": number == 0,
                          "service_setup_ms": setup_ms if number == 0 else 0.0,
                          "startup_ms": telemetry.get("startup_ms", 0.0),
                          "build_ms": telemetry.get("build_ms", 0.0),
                          "ask_wall_ms": telemetry.get("ask_wall_ms", 0.0),
                          "client_wall_ms": wall, "http_status": response["http_status"],
                          "json_parse_ms": response["json_parse_ms"],
                          "http_plus_json_ms": wall + response["json_parse_ms"],
                          "response_bytes": response["response_bytes"], "source_read_ms": source_ms,
                          "response_file": str(response_path) if response_path else None,
                          "response_problems": issues, "transport_error": transport_error,
                          "latency_censored": transport_error is not None,
                          "response_complete": transport_error is None,
                          "upload_dir": current["upload_dir"], "cache_root": current["cache_root"],
                          "stage_ms": cli.stage_costs(raw.get("trace")), "answer": raw,
                          "telemetry": telemetry, **cli.classify(row, judged, wall)}
                if transport_error is not None:
                    record["within_3s"] = False  # No complete HTTP response arrived.
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
                new.append(record)
                scans.save_json(output / (stem + ".summary.json"), http_summary(saved + new))
                print(json.dumps({"mode": mode, "variant": variant,
                                  "completed": len(saved) + len(new), "selected": len(rows)}), flush=True)
                if record["error"] or record["degraded"]:
                    adapter.blocked = True
                    raise RuntimeError("HTTP recognition failed or degraded; stop before the next image")
    except BaseException as exc:
        adapter.blocked = True
        scans.save_json(output / (stem + ".failure.json"),
                        {"query_id": current["query_id"] if current else None,
                         "error": "%s: %s" % (type(exc).__name__, exc),
                         "completed_rows": len(saved) + len(new),
                         "outstanding_remote_work_possible": True,
                         "action": "Check outstanding service work before resuming."})
        raise
    return http_summary(saved + new)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline-run", "baseline-log", "stage1", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--images-dir", type=Path, default=ROOT / "data/testsets/images")
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--profile", default=cli.DEFAULT_PROFILE)
    parser.add_argument("--variants", default="full")
    parser.add_argument("--modes", default="process,persistent")
    parser.add_argument("--sample-size", type=int, default=64)
    parser.add_argument("--watchdog-s", type=float, default=300)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    try:
        variants, modes = args.variants.split(","), args.modes.split(",")
        if (not variants or any(v not in cli.VARIANTS for v in variants)
                or len(set(variants)) != len(variants) or not modes
                or any(m not in cli.MODES for m in modes) or len(set(modes)) != len(modes)
                or args.watchdog_s <= 0):
            raise ValueError("invalid HTTP variant, mode, or watchdog")
        import benchmark_barcode_variants as scans
        from benchmark_barcode_crops import measurement_lock, require_stage1
        baseline = scans.require_finished(args.baseline_run, args.baseline_log)
        query_ids = [r["query_id"] for r in scans.read_jsonl(args.baseline_run / "queries.jsonl")]
        require_stage1(args.stage1, query_ids, baseline_run=args.baseline_run)
        with measurement_lock(args.stage1):
            require_stage1(args.stage1, query_ids, baseline_run=args.baseline_run)
            rows = scans.load_photos(args.baseline_run, args.images_dir)
            if len(rows) != baseline["answered"]:
                raise ValueError("baseline answer count is incomplete")
            results = {r["query_id"]: r for r in scans.read_jsonl(args.baseline_run / "results.jsonl")}
            selected = cli.select_sample(rows, results, args.sample_size)
            output = args.output.resolve()
            forbidden = [args.baseline_run.resolve(), args.stage1.resolve(),
                         (ROOT / "data").resolve(), (ROOT / "runs").resolve()]
            if any(output == p or p in output.parents or output in p.parents for p in forbidden):
                raise ValueError("HTTP output overlaps production or earlier measurements")
            set_name = baseline["options"]["set"]
            inputs = cli.input_identity(args.config, args.profile, set_name)
            selection = [{k: r[k] for k in ("query_id", "image_sha256", "selection_reasons")}
                         for r in selected]
            identity = {"revision": REVISION, "scope": SCOPE, "inputs": inputs,
                        "baseline": str(args.baseline_run.resolve()),
                        "baseline_hashes": {n: cli.file_hash(args.baseline_run / n)
                                            for n in ("run.json", "queries.jsonl", "results.jsonl")},
                        "selection": selection, "selection_fingerprint": cli.digest(selection),
                        "modes": modes, "variants": variants, "profile": args.profile,
                        "watchdog_s": args.watchdog_s, "server_python": sys.version,
                        "worker_runtime": worker_identity(args.config, args.profile),
                        "pillow": scans.barcode.PILLOW_VERSION,
                        "sources": {str(p.relative_to(ROOT)): cli.file_hash(p)
                                    for p in sorted(list((ROOT / "pipeline").glob("*.py")) +
                                                    list((ROOT / "scripts").glob("benchmark_*.py")))}}
            manifest = output / "manifest.json"
            if manifest.exists():
                if not args.resume or json.loads(manifest.read_text()) != identity:
                    raise ValueError("HTTP resume needs unchanged selection, code, configuration, and data")
            elif args.resume:
                raise ValueError("HTTP resume needs a manifest")
            elif output.exists() and any(output.iterdir()):
                raise ValueError("HTTP experiment needs an empty output directory")
            output.mkdir(parents=True, exist_ok=True)
            scans.save_json(manifest, identity)
            scans.save_json(output / ("host-%d.json" % time.time_ns()),
                            {"pid": os.getpid(), "host": platform.platform(),
                             "cpu_count": os.cpu_count(), "load_average": os.getloadavg(),
                             "scope": SCOPE, "hard_timeout_implemented": False})
            options = {"profile": args.profile, "config": str(args.config.resolve()),
                       "database": inputs["database"], "watchdog_s": args.watchdog_s}
            for mode in modes:
                for variant in variants:
                    if cli.input_identity(args.config, args.profile, set_name) != inputs:
                        raise ValueError("live configuration or catalogue changed")
                    run_session(mode, variant, selected, options, output, args.resume)
            if cli.input_identity(args.config, args.profile, set_name) != inputs:
                raise ValueError("live configuration or catalogue changed during measurement")
            scans.save_json(output / "complete.json", {"manifest_fingerprint": cli.digest(identity),
                                                       "finished": time.time(), "scope": SCOPE})
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, TimeoutError) as exc:
        print("HTTP recognition benchmark stopped: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
