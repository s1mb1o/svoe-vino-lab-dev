"""Version the sauce/continuation quality policy without modifying frozen v1/v2.

Style families are editorial classifications from reviewed source descriptions,
not laboratory measurements. They define a conservative recommendation envelope;
embeddings rank only wines inside that envelope. No model is called at runtime.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

FAMILIES = {
    "robust_red": "R1 R3 G4", "oaky_robust_red": "R2",
    "rounded_red": "R4 R5 G2 G3", "delicate_red": "P1 P3 P4 P5 G1", "light_red": "P2",
    "fresh_white": "O4 K1 K3 F1 F2 F3 F4 F6", "full_creamy_white": "K2",
    "full_fresh_white": "F5", "aromatic_white": "F7", "white_brut": "O1 O2 O3 O5",
    "dry_rose": "T1 T2 T3 T4", "rose_brut": "B1 B2 B3",
    "offdry_fresh_white": "H1 H5", "offdry_fruity_sparkling": "H3", "offdry_full_white": "H4", "semisweet_white": "H2",
    "sweet_white": "D1 D2 D4", "sweet_aromatic_white": "D3", "sweet_red": "D5 D6 D7", "sweet_rose": "D8",
}


def make_policy(data):
    rules = {}

    def assign(profiles, families):
        for profile in profiles.split():
            if profile in rules:
                raise ValueError("Duplicate quality profile: " + profile)
            rules[profile] = families.split()

    reds = "robust_red oaky_robust_red rounded_red delicate_red"
    fresh = "fresh_white white_brut"
    creamy = "fresh_white full_creamy_white full_fresh_white white_brut"
    light = "fresh_white white_brut dry_rose rose_brut"
    assign("meat_general grilled_meat", reds + " dry_rose")
    assign("meat_steak ribeye lamb", "robust_red oaky_robust_red rounded_red")
    assign("game venison", "robust_red rounded_red delicate_red fresh_white full_creamy_white")
    assign("meat_dough minced_meat meat_tomato", "rounded_red delicate_red dry_rose")
    assign("duck_berry", "rounded_red delicate_red")
    assign("braised_beef", "rounded_red delicate_red")
    assign("cold_meat", "rounded_red delicate_red dry_rose white_brut")
    assign("poultry", fresh + " delicate_red")
    assign("fish_general", fresh + " dry_rose")
    assign("fish_plain raw_fish crustaceans crab fish_soup", fresh)
    assign("seafood_citrus molluscs", fresh + " full_fresh_white")
    assign("crab_butter scallops_grilled white_butter_cream", creamy)
    assign("fried roe salads soft_cheese eggs", light)
    assign("salted_fish", light + " offdry_fresh_white")
    assign("mayonnaise", fresh)
    assign("olivier", fresh)
    assign("vegetable_acid", light + " full_fresh_white")
    assign("cheese_pastry", creamy + " dry_rose rose_brut")
    assign("cheese_general", fresh + " delicate_red rounded_red sweet_white sweet_aromatic_white")
    assign("hard_cheese", creamy + " " + reds)
    assign("blue_cheese dessert_general", "sweet_white sweet_aromatic_white sweet_red sweet_rose")
    assign("mushrooms", "rounded_red delicate_red fresh_white full_creamy_white full_fresh_white")
    assign("vegetables", light + " delicate_red")
    assign("vegetables_tomato", "rounded_red delicate_red dry_rose fresh_white full_fresh_white")
    assign("potato_pastry veg_pastry", creamy + " dry_rose rose_brut")
    assign("meat_pastry savory_pastry", creamy + " rounded_red delicate_red dry_rose rose_brut")
    assign("pumpkin", creamy + " aromatic_white offdry_fresh_white offdry_full_white")
    assign("dumplings", "rounded_red delicate_red fresh_white full_creamy_white full_fresh_white")
    assign("soup_general", "fresh_white dry_rose rounded_red delicate_red offdry_fresh_white")
    assign("sour_cabbage", "fresh_white full_fresh_white offdry_fresh_white dry_rose")
    assign("meat_soup_tomato", "fresh_white full_fresh_white dry_rose rounded_red delicate_red")
    assign("legumes grains", "fresh_white dry_rose delicate_red")
    assign("mixed", light + " delicate_red")
    assign("spicy spicy_sour sweet_glaze", "offdry_fresh_white semisweet_white")
    assign("fruit", "semisweet_white sweet_white sweet_aromatic_white sweet_rose")
    assign("fruit_dessert curd_dessert", "sweet_white sweet_aromatic_white sweet_rose")
    assign("honey_cake", "sweet_white sweet_aromatic_white")
    assign("coffee_cocoa", "sweet_red sweet_white")
    assign("seafood_tomato seafood_rice", "fresh_white full_fresh_white dry_rose")
    assign("offal_general", "rounded_red delicate_red fresh_white dry_rose")
    # Light, elegant Pinot remains a valid option for gentle foods; it is excluded
    # where the selected style explicitly requires more weight.
    for families in rules.values():
        if "delicate_red" in families:
            families.append("light_red")
        if "offdry_fresh_white" in families:
            families.append("offdry_fruity_sparkling")
    assign("sweet_glaze_rich_meat", "robust_red rounded_red")
    assign("sweet_glaze_duck", "robust_red rounded_red delicate_red")
    assign("spicy_meat", "offdry_fresh_white light_red")
    assert set(rules) == {p["id"] for p in data["profiles"]}
    wines = {w["id"]: w for w in data["wines"]}
    annotations = {}
    for family, codes in FAMILIES.items():
        for code in codes.split():
            assert code not in annotations
            wine = wines[code]
            annotations[code] = {"wine_slug": wine["wine_slug"], "family": family,
                "basis": "editorial_style_classification_not_measured_source_field",
                "source_description_ru": wine["style_summary"]["text_ru"],
                "source_description_sha256": hashlib.sha256(wine["style_summary"]["text_ru"].encode()).hexdigest()}
    assert set(annotations) == set(wines)
    return {"version": "1.0.0", "source_refs": ["wset_general", "wset_spice", "wset_winter"],
        "basis": "Conservative editorial style envelope, source-linked and independent of the blind test judge. Not measured body/tannin/acidity and not a probability of taste preference.",
        "families": sorted(FAMILIES), "wines": list(annotations.values()),
        "profiles": rules, "unknown_style_action": "exclude_until_reviewed",
        "continuation": "Never extend pagination beyond the approved style envelope to fill a page.",
        "sauce_context_policy": "Combine selected recipe style requirements with explicit user attributes. Cream must not erase existing chilli or glaze; no redundant non-dessert or protein flag is required.",
        "node_family_overrides": {n["id"]: ["sweet_red"] for n in data["nodes"] if "chocolate_desserts" in n["hierarchy_path"]},
        "node_family_extensions": {"herring_under_fur_coat": ["offdry_fresh_white"]},
        "profile_context_defaults": {"spicy": {"heat": "medium"}, "spicy_sour": {"heat": "medium", "acidity": "high"},
            "spicy_meat": {"heat": "medium"}, "sweet_glaze": {"sauce_sweetness": "medium"},
            "sweet_glaze_rich_meat": {"sauce_sweetness": "medium"}, "sweet_glaze_duck": {"sauce_sweetness": "medium"}}}


def add_composite_profiles(data):
    wines = {w["id"]: w for w in data["wines"]}
    base = next(p for p in data["profiles"] if p["id"] == "sweet_glaze")
    additions = [
        ("sweet_glaze_rich_meat", "Насыщенное мясо со сладкой глазурью без чили", "R3 R1 R4 G4 R5",
         ["red"], ["dry"], None,
         "Ripe, fruit-forward dry red wine of medium to full weight, with soft or velvety tannins, freshness and restrained oak. For rich savoury meat with a sweet barbecue or fruit glaze and no chilli. Fruit and texture must balance both the meat and sauce; dessert wine is not the default.",
         "Фруктовое сухое красное средней или высокой насыщенности, с мягкими танинами и умеренными древесными оттенками к насыщенному мясу и сладкой глазури без чили.",
         "фруктовая насыщенность и мягкая структура поддерживают мясо и сладкую глазурь; сладкий соус не превращает основное блюдо в десерт"),
        ("sweet_glaze_duck", "Утка со сладким ягодным соусом или хойсином", "P3 R4 G4 P1 P5",
         ["red"], ["dry"], None,
         "Fresh, ripe berry-fruited dry red wine with medium weight and soft or velvety tannins. For rich duck with a sweet berry or hoisin sauce, without hot chilli. Avoid excessively light texture and dominant wood; keep both duck fat and sauce in the pairing.",
         "Фруктовое сухое красное с мягкими танинами, свежестью и достаточной насыщенностью к жирной утке и сладкому ягодному соусу без чили.",
         "зрелые ягоды и мягкая структура поддерживают жирную утку и сладкий соус, сохраняя мясную насыщенность сочетания"),
        ("spicy_meat", "Острое мясо без сладкой глазури", "H1 H5 P2",
         ["white", "red"], ["semi_dry", "dry"], 12.5,
         "Fresh off-dry white wine, or a light dry red with explicitly soft elegant tannins, and verified alcohol no higher than12.5 percent. For hot chilli with savoury red meat and no distinctly sweet glaze. Preserve freshness, moderate alcohol and a delicate tannin structure rather than defaulting to a powerful steak wine.",
         "Свежее полусухое белое либо лёгкое сухое красное с мягкими танинами и подтверждённым алкоголем не выше 12,5% к мясу с чили без сладкой глазури.",
         "умеренный алкоголь, свежесть и деликатная танинность учитывают чили, сохраняя подходящую насыщенность для мясного блюда")
    ]
    styles = json.loads((ROOT / "prompts/style-guidance.en.json").read_bytes())
    for profile_id, label, codes, colors, sugar, maximum, query, description, rationale in additions:
        profile = deepcopy(base)
        profile.update(id=profile_id, label_ru=label, embedding_query_text=query,
            curation_pool=[wines[c]["wine_slug"] for c in codes.split()], match_rationale_ru=rationale,
            source_refs=["wset_general", "wset_spice", "wset_takeaway"])
        profile["target"].update(colors=colors, sweetness=sugar, wine_kinds=["still"], description_ru=description,
            preferred_grapes=["Сира", "Мерло", "Саперави", "Каберне Совиньон"] if profile_id == "sweet_glaze_rich_meat" else
                ["Пино Нуар", "Мерло", "Саперави"] if profile_id == "sweet_glaze_duck" else ["Рислинг", "Пино Нуар"])
        profile["eligibility"].update(colors=colors, sweetness=sugar, wine_kinds=["still"], max_alcohol_percent=maximum)
        profile["soft_penalties"] = ["Доминирующая древесность", "Жёсткая танинность", "Несоразмерная насыщенность"]
        data["profiles"].append(profile)
        styles["profiles"][profile_id] = {"source_input_sha256": hashlib.sha256(query.encode()).hexdigest(), "text_en": query}
    styles["schema_version"] = "2.0.0"
    (ROOT / "prompts/style-guidance.v2.en.json").write_text(json.dumps(styles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build():
    path = ROOT / "data/pairing-dataset.v2.json"
    data = json.loads(path.read_bytes())
    data["schema_version"] = "3.0.0"
    data["taxonomy_version"] = "3.0.0"
    data["dataset_id"] = "dinner-lens-200-sauce-quality-20261019"
    data["supersedes"] = "pairing-dataset.v2.json"
    data["$schema"] = "./pairing-dataset.v3.schema.json"
    add_composite_profiles(data)
    data["suitability_policy"] = make_policy(data)
    data["sources"].append({"id": "wset_takeaway", "title": "How to pair wine with your favourite takeaway meals",
        "url": "https://www.wsetglobal.com/knowledge-centre/blog/2020/june/02/how-to-pair-wine-with-your-favourite-takeaway-meals/",
        "use": "Complementary and contrasting food components, red-meat weight, soft-tannin red alternatives and duck pairings. New composite profiles are editorial applications, not direct product endorsements.", "checked_at": "2026-10-19"})
    wines_by_slug = {w["wine_slug"]: w for w in data["wines"]}
    profiles = {p["id"]: p for p in data["profiles"]}
    # Reviewed recipe references whose generic or inflected ingredient words are
    # not safely covered by the coarse offline pattern. These are selected recipe
    # identities, never protein deductions from an image or a model hypothesis.
    recipe_proteins = {
        "perm_posikunchiki_meat": "meat", "olivier_doctors": "meat",
        "red_caviar_sandwich": "fish", "herring_under_fur_coat": "fish",
        "beef_tongue_mustard": "meat", "mixed_meat_solyanka": "meat",
        "pasta_carbonara": "meat", "eggs_benedict_ham": "meat",
        "okroshka_kefir": "meat", "pasta_bolognese": "meat",
        "pizza_pepperoni": "meat", "pizza_ham_mushrooms": "meat",
        "quiche_lorraine": "meat", "blini_meat": "meat",
        "croissant_ham_cheese": "meat", "beef_liver_onions": "meat",
        "crimean_cheburek_beef": "meat", "surimi_mayonnaise_salad": "fish",
    }
    for node in data["nodes"]:
        path_ids = node["hierarchy_path"]
        reference = {}
        for root, family in (("meat", "meat"), ("poultry", "poultry"), ("game", "game"),
                             ("fish", "fish"), ("crustaceans", "seafood"), ("molluscs", "seafood")):
            if root in path_ids:
                reference["protein_family"] = family
        if node["kind"] == "dish":
            # Offline interpretation of the explicitly selected recipe reference,
            # never an ingredient detector over image/model text.
            base = node["editorial_recipe_template"]["protein_or_base"].casefold().replace("ё", "е")
            for pattern, family in ((r"говядин|теля|свин|баран|ягнен|конин", "meat"),
                    (r"куриц|курин|цыпл|индей|утк|утин", "poultry"),
                    (r"лосос|семг|форел|палтус|треск|тунец|тунц|рыб|сиг|чир|омул|скумбр|щук|судак|угор", "fish"),
                    (r"морепродукт|краб|кревет|кальмар|осьмин|мидии|гребеш|устриц|раки", "seafood")):
                if re.search(pattern, base):
                    reference["protein_family"] = family
            if re.search(r"утк|утин", base):
                reference["poultry_style"] = "duck"
        if node["id"] in recipe_proteins:
            reference["protein_family"] = recipe_proteins[node["id"]]
        if "duck" in path_ids:
            reference["poultry_style"] = "duck"
        if "desserts" in path_ids:
            reference["is_dessert"] = True
        node["pairing_reference_attributes"] = reference
        node["pairing_reference_basis"] = "Selected recipe/category reference only; never observed image facts or automatically user-confirmed attributes. Explicit user corrections take precedence."
        original = node["pairing_rule"]["profile_id"]
        replacement = None
        if original in {"spicy", "spicy_sour"} and reference.get("protein_family") in {"meat", "game"}:
            replacement = "spicy_meat"
        elif original == "sweet_glaze":
            replacement = ("sweet_glaze_duck" if reference.get("poultry_style") == "duck" else
                "sweet_glaze_rich_meat" if "meat" in path_ids or "game" in path_ids else None)
        if replacement:
                profile = profiles[replacement]
                node["pairing_rule"].update(profile_id=replacement, rationale_ru=profile["match_rationale_ru"],
                    target_wine_description_ru=profile["target"]["description_ru"])
                node["curated"] = []
                for rank, slug in enumerate(profile["curation_pool"], 1):
                    wine = wines_by_slug[slug]
                    node["curated"].append({"wine_slug": slug, "rank": rank,
                        "explanation_ru": f"К «{node['label_ru']}»: {wine['style_summary']['text_ru']} {profile['match_rationale_ru'][:1].upper() + profile['match_rationale_ru'][1:]}.",
                        "source_facts_used": {"color": wine["facts"]["color"]["value"], "sweetness": wine["facts"]["sweetness"]["value"], "style_summary": wine["style_summary"]["text_ru"]},
                        "explanation_basis": "editorial_pairing_rule_plus_source_facts", "applicability_conditions": [],
                        "curation_status": "editorial_draft_not_panel_tasted"})
                node["embedding_query_document"].update(profile_id=replacement, text=profile["embedding_query_text"])
                node["revised_in"] = "3.0.0"
    # A supplied sweet sauce is meaningful without a redundant is_dessert=false.
    rule = next(r for r in data["modifier_rules"] if r["id"] == "sweet_sauce")
    rule["when"] = {"attribute": "sauce_sweetness", "op": "in", "value": ["medium", "high"]}
    data["provenance"]["sauce_quality_revision"] = {
        "base_dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "preserved": "Frozen v1 and v2 files, historical ground truth, labels, hierarchy and catalog source facts.",
        "editorial_style_labels_are_not_measurements": True,
        "quality_evaluation": "Separate blind model editorial judgments from catalog cards; not a tasting panel. Original benchmark contracts remain versioned separately."}
    # These descendants explicitly confirm chocolate rather than a cream-dominant
    # coffee dessert. Keep the three reviewed cocoa-compatible sweet reds.
    cocoa = [next(w for w in data["wines"] if w["id"] == code) for code in ("D5", "D6", "D7")]
    for node in data["nodes"]:
        if node["id"] not in data["suitability_policy"]["node_family_overrides"]:
            continue
        template = deepcopy(node["curated"][0])
        node["curated"] = []
        for rank, wine in enumerate(cocoa, 1):
            entry = deepcopy(template)
            entry.update(wine_slug=wine["wine_slug"], rank=rank, applicability_conditions=[],
                explanation_ru=f"К «{node['label_ru']}»: {wine['style_summary']['text_ru']} Насыщенный сладкий ягодно-шоколадный стиль поддерживает какао и сладость десерта.",
                source_facts_used={"color": "red", "sweetness": "sweet", "style_summary": wine["style_summary"]["text_ru"]})
            node["curated"].append(entry)
    data["scope"]["curated_wine_links"] = sum(len(n["curated"]) for n in data["nodes"])
    data["embedding_documents"]["query_profiles"] = [n["embedding_query_document"] for n in data["nodes"]]
    data["validation_summary"] = {"report_file": "pairing-dataset.v3.validation.json",
        "validated_scope": "Run v3 validation and sauce/continuation tests. Existing v2 text contracts do not define v3 style admission."}
    data["known_data_quality_notes"].append("V3 narrows continuation using reviewed editorial style families. Similarity ranks suitable candidates; exhaustion does not imply all wines of a color/sugar category are good pairings. Some styles have only 3–4 supported wines, sometimes from fewer than three producers.")
    target = ROOT / "data/pairing-dataset.v3.json"
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    schema = json.loads((ROOT / "data/pairing-dataset.schema.json").read_bytes())
    schema["$id"] = "urn:dinner-lens:pairing-dataset:3.0.0"
    schema["properties"]["schema_version"]["const"] = "3.0.0"
    schema["required"].append("suitability_policy")
    (ROOT / "data/pairing-dataset.v3.schema.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dataset": target.name, "families": len(FAMILIES), "style_annotations": 49,
                      "curated_links": data["scope"]["curated_wine_links"]}))


if __name__ == "__main__":
    build()
