"""Measure barcode variants after a baseline run finishes. Never call a model service.

Use --baseline-run DIR --baseline-log FILE --output DIR. Use --resume to continue.
The demo variants read no cache. The bulk variants use caches below the output directory.
A warm bulk variant requires its cold variant for the same selected photos.
"""
import argparse
import concurrent.futures as futures
import contextlib
import hashlib
import itertools
import json
import math
import sys
import threading
import time
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import barcode  # noqa: E402
import model_cache  # noqa: E402

VARIANTS = ("full", "whole1", "whole", "tiles3", "photo4", "cache-cold-1",
            "cache-warm-1", "cache-cold-4", "cache-warm-4")
REVISION = 1
DEADLINE_MS = 3000


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]


def require_finished(run_dir, log_path):
    """Refuse every scan until this exact baseline has a final done event and metadata."""
    run_dir = Path(run_dir)
    if not (run_dir / "run.json").is_file():
        raise ValueError("baseline run.json is absent; no barcode scan is allowed")
    events = []
    for line in Path(log_path).read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and "event" in event:
            events.append(event)
    if (not events or events[-1].get("event") != "done"
            or events[-1].get("run_id") != run_dir.name):
        raise ValueError("baseline job log does not end with done for this run; no scan is allowed")
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    if meta.get("run_id") != run_dir.name or not meta.get("finished"):
        raise ValueError("baseline metadata does not identify a finished run")
    return meta


def load_photos(run_dir, images_dir):
    """Match query digests to the stored photos. Keep the baseline query order."""
    queries = read_jsonl(Path(run_dir) / "queries.jsonl")
    results = {row["query_id"]: row for row in read_jsonl(Path(run_dir) / "results.jsonl")}
    paths = {}
    for path in sorted(Path(images_dir).rglob("*")):
        if path.is_file():
            paths.setdefault(path.name.split(".", 1)[0], path)
    rows = []
    for query in queries:
        digest, qid = query["image_sha256"], query["query_id"]
        if digest not in paths or qid not in results:
            raise ValueError("baseline query %s has no stored photo or result" % qid)
        result = results[qid]
        if result.get("image_sha256") != digest:
            raise ValueError("baseline result digest differs for %s" % qid)
        step = next((s for s in (result.get("trace") or {}).get("steps", [])
                     if s.get("id") == "barcode"), None)
        if step is None:
            raise ValueError("baseline query %s has no barcode trace" % qid)
        rows.append(dict(query, path=str(paths[digest]), baseline_step=step,
                         baseline_latency_ms=result["latency_ms"]))
    if len({row["query_id"] for row in rows}) != len(rows):
        raise ValueError("baseline query IDs are not unique")
    return rows


class MeasuredDecoder(barcode.Decoder):
    """Count scanner calls, including speculative parallel work and caught errors."""

    def __init__(self, options):
        super().__init__(options)
        self.calls = self.decode_errors = 0
        self._measure_lock = threading.Lock()
        self._instrument()

    def _instrument(self):
        native = self.scanner.decode

        def measured(*args, **kwargs):
            with self._measure_lock:
                self.calls += 1
            try:
                return native(*args, **kwargs)
            except Exception:
                with self._measure_lock:
                    self.decode_errors += 1
                raise

        self.scanner.decode = measured

    def configure(self, scanner):
        super().configure(scanner)
        self._instrument()
        return self


def scan_stages(decoder, image, lookup, stages, pool=None):
    """Keep the production stage order. At most four stages decode at the same time."""
    image = decoder.scaled(image)
    found = barcode._dedupe(decoder.read(image))
    hit = lookup.find(found)
    if barcode.is_unique(hit) or stages == 1 or not decoder.options["tile_scan"]:
        return found, hit
    tiles = itertools.islice(barcode.tiles(image), stages - 1)
    if pool is None:
        for tile in tiles:
            found = barcode._dedupe(found + decoder.read(tile))
            hit = lookup.find(found)
            if barcode.is_unique(hit):
                break
        return found, hit
    pending = deque()
    try:
        for tile in itertools.islice(tiles, 4):
            pending.append(pool.submit(decoder.read, tile))
        while pending:
            found = barcode._dedupe(found + pending.popleft().result())
            hit = lookup.find(found)
            if barcode.is_unique(hit):
                break
            tile = next(tiles, None)
            if tile is not None:
                pending.append(pool.submit(decoder.read, tile))
    finally:
        # Running native calls cannot be cancelled. Include their time and call count.
        for task in pending:
            task.cancel()
        for task in pending:
            with contextlib.suppress(Exception):
                task.result()
    return found, hit


