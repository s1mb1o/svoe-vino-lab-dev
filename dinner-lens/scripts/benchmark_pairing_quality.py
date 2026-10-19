"""Capture sauce-sensitive wine recommendations through every authenticated page.

The separate blind judgment file must be frozen before scoring. It is an editorial
model assessment from wine evidence, not a tasting panel or an implementation oracle.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from dinner_lens.api import create_app
from dinner_lens.data import Knowledge
from dinner_lens.embeddings import EmbeddingIndex
from dinner_lens.engine import Engine
from dinner_lens.paths import bundle_root, default_dataset, default_index
try:
    from dinner_lens.paths import default_style
except ImportError:
    # Allow a hash-verified pre-fix package to reproduce the holdout baseline.
    def default_style():
        return bundle_root() / "prompts/style-guidance.en.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(cases_path, output):
    root = bundle_root()
    knowledge = Knowledge(default_dataset(), default_style())
    engine = Engine(knowledge, EmbeddingIndex(knowledge, default_index()),
                    cursor_secret=b"pairing-quality-audit-only-secret-at-least-32-bytes")
    token = "pairing-quality-audit-token-at-least-24-characters"
    source = json.loads(default_dataset().read_bytes())
    codes = {w["wine_slug"]: w["id"] for w in source["wines"]}
    cases = json.loads(cases_path.read_bytes())["cases"]
    results = []
    with TestClient(create_app(engine, None, api_token=token)) as client:
        client.headers["Authorization"] = "Bearer " + token
        for case in cases:
            payload = {"node_id": case["node_id"], "confirmed_attributes": case["confirmed_attributes"],
                       "user_constraints": case.get("user_constraints", {}), "limit": 3}
            response = client.post("/v1/recommendations", json=payload)
            assert response.status_code == 200, response.text
            pages = [response.json()]
            while pages[-1]["next_cursor"]:
                assert len(pages) < 100
                response = client.post("/v1/recommendations/more", json={"cursor": pages[-1]["next_cursor"]})
                assert response.status_code == 200, response.text
                pages.append(response.json())
            entries = []
            for number, page in enumerate(pages, 1):
                for entry in page["results"]:
                    entries.append({"position": len(entries) + 1, "page": number,
                        "code": codes.get(entry["wine_slug"], entry["wine_slug"]), **entry})
            slugs = [e["wine_slug"] for e in entries]
            sources = [e["selection_source"] for e in entries]
            flags = {
                "unique_wines": len(slugs) == len(set(slugs)),
                "all_pages_preserve_node": all(p["resolved_node_id"] == case["node_id"] for p in pages),
                "all_pages_preserve_profile": len({p["effective_profile_id"] for p in pages}) == 1,
                "complete_count": len(entries) == pages[0]["total_eligible"],
                "expected_availability": bool(entries) is not case.get("expect_empty", False),
                "curated_before_embedding": "embedding" not in sources or "curated" not in sources or
                    max(i for i, s in enumerate(sources) if s == "curated") < sources.index("embedding"),
            }
            results.append({"case": case, "label_ru": knowledge.nodes[case["node_id"]]["label_ru"],
                "effective_profile_id": pages[0]["effective_profile_id"], "applied_modifier_ids": pages[0]["applied_modifier_ids"],
                "diagnostics": pages[0]["diagnostics"], "page_count": len(pages), "wine_count": len(entries),
                "functional_checks": flags, "entries": entries})
    value = {"mode": "authenticated ASGI HTTP; user-confirmed dishes; all continuation pages",
        "cases_sha256": sha(cases_path), "dataset_sha256": knowledge.sha256,
        "capture_script_sha256": sha(Path(__file__)),
        "source_sha256": {p.name: sha(p) for p in (root / "src/dinner_lens").glob("*.py")},
        "case_count": len(results), "wine_recommendations": sum(r["wine_count"] for r in results),
        "functional_pass": all(all(r["functional_checks"].values()) for r in results), "cases": results}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in value.items() if k not in {"cases", "source_sha256"}}))


def score(capture_path, judgment_path, output):
    captured = json.loads(capture_path.read_bytes())
    raw_judgments = json.loads(judgment_path.read_bytes())["cases"]
    judgments = {c["id"]: c for c in raw_judgments}
    if len(judgments) != len(raw_judgments) or set(judgments) != {r["case"]["id"] for r in captured["cases"]}:
        raise ValueError("Judgments must uniquely cover the exact captured case set")
    source_codes = {w["id"] for w in json.loads(default_dataset().read_bytes())["wines"]}
    for judgment in raw_judgments:
        codes = [code for grade in ("best", "acceptable", "weak", "avoid", "unknown") for code in judgment[grade]]
        if set(codes) != source_codes or len(codes) != len(set(codes)):
            raise ValueError("Each judgment must classify every reviewed wine exactly once")
    buckets = {"first_3": lambda e: e["position"] <= 3,
               "first_5": lambda e: e["position"] <= 5,
               "positions_6_10": lambda e: 6 <= e["position"] <= 10,
               "positions_11_plus": lambda e: e["position"] > 10,
               "embedding_only": lambda e: e["selection_source"] == "embedding",
               "all": lambda e: True}
    totals = {b: Counter() for b in buckets}
    cases = []
    for row in captured["cases"]:
        assessment = judgments[row["case"]["id"]]
        grades = {code: grade for grade in ("best", "acceptable", "weak", "avoid", "unknown") for code in assessment[grade]}
        annotated = []
        for entry in row["entries"]:
            grade = grades[entry["code"]]
            for bucket, selects in buckets.items():
                if selects(entry):
                    totals[bucket][grade] += 1
            annotated.append({"code": entry["code"], "name": entry["name"], "producer": entry["producer"],
                "position": entry["position"], "source": entry["selection_source"], "judgment": grade})
        cases.append({"id": row["case"]["id"], "profile": row["effective_profile_id"],
                      "wine_count": len(annotated), "entries": annotated})
    metrics = {}
    for bucket, counts in totals.items():
        count = sum(counts.values())
        metrics[bucket] = {"count": count, **{g: counts[g] for g in ("best", "acceptable", "weak", "avoid", "unknown")},
            "acceptable_or_best_rate": (counts["best"] + counts["acceptable"]) / count if count else None}
    result = {"assessment_kind": "blind_model_editorial_not_panel", "capture_sha256": sha(capture_path),
        "scorer_sha256": sha(Path(__file__)),
        "judgment_sha256": sha(judgment_path), "cases": cases, "metrics": metrics,
        "case_availability": {"cases": len(cases), "nonempty": sum(c["wine_count"] > 0 for c in cases),
                              "min_wines": min(c["wine_count"] for c in cases)}}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--judgments", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.cases:
        capture(args.cases, args.output)
    else:
        score(args.capture, args.judgments, args.output)
