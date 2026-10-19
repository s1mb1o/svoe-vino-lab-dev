"""Validate editorial coverage and export text contracts without running a recognizer.

The style oracle uses frozen source facts and approved categories directly; it does
not call production admission, modifier or ranking functions. Resolution compatibility
is separately audited with the real v1 and v2 resolvers. This is
contract ground truth, not independent sensory or photographic annotation.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import unicodedata

ROOT = Path(__file__).resolve().parents[1]


def norm(s):
    return " ".join(unicodedata.normalize("NFKC", s).casefold().replace("ё", "е").split())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate():
    path = ROOT / "data/pairing-dataset.v2.json"
    data = json.loads(path.read_bytes())
    base = json.loads((ROOT / "data/pairing-dataset.v1.json").read_bytes())
    spec = json.loads((ROOT / "data/expansion.v2.json").read_bytes())
    import jsonschema
    jsonschema.Draft202012Validator(json.loads((ROOT / "data/pairing-dataset.schema.json").read_bytes())).validate(data)
    nodes = {n["id"]: n for n in data["nodes"]}
    profiles = {p["id"]: p for p in data["profiles"]}
    wines = {w["wine_slug"]: w for w in data["wines"]}
    payloads = {d["wine_slug"]: d["payload"] for d in data["embedding_documents"]["wines"]}
    assert len(nodes) == len(data["nodes"])
    assert len({n["original_number"] for n in nodes.values() if n["kind"] == "dish"}) == 200
    assert data["nodes"][:len(base["nodes"])] == base["nodes"], "Existing taxonomy nodes changed"
    for key in ("profiles", "wines", "catalog_snapshot", "modifier_rules", "root_class_ids"):
        assert data[key] == base[key], key + " changed"
    assert data["embedding_documents"]["wines"] == base["embedding_documents"]["wines"]
    assert data["evaluation_cases"]["recognition"] == base["evaluation_cases"]["recognition"]
    source_ids = {s["id"] for s in data["sources"]}
    assert len(source_ids) == len(data["sources"])
    for owner in [*nodes.values(), *profiles.values()]:
        for ref in [*owner.get("source_refs", []), *owner.get("recipe_source_refs", []), *owner.get("pairing_rule", {}).get("source_refs", [])]:
            assert ref in source_ids, "Dangling source reference: " + ref
    assert set(data["family_evidence_refs"]).issubset(source_ids)
    assert data["embedding_documents"]["query_profiles"] == [n["embedding_query_document"] for n in nodes.values()]
    assert len({norm(n["label_ru"]) for n in nodes.values()}) == len(nodes), "Canonical label collision"
    conditional_styles = {"poultry": ("colors", "red"), "game": ("colors", "white"),
                          "cheese_general": ("sweetness", "sweet"), "dessert_general": ("colors", "red")}

    def approved(slug, profile_id, *, confirmed_style=False, node=None):
        wine = wines[slug]
        rules = profiles[profile_id]["eligibility"]
        facts = {k: v["value"] for k, v in wine["facts"].items()}
        if wine["catalog_state"] != "Active" or payloads[slug]["discovery_eligible"] is not True:
            return False
        for fact, field in (("color", "colors"), ("sweetness", "sweetness"), ("wine_kind", "wine_kinds")):
            if facts[fact] not in rules[field]:
                return False
            refined = node.get("pairing_rule", {}).get("eligibility_overrides", {}) if node else {}
            if field in refined and facts[fact] not in refined[field]:
                return False
            if not confirmed_style and profile_id in conditional_styles:
                blocked_field, blocked_value = conditional_styles[profile_id]
                if field == blocked_field and facts[fact] == blocked_value:
                    return False
        maximum = rules.get("max_alcohol_percent")
        return maximum is None or facts["alcohol_percent"] is not None and facts["alcohol_percent"] <= maximum

    aliases = defaultdict(set)
    contracts = []
    for node in nodes.values():
        ancestry = [node["id"]]
        parent = node["parent_id"]
        while parent is not None:
            assert parent in nodes and parent not in ancestry, "Invalid taxonomy graph"
            assert nodes[parent]["kind"] != "dish"
            ancestry.insert(0, parent)
            parent = nodes[parent]["parent_id"]
        assert ancestry == node["hierarchy_path"] and node["depth"] == len(ancestry) - 1
        assert ancestry[0] in data["root_class_ids"]
        assert 3 <= len(node["curated"]) <= 5
        assert len({c["wine_slug"] for c in node["curated"]}) == len(node["curated"])
        assert [c["rank"] for c in node["curated"]] == list(range(1, len(node["curated"]) + 1))
        profile_id = node["pairing_rule"]["profile_id"]
        for choice in node["curated"]:
            assert choice["wine_slug"] in wines
            assert approved(choice["wine_slug"], profile_id, confirmed_style=bool(choice["applicability_conditions"]), node=node), node["id"]
            assert len(choice["explanation_ru"]) >= 35
        default_curated = [c["wine_slug"] for c in node["curated"] if not c["applicability_conditions"]]
        assert len(default_curated) >= 3
        assert len({wines[s]["producer"] for s in default_curated}) >= 3, node["id"]
        for label in [node["label_ru"], *node["aliases"]]:
            aliases[norm(label)].add(node["id"])
        contracts.append({"id": "canonical:" + node["id"], "input_label": node["label_ru"],
            "expected_node_id": node["id"], "expected_profile_id": profile_id,
            "expected_eligible_wine_slugs": sorted(s for s in wines if approved(s, profile_id, node=node)),
            "expected_curated_wine_slugs": default_curated, "introduced_in": node.get("introduced_in", "1.0.0"),
            "oracle_type": "editorial_text_contract_not_photo_or_sensory_ground_truth"})
    disambiguations = {norm(r["phrase"]): r for r in data["disambiguation_rules"]}
    assert len(disambiguations) == len(data["disambiguation_rules"])
    canonical_labels = {norm(n["label_ru"]): n["id"] for n in nodes.values()}
    unresolved_collisions = {a: sorted(ids) for a, ids in aliases.items()
        if len(ids) > 1 and a not in disambiguations and a not in canonical_labels}
    # Ambiguous aliases may exist in frozen v1; fail on new collisions only.
    old_aliases = defaultdict(set)
    for n in base["nodes"]:
        for label in [n["label_ru"], *n["aliases"]]:
            old_aliases[norm(label)].add(n["id"])
    assert all(set(ids) == old_aliases[a] for a, ids in unresolved_collisions.items()), unresolved_collisions
    new_collisions = {a: sorted(ids) for a, ids in aliases.items() if len(ids) > 1 and ids != old_aliases[a]}
    from dinner_lens.data import Knowledge
    old_knowledge = Knowledge(ROOT / "data/pairing-dataset.v1.json", ROOT / "prompts/style-guidance.en.json")
    new_knowledge = Knowledge(path, ROOT / "prompts/style-guidance.en.json")
    old_phrases = sorted(old_aliases)
    resolution_changes = [{"phrase": p, "v1": old_knowledge.resolve(p), "v2": new_knowledge.resolve(p)}
        for p in old_phrases if old_knowledge.resolve(p) != new_knowledge.resolve(p)]
    expected_changes = [{k: e[k] for k in ("phrase", "v1", "v2")} for e in spec["superseded_v1_resolutions"]]
    assert resolution_changes == expected_changes, "Unapproved legacy resolution change"
    for rule in data["disambiguation_rules"]:
        phrase = norm(rule["phrase"])
        fallback = rule.get("fallback_node_id")
        assert fallback is None or fallback in nodes
        if "must_not_resolve_to" in rule:
            assert rule["must_not_resolve_to"] in nodes, "Dangling forbidden ID"
            assert fallback != rule["must_not_resolve_to"]
        if phrase in canonical_labels:
            assert fallback == canonical_labels[phrase], "Canonical label defeats disambiguation: " + phrase
        if rule.get("introduced_in") == "2.0.0":
            if fallback is not None:
                assert nodes[fallback]["kind"] != "dish"
                if rule["fallback_relation"] == "ancestor":
                    assert fallback in nodes[rule["must_not_resolve_to"]]["hierarchy_path"]
                else:
                    assert rule["fallback_relation"] == "cross_branch_generalization"
                    assert any(e["phrase"] == rule["phrase"] and e["fallback_node_id"] == fallback for e in spec["cross_branch_fallbacks"])
                    assert rule["generalization_reason"]
            else:
                assert rule["fallback_relation"] == "no_category_until_confirmed"
            contracts.append({"id": "ambiguity:" + phrase, "input_label": rule["phrase"],
                "expected_node_id": fallback, "must_not_resolve_to": rule["must_not_resolve_to"],
                "needs_clarification": True,
                "oracle_type": "manually_authored_ambiguity_contract"})
    actual = Counter(n["kind"] for n in nodes.values())
    assert (actual["dish"], actual["class"], actual["fallback_class"]) == (200, 104, 16)
    assert data["scope"]["total_nodes"] == len(nodes)
    assert data["scope"]["curated_wine_links"] == sum(len(n["curated"]) for n in nodes.values())
    assert data["scope"]["dish_groups"] == dict(Counter(n["group"] for n in nodes.values() if n["kind"] == "dish"))
    assert data["scope"]["intermediate_classes"] == actual["class"]
    assert data["scope"]["dishes"] == actual["dish"]
    assert len(data["root_class_ids"]) == actual["fallback_class"]
    data["validation_summary"] = {"passed": True, "report_file": "pairing-dataset.validation.json",
        "validated_scope": "Schema, graph, unchanged v1 nodes and catalog facts, IDs, 3–5 editorial wines per node, default style eligibility, producer diversity and text/ambiguity contracts. No visual or sensory accuracy claim."}
    save(path, data)
    truth = ROOT / "data/ground-truth.expanded-text.v2.jsonl"
    truth.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in contracts), encoding="utf-8")
    report = {"passed": True, "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "base_dataset_sha256": hashlib.sha256((ROOT / "data/pairing-dataset.v1.json").read_bytes()).hexdigest(),
        "ground_truth_sha256": hashlib.sha256(truth.read_bytes()).hexdigest(), "scope": data["scope"],
        "added_dish_ids": [r[0] for r in spec["dishes"]], "added_class_ids": [r[0] for r in spec["classes"]],
        "root_dish_counts": [{"root": r, "before": sum(n["kind"] == "dish" and r in n["hierarchy_path"] for n in base["nodes"]),
            "after": sum(n["kind"] == "dish" and r in n["hierarchy_path"] for n in nodes.values())} for r in data["root_class_ids"]],
        "empty_roots_after": [r for r in data["root_class_ids"] if not any(n["kind"] == "dish" and r in n["hierarchy_path"] for n in nodes.values())],
        "legacy_alias_collisions": unresolved_collisions, "new_alias_collisions": new_collisions,
        "legacy_phrases_audited": len(old_phrases), "superseded_v1_resolutions": spec["superseded_v1_resolutions"],
        "family_evidence_only_sources": data["family_evidence_refs"],
        "contract_cases": len(contracts), "visual_benchmark": "Unchanged original 75 photos; expanded taxonomy not evaluated on new photos.",
        "wine_coverage": "Unchanged: 49 reviewed wines from 12 producers, 2093 catalog embedding documents, 65 profiles."}
    save(ROOT / "data/pairing-dataset.validation.json", report)
    print(json.dumps({"passed": True, "nodes": len(nodes), "text_contracts": len(contracts), "empty_roots": report["empty_roots_after"]}))


if __name__ == "__main__":
    validate()
