"""Sauce composition, style admission and long-tail behavior across real vectors."""
import json
from pathlib import Path
import tempfile
import unittest

from dinner_lens.data import Knowledge
from dinner_lens.embeddings import EmbeddingIndex
from dinner_lens.engine import Engine, PipelineError
from dinner_lens.paths import default_dataset, default_index, default_style


class PairingQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k = Knowledge(default_dataset(), default_style())
        cls.index = EmbeddingIndex(cls.k, default_index())

    def setUp(self):
        self.engine = Engine(self.k, self.index, cursor_secret=b"quality-tests-only-secret-at-least-32-bytes")

    def all_rows(self, node, attrs=None, filters=None):
        first = self.engine.recommend(node_id=node, confirmed_attributes=attrs, filters=filters)
        rows = list(first["results"])
        page = first
        while page["next_cursor"]:
            page = self.engine.more(page["next_cursor"])
            rows.extend(page["results"])
        self.assertEqual(len(rows), first["total_eligible"])
        self.assertEqual(len(rows), len({r["wine_slug"] for r in rows}))
        return first, rows

    def test_sweet_sauce_does_not_require_redundant_non_dessert_flag(self):
        a, rows_a = self.all_rows("ribeye_grilled", {"sauce_sweetness": "high"})
        b, rows_b = self.all_rows("ribeye_grilled", {"sauce_sweetness": "high", "is_dessert": False})
        self.assertEqual(a["effective_profile_id"], "sweet_glaze_rich_meat")
        self.assertEqual(a["effective_profile_id"], b["effective_profile_id"])
        self.assertEqual([r["wine_slug"] for r in rows_a], [r["wine_slug"] for r in rows_b])
        self.assertNotIn("oaky_robust_red", {self.k.style_families[r["wine_slug"]] for r in rows_a})

    def test_cream_does_not_erase_tom_yum_heat_and_acidity(self):
        first, rows = self.all_rows("tom_yam_shrimp", {"fatty_cream_sauce": True, "protein_family": "seafood"})
        self.assertEqual(first["effective_profile_id"], "spicy_sour")
        self.assertTrue(all(r["facts"]["alcohol_percent"] <= 12.5 for r in rows))
        self.assertTrue(all(r["facts"]["sweetness"] in {"semi_dry", "semi_sweet"} for r in rows))
        self.assertIn("Prioritize freshness", first["diagnostics"]["query_text"])

    def test_cream_does_not_erase_named_teriyaki_glaze(self):
        first, rows = self.all_rows("chicken_teriyaki", {"fatty_cream_sauce": True})
        self.assertEqual(first["effective_profile_id"], "sweet_glaze")
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["facts"]["sweetness"] in {"semi_dry", "semi_sweet"} for r in rows))

    def test_intrinsic_chilli_survives_an_added_cream_confirmation(self):
        first, rows = self.all_rows("spicy_butter_chicken", {"fatty_cream_sauce": True})
        self.assertEqual(first["effective_profile_id"], "spicy")
        self.assertTrue(all(r["facts"]["alcohol_percent"] <= 12.5 for r in rows))

    def test_known_fish_protein_need_not_be_repeated_by_client(self):
        attrs = {"fatty_cream_sauce": True}
        first, rows = self.all_rows("salmon_grilled_lemon", attrs)
        repeated, other = self.all_rows("salmon_grilled_lemon", {**attrs, "protein_family": "fish"})
        self.assertEqual(first["effective_profile_id"], "white_butter_cream")
        self.assertEqual(first["effective_profile_id"], repeated["effective_profile_id"])
        self.assertEqual([r["wine_slug"] for r in rows], [r["wine_slug"] for r in other])
        self.assertEqual(first["confirmed_attributes"], attrs)
        self.assertEqual(attrs, {"fatty_cream_sauce": True})
        self.assertFalse(first["diagnostics"]["sauce_rule_context"]["reference_attributes_are_visual_facts"])

    def test_ribeye_discovery_keeps_rich_meat_style_beyond_five(self):
        _, rows = self.all_rows("ribeye_grilled")
        self.assertGreater(len(rows), 5)
        self.assertTrue(any(r["selection_source"] == "embedding" for r in rows[5:]))
        self.assertTrue(all(self.k.style_families[r["wine_slug"]] in {"robust_red", "oaky_robust_red", "rounded_red"} for r in rows))

    def test_named_mixed_seafood_does_not_require_repeating_protein_for_cream(self):
        for node_id in ("seafood_pasta_tomato", "seafood_paella"):
            with self.subTest(node=node_id):
                attrs = {"fatty_cream_sauce": True}
                first, rows = self.all_rows(node_id, attrs)
                explicit, other = self.all_rows(node_id, {**attrs, "protein_family": "seafood"})
                self.assertEqual(first["effective_profile_id"], "white_butter_cream")
                self.assertEqual(first["effective_profile_id"], explicit["effective_profile_id"])
                self.assertEqual([r["wine_slug"] for r in rows], [r["wine_slug"] for r in other])
                self.assertEqual(first["confirmed_attributes"], attrs)

    def test_named_mixed_meat_matches_repeated_protein_for_chilli(self):
        for node_id in ("pasta_bolognese", "pizza_pepperoni", "crimean_cheburek_beef",
                        "blini_meat", "perm_posikunchiki_meat", "mixed_meat_solyanka"):
            with self.subTest(node=node_id):
                attrs = {"heat": "high"}
                first, rows = self.all_rows(node_id, attrs)
                explicit, other = self.all_rows(node_id, {**attrs, "protein_family": "meat"})
                self.assertEqual(first["effective_profile_id"], "spicy_meat")
                self.assertEqual(first["effective_profile_id"], explicit["effective_profile_id"])
                self.assertEqual([r["wine_slug"] for r in rows], [r["wine_slug"] for r in other])

    def test_unapplied_cream_does_not_claim_to_change_selection(self):
        _, rows = self.all_rows("ribeye_grilled", {"fatty_cream_sauce": True})
        self.assertTrue(all("сливочная жирность" not in r["reason"] for r in rows))

    def test_raw_fish_discovery_does_not_drift_to_vanilla_or_perfumed_white(self):
        _, rows = self.all_rows("salmon_sashimi")
        self.assertGreater(len(rows), 5)
        self.assertTrue(all(self.k.style_families[r["wine_slug"]] not in {"full_creamy_white", "aromatic_white"} for r in rows))

    def test_chocolate_does_not_fill_with_fruity_white_dessert_wines(self):
        first, rows = self.all_rows("dark_chocolate_brownie")
        self.assertEqual(len(rows), 3)
        self.assertEqual(len(first["results"]), 2)  # Only two distinct producers qualify.
        self.assertTrue(first["next_cursor"])
        self.assertTrue(all(r["facts"]["color"] == "red" and r["facts"]["sweetness"] == "sweet" for r in rows))

    def test_hot_sweet_sour_cream_retains_every_confirmed_dimension(self):
        attrs = {"heat": "high", "sauce_sweetness": "high", "acidity": "high", "fatty_cream_sauce": True}
        first, rows = self.all_rows("chicken_roast_herbs", attrs)
        self.assertEqual(first["effective_profile_id"], "spicy")
        self.assertEqual(first["confirmed_attributes"], attrs)
        self.assertIn("Prioritize freshness", first["diagnostics"]["query_text"])
        self.assertTrue(all(r["facts"]["alcohol_percent"] <= 12.5 for r in rows))
        self.assertTrue(all("чили" in r["reason"] and "сладость" in r["reason"] and "кислая" in r["reason"] for r in rows))

    def test_chilli_dessert_retains_sweetness_and_alcohol_cap(self):
        _, rows = self.all_rows("chocolate_fondant", {"heat": "medium", "is_dessert": True})
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["facts"]["sweetness"] == "sweet" and r["facts"]["color"] == "red" and r["facts"]["alcohol_percent"] <= 12.5 for r in rows))

    def test_rejecting_all_curated_choices_uses_only_suitable_embedding_candidates(self):
        curated = [c["wine_slug"] for c in self.k.nodes["ribeye_grilled"]["curated"]]
        _, rows = self.all_rows("ribeye_grilled", filters={"rejected_wine_slugs": curated})
        self.assertGreater(len(rows), 0)
        self.assertTrue(all(r["selection_source"] == "embedding" for r in rows))
        self.assertFalse(set(curated) & {r["wine_slug"] for r in rows})
        light = next(s for s, f in self.k.style_families.items() if f == "light_red")
        first = self.engine.recommend(node_id="ribeye_grilled", filters={"restaurant_wine_slugs": [light]})
        self.assertEqual(first["status"], "no_results")
        self.assertIsNone(first["next_cursor"])

    def test_changed_sauce_cannot_reuse_an_old_cursor(self):
        first = self.engine.recommend(node_id="ribeye_grilled")
        with self.assertRaises(PipelineError):
            self.engine.more(first["next_cursor"], confirmed_attributes={"heat": "high"})

    def test_reviewed_style_annotation_is_bound_to_source_description(self):
        raw = json.loads(default_dataset().read_bytes())
        raw["wines"][0]["style_summary"]["text_ru"] += " Changed reference."
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changed.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "annotation is stale"):
                Knowledge(path, default_style())

    def test_visual_hypothesis_never_seeds_recipe_specific_sauce_defaults(self):
        result = self.engine.recommend_from_recognition({"visual_node_id": "poultry",
            "hypothesis_node_id": "spicy_butter_chicken", "needs_clarification": True})
        self.assertEqual(result["effective_profile_id"], "poultry")
        self.assertNotIn("heat", result["diagnostics"]["sauce_rule_context"]["effective_rule_attributes"])

    def test_explicit_wine_constraints_are_not_relaxed_by_quality_policy(self):
        for filters in ({"color": "white"}, {"max_price_rub": 2000}, {"in_stock": True}):
            first, rows = self.all_rows("ribeye_grilled", filters=filters)
            self.assertEqual(rows, [])
            self.assertEqual(first["status"], "no_results")


if __name__ == "__main__":
    unittest.main()