def signature(hit):
    return None if hit is None else (hit["source"], hit["code"], tuple(hit["slugs"]))


def measure_one(row, variant, options, lookup, pool=None, factory=MeasuredDecoder):
    decoder = factory(options)
    if variant == "whole1" and hasattr(decoder, "binarizers"):
        decoder.binarizers = decoder.binarizers[:1]
    started = time.perf_counter()
    found, hit, cached, error = [], None, False, None
    try:
        if variant.startswith("cache-"):
            found, hit, cached = decoder.scan_file(row["path"], lookup)
        else:
            image, _ = barcode.derive.open_image(row["path"])
            stages = 1 if variant in ("whole", "whole1") else 10 if variant == "tiles3" else 35
            found, hit = scan_stages(decoder, image, lookup, stages, pool)
    except Exception as exc:
        error = "%s: %s" % (type(exc).__name__, exc)
    ms = (time.perf_counter() - started) * 1000
    baseline = row["baseline_step"].get("out", {}).get("hit")
    unique, was_unique = barcode.is_unique(hit), barcode.is_unique(baseline)
    truth = row.get("truth") or []
    positive = row.get("label") == "positive"
    eligible = not row["baseline_step"].get("error")
    correct = bool(positive and unique and hit["slugs"][0] in truth)
    was_correct = bool(positive and was_unique and baseline["slugs"][0] in truth)
    wrong = None
    if unique:
        if positive:
            wrong = not correct
        elif row.get("label") == "negative":
            rejected = set(truth or [row.get("slug")])
            wrong = True if hit["slugs"][0] in rejected else None
        elif row.get("label") == "no_match":
            wrong = True
    same = signature(hit) == signature(baseline)
    remainder = max(0, row["baseline_latency_ms"] - row["baseline_step"]["ms"])
    estimated = ms if unique else ms + remainder if same else None
    return {"query_id": row["query_id"], "image_sha256": row["image_sha256"],
            "image_path": row["image_path"], "variant": variant, "truth": truth,
            "label": row["label"], "ms": round(ms, 3), "calls": decoder.calls,
            "decode_errors": decoder.decode_errors, "error": error, "cached": cached,
            "codes": found, "hit": hit, "match": "unique" if unique else "shared" if hit else "miss",
            "baseline_hit": baseline, "baseline_codes": row["baseline_step"].get("out", {}).get("codes", []),
            "baseline_eligible": eligible, "same_match": same,
            "lost_baseline_hit": baseline is not None and hit is None,
            "conflict": bool(was_unique and unique and baseline["slugs"] != hit["slugs"]),
            "truth_correct": correct, "baseline_truth_correct": was_correct,
            "truth_wrong": wrong,
            "baseline_remaining_ms": round(remainder, 3),
            "estimated_total_ms": round(estimated, 3) if estimated is not None else None,
            "barcode_over_3s": ms > DEADLINE_MS}


def distribution(values):
    values = sorted(values)
    if not values:
        return {"median": None, "p95": None, "p99": None, "max": None}
    middle = len(values) // 2
    median = values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2
    return {"median": median, "p95": values[math.ceil(.95 * len(values)) - 1],
            "p99": values[math.ceil(.99 * len(values)) - 1], "max": values[-1]}


