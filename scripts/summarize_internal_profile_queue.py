"""Write an offline snapshot of recorded internal profile attempts.

Read only the queue and its archived attempt.json files. Never inspect a live job,
load production modules, open images, contact a service, or update the queue.
--output MUST name a new directory. The parent owns invocation and PID checks.
"""
import argparse
import collections
import datetime
import hashlib
import json
import math
from pathlib import Path

EXTERNAL = "vino-svoe-search-by-photo"
LABEL = "barcode-rerank-siglip2-512-crop-label"
COUNTERPART = "barcode-rerank-siglip2-512-crop"
ARTIFACTS = {"run.json", "metrics.json", "queries.jsonl", "results.jsonl", "predictions.jsonl"}
TERMINAL = {"done", "failed", "stopped", "invalid_completion", "rejected", "unavailable"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def summarize_attempt(attempt, row, expected, expected_unique, queue_dir):
    issues = []
    archive_hash = None
    archive = attempt.get("archive")
    if archive:
        directory = Path(archive)
        if not directory.is_absolute():
            directory = queue_dir / directory
        try:
            body = (directory / "attempt.json").read_bytes()
            archive_hash = hashlib.sha256(body).hexdigest()
            if json.loads(body) != attempt:
                issues.append("Queue and archived attempt differ. Reconcile before a complete report.")
        except (OSError, ValueError) as exc:
            issues.append("Archived attempt is unavailable: %s" % exc)
    else:
        issues.append("No archived attempt path is recorded.")
    identity = attempt.get("identity") or {}
    request = attempt.get("request") or {}
    run = attempt.get("run") or {}
    metrics = attempt.get("metrics") or {}
    final = attempt.get("final_event") or {}
    progress = attempt.get("progress") or {}
    queries = identity.get("queries") or []
    labels = collections.Counter(q.get("label") for q in queries)
    digests = {q.get("image_sha256") for q in queries if q.get("image_sha256")}
    query_ids = [q.get("query_id") for q in queries]
    recorded_state = attempt.get("state", "unknown")
    run_id = attempt.get("run_id")
    hashes = attempt.get("artifact_sha256") or {}
    configured_barcode = identity.get("has_barcode")
    observed_rows = run.get("answered", progress.get("done"))
    errors = final.get("errors", progress.get("errors"))
    degraded = attempt.get("degraded_queries")
    complete = recorded_state == "done"
    if complete:
        checks = {
            "terminal runner evidence": attempt.get("runner_exit_verified") is True
                and final.get("event") == "done" and bool(run.get("finished")),
            "matching run identifiers": bool(run_id) and all(x == run_id for x in
                (run.get("run_id"), metrics.get("run_id"), final.get("run_id"))),
            "matching profile": request.get("configuration") == row["name"]
                and run.get("configuration") == row["name"],
            "complete query coverage": len(queries) == expected and len(set(query_ids)) == expected
                and None not in query_ids and len(digests) == expected_unique
                and all(q.get("image_sha256") for q in queries)
                and observed_rows == expected and final.get("answered") == expected
                and (metrics.get("queries") or {}).get("total") == expected,
            "quality denominators": all((metrics.get("queries") or {}).get(kind, 0) == labels[kind]
                and (metrics.get(kind) or {}).get("n", 0) == labels[kind]
                for kind in ("positive", "negative", "no_match", "unlabelled")),
            "error-free results": errors == 0 and degraded == 0
                and all((metrics.get(kind) or {}).get("errors", 0) == 0
                        for kind in ("positive", "negative", "no_match", "unlabelled")),
            "saved artifact validation": ARTIFACTS <= hashes.keys() and all(
                isinstance(hashes[k], str) and len(hashes[k]) == 64
                and set(hashes[k]) <= set("0123456789abcdef") for k in ARTIFACTS),
            "matching run options": (run.get("options") or {}).get("set") == request.get("set")
                and (run.get("options") or {}).get("workers") == request.get("workers")
                and (run.get("options") or {}).get("limit") is None
                and run.get("use_cache") == request.get("use_cache")
                and (configured_barcode is not True or run.get("use_barcode") is True),
        }
        issues.extend("Missing or inconsistent %s." % key for key, ok in checks.items() if not ok)
        complete = not issues
    wall = number(run.get("wall_s", metrics.get("wall_s")))
    start, end = number(attempt.get("intent_t")), number(final.get("t"))
    elapsed = end - start if start is not None and end is not None and end >= start else None
    return {
        "id": attempt.get("id"), "recorded_state": recorded_state,
        "state": "done" if complete else "unverified_completion" if recorded_state == "done" else recorded_state,
        "complete": complete, "metrics_scope": "complete recorded run" if complete else "partial or unverified",
        "run_id": run_id, "pid_recorded": attempt.get("pid"), "observed_t": attempt.get("observed_t"),
        "workers": request.get("workers", row.get("workers")),
        "cache_requested": request.get("use_cache", row.get("use_cache")),
        "barcode_requested": request.get("use_barcode", row.get("use_barcode")),
        "barcode_configured": configured_barcode,
        "barcode_used": run.get("use_barcode"),
        "coverage": {"expected_rows": expected, "expected_unique_images": expected_unique,
                     "observed_rows": observed_rows, "identity_rows": len(queries),
                     "identity_unique_images": len(digests), "errors": errors, "degraded": degraded},
        "positive": metrics.get("positive"), "negative": metrics.get("negative"),
        "no_match": metrics.get("no_match"), "latency_ms": metrics.get("latency_ms"),
        "run_wall_s": wall, "recorded_attempt_elapsed_s": elapsed,
        "run_rows_per_second": observed_rows / wall if complete and wall and number(observed_rows) is not None else None,
        "index_coverage": run.get("embeddings"),
        "query_identity_sha256": digest(queries) if queries else None,
        "catalogue_identity_sha256": digest(identity["catalogue"]) if "catalogue" in identity else None,
        "artifact_sha256_recorded": hashes, "archive": archive, "archive_sha256": archive_hash,
        "error": attempt.get("error"), "identity_check_error": attempt.get("identity_check_error"),
        "issues": issues,
    }


def label_comparison(profiles):
    selected = {p["name"]: p for p in profiles if p["name"] in (LABEL, COUNTERPART)}
    result = {"label_profile": LABEL, "counterpart": COUNTERPART, "state": "pending",
              "scope": "Aggregate recorded bulk metrics. This is not a paired prediction comparison."}
    if len(selected) != 2 or not all(p["complete"] for p in selected.values()):
        result["reason"] = "Both profiles need a verified complete recorded attempt."
        return result
    a, b = selected[COUNTERPART]["latest_attempt"], selected[LABEL]["latest_attempt"]
    keys = ("query_identity_sha256", "catalogue_identity_sha256")
    if any(not a.get(k) or a[k] != b.get(k) for k in keys):
        result.update(state="not_comparable", reason="Recorded query or catalogue identities differ or are absent.")
        return result
    differences = {}
    for key in ("recall_at_1", "recall_at_5"):
        left, right = (a.get("positive") or {}).get(key), (b.get("positive") or {}).get(key)
        differences[key] = right - left if number(left) is not None and number(right) is not None else None
    result.update(state="complete", label_minus_counterpart=differences,
                  counterpart_metrics={k: a[k] for k in ("positive", "negative", "latency_ms", "run_wall_s", "index_coverage")},
                  label_metrics={k: b[k] for k in ("positive", "negative", "latency_ms", "run_wall_s", "index_coverage")})
    return result


def build_report(queue_path, expected_unique=1851):
    queue_path = Path(queue_path).resolve()
    data = queue_path.read_bytes()
    queue = json.loads(data)
    rows = queue["profiles"]
    names = [r["name"] for r in rows]
    if len(names) != len(set(names)):
        raise ValueError("queue contains duplicate profile names")
    expected = queue["query_count_at_queue_time"]
    if type(expected) is not int or expected <= 0 or type(expected_unique) is not int or expected_unique <= 0:
        raise ValueError("expected row and unique-image counts MUST be positive integers")
    profiles = []
    for row in rows:
        attempts = [summarize_attempt(a, row, expected, expected_unique, queue_path.parent)
                    for a in row.get("attempts", [])]
        latest = attempts[-1] if attempts else None
        authorized = row.get("authorized_to_start") is True and row["name"] != EXTERNAL
        state = latest["state"] if latest else row.get("status", "unknown")
        complete = bool(latest and latest["complete"])
        profile_issues = []
        if not latest and state == "done":
            state = "unverified_completion"
            profile_issues.append("Queue says done, but no attempt records prove completion.")
        if not authorized:
            state = "awaiting_user_approval" if row["name"] == EXTERNAL else "not_authorized"
            complete = False
        profiles.append({"name": row["name"], "authorized_to_start": authorized,
            "queue_status": row.get("status"), "state": state, "complete": complete,
            "embedding": row.get("embedding"), "model_backend": row.get("model_backend"),
            "workers": latest["workers"] if latest else row.get("workers"),
            "cache_requested": row.get("use_cache"), "barcode_requested": row.get("use_barcode"),
            "barcode_configured": latest["barcode_configured"] if latest else None,
            "run_id": latest["run_id"] if latest else row.get("run_id"),
            "attempt_count": len(attempts), "attempts": attempts, "latest_attempt": latest,
            "issues": profile_issues,
            "reason": row.get("reason") or row.get("error") or row.get("reason_at_queue_time")})
    if queue_path.read_bytes() != data:
        raise ValueError("queue changed during the snapshot; invoke the reader again")
    authorized = [p for p in profiles if p["authorized_to_start"]]
    terminal = sum(p["state"] in TERMINAL for p in authorized)
    status = ("complete" if authorized and all(p["complete"] for p in authorized)
              else "terminal_with_failures" if authorized and terminal == len(authorized) else "partial")
    return {"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "queue": str(queue_path), "queue_sha256": hashlib.sha256(data).hexdigest(),
        "scope": "Offline snapshot of saved queue and attempt records. No live process verification.",
        "status": status,
        "expected_query_rows": expected, "expected_unique_images": expected_unique,
        "profile_count": len(profiles), "authorized_profile_count": len(authorized),
        "complete_authorized_profiles": sum(p["complete"] for p in authorized),
        "terminal_authorized_profiles": terminal,
        "state_counts": dict(collections.Counter(p["state"] for p in profiles)),
        "external_approval": queue.get("external_recognizer_approval", "unknown"),
        "external_approval_reason": queue.get("external_recognizer_approval_reason"),
        "required_index_builds": queue.get("required_index_builds", []),
        "profiles": profiles, "label_comparison": label_comparison(profiles),
        "notes": ["All queue profiles remain visible. A missing metric means unknown, not zero.",
            "Completion uses saved runner-exit evidence and artifact validation. This reader does not rehash run files or verify current PIDs.",
            "An archive mismatch can occur during reconciliation. Repeat the snapshot after reconciliation.",
            "Metrics from failed, active, or unverified attempts are partial. Do not rank these attempts as complete runs.",
            "Latency describes cached bulk requests. It does not establish new-image demo latency or a three-second response guarantee.",
            "Run wall excludes work outside the benchmark. Attempt elapsed is the recorded intent-to-final interval. It is not isolated startup time.",
            "Barcode requested does not mean barcode configured. Profiles without a barcode stage do not add one.",
            "Negative labels exclude a named wine. A different prediction does not prove correct identification.",
            "Index coverage and model cache state can differ. Compare these records before interpreting timing or quality differences."]}


def markdown(report):
    def cell(value):
        return "—" if value is None else str(value).replace("|", "\\|").replace("\n", " ")
    def flag(value):
        return "yes" if value is True else "no" if value is False else "unknown"
    def fmt(value):
        return "—" if number(value) is None else "%.2f" % value
    def signed(value):
        return "unknown" if type(value) not in (int, float) or not math.isfinite(value) else "%.2f" % value
    def recall(metric, key):
        val = metric.get(key)
        return "—" if number(val) is None else "%.2f%% (n=%s)" % (val * 100, cell(metric.get("n")))
    lines = ["# Internal profile queue snapshot", "", "Status: %s." % report["status"],
        "Complete authorized profiles: %d of %d. Total queue profiles: %d." %
        (report["complete_authorized_profiles"], report["authorized_profile_count"], report["profile_count"]),
        "Expected coverage: %d query rows and %d unique images." %
        (report["expected_query_rows"], report["expected_unique_images"]),
        "External recognizer approval: %s." % report["external_approval"],
        "", "| Profile | State | Attempts | Workers | Cache requested | Barcode configured | Run ID |",
        "|---|---|---:|---:|---|---|---|"]
    for p in report["profiles"]:
        lines.append("| %s | %s | %d | %s | %s | %s | %s |" % (cell(p["name"]), cell(p["state"]),
            p["attempt_count"], cell(p["workers"]), flag(p["cache_requested"]), flag(p["barcode_configured"]), cell(p["run_id"])))
    lines += ["", "## Recorded metrics", "", "Partial and unverified attempts remain labelled in the State column.", "",
        "| Profile | State | Rows / expected | Errors / degraded | R@1 | R@5 | Forbidden top-1 / negative | Bulk p50 / p95 ms | Run / attempt s | Rows/s |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for p in report["profiles"]:
        a = p["latest_attempt"] or {}; cov = a.get("coverage") or {}; pos = a.get("positive") or {}
        neg = a.get("negative") or {}; lat = a.get("latency_ms") or {}
        lines.append("| %s | %s | %s / %d | %s / %s | %s | %s | %s / %s | %s / %s | %s / %s | %s |" % (
            cell(p["name"]), cell(p["state"]), cell(cov.get("observed_rows")), report["expected_query_rows"],
            cell(cov.get("errors")), cell(cov.get("degraded")), recall(pos, "recall_at_1"), recall(pos, "recall_at_5"),
            cell(neg.get("false_match_at_1")), cell(neg.get("n")), fmt(lat.get("median")), fmt(lat.get("p95")),
            fmt(a.get("run_wall_s")), fmt(a.get("recorded_attempt_elapsed_s")), fmt(a.get("run_rows_per_second"))))
    lines += ["", "## Attempt notes", ""]
    for p in report["profiles"]:
        if p.get("reason"):
            lines.append("- `%s`: %s" % (p["name"], cell(p["reason"])))
        for issue in p["issues"]:
            lines.append("- `%s`: %s" % (p["name"], cell(issue)))
        for a in p["attempts"]:
            details = [a[k] for k in ("error", "identity_check_error") if a.get(k)] + a["issues"]
            if details or a["state"] not in ("done", "running", "starting"):
                lines.append("- `%s`, attempt `%s`, %s: %s" % (p["name"], cell(a["id"]), a["state"], cell(" ".join(details) or "No completion is recorded.")))
    comparison = report["label_comparison"]
    lines += ["", "## Label profile comparison", "", "State: %s." % comparison["state"], comparison["scope"]]
    if comparison.get("reason"):
        lines.append(comparison["reason"])
    if comparison.get("label_minus_counterpart"):
        for key, value in comparison["label_minus_counterpart"].items():
            lines.append("- %s difference: %s percentage points." % (key, signed(value * 100) if value is not None else "unknown"))
    lines += ["", "## Measurement limits", ""] + ["- " + note for note in report["notes"]]
    if report.get("external_approval_reason"):
        lines += ["", report["external_approval_reason"]]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-unique", type=int, default=1851)
    args = parser.parse_args(argv)
    try:
        report = build_report(args.queue, args.expected_unique)
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "queue-summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        (args.output / "queue-summary.md").write_text(markdown(report))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("Queue report refused: %s" % exc)
        return 2
    print("%s: %d of %d authorized profiles complete" %
          (report["status"], report["complete_authorized_profiles"], report["authorized_profile_count"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
