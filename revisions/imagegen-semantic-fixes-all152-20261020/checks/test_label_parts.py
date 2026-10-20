"""Test label-piece retrieval, VLM integration, and controlled evaluation settings."""

import base64
from io import BytesIO
import os
from pathlib import Path
import tempfile
from time import perf_counter
import unittest
from unittest import mock

import yaml
from fastapi.testclient import TestClient
from PIL import Image

from matcher.cascade import Cascade, CascadeConfig, RerankConfig, Sam3Config
from matcher.cascade_run import Budget
from matcher.group import GroupMatchError
from matcher.rerank import RuleBook
from matcher.service import ConfigError, load_matcher
from matcher.services import Services
from matcher.siglip2 import Siglip2Error

from cascade_fakes import (FakeServices, chat_body, instance, make_bundle, photo,
                           rules, scene)
from test_cascade_api import entry, write_cascade_catalog, write_config
from test_catalog import ROWS, write_catalog


class LabelPartsEvaluationTest(unittest.TestCase):
    def test_controlled_pair_differs_only_in_crop_view(self):
        from matcher.scripts.evaluate_label_parts import make_cells
        config = yaml.safe_load((Path(__file__).parents[1] / "config.yaml").read_text())
        cells = make_cells(config)
        self.assertEqual(len(cells), 4)
        self.assertNotIn("rerank", cells["parts"])
        self.assertNotIn("rerank", cells["direct"])
        self.assertTrue(cells["direct"]["label_only"])
        a, b = (dict(cells[name]) for name in ("parts-vlm", "full-vlm"))
        self.assertEqual(a.pop("crop_view"), "label")
        self.assertEqual(b.pop("crop_view"), "full")
        a.pop("name")
        b.pop("name")
        self.assertEqual(a, b)
        self.assertNotIn("rot5", a["embedding"])

    def test_paired_scoring_and_query_alignment(self):
        from matcher.scripts.evaluate_label_parts import paired
        before = [{"query_id": "a", "predicted_slug": "x", "accepted_hit": False},
                  {"query_id": "b", "predicted_slug": "y", "accepted_hit": True}]
        after = [{"query_id": "a", "predicted_slug": "y", "accepted_hit": True},
                 {"query_id": "b", "predicted_slug": "x", "accepted_hit": False}]
        result = paired(before, after)
        self.assertEqual((result["wins"], result["losses"]), (1, 1))
        with self.assertRaises(ValueError):
            paired(before, after[:1])
        with self.assertRaises(ValueError):
            paired(before, after[::-1])


def multipart_scene(nouns, size, packages=True):
    """Two body-label pieces and a large label on another bottle."""
    answer = scene(nouns, size, packages=((200, 100, 400, 700),) if packages else ())
    sx, sy = size[0] / 600, size[1] / 800
    for box in ((240, 575, 360, 650), (460, 300, 575, 590)):
        scaled = tuple(round(n * (sx if i % 2 == 0 else sy)) for i, n in enumerate(box))
        answer["instances"].append(instance("label", scaled, size))
    answer["count"] = len(answer["instances"])
    return answer


class LabelPartsRunTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake = FakeServices()
        self.addCleanup(self.fake.close)

    async def cascade(self, vlm=False):
        config = CascadeConfig(whole_image=False, sam3=Sam3Config(), crop_view="label",
                               rerank=RerankConfig() if vlm else None)
        bundle = make_bundle(label_rows=(((0, 0, 0, 1), "wine-a"),
                                        ((0, .1, 0, .99), "wine-a2")))
        cascade = Cascade(config, bundle, Services(siglip2=self.fake.siglip2,
                           sam3=self.fake.sam3, vlm=self.fake.vlm if vlm else None),
                           rules=RuleBook(*rules()) if vlm else None)
        await cascade.start()
        self.addAsyncCleanup(cascade.close)
        return cascade

    async def test_two_body_pieces_are_retained_and_other_bottle_is_excluded(self):
        self.fake.segment = multipart_scene
        cascade = await self.cascade()
        slug, trace = await cascade.predict(photo(), Budget(perf_counter()))
        self.assertEqual(slug, "wine-a")
        label = trace["decision"]["label"]
        self.assertEqual((label["method"], label["parts"]), ("crop", 2))
        self.assertGreaterEqual(label["box"][3], 649)
        self.assertLess(label["box"][2], 400)
        self.assertEqual({s["id"] for s in trace["stages"]}, {"sam3_full", "label"})
        self.assertEqual(self.fake.routes("segment")[0]["fields"]["texts"],
                         b"wine bottle, can, packet, box, hand, label")
        self.assertEqual(len(self.fake.routes("embed")), 1)

    async def test_vlm_changes_label_ranking_and_receives_both_parts(self):
        self.fake.segment = multipart_scene
        self.fake.chat = lambda payload: chat_body({"wine": "B"})
        cascade = await self.cascade(vlm=True)
        pairs, trace = await cascade.match(photo(), 2, Budget(perf_counter()))
        self.assertEqual([p[0] for p in pairs], ["wine-a2", "wine-a"])
        self.assertEqual(trace["decision"]["source"], "rerank")
        self.assertTrue(trace["decision"]["rerank"]["changed"])
        payload = self.fake.routes("chat")[0]["fields"]
        encoded = payload["messages"][0]["content"][0]["image_url"]["url"].split(",", 1)[1]
        with Image.open(BytesIO(base64.b64decode(encoded))) as image:
            # The retained strip makes the image taller than the largest mask alone.
            self.assertGreater(image.height / image.width, 2.3)

    async def test_no_package_does_not_merge_unassociated_labels(self):
        self.fake.segment = lambda nouns, size: multipart_scene(nouns, size, packages=False)
        cascade = await self.cascade()
        _, trace = await cascade.predict(photo(), Budget(perf_counter()))
        self.assertEqual(trace["decision"]["label"]["parts"], 1)
        self.assertNotIn("package", trace["decision"])

    async def test_single_label_close_up_still_matches(self):
        self.fake.segment = lambda nouns, size: scene(nouns, size, packages=())
        cascade = await self.cascade()
        slug, trace = await cascade.predict(photo(), Budget(perf_counter()))
        self.assertEqual(slug, "wine-a")
        self.assertEqual(trace["decision"]["label"]["method"], "seg")

    async def test_no_label_has_no_whole_image_fallback(self):
        self.fake.segment = lambda nouns, size: scene(nouns, size, label=None)
        cascade = await self.cascade(vlm=True)
        slug, trace = await cascade.predict(photo(), Budget(perf_counter()))
        self.assertEqual(slug, "")
        self.assertEqual(trace["decision"]["source"], "none")
        self.assertFalse(self.fake.routes("embed") or self.fake.routes("chat"))

    async def test_sam3_error_has_no_whole_image_fallback(self):
        self.fake.statuses["segment"] = 400
        cascade = await self.cascade()
        with self.assertRaises(GroupMatchError):
            await cascade.predict(photo(), Budget(perf_counter()))
        self.assertFalse(self.fake.routes("embed"))

    async def test_embedding_error_is_explicit(self):
        self.fake.statuses["embed"] = 400
        cascade = await self.cascade()
        with self.assertRaises(Siglip2Error):
            await cascade.predict(photo(), Budget(perf_counter()))
        self.assertEqual(len(self.fake.routes("embed")), 1)

    async def test_slow_vlm_returns_label_ranking_at_answer_deadline(self):
        self.fake.delays["chat"] = 2
        cascade = await self.cascade(vlm=True)
        now = perf_counter()
        slug, trace = await cascade.predict(photo(), Budget(now, now + .6, now + 1.5))
        self.assertEqual(slug, "wine-a")
        self.assertEqual(trace["decision"]["reason"], "answer_at")
        self.assertEqual(trace["decision"]["source"], "label")
        self.assertEqual(next(s for s in trace["stages"] if s["id"].startswith("vlm:"))
                         ["status"], "cancelled")


class LabelPartsConfigTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.fake = FakeServices()
        self.addCleanup(self.fake.close)
        self.catalog = write_cascade_catalog(self.root / "catalog")

    def pipeline(self, **changes):
        return entry(self.catalog, self.fake, crop_view="label", whole_image=False,
                     barcode=None, **changes)

    def test_valid_configuration_with_vlm(self):
        matcher = load_matcher(write_config(self.root / "config.yaml", self.pipeline()))
        self.addCleanup(matcher.cascade.executor.shutdown)
        self.assertEqual(matcher.cascade.config.crop_view, "label")
        self.assertIsNotNone(matcher.cascade.config.rerank)
        self.assertTrue(matcher.can_match_group)

    def test_invalid_view_and_incompatible_stages(self):
        for changes in ({"crop_view": "wrong"}, {"crop_view": True}, {"crop_view": []},
                        {"whole_image": True}, {"label_only": True}, {"sam3": None},
                        {"sam3": {"endpoint": self.fake.sam3, "label": False}},
                        {"sam3": {"endpoint": self.fake.sam3, "packages_first": True}}):
            value = self.pipeline()
            value.update(changes)
            if value.get("sam3", 1) is None:
                value.pop("sam3")
            with self.subTest(changes=changes), self.assertRaises(ConfigError):
                load_matcher(write_config(self.root / "bad.yaml", value))

    def test_missing_label_vectors_are_rejected(self):
        catalog = write_catalog(self.root / "full-only", rows=tuple(
            row for row in ROWS if row[0] == "full"))
        value = self.pipeline(rerank=None)
        value["catalog"] = str(catalog)
        with self.assertRaisesRegex(ConfigError, "view label"):
            load_matcher(write_config(self.root / "bad.yaml", value))

    def test_api_predict_match_and_no_label(self):
        config = write_config(self.root / "api.yaml", self.pipeline(rerank=None))
        with mock.patch.dict(os.environ, {"SVOE_VINO_MATCHER_CONFIG": str(config)}):
            from matcher.app import create_app
        with TestClient(create_app(config)) as client:
            for endpoint in ("/v1/eval/predict", "/v1/match?k=2"):
                reply = client.post(endpoint, files={"image": ("p.png", photo(), "image/png")})
                self.assertEqual(reply.status_code, 200, reply.text)
                if endpoint.endswith("predict"):
                    self.assertEqual(reply.json()["slug"], "wine-c")
                else:
                    self.assertEqual(reply.json()["candidates"][0]["slug"], "wine-c")
            self.fake.segment = lambda nouns, size: scene(nouns, size, label=None)
            reply = client.post("/v1/match", files={"image": ("p.png", photo(), "image/png")})
            self.assertEqual(reply.status_code, 200)
            self.assertEqual(reply.json()["candidates"], [])
