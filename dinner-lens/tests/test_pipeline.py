"""Behavioral tests for eligibility, ordering, pagination, modifiers and API boundaries."""
import base64
import copy
import io
import json
import math
import secrets
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from dinner_lens.api import create_app
from dinner_lens.data import Knowledge
from dinner_lens.embeddings import EmbeddingIndex
from dinner_lens.engine import Engine, PipelineError, rejection_reasons, validate_filters
from dinner_lens.provider import QwenRecognizer, sanitize_image, read_response

ROOT = Path(__file__).resolve().parents[1]


class FakeRecognizer:
    def recognize(self, image):
        return {"visual_node_id": "ribeye_grilled", "hypothesis_node_id": "ribeye_grilled",
                "needs_clarification": False, "clarification_question": None}, {"returned_model": "test-double"}


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.knowledge = Knowledge(ROOT / "data/pairing-dataset.v1.json", ROOT / "prompts/style-guidance.en.json")
        cls.index = EmbeddingIndex(cls.knowledge, ROOT / "data/index")
        cls.counter = 1000.0

    def setUp(self):
        self.engine = Engine(self.knowledge, self.index, cursor_secret=b"unit-test-only-not-a-real-secret-123", clock=lambda: self.counter)

    def pages(self, first):
        pages = [first]
        while pages[-1]["next_cursor"]:
            self.assertLess(len(pages), 1000)
            pages.append(self.engine.more(pages[-1]["next_cursor"]))
        return pages

    def test_all_canonical_labels_resolve_without_llm(self):
        for node in self.knowledge.nodes.values():
            self.assertEqual(self.knowledge.resolve(node["label_ru"]), node["id"])

    def test_whole_phrase_aliases_do_not_confirm_substrings(self):
        self.assertEqual(self.knowledge.resolve("  РИБАЙ НА ГРИЛЕ  "), "ribeye_grilled")
        self.assertIsNone(self.knowledge.resolve("неизвестный салат со словом рибай"))
        self.assertIsNone(self.knowledge.resolve("стейк"))
        self.assertEqual(self.knowledge.resolve("стейк из лосося"), "fish")

    def test_curated_first_then_real_embedding_continuation(self):
        pages = self.pages(self.engine.recommend(node_id="ribeye_grilled"))
        entries = [e for page in pages for e in page["results"]]
        kinds = [e["selection_source"] for e in entries]
        self.assertIn("embedding", kinds)
        first_embedding = kinds.index("embedding")
        self.assertTrue(all(k == "curated" for k in kinds[:first_embedding]))
        self.assertTrue(all(k == "embedding" for k in kinds[first_embedding:]))
        self.assertEqual([e["wine_slug"] for e in entries[:5]], [e["wine_slug"] for e in self.knowledge.nodes['ribeye_grilled']['curated']])
        self.assertTrue(all(math.isfinite(e["ranking_evidence"]["semantic_similarity"]) for e in entries))

    def test_every_page_is_disjoint_and_retains_recipe(self):
        pages = self.pages(self.engine.recommend(node_id="ribeye_grilled"))
        slugs = [s for p in pages for s in p["wine_slugs"]]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertTrue(all(p["resolved_node_id"] == "ribeye_grilled" for p in pages))
        self.assertTrue(all(p["effective_profile_id"] == "ribeye" for p in pages))
        self.assertEqual(len(slugs), pages[0]["total_eligible"])

    def test_producer_exclusion_applies_to_all_pages(self):
        pages = self.pages(self.engine.recommend(node_id="ribeye_grilled", filters={"exclude_producer": "Фанагория"}))
        self.assertTrue(all(e["producer"] != "Фанагория" for p in pages for e in p["results"]))

    def test_explicit_dry_never_accepts_brut(self):
        pages = self.pages(self.engine.recommend(node_id="olivier_doctors", filters={"sweetness": "dry"}))
        self.assertTrue(all(e["facts"]["sweetness"] == "dry" for p in pages for e in p["results"]))

    def test_unknown_budget_returns_empty_and_keeps_exact_dish(self):
        result = self.engine.recommend(node_id="ribeye_grilled", filters={"max_price_rub": 1000})
        self.assertEqual(result["wine_slugs"], [])
        self.assertEqual(result["resolved_node_id"], "ribeye_grilled")
        self.assertTrue(result["needs_clarification"])
        self.assertIsNone(result["next_cursor"])

    def test_unknown_numerical_sugar_is_not_inferred_from_brut(self):
        result = self.engine.recommend(node_id="olivier_doctors", filters={"max_sugar_g_l": 4})
        self.assertEqual(result["wine_slugs"], [])

    def test_unknown_stock_does_not_count_as_available(self):
        self.assertEqual(self.engine.recommend(node_id="olivier_doctors", filters={"in_stock": True})["wine_slugs"], [])

    def test_conflicting_color_is_not_silently_relaxed(self):
        result = self.engine.recommend(node_id="ribeye_grilled", filters={"color": "white"})
        self.assertEqual(result["wine_slugs"], [])
        self.assertEqual(result["resolved_node_id"], "ribeye_grilled")

    def test_seen_and_rejected_wines_never_return(self):
        first = self.engine.recommend(node_id="ribeye_grilled")
        rejected = self.knowledge.nodes["ribeye_grilled"]["curated"][3]["wine_slug"]
        pages = self.pages(self.engine.recommend(node_id="ribeye_grilled", filters={"seen_wine_slugs": first["wine_slugs"], "rejected_wine_slugs": [rejected]}))
        shown = {s for p in pages for s in p["wine_slugs"]}
        self.assertFalse(shown & set(first["wine_slugs"]))
        self.assertNotIn(rejected, shown)

    def test_restaurant_wine_list_is_an_admission_filter(self):
        allowed = [self.knowledge.nodes["ribeye_grilled"]["curated"][0]["wine_slug"]]
        pages = self.pages(self.engine.recommend(node_id="ribeye_grilled", filters={"restaurant_wine_slugs": allowed}))
        self.assertEqual([s for p in pages for s in p["wine_slugs"]], allowed)
        self.assertEqual(self.engine.recommend(node_id="ribeye_grilled", filters={"restaurant_wine_slugs": []})["wine_slugs"], [])

    def test_absolute_grape_exclusion_rejects_incomplete_blends(self):
        self.assertEqual(self.engine.recommend(node_id="ribeye_grilled", filters={"grapes_exclude": ["Мерло"]})["wine_slugs"], [])

    def test_known_numeric_values_pass_and_unknowns_fail(self):
        wine = copy.deepcopy(next(iter(self.knowledge.wines.values())))
        wine.update(catalog_state="Active", discovery_eligible=True, color="red", sweetness="dry", wine_kind="still", price=1000, stock=True, residual_sugar_g_l=4)
        eligibility = {"colors": ["red"], "sweetness": ["dry"], "wine_kinds": ["still"], "max_alcohol_percent": None}
        filters = {"max_price_rub": 1000, "max_sugar_g_l": 4, "in_stock": True}
        self.assertEqual(rejection_reasons(wine, eligibility, filters), [])
        wine["price"] = None
        self.assertIn("price", rejection_reasons(wine, eligibility, filters))
        wine["price"] = True
        self.assertIn("price", rejection_reasons(wine, eligibility, filters))

    def test_inactive_and_discovery_conflicts_fail_admission(self):
        wine = copy.deepcopy(next(iter(self.knowledge.wines.values())))
        eligibility = {"colors": [wine["color"]], "sweetness": [wine["sweetness"]], "wine_kinds": [wine["wine_kind"]], "max_alcohol_percent": None}
        wine["catalog_state"] = "Archived"
        wine["discovery_eligible"] = False
        reasons = rejection_reasons(wine, eligibility, {})
        self.assertIn("catalog_not_active", reasons)
        self.assertIn("discovery_ineligible", reasons)

    def test_first_page_does_not_repeat_a_producer(self):
        for node_id in self.knowledge.nodes:
            result = self.engine.recommend(node_id=node_id)
            producers = [r["producer"] for r in result["results"]]
            self.assertEqual(len(producers), len(set(producers)), node_id)

    def test_missing_applicability_cannot_reenter_through_embeddings(self):
        for node_id in ["poultry", "game", "cheese", "desserts"]:
            blocked = {e["wine_slug"] for e in self.knowledge.nodes[node_id]["curated"] if e.get("applicability_conditions")}
            shown = {s for p in self.pages(self.engine.recommend(node_id=node_id)) for s in p["wine_slugs"]}
            self.assertFalse(shown & blocked, node_id)

    def test_conditional_styles_apply_to_all_sibling_wines_and_pages(self):
        cases = [("poultry", "color", "red", {"poultry_style": "duck"}),
                 ("game", "color", "white", {"game_type": "delicate_feathered_game"}),
                 ("cheese", "sweetness", "sweet", {"cheese_type": "blue"}),
                 ("desserts", "color", "red", {"dessert_base": "chocolate"})]
        for node, field, conditional, confirmed in cases:
            with self.subTest(node=node):
                rows = [r for p in self.pages(self.engine.recommend(node_id=node)) for r in p["results"]]
                self.assertTrue(rows)
                self.assertTrue(all(r["facts"][field] != conditional for r in rows))
                allowed = [r for p in self.pages(self.engine.recommend(node_id=node, confirmed_attributes=confirmed)) for r in p["results"]]
                self.assertTrue(any(r["facts"][field] == conditional for r in allowed))

    def test_filter_sets_are_compiled_once_per_page(self):
        from dinner_lens.engine import prepare_filters
        with patch('dinner_lens.engine.prepare_filters', wraps=prepare_filters) as prepare:
            self.engine.recommend(node_id="ribeye_grilled", filters={"exclude_producers": ["unrelated-producer"] * 2000})
            self.assertEqual(prepare.call_count, 1)

    def test_filter_size_and_cursor_size_have_consistent_bounds(self):
        with self.assertRaises(PipelineError):
            validate_filters({"exclude_producers": [str(i) + "x" * 390 for i in range(2500)]})
        result = self.engine.recommend(node_id="ribeye_grilled", filters={"seen_wine_slugs": ["unrelated-" + str(i) + "x" * 25 for i in range(2500)]})
        self.assertLess(len(result['next_cursor']), 1_500_000)
        self.assertTrue(self.engine.more(result['next_cursor'])['wine_slugs'])

    def test_huge_integer_is_rejected_and_unknown_food_validates_attributes(self):
        with self.assertRaises(PipelineError):
            self.engine.recommend(node_id="meat", filters={"max_price_rub": 10 ** 400})
        with self.assertRaises(PipelineError):
            self.engine.recommend(confirmed_dish="неизвестное блюдо", confirmed_attributes={"bogus": 1})

    def test_only_effective_modifier_ids_are_reported(self):
        result = self.engine.recommend(node_id="ribeye_grilled", confirmed_attributes={"heat": "high", "acidity": "high"})
        self.assertIn('confirmed_sour_chili', result['applied_modifier_ids'])
        self.assertIn('acidic_dressing', result['applied_modifier_ids'])
        self.assertNotIn('confirmed_chili', result['applied_modifier_ids'])
        result = self.engine.recommend(node_id="tiramisu", confirmed_attributes={"heat": "high", "is_dessert": True})
        self.assertIn('dessert_sugar', result['applied_modifier_ids'])
        self.assertNotIn('confirmed_chili', result['applied_modifier_ids'])

    def test_photo_metadata_is_stripped_and_orientation_applied(self):
        image = Image.new('RGB', (16, 8), 'red')
        exif = Image.Exif(); exif[274] = 6; exif[270] = "Private caption and location"
        buffer = io.BytesIO(); image.save(buffer, format='JPEG', exif=exif)
        sanitized, mime = sanitize_image(buffer.getvalue())
        self.assertEqual(mime, 'image/jpeg')
        with Image.open(io.BytesIO(sanitized)) as cleaned:
            self.assertEqual(cleaned.size, (8, 16))
            self.assertFalse(cleaned.getexif())
            self.assertNotIn('exif', cleaned.info)
        self.assertNotIn(b'Private caption', sanitized)

    def test_phone_mpo_jpeg_uses_primary_frame(self):
        first = Image.new('RGB', (32, 16), 'red')
        second = Image.new('RGB', (32, 16), 'blue')
        output = io.BytesIO()
        first.save(output, format='MPO', save_all=True, append_images=[second])
        with Image.open(io.BytesIO(output.getvalue())) as opened:
            self.assertEqual(opened.format, 'MPO')
        sanitized, mime = sanitize_image(output.getvalue())
        with Image.open(io.BytesIO(sanitized)) as cleaned:
            self.assertEqual(cleaned.format, 'JPEG')
            self.assertEqual(cleaned.size, (32, 16))
            self.assertGreater(cleaned.getpixel((10, 10))[0], 200)
        self.assertEqual(mime, 'image/jpeg')

    def test_corrupt_png_crc_returns_input_error(self):
        output = io.BytesIO()
        Image.new('RGB', (16, 16), 'blue').save(output, format='PNG')
        data = bytearray(output.getvalue())
        start = data.index(b'IDAT')
        length = int.from_bytes(data[start - 4:start], 'big')
        data[start + 4 + length] ^= 1
        with self.assertRaises(PipelineError):
            sanitize_image(bytes(data))

    def test_sanitizer_bounds_pixels_and_preserves_specific_errors(self):
        output = io.BytesIO()
        Image.new('RGB', (4096, 200), 'green').save(output, format='JPEG')
        sanitized, _ = sanitize_image(output.getvalue())
        with Image.open(io.BytesIO(sanitized)) as cleaned:
            self.assertLessEqual(max(cleaned.size), 2048)
        with patch('dinner_lens.provider.MAX_IMAGE_PIXELS', 1), self.assertRaisesRegex(PipelineError, 'Only bounded'):
            sanitize_image(output.getvalue())

    def test_new_conditional_styles_fail_startup_without_a_matching_gate(self):
        data = json.loads((ROOT / 'data/pairing-dataset.v1.json').read_bytes())
        node = next(n for n in data['nodes'] if n['id'] == 'fish')
        node['curated'][0]['applicability_conditions'] = [{"attribute": "sauce_sweetness", "op": "eq", "value": "high"}]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'changed.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'no matching profile-wide gate'):
                Knowledge(path, ROOT / 'prompts/style-guidance.en.json')
            node['curated'][0]['wine_slug'] = 'missing-catalog-wine'
            path.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'references an unknown wine'):
                Knowledge(path, ROOT / 'prompts/style-guidance.en.json')

    def test_non_object_provider_json_maps_to_runtime_failure(self):
        output = io.BytesIO()
        Image.new('RGB', (12, 12), 'red').save(output, format='JPEG')
        recognizer = QwenRecognizer(self.knowledge, ROOT / 'prompts/image-system.en.txt')
        for body in [[1], 'error', None]:
            with self.subTest(body=body), patch.dict('os.environ', {'QWENCLOUD_PAYGO_API_KEY': 'unit-test-placeholder'}), patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(body).encode())):
                with self.assertRaisesRegex(RuntimeError, 'all_providers_failed'):
                    recognizer.recognize(output.getvalue())

    def test_provider_response_has_deadline_and_size_bounds(self):
        with self.assertRaises(TimeoutError):
            read_response(io.BytesIO(b'{}'), 0)
        with patch('dinner_lens.provider.MAX_RESPONSE_BYTES', 1), self.assertRaises(RuntimeError):
            read_response(io.BytesIO(b'{}'), float('inf'))

    def test_photo_capacity_has_a_short_queue_timeout(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        class BlockingRecognizer:
            count = 0
            lock = threading.Lock()
            full = threading.Event()
            release = threading.Event()
            def recognize(self, image):
                with self.lock:
                    self.count += 1
                    if self.count == 4:
                        self.full.set()
                self.release.wait(5)
                return FakeRecognizer().recognize(image)
        recognizer = BlockingRecognizer()
        token = secrets.token_urlsafe(32)
        with TestClient(create_app(self.engine, recognizer, api_token=token)) as client, ThreadPoolExecutor(max_workers=4) as pool:
            def request():
                return client.post('/v1/recognize-and-recommend', headers={'Authorization': 'Bearer ' + token}, json={'image_base64': 'dGVzdA=='})
            jobs = [pool.submit(request) for _ in range(4)]
            try:
                self.assertTrue(recognizer.full.wait(3))
                self.assertEqual(request().status_code, 503)
            finally:
                recognizer.release.set()
            self.assertTrue(all(j.result().status_code == 200 for j in jobs))

    def test_confirmed_heat_changes_profile_without_changing_node(self):
        result = self.engine.recommend(node_id="ribeye_grilled", confirmed_attributes={"heat": "high"})
        self.assertEqual(result["effective_profile_id"], "spicy")
        self.assertEqual(result["resolved_node_id"], "ribeye_grilled")
        self.assertIn("confirmed_chili", result["applied_modifier_ids"])
        self.assertTrue(all(r["facts"]["color"] == "white" for r in result["results"]))

    def test_highest_priority_modifier_and_query_boost(self):
        result = self.engine.recommend(node_id="ribeye_grilled", confirmed_attributes={"heat": "high", "acidity": "high", "sauce_sweetness": "high"})
        self.assertEqual(result["effective_profile_id"], "spicy")
        self.assertIn("Prioritize freshness", result["diagnostics"]["query_text"])

    def test_unconfirmed_attributes_do_not_trigger_modifiers(self):
        result = self.engine.recommend(node_id="ribeye_grilled")
        self.assertEqual(result["applied_modifier_ids"], [])

    def test_cursor_tampering_is_rejected(self):
        cursor = self.engine.recommend(node_id="ribeye_grilled")["next_cursor"]
        body, sig = cursor.split(".")
        with self.assertRaises(PipelineError):
            self.engine.more(body[:-1] + ("A" if body[-1] != "A" else "B") + "." + sig)

    def test_cursor_expiration_is_checked(self):
        cursor = self.engine.recommend(node_id="ribeye_grilled")["next_cursor"]
        self.counter += 3601
        try:
            with self.assertRaisesRegex(PipelineError, "expired"):
                self.engine.more(cursor)
        finally:
            self.counter -= 3601

    def test_cursor_is_invalidated_by_bundle_version(self):
        cursor = self.engine.recommend(node_id="ribeye_grilled")["next_cursor"]
        self.engine.version = "different"
        with self.assertRaisesRegex(PipelineError, "changed"):
            self.engine.more(cursor)

    def test_cursor_rejects_changed_filters_or_attributes(self):
        cursor = self.engine.recommend(node_id="ribeye_grilled")["next_cursor"]
        with self.assertRaises(PipelineError):
            self.engine.more(cursor, filters={"exclude_producer": "Фанагория"})
        with self.assertRaises(PipelineError):
            self.engine.more(cursor, confirmed_attributes={"heat": "high"})

    def test_empty_explicit_secret_is_rejected(self):
        with self.assertRaises(ValueError):
            Engine(self.knowledge, self.index, cursor_secret=b"")

    def test_invalid_filters_are_not_ignored(self):
        for filters in [{"bogus": True}, {"max_price_rub": float('nan')}, {"max_price_rub": True}, {"max_sugar_g_l": -1}, {"in_stock": "yes"}, [], {"seen_wine_slugs": "abc"}]:
            with self.subTest(filters=filters), self.assertRaises(PipelineError):
                self.engine.recommend(node_id="ribeye_grilled", filters=filters)

    def test_unknown_food_does_not_get_random_wines(self):
        result = self.engine.recommend(confirmed_dish="неизвестное блюдо")
        self.assertEqual(result["status"], "needs_category")
        self.assertEqual(result["wine_slugs"], [])
        self.assertEqual(len(result["categories"]), 16)

    def test_photo_hypothesis_is_not_a_recipe_confirmation(self):
        result = self.engine.recommend_from_recognition(FakeRecognizer().recognize(b'')[0])
        self.assertEqual(result["resolved_node_id"], "meat_steak")
        self.assertTrue(result["needs_clarification"])
        self.assertTrue(result["resolution"]["guardrail_demoted"])

    def test_unknown_recognition_id_is_rejected(self):
        with self.assertRaises(PipelineError):
            self.engine.recommend_from_recognition({"visual_node_id": "invented", "hypothesis_node_id": None})

    def test_qwen_payload_contains_only_english_instructions_and_reference_data(self):
        recognizer = QwenRecognizer(self.knowledge, ROOT / "prompts/image-system.en.txt")
        data = io.BytesIO()
        Image.new('RGB', (12, 12), 'white').save(data, format='JPEG')
        payload = recognizer.payload(data.getvalue())
        self.assertEqual(payload["model"], "qwen3.8-flash")
        self.assertEqual(payload["messages"][1]["content"][1]["text"], "Identify the dish in the photograph and any recipe details that must be clarified before selecting wine.")
        serialized = json.dumps(payload)
        self.assertNotIn('ground-truth', serialized)
        self.assertNotIn('expected', serialized)

    def test_api_auth_validation_and_photo_route(self):
        token = secrets.token_urlsafe(32)
        app = create_app(self.engine, FakeRecognizer(), api_token=token)
        with TestClient(app) as client:
            self.assertEqual(client.get('/health').status_code, 200)
            self.assertEqual(client.post('/v1/recommendations', json={"node_id": "meat"}).status_code, 401)
            headers = {"Authorization": "Bearer " + token}
            result = client.post('/v1/recommendations', headers=headers, json={"node_id": "ribeye_grilled"})
            self.assertEqual(result.status_code, 200)
            self.assertTrue(result.json()['results'])
            cursor = result.json()['next_cursor']
            more = client.post('/v1/recommendations/more', headers=headers, json={"cursor": cursor})
            self.assertEqual(more.status_code, 200)
            self.assertFalse(set(result.json()['wine_slugs']) & set(more.json()['wine_slugs']))
            self.assertEqual(client.post('/v1/recommendations', headers=headers, json={"node_id": "meat", "bogus": 1}).status_code, 422)
            self.assertEqual(client.post('/v1/recommendations', headers=headers, json={"node_id": "meat", "limit": True}).status_code, 422)
            photo = client.post('/v1/recognize-and-recommend', headers=headers, json={"image_base64": base64.b64encode(b'test').decode()})
            self.assertEqual(photo.status_code, 200)
            self.assertEqual(photo.json()['resolved_node_id'], 'meat_steak')
            too_large = client.post('/v1/recommendations', headers=headers, content=b' ' * (8 * 1024 * 1024 + 1))
            self.assertEqual(too_large.status_code, 413)


if __name__ == '__main__':
    unittest.main()
