"""Exercise every v2 text contract through the authenticated HTTP implementation.

No LLM is used here: names are user-confirmed inputs. Frozen original image scores
must not be attributed to this expanded taxonomy without a separate fresh run.
"""
import argparse
import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from dinner_lens.api import create_app
from dinner_lens.data import Knowledge
from dinner_lens.embeddings import EmbeddingIndex
from dinner_lens.engine import Engine
from dinner_lens.paths import bundle_root, default_dataset, default_index


class NoRecognizer:
    def recognize(self, image):
        raise AssertionError("A text contract must not call an LLM")


def run(output):
    root = bundle_root()
    # Frozen v2 contract reproduction; v3 has a separate source-linked style oracle.
    data_path = root / "data/pairing-dataset.v2.json"
    truth_path = root / "data/ground-truth.expanded-text.v2.jsonl"
    validation = json.loads((root / "data/pairing-dataset.validation.json").read_bytes())
    assert hashlib.sha256(data_path.read_bytes()).hexdigest() == validation["dataset_sha256"]
    assert hashlib.sha256(truth_path.read_bytes()).hexdigest() == validation["ground_truth_sha256"]
    truth = [json.loads(line) for line in truth_path.read_text(encoding="utf-8").splitlines()]
    knowledge = Knowledge(data_path, root / "prompts/style-guidance.en.json")
    index = EmbeddingIndex(knowledge, root / "data/index.v2")
    engine = Engine(knowledge, index, cursor_secret=b"expanded-text-test-secret-at-least-32-bytes")
    token = "expanded-text-test-token-at-least-24-characters"
    rows = []
    with TestClient(create_app(engine, NoRecognizer(), api_token=token)) as client:
        client.headers["Authorization"] = "Bearer " + token
        for case in truth:
            failures = []
            response = client.post("/v1/recommendations", json={"confirmed_dish": case["input_label"]})
            if response.status_code != 200:
                failures.append("http_status")
            body = response.json()
            if body.get("resolved_node_id") != case["expected_node_id"]:
                failures.append("node")
            if case.get("needs_clarification") and (not body.get("needs_clarification") or not body.get("clarification_question")):
                failures.append("missing_clarification")
            pages = [body]
            while pages[-1].get("next_cursor"):
                if len(pages) > 100:
                    raise RuntimeError("Nonterminating pagination")
                following = client.post("/v1/recommendations/more", json={"cursor": pages[-1]["next_cursor"]})
                assert following.status_code == 200
                pages.append(following.json())
            entries = [e for p in pages for e in p["results"]]
            slugs = [e["wine_slug"] for e in entries]
            if case["expected_node_id"] is None:
                if entries or body.get("status") != "needs_category" or not body.get("needs_clarification"):
                    failures.append("unknown_confirmation")
            elif "expected_profile_id" in case:
                if set(slugs) != set(case["expected_eligible_wine_slugs"]):
                    failures.append("complete_eligibility")
                if len(slugs) != len(set(slugs)):
                    failures.append("duplicates")
                if any(p["resolved_node_id"] != case["expected_node_id"] or p["effective_profile_id"] != case["expected_profile_id"] for p in pages):
                    failures.append("context_drift")
                sources = [e["selection_source"] for e in entries]
                if "curated" in sources and "embedding" in sources and max(i for i,s in enumerate(sources) if s == "curated") > sources.index("embedding"):
                    failures.append("editorial_order")
                actual_curated = {e["wine_slug"] for e in entries if e["selection_source"] == "curated"}
                if actual_curated != set(case["expected_curated_wine_slugs"]):
                    failures.append("editorial_membership")
                if any(not e["reason"] or not e["source_url"] for e in entries):
                    failures.append("missing_explanation_evidence")
                if len({e["producer"] for e in body["results"]}) != len(body["results"]):
                    failures.append("initial_producer_diversity")
            rows.append({"id": case["id"], "resolved_node_id": body.get("resolved_node_id"),
                "pages": len(pages), "wine_count": len(entries), "failures": failures, "passed": not failures})
    result = {"mode": "authenticated ASGI HTTP, confirmed names, no LLM calls", "passed": all(r["passed"] for r in rows),
        "cases": len(rows), "passed_cases": sum(r["passed"] for r in rows),
        "dataset_sha256": knowledge.sha256, "ground_truth_sha256": validation["ground_truth_sha256"],
        "new_photo_accuracy_measured": False, "independent_sensory_quality_measured": False, "results": rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k != "results"}))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