def summarize(records):
    counts = Counter(row["match"] for row in records)
    eligible = [r for r in records if r["baseline_eligible"] and r["label"] == "positive"]
    estimates = [r["estimated_total_ms"] for r in records if r["estimated_total_ms"] is not None]
    return {"photos": len(records), "matched": counts["unique"] + counts["shared"],
            "missed": counts["miss"], "unique": counts["unique"], "shared": counts["shared"],
            "conflicts": sum(r["conflict"] for r in records),
            "lost_baseline_hits": sum(r["lost_baseline_hit"] for r in records),
            "same_matches": sum(r["same_match"] for r in records),
            "truth_correct": sum(r["truth_correct"] for r in records),
            "truth_wrong": sum(r["truth_wrong"] is True for r in records),
            "errors": sum(bool(r["error"] or r["decode_errors"]) for r in records),
            "native_calls": sum(r["calls"] for r in records),
            "cache_hits": sum(r["cached"] for r in records),
            "barcode_ms": distribution([r["ms"] for r in records]),
            "barcode_over_3s": sum(r["barcode_over_3s"] for r in records),
            "barcode_within_3s_share": (sum(not r["barcode_over_3s"] for r in records) / len(records)
                                        if records else None),
            "estimated_total_ms": distribution(estimates),
            "estimated_total_over_3s": sum(ms > DEADLINE_MS for ms in estimates),
            "estimated_total_photos": len(estimates),
            "estimated_total_within_3s_share": (sum(ms <= DEADLINE_MS for ms in estimates) / len(estimates)
                                                if estimates else None),
            "paired_positive_photos": len(eligible),
            "paired_correct_delta": sum(int(r["truth_correct"]) - int(r["baseline_truth_correct"])
                                         for r in eligible),
            "paired_gained": sum(r["truth_correct"] and not r["baseline_truth_correct"] for r in eligible),
            "paired_lost": sum(not r["truth_correct"] and r["baseline_truth_correct"] for r in eligible)}


