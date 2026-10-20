"""Verify committed Android research. Uses only the Python standard library."""
import hashlib
import json
import math
import re
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def calculate(rows):
    require(bool(rows), "Empty observations")
    require(len({r["query_id"] for r in rows}) == len(rows), "Duplicate query ID")
    for row in rows:
        require(type(row["error"]) is bool, "Error flag must be boolean")
        require(type(row["request_ms"]) in (int, float) and math.isfinite(row["request_ms"])
                and row["request_ms"] > 0, "Invalid request latency")
        for k in (1, 5, 10):
            require(type(row[f"hit_{k}"]) is bool, "Hit flag must be boolean")
        require(row["hit_1"] <= row["hit_5"] <= row["hit_10"], "Inconsistent Top-k flags")
        require(not row["error"] or not row["hit_10"], "An error cannot count as a hit")
    times = [r["request_ms"] for r in rows]
    return dict(assignments=len(rows), errors=sum(r["error"] for r in rows),
                hits={str(k): sum(r[f"hit_{k}"] for r in rows) for k in (1, 5, 10)},
                median_ms=statistics.median(times),
                p95_ms=statistics.quantiles(times, n=100, method="inclusive")[94], max_ms=max(times))


def paired(new, baseline):
    require([r["query_id"] for r in new] == [r["query_id"] for r in baseline], "Unpaired observations")
    return [sum(a["hit_1"] and not b["hit_1"] for a, b in zip(new, baseline)),
            sum(b["hit_1"] and not a["hit_1"] for a, b in zip(new, baseline))]


def verify_hashes(root):
    manifest = json.loads((root / "package-manifest.json").read_text())
    for name, expected in manifest.items():
        path = (root / name).resolve()
        require(root.resolve() in path.parents, "Unsafe manifest path")
        data = path.read_bytes()
        require(len(data) == expected["bytes"] and hashlib.sha256(data).hexdigest() == expected["sha256"],
                f"Package file changed: {name}")
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
              and "__pycache__" not in p.parts and p.name != "package-manifest.json"}
    require(actual == set(manifest), "Package inventory differs")
    return len(manifest)


def main():
    files = verify_hashes(ROOT)
    result = json.loads((ROOT / "results.json").read_text())
    require(result["schema_version"] == 1, "Unsupported research schema")
    cohort = read_rows(ROOT / "cohorts/my-failed-2.jsonl")
    canonical = (json.dumps(cohort, sort_keys=True, separators=(",", ":")) + "\n").encode()
    require(hashlib.sha256(canonical).hexdigest() == result["cohorts"]["my-failed-2"]["fingerprint"], "Cohort changed")
    require(len(cohort) == 668 and len({r["image_sha256"] for r in cohort}) == 627, "Cohort count differs")
    runs = {}
    for run in result["runs"]:
        require(run["id"] not in runs, "Duplicate run ID")
        require(run["reranking"] is False and run["barcode"] is False, "Unexpected recognition stage")
        rows = read_rows(ROOT / run["observations"])
        require([(r["query_id"], r["image_sha256"]) for r in rows]
                == [(r["query_id"], r["image_sha256"]) for r in cohort], "Cohort membership differs")
        actual = calculate(rows)
        for key in ("assignments", "errors", "hits"):
            require(actual[key] == run["metrics"][key], f"Metric mismatch: {run['id']} {key}")
        for key in ("median_ms", "p95_ms", "max_ms"):
            require(math.isclose(actual[key], run["metrics"][key], abs_tol=.00001), "Latency mismatch")
        runs[run["id"]] = rows
    require(len(runs) == 23, "Expected 13 Base series and 10 shared SO400M recipe series")
    pairs = [("pooling-2", "pooling-1", [30, 26]), ("pooling-4", "pooling-3", [37, 16]),
             ("yolo-full-image-custom", "pooling-4", [69, 56]),
             ("dis1024-cropped-custom", "standard-dis-control", [115, 75]),
             ("dis1024-cropped-custom", "dis1024-full-image-custom", [73, 51]),
             ("dis768-cropped-custom", "dis1024-cropped-custom", [36, 39])]
    for new, old, expected in pairs:
        require(paired(runs[new], runs[old]) == expected, f"Paired quality changed: {new}")
    for control in ("standard-full-image-control", "standard-dis-control"):
        require([r["top1_sha256"] for r in runs[control]] == [r["top1_sha256"] for r in runs["standard-original"]],
                "Production standard parity changed")
    require([r["top1_sha256"] for r in runs["production-custom"]]
            == [r["top1_sha256"] for r in runs["dis768-cropped-custom"]], "Production custom parity changed")
    resumed = next(r for r in result["runs"] if r["id"] == "dis1024-cropped-custom")
    require(resumed["provenance"]["resumed"] is True, "USB continuation caveat missing")
    for run in result["runs"]:
        if run["id"].startswith("so400m-"):
            require("shared-query-work" in run["timing_scope"], "Shared timing mislabeled")
    evaluation = read_rows(ROOT / result["eval_zip"]["observations"])
    require(len(evaluation) == 100 and sum(r["accepted"] for r in evaluation) == 86, "Eval.zip result differs")
    require(result["eval_zip"]["comparison_status"] == "FAIL", "Do not hide Eval.zip mismatches")
    release = json.loads((ROOT / "provenance/release-contract.json").read_text())
    require(release["version_name"] == "0.3.0" and release["version_code"] == 7
            and release["default_pipeline"] == "DIS768_CUSTOM" and release["alternative_pipeline"] == "STANDARD",
            "Release pipeline identity differs")
    require(release["publication"]["sha256"] == release["apk_sha256"]
            and release["publication"]["bytes"] == release["apk_bytes"], "Public APK receipt differs")
    require(release["yolo_available"] is False and release["model_pack_format"] == 7, "Public pack identity differs")
    require("android.permission.INTERNET" in release["merged_apk_permissions"], "Permission evidence differs")
    for key, value in (("median_ms", statistics.median(r["request_ms"] for r in evaluation)),
                       ("p95_ms", statistics.quantiles([r["request_ms"] for r in evaluation], n=100, method="inclusive")[94])):
        require(math.isclose(result["eval_zip"][key], value, abs_tol=.00001), "Eval.zip latency differs")
    report = ROOT.parent.parent / "ANDROID-RESEARCH-AND-RESULTS-20261020.md"
    text = report.read_text()
    for run in result["runs"]:
        hits = run["metrics"]["hits"]
        printed = " / ".join(f"{100 * hits[str(k)] / 668:.2f}" for k in (1, 5, 10)) + "%"
        require(printed in text, f"Research table omits quality: {run['id']}")
    for document in (report, ROOT / "README.md"):
        for link in re.findall(r"\]\(([^)]+)\)", document.read_text()):
            if "://" not in link:
                require((document.parent / link.split("#")[0]).exists(), f"Missing research link: {link}")
    print(f"PASS: {files} file hashes; 23 series; {sum(len(r) for r in runs.values())} hard-cohort observations; "
          "100 Eval.zip observations; quality, paired changes, latency, and production Top-1 parity. No inference.")


if __name__ == "__main__":
    main()
