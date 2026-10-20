"""Export saved Android measurements. This command starts no inference or device work."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parent
CONFIGS = [
    ("standard-original", "android-offline-retrieval-variants-20261019/control-base-p512-no-seg"),
    *[(f"pooling-{i}", f"android-base-p224-pooling-20261020/comparison-v3/condition-{i}-full") for i in range(1, 5)],
    ("standard-full-image-control", "android-full-image-p512-pooling-20261020/comparison-v2/condition-5-full"),
    ("yolo-full-image-custom", "android-full-image-p512-pooling-20261020/comparison-v2/condition-6-full"),
    ("standard-dis-control", "android-dis-p512-pooling-20261020/comparison-v3/condition-5-full"),
    ("dis1024-full-image-custom", "android-dis-p512-pooling-20261020/comparison-v3/condition-7-full"),
    ("dis1024-cropped-custom", "android-dis-p512-pooling-20261020/comparison-v4/condition-8-full"),
    *[(f"dis{size}-cropped-custom", f"android-dis-resolution-20261020/comparison-v1/dis-{size}/full") for size in (768, 512)],
    ("production-custom", "android-dual-pipeline-20261020/validation-v1/custom-full"),
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def percentile95(values):
    ordered = sorted(values)
    position = (len(ordered) - 1) * .95
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def metrics(rows):
    values = [r["request_ms"] for r in rows]
    return dict(assignments=len(rows), errors=sum(r["error"] for r in rows),
                hits={str(k): sum(r[f"hit_{k}"] for r in rows) for k in (1, 5, 10)},
                median_ms=statistics.median(values), p95_ms=percentile95(values), max_ms=max(values))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--eval-run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("Preserve the published export. Use a new research directory.")
    sources = {}

    def read(path, jsonl=False):
        data = path.read_bytes()
        try:
            name = "artifacts/" + str(path.relative_to(args.artifacts))
        except ValueError:
            name = "eval-run/" + path.name
        sources[name] = dict(bytes=len(data), sha256=digest(data))
        return [json.loads(line) for line in data.splitlines()] if jsonl else json.loads(data)

    queries = read(args.artifacts / CONFIGS[0][1] / "queries.json")
    cohort = [dict(query_id=q["query_id"], image_sha256=q["image_sha256"],
                   accepted_answers_sha256=digest(encoded(sorted(q["truth"])))) for q in queries]
    assert len(cohort) == 668 and len({q["image_sha256"] for q in cohort}) == 627
    cohorts = {"my-failed-2": dict(assignments=668, distinct_images=627, fingerprint=digest(encoded(cohort)))}
    runs = []
    outputs = {"cohorts/my-failed-2.jsonl": b"".join(encoded(row) for row in cohort)}

    def export(run_id, path, variant=None):
        state = read(path / "run.json")
        assert state["complete"] and state["reranking"] is False
        raw = read(path / "responses.jsonl", True)
        assert len(raw) == 668
        audit = read(path / "independent-audit.json") if (path / "independent-audit.json").exists() else state
        assert audit.get("passed", audit.get("verification_passed", True))
        expected = (audit["variants"][str(variant)]["observed_hits"] if variant else audit["hits"])
        rows = []
        for query, record in zip(queries, raw):
            assert query["query_id"] == record["query_id"]
            assert record.get("image_sha256", query["image_sha256"]) == query["image_sha256"]
            body = record["response"]
            variants = body.get("variants", [])
            result = next((v for v in variants if v["variant"] == variant), {}) if variant else (variants[0] if variants else body)
            candidates = result.get("candidates", [])
            for candidate in candidates:
                assert math.isfinite(candidate["score"])
            error = record.get("status", 200) != 200
            flags = {f"hit_{k}": bool(set(query["truth"]) & {c["slug"] for c in candidates[:k]}) for k in (1, 5, 10)}
            if "outcomes" in audit:
                assert all(flags[f"hit_{k}"] == audit["outcomes"][query["query_id"]][str(k)] for k in (1, 5, 10))
            assert not error or not any(flags.values())
            rows.append(dict(query_id=query["query_id"], image_sha256=query["image_sha256"],
                             request_ms=record.get("client_ms", record.get("latency_ms")), error=error,
                             top1_sha256=digest(candidates[0]["slug"].encode()) if candidates else None, **flags))
        actual = metrics(rows)
        assert actual["hits"] == expected and actual["errors"] == state["errors"], run_id
        med = audit.get("client_median_ms", audit.get("median_ms", audit.get("client_ms", {}).get("median")))
        p95 = audit.get("client_p95_ms", audit.get("p95_ms", audit.get("client_ms", {}).get("p95")))
        assert math.isclose(actual["median_ms"], med, abs_tol=.00001), run_id
        assert math.isclose(actual["p95_ms"], p95, abs_tol=.00001), run_id
        filename = f"observations/{run_id}.jsonl"
        outputs[filename] = b"".join(encoded(row) for row in rows)
        metadata = {k: state[k] for k in ("condition", "package", "pack_version", "installed_apk_sha256",
                    "pack_manifest_sha256", "query_file_sha256", "initial_pid", "final_pid",
                    "peak_sampled_pss_kib", "maximum_thermal_status", "maximum_battery_celsius") if k in state}
        if variant:
            metadata.pop("condition", None)
            metadata.update(variant=variant, model="google/siglip2-so400m-patch16-naflex", dimension=1152)
        else:
            metadata.update(model="google/siglip2-base-patch16-naflex", dimension=768)
        metadata["resumed"] = bool(state.get("resume"))
        health = state.get("health_before", {})
        metadata["wine_count"] = health.get("wine_count", raw[0]["response"].get("wine_count"))
        metadata["model_revision"] = health.get("revision", raw[0]["response"].get("revision"))
        if variant:
            metadata["process_segments"] = audit["process_segments"]
            metadata["recipe"] = next(v["recipe"] for r in raw for v in r["response"].get("variants", [])
                                      if v["variant"] == variant)
        scope = "shared-query-work: one request evaluates all ten recipes" if variant else "complete USB HTTP request"
        runs.append(dict(id=run_id, cohort="my-failed-2", observations=filename,
                         reranking=False, barcode=False, timing_scope=scope, metrics=actual, provenance=metadata))

    for run_id, rel in CONFIGS:
        export(run_id, args.artifacts / rel)
    for variant in range(1, 11):
        export(f"so400m-recipe-{variant:02d}", args.artifacts / "android-offline-retrieval-variants-20261019/full-my-failed2-v4", variant)
    eval_state = read(args.eval_run / "run.json")
    eval_report = read(args.eval_run / "report.json")
    eval_predictions = read(args.eval_run / "predictions.jsonl", True)
    assert eval_state["transport_status"] == "completed" and len(eval_predictions) == 100
    detail = {r["query_id"]: r for r in eval_report["details"]}
    eval_rows = []
    for p in eval_predictions:
        d = detail[p["query_id"]]
        accepted = p["predicted_slug"] in [d["expected_slug"], *d["alternative_slugs"]]
        eval_rows.append(dict(query_id=p["query_id"], image_sha256=p["image_sha256"],
                              request_ms=p["latency_ms"], accepted=accepted))
    assert sum(r["accepted"] for r in eval_rows) == eval_state["accepted_count"] == 86
    outputs["observations/eval-zip.jsonl"] = b"".join(encoded(r) for r in eval_rows)
    results = dict(schema_version=1, date="2026-10-20", cohorts=cohorts, runs=runs,
        eval_zip=dict(assignments=100, accepted=86, exact=81, alternatives=5, mismatches=14,
                      comparison_status="FAIL", transport_status="completed", observations="observations/eval-zip.jsonl",
                      median_ms=statistics.median(r["request_ms"] for r in eval_rows),
                      p95_ms=percentile95([r["request_ms"] for r in eval_rows])),
        limits=["Acceptance flags are derived evidence, not published reference answers.",
                "No images, masks, reference answers, raw vectors, model weights, or device state are included.",
                "Summary verification does not reproduce model inference or independently relabel predictions."])
    outputs["results.json"] = json.dumps(results, indent=2, allow_nan=False).encode() + b"\n"
    outputs["source-manifest.json"] = json.dumps(sources, indent=2, sort_keys=True).encode() + b"\n"
    for name, data in outputs.items():
        path = args.out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
    print(f"Exported {len(runs)} hard-cohort runs and 100 Eval.zip observations. No device was accessed.")


if __name__ == "__main__":
    main()
