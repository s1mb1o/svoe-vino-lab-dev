"""Measure barcode scans on saved SAM3 rectangles after stage 1 completes.

Use --baseline-run DIR --baseline-log FILE --stage1 DIR --output DIR.
Preparation reads the production SAM3 cache. It never sends a model request or writes
that cache. Checkpoints store geometry, not image derivatives. All decoder calls are
uncached and sequential. Barcode rectangles get a 10% margin on each side, with no cap.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import benchmark_barcode_variants as base
import alternatives
import derive
import embedding_run
import model_cache

REVISION = 2
REGIONS = ("package", "bottle", "label", "barcode")
VARIANTS = tuple(mode + region for region in REGIONS for mode in ("", "whole-"))
BARCODE_MARGIN = 0.10


def digest_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_stage1(stage1, query_ids, baseline_run=None):
    """Require all nine complete result sets, and refuse a live stage-1 process."""
    stage1 = Path(stage1)
    process_path = stage1.parent / "stage1-process.json"
    if process_path.exists():
        process = json.loads(process_path.read_text())
        pid = process.get("pid")
        if isinstance(pid, int) and pid > 0:
            alive = True
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                alive = False
            except PermissionError:
                pass
            if alive:
                try:
                    status = subprocess.run(["ps", "-o", "command=", "-p", str(pid)],
                                            capture_output=True, text=True, check=False, timeout=5)
                except (OSError, subprocess.SubprocessError) as exc:
                    raise ValueError("cannot verify that the stage 1 process stopped") from exc
                if status.returncode or not status.stdout.strip():
                    raise ValueError("cannot verify that the stage 1 process stopped")
                if "benchmark_barcode_variants.py" in status.stdout:
                    raise ValueError("stage 1 is still running; no preparation or scan is allowed")
    expected = set(query_ids)
    if len(expected) != len(query_ids) or not expected:
        raise ValueError("baseline query IDs MUST be nonempty and unique")
    manifest = json.loads((stage1 / "manifest.json").read_text())
    if baseline_run is not None:
        baseline_run = Path(baseline_run).resolve()
        files = ("run.json", "queries.jsonl", "results.jsonl")
        if (manifest.get("baseline") != str(baseline_run)
                or set(manifest.get("files", {})) != set(files)
                or any(manifest["files"][name] != digest_file(baseline_run / name) for name in files)):
            raise ValueError("stage 1 baseline path or artifact hashes differ")
    reference = None
    summaries = {}
    for variant in base.VARIANTS:
        summary = json.loads((stage1 / (variant + ".summary.json")).read_text())
        records = base.read_jsonl(stage1 / (variant + ".jsonl"))
        keys = [(row["query_id"], row["image_sha256"]) for row in records]
        if (summary.get("photos") != len(expected) or len(keys) != len(expected)
                or {key[0] for key in keys} != expected):
            raise ValueError("stage 1 variant %s does not cover the complete baseline" % variant)
        segments = summary.get("wall_segments") or []
        if (not segments or not all(s.get("complete") for s in segments)
                or summary.get("elapsed_incomplete")):
            raise ValueError("stage 1 variant %s has incomplete timing segments" % variant)
        if summary.get("errors", 0):
            raise ValueError("stage 1 variant %s has errors; review them before stage 2" % variant)
        if reference is not None and set(keys) != reference:
            raise ValueError("stage 1 variants disagree about photo digests")
        reference = set(keys)
        summaries[variant] = summary
    return {"manifest": manifest, "summaries": summaries}


@contextlib.contextmanager
def measurement_lock(stage1):
    """Share a nonblocking measurement lock with the sequential demo harness."""
    path = Path(stage1).parent / "measurement.lock"
    with path.open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("another crop or demo measurement holds measurement.lock") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


class ReadOnlySam3(embedding_run.CachedSam3):
    """Retain the raw cache answer, including actual sent-image dimensions."""

    def __init__(self):
        super().__init__(endpoint=os.environ.get("SAM3_ENDPOINT") or derive.SAM3_ENDPOINT)

    def _send(self, data, form):
        raise derive.Sam3Unavailable("network_disabled")

    def _post(self, data, texts=derive.SAM3_TEXTS, return_masks=True):
        if not model_cache.READ:
            raise ValueError("SAM3 cache replay requires model_cache.READ=True")
        params = {"threshold": str(derive.SAM3_THRESHOLD),
                  "mask_threshold": str(derive.SAM3_MASK_THRESHOLD),
                  "return_masks": "true" if return_masks else "false"}
        fields = model_cache.request_fields(self.endpoint + "/segment_multi", derive.SAM3_MODEL,
                                            params, texts, [data])
        path = Path(model_cache.path_of(fields))
        if not path.exists():
            raise derive.Sam3Unavailable("missing_cache")
        record = model_cache.lookup(fields)
        if record is None or not isinstance(record.get("answer"), dict):
            raise derive.Sam3Unavailable("invalid_cache")
        self.answer = record["answer"]
        instances = self.answer.get("instances")
        if not isinstance(instances, list) or any(not isinstance(item, dict) for item in instances):
            raise derive.Sam3Unavailable("invalid_cache")
        self.cache_identity = {"key": model_cache.key_of(fields),
                               "answer_sha256": hashlib.sha256(
                                   model_cache.canonical(self.answer).encode()).hexdigest()}
        return self.answer


@contextlib.contextmanager
def cache_reads():
    old = model_cache.READ
    model_cache.READ = True
    try:
        yield
    finally:
        model_cache.READ = old


def rectangle(box, original, sent=None, margin=0):
    """Map a finite rectangle with separate x/y ratios, grow, round, and clamp it."""
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        raise ValueError("invalid_box")
    try:
        left, top, right, bottom = map(float, box)
        width, height = original
        sw, sh = sent or original
        if (not all(math.isfinite(v) for v in (left, top, right, bottom, sw, sh))
                or sw <= 0 or sh <= 0 or right <= left or bottom <= top):
            raise ValueError("invalid_box")
        left, right = left * width / sw, right * width / sw
        top, bottom = top * height / sh, bottom * height / sh
        mx, my = (right - left) * margin, (bottom - top) * margin
        out = [max(0, math.floor(left - mx)), max(0, math.floor(top - my)),
               min(width, math.ceil(right + mx)), min(height, math.ceil(bottom + my))]
        if out[2] <= out[0] or out[3] <= out[1]:
            raise ValueError("invalid_box")
        return out
    except (TypeError, OverflowError) as exc:
        raise ValueError("invalid_box") from exc


def unavailable(reason, **fields):
    return {"status": reason, "boxes": [], **fields}


def detected_boxes(answer, noun, size, margin=0):
    sent = (answer.get("width"), answer.get("height"))
    try:
        if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in sent):
            return unavailable("invalid_answer_dimensions")
    except TypeError:
        return unavailable("invalid_answer_dimensions")
    candidates, invalid = [], 0
    instances = [i for i in answer.get("instances", []) if isinstance(i, dict) and i.get("label") == noun]
    for item in instances:
        try:
            box = rectangle(item.get("box"), size, sent, margin)
            score = float(item.get("score") or 0)
            score = score if math.isfinite(score) else 0
            candidates.append((box, score))
        except (ValueError, TypeError):
            invalid += 1
    candidates.sort(key=lambda value: (-((value[0][2] - value[0][0]) *
                                          (value[0][3] - value[0][1])), -value[1], value[0]))
    boxes = [box for box, _score in candidates]
    if noun == alternatives.BOTTLE_NOUN:
        boxes = boxes[:1]
    return {"status": "available" if boxes else "invalid_box" if invalid else "missing_detection",
            "boxes": boxes, "detections": len(instances), "invalid_boxes": invalid}


def prepare_one(row, client=None):
    """Prepare one unique original, with no scan or production cache mutation."""
    started = time.perf_counter()
    out = {"image_sha256": row["image_sha256"], "path": row["path"], "regions": {}}
    try:
        if digest_file(row["path"]) != row["image_sha256"]:
            raise ValueError("source_digest_changed")
        image, _ = derive.open_image(row["path"])
    except (OSError, ValueError) as exc:
        out.update(error=str(exc), prep_ms=round((time.perf_counter() - started) * 1000, 3))
        out["regions"] = {name: unavailable("source_error") for name in REGIONS}
        return out
    out["size"] = list(image.size)
    box = row.get("package_box")
    try:
        out["regions"]["package"] = ({"status": "available", "boxes": [rectangle(box, image.size)]}
                                       if box is not None else unavailable("missing_baseline_box"))
    except ValueError:
        out["regions"]["package"] = unavailable("invalid_box")
    client = client or ReadOnlySam3()
    sam_started = time.perf_counter()
    try:
        with cache_reads():
            instances, _scale = client.instances(image, alternatives.DETECT_TEXTS)
        answer = client.answer
        if (not isinstance(answer, dict) or not isinstance(instances, list)
                or any(not isinstance(item, dict) for item in instances)):
            raise derive.Sam3Unavailable("invalid_cache")
        out["cache"] = client.cache_identity
        out["answer_size"] = [answer.get("width"), answer.get("height")]
        out["regions"]["bottle"] = detected_boxes(answer, alternatives.BOTTLE_NOUN, image.size)
        out["regions"]["barcode"] = detected_boxes(answer, alternatives.BARCODE_NOUN,
                                                    image.size, BARCODE_MARGIN)
        try:
            cut = alternatives.label_cut_of(image, instances)
            out["regions"]["label"] = ({"status": "available", "boxes": [rectangle(cut[2], image.size)],
                                         "method": cut[0]} if cut else unavailable("missing_detection"))
        except (ValueError, TypeError, KeyError, OSError, AttributeError) as exc:
            out["regions"]["label"] = unavailable("invalid_label", error=str(exc))
    except derive.Sam3Unavailable as exc:
        reason = str(exc) if str(exc) in ("missing_cache", "invalid_cache") else "invalid_cache"
        for name in ("bottle", "barcode", "label"):
            out["regions"][name] = unavailable(reason, error=str(exc))
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        for name in ("bottle", "barcode", "label"):
            out["regions"][name] = unavailable("invalid_cache", error=str(exc))
    finally:
        image.close()
    out["cache_replay_and_label_ms"] = round((time.perf_counter() - sam_started) * 1000, 3)
    out["prep_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return out


def scan_prepared(prepared, variant, options, lookup, factory=base.MeasuredDecoder):
    """Read each region in order. Stop only after a unique lookup match."""
    region = variant.removeprefix("whole-")
    fallback = variant.startswith("whole-")
    record = prepared["regions"][region]
    boxes = record["boxes"]
    result = {"image_sha256": prepared["image_sha256"], "variant": variant,
              "region_status": record["status"], "available": record["status"] == "available",
              "region_boxes": boxes, "call_budget": 2 * (len(boxes) + int(fallback)),
              "prep_ms": prepared["prep_ms"], "calls": 0, "decode_errors": 0,
              "codes": [], "hit": None, "error": None, "load_ms": 0.0,
              "scan_ms": 0.0, "wall_ms": 0.0, "regions_scanned": 0}
    if prepared.get("error"):
        result["error"] = prepared["error"]
        return result
    if not boxes and not fallback:
        return result
    decoder = factory(dict(options, tile_scan=False))
    started = time.perf_counter()
    image = None
    try:
        load_started = time.perf_counter()
        image, _ = derive.open_image(prepared["path"])
        result["load_ms"] += (time.perf_counter() - load_started) * 1000
        for box in ([None] if fallback else []) + boxes:
            load_started = time.perf_counter()
            part = image.crop(box) if box is not None else image
            result["load_ms"] += (time.perf_counter() - load_started) * 1000
            scan_started = time.perf_counter()
            found = decoder.read(decoder.scaled(part))
            result["codes"] = base.barcode._dedupe(result["codes"] + found)
            result["hit"] = lookup.find(result["codes"])
            result["scan_ms"] += (time.perf_counter() - scan_started) * 1000
            result["regions_scanned"] += 1
            if part is not image:
                part.close()
            if base.barcode.is_unique(result["hit"]):
                break
    except Exception as exc:
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
    finally:
        if image is not None:
            image.close()
    result.update(calls=decoder.calls, decode_errors=decoder.decode_errors,
                  wall_ms=round((time.perf_counter() - started) * 1000, 3))
    for key in ("load_ms", "scan_ms"):
        result[key] = round(result[key], 3)
    return result


def compare(row, measured):
    hit, baseline = measured["hit"], row["baseline_step"].get("out", {}).get("hit")
    unique, was_unique = base.barcode.is_unique(hit), base.barcode.is_unique(baseline)
    truth, label = row.get("truth") or [], row.get("label")
    correct = bool(label == "positive" and unique and hit["slugs"][0] in truth)
    wrong = None
    if unique:
        if label == "positive":
            wrong = not correct
        elif label == "negative":
            wrong = True if hit["slugs"][0] in set(truth or [row.get("slug")]) else None
        elif label == "no_match":
            wrong = True
    return dict(measured, query_id=row["query_id"], label=label, truth=truth,
                baseline_hit=baseline, baseline_eligible=not row["baseline_step"].get("error"),
                match="unique" if unique else "shared" if hit else "miss",
                truth_correct=correct, truth_wrong=wrong,
                baseline_truth_correct=bool(label == "positive" and was_unique and baseline["slugs"][0] in truth),
                same_match=base.signature(hit) == base.signature(baseline),
                lost_baseline_hit=baseline is not None and hit is None,
                conflict=bool(was_unique and unique and baseline["slugs"] != hit["slugs"]))


def distribution(values):
    result = base.distribution(values)
    return dict(result, p50=result["median"])


def summary(records, unique):
    counts = Counter(r["match"] for r in records)
    eligible = [r for r in records if r["baseline_eligible"] and r["label"] == "positive"]
    measured = [r for r in unique if r["regions_scanned"]]
    by_image = defaultdict(list)
    for row in records:
        by_image[row["image_sha256"]].append(row)
    return {"query_rows": len(records), "unique_images": len(unique),
            "measured_unique_images": len(measured), "match_rows": dict(counts),
            "match_unique": dict(Counter("unique" if base.barcode.is_unique(r["hit"]) else "shared" if r["hit"] else "miss" for r in unique)),
            "region_status_rows": dict(Counter(r["region_status"] for r in records)),
            "region_status_unique": dict(Counter(r["region_status"] for r in unique)),
            "truth_correct_rows": sum(r["truth_correct"] for r in records),
            "truth_wrong_rows": sum(r["truth_wrong"] is True for r in records),
            "positive_query_rows": sum(r["label"] == "positive" for r in records),
            "unique_images_with_positive_query": sum(any(r["label"] == "positive" for r in rs) for rs in by_image.values()),
            "unique_images_with_correct_positive_query": sum(any(r["truth_correct"] for r in rs) for rs in by_image.values()),
            "unique_images_with_wrong_labeled_query": sum(any(r["truth_wrong"] is True for r in rs) for rs in by_image.values()),
            "same_match_rows": sum(r["same_match"] for r in records),
            "same_match_unique": sum(all(r["same_match"] for r in rs) for rs in by_image.values()),
            "baseline_hit_rows": sum(r["baseline_hit"] is not None for r in records),
            "baseline_hit_unique": sum(any(r["baseline_hit"] is not None for r in rs) for rs in by_image.values()),
            "lost_baseline_hit_rows": sum(r["lost_baseline_hit"] for r in records),
            "lost_baseline_hit_unique": sum(any(r["lost_baseline_hit"] for r in rs) for rs in by_image.values()),
            "conflict_rows": sum(r["conflict"] for r in records),
            "paired_positive_rows": len(eligible),
            "paired_correct_delta": sum(int(r["truth_correct"]) - int(r["baseline_truth_correct"]) for r in eligible),
            "paired_gained_rows": sum(r["truth_correct"] and not r["baseline_truth_correct"] for r in eligible),
            "paired_lost_rows": sum(not r["truth_correct"] and r["baseline_truth_correct"] for r in eligible),
            "native_calls": sum(r["calls"] for r in unique),
            "error_unique_images": sum(bool(r["error"] or r["decode_errors"]) for r in unique),
            "scan_ms_unique": distribution([r["scan_ms"] for r in measured]),
            "wall_ms_unique": distribution([r["wall_ms"] for r in measured]),
            "load_ms_unique": distribution([r["load_ms"] for r in measured]),
            "scan_ms_row_weighted": distribution([r["scan_ms"] for r in records if r["regions_scanned"]]),
            "prep_ms_unique": distribution([r["prep_ms"] for r in unique]),
            "barcode_over_3s_unique": sum(r["wall_ms"] > base.DEADLINE_MS for r in measured),
            "barcode_within_3s_share": sum(r["wall_ms"] <= base.DEADLINE_MS for r in measured) / len(measured) if measured else None,
            "note": "Each unique image is scanned once. Row-weighted times are projections, not bulk throughput. Prep time covers all four regions together. Cached SAM3 preparation and barcode time do not measure full new-photo recognition."}


def grouped_rows(rows, run_dir):
    results = {r["query_id"]: r for r in base.read_jsonl(Path(run_dir) / "results.jsonl")}
    groups = {}
    for row in rows:
        unique = groups.setdefault(row["image_sha256"], dict(row, package_box=None))
        step = next((s for s in (results[row["query_id"]].get("trace") or {}).get("steps", [])
                     if s.get("id") == "sam3-package"), {})
        box = (step.get("out") or {}).get("box")
        if box is not None:
            if unique["package_box"] is not None and unique["package_box"] != box:
                raise ValueError("baseline package boxes differ for a repeated image")
            unique["package_box"] = box
    return list(groups.values())


def check_manifest(output, identity, resume):
    path = output / "manifest.json"
    if path.exists():
        if not resume or json.loads(path.read_text()) != identity:
            raise ValueError("resume needs the same selection, sources, lookup and settings")
    elif resume:
        raise ValueError("resume needs an existing crop benchmark manifest")
    elif output.exists() and any(output.iterdir()):
        raise ValueError("new crop output directory MUST be empty")
    output.mkdir(parents=True, exist_ok=True)
    base.save_json(path, identity)


def verify_source(row):
    if digest_file(row["path"]) != row["image_sha256"]:
        raise ValueError("source digest changed for %s" % row["image_sha256"])


def require_lookup(lookup, stage1_manifest):
    snapshot = [[kind, code, slugs] for (kind, code), slugs in sorted(lookup.values.items())]
    if snapshot != stage1_manifest.get("lookup"):
        raise ValueError("barcode lookup differs from stage 1; crop gains cannot be compared")
    return snapshot


def preparation_index(directory, selected):
    """Verify every frozen geometry file. Refuse an unindexed interrupted write."""
    path = directory.parent / "preparation.index.json"
    present = {p.stem for p in directory.glob("*.json")}
    if path.exists():
        index = json.loads(path.read_text())
        if (not isinstance(index, dict) or index.get("selected") != selected
                or not isinstance(index.get("records"), dict)):
            raise ValueError("preparation index has a different selection or invalid records")
        records = index["records"]
        if set(records) != present or set(records) - set(selected):
            raise ValueError("unindexed or missing frozen preparation file; preserve it and use a new output")
        if any(digest_file(directory / (key + ".json")) != digest for key, digest in records.items()):
            raise ValueError("frozen preparation file changed")
        if index.get("complete") != (set(records) == set(selected)):
            raise ValueError("preparation index has an invalid completion state")
        return index
    if present:
        raise ValueError("unindexed frozen preparation files; preserve them and use a new output")
    index = {"selected": selected, "records": {}, "complete": not selected}
    base.save_json(path, index)
    return index


def freeze_preparation(directory, record, index):
    key = record["image_sha256"]
    if key not in index["selected"] or key in index["records"]:
        raise ValueError("preparation can only add an unfinished selected image")
    path = directory / (key + ".json")
    if path.exists():
        raise ValueError("refuse to overwrite an unindexed preparation file")
    base.save_json(path, record)
    index["records"][key] = digest_file(path)
    index["complete"] = set(index["records"]) == set(index["selected"])
    base.save_json(directory.parent / "preparation.index.json", index)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline-run", "baseline-log", "stage1", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--images-dir", type=Path, default=base.ROOT / "data" / "images")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--variants", default=",".join(VARIANTS))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        meta = base.require_finished(args.baseline_run, args.baseline_log)
        all_rows = base.load_photos(args.baseline_run, args.images_dir)
        if len(all_rows) != meta["answered"] or len(all_rows) != meta["query_set"]["total"]:
            raise ValueError("baseline MUST cover every query")
        gate = require_stage1(args.stage1, [r["query_id"] for r in all_rows], args.baseline_run)
        if gate["manifest"]["baseline"] != str(args.baseline_run.resolve()):
            raise ValueError("stage 1 belongs to another baseline")
        for name, digest in gate["manifest"]["files"].items():
            if digest_file(args.baseline_run / name) != digest:
                raise ValueError("baseline differs from stage 1")
        if args.limit is not None and args.limit < 1:
            raise ValueError("limit MUST be positive")
        variants = args.variants.split(",")
        if len(set(variants)) != len(variants) or any(v not in VARIANTS for v in variants):
            raise ValueError("unknown or repeated crop variant")
        rows = all_rows[:args.limit] if args.limit else all_rows
        originals = grouped_rows(rows, args.baseline_run)
        output = args.output.resolve()
        for protected in (Path(model_cache.ROOT), args.baseline_run, args.images_dir, args.stage1):
            protected = protected.resolve()
            if output == protected or output in protected.parents or protected in output.parents:
                raise ValueError("output MUST be separate from source images, runs, stage 1 and production cache")
        options = base.barcode.check_options({k: v for k, v in meta["backend"]["barcode"].items() if k in base.barcode.DEFAULTS})
        lookup = base.barcode.CodeLookup.load(meta["options"]["database"])
        lookup_snapshot = require_lookup(lookup, gate["manifest"])
        cache_root = Path(model_cache.ROOT) / derive.SAM3_MODEL
        sources = [Path(__file__), Path(base.__file__), Path(derive.__file__), Path(alternatives.__file__),
                   Path(base.barcode.__file__), Path(model_cache.__file__), Path(embedding_run.__file__)]
        identity = {"revision": REVISION, "baseline": gate["manifest"]["files"],
                    "stage1_manifest": digest_file(args.stage1 / "manifest.json"),
                    "query_ids": [r["query_id"] for r in rows], "variants": variants,
                    "images_dir": str(args.images_dir.resolve()), "options": options,
                    "sources": {str(p.relative_to(base.ROOT)): digest_file(p) for p in sources},
                    "zxing": base.barcode.version(base.barcode.ENGINE), "pillow": base.barcode.PILLOW_VERSION,
                    "sam3": {"endpoint": os.environ.get("SAM3_ENDPOINT") or derive.SAM3_ENDPOINT, "texts": alternatives.DETECT_TEXTS,
                             "max_side": derive.SAM3_MAX_SIDE, "label_rule": alternatives.SETTINGS_LABEL},
                    "sam3_cache_root": str(cache_root.resolve()),
                    "lookup": lookup_snapshot,
                    "barcode_margin_per_side": BARCODE_MARGIN, "barcode_rectangle_cap": None,
                    "rectangle_order": "area descending, score descending, coordinates ascending"}
        with measurement_lock(args.stage1):
            require_stage1(args.stage1, [r["query_id"] for r in all_rows], args.baseline_run)
            check_manifest(output, identity, args.resume)
            prepared_dir = output / "prepared"
            prepared_dir.mkdir(exist_ok=True)
            index = preparation_index(prepared_dir, [row["image_sha256"] for row in originals])
            prepared = {}
            for number, row in enumerate(originals, 1):
                verify_source(row)
                path = prepared_dir / (row["image_sha256"] + ".json")
                saved = row["image_sha256"] in index["records"]
                record = json.loads(path.read_text()) if saved else prepare_one(row)
                if record["image_sha256"] != row["image_sha256"] or record["path"] != row["path"]:
                    raise ValueError("preparation checkpoint has a different source")
                if not saved:
                    freeze_preparation(prepared_dir, record, index)
                prepared[row["image_sha256"]] = record
                if number % 25 == 0:
                    print(json.dumps({"stage": "prepare", "unique_done": number, "unique_total": len(originals)}), flush=True)
            base.save_json(output / "preparation.summary.json", {
                "query_rows": len(rows), "unique_images": len(prepared),
                "prep_ms_unique": distribution([p["prep_ms"] for p in prepared.values()]),
                "region_status_unique": {r: dict(Counter(p["regions"][r]["status"] for p in prepared.values())) for r in REGIONS}})
            if args.prepare_only:
                require_lookup(base.barcode.CodeLookup.load(meta["options"]["database"]), gate["manifest"])
                return 0
            for variant in variants:
                path = output / (variant + ".unique.jsonl")
                existing = base.records_for_resume(path) if args.resume else []
                by_digest = {r["image_sha256"]: r for r in existing}
                if (len(by_digest) != len(existing) or set(by_digest) - set(prepared)
                        or any(r.get("variant") != variant for r in existing)):
                    raise ValueError("invalid unique result checkpoint")
                with path.open("a" if args.resume else "w") as stream:
                    for digest, record in prepared.items():
                        if digest not in by_digest:
                            by_digest[digest] = scan_prepared(record, variant, options, lookup)
                            stream.write(json.dumps(by_digest[digest], ensure_ascii=False) + "\n")
                            stream.flush()
                            if len(by_digest) % 25 == 0:
                                print(json.dumps({"variant": variant, "unique_done": len(by_digest),
                                                  "unique_total": len(prepared)}), flush=True)
                records = [compare(row, by_digest[row["image_sha256"]]) for row in rows]
                (output / (variant + ".jsonl")).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
                result = summary(records, list(by_digest.values()))
                base.save_json(output / (variant + ".summary.json"), result)
                print(json.dumps({"variant": variant, "summary": result}), flush=True)
            require_lookup(base.barcode.CodeLookup.load(meta["options"]["database"]), gate["manifest"])
            base.save_json(output / "completion.json", {"complete": True, "variants": variants,
                "lookup_sha256": hashlib.sha256(model_cache.canonical(lookup_snapshot).encode()).hexdigest(),
                "preparation_index_sha256": digest_file(output / "preparation.index.json")})
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print("crop benchmark refused: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
