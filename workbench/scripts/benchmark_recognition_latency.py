"""Measure sequential recognition in isolated processes after stage 1 finishes.

This is an experimental CLI client. Its wall time includes process startup for the
process mode. It excludes HTTP, upload storage, and the Recognize page step view.
It does not implement a hard 3-second timeout. The watchdog stops the experiment on
a stalled child. A remote request can continue after its client process stops.

Read the barcode benchmark plan and check GPU services before starting this script.
Use --baseline-run, --baseline-log, --stage1, and --output. Use --resume to continue.
Every child disables model-cache reads before backend construction. Cache writes go
under the experiment output. No production profile or production cache is changed.
The opt-in fresh crop variants request SAM3 within recognition. They scan original
rectangles. Later pipeline segmentation can repeat the SAM3 call and stays charged.
"""
import time

MODULE_STARTED = time.perf_counter()

import argparse
import concurrent.futures
import contextlib
import hashlib
import io
import json
import os
import platform
import select
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
REVISION = 2
CROP_VARIANTS = tuple(prefix + region for prefix in ("fresh-", "whole-fresh-")
                      for region in ("bottle", "label", "barcode"))
VARIANTS = ("full", "whole1", "whole", "tiles3", "photo4") + CROP_VARIANTS
MODES = ("process", "persistent")
DEFAULT_PROFILE = "barcode-rerank-siglip2-512-crop"
DEADLINE_MS = 3000
SCOPE = "CLI worker wall; excludes HTTP, upload storage, and step-view construction"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"))
                          .encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def distribution_version(name):
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def cache_directory(path, boundary=None):
    """Validate an experiment cache root before assigning it in a worker."""
    cache = Path(path).resolve()
    for production in ((ROOT / "data").resolve(), (ROOT / "runs").resolve()):
        if cache == production or production in cache.parents or cache in production.parents:
            raise ValueError("worker cache MUST be outside the production cache and data")
    if boundary is not None:
        base = Path(boundary).resolve()
        if cache != base and base not in cache.parents:
            raise ValueError("worker cache is outside the experiment cache boundary")
    return cache


