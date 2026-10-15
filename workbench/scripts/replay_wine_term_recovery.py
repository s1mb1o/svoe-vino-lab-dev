"""Replay frozen OCR. Do not run inference or write to the source campaign."""
# ruff: noqa: E402
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workbench/pipeline"))
import variant_attributes as attrs
import wine_term_recovery as recovery
import wine_terms

DEFAULT_SOURCE = ROOT / "internal/victor-dravigny-rank6-20261007/benchmark-repeat-20261009"
DEFAULT_OCR = ROOT / "workbench/work/main-label-benchmark-repeat-20261009"
VARIANTS = (("exact", "exact", "damerau"), ("whitespace", "whitespace", "damerau"),
            ("fuzzy_damerau", "fuzzy", "damerau"), ("fuzzy_levenshtein", "fuzzy", "levenshtein"))
OPTIONS = {"window": 10, "min_confidence": 70}
COUNT_FIELDS = ("order_changes", "top1_changes", "with_usable_attributes", "with_recovery",
                "accepted_corrections", "all_shortlist_conflicts", "new_truth_conflicts",
                "positive_rows", "positive_top1", "positive_top5", "positive_top10",
                "positive_fixed", "positive_regressed", "named_negative_rows",
                "named_negative_errors", "named_negative_fixed", "named_negative_regressed")


def cache_pure_functions():
    """Cache deterministic parsing in this replay process alone."""
    original = attrs.expected

    @lru_cache(maxsize=8192)
    def expected(fields):
        return original(dict(fields))

    attrs.expected = lambda record: expected(tuple((key, (record or {}).get(key))
                                                   for key in ("name", "slug", "grapes", "color")))
    wine_terms.normalize = lru_cache(maxsize=65536)(wine_terms.normalize)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n")


def rank(query, candidates):
    return next((i + 1 for i, row in enumerate(candidates) if row["slug"] in query["truth"]), None)


def partition(query, catalog):
    # Keep one producer in one descriptive partition. Do not tune thresholds here.
    record = catalog.get(query["named_slug"], {})
    group = wine_terms.base_text(record.get("producer")) or query["named_slug"]
    return "development" if int(hashlib.sha256(group.encode()).hexdigest()[:8], 16) % 5 == 0 else "evaluation"


