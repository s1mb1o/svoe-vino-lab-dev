"""Check direct label segmentation with local HTTP fakes."""

import base64
import hashlib
from io import BytesIO
from pathlib import Path
import tempfile
import os
import json
from time import perf_counter
import unittest
import zipfile
from unittest import mock

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from matcher.cascade import Cascade, CascadeConfig, Sam3Config
from matcher.cascade_run import Budget
from matcher.group import GroupMatchError
from matcher.service import ConfigError, load_matcher
from matcher.services import Services
from matcher.scripts.evaluate_label_only import accepted_slugs, metrics, read_queries

from cascade_fakes import (FakeServices, colour_vector, instance, make_bundle,
                           photo, scene)
from test_cascade_api import entry, write_config
from test_catalog import ROWS, write_catalog


CONFIG = CascadeConfig(whole_image=False, sam3=Sam3Config(hand=False), label_only=True)


class LabelOnlyRunTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake = FakeServices()
        self.addCleanup(self.fake.close)
        # The full view would return wine-d for the blue query. Only the label
        # view returns wine-a. This tests view isolation.
        bundle = make_bundle(label_rows=(((0, 0, 0, 1), "wine-a"),
                                        ((0, 1, 0, 0), "wine-b")))
        self.cascade = Cascade(CONFIG, bundle, Services(
            siglip2=self.fake.siglip2, sam3=self.fake.sam3))
        await self.cascade.start()
        self.addAsyncCleanup(self.cascade.close)

    async def predict(self):
        return await self.cascade.predict(photo(), Budget(perf_counter()))

    async def test_only_label_noun_and_label_view(self):
        slug, trace = await self.predict()
        self.assertEqual(slug, "wine-a")
        self.assertEqual(trace["decision"]["source"], "label")
        self.assertEqual(trace["decision"]["label"]["method"], "seg")
        self.assertNotIn("package", trace["decision"])
        self.assertEqual([s["id"] for s in trace["stages"]], ["sam3_label", "label"])
        self.assertEqual(self.fake.routes("segment")[0]["fields"]["texts"], b"label")
        self.assertEqual(len(self.fake.routes("embed")), 1)
        self.assertFalse(self.fake.routes("scan") or self.fake.routes("chat"))
        pairs, _ = await self.cascade.match(photo(), 2, Budget(perf_counter()))
        self.assertEqual([p[0] for p in pairs], ["wine-a", "wine-b"])

    async def test_other_bottle_labels_are_not_merged(self):
        def segment(nouns, size):
            answer = scene(nouns, size)
            answer["instances"].append(instance("label", (750, 420, 900, 550), size))
            answer["count"] += 1
            return answer
        self.fake.segment = segment
        slug, trace = await self.predict()
        self.assertEqual(slug, "wine-a")
        self.assertEqual(trace["decision"]["label"]["method"], "seg")
        self.assertLess(trace["decision"]["label"]["box"][2], 400)

    async def test_mask_background_is_white(self):
        seen = []
        def segment(nouns, size):
            answer = scene(nouns, size)
            item = answer["instances"][0]
            mask = Image.new("L", size, 0)
            ImageDraw.Draw(mask).ellipse(item["box"], fill=255)
            output = BytesIO()
            mask.save(output, "PNG")
            item["mask_png_b64"] = base64.b64encode(output.getvalue()).decode()
            return answer
        def embed(image):
            seen.append(image.copy())
            return colour_vector(image)
        self.fake.segment, self.fake.embed = segment, embed
        await self.predict()
        self.assertEqual(seen[0].getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(seen[0].getpixel((seen[0].width // 2, seen[0].height // 2)),
                         (20, 20, 220))

    async def test_no_label_has_no_embedding_or_fallback(self):
        self.fake.segment = lambda nouns, size: scene(nouns, size, label=None)
        slug, trace = await self.predict()
        self.assertEqual(slug, "")
        self.assertEqual(trace["decision"]["source"], "none")
        self.assertFalse(self.fake.routes("embed"))

    async def test_empty_mask_has_no_embedding(self):
        def segment(nouns, size):
            answer = scene(nouns, size)
            output = BytesIO()
            Image.new("L", size, 0).save(output, "PNG")
            answer["instances"][0]["mask_png_b64"] = base64.b64encode(
                output.getvalue()).decode()
            return answer
        self.fake.segment = segment
        self.assertEqual((await self.predict())[0], "")
        self.assertFalse(self.fake.routes("embed"))

    async def test_service_failure_is_not_a_no_label_result(self):
        self.fake.statuses["segment"] = 400
        with self.assertRaises(GroupMatchError):
            await self.predict()
        self.assertFalse(self.fake.routes("embed"))

    async def test_deadline_cancels_sam3_without_whole_image(self):
        self.fake.delays["segment"] = 2
        now = perf_counter()
        slug, trace = await self.cascade.predict(photo(), Budget(now, now + .1, now + .3))
        self.assertEqual(slug, "")
        self.assertEqual(trace["decision"]["reason"], "timeout")
        self.assertLess(perf_counter() - now, 1)
        self.assertFalse(self.fake.routes("embed"))


class LabelOnlyConfigTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.fake = FakeServices()
        self.addCleanup(self.fake.close)
        self.catalog = write_catalog(self.root / "catalog")

    def pipeline(self, **changes):
        value = entry(self.catalog, self.fake, label_only=True, whole_image=False,
                      barcode=None, rerank=None,
                      sam3={"endpoint": self.fake.sam3, "hand": False, "label": True})
        value.update(changes)
        return value

    def load(self, pipeline):
        return load_matcher(write_config(self.root / "config.yaml", pipeline))

    def test_valid_configuration(self):
        matcher = self.load(self.pipeline())
        self.addCleanup(matcher.cascade.executor.shutdown)
        self.assertTrue(matcher.cascade.config.label_only)
        self.assertTrue(matcher.can_match_group)

    def test_incompatible_stages_and_non_boolean_are_rejected(self):
        variants = [{"label_only": "true"}, {"whole_image": True}, {"barcode": {}},
                    {"rerank": {}}, {"sam3": {}},
                    {"sam3": {"endpoint": self.fake.sam3, "hand": True}},
                    {"sam3": {"endpoint": self.fake.sam3, "hand": False, "label": False}},
                    {"sam3": {"endpoint": self.fake.sam3, "hand": False,
                              "packages_first": True}}]
        for changes in variants:
            with self.subTest(changes=changes), self.assertRaises(ConfigError):
                self.load(self.pipeline(**changes))
        value = self.pipeline()
        del value["sam3"]
        with self.assertRaises(ConfigError):
            self.load(value)

    def test_missing_label_vectors_are_rejected(self):
        catalog = write_catalog(self.root / "full-only", rows=tuple(
            row for row in ROWS if row[0] == "full"))
        with self.assertRaisesRegex(ConfigError, "view label"):
            self.load(self.pipeline(catalog=str(catalog)))

    def test_api_prediction_match_and_empty_response(self):
        config = write_config(self.root / "api.yaml", self.pipeline())
        with mock.patch.dict(os.environ, {"SVOE_VINO_MATCHER_CONFIG": str(config)}):
            from matcher.app import create_app
        with TestClient(create_app(config)) as client:
            self.assertEqual(client.get("/readyz").status_code, 200)
            prediction = client.post("/v1/eval/predict",
                                     files={"image": ("photo.png", photo(), "image/png")})
            self.assertEqual(prediction.status_code, 200, prediction.text)
            self.assertEqual(prediction.json()["slug"], "wine-c")
            matched = client.post("/v1/match?k=2",
                                  files={"image": ("photo.png", photo(), "image/png")})
            self.assertEqual(matched.status_code, 200, matched.text)
            self.assertEqual(matched.json()["candidates"][0]["slug"], "wine-c")
            self.fake.segment = lambda nouns, size: scene(nouns, size, label=None)
            empty = client.post("/v1/eval/predict",
                                files={"image": ("photo.png", photo(), "image/png")})
            self.assertEqual(empty.status_code, 200)
            self.assertEqual(empty.json()["slug"], "")


class EvaluationInputTest(unittest.TestCase):
    def test_archive_hash_mismatch_is_refused_before_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive, expected = root / "Eval.zip", root / "expected.jsonl"
            body = photo()
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("Eval/queries.tsv", "query_id\timage_path\nq-1\tp.png\n")
                output.writestr("Eval/queries/p.png", body)
            truth = {"query_id": "q-1", "image_path": "p.png",
                     "image_sha256": hashlib.sha256(body).hexdigest(),
                     "predicted_slug": "wine-a", "alternative_slug": "wine-b"}
            expected.write_text(json.dumps(truth) + "\n")
            self.assertEqual(len(read_queries(archive, expected)), 1)
            self.assertEqual(accepted_slugs(truth), {"wine-a", "wine-b"})
            truth["image_sha256"] = "0" * 64
            expected.write_text(json.dumps(truth) + "\n")
            with self.assertRaisesRegex(ValueError, "does not match"):
                read_queries(archive, expected)

    def test_metrics_keep_query_errors_separate_from_empty_predictions(self):
        rows = [{"expected_slug": "wine-a", "predicted_slug": "wine-b",
                 "strict_hit": False, "accepted_hit": True, "error": None,
                 "latency_ms": 100},
                {"expected_slug": None, "predicted_slug": None,
                 "strict_hit": False, "accepted_hit": False, "error": {"type": "error"},
                 "latency_ms": 200}]
        result = metrics(rows)
        self.assertEqual((result["strict_hits"], result["accepted_hits"],
                          result["negative_hits"], result["errors"]), (0, 1, 0, 1))
        self.assertEqual(result["latency_ms"]["p95"], 200)
