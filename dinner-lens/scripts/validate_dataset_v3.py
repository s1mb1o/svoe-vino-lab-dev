"""Validate v3 data and all 320 canonical routes/pages against source categories.

This is a contract check, not the blind suitability assessment. Its expected ID
sets are projected from JSON source facts and reviewed style annotations without
calling production admission/profile/style-rejection functions.
"""
import hashlib
import json
from pathlib import Path

import jsonschema
from fastapi.testclient import TestClient

from dinner_lens.api import create_app
from dinner_lens.data import Knowledge
from dinner_lens.embeddings import EmbeddingIndex
from dinner_lens.engine import Engine
from dinner_lens.paths import bundle_root, default_dataset, default_index, default_style


def run():
    root = bundle_root()
    path = root / "data/pairing-dataset.v3.json"
    data = json.loads(path.read_bytes())
    base = json.loads((root / "data/pairing-dataset.v2.json").read_bytes())
    jsonschema.Draft202012Validator(json.loads((root / "data/pairing-dataset.v3.schema.json").read_bytes())).validate(data)
    for key in ("wines", "catalog_snapshot", "root_class_ids", "disambiguation_rules"):
        assert data[key] == base[key], key
    assert data["embedding_documents"]["wines"] == base["embedding_documents"]["wines"]
    assert len(data["nodes"]) == 320 and len(data["profiles"]) == 68
    baseline_nodes = {n["id"]: n for n in base["nodes"]}
    profiles = {p["id"]: p for p in data["profiles"]}
    wines = {w["wine_slug"]: w for w in data["wines"]}
    policy = data["suitability_policy"]
    families = {a["wine_slug"]: a["family"] for a in policy["wines"]}
    assert set(families) == set(wines) and len(families) == len(policy["wines"]) == 49
    source_ids = {s["id"] for s in data["sources"]}
    assert len(source_ids) == len(data["sources"])
    for profile in profiles.values():
        assert set(profile["source_refs"]).issubset(source_ids)
    k = Knowledge(path, default_style())
    engine = Engine(k, EmbeddingIndex(k, root / "data/index.v3"), cursor_secret=b"full-v3-contract-validation-secret-at-least-32-bytes")
    token = "full-v3-validation-token-at-least-24-characters"
    results = []
    with TestClient(create_app(engine, None, api_token=token)) as client:
        client.headers["Authorization"] = "Bearer " + token
        for node in data["nodes"]:
            old = baseline_nodes[node["id"]]
            for field in ("label_ru", "parent_id", "hierarchy_path", "aliases", "kind"):
                assert node[field] == old[field], (node["id"], field)
            assert 3 <= len(node["curated"]) <= 5
            assert all(c["wine_slug"] in wines for c in node["curated"])
            assert set(node["pairing_rule"]["source_refs"]).issubset(source_ids)
            assert set(node.get("recipe_source_refs", [])).issubset(source_ids)
            profile_id = node["pairing_rule"]["profile_id"]
            eligibility = dict(profiles[profile_id]["eligibility"])
            eligibility.update(node["pairing_rule"].get("eligibility_overrides", {}))
            # Four unchanged default-confirmation gates; named composite profiles
            # already encode the sauce/body selection without hidden API flags.
            if profile_id == "poultry" and node["pairing_reference_attributes"].get("poultry_style") not in {"duck", "grilled_dark_meat"}:
                eligibility["colors"] = [c for c in eligibility["colors"] if c != "red"]
            if profile_id == "game":
                eligibility["colors"] = [c for c in eligibility["colors"] if c != "white"]
            if profile_id == "cheese_general":
                eligibility["sweetness"] = [s for s in eligibility["sweetness"] if s != "sweet"]
            if profile_id == "dessert_general":
                eligibility["colors"] = [c for c in eligibility["colors"] if c != "red"]
            allowed = set(policy["node_family_overrides"].get(node["id"], policy["profiles"][profile_id]))
            allowed.update(policy["node_family_extensions"].get(node["id"], []))
            expected = set()
            for slug, wine in wines.items():
                facts = {key: fact["value"] for key, fact in wine["facts"].items()}
                if (facts["color"] in eligibility["colors"] and facts["sweetness"] in eligibility["sweetness"]
                    and facts["wine_kind"] in eligibility["wine_kinds"] and families[slug] in allowed
                    and (eligibility.get("max_alcohol_percent") is None or facts["alcohol_percent"] <= eligibility["max_alcohol_percent"])):
                    expected.add(slug)
            response = client.post("/v1/recommendations", json={"confirmed_dish": node["label_ru"]})
            assert response.status_code == 200, node["id"]
            first = page = response.json()
            actual = []
            stages = []
            page_count = 0
            while True:
                page_count += 1
                assert page_count < 100
                assert page["resolved_node_id"] == node["id"] and page["effective_profile_id"] == profile_id, node["id"]
                actual.extend(page["wine_slugs"])
                stages.extend(row["selection_source"] for row in page["results"])
                if not page["next_cursor"]:
                    break
                response = client.post("/v1/recommendations/more", json={"cursor": page["next_cursor"]})
                assert response.status_code == 200
                page = response.json()
            assert set(actual) == expected and len(actual) == len(set(actual)) and len(actual) >= 3, node["id"]
            assert len(actual) == first["total_eligible"]
            assert len({r["producer"] for r in first["results"]}) == len(first["results"])
            if "embedding" in stages:
                assert "curated" not in stages[stages.index("embedding"):]
            results.append({"node_id": node["id"], "profile": profile_id, "wine_count": len(actual), "pages": page_count, "passed": True})
    result = {"passed": True, "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "canonical_cases": len(results), "pages": sum(r["pages"] for r in results),
        "scope": data["scope"], "profiles": len(profiles), "results": results,
        "taste_validation": "Separate blind model judgment reports; these contract checks do not establish sensory quality."}
    (root / "data/pairing-dataset.v3.validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"results", "scope"}}))


if __name__ == "__main__":
    run()
