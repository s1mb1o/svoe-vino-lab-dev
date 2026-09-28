"""Report saved HTTP experiments without importing the pipeline or calling a service.

Use --run DIR --selection FILE --output DIR. The output directory receives
http-comparison.json and http-comparison.md. Partial runs remain partial. Failed
observations stay in every applicable denominator. No hard timeout is inferred.
"""
import argparse
import collections
import hashlib
import json
import math
import statistics
from pathlib import Path

DEADLINE_MS = 3000
CONFLICT_IDS = {"q-000483", "q-000484"}
HIT_REASON = "baseline_barcode_hit"
SCOPE = "Loopback HTTP through complete response; excludes browser rendering and remote client network"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"))
                          .encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def distribution(values):
    values = sorted(values)
    if not values:
        return {"observations": 0, "median": None, "p95": None, "p99": None, "max": None}
    return {"observations": len(values), "median": statistics.median(values),
            "p95": values[math.ceil(len(values) * .95) - 1],
            "p99": values[math.ceil(len(values) * .99) - 1], "max": values[-1]}


def timing(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("timing MUST be a finite nonnegative number")
    return float(value)


def projection(row):
    return {key: row[key] for key in ("query_id", "image_sha256", "selection_reasons")}


def load_selection(path, manifest):
    frozen = read_json(path)
    selection, rows = frozen["selection"], frozen["rows"]
    if (digest(selection) != frozen["selection_fingerprint"]
            or manifest["selection"] != selection
            or manifest["selection_fingerprint"] != frozen["selection_fingerprint"]):
        raise ValueError("manifest does not match the frozen selection fingerprint")
    if [projection(row) for row in rows] != selection or len({r["query_id"] for r in rows}) != len(rows):
        raise ValueError("frozen rows do not match the unique selected query IDs")
    for name, expected in frozen["baseline_artifact_hashes"].items():
        if manifest["baseline_hashes"].get(name) != expected:
            raise ValueError("manifest baseline hashes differ from the frozen selection")
    for row in rows:
        if row.get("label") == "positive" and not row.get("truth"):
            raise ValueError("a positive frozen row has no truth")
    return frozen


def judge(record, selected):
    """Recompute verdicts. Do not trust precomputed deadline or correctness flags."""
    answer = record.get("answer") or {}
    candidates = answer.get("candidates") or []
    slugs = [c.get("slug") for c in candidates]
    truth = set(selected.get("truth") or [])
    top = slugs[0] if slugs else None
    wall = timing(record["client_wall_ms"])
    censored = bool(record.get("latency_censored") or record.get("transport_error")
                    or record.get("response_complete") is False)
    complete = record.get("response_complete") is True and not censored
    stage_errors = [step.get("error") or (step.get("out") or {}).get("error")
                    for step in (answer.get("trace") or {}).get("steps", [])]
    degraded = bool(record.get("degraded") or any(stage_errors) or answer.get("decode_errors")
                    or answer.get("sam3_failure_after") or (answer.get("crop_scan") or {}).get("error"))
    error = bool(record.get("error") or answer.get("error") or record.get("response_problems")
                 or record.get("transport_error") or not complete or record.get("http_status") != 200
                 or answer.get("http_status") != 200)
    valid = complete and not error and not degraded
    positive = selected.get("label") == "positive"
    correct = positive and bool(truth) and top in truth
    excluded = truth or ({selected["slug"]} if selected.get("slug") else set())
    forbidden = (bool(candidates) if selected.get("label") == "no_match" else
                 bool(candidates) and top in excluded if selected.get("label") == "negative" else False)
    return {"query_id": selected["query_id"], "image_sha256": selected["image_sha256"],
            "positive": positive, "complete_response": complete, "censored": censored,
            "error": error, "degraded": degraded, "valid_response": valid,
            "complete_within_3s": complete and wall <= DEADLINE_MS,
            "correct_within_3s": valid and correct and wall <= DEADLINE_MS,
            "correct_late": valid and correct and wall > DEADLINE_MS,
            "valid_correct": valid and correct, "top1_prediction_correct": correct,
            "top5_prediction_correct": positive and bool(truth.intersection(slugs[:5])),
            "negative_forbidden_top1": forbidden, "wall_ms": wall, "record": record}


def metric(selected, judged):
    positive = sum(row.get("label") == "positive" for row in selected)
    negative = sum(row.get("label") in ("negative", "no_match") for row in selected)
    within = sum(j["complete_within_3s"] for j in judged)
    correct = sum(j["correct_within_3s"] for j in judged)
    return {"selected_rows": len(selected), "selected_unique_images": len({r["image_sha256"] for r in selected}),
            "positive_denominator": positive, "negative_constraint_denominator": negative,
            "observed_rows": len(judged), "observed_positive_rows": sum(j["positive"] for j in judged),
            "pending_rows": len(selected) - len(judged),
            "complete_responses": sum(j["complete_response"] for j in judged),
            "successful_within_3s": sum(j["valid_response"] and j["wall_ms"] <= DEADLINE_MS for j in judged),
            "complete_within_3s": within, "complete_within_3s_share": within / len(selected) if selected else None,
            "correct_within_3s": correct, "correct_within_3s_share": correct / positive if positive else None,
            "correct_late": sum(j["correct_late"] for j in judged),
            "valid_correct_responses": sum(j["valid_correct"] for j in judged),
            "top1_prediction_correct": sum(j["top1_prediction_correct"] for j in judged),
            "top5_prediction_correct": sum(j["top5_prediction_correct"] for j in judged),
            "negative_forbidden_top1": sum(j["negative_forbidden_top1"] for j in judged),
            "negative_forbidden_top1_share": sum(j["negative_forbidden_top1"] for j in judged) / negative if negative else None,
            "errors": sum(j["error"] for j in judged), "degraded": sum(j["degraded"] for j in judged),
            "censored_rows": sum(j["censored"] for j in judged),
            "http_wait_all_attempts_ms": distribution([j["wall_ms"] for j in judged]),
            "complete_http_wall_ms": distribution([j["wall_ms"] for j in judged if j["complete_response"]])}


def child_timing(record, key):
    """Ignore route placeholders when no child answer or measured timing exists."""
    answer = record.get("answer") or {}
    telemetry = record.get("telemetry") or {}
    measured = (answer.get("event") == "answer" or key in telemetry
                or (key == "ask_wall_ms" and key in answer))
    value = record.get(key)
    return timing(value) if measured and value is not None else None


def components(records):
    result = {}
    for key in ("startup_ms", "build_ms", "ask_wall_ms"):
        values = [child_timing(r, key) for r in records]
        result[key] = distribution([value for value in values if value is not None])
        result[key]["missing_observations"] = values.count(None)
        result[key]["missing_query_ids"] = [r["query_id"] for r, value in zip(records, values)
                                             if value is None]
    for key in ("service_setup_ms", "source_read_ms", "json_parse_ms"):
        result[key] = distribution([timing(r[key]) for r in records if key in r])
    for key in ("upload_ms", "steps_answer_ms", "process_ms", "worker_request_ms", "cleanup_ms"):
        result[key] = distribution([timing(r["telemetry"][key]) for r in records if key in r.get("telemetry", {})])
    stages = sorted({name for record in records for name in record.get("stage_ms", {})})
    result["stage_ms"] = {name: distribution([timing(r["stage_ms"][name]) for r in records
                                            if name in r.get("stage_ms", {})]) for name in stages}
    crops = [r["answer"]["crop_scan"] for r in records if r.get("answer", {}).get("crop_scan")]
    result["fresh_crop"] = {"rows": len(crops),
                            "status_counts": dict(collections.Counter(c["status"] for c in crops)),
                            **{key: distribution([timing(c[key]) for c in crops if key in c])
                               for key in ("sam3_wall_ms", "sent_image_prepare_ms", "geometry_ms", "crop_decode_ms")}}
    return result


def summarize_session(path, mode, variant, frozen):
    rows = frozen["rows"]
    selected = {row["query_id"]: row for row in rows}
    records = []
    if path.exists():
        with path.open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError("invalid JSONL record %s:%d; no row was silently dropped" % (path, number)) from exc
    seen = set()
    for record in records:
        key = record["query_id"]
        if key in seen or key not in selected:
            raise ValueError("duplicate or unselected query ID in %s" % path.name)
        seen.add(key)
        row = selected[key]
        if (projection(record) != projection(row) or record.get("label") != row.get("label")
                or record.get("truth") != row.get("truth") or record.get("mode") != mode
                or record.get("variant") != variant or not isinstance(record.get("session_first"), bool)):
            raise ValueError("result identity or frozen labels differ: %s" % key)
    if records and records[0]["session_first"] is not True:
        raise ValueError("the first observation must include its session-first marker")
    judged = [judge(record, selected[record["query_id"]]) for record in records]
    first = [j for j in judged if j["record"]["session_first"]]
    steady = [j for j in judged if not j["record"]["session_first"]]
    strata = {}
    for name, predicate in (("baseline_barcode_hit", lambda r: HIT_REASON in r["selection_reasons"]),
                            ("other_selected_rows", lambda r: HIT_REASON not in r["selection_reasons"]),
                            ("positive", lambda r: r.get("label") == "positive"),
                            ("negative_constraint", lambda r: r.get("label") in ("negative", "no_match"))):
        keys = {r["query_id"] for r in rows if predicate(r)}
        strata[name] = metric([r for r in rows if r["query_id"] in keys], [j for j in judged if j["query_id"] in keys])
    sensitivity = [r for r in rows if r["query_id"] not in CONFLICT_IDS]
    failure_path = path.with_suffix(".failure.json")
    return {"mode": mode, "variant": variant, "coverage_complete": len(records) == len(rows),
            "full": metric(rows, judged), "strata": strata,
            "sensitivity_excluded_ids": sorted(CONFLICT_IDS.intersection(selected)),
            "sensitivity": metric(sensitivity, [j for j in judged if j["query_id"] not in CONFLICT_IDS]),
            "first_requests": [{"query_id": j["query_id"], "http_wall_ms": j["wall_ms"],
                                "startup_ms": child_timing(j["record"], "startup_ms"),
                                "build_ms": child_timing(j["record"], "build_ms"),
                                "service_setup_ms": j["record"].get("service_setup_ms"),
                                "censored": j["censored"]} for j in first],
            "after_session_first_observed": metric([selected[j["query_id"]] for j in steady], steady),
            "components_all_observed": components(records),
            "components_after_session_first": components([j["record"] for j in steady]),
            "observations": [{key: value for key, value in j.items() if key != "record"} |
                             {"session_first": j["record"]["session_first"],
                              "startup_ms": child_timing(j["record"], "startup_ms"),
                              "build_ms": child_timing(j["record"], "build_ms"),
                              "stage_ms": j["record"].get("stage_ms", {}),
                              "upload_ms": j["record"].get("telemetry", {}).get("upload_ms"),
                              "steps_answer_ms": j["record"].get("telemetry", {}).get("steps_answer_ms"),
                              "crop_scan": j["record"].get("answer", {}).get("crop_scan")}
                             for j in judged],
            "failure_artifact": read_json(failure_path) if failure_path.exists() else None,
            "result_sha256": file_digest(path) if path.exists() else None,
            "failed_query_ids": [j["query_id"] for j in judged if j["error"] or j["degraded"]]}


def build_report(run, selection_path):
    run = Path(run)
    manifest = read_json(run / "manifest.json")
    frozen = load_selection(selection_path, manifest)
    modes, variants = manifest["modes"], manifest["variants"]
    if (not modes or not variants or len(modes) != len(set(modes)) or len(variants) != len(set(variants))
            or any(m not in ("process", "persistent") for m in modes)
            or any(not isinstance(v, str) or not v or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in v) for v in variants)):
        raise ValueError("invalid manifest mode or variant")
    sessions = [summarize_session(run / (mode + "-" + variant + ".jsonl"), mode, variant, frozen)
                for mode in modes for variant in variants]
    marker = read_json(run / "complete.json") if (run / "complete.json").exists() else None
    if marker is not None and marker.get("manifest_fingerprint") != digest(manifest):
        raise ValueError("completion marker belongs to another manifest")
    complete = marker is not None and all(s["coverage_complete"] for s in sessions)
    return {"scope": SCOPE, "run": str(run.resolve()), "profile": manifest.get("profile"),
            "selection_fingerprint": frozen["selection_fingerprint"],
            "manifest_sha256": file_digest(run / "manifest.json"), "selection_file_sha256": file_digest(selection_path),
            "hard_timeout_implemented": False, "deadline_ms": DEADLINE_MS,
            "status": "complete" if complete else "partial", "completion_marker_present": marker is not None,
            "selected_rows": len(frozen["rows"]), "selected_unique_images": len({r["image_sha256"] for r in frozen["rows"]}),
            "selected_labels": dict(collections.Counter(r.get("label") for r in frozen["rows"])),
            "quality_caveats": frozen.get("quality_caveats", []), "sessions": sessions,
            "notes": ["Failed and censored observations remain in selected-row and positive denominators.",
                      "Pending rows are listed separately. Partial selected-denominator rates are provisional lower bounds.",
                      "After-first statistics exclude each session's first observation, including resumed sessions.",
                      "After-first does not prove warm remote models. A later request can trigger a cold model load; compare per-query stage times with the saved service preflight.",
                      "Process mode still starts a child for every after-first observation. It is not a persistent warm backend.",
                      "Service setup, client source-file reads, and client JSON parsing are outside HTTP wall time.",
                      "Upload and step-view timing are inside HTTP wall time. Startup, build, ask, process, and stage timings overlap.",
                      "Missing child startup, build, and ask timings are excluded from component statistics. Route placeholder zeros do not measure zero work. HTTP failures stay in all applicable latency and success denominators.",
                      "Censored waits are lower bounds. Complete-response quantiles exclude them, but success rates retain them.",
                      "Negative labels constrain excluded wines. An allowed prediction does not prove a correct identification.",
                      "Backend top-1 and top-5 prediction counts can include a response that later failed or degraded.",
                      "The pilot oversamples barcode hits. Its deadline fraction is not a corpus estimate.",
                      "The experimental child imports differ from production recognize.py. No enforced 3-second timeout is established."]}


