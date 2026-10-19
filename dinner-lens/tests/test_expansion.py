"""Coverage expansion must preserve old recipes, evidence and safe ambiguity."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import numpy as np
import yaml

from dinner_lens.api import app_from_environment
from dinner_lens.data import Knowledge
from dinner_lens.embeddings import EmbeddingIndex
from dinner_lens.engine import Engine, PipelineError
from dinner_lens.paths import default_dataset, default_index

ROOT = Path(__file__).resolve().parents[1]
SECRET = b"expansion-test-only-secret-at-least-32-bytes"


class ExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = Knowledge(ROOT / "data/pairing-dataset.v1.json", ROOT / "prompts/style-guidance.en.json")
        cls.new = Knowledge(ROOT / "data/pairing-dataset.v2.json", ROOT / "prompts/style-guidance.en.json")
        cls.old_index = EmbeddingIndex(cls.old, ROOT / "data/index")
        cls.new_index = EmbeddingIndex(cls.new, ROOT / "data/index.v2")

    def test_original_nodes_and_embedding_inputs_preserved(self):
        self.assertEqual(len(self.new.nodes), 320)
        self.assertEqual(sum(n["kind"] == "dish" for n in self.new.nodes.values()), 200)
        for node_id, node in self.old.nodes.items():
            self.assertEqual(self.new.nodes[node_id], node)
        self.assertEqual(self.new.embedding_documents(), self.old.embedding_documents())
        self.assertTrue(np.array_equal(self.old_index.matrix, self.new_index.matrix))

    def test_default_factory_serves_expansion(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            document = yaml.safe_load((ROOT / "config.yaml").read_text())
            document["assets"]["index"] = str(ROOT / "data/index.v4")
            config_path.write_text(yaml.safe_dump(document))
            with patch.dict(os.environ, {"QWENCLOUD_PAYGO_API_KEY": "unit-test-placeholder", "DINNER_LENS_CONFIG": str(config_path), "DINNER_LENS_API_TOKEN": "expanded-test-token-at-least-24-characters",
                                    "DINNER_LENS_CURSOR_SECRET": "expansion-cursor-secret-at-least-32-bytes"}):
                with TestClient(app_from_environment()) as client:
                    response = client.post("/v1/recommendations", json={"confirmed_dish": "Хумус с тахини"},
                        headers={"Authorization": "Bearer expanded-test-token-at-least-24-characters"})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["resolved_node_id"], "hummus_tahini")
                    self.assertTrue(all(r["selection_source"] == "curated" for r in response.json()["results"]))

    def test_ambiguous_names_do_not_confirm_hidden_recipes(self):
        for phrase, expected in {"роллы": "sushi_rolls", "паста": "pasta", "цезарь": "salads",
                "плов": "rice_dishes", "голубцы": "mixed_dishes", "тартар": None,
                "котлета": None, "шашлык": None, "вареники": None, "паштет": None,
                "хумус": "chickpea_dishes", "фалафель": "legumes", "цезарь с курицей": "salads"}.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(self.new.resolve(phrase), expected)

    def test_different_sauces_select_different_styles(self):
        engine = Engine(self.new, self.new_index, cursor_secret=SECRET)
        for node, profile in {"chicken_roast_herbs": "poultry", "chicken_teriyaki": "sweet_glaze",
                "spicy_butter_chicken": "spicy", "salmon_nigiri": "raw_fish",
                "eel_unagi_roll": "sweet_glaze", "vegetable_rice_cabbage_rolls": "vegetables_tomato",
                "blue_cheese_pear": "blue_cheese", "chocolate_fondant": "coffee_cocoa"}.items():
            with self.subTest(node=node):
                response = engine.recommend(node_id=node)
                self.assertEqual(response["effective_profile_id"], profile)
                self.assertGreaterEqual(len(response["results"]), 3)
        dessert = engine.recommend(node_id="chocolate_fondant")
        self.assertTrue(all(r["facts"]["sweetness"] == "sweet" for r in dessert["results"]))

    def test_cross_version_cursors_and_indices_rejected(self):
        old = Engine(self.old, self.old_index, cursor_secret=SECRET)
        new = Engine(self.new, self.new_index, cursor_secret=SECRET)
        cursor = old.recommend(node_id="ribeye_grilled")["next_cursor"]
        with self.assertRaises(PipelineError) as error:
            new.more(cursor)
        self.assertEqual(error.exception.code, "stale_cursor")
        with self.assertRaises(ValueError):
            EmbeddingIndex(self.new, ROOT / "data/index")

    def test_new_visual_recipe_still_requires_confirmation(self):
        engine = Engine(self.new, self.new_index, cursor_secret=SECRET)
        page = engine.recommend_from_recognition({"visual_node_id": "philadelphia_salmon_cream_cheese",
            "hypothesis_node_id": "philadelphia_salmon_cream_cheese", "needs_clarification": False})
        self.assertEqual(page["resolved_node_id"], "cream_cheese_rolls")
        self.assertTrue(page["needs_clarification"])
        self.assertFalse(page["resolution"]["recipe_confirmed_by_user"])

    def test_every_fallback_has_recipe_examples(self):
        roots = [n["id"] for n in self.new.nodes.values() if n["kind"] == "fallback_class"]
        for root in roots:
            self.assertTrue(any(n["kind"] == "dish" and root in n["hierarchy_path"] for n in self.new.nodes.values()), root)
        self.assertEqual(self.new.nodes["rassolnik_beef"]["parent_id"], "sour_brine_soups")
        self.assertEqual(self.new.nodes["salmon_grilled_lemon"]["parent_id"], "grilled_fish")
        self.assertEqual(self.new.nodes["baked_brie"]["parent_id"], "soft_ripened_cheese")
        self.assertEqual(self.new.nodes["vegetable_dumplings"]["parent_id"], "savory_pastry")
        self.assertNotIn("dumplings", self.new.nodes["vareniki_potato"]["hierarchy_path"])

    def test_ambiguity_and_new_classes_ask_for_refinement(self):
        engine = Engine(self.new, self.new_index, cursor_secret=SECRET)
        for name in ("паста", "цезарь", "роллы", "чизкейк"):
            page = engine.recommend(confirmed_dish=name)
            self.assertTrue(page["needs_clarification"], name)
            self.assertTrue(page["clarification_question"], name)
        self.assertEqual(engine.recommend(confirmed_dish="чизкейк")["resolved_node_id"], "desserts")
        question = self.new.nodes["duck_confit_lingonberry"]["clarifying_question_ru"]
        self.assertIn("сладость", question)
        self.assertIn("жгучесть", question)

    def test_recipe_style_refinements_hold_across_discovery(self):
        engine = Engine(self.new, self.new_index, cursor_secret=SECRET)
        for node, field, values in [("caesar_chicken", "sweetness", {"dry", "brut"}),
                ("shakshuka_tomato", "color", {"red", "rose"})]:
            page = engine.recommend(node_id=node)
            entries = list(page["results"])
            while page["next_cursor"]:
                page = engine.more(page["next_cursor"])
                entries.extend(page["results"])
            self.assertIn("embedding", {e["selection_source"] for e in entries})
            self.assertTrue(all(e["facts"][field] in values for e in entries))
        spicy = engine.recommend(node_id="caesar_chicken", confirmed_attributes={"heat": "high"})
        self.assertEqual(spicy["effective_profile_id"], "spicy")
        self.assertTrue(all(e["facts"]["sweetness"] in {"semi_dry", "semi_sweet"} for e in spicy["results"]))

    def test_node_refinements_cannot_widen_style_eligibility(self):
        raw = json.loads(self.new.path.read_bytes())
        node = next(n for n in raw["nodes"] if n["id"] == "caesar_chicken")
        node["pairing_rule"]["eligibility_overrides"] = {"colors": ["orange"]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must narrow"):
                Knowledge(path, ROOT / "prompts/style-guidance.en.json")


if __name__ == "__main__":
    unittest.main()