@contextlib.contextmanager
def isolated_cache(path, read):
    old = model_cache.ROOT, model_cache.READ
    model_cache.ROOT, model_cache.READ = str(path), read
    try:
        yield
    finally:
        model_cache.ROOT, model_cache.READ = old


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def records_for_resume(path):
    """Discard only an interrupted final JSON line in this benchmark's own output."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = []
    for number, line in enumerate(lines):
        try:
            rows.append(json.loads(line))
        except ValueError:
            if number != len(lines) - 1:
                raise ValueError("invalid result inside %s" % path)
            break
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return rows


def run_variant(variant, rows, options, lookup, output, resume, factory=MeasuredDecoder):
    path = output / (variant + ".jsonl")
    existing = records_for_resume(path) if resume else []
    done = {row["query_id"] for row in existing}
    todo = [row for row in rows if row["query_id"] not in done]
    selected = {row["query_id"] for row in rows}
    if variant.startswith("cache-warm-"):
        cold = output / (variant.replace("-warm-", "-cold-") + ".jsonl")
        warmed = {row["query_id"] for row in read_jsonl(cold)} if cold.is_file() else set()
        if selected - warmed:
            raise ValueError("%s needs its cold variant for every selected photo" % variant)
    workers = 4 if variant.endswith("-4") else 1
    cache = output / "cache" / (str(workers) if variant.startswith("cache-") else "unused")
    timing_path = output / (variant + ".timing.json")
    segments = json.loads(timing_path.read_text()) if resume and timing_path.exists() else []
    if existing and not segments:
        segments.append({"photos": len(existing), "wall_s": 0, "complete": False})
    segment = {"photos": 0, "wall_s": 0, "complete": False}
    segments.append(segment)
    save_json(timing_path, segments)
    started, new = time.perf_counter(), []
    with isolated_cache(cache, "-cold-" not in variant), contextlib.ExitStack() as stack:
        pool = stack.enter_context(futures.ThreadPoolExecutor(4)) if variant == "photo4" else None
        images = stack.enter_context(futures.ThreadPoolExecutor(workers)) if workers > 1 else None
        measure = lambda row: measure_one(row, variant, options, lookup, pool, factory)
        answers = images.map(measure, todo) if images else map(measure, todo)
        with path.open("a" if resume else "w", encoding="utf-8") as stream:
            for record in answers:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
                new.append(record)
                if len(new) % 25 == 0:
                    print(json.dumps({"variant": variant, "completed": len(done) + len(new),
                                      "selected": len(rows)}), flush=True)
    summary = summarize([r for r in existing + new if r["query_id"] in selected])
    segment.update(photos=len(new), wall_s=round(time.perf_counter() - started, 6), complete=True)
    save_json(timing_path, segments)
    complete = all(s.get("complete") for s in segments)
    measured_wall = sum(s["wall_s"] for s in segments)
    timed_photos = sum(s["photos"] for s in segments)
    summary.update(image_workers=workers, decoder_workers=4 if variant == "photo4" else 1,
                   max_active_decodes=4 if variant == "photo4" else workers,
                   wall_segments=segments, elapsed_incomplete=not complete,
                   wall_total_s=measured_wall if complete else None,
                   photos_per_second=timed_photos / measured_wall if complete and measured_wall else None,
                   note="Estimated total reuses baseline non-barcode time. It is not a new full recognition measurement.")
    save_json(output / (variant + ".summary.json"), summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-run", required=True, type=Path)
    parser.add_argument("--baseline-log", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--images-dir", type=Path, default=ROOT / "data" / "testsets" / "images")
    parser.add_argument("--variants", default=",".join(VARIANTS))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.limit is not None and args.limit < 1:
            raise ValueError("--limit MUST be positive")
        variants = args.variants.split(",")
        if not variants or any(v not in VARIANTS for v in variants) or len(set(variants)) != len(variants):
            raise ValueError("--variants MUST name unique values from %s" % ",".join(VARIANTS))
        meta = require_finished(args.baseline_run, args.baseline_log)
        output, production = args.output.resolve(), Path(model_cache.ROOT).resolve()
        if (output == production or output in production.parents or production in output.parents
                or output == args.baseline_run.resolve()):
            raise ValueError("output MUST be separate from production cache and baseline files")
        options = barcode.check_options({k: v for k, v in meta["backend"]["barcode"].items()
                                         if k in barcode.DEFAULTS})
        scanner = meta["backend"]["barcode"].get("scanner")
        if not isinstance(scanner, dict):
            raise ValueError("baseline has no HTTP scanner identity")
        factory = lambda configured: MeasuredDecoder(configured).configure(scanner)
        rows = load_photos(args.baseline_run, args.images_dir)
        if len(rows) != meta["answered"] or len(rows) != meta["query_set"]["total"]:
            raise ValueError("baseline does not hold a completed result for every query")
        lookup = barcode.CodeLookup.load(meta["options"]["database"])
        identity = {"revision": REVISION, "baseline": str(args.baseline_run.resolve()),
                    "images_dir": str(args.images_dir.resolve()), "options": options,
                    "scanner": scanner, "pillow": barcode.PILLOW_VERSION,
                    "production_cache_revision": barcode.CACHE_REVISION,
                    "files": {name: hashlib.sha256((args.baseline_run / name).read_bytes()).hexdigest()
                              for name in ("run.json", "queries.jsonl", "results.jsonl")},
                    "lookup": [[kind, code, slugs] for (kind, code), slugs in sorted(lookup.values.items())]}
        manifest = output / "manifest.json"
        if manifest.exists():
            if not args.resume or json.loads(manifest.read_text()) != identity:
                raise ValueError("output exists; --resume needs unchanged baseline, lookup and decoder settings")
        elif args.resume:
            raise ValueError("--resume needs an existing benchmark manifest")
        elif output.exists() and any(output.iterdir()):
            raise ValueError("a new benchmark needs an empty output directory")
        output.mkdir(parents=True, exist_ok=True)
        save_json(manifest, identity)
        rows = rows[:args.limit] if args.limit else rows
        # Validate source identity before timing. This reads bytes but performs no scan.
        for row in rows:
            if hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest() != row["image_sha256"]:
                raise ValueError("stored photo digest differs for %s" % row["query_id"])
        for variant in variants:
            require_finished(args.baseline_run, args.baseline_log)
            summary = run_variant(variant, rows, options, lookup, output, args.resume,
                                  factory)
            print(json.dumps({"variant": variant, "summary": summary}), flush=True)
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print("benchmark refused: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
