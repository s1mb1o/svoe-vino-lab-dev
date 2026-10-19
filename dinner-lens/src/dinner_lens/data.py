"""Load production pairing knowledge; benchmark labels are never an input."""
from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from pathlib import Path
from typing import Any

PROFILE_STYLE_GATES = {
    "poultry": ("colors", "red", {"attribute": "poultry_style", "op": "in", "value": ["duck", "grilled_dark_meat"]}),
    "game": ("colors", "white", {"attribute": "game_type", "op": "eq", "value": "delicate_feathered_game"}),
    "cheese_general": ("sweetness", "sweet", {"attribute": "cheese_type", "op": "eq", "value": "blue"}),
    "dessert_general": ("colors", "red", {"attribute": "dessert_base", "op": "in", "value": ["cocoa", "chocolate", "dark_berries"]}),
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().replace("ё", "е").split())


def known_number(value: Any) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def predicate(rule: dict, attrs: dict) -> bool:
    """Unknown predicates fail, including inside conjunctions."""
    if "all" in rule:
        return all(predicate(item, attrs) for item in rule["all"])
    if "any" in rule:
        return any(predicate(item, attrs) for item in rule["any"])
    key = rule.get("attribute")
    if key not in attrs or attrs[key] is None:
        return False
    if rule.get("op") == "eq":
        return attrs[key] == rule["value"]
    if rule.get("op") == "in":
        return attrs[key] in rule["value"]
    raise ValueError("Unsupported knowledge predicate")