def markdown(report):
    def ms(value):
        return "—" if value is None else "%.1f" % value
    lines = ["# Offline HTTP recognition comparison", "", "Status: %s." % report["status"],
             "Profile: `%s`." % report["profile"], "Scope: %s." % report["scope"],
             "Selection: `%s`." % report["selection_fingerprint"],
             "Selected rows: %d. Unique images: %d. Labels: %s." % (report["selected_rows"], report["selected_unique_images"], report["selected_labels"]),
             "", "## Full selected sample", "",
             "| Mode / variant | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Late correct | Error / degraded / censored | HTTP p50 / p95 / p99 ms |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for session in report["sessions"]:
        full = session["full"]; wall = full["complete_http_wall_ms"]
        lines.append("| %s / %s | %d / %d | %d / %d | %d / %d | %d | %d / %d / %d | %s / %s / %s |" %
                     (session["mode"], session["variant"], full["observed_rows"], full["selected_rows"],
                      full["complete_within_3s"], full["selected_rows"], full["correct_within_3s"], full["positive_denominator"],
                      full["correct_late"], full["errors"], full["degraded"], full["censored_rows"], ms(wall["median"]), ms(wall["p95"]), ms(wall["p99"])))
    for session in report["sessions"]:
        lines.extend(["", "## %s / %s" % (session["mode"], session["variant"]), "",
                      "| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |",
                      "|---|---:|---:|---:|---:|"])
        groups = dict(session["strata"], sensitivity=session["sensitivity"], after_session_first_observed=session["after_session_first_observed"])
        for name, value in groups.items():
            lines.append("| %s | %d / %d | %d / %d | %d / %d | %d / %d |" %
                         (name, value["observed_rows"], value["selected_rows"], value["complete_within_3s"], value["selected_rows"],
                          value["correct_within_3s"], value["positive_denominator"], value["negative_forbidden_top1"], value["negative_constraint_denominator"]))
        lines.extend(["", "First requests: `%s`." % json.dumps(session["first_requests"], ensure_ascii=False),
                      "Sensitivity excludes: `%s`." % ", ".join(session["sensitivity_excluded_ids"]),
                      "Failed or degraded query IDs: `%s`." % ", ".join(session["failed_query_ids"]), "",
                      "Component times include available observations. Nested costs MUST NOT be added together.", "",
                      "| Component | Observations | Missing | p50 ms | p95 ms | p99 ms |",
                      "|---|---:|---:|---:|---:|---:|"])
        for name, value in session["components_all_observed"].items():
            if "observations" in value:
                missing = value.get("missing_observations", session["full"]["observed_rows"] - value["observations"])
                lines.append("| %s | %d | %d | %s | %s | %s |" %
                             (name, value["observations"], missing, ms(value["median"]), ms(value["p95"]), ms(value["p99"])))
        if session["failure_artifact"]:
            lines.extend(["", "Saved failure: `%s`." % session["failure_artifact"].get("error", "present")])
    lines.extend(["", "## Measurement limits", ""] + ["- " + note for note in report["notes"]])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = build_report(args.run, args.selection)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "http-comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (args.output / "http-comparison.md").write_text(markdown(report), encoding="utf-8")
        print("%s: %d sessions, %d selected rows" % (report["status"], len(report["sessions"]), report["selected_rows"]))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("HTTP report refused: %s" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
