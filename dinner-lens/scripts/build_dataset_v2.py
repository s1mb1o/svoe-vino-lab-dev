"""Reproducibly extend the frozen v1 taxonomy from an explicit editorial JSON spec.

No model calls, catalog refetches, inferred wine facts, or changes to v1 nodes.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build():
    base_path = ROOT / "data/pairing-dataset.v1.json"
    spec_path = ROOT / "data/expansion.v2.json"
    data = json.loads(base_path.read_bytes())
    spec = json.loads(spec_path.read_bytes())
    style_path = ROOT / "prompts/style-guidance.en.json"
    styles = json.loads(style_path.read_bytes())["profiles"]
    old_nodes = deepcopy(data["nodes"])
    nodes = {n["id"]: n for n in data["nodes"]}
    profiles = {p["id"]: p for p in data["profiles"]}
    for profile_id, profile in profiles.items():
        if styles[profile_id]["source_input_sha256"] != hashlib.sha256(profile["embedding_query_text"].encode()).hexdigest():
            raise ValueError("Stale English style translation: " + profile_id)
    wines = {w["wine_slug"]: w for w in data["wines"]}
    # These are style categories, not assertions about an unconfirmed recipe.
    bridges = {
        "meat_steak": "Структура сухого красного соразмерна мясному вкусу и корочке.",
        "braised_beef": "Округлый красный стиль сопоставлен с насыщенностью мяса и соуса.",
        "cold_meat": "Деликатный сухой стиль сохраняет тонкую мясную текстуру; соль и заправка учитываются отдельно.",
        "sweet_glaze": "Небольшая или выраженная сладость вина поддерживает подтверждённо сладкий соус.",
        "meat_general": "Сухой фруктовый стиль сопоставлен с мясной насыщенностью без требования мощных танинов.",
        "fried": "Свежий сухой или игристый стиль даёт освежающее сопровождение к жарке и панировке.",
        "meat_tomato": "Фруктовый сухой стиль сопоставлен с мясной насыщенностью и томатной кислотностью.",
        "poultry": "Деликатный белый стиль выбран для нежного птичьего или сходного по насыщенности мяса и бульона.",
        "vegetables_tomato": "Свежий фруктовый стиль сопоставлен с кислотностью томатов и умеренной насыщенностью блюда.",
        "white_butter_cream": "Белый стиль средней насыщенности или брют выбран к жирной молочной либо масляной текстуре.",
        "game": "Структура красного вина сопоставлена с насыщенным вкусом дичи.",
        "duck_berry": "Ягодный красный или розовый стиль поддерживает жирную утку и кислую ягодную подачу.",
        "fish_plain": "Деликатный сухой белый или брют сохраняет рыбный вкус без доминирующей танинности.",
        "scallops_grilled": "Белый стиль средней насыщенности сопоставлен с моллюском и обжаренной корочкой.",
        "crab_butter": "Белый стиль или брют сопоставлен с нежными ракообразными и жирностью сливочного масла.",
        "crustaceans": "Деликатный белый стиль или брют сохраняет нежную текстуру ракообразных.",
        "salted_fish": "Свежий белый, розовый или брют сопоставлен с солёной жирной рыбой; сладость остаётся явным выбором.",
        "seafood_citrus": "Цитрусовая свежесть целевого стиля поддерживает кислую подачу морепродуктов.",
        "raw_fish": "Деликатный свежий белый стиль выбран для сырой рыбы и подкислённого риса либо холодной заправки.",
        "vegetable_acid": "Свежий сухой стиль сопоставлен с кислой овощной или рисовой заправкой.",
        "soft_cheese": "Деликатный белый или розовый стиль сохраняет мягкий сырный вкус и сопровождает жирную текстуру.",
        "mayonnaise": "Свежий белый или брют даёт освежающее сопровождение к жирной яичной заправке.",
        "vegetables": "Умеренная насыщенность и фруктовый характер выбранного стиля сохраняют овощной вкус.",
        "legumes": "Умеренно насыщенный фруктовый стиль сопоставлен с крахмалистой бобовой текстурой.",
        "eggs": "Деликатный белый, розовый или брют сохраняет мягкую яичную текстуру.",
        "pumpkin": "Фруктовый округлый стиль сопоставлен с естественной сладостью тыквы и мягкой текстурой.",
        "cheese_pastry": "Свежий белый, розовый или брют сопоставлен с солёным сыром и жирной выпечкой.",
        "mushrooms": "Умеренно насыщенный белый или деликатный красный стиль поддерживает грибной вкус.",
        "potato_pastry": "Белый, розовый или брют сопоставлен с мягкой крахмалистой основой и жирностью подачи.",
        "fruit_dessert": "Сладкий фруктовый стиль поддерживает сладость десерта и его фруктовую составляющую.",
        "meat_pastry": "Фруктовый сухой стиль сопоставлен с мясной начинкой и насыщенностью теста.",
        "hard_cheese": "Сухой стиль средней насыщенности сопоставлен с солёностью и плотностью выдержанного сыра.",
        "blue_cheese": "Сладкий стиль создаёт контраст к солёному голубому сыру и поддерживает спелую грушу, если она есть.",
        "fruit": "Фруктовый стиль с остаточной сладостью сопоставлен с естественной сладостью фруктов; спелость уточняется.",
        "curd_dessert": "Сладкий мягкий стиль сопоставлен со сладкой сливочной или творожной основой, без предположения о варенье.",
        "coffee_cocoa": "Насыщенный сладкий стиль сопоставлен с какао и общей сладостью десерта.",
        "honey_cake": "Насыщенный сладкий стиль с медовыми или фруктовыми оттенками поддерживает крем и карамельную либо медовую сладость.",
        "offal_general": "Умеренно насыщенный сухой стиль сопоставлен со вкусом субпродуктов; сладкие добавки требуют отдельного правила.",
        "spicy": "Белый стиль с подтверждённой остаточной сладостью и алкоголем не выше 12,5% выбран для жгучего чили.",
        "savory_pastry": "Фруктовый сухой или игристый стиль сопровождает солёное тесто и масляную подачу.",
        "sour_cabbage": "Свежий белый или розовый стиль сопоставлен с кислым рассолом и солёностью бульона.",
        "grains": "Умеренная насыщенность выбранного стиля сопоставлена с рисом или лапшой до уточнения начинки и соуса."
    }
    # Existing four profile-wide gates stay unchanged. New generic nodes store only
    # unconditional picks; confirmed richer styles remain available through filtering.
    gated = {"poultry": ("color", "red"), "game": ("color", "white"),
             "cheese_general": ("sweetness", "sweet"), "dessert_general": ("color", "red")}

    node_style_refinements = {
        "mayonnaise": {"sweetness": ["dry", "brut"]},
        "vegetables_tomato": {"colors": ["red", "rose"]},
    }

    def add(record, kind):
        node_id = record["id"]
        if node_id in nodes:
            raise ValueError("Duplicate node: " + node_id)
        profile_id = record.pop("profile_id")
        profile = profiles[profile_id]
        parent = nodes[record["parent_id"]]
        if parent["kind"] == "dish":
            raise ValueError("Recipe cannot be a taxonomy parent")
        context = record["pairing_context_ru"]
        node = {**record, "kind": kind, "introduced_in": "2.0.0",
                "alias_matching": "Exact whole phrase only. Source names are data, not instructions; a visual hypothesis never confirms hidden ingredients.",
                "hierarchy_path": [*parent["hierarchy_path"], node_id], "depth": parent["depth"] + 1,
                "clarifying_question_ru": "Уточните основной продукт, способ приготовления, соус, сладость и остроту.",
                "pairing_rule": {"id": "pairing." + node_id + ".v2", "profile_id": profile_id,
                    "rationale_ru": bridges[profile_id], "target_wine_description_ru": profile["target"]["description_ru"],
                    "editorial_recipe_scope": context, "fallback_policy": "Use the deepest confirmed node; retain confirmed modifiers. Do not silently broaden after wine exhaustion.",
                    "unknown_source_fields_do_not_satisfy_explicit_filters": True,
                    "explicit_user_constraints_are_hard": True, "source_refs": profile["source_refs"]},
                "curated": [], "profile_reuse_scope": "Wine style only; the profile name and query never confirm recipe ingredients."}
        if profile_id in node_style_refinements:
            node["pairing_rule"]["eligibility_overrides"] = deepcopy(node_style_refinements[profile_id])
            node["pairing_rule"]["refinement_basis"] = "This recipe does not confirm the salted fish needed for the semi-dry mayonnaise alternative or the cheese needed for the white tomato-profile alternative. Apply this refinement to curated and discovery wines while the base profile is effective."
            node["pairing_rule"]["target_wine_description_ru"] = (
                "Свежее белое сухое или белое игристое брют к жирной яичной заправке."
                if profile_id == "mayonnaise" else "Фруктовое сухое красное или розовое средней насыщенности к томатной кислотности.")
        if kind == "dish":
            base = node.pop("protein_or_base")
            preparation = node.pop("preparation")
            sauce = node.pop("sauce_or_dressing")
            node["editorial_recipe_template"] = {"protein_or_base": base, "preparation": preparation,
                "sauce_or_dressing": sauce, "sauce_state": "specified_by_dish_name" if sauce else "unspecified_not_assumed_absent",
                "basis": "typical_recipe_template_not_image_observation"}
            node["confirmed_attribute_requirements"] = [base, preparation, sauce or "соус, включая отсутствие сладости и остроты"]
            node["confirmed_attribute_requirements"].append("фактическая сладость и жгучесть соуса")
            node["clarifying_question_ru"] = "Подтвердите состав и подачу: " + ", ".join(node["confirmed_attribute_requirements"]) + "."
            node["recipe_variation_notes"] = ["Редакторский вариант блюда; сокращённое название и фото не доказывают скрытый состав."]
        pool = list(profile["curation_pool"])
        if profile_id == "vegetables_tomato":
            # Reviewed dry rosé replaces the conditional white; three producers
            # remain available without inventing a new catalog fact or profile.
            pool = ["vinodelnya-vedernikov-krasnostop-zolotovskiy-roze-rozovoe-suhoe-12" if wines[s]["facts"]["color"]["value"] == "white" else s for s in pool]
            node["curation_refinement"] = "The approved reviewed dry rosé substitution replaces the white alternative reserved for cheese-based vegetable dishes."
        for slug in pool:
            wine = wines[slug]
            overrides = node["pairing_rule"].get("eligibility_overrides", {})
            if any(wine["facts"][{"colors": "color", "sweetness": "sweetness", "wine_kinds": "wine_kind"}[field]]["value"] not in allowed for field, allowed in overrides.items()):
                continue
            if profile_id in gated:
                key, value = gated[profile_id]
                if wine["facts"][key]["value"] == value:
                    continue
            node["curated"].append({"wine_slug": slug, "rank": len(node["curated"]) + 1,
                "explanation_ru": f"К «{node['label_ru']}»: {wine['style_summary']['text_ru']} {bridges[profile_id]} Контекст: {context}.",
                "source_facts_used": {"color": wine["facts"]["color"]["value"],
                    "sweetness": wine["facts"]["sweetness"]["value"],
                    "style_summary": wine["style_summary"]["text_ru"]},
                "explanation_basis": "editorial_pairing_rule_plus_source_facts", "applicability_conditions": [],
                "curation_status": "editorial_draft_not_panel_tasted"})
        if not 3 <= len(node["curated"]) <= 5:
            raise ValueError("Invalid curation size: " + node_id)
        node["embedding_query_document"] = {"id": "query:" + node_id, "resolved_node_id": node_id,
            "profile_id": profile_id, "text": styles[profile_id]["text_en"],
            "context_not_embedded_as_wine_facts": {"dish_label": node["label_ru"], "recipe_context": context},
            "rebuild_when": ["confirmed_modifiers_change", "profile_changes", "embedding_model_changes"]}
        nodes[node_id] = node
        data["nodes"].append(node)

    for row in spec["classes"]:
        add(dict(zip(spec["class_columns"], row, strict=True)), "class")
    for number, row in enumerate(spec["dishes"], 76):
        record = dict(zip(spec["dish_columns"], row, strict=True))
        record["original_number"] = number
        add(record, "dish")

    ambiguous = [
        ("паста", "pasta", "pasta_carbonara"), ("макароны", "pasta", "pasta_bolognese"),
        ("ролл", "sushi_rolls", "philadelphia_salmon_cream_cheese"), ("филадельфия", "cream_cheese_rolls", "philadelphia_salmon_cream_cheese"),
        ("цезарь", "salads", "caesar_chicken"), ("caesar salad", "salads", "caesar_chicken"),
        ("шашлык", "grilled_meat", "pork_shashlik"), ("плов", "rice_dishes", "uzbek_lamb_plov"),
        ("тартар", None, "beef_tartare_capers"), ("карпаччо", None, "beef_carpaccio_parmesan"),
        ("котлета", None, "homestyle_cutlet_mash"), ("стриплойн", "meat_steak", "striploin_grilled"),
        ("бургер", "sandwiches", "beef_cheddar_burger"), ("вареники", "dumplings", "vareniki_potato"),
        ("голубцы", "mixed_dishes", "stuffed_cabbage_meat_rice"),
        ("перец фаршированный", "mixed_dishes", "stuffed_peppers_meat_rice"),
        ("паштет", None, "chicken_liver_pate"), ("крем-суп", "soups", "mushroom_cream_soup"),
        ("чизкейк", "desserts", "vanilla_cheesecake"), ("шницель", None, "pork_schnitzel"),
        ("цезарь с курицей", "salads", "caesar_chicken"), ("цезарь с креветками", "salads", "caesar_shrimp"),
        ("хумус", "chickpea_dishes", "hummus_tahini"), ("фалафель", "legumes", "falafel_tahini"),
        ("панна-котта", "cream_desserts", "panna_cotta_berries"), ("нигири", "sushi_rolls", "salmon_nigiri"),
        ("паста болоньезе", "meat_pasta", "pasta_bolognese"), ("паста альфредо", "cream_pasta", "pasta_alfredo"),
    ]
    # 'Shashlik' may be poultry/fish; don't assume red meat from the short name.
    ambiguous = [(s, None if s in {"шашлык", "вареники"} else f, d) for s, f, d in ambiguous]
    for phrase, fallback, forbidden in ambiguous:
        rule = {"phrase": phrase, "fallback_node_id": fallback,
                "must_not_resolve_to": forbidden, "action": "Ask for ingredients, preparation and sauce before refining the class.",
                "introduced_in": "2.0.0"}
        if fallback is None:
            rule["fallback_relation"] = "no_category_until_confirmed"
        elif fallback in nodes[forbidden]["hierarchy_path"]:
            rule["fallback_relation"] = "ancestor"
        else:
            exception = next(r for r in spec["cross_branch_fallbacks"] if r["phrase"] == phrase and r["fallback_node_id"] == fallback)
            rule["fallback_relation"] = "cross_branch_generalization"
            rule["generalization_reason"] = exception["reason"]
        data["disambiguation_rules"].append(rule)
        data["evaluation_cases"]["disambiguation"].append(deepcopy(rule))

    for node in data["nodes"][len(old_nodes):]:
        if node["kind"] == "dish":
            data["evaluation_cases"].setdefault("text_contracts", []).append({"id": "confirmed_name_v2_" + node["id"],
                "input_label": node["label_ru"], "required_confirmations": node["confirmed_attribute_requirements"],
                "expected_node_id": node["id"], "expected_group": node["group"],
                "evaluation_status": "editorial_text_reference_not_photo_ground_truth"})
    data.update(schema_version="2.0.0", dataset_id="dinner-lens-200-20261019", taxonomy_version="2.0.0",
                created_at="2026-10-19", supersedes="pairing-dataset.v1.json",
                status="expanded_editorial_dataset_not_panel_tasted")
    scope = data["scope"]
    scope.update(dishes=sum(n["kind"] == "dish" for n in nodes.values()),
        dish_groups=dict(Counter(n["group"] for n in nodes.values() if n["kind"] == "dish")),
        intermediate_classes=sum(n["kind"] == "class" for n in nodes.values()), total_nodes=len(nodes),
        curated_wine_links=sum(len(n["curated"]) for n in nodes.values()),
        vlm_evaluated=False, taste_panel_evaluated=False)
    data["provenance"]["expansion"] = {"spec": spec_path.name, "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        "base_sha256": hashlib.sha256(base_path.read_bytes()).hexdigest(), "base_nodes_preserved_verbatim": True,
        "english_style_guidance_sha256": hashlib.sha256(style_path.read_bytes()).hexdigest(),
        "superseded_v1_resolutions": spec["superseded_v1_resolutions"],
        "selection_basis": spec["selection_basis"], "new_wine_facts_inferred": False,
        "curation_method": "Explicit recipe-to-style assignments and reused reviewed editorial wine pools, with documented node-level refinements and substitutions. Every link carries recipe context, style rationale and catalog evidence; no tasting-panel validation is claimed.",
        "evaluation_boundary": "The original 75-photo ground truth remains frozen. Added text cases are editorial contract references, not new visual evidence or proof of improved model accuracy."}
    data["sources"] += [
        {"id": "tokyo_city_menu", "title": "TOKYO-CITY official menu", "url": "https://www.tokyo-city.ru/msk", "use": "Evidence of menu families: sushi, rolls, wok, salads, pasta and desserts. Not a recipe or prevalence audit of every added dish.", "checked_at": "2026-10-19"},
        {"id": "shakshuka_menu", "title": "Shakshuka official menu", "url": "https://itshakshuka.ru/", "use": "Evidence of egg and chickpea restaurant offerings; exact variants remain editorial templates.", "checked_at": "2026-10-19"},
        {"id": "tatar_culture_kystyby", "title": "Tatar cultural resource centre: Kystyby", "url": "https://www.tatcultresurs.ru/onkn/kystybyy", "use": "Regional dish identity and potato filling.", "checked_at": "2026-10-19"},
        {"id": "muuskhaia_menu", "title": "Muus Khaia official restaurant menu", "url": "https://muuskhaia.ru/restoran/", "use": "Indigirka from chir in a Yakut restaurant.", "checked_at": "2026-10-19"},
        {"id": "perm_kitchen_omul", "title": "Perm Kitchen official menu", "url": "https://permkuhnya.ru/menu/museum/appetizers/нельма-омуль-слабосоленые-с-овощами/", "use": "Lightly salted omul restaurant offering; geographic origin is not an exclusivity claim.", "checked_at": "2026-10-19"},
        {"id": "fydzhin_recipe", "title": "Ossetian pie: Fydzhin", "url": "https://south-ossetia.info/osetinskij-pirog-fyddzhyn/", "use": "Recipe identity only; not a claim of exclusive regional origin.", "checked_at": "2026-10-19"},
        {"id": "crimean_chebureki_menu", "title": "Crimean Chebureki official menu", "url": "https://chir-chir.ru/menu", "use": "Crimean restaurant family; exact beef variant remains an editorial template.", "checked_at": "2026-10-19"},
        {"id": "kalakeitto_festival", "title": "Local Taste Festival: Karelia", "url": "https://auc.rest/localtastefestival_2022", "use": "Karelian kalakeitto restaurant family; whitefish and milk variant remains an editorial template.", "checked_at": "2026-10-19"}
    ]
    recipe_sources = dict(zip(["indigirka_whitefish", "omul_light_salt", "kystyby_potato", "ossetian_fydzhin", "crimean_cheburek_beef", "kalakeitto_whitefish_milk"],
        ["muuskhaia_menu", "perm_kitchen_omul", "tatar_culture_kystyby", "fydzhin_recipe", "crimean_chebureki_menu", "kalakeitto_festival"], strict=True))
    for node_id, source in recipe_sources.items():
        nodes[node_id]["recipe_source_refs"] = [source]
    data["family_evidence_refs"] = ["tokyo_city_menu", "shakshuka_menu"]
    for source in data["sources"]:
        if source["id"] in data["family_evidence_refs"]:
            source["evidence_scope"] = "family_evidence_only_not_every_recipe"
    data["embedding_documents"]["query_profiles"] = [n["embedding_query_document"] for n in nodes.values()]
    data["retrieval_contract"]["embedding"]["prepared_query_documents"] = len(nodes)
    data["known_data_quality_notes"].append("v2 expands editorial recipe coverage, not catalog facts or measured visual coverage. The same 49 reviewed wines and 65 style profiles are reused; cold soup, filling and sauce ambiguity must still be confirmed.")
    data["validation_summary"] = {"passed": False, "report_file": "pairing-dataset.validation.json", "validated_scope": "Run scripts/validate_dataset_v2.py after building."}
    assert data["nodes"][:len(old_nodes)] == old_nodes
    assert scope["dishes"] == 200
    write_json(ROOT / "data/pairing-dataset.v2.json", data)
    print(json.dumps(scope))


if __name__ == "__main__":
    build()
    from validate_dataset_v2 import validate
    validate()