class Knowledge:
    def __init__(self, path: str | Path, style_path: str | Path):
        self.path = Path(path)
        raw = self.path.read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        data = json.loads(raw)
        self.nodes = {n["id"]: n for n in data["nodes"]}
        self.profiles = {p["id"]: p for p in data["profiles"]}
        if len(self.nodes) != len(data["nodes"]) or len(self.profiles) != len(data["profiles"]):
            raise ValueError("Duplicate knowledge identifier")
        self.modifiers = data["modifier_rules"]
        translations = json.loads(Path(style_path).read_text(encoding="utf-8"))["profiles"]
        self.style_text = {}
        for profile_id, profile in self.profiles.items():
            entry = translations[profile_id]
            expected = hashlib.sha256(profile["embedding_query_text"].encode()).hexdigest()
            if entry["source_input_sha256"] != expected:
                raise ValueError("Style translation is stale: " + profile_id)
            self.style_text[profile_id] = entry["text_en"]
        self.wines = {}
        for doc in data["embedding_documents"]["wines"]:
            payload = dict(doc["payload"])
            slug = doc["wine_slug"]
            if slug in self.wines:
                raise ValueError("Duplicate catalog slug")
            text = doc["text"]
            name = text.removeprefix("Название: ").split(". Цвет: ", 1)[0]
            self.wines[slug] = {
                **payload, "slug": slug, "name": name,
                "description": text, "source_url": doc["evidence"].get("source_url"),
                "evidence": dict(doc["evidence"]),
            }
        for source in data["wines"]:
            slug = source["wine_slug"]
            if slug not in self.wines:
                raise ValueError("Curated wine is absent from active snapshot")
            wine = self.wines[slug]
            facts = source["facts"]
            for key in ("color", "sweetness", "wine_kind", "alcohol_percent", "residual_sugar_g_l"):
                wine[key] = facts[key]["value"]
            wine.update(name=source["name"], producer=source["producer"],
                        reported_grapes=facts["grapes_reported"]["value"],
                        grape_list_completeness=facts["grapes_reported"].get("completeness", "not_verified"),
                        description=source["style_summary"]["text_ru"], source_url=source["source_url"],
                        price=source["price"], stock=source["stock"])
            wine["evidence"]["curated_facts"] = facts
        self.curated_slugs = {w["wine_slug"] for w in data["wines"]}
        covered_gates = set()
        for node in self.nodes.values():
            overrides = node["pairing_rule"].get("eligibility_overrides", {})
            base_eligibility = self.profiles[node["pairing_rule"]["profile_id"]]["eligibility"]
            if (type(overrides) is not dict or set(overrides) - {"colors", "sweetness", "wine_kinds"}
                    or any(type(values) is not list or not values or any(type(v) is not str or v not in base_eligibility[field] for v in values)
                           for field, values in overrides.items())):
                raise ValueError("Node eligibility refinements must narrow existing categories: " + node["id"])
            for entry in node["curated"]:
                if entry["wine_slug"] not in self.wines:
                    raise ValueError("Curated selection references an unknown wine")
                conditions = entry.get("applicability_conditions", [])
                if not conditions:
                    continue
                profile_id = node["pairing_rule"]["profile_id"]
                gate = PROFILE_STYLE_GATES.get(profile_id)
                semantic_conditions = [{k: v for k, v in rule.items() if k != "unknown_action"} for rule in conditions]
                if (gate is None or semantic_conditions != [gate[2]]
                        or self.wines[entry["wine_slug"]].get({"colors": "color", "sweetness": "sweetness"}[gate[0]]) != gate[1]
                        or gate[1] not in self.profiles[profile_id]["eligibility"][gate[0]]):
                    raise ValueError("Conditional editorial style has no matching profile-wide gate: " + node["id"])
                covered_gates.add(profile_id)
        if covered_gates != set(PROFILE_STYLE_GATES):
            raise ValueError("Profile-wide gates no longer match the reference conditions")
        self.aliases: dict[str, set[str]] = {}
        for node_id, node in self.nodes.items():
            if node["parent_id"] is not None and node["parent_id"] not in self.nodes:
                raise ValueError("Missing taxonomy parent")
            for label in [node["label_ru"], *node.get("aliases", [])]:
                self.aliases.setdefault(normalize(label), set()).add(node_id)
            for entry in node["curated"]:
                if entry["wine_slug"] not in self.wines:
                    raise ValueError("Curated selection references an unknown wine")
        self.disambiguations = {normalize(r["phrase"]): r for r in data["disambiguation_rules"]}
        self.catalog_version = data["catalog_snapshot"]["version"] if "version" in data["catalog_snapshot"] else digest(data["catalog_snapshot"])
        self.suitability_policy = data.get("suitability_policy")
        self.style_families = {}
        self.wine_style_annotations = {}
        if self.suitability_policy is not None:
            policy = self.suitability_policy
            families = set(policy["families"])
            if set(policy["profiles"]) != set(self.profiles):
                raise ValueError("Style policy must cover every profile")
            for allowed in [*policy["profiles"].values(), *policy["node_family_overrides"].values(), *policy["node_family_extensions"].values()]:
                if not allowed or not set(allowed).issubset(families):
                    raise ValueError("Unknown or empty approved style family")
            if not (set(policy["node_family_overrides"]) | set(policy["node_family_extensions"])).issubset(self.nodes):
                raise ValueError("Unknown quality-policy node")
            for annotation in policy["wines"]:
                slug = annotation["wine_slug"]
                if slug not in self.curated_slugs or slug in self.style_families or annotation["family"] not in families:
                    raise ValueError("Invalid reviewed wine style annotation")
                expected = hashlib.sha256(self.wines[slug]["description"].encode()).hexdigest()
                if annotation["source_description_sha256"] != expected:
                    raise ValueError("Reviewed style annotation is stale: " + slug)
                self.style_families[slug] = annotation["family"]
                self.wine_style_annotations[slug] = annotation
            if policy.get("qualitative_guards"):
                guards = policy["qualitative_guards"]
                marker_values = {"dominant_herbal", "round_ripe_white", "round_structured_red", "forest_or_earth", "vanilla_full_white", "savory_smoke", "pepper_moderate_tannin"}
                for key, allowed in [("acid_conflicts", {"unknown", "soft", "moderate", "fresh", "pronounced"}),
                        ("mushroom_excluded_markers", marker_values), ("raw_shellfish_excluded_markers", marker_values),
                        ("creamy_excluded_markers", marker_values), ("glaze_excluded_markers", marker_values),
                        ("creamy_glaze_excluded_markers", marker_values),
                        ("required_acidity_for_high_acid", {"fresh", "pronounced"}),
                        ("creamy_profiles", set(self.profiles)), ("creamy_excluded_families", families),
                        ("raw_shellfish_excluded_body", {"unknown", "light", "medium", "full"})]:
                    if type(guards.get(key)) is not list or not set(guards[key]).issubset(allowed):
                        raise ValueError("Invalid qualitative guard: " + key)
                minimum = guards.get("minimum_body_by_profile")
                excluded = guards.get("profile_excluded_families")
                if (type(minimum) is not dict or not set(minimum).issubset(self.profiles)
                        or any(v not in {"light", "medium", "full"} for v in minimum.values())
                        or type(excluded) is not dict or not set(excluded).issubset(self.profiles)
                        or any(type(v) is not list or not set(v).issubset(families) for v in excluded.values())):
                    raise ValueError("Invalid qualitative profile constraints")
                for node in self.nodes.values():
                    context = node.get("qualitative_pairing_context", {})
                    if (set(context) != {"mushroom_umami", "raw_shellfish"}
                            or any(type(value) is not bool for value in context.values())):
                        raise ValueError("Invalid selected recipe qualitative context")
                if set(self.wine_style_annotations) != self.curated_slugs:
                    raise ValueError("Qualitative policy must cover every reviewed wine")
                for annotation in self.wine_style_annotations.values():
                    traits = annotation.get("qualitative_traits", {})
                    if (set(traits) != {"body", "acidity", "markers"}
                            or traits["body"] not in {"unknown", "light", "medium", "full"}
                            or traits["acidity"] not in {"unknown", "soft", "moderate", "fresh", "pronounced"}
                            or type(traits["markers"]) is not list
                            or any(m not in marker_values for m in traits["markers"])):
                        raise ValueError("Invalid reviewed qualitative traits")

    def resolve(self, confirmed_name: str) -> str | None:
        label = normalize(confirmed_name)
        # Exact canonical labels take precedence over aliases and ambiguity hints.
        exact = [n["id"] for n in self.nodes.values() if normalize(n["label_ru"]) == label]
        if len(exact) == 1:
            return exact[0]
        rule = self.disambiguations.get(label)
        if rule:
            return rule.get("fallback_node_id")
        matches = self.aliases.get(label, set())
        return next(iter(matches)) if len(matches) == 1 else None

    def effective_profile(self, node_id: str, attrs: dict) -> tuple[str, list[str], list[str], dict]:
        original = self.nodes[node_id]["pairing_rule"]["profile_id"]
        if self.suitability_policy:
            attrs = self.rule_context(node_id, attrs)["effective_rule_attributes"]
        matched = sorted((r for r in self.modifiers if predicate(r["when"], attrs)),
                         key=lambda r: r["priority"], reverse=True)
        replacements = [r for r in matched if "replace_profile_id" in r["action"]]
        profile_id = replacements[0]["action"]["replace_profile_id"] if replacements else original
        dessert = attrs.get("is_dessert") is True or (self.suitability_policy and "desserts" in self.nodes[node_id]["hierarchy_path"])
        if self.suitability_policy and not dessert:
            if profile_id == "sweet_glaze":
                if attrs.get("poultry_style") == "duck":
                    profile_id = "sweet_glaze_duck"
                elif ("meat" in self.nodes[node_id]["hierarchy_path"] or "game" in self.nodes[node_id]["hierarchy_path"]
                        or original in {"ribeye", "meat_steak", "grilled_meat", "lamb", "venison", "game", "braised_beef", "meat_general"}):
                    profile_id = "sweet_glaze_rich_meat"
            elif (profile_id in {"spicy", "spicy_sour"} and attrs.get("protein_family") in {"meat", "game"}
                  and attrs.get("sauce_sweetness") not in {"medium", "high"}):
                profile_id = "spicy_meat"
            elif profile_id == "white_butter_cream" and attrs.get("poultry_style") == "duck":
                # Cream must not erase a selected duck/berry style. The original
                # profile already supports duck weight and its source references.
                profile_id = original
        if dessert:
            profile_id = original if "desserts" in self.nodes[node_id]["hierarchy_path"] else "dessert_general"
        boosts = sorted({trait for r in matched for trait in r["action"].get("boost_target_traits", [])})
        eligibility = dict(self.profiles[profile_id]["eligibility"])
        if dessert:
            eligibility["sweetness"] = ["sweet"]
        if self.suitability_policy and attrs.get("heat") in {"medium", "high"}:
            eligibility["max_alcohol_percent"] = min(eligibility.get("max_alcohol_percent") or 12.5, 12.5)
        # These profile-wide styles require the same confirmation as their editorial
        # examples. Blocking only a particular curated slug lets siblings bypass it.
        if profile_id in PROFILE_STYLE_GATES:
            field, conditional_value, condition = PROFILE_STYLE_GATES[profile_id]
            if not predicate(condition, attrs):
                eligibility[field] = [v for v in eligibility[field] if v != conditional_value]
        if profile_id == original:
            for field, allowed in self.nodes[node_id]["pairing_rule"].get("eligibility_overrides", {}).items():
                eligibility[field] = [v for v in eligibility[field] if v in allowed]
        applied = [r["id"] for r in matched if "replace_profile_id" not in r["action"]]
        if replacements and not dessert:
            applied.insert(0, replacements[0]["id"])
        return profile_id, boosts, applied, eligibility

    def rule_context(self, node_id: str, attrs: dict) -> dict:
        """Recipe style defaults inform pairing rules; they never become image facts."""
        defaults = {}
        if self.suitability_policy:
            profile = self.nodes[node_id]["pairing_rule"]["profile_id"]
            defaults.update(self.suitability_policy["profile_context_defaults"].get(profile, {}))
            defaults.update(self.nodes[node_id].get("pairing_reference_attributes", {}))
        return {"selected_reference_attributes": defaults, "user_confirmed_attributes": dict(attrs),
                "effective_rule_attributes": {**defaults, **attrs}, "reference_attributes_are_visual_facts": False}

    def style_rejection(self, slug: str, node_id: str, profile_id: str, attrs: dict | None = None) -> str | None:
        if not self.suitability_policy:
            return None
        family = self.style_families.get(slug)
        if family is None:
            return "wine_style_not_reviewed"
        policy = self.suitability_policy
        allowed = set(policy["profiles"][profile_id])
        if profile_id == self.nodes[node_id]["pairing_rule"]["profile_id"]:
            allowed = set(policy["node_family_overrides"].get(node_id, allowed))
            allowed.update(policy["node_family_extensions"].get(node_id, []))
        if family not in allowed:
            return "outside_reviewed_pairing_style"
        guards = policy.get("qualitative_guards")
        if not guards:
            return None
        annotation = self.wine_style_annotations[slug]
        traits = annotation["qualitative_traits"]
        context = self.rule_context(node_id, attrs or {})["effective_rule_attributes"]
        if context.get("acidity") == "high" and traits["acidity"] not in guards["required_acidity_for_high_acid"]:
            return "insufficient_acidity_evidence_for_acidic_sauce"
        body = {"unknown": 0, "light": 1, "medium": 2, "full": 3}
        minimum = guards["minimum_body_by_profile"].get(profile_id)
        if minimum and body[traits["body"]] < body[minimum]:
            return "insufficient_weight_for_selected_profile"
        if family in guards["profile_excluded_families"].get(profile_id, []):
            return "style_conflicts_with_selected_profile"
        if profile_id in guards["creamy_profiles"]:
            if (set(traits["markers"]) & set(guards["creamy_excluded_markers"])
                    or family in guards["creamy_excluded_families"] or traits["body"] == "light"):
                return "style_conflicts_with_creamy_texture"
        if profile_id == "sweet_glaze" and family == "semisweet_white" and context.get("sauce_sweetness") != "high":
            return "dessert_like_sweetness_for_savory_glaze"
        if profile_id == "spicy" and context.get("sauce_sweetness") not in {"medium", "high"} and family == "semisweet_white":
            return "excess_sweetness_for_unsweetened_spicy_food"
        if profile_id == "sweet_glaze_rich_meat":
            if set(traits["markers"]) & set(guards["glaze_excluded_markers"]):
                return "savory_earthy_style_conflicts_with_fruit_glaze"
            if context.get("fatty_cream_sauce") and set(traits["markers"]) & set(guards["creamy_glaze_excluded_markers"]):
                return "tannin_conflicts_with_creamy_sweet_glaze"
        recipe = self.nodes[node_id].get("qualitative_pairing_context", {})
        sauce_dominates = context.get("heat") in {"medium", "high"} or context.get("sauce_sweetness") in {"medium", "high"}
        if not sauce_dominates:
            if recipe.get("mushroom_umami") and set(traits["markers"]) & set(guards["mushroom_excluded_markers"]):
                return "style_overwhelms_mushroom_umami"
            if recipe.get("raw_shellfish") and not context.get("fatty_cream_sauce"):
                if (traits["body"] in guards["raw_shellfish_excluded_body"]
                        or set(traits["markers"]) & set(guards["raw_shellfish_excluded_markers"])):
                    return "style_overwhelms_raw_shellfish"
        return None

    def query(self, profile_id: str, boosts: list[str]) -> tuple[str, str]:
        key = profile_id + ("|acid" if boosts else "")
        text = self.style_text[profile_id]
        if boosts:
            text += " Prioritize freshness and noticeable acidity."
        return key, text

    def embedding_documents(self) -> list[dict]:
        docs = []
        for slug, wine in sorted(self.wines.items()):
            facts = {key: wine.get(key) for key in ("name", "color", "sweetness", "wine_kind", "reported_grapes", "description")}
            docs.append({"id": "wine:" + slug, "text": canonical(facts), "kind": "wine"})
        for profile_id in sorted(self.profiles):
            for boosts in ([], ["acidity_present", "freshness"]):
                key, text = self.query(profile_id, boosts)
                docs.append({"id": "query:" + key, "text": text, "kind": "query"})
        return docs
