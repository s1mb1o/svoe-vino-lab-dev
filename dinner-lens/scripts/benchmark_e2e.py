#!/usr/bin/env python3
"""Frozen-ground-truth HTTP benchmark. Expected labels are scorer inputs only."""
from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sys
import time

from fastapi.testclient import TestClient

from dinner_lens.api import create_app
from dinner_lens.data import Knowledge, digest
from dinner_lens.embeddings import EmbeddingIndex
from dinner_lens.engine import Engine
from dinner_lens.provider import QwenRecognizer


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


class ReplayRecognizer(QwenRecognizer):
    """Explicitly reuse recorded live outputs after code fixes; never claim new calls."""
    def recognize(self, image):
        path = self.record_directory / (hashlib.sha256(image).hexdigest() + ".json")
        record = json.loads(path.read_text(encoding="utf-8"))
        payload = self.payload(image)
        body = json.dumps(payload, ensure_ascii=False).encode()
        if record["request_sha256"] != hashlib.sha256(body).hexdigest():
            raise RuntimeError("Replay request changed")
        if record.get("record_type") == "recorded_pipeline_failure":
            raise RuntimeError(record["error"])
        return record["parsed"], {k: v for k, v in record.items() if k not in {"parsed", "response"}} | {"replayed": True}


def run(args):
    project = Path(__file__).resolve().parents[1]
    root, output = args.ground_truth_root.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    k = Knowledge(project / "data/pairing-dataset.v1.json", project / "prompts/style-guidance.en.json")
    index = EmbeddingIndex(k, project / "data/index")
    engine = Engine(k, index, cursor_secret=secrets.token_bytes(32))
    records = (args.replay_records or output / "live-api-recognition").resolve()
    recognizer = (ReplayRecognizer if args.replay_records else QwenRecognizer)(
        k, project / "prompts/image-system.en.txt", record_directory=records)
    source_hashes = {str(p.relative_to(project)): sha(p) for p in sorted((project / "src").rglob("*.py"))}
    manifest = {"generated_at": datetime.now(timezone.utc).isoformat(),
                "recognition_mode": "recorded_live_response_replay" if args.replay_records else "fresh_live_api",
                "recognition_records": str(records), "ground_truth_root": str(root),
                "ground_truth_sha256": {}, "source_sha256": source_hashes,
                "benchmark_sha256": sha(__file__),
                "tests_sha256": {str(p.relative_to(project)): sha(p) for p in sorted((project / "tests").glob("*.py"))},
                "dataset_sha256": k.sha256, "index_version": index.version,
                "engine_version": engine.version, "prompt_sha256": recognizer.prompt_sha256,
                "model": "qwen3.8-flash", "instruction_language": "en",
                "catalog_wines": len(k.wines), "wine_vectors": len(k.wines),
                "protocol": "Actual FastAPI request/response surface with real embeddings. Text inputs contain only confirmed dish and structured user constraints. Photo inputs contain only frozen image bytes and empty constraints. No expected labels or approved styles are passed to the service. Every continuation is followed to exhaustion. Expected outputs are read only by scoring code.",
                "limits": ["ASGI HTTP integration, not a deployed reverse proxy or load test.",
                           "The reference data and ground truth share editorial origins; this is a regression test, not an independent sommelier trial.",
                           "Every returned ID and complete returned set are scored against frozen eligibility, not production filter code. Accepted photo nodes use their exact frozen set; wrong nodes use a reference union for diagnostics only. Independent confirmation gates apply. This coarse style oracle does not prove sensory preference.",
                           "Only wines with confirmed required facts can pass; most catalog wines lack confirmed wine_kind.",
                           "Model outputs can vary despite temperature zero; before/after live photo runs are separate draws."]}
    cases = []
    frozen_eligible_by_node = {}
    for group in ["text", "fallbacks", "images"]:
        path = root / f"ground-truth.{group}.jsonl"
        data = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        old = json.loads((root / ("ground-truth.manifest.json" if group == "text" else f"ground-truth.{group}.manifest.json")).read_text(encoding="utf-8"))
        if sha(path) != (old.get("text_ground_truth_sha256") or old["ground_truth_sha256"]):
            raise RuntimeError("Ground truth changed")
        manifest["ground_truth_sha256"][group] = sha(path)
        cases.extend((group, case) for case in data)
        if group != "images":
            frozen_eligible_by_node.update({c["expected"]["resolved_node_id"]: set(c["expected"]["eligible_wine_slugs"]) for c in data if not c["case_id"].startswith("constraint")})
    # Independent oracle: frozen expected ID sets, plus explicit confirmation gates.
    # It deliberately does not call the production rule/profile interpreter.
    source_manifest = json.loads((root / "ground-truth.manifest.json").read_text(encoding="utf-8"))
    if k.sha256 != source_manifest["source_dataset_sha256"]:
        raise RuntimeError("Reference catalog differs from the ground-truth source")
    frozen_data = json.loads(k.path.read_text(encoding="utf-8"))
    frozen_nodes = {n["id"]: n for n in frozen_data["nodes"]}
    frozen_facts = {w["wine_slug"]: {field: w["facts"][field]["value"] for field in ["color", "sweetness"]} for w in frozen_data["wines"]}

    def unconfirmed_style(node_id, slug):
        profile = frozen_nodes[node_id]["pairing_rule"]["profile_id"]
        facts = frozen_facts.get(slug, {})
        return ((profile == "poultry" and facts.get("color") == "red")
                or (profile == "game" and facts.get("color") == "white")
                or (profile == "cheese_general" and facts.get("sweetness") == "sweet")
                or (profile == "dessert_general" and facts.get("color") == "red"))
    save(output / "run.manifest.json", manifest)

    token = secrets.token_urlsafe(32)
    app = create_app(engine, recognizer, api_token=token)
    headers = {"Authorization": "Bearer " + token}
    rows = []
    with TestClient(app) as client:
        def execute(group, case):
            started = time.monotonic()
            inputs = case["input"]
            if group == "images":
                image = (root / inputs["image_path"]).read_bytes()
                if hashlib.sha256(image).hexdigest() != case["provenance"]["image_sha256"]:
                    raise RuntimeError("Frozen image changed")
                payload = {"image_base64": base64.b64encode(image).decode()}
                endpoint = "/v1/recognize-and-recommend"
            else:
                payload = {"confirmed_dish": inputs["confirmed_dish"], "user_constraints": inputs["user_constraints"]}
                endpoint = "/v1/recommendations"
            response = client.post(endpoint, json=payload, headers=headers)
            http_requests = 1
            first = response.json()
            pages, all_slugs, sources, violations = [], [], [], []
            current = first
            while response.status_code == 200:
                slugs = current.get("wine_slugs", [])
                pages.append({"wine_slugs": slugs, "sources": [r["selection_source"] for r in current.get("results", [])],
                              "resolved_node_id": current.get("resolved_node_id"), "profile": current.get("effective_profile_id"),
                              "http_status": response.status_code})
                if set(slugs) & set(all_slugs) or len(set(slugs)) != len(slugs):
                    violations.append("duplicate_wine")
                if current.get("resolved_node_id") != first.get("resolved_node_id") or current.get("effective_profile_id") != first.get("effective_profile_id"):
                    violations.append("context_changed")
                all_slugs.extend(slugs)
                sources.extend(pages[-1]["sources"])
                if first.get("resolved_node_id") in frozen_nodes:
                    if any(unconfirmed_style(first["resolved_node_id"], slug) for slug in slugs):
                        violations.append("unconfirmed_conditional_style")
                if not current.get("next_cursor"):
                    break
                if not slugs or len(pages) > len(k.wines):
                    violations.append("pagination_did_not_progress")
                    break
                response = client.post("/v1/recommendations/more", json={"cursor": current["next_cursor"]}, headers=headers)
                http_requests += 1
                current = response.json()
                if response.status_code != 200:
                    violations.append("continuation_http_failure")
            if "embedding" in sources and "curated" in sources[sources.index("embedding"):]:
                violations.append("curated_after_discovery")
            if first.get("total_eligible") is not None and len(all_slugs) != first["total_eligible"]:
                violations.append("pagination_not_exhaustive")
            producers = [r["producer"] for r in first.get("results", [])]
            if len(producers) != len(set(producers)):
                violations.append("first_page_producer_duplicate")
            record = {"case_id": case["case_id"], "group": group,
                      "ground_truth_case_sha256": hashlib.sha256(json.dumps(case, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                      "input_request_sha256": digest(payload), "http_status": pages[0]["http_status"] if pages else response.status_code,
                      "first_response": first, "pages": pages, "violations": sorted(set(violations)),
                      "total_returned": len(all_slugs), "latency_seconds": round(time.monotonic() - started, 3)}
            record["http_requests"] = http_requests
            save(output / "http-cases" / (case["case_id"] + ".json"), record)
            row = {k: record[k] for k in ["case_id", "group", "http_status", "http_requests", "violations", "total_returned", "latency_seconds"]}
            row["page_count"] = len(pages)
            row["pagination_pass"] = not violations and record["http_status"] == 200
            row["selected_wine_slugs"] = first.get("wine_slugs", [])
            row["resolved_node_id"] = first.get("resolved_node_id")
            reasons = first.get("explanations", [])
            row["explanations_pass"] = {r.get("wine_slug") for r in reasons} == set(row["selected_wine_slugs"]) and all(isinstance(r.get("reason"), str) and r["reason"].strip() for r in reasons)
            if group != "images":
                eligible = set(case["expected"]["eligible_wine_slugs"])
                relevant = set(case["expected"]["editorial_relevant_wine_slugs"])
                selected = row["selected_wine_slugs"]
                complete_eligible = eligible - {s for s in eligible if unconfirmed_style(case["expected"]["resolved_node_id"], s)}
                row.update(node_correct=row["resolved_node_id"] == case["expected"]["resolved_node_id"],
                           frozen_gold_eligibility_pass=all(s in eligible for s in selected),
                           frozen_gold_all_pages_eligibility_pass=all(s in eligible for s in all_slugs),
                           complete_eligible_set_pass=set(all_slugs) == complete_eligible,
                           availability_pass=bool(selected) == bool(eligible),
                           curated_precision_at_3=len(set(selected) & relevant) / 3 if relevant else None)
                row["strict_pass"] = all(row[x] for x in ["pagination_pass", "explanations_pass", "node_correct", "frozen_gold_all_pages_eligibility_pass", "availability_pass", "complete_eligible_set_pass"]) and len(selected) <= 3
            else:
                expected = case["expected"]
                raw = first.get("recognition", {})
                accepted_node = row["resolved_node_id"] in expected["acceptable_visual_node_ids"]
                reference_nodes = [row["resolved_node_id"]] if accepted_node else expected["acceptable_visual_node_ids"]
                reference_eligible = set().union(*(frozen_eligible_by_node[node] - {s for s in frozen_eligible_by_node[node] if unconfirmed_style(node, s)} for node in reference_nodes))
                question = first.get("needs_clarification") is True and bool(first.get("clarification_question"))
                row.update(raw_visual_node_id=raw.get("visual_node_id"),
                           raw_safe=raw.get("visual_node_id") in expected["acceptable_visual_node_ids"],
                           raw_deepest=raw.get("visual_node_id") in expected["maximum_visually_supported_node_ids"],
                           guarded_safe=row["resolved_node_id"] in expected["acceptable_visual_node_ids"],
                           guarded_deepest=row["resolved_node_id"] in expected["maximum_visually_supported_node_ids"],
                           required_question_pass=question if expected["clarification_required"] else True,
                           guardrail_demoted=first.get("resolution", {}).get("guardrail_demoted", False))
                row["reference_union_diagnostic_pass"] = all(s in reference_eligible for s in all_slugs)
                row["frozen_gold_all_pages_eligibility_pass"] = accepted_node and row["reference_union_diagnostic_pass"]
                row["complete_eligible_set_pass"] = accepted_node and set(all_slugs) == reference_eligible
                row["availability_pass"] = bool(row["selected_wine_slugs"]) == bool(reference_eligible)
                row["safe_resolution_and_question_pass"] = row["guarded_safe"] and row["required_question_pass"]
                row["strict_pass"] = all(row[x] for x in ["pagination_pass", "explanations_pass", "guarded_safe", "required_question_pass", "frozen_gold_all_pages_eligibility_pass", "availability_pass", "complete_eligible_set_pass"])
            return row

        for group, case in cases:
            if group != "images":
                rows.append(execute(group, case))
        print("text_and_fallbacks", len(rows), "strict", sum(r["strict_pass"] for r in rows), flush=True)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            jobs = {pool.submit(execute, group, case): case["case_id"] for group, case in cases if group == "images"}
            for job in as_completed(jobs):
                rows.append(job.result())
                print(jobs[job], "strict", rows[-1]["strict_pass"], "pages", rows[-1]["page_count"], flush=True)
    rows.sort(key=lambda row: row["case_id"])

    def aggregate(items):
        fields = ["strict_pass", "pagination_pass", "explanations_pass", "node_correct", "frozen_gold_eligibility_pass", "frozen_gold_all_pages_eligibility_pass", "complete_eligible_set_pass", "availability_pass", "raw_safe", "raw_deepest", "guarded_safe", "guarded_deepest", "required_question_pass", "safe_resolution_and_question_pass"]
        return {"cases": len(items), **{field: {"passed": sum(bool(r[field]) for r in items if field in r), "total": sum(field in r for r in items)} for field in fields if any(field in r for r in items)},
                "http_requests": sum(r["http_requests"] for r in items),
                "curated_precision_at_3": sum(r["curated_precision_at_3"] for r in items if r.get("curated_precision_at_3") is not None) / max(1, sum(r.get("curated_precision_at_3") is not None for r in items)) if items and "curated_precision_at_3" in items[0] else None}
    report = {"manifest": manifest, "complete": len(rows) == 238,
              "text_75": aggregate([r for r in rows if r["group"] == "text" and not r["case_id"].startswith("constraint")]),
              "constraints_20": aggregate([r for r in rows if r["case_id"].startswith("constraint")]),
              "fallbacks_68": aggregate([r for r in rows if r["group"] == "fallbacks"]),
              "images_75": aggregate([r for r in rows if r["group"] == "images"]),
              "all": aggregate(rows), "failed_case_ids": [r["case_id"] for r in rows if not r["strict_pass"]], "cases": rows}
    save(output / "results.e2e.json", report)
    print(json.dumps({k: v for k, v in report.items() if k not in {"manifest", "cases"}}, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ground-truth-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replay-records", type=Path, help="Explicitly replay matching recorded live model requests after code-only fixes")
    parser.add_argument("--workers", type=int, default=4)
    run(parser.parse_args())
