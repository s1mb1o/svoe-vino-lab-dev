"""Read bulk benchmark artifacts. Write reports only through an explicit CLI call.

This module uses the standard library only. It does not read images, import pipeline
code, inspect processes, launch jobs, or call services. The parent task MUST verify
live PID commands. Recorded supervisor metadata does not verify a live process.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
import json
from pathlib import Path
import statistics


VARIANTS = ("cold-1", "warm-1", "cold-4", "warm-4")
QUERY_KEYS = ("query_id", "image_path", "image_sha256", "slug", "label", "truth")
EXPECTED_ROWS = 2228
EXPECTED_DIGESTS = 1851


def read_json(path, issues):
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError("expected an object")
        return value
    except (OSError, ValueError) as exc:
        issues.append("Cannot read %s: %s" % (path, exc))
        return None


def read_rows(path, issues):
    """Keep valid records. Report a partial final line without changing the file."""
    rows, duplicate_ids = {}, []
    if not path.exists():
        return rows
    try:
        with path.open() as stream:
            for number, line in enumerate(stream, 1):
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict) or not isinstance(row.get("query_id"), str):
                        raise ValueError("missing string query_id")
                    key = row["query_id"]
                    if key in rows:
                        duplicate_ids.append(key)
                    else:
                        rows[key] = row
                except ValueError as exc:
                    issues.append("Invalid record in %s at line %d: %s" % (path, number, exc))
    except OSError as exc:
        issues.append("Cannot read %s: %s" % (path, exc))
    for key in sorted(set(duplicate_ids)):
        rows.pop(key, None)  # An ambiguous query must not enter a paired comparison.
    if duplicate_ids:
        issues.append("Duplicate query IDs in %s: %s" % (path, sorted(set(duplicate_ids))))
    return rows


def query_identity(row):
    return {key: row.get(key) for key in QUERY_KEYS}


def distribution(values):
    values = sorted(v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool))
    if not values:
        return {"n": 0}
    return {"n": len(values), "median": statistics.median(values),
            "p95": values[min(len(values) - 1, int(0.95 * len(values)))], "max": values[-1]}


def observed_stats(rows):
    """Report observed rows only. Completion is a separate decision."""
    steps = [next((s for s in (r.get("trace") or {}).get("steps", [])
                   if s.get("id") == "barcode"), {}) for r in rows.values()]
    positive = [r for r in rows.values() if r.get("label") == "positive"]
    hits = lambda n: sum(isinstance(r.get("rank_of_truth"), int)
                         and 1 <= r["rank_of_truth"] <= n for r in positive)
    return {"rows": len(rows),
            "unique_image_digests": len({r.get("image_sha256") for r in rows.values()
                                          if r.get("image_sha256")}),
            "errors": sum(bool(r.get("error")) for r in rows.values()),
            "degraded_rows": sum(any(s.get("error") or (s.get("out") or {}).get("error")
                                      for s in (r.get("trace") or {}).get("steps", []))
                                  for r in rows.values()),
            "barcode_errors": sum(bool(s.get("error")) for s in steps),
            "barcode_cache_hits": sum(s.get("cached") is True for s in steps),
            "barcode_cache_misses": sum(s.get("cached") is False for s in steps),
            "barcode_cache_unknown": sum("cached" not in s for s in steps),
            "outcomes": dict(sorted(Counter(r.get("outcome", "unknown") for r in rows.values()).items())),
            "positive_rows": len(positive), "positive_top1": hits(1), "positive_top5": hits(5),
            "latency_ms": distribution([r.get("latency_ms") for r in rows.values()]),
            "barcode_ms": distribution([s.get("ms") for s in steps])}


def inspect_run(directory, reference=None):
    issues = []
    for name in ("run.json", "metrics.json", "queries.jsonl", "results.jsonl", "predictions.jsonl"):
        if not (directory / name).is_file():
            issues.append("Missing artifact: %s" % (directory / name))
    meta = read_json(directory / "run.json", issues)
    metrics = read_json(directory / "metrics.json", issues)
    queries = read_rows(directory / "queries.jsonl", issues)
    results = read_rows(directory / "results.jsonl", issues)
    predictions = read_rows(directory / "predictions.jsonl", issues)
    expected = reference if reference is not None else queries
    changed_queries = sorted(k for k in expected.keys() & queries.keys()
                             if query_identity(expected[k]) != query_identity(queries[k]))
    changed_results = sorted(k for k in expected.keys() & results.keys()
                             if query_identity(expected[k]) != query_identity(results[k]))
    mismatched_predictions = sorted(k for k in results.keys() & predictions.keys()
                                    if any(results[k].get(field) != predictions[k].get(field)
                                           for field in ("image_path", "image_sha256", "predicted_slug")))
    coverage = {"query_rows": len(queries), "result_rows": len(results),
                "prediction_rows": len(predictions),
                "query_unique_image_digests": len({r.get("image_sha256") for r in queries.values()
                                                  if r.get("image_sha256")}),
                "missing_query_ids": sorted(expected.keys() - queries.keys()),
                "extra_query_ids": sorted(queries.keys() - expected.keys()),
                "missing_result_ids": sorted(expected.keys() - results.keys()),
                "extra_result_ids": sorted(results.keys() - expected.keys()),
                "missing_prediction_ids": sorted(expected.keys() - predictions.keys()),
                "extra_prediction_ids": sorted(predictions.keys() - expected.keys()),
                "changed_query_ids": changed_queries, "changed_result_ids": changed_results,
                "mismatched_prediction_ids": mismatched_predictions}
    coverage["complete"] = bool(expected) and not issues and not any(
        value for key, value in coverage.items() if key.endswith("_ids"))
    eligible = {k: r for k, r in results.items() if k in expected
                and query_identity(r) == query_identity(expected[k])}
    return {"run_dir": str(directory), "run": meta, "metrics": metrics,
            "coverage": coverage, "observed": observed_stats(results), "issues": issues}, queries, eligible


def decision(row):
    candidates = row.get("candidates") or []
    return {"predicted_slug": row.get("predicted_slug"),
            "candidate_slugs": [c.get("slug") for c in candidates],
            "candidate_ranks": [[c.get("slug"), c.get("rank")] for c in candidates],
            "top5_slugs": [c.get("slug") for c in candidates[:5]],
            "rank_of_truth": row.get("rank_of_truth"), "outcome": row.get("outcome"),
            "error": row.get("error")}


def compare(left_name, left, right_name, right, expected_rows, full=False):
    common = sorted(left.keys() & right.keys())
    fields = tuple(decision({}))
    changed = {field: [] for field in fields}
    details = []
    for key in common:
        a, b = decision(left[key]), decision(right[key])
        differences = [field for field in fields if a[field] != b[field]]
        for field in differences:
            changed[field].append(key)
        if differences:
            details.append({"query_id": key, "changed_fields": differences, "left": a, "right": b})
    return {"left": left_name, "right": right_name,
            "scope": "complete paired runs" if full and len(common) == expected_rows else "partial matched rows only",
            "matched_rows": len(common), "expected_rows": expected_rows,
            "changed_counts": {field: len(keys) for field, keys in changed.items()},
            "changed_query_ids": changed, "differences": details}


def inspect_variant(name, bulk_dir, supervisor_dir, runs_dir, queries, expected_rows, expected_digests):
    issues = []
    summary = read_json(bulk_dir / (name + ".summary.json"), issues)
    intent = read_json(bulk_dir / (name + ".intent.json"), issues)
    supervisor = read_json(supervisor_dir / ("bulk-" + name + "-process.json"), issues)
    summary, intent, supervisor = summary or {}, intent or {}, supervisor or {}
    run_ids = {v for v in (summary.get("run_id"), intent.get("run_id"), supervisor.get("run_id")) if v}
    if len(run_ids) > 1:
        issues.append("Recorded run IDs disagree.")
    run_id = intent.get("run_id") or summary.get("run_id") or supervisor.get("run_id")
    if run_id and (Path(run_id).name != run_id or run_id in (".", "..")):
        issues.append("Recorded run ID is not a directory name.")
        run_id = None
    result, answers = None, {}
    if run_id:
        result, _, answers = inspect_run(runs_dir / run_id, queries)
        issues.extend(result["issues"])
        if (result["run"] or {}).get("run_id") not in (None, run_id):
            issues.append("run.json identifies a different run.")
        if summary.get("run_dir") and Path(summary["run_dir"]).resolve() != (runs_dir / run_id).resolve():
            issues.append("Summary run directory differs from the selected run.")
    meta = (result or {}).get("run") or {}
    observed = (result or {}).get("observed") or observed_stats({})
    if intent.get("pid") and supervisor.get("pid") and intent["pid"] != supervisor["pid"]:
        issues.append("Intent and supervisor PIDs differ.")
    for key, measured in (("queries", observed["rows"]), ("unique_images", observed["unique_image_digests"]),
                          ("errors", observed["errors"]), ("degraded_queries", observed["degraded_rows"]),
                          ("barcode_cache_hits", observed["barcode_cache_hits"])):
        if summary and summary.get(key) != measured:
            issues.append("Summary %s differs from persisted results." % key)
    terminal = supervisor.get("state") == "exited" and supervisor.get("exit_code") is not None
    complete = bool(summary.get("complete") is True and intent.get("status") == "done"
                    and intent.get("finished") and terminal and supervisor.get("exit_code") == 0
                    and supervisor.get("ended_at") and meta.get("finished")
                    and meta.get("answered") == expected_rows and result
                    and result["coverage"]["complete"] and observed["rows"] == expected_rows
                    and observed["unique_image_digests"] == expected_digests and not issues
                    and summary.get("native_errors") == 0 and summary.get("input_drift") is False
                    and not (observed["errors"] or observed["degraded_rows"]
                             or observed["barcode_cache_unknown"] or summary.get("warm_cache_misses")))
    if name.startswith("warm-") and observed["barcode_cache_hits"] != expected_rows:
        complete = False
    if complete:
        state = "complete"
    elif not (summary or intent or supervisor or result or issues):
        state = "missing"
    elif (supervisor.get("state") == "supervisor_error" or (terminal and supervisor.get("exit_code") != 0)
          or intent.get("status") == "errors" or summary.get("complete") is False):
        state = "failed"
    elif supervisor.get("state") == "running":
        state = "recorded_running"
    else:
        state = "incomplete"
    harness_wall = summary.get("wall_s")
    process_wall = supervisor.get("process_wall_s") if terminal else None
    positive = lambda value: isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0
    timing = {"harness_wall_s": harness_wall, "process_wall_s": process_wall,
              "backend_build_ms": summary.get("build_ms"), "benchmark_loop_wall_s": meta.get("wall_s"),
              "outside_harness_wall_s": (process_wall - harness_wall
                                          if positive(process_wall) and positive(harness_wall) else None),
              "complete_queries_per_harness_s": expected_rows / harness_wall
                                                  if complete and positive(harness_wall) else None,
              "complete_queries_per_process_s": expected_rows / process_wall
                                                  if complete and positive(process_wall) else None,
              "note": "Process wall includes child launch, imports, validation, hashing, report writes, and cleanup. Its difference from harness wall is not pure startup time."}
    first_key = next((key for key in queries if key in answers), None)
    first = answers.get(first_key) or {}
    timing["first_observed_query"] = ({"query_id": first_key, "latency_ms": first.get("latency_ms"),
                                      "embedding_steps_ms": [s.get("ms") for s in
                                          (first.get("trace") or {}).get("steps", []) if s.get("id") == "embed"]}
                                     if first_key else None)
    return {"variant": name, "state": state, "complete": complete,
            "metrics_scope": "complete run" if complete else "partial or unverified artifacts",
            "run_id": run_id, "intent": intent, "summary": summary, "supervisor": supervisor,
            "artifact_inspection": result, "observed": observed, "timing": timing,
            "native_calls": summary.get("native_calls"), "native_errors": summary.get("native_errors"),
            "issues": issues, "supervisor_terminal_recorded": terminal}, answers


def build_report(baseline_run, bulk_dir, supervisor_dir, runs_dir,
                 expected_rows=EXPECTED_ROWS, expected_digests=EXPECTED_DIGESTS):
    baseline, queries, baseline_answers = inspect_run(Path(baseline_run))
    baseline_meta = baseline["run"] or {}
    baseline["complete"] = bool(baseline["coverage"]["complete"] and baseline_meta.get("finished")
                                and baseline_meta.get("answered") == expected_rows
                                and len(queries) == expected_rows
                                and baseline["coverage"]["query_unique_image_digests"] == expected_digests)
    variants, answers, comparisons = [], {}, []
    for name in VARIANTS:
        item, rows = inspect_variant(name, Path(bulk_dir), Path(supervisor_dir), Path(runs_dir),
                                     queries, expected_rows, expected_digests)
        if not baseline["complete"] and item["complete"]:
            item.update(complete=False, state="incomplete", metrics_scope="partial or unverified artifacts")
            item["issues"].append("Baseline coverage or terminal artifacts are incomplete.")
            item["timing"]["complete_queries_per_harness_s"] = None
            item["timing"]["complete_queries_per_process_s"] = None
        variants.append(item)
        answers[name] = rows
        if rows:
            comparisons.append(compare("baseline", baseline_answers, name, rows, expected_rows,
                                       baseline["complete"] and item["complete"]))
    completed = [item["variant"] for item in variants if item["complete"]]
    for a, b in combinations(completed, 2):
        comparisons.append(compare(a, answers[a], b, answers[b], expected_rows, True))
    observation_issues = []
    startup_observation = read_json(Path(supervisor_dir) / "bulk-startup-observation.json", observation_issues)
    return {"generated_at": datetime.now(timezone.utc).isoformat(),
            "expected_query_rows": expected_rows, "expected_unique_image_digests": expected_digests,
            "baseline": baseline, "variants": variants, "comparisons": comparisons,
            "all_variants_complete": len(completed) == len(VARIANTS),
            "startup_observation": startup_observation, "startup_observation_issues": observation_issues,
            "process_verification": "This report reads recorded metadata only. The parent task MUST verify actual PID commands before any launch or retry.",
            "caveats": ["Artifacts can change while a run is active. Partial observations are not complete-run metrics.",
                        "Bulk timings do not establish latency for a new demo image.",
                        "Cold barcode caches permit natural hits for repeated image digests.",
                        "Normal SAM3 and VLM response caches remain enabled. Query embeddings have no client response cache.",
                        "The first request can include remote model startup. Keep its full latency in total wall time. Its latency is not an isolated model-load duration.",
                        "Candidate scores are not compared. Prediction order, candidate ranks, truth ranks, outcomes, and errors are compared by query ID."]}


def markdown(report):
    def show(value):
        return "unavailable" if value is None else "%.3f" % value if isinstance(value, float) else str(value)
    lines = ["# Barcode bulk comparison", "", "Expected coverage: %d query rows and %d unique image digests."
             % (report["expected_query_rows"], report["expected_unique_image_digests"]), "",
             report["process_verification"], "",
             "| Variant | State | Observed rows | Digests | Errors | Degraded | Barcode hits | Native calls | Harness s | Process s |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for item in report["variants"]:
        stats, timing = item["observed"], item["timing"]
        lines.append("| %s |" % " | ".join(map(show, (item["variant"], item["state"], stats["rows"],
                     stats["unique_image_digests"], stats["errors"], stats["degraded_rows"],
                     stats["barcode_cache_hits"], item["native_calls"], timing["harness_wall_s"], timing["process_wall_s"])) ))
    lines += ["", "Rows from an incomplete run are partial observations. They are not complete-run metrics.", "",
              "| Left | Right | Scope | Matched rows | Prediction changes | Top-5 changes | Truth-rank changes | Outcome changes |",
              "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for item in report["comparisons"]:
        counts = item["changed_counts"]
        lines.append("| %s |" % " | ".join(map(str, (item["left"], item["right"], item["scope"],
                     item["matched_rows"], counts["predicted_slug"], counts["top5_slugs"],
                     counts["rank_of_truth"], counts["outcome"]))))
    lines += ["", "Process wall includes work outside harness timing. Do not interpret the difference as pure startup time.", ""]
    if not report["baseline"]["complete"]:
        lines += ["The baseline has incomplete or inconsistent artifacts.", ""]
    for item in report["variants"]:
        for issue in item["issues"]:
            lines.append("- %s: %s" % (item["variant"], issue.replace("\n", " ")))
    lines += ["", *["- " + value for value in report["caveats"]], ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-run", required=True, type=Path)
    parser.add_argument("--bulk-dir", required=True, type=Path)
    parser.add_argument("--supervisor-dir", type=Path)
    parser.add_argument("--runs-dir", type=Path)
    parser.add_argument("--expected-rows", type=int, default=EXPECTED_ROWS)
    parser.add_argument("--expected-digests", type=int, default=EXPECTED_DIGESTS)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.expected_rows < 1 or not 1 <= args.expected_digests <= args.expected_rows:
        parser.error("expected counts MUST be positive; digests MUST NOT exceed rows")
    targets = [args.output_json.resolve(), args.output_md.resolve()]
    if targets[0] == targets[1] or any(p.exists() for p in targets):
        parser.error("output paths MUST be distinct new files; existing artifacts are never overwritten")
    report = build_report(args.baseline_run, args.bulk_dir, args.supervisor_dir or args.bulk_dir.parent,
                          args.runs_dir or args.baseline_run.parent, args.expected_rows, args.expected_digests)
    for path, text in ((targets[0], json.dumps(report, indent=2, ensure_ascii=False) + "\n"),
                       (targets[1], markdown(report))):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x") as stream:
            stream.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