def select_sample(rows, results, size):
    """Keep every code hit. Add deterministic rerank, large, slow, and spread cases."""
    if size < 1:
        raise ValueError("sample size MUST be positive")
    selected, reasons = {}, {}

    def add(row, reason):
        key = row["query_id"]
        selected[key] = row
        reasons.setdefault(key, []).append(reason)

    def ordered(items):
        return sorted(items, key=lambda r: (r["image_sha256"], r["query_id"]))

    for row in ordered(rows):
        if row["baseline_step"].get("out", {}).get("hit") is not None:
            add(row, "baseline_barcode_hit")
    if len(selected) > size:
        raise ValueError("sample size is smaller than the %d mandatory barcode hits" % len(selected))

    def steps(row):
        return (results[row["query_id"]].get("trace") or {}).get("steps", [])

    def pixels(row):
        inp = next((s.get("out", {}) for s in steps(row) if s["id"] == "input"), {})
        return int(inp.get("width") or 0) * int(inp.get("height") or 0)

    rerank = [r for r in ordered(rows) if any(s["id"] == "cluster_rules" for s in steps(r))]
    strata = (("rerank", sorted(rerank, key=lambda r: -r["baseline_latency_ms"])),
              ("large_image", sorted(ordered(rows), key=lambda r: -pixels(r))),
              ("slow_barcode", sorted(ordered(rows),
                                      key=lambda r: -r["baseline_step"].get("ms", 0))))
    quota = max(1, (size - len(selected)) // 4)
    for reason, candidates in strata:
        taken = 0
        for row in candidates:
            if len(selected) >= size or taken >= quota:
                break
            if row["query_id"] not in selected:
                add(row, reason)
                taken += 1
    remaining = [r for r in ordered(rows) if r["query_id"] not in selected]
    needed = min(size - len(selected), len(remaining))
    for i in range(needed):
        add(remaining[i * len(remaining) // needed], "deterministic_spread")
    # Keep a fixed order. Cache reads stay off even when source bytes repeat.
    return [dict(row, selection_reasons=reasons[row["query_id"]])
            for row in ordered(selected.values())]


def classify(row, answer, client_wall_ms):
    """Do not interpret negative or unknown labels as a positive identification."""
    candidates = answer.get("candidates") or []
    trace = answer.get("trace") or {}
    stage_errors = [s.get("error") or (s.get("out") or {}).get("error")
                    for s in trace.get("steps", [])]
    stage_errors = [e for e in stage_errors if e]
    failure = answer.get("error") or ("HTTP status %s" % answer.get("http_status")
                                      if answer.get("http_status") != 200 else None)
    top = candidates[0].get("slug") if candidates else None
    truth, label = set(row.get("truth") or []), row.get("label")
    correct = top in truth if label == "positive" and truth else None
    wrong = (not correct if correct is not None else
             bool(candidates) if label == "no_match" else
             True if label == "negative" and top in (truth or {row.get("slug")}) else None)
    # An optional stage can fail and still return the base ranking. Record this as
    # degraded. Do not count that failure as a successful complete-pipeline deadline.
    degraded = bool(stage_errors or answer.get("sam3_failure_after") or answer.get("decode_errors"))
    success = not failure and not degraded and bool(candidates)
    within = client_wall_ms <= DEADLINE_MS
    return {"error": failure, "stage_errors": stage_errors, "degraded": degraded,
            "truth_correct": correct, "truth_wrong": wrong,
            "top5_correct": (any(c.get("slug") in truth for c in candidates[:5])
                             if label == "positive" and truth else None),
            "within_3s": within, "successful_response": success,
            "correct_within_3s": bool(success and correct and within),
            "late_correct": bool(success and correct and not within),
            "fast_error": bool((failure or degraded) and within)}


def stage_costs(trace):
    result = {}
    for step in (trace or {}).get("steps", []):
        name = step.get("id", "unknown")
        result[name] = round(result.get(name, 0.0) + float(step.get("ms") or 0), 3)
    return result


def summary(records):
    from benchmark_barcode_variants import distribution
    labelled = [r for r in records if r["truth_correct"] is not None]
    steady = [r for r in records if not r["session_first"]]
    crops = [r["answer"]["crop_scan"] for r in records if r["answer"].get("crop_scan")]
    skipped = sum(c["status"] == "skipped_unique_whole_hit" for c in crops)
    crop_summary = {"rows": len(crops), "sam3_client_calls": sum(c["sam3_requests"] for c in crops),
                    "whole_hit_skips": skipped,
                    "whole_hit_skip_share": skipped / len(crops) if crops else None,
                    "status_counts": {s: sum(c["status"] == s for c in crops)
                                      for s in sorted({c["status"] for c in crops})},
                    "sam3_wall_ms": distribution([c["sam3_wall_ms"] for c in crops]),
                    "geometry_ms": distribution([c["geometry_ms"] for c in crops]),
                    "crop_decode_ms": distribution([c["crop_decode_ms"] for c in crops]),
                    "cost_note": "These costs are inside barcode and client wall time. Do not add them again."}
    strata = {}
    for name, hit in (("baseline_barcode_hit", True), ("other_selected_rows", False)):
        rows = [r for r in records if ("baseline_barcode_hit" in r["selection_reasons"]) == hit]
        labelled_rows = [r for r in rows if r["truth_correct"] is not None]
        strata[name] = {"rows": len(rows), "positive_labelled_rows": len(labelled_rows),
                        "within_3s": sum(r["within_3s"] for r in rows),
                        "correct_within_3s": sum(r["correct_within_3s"] for r in rows),
                        "client_wall_ms": distribution([r["client_wall_ms"] for r in rows])}
    return {"rows": len(records), "unique_images": len({r["image_sha256"] for r in records}),
            "positive_labelled_rows": len(labelled), "scope": SCOPE,
            "hard_timeout_implemented": False, "deadline_ms": DEADLINE_MS,
            "client_wall_ms": distribution([r["client_wall_ms"] for r in records]),
            "steady_client_wall_ms": distribution([r["client_wall_ms"] for r in steady]),
            "first_requests": [{k: r[k] for k in ("query_id", "client_wall_ms", "startup_ms",
                                                   "build_ms", "ask_wall_ms")}
                               for r in records if r["session_first"]],
            "correct_within_3s": sum(r["correct_within_3s"] for r in records),
            "within_3s": sum(r["within_3s"] for r in records),
            "within_3s_share": (sum(r["within_3s"] for r in records) / len(records)
                                 if records else None),
            "successful_within_3s": sum(r["successful_response"] and r["within_3s"]
                                         for r in records),
            "correct_within_3s_share": (sum(r["correct_within_3s"] for r in labelled)
                                         / len(labelled) if labelled else None),
            "late_correct": sum(r["late_correct"] for r in records),
            "fast_errors": sum(r["fast_error"] for r in records),
            "errors": sum(bool(r["error"]) for r in records),
            "degraded": sum(r["degraded"] for r in records),
            "decoder_error_rows": sum(bool(r["answer"].get("decode_errors")) for r in records),
            "decoder_errors": sum(r["answer"].get("decode_errors", 0) for r in records),
            "top1_correct": sum(r["truth_correct"] is True for r in records),
            "top5_correct": sum(r["top5_correct"] is True for r in records),
            "proven_wrong": sum(r["truth_wrong"] is True for r in records),
            "selection_strata": strata,
            "fresh_crop": crop_summary,
            "sample_note": "This pilot retains every barcode hit. Its aggregate deadline share is not a corpus estimate.",
            "tail_note": "Sample p95 and p99 are descriptive; they do not prove reliability."}


def fresh_crop_geometry(image, region, client, detail, clock=time.perf_counter):
    """Obtain fresh geometry. Do not read a saved response or saved rectangle."""
    import alternatives
    import model_cache
    from benchmark_barcode_crops import BARCODE_MARGIN, detected_boxes, rectangle
    if model_cache.READ or not client.refresh:
        raise RuntimeError("fresh crop geometry requires disabled cache reads and refresh=True")
    started = clock()
    data, _scale = client._sent_copy(image)
    detail["sent_image_prepare_ms"] = (clock() - started) * 1000
    started = clock()
    detail["sam3_requests"] += 1
    try:
        answer = client._post(data, alternatives.DETECT_TEXTS, True)
    finally:
        detail["sam3_wall_ms"] = (clock() - started) * 1000
    if (not isinstance(answer, dict) or not isinstance(answer.get("instances"), list)
            or any(not isinstance(item, dict) for item in answer["instances"])):
        raise ValueError("invalid fresh SAM3 answer")
    detail["sent_size"] = [answer.get("width"), answer.get("height")]
    started = clock()
    try:
        if region == "label":
            cut = alternatives.label_cut_of(image, answer["instances"])
            if cut is None:
                return {"status": "missing_detection", "boxes": []}
            try:
                return {"status": "available", "boxes": [rectangle(cut[2], image.size)],
                        "method": cut[0]}
            finally:
                cut[1].close()
        noun = alternatives.BOTTLE_NOUN if region == "bottle" else alternatives.BARCODE_NOUN
        result = detected_boxes(answer, noun, image.size,
                                BARCODE_MARGIN if region == "barcode" else 0)
        if result["status"] not in ("available", "missing_detection") or result["invalid_boxes"]:
            raise ValueError("invalid fresh SAM3 geometry: %s" % result["status"])
        return result
    finally:
        detail["geometry_ms"] = (clock() - started) * 1000


def scan_fresh_crops(decoder, image, lookup, variant, client, clock=time.perf_counter):
    """Scan original rectangles. Charge preparation and SAM3 to this request."""
    import barcode
    region = variant.split("fresh-", 1)[1]
    detail = {"variant": variant, "region": region, "status": "not_requested",
              "source": "fresh_sam3", "cache_read": False,
              "endpoint": client.endpoint, "boxes": [], "original_size": list(image.size),
              "sam3_requests": 0, "sam3_wall_ms": 0.0, "sent_image_prepare_ms": 0.0,
              "geometry_ms": 0.0, "whole_decode_ms": 0.0, "crop_decode_ms": 0.0,
              "regions_scanned": 0, "error": None,
              "sam3_request_scope": "Client calls. Existing retries stay in sam3_wall_ms.",
              "reuse": "No response reuse. Later pipeline segmentation is charged again."}
    decoder.crop_scan = detail
    started, found, hit = clock(), [], None
    try:
        if variant.startswith("whole-"):
            scan_started = clock()
            found = barcode._dedupe(decoder.read(decoder.scaled(image)))
            hit = lookup.find(found)
            detail["whole_decode_ms"] = (clock() - scan_started) * 1000
            if barcode.is_unique(hit):
                detail["status"] = "skipped_unique_whole_hit"
                return found, hit
        detail.update(fresh_crop_geometry(image, region, client, detail, clock))
        for box in detail["boxes"]:
            scan_started = clock()
            part = image.crop(box)
            try:
                found = barcode._dedupe(found + decoder.read(decoder.scaled(part)))
                hit = lookup.find(found)
                detail["regions_scanned"] += 1
            finally:
                part.close()
                detail["crop_decode_ms"] += (clock() - scan_started) * 1000
            if barcode.is_unique(hit):
                break
        return found, hit
    except Exception as exc:
        detail["status"] = "error"
        detail["error"] = "%s: %s" % (type(exc).__name__, exc)
        decoder.crop_failure = detail["error"]
        raise
    finally:
        detail["wall_ms"] = (clock() - started) * 1000


@contextlib.contextmanager
def build_experiment(options):
    """Construct the real backend with an isolated experimental barcode decoder."""
    import barcode
    import embedding_run
    import embeddings
    import model_cache
    import benchmark_barcode_variants as scans
    from benchmark_bulk_cache import internal_profile
    # Validate every endpoint before constructing any client or local model.
    pipeline, _ = internal_profile(embeddings.load_settings(options["config"]), options["profile"])
    variant = options["variant"]
    if variant not in VARIANTS:
        raise ValueError("unknown barcode variant")
    with contextlib.ExitStack() as stack:
        pool = (stack.enter_context(concurrent.futures.ThreadPoolExecutor(4))
                if variant == "photo4" else None)

        class ExperimentalDecoder(scans.MeasuredDecoder):
            def __init__(self, config):
                super().__init__(config)
                self.crop_scan, self.crop_failure = None, None
                if variant == "whole1":
                    self.binarizers = self.binarizers[:1]
                if variant in CROP_VARIANTS:
                    # internal_profile checked the actual configured destination and
                    # rejected a conflicting canonical environment value above.
                    self.crop_client = barcode.derive.Sam3Client(
                        endpoint=os.environ.get("SAM3_ENDPOINT") or barcode.derive.SAM3_ENDPOINT,
                        refresh=True)
                    stack.callback(self.crop_client.session.close)

            def scan_file(self, path, lookup):
                self.crop_scan, self.crop_failure = None, None
                if variant == "full":
                    return super().scan_file(path, lookup)
                # The experimental cache record has a separate model namespace.
                # Keep source hashing and a cache write in the measured path.
                data = Path(path).read_bytes()
                fields = model_cache.request_fields(
                    "local://demo-barcode/scan", "demo-barcode",
                    {"variant": variant, "revision": REVISION, "options": self.options},
                    "", [data])
                image, _ = barcode.derive.open_image(io.BytesIO(data))
                started = time.perf_counter()
                try:
                    if variant in CROP_VARIANTS:
                        found, hit = scan_fresh_crops(self, image, lookup, variant, self.crop_client)
                    else:
                        count = 1 if variant in ("whole1", "whole") else 10 if variant == "tiles3" else 35
                        found, hit = scans.scan_stages(self, image, lookup, count, pool)
                    model_cache.store(fields, {"codes": found}, (time.perf_counter() - started) * 1000)
                finally:
                    image.close()
                return found, hit, False

        original = barcode.Decoder
        barcode.Decoder = ExperimentalDecoder
        try:
            backend = embedding_run.build_pipeline_backend(pipeline, options["config"])
        finally:
            barcode.Decoder = original
        if variant in CROP_VARIANTS:
            inner_ask = backend.inner.ask

            def guarded_inner_ask(*args, **kwargs):
                # CodeFirst catches decoder errors. Stop before another model call
                # when fresh geometry failed, while retaining the worker error row.
                if backend.decoder.crop_failure:
                    return [], 0, None, backend.decoder.crop_failure, {"v": 1, "steps": []}
                return inner_ask(*args, **kwargs)

            backend.inner.ask = guarded_inner_ask
            stack.callback(setattr, backend.inner, "ask", inner_ask)
        yield backend
        # The pool waits for all native work before the child accepts shutdown.


def sam3_failure(backend):
    seen = set()
    while backend is not None and id(backend) not in seen:
        seen.add(id(backend))
        segmenter = getattr(backend, "segmenter", None)
        failure = getattr(segmenter, "failure", None)
        if failure:
            return str(failure)
        backend = getattr(backend, "inner", None)
    return None


def worker_loop(source, sink, builder=build_experiment):
    """Serve one request at a time. This function runs inside the child process."""
    import model_cache
    import benchmark_bulk_cache  # noqa: F401 - charge pipeline imports before backend build
    options = json.loads(source.readline())
    boundary = cache_directory(options.get("cache_boundary") or options["cache_root"])
    cache = cache_directory(options["cache_root"], boundary)
    previous = model_cache.ROOT, model_cache.READ
    model_cache.ROOT, model_cache.READ = str(cache), False

    def emit(record):
        sink.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        sink.flush()

    try:
        with contextlib.redirect_stdout(sys.stderr):
            imported_ms = (time.perf_counter() - MODULE_STARTED) * 1000
            started = time.perf_counter()
            with builder(options) as backend:
                build_ms = (time.perf_counter() - started) * 1000
                emit({"event": "ready", "build_ms": build_ms, "worker_import_ms": imported_ms,
                      "cache_read": model_cache.READ, "cache_root": model_cache.ROOT,
                      "spec": backend.spec, "python": sys.executable, "python_version": sys.version,
                      "zxing_version": distribution_version("zxing-cpp"),
                      "pillow_version": distribution_version("Pillow")})
                for line in source:
                    request = json.loads(line)
                    if request.get("stop"):
                        break
                    if request.get("cache_root") is not None:
                        model_cache.ROOT = str(cache_directory(request["cache_root"], boundary))
                    model_cache.READ = False
                    failure_before = sam3_failure(backend)
                    decoder = getattr(backend, "decoder", None)
                    if decoder is not None:
                        decoder.crop_scan = None
                    calls_before = getattr(decoder, "calls", 0)
                    errors_before = getattr(decoder, "decode_errors", 0)
                    started = time.perf_counter()
                    try:
                        answer = backend.ask(request["path"])
                        cands, latency, status, error = answer[:4]
                        out = {"candidates": [{k: v for k, v in cand.items() if k != "items"}
                                              for cand in cands],
                               "latency_ms": latency, "http_status": status, "error": error,
                               "trace": answer[4] if len(answer) > 4 else None}
                    except Exception as exc:  # Preserve an error row, then stop this session.
                        out = {"candidates": [], "http_status": None,
                               "error": "%s: %s" % (type(exc).__name__, exc), "trace": None}
                    out.update(event="answer", query_id=request["query_id"],
                               ask_wall_ms=(time.perf_counter() - started) * 1000,
                               decode_calls=getattr(decoder, "calls", 0) - calls_before,
                               decode_errors=getattr(decoder, "decode_errors", 0) - errors_before,
                               crop_scan=getattr(decoder, "crop_scan", None),
                               sam3_failure_before=failure_before,
                               sam3_failure_after=sam3_failure(backend),
                               cache_read=model_cache.READ, cache_root=model_cache.ROOT)
                    emit(out)
                    if out["error"] or out["sam3_failure_after"]:
                        break  # Do not turn a latched outage into fast subsequent requests.
    finally:
        model_cache.ROOT, model_cache.READ = previous


class Worker:
    """Own one child. Wait for native work on normal shutdown. Stop on a watchdog."""

    def __init__(self, options, log_path, timeout=300):
        self.timeout, self.process, self.log = timeout, None, None
        self._close_lock = threading.RLock()
        started = time.perf_counter()
        try:
            self.log = Path(log_path).open("a", encoding="utf-8")
            self.process = subprocess.Popen([options.get("python") or sys.executable, "-u",
                                             str(Path(__file__).resolve()),
                                             "--worker"], stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, stderr=self.log, text=True,
                                            cwd=ROOT)
            self._send(options)
            self.ready = self._receive()
            if self.ready.get("event") != "ready" or self.ready.get("cache_read") is not False:
                raise RuntimeError("child did not confirm a ready backend with cache reads disabled")
            self.cache_root = str(cache_directory(options["cache_root"]))
            if self.ready.get("cache_root") != self.cache_root:
                raise RuntimeError("child did not confirm the isolated cache root")
            self.startup_ms = (time.perf_counter() - started) * 1000
        except BaseException:
            self.close(force=True)
            raise

    def _send(self, record):
        process = self.process
        if process is None:
            raise RuntimeError("child process is closed")
        process.stdin.write(json.dumps(record) + "\n")
        process.stdin.flush()

    def _receive(self):
        process = self.process
        if process is None:
            raise RuntimeError("child process is closed")
        if not select.select([process.stdout], [], [], self.timeout)[0]:
            raise TimeoutError("child watchdog expired; stop before another image")
        line = process.stdout.readline()
        if not line:
            raise RuntimeError("child stopped without an answer; inspect worker.log")
        return json.loads(line)

    def ask(self, row):
        started = time.perf_counter()
        request = {"query_id": row["query_id"], "path": row["path"]}
        if row.get("cache_root") is not None:
            request["cache_root"] = str(cache_directory(row["cache_root"]))
        self._send(request)
        out = self._receive()
        if out.get("event") != "answer" or out.get("query_id") != row["query_id"]:
            raise RuntimeError("child answer does not match the sequential request")
        if out.get("cache_read") is not False:
            raise RuntimeError("child enabled model-cache reads")
        expected_cache = request.get("cache_root", self.cache_root)
        if out.get("cache_root") != expected_cache:
            raise RuntimeError("child answer used the wrong isolated cache root")
        self.cache_root = expected_cache
        return out, (time.perf_counter() - started) * 1000

    def close(self, force=False):
        # A client disconnect can race the HTTP handler's normal cleanup.
        with self._close_lock:
            process = self.process
            if process is not None:
                if process.poll() is None:
                    if not force:
                        with contextlib.suppress(BrokenPipeError, OSError):
                            self._send({"stop": True})
                        try:
                            process.wait(timeout=self.timeout)
                        except subprocess.TimeoutExpired:
                            force = True
                    if force and process.poll() is None:
                        process.kill()
                        process.wait()
                for stream in (process.stdin, process.stdout):
                    if stream is not None:
                        stream.close()
                self.process = None
            if self.log is not None:
                self.log.close()
                self.log = None


def run_session(mode, variant, rows, options, output, resume, factory=Worker):
    """Checkpoint each sequential answer. A failure stops the complete experiment."""
    import benchmark_barcode_variants as scans
    stem = mode + "-" + variant
    path = output / (stem + ".jsonl")
    saved = scans.records_for_resume(path) if resume else []
    selected = {row["query_id"] for row in rows}
    done = {row["query_id"] for row in saved}
    if len(done) != len(saved) or not done <= selected:
        raise ValueError("checkpoint query IDs do not match the selection")
    todo = [row for row in rows if row["query_id"] not in done]
    worker, new = None, []
    current_row, current_started = None, None
    try:
        with path.open("a" if resume else "w", encoding="utf-8") as stream:
            for number, row in enumerate(todo):
                current_row, current_started = row, time.perf_counter()
                startup = 0.0
                if worker is None:
                    worker = factory(dict(options, variant=variant,
                                          cache_root=str(output / "cache" / stem)),
                                     output / (stem + ".worker.log"), options["watchdog_s"])
                    startup = worker.startup_ms
                try:
                    answer, request_ms = worker.ask(row)
                    cleanup_ms = 0.0
                    if mode == "process":
                        started = time.perf_counter()
                        worker.close()
                        cleanup_ms = (time.perf_counter() - started) * 1000
                    wall = startup + request_ms + cleanup_ms
                    record = {"query_id": row["query_id"], "image_sha256": row["image_sha256"],
                              "truth": row.get("truth"), "label": row.get("label"),
                              "selection_reasons": row["selection_reasons"], "mode": mode,
                              "variant": variant, "scope": SCOPE, "session_first": number == 0,
                              "startup_ms": startup,
                              "build_ms": worker.ready["build_ms"] if startup else 0.0,
                              "backend_initial_build_ms": worker.ready["build_ms"],
                              "worker_import_ms": worker.ready["worker_import_ms"],
                              "request_ms": request_ms, "cleanup_ms": cleanup_ms,
                              "client_wall_ms": wall, "ask_wall_ms": answer["ask_wall_ms"],
                              "stage_ms": stage_costs(answer.get("trace")), "answer": answer,
                              "spec": worker.ready["spec"],
                              **classify(row, answer, wall)}
                except BaseException:
                    worker.close(force=True)
                    worker = None
                    raise
                if mode == "process":
                    worker = None
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
                new.append(record)
                scans.save_json(output / (stem + ".summary.json"), summary(saved + new))
                print(json.dumps({"mode": mode, "variant": variant,
                                  "completed": len(saved) + len(new), "selected": len(rows)}),
                      flush=True)
                if record["error"] or record["degraded"] or answer.get("sam3_failure_after"):
                    raise RuntimeError("recognition failed; checkpoint kept; stop before another image")
    except BaseException as exc:
        scans.save_json(output / (stem + ".failure.json"),
                        {"query_id": current_row["query_id"] if current_row else None,
                         "error": "%s: %s" % (type(exc).__name__, exc),
                         "attempt_wall_ms": ((time.perf_counter() - current_started) * 1000
                                             if current_started is not None else None),
                         "completed_rows": len(saved) + len(new),
                         "outstanding_remote_work_possible": True,
                         "action": "Check services before resuming. No next image was sent."})
        raise
    finally:
        if worker is not None:
            worker.close()
    return summary(saved + new)


def input_identity(config_path, profile, set_name):
    """Record live configuration and data identity. Do not construct a model backend."""
    import embeddings
    import barcode
    import derive
    from benchmark_bulk_cache import catalogue_identity, index_identity, internal_profile
    settings = embeddings.load_settings(str(config_path))
    pipeline, entry = internal_profile(settings, profile)
    database = settings.db_path
    directory = embeddings.entry_dir(database, pipeline.embedding)
    rule_files = {}
    if pipeline.rerank:
        rule_dir = Path(embeddings.entry_dir(database, pipeline.rerank["rules"]))
        rule_files = {str(p.resolve()): file_hash(p) for p in sorted(rule_dir.iterdir())
                      if p.is_file() and p.suffix in (".json", ".jsonl")}
    return {"config": file_hash(config_path), "database": str(Path(database).resolve()),
            "catalogue": catalogue_identity(database, set_name),
            "index": index_identity(directory), "rule_files": rule_files,
            "lookup": [[kind, code, slugs] for (kind, code), slugs in
                       sorted(barcode.CodeLookup.load(database).values.items())],
            "actual_endpoints": {"embedding": entry.base_url, "sam3": derive.SAM3_ENDPOINT}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--baseline-run", type=Path)
    parser.add_argument("--baseline-log", type=Path)
    parser.add_argument("--stage1", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--images-dir", type=Path, default=ROOT / "data/testsets/images")
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--variants", default="full,whole1,whole,tiles3,photo4")
    parser.add_argument("--modes", default="process,persistent")
    parser.add_argument("--sample-size", type=int, default=64)
    parser.add_argument("--watchdog-s", type=float, default=300)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if args.worker:
        try:
            worker_loop(sys.stdin, sys.stdout)
            return 0
        except Exception as exc:
            print("worker failed: %s" % exc, file=sys.stderr)
            return 1
    try:
        if not all((args.baseline_run, args.baseline_log, args.stage1, args.output)):
            raise ValueError("baseline-run, baseline-log, stage1, and output are required")
        variants, modes = args.variants.split(","), args.modes.split(",")
        if (not variants or any(v not in VARIANTS for v in variants)
                or len(set(variants)) != len(variants)
                or not modes or any(m not in MODES for m in modes)
                or len(set(modes)) != len(modes) or args.watchdog_s <= 0):
            raise ValueError("invalid variant, mode, or watchdog")
        import benchmark_barcode_variants as scans
        from benchmark_barcode_crops import measurement_lock, require_stage1
        baseline = scans.require_finished(args.baseline_run, args.baseline_log)
        queries = scans.read_jsonl(args.baseline_run / "queries.jsonl")
        ids = [row["query_id"] for row in queries]
        require_stage1(args.stage1, ids, baseline_run=args.baseline_run)
        with measurement_lock(args.stage1):
            stage1 = require_stage1(args.stage1, ids, baseline_run=args.baseline_run)
            baseline_hashes = {n: file_hash(args.baseline_run / n)
                               for n in ("run.json", "queries.jsonl", "results.jsonl")}
            if (stage1["manifest"].get("baseline") != str(args.baseline_run.resolve())
                    or stage1["manifest"].get("files") != baseline_hashes):
                raise ValueError("stage 1 does not belong to this exact baseline")
            rows = scans.load_photos(args.baseline_run, args.images_dir)
            if len(rows) != baseline["answered"]:
                raise ValueError("baseline answer count is incomplete")
            results = {r["query_id"]: r for r in scans.read_jsonl(args.baseline_run / "results.jsonl")}
            sample = select_sample(rows, results, args.sample_size)
            output = args.output.resolve()
            forbidden = [args.baseline_run.resolve(), args.stage1.resolve(),
                         (ROOT / "data").resolve(), (ROOT / "runs").resolve()]
            if any(output == p or p in output.parents or output in p.parents for p in forbidden):
                raise ValueError("output overlaps production data or earlier measurement artifacts")
            set_name = baseline["options"]["set"]
            inputs = input_identity(args.config, args.profile, set_name)
            identity = {"revision": REVISION, "baseline": str(args.baseline_run.resolve()),
                        "baseline_hashes": baseline_hashes,
                        "selection": [{k: r[k] for k in ("query_id", "image_sha256", "selection_reasons")}
                                      for r in sample], "inputs": inputs,
                        "modes": modes, "variants": variants, "profile": args.profile,
                        "watchdog_s": args.watchdog_s,
                        "python": sys.version, "zxing": scans.barcode.version(scans.barcode.ENGINE),
                        "pillow": scans.barcode.PILLOW_VERSION,
                        "sources": {str(p.relative_to(ROOT)): file_hash(p)
                                    for p in sorted(list((ROOT / "pipeline").glob("*.py")) +
                                                    list((ROOT / "scripts").glob("benchmark_*.py")))}}
            identity["selection_fingerprint"] = digest(identity["selection"])
            manifest = output / "manifest.json"
            if manifest.exists():
                if not args.resume or json.loads(manifest.read_text()) != identity:
                    raise ValueError("resume needs the unchanged selection, config, data, and code")
            elif args.resume:
                raise ValueError("resume needs an existing manifest")
            elif output.exists() and any(output.iterdir()):
                raise ValueError("new measurement needs an empty output directory")
            output.mkdir(parents=True, exist_ok=True)
            scans.save_json(manifest, identity)
            scans.save_json(output / ("host-%d.json" % time.time_ns()),
                            {"pid": os.getpid(), "host": platform.platform(),
                             "cpu_count": os.cpu_count(), "load_average": os.getloadavg(),
                             "cache_reads": False, "hard_timeout_implemented": False,
                             "scope": SCOPE})
            for row in sample:
                if file_hash(row["path"]) != row["image_sha256"]:
                    raise ValueError("source digest changed: %s" % row["query_id"])
            options = {"profile": args.profile, "config": str(args.config.resolve()),
                       "watchdog_s": args.watchdog_s}
            for mode in modes:
                for variant in variants:
                    if input_identity(args.config, args.profile, set_name) != inputs:
                        raise ValueError("configuration or catalogue changed; do not mix measurements")
                    run_session(mode, variant, sample, options, output, args.resume)
            if input_identity(args.config, args.profile, set_name) != inputs:
                raise ValueError("configuration or catalogue changed during the last measurement")
            scans.save_json(output / "complete.json", {"manifest_fingerprint": digest(identity),
                                                       "scope": SCOPE, "finished": time.time()})
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, TimeoutError) as exc:
        print("recognition benchmark stopped: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