def metrics(records, variant):
    counts = Counter(dict.fromkeys(COUNT_FIELDS, 0))
    counts["rows"] = len(records)
    for record in records:
        base, new = record["variants"]["exact"], record["variants"][variant]
        counts["order_changes"] += new["order"] != base["order"]
        counts["top1_changes"] += new["order"][:1] != base["order"][:1]
        counts["with_usable_attributes"] += any(new["observed_attributes"].values())
        counts["with_recovery"] += bool(new["corrections"])
        counts["accepted_corrections"] += len(new["corrections"])
        counts["all_shortlist_conflicts"] += new["all_shortlist_conflicts"]
        counts["new_truth_conflicts"] += len(set(new["truth_conflicts"]) - set(base["truth_conflicts"]))
        if record["label"] in ("positive", "variant"):
            counts["positive_rows"] += 1
            counts["positive_top1"] += new["rank"] == 1
            counts["positive_top5"] += new["rank"] is not None and new["rank"] <= 5
            counts["positive_top10"] += new["rank"] is not None and new["rank"] <= 10
            counts["positive_fixed"] += new["rank"] == 1 and base["rank"] != 1
            counts["positive_regressed"] += new["rank"] != 1 and base["rank"] == 1
        elif record["label"] == "negative":
            counts["named_negative_rows"] += 1
            old_bad = base["order"][:1] == [record["named_slug"]]
            new_bad = new["order"][:1] == [record["named_slug"]]
            counts["named_negative_errors"] += new_bad
            counts["named_negative_fixed"] += old_bad and not new_bad
            counts["named_negative_regressed"] += new_bad and not old_bad
    positive = counts["positive_rows"]
    return dict(counts, positive_top1_rate=round(counts["positive_top1"] / positive, 6) if positive else None,
                correction_precision=None, abstentions=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--ocr-dir", type=Path, default=DEFAULT_OCR)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    inputs = [args.source_dir / name for name in ("inputs.json", "catalogue.json")]
    inputs += [args.ocr_dir / engine / name for engine in ("tesseract", "paddleocr")
               for name in ("identity.json", "scores.jsonl")]
    # Audit all saved ranking files, even though only the manifest supplies rankings.
    inputs += sorted((args.source_dir / "query-results").glob("*.jsonl"))
    hashes = {str(path.resolve()): sha(path) for path in inputs}
    manifest = json.loads(inputs[0].read_text())
    catalog = json.loads(inputs[1].read_text())
    if sha(inputs[1]) != manifest["catalogue_sha256"]:
        raise ValueError("Frozen catalogue hash differs")
    identity = {"sources": hashes, "normalization": recovery.IDENTITY,
                "script_sha256": sha(Path(__file__)), "variants": VARIANTS,
                "options": OPTIONS, "limit": args.limit}
    frozen = args.output / "inputs.json"
    if frozen.exists() and json.loads(frozen.read_text()) != json.loads(json.dumps(identity)):
        raise ValueError("Output directory belongs to a different experiment")
    dump(frozen, identity)
    (args.output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    for module in (attrs, wine_terms, recovery):
        (args.output / Path(module.__file__).name).write_bytes(Path(module.__file__).read_bytes())
    (args.output / "wine_terms.json").write_bytes(Path(wine_terms.__file__).with_suffix(".json").read_bytes())
    cache_pure_functions()
    queries = manifest["queries"][:args.limit] if args.limit else manifest["queries"]
    report = {"scope": "Frozen development-cohort replay. No inference and no live matcher change.",
              "threshold_policy": "Fixed before replay. No threshold fitting to the cohort.",
              "limitations": ["The cohort was used in earlier development. Partitions are not new held-out evidence.",
                              "No independently transcribed span truth exists. Real correction precision is unmeasured.",
                              "Named negatives exclude one identity. Other predictions are not proven correct.",
                              "All-shortlist conflict is a diagnostic. No new abstention or retrieval policy is applied.",
                              "The saved Tesseract output has no line geometry. Cross-word recovery is disabled for it."],
              "engines": {}}
    for engine in ("tesseract", "paddleocr"):
        reader = {row["key"]: row for row in rows(args.ocr_dir / engine / "scores.jsonl")}
        reader_identity = json.loads((args.ocr_dir / engine / "identity.json").read_text())
        if reader_identity["manifest_sha256"] != sha(inputs[0]):
            raise ValueError("OCR cache belongs to a different query manifest")
        records, started, statuses = [], time.perf_counter(), Counter()
        for index, query in enumerate(queries):
            candidates = [dict(slug=c["slug"], rank=i + 1, score=c["visual_score"])
                          for i, c in enumerate(query["candidates"])]
            item = reader.get(query["query"].get("sha256"))
            status = ("missing_label" if query["query"]["status"] != "ready" else
                      "reader_error" if item is None or item.get("error") else "ready")
            statuses[status] += 1
            words = item["words"] if status == "ready" else []
            record = {"id": query["id"], "label": query["label"], "named_slug": query["named_slug"],
                      "truth": query["truth"], "source_sha256": query["query"]["source_sha256"],
                      "image_path": query["image_path"], "partition": partition(query, catalog),
                      "status": status, "raw_words": words, "variants": {}}
            for name, mode, metric in VARIANTS:
                if mode == "exact":
                    answer, evidence = attrs.verify(candidates, words, catalog, OPTIONS)
                    observed = evidence["observed_attributes"]
                    changes, soft = [], []
                else:
                    answer, evidence = recovery.verify(candidates, words, catalog, OPTIONS, mode, metric)
                    observed = evidence["observed_attributes"]
                    changes = evidence["recovery"]["corrections"]
                    soft = evidence["soft_fields"]
                # Check contradictions without requiring differences in the shortlist.
                contradictions = []
                for candidate in candidates[:OPTIONS["window"]]:
                    values, complete = attrs.expected(dict(catalog.get(candidate["slug"]) or {}, slug=candidate["slug"]))
                    if any(field not in soft and attrs.compare(field, observed[field], values[field], complete) == "conflict"
                           for field in attrs.FIELDS):
                        contradictions.append(candidate["slug"])
                record["variants"][name] = {
                    "order": [row["slug"] for row in answer], "rank": rank(query, answer),
                    "observed_attributes": observed, "soft_fields": soft,
                    "corrections": changes, "conflicts": evidence["conflicts"],
                    "truth_conflicts": sorted(set(contradictions) & set(query["truth"])),
                    "all_shortlist_conflicts": bool(candidates and len(contradictions) == min(OPTIONS["window"], len(candidates))),
                    "attribute_rejections": evidence["attribute_rejections"]}
            records.append(record)
            if (index + 1) % 100 == 0:
                print(json.dumps({"engine": engine, "rows": index + 1,
                                  "elapsed_s": round(time.perf_counter() - started, 2)}), flush=True)
        with (args.output / (engine + ".jsonl")).open("w") as stream:
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
        report["engines"][engine] = {
            "source_statuses": dict(statuses), "elapsed_s": round(time.perf_counter() - started, 2),
            "metrics": {name: metrics(records, name) for name, _, _ in VARIANTS},
            "partitions": {part: {name: metrics([r for r in records if r["partition"] == part], name)
                                   for name, _, _ in VARIANTS} for part in ("development", "evaluation")}}
        print(json.dumps({"engine": engine, "metrics": report["engines"][engine]["metrics"]}), flush=True)
    for path, expected in hashes.items():
        if sha(Path(path)) != expected:
            raise ValueError("A source file changed during the replay: " + path)
    report["verified_source_files_unchanged"] = len(hashes)
    dump(args.output / "summary.json", report)


if __name__ == "__main__":
    main()
