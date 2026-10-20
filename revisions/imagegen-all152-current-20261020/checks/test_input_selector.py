"""Config, coordinate and runtime contracts of the optional matcher input module."""

from copy import deepcopy
from dataclasses import replace
from io import BytesIO
import os
from pathlib import Path
import tempfile
from time import perf_counter
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np
from PIL import Image

from matcher.cascade import BarcodeConfig, Cascade, CascadeConfig, RerankConfig, Sam3Config
from matcher.cascade_run import Budget, Run
from matcher.group import GroupMatchError
from matcher.input_selector import InputSelector, scale_box
from matcher.semantic_selector import NOUNS, select
from matcher.selective_ocr import SelectiveOCRConfig
from matcher.service import ConfigError, READINESS_TIMEOUT_SECONDS, load_matcher
from matcher.services import Services

from cascade_fakes import (LABEL, PACKAGE, SIZE, FakeServices, instance, make_bundle,
                           photo, scene)
from test_cascade_api import entry, write_cascade_catalog
from test_match import write_bundle_v2, write_config


ENABLED = {"enabled": True, "variant": "semantic-v2"}


def encoded(image):
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class InputSelectorConfigTest(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = Path(root.name)
        write_bundle_v2(self.root / "bundle")

    def load(self, **options):
        pipeline = dict(name="input-test", backend="siglip2",
                        bundle=str(self.root / "bundle"), endpoint="http://siglip.test")
        pipeline.update(options)
        return load_matcher(write_config(self.root / "config.yaml", pipeline))

    def test_default_and_disabled_need_no_sam3_and_preserve_original_bytes(self):
        for options in ({}, {"input_selector": {"enabled": False}},
                        {"input_selector": {"variant": "semantic-v2"}}):
            matcher = self.load(**options)
            with mock.patch("matcher.input_selector.select_photo") as selector:
                self.assertEqual(matcher._single_image(b"original"), b"original")
            selector.assert_not_called()

    def test_enabled_variant_and_existing_hand_option_load(self):
        self.assertEqual(self.load(input_selector=ENABLED).input_selector,
                         InputSelector(True, "semantic-v2"))
        self.assertTrue(self.load(hand_selection=True).hand_selection)
        self.assertEqual(self.load(input_selector={"enabled": True, "variant": "scene-v1"})
                         .input_selector.variant, "scene-v1")

    def test_checked_in_example_enables_selection_and_default_config_does_not(self):
        directory = Path(__file__).resolve().parents[1]
        with mock.patch.dict(os.environ, {"SIGLIP2_ENDPOINT": "http://siglip.test"}):
            self.assertTrue(load_matcher(directory / "config.main-selector.example.yaml")
                            .input_selector.enabled)
            self.assertFalse(load_matcher(directory / "config.yaml").input_selector.enabled)

    def test_invalid_settings_are_rejected_even_when_disabled(self):
        for value in (True, "semantic-v2", [], {"enabled": 1}, {"enabled": "true"},
                      {"variant": None}, {"variant": []}, {"variant": "unknown"},
                      {"enable": True}, {"enabled": False, "variant": "unknown"}):
            with self.subTest(value=value), self.assertRaises(ConfigError):
                self.load(input_selector=value)

    def test_enabled_mock_or_duplicate_preprocessing_is_rejected(self):
        for options in (dict(backend="mock", answers={}, input_selector=ENABLED),
                        dict(hand_selection=True, input_selector=ENABLED)):
            with self.subTest(options=options), self.assertRaises(ConfigError):
                self.load(**options)

    def test_siglip_predict_and_match_receive_the_selected_fallback_crop(self):
        matcher = self.load(input_selector=ENABLED)
        decision = select(Image.new("RGB", (80, 120), "orange"), [])
        with (mock.patch("matcher.input_selector.select_photo", return_value=decision) as selector,
              mock.patch.object(type(matcher.backend), "predict", return_value="wine-a") as predict,
              mock.patch.object(type(matcher.backend), "embed", return_value=[1, 0, 0, 0]) as embed,
              mock.patch.dict(os.environ, {"SAM3_ENDPOINT": "http://sam3.test"})):
            self.assertEqual(matcher.predict(b"raw"), "wine-a")
            matcher.match(b"raw", 2)
        predict.assert_called_once_with(decision.crop)
        self.assertEqual(selector.call_count, 2)
        self.assertEqual(selector.call_args.args, (b"raw", "http://sam3.test"))
        with Image.open(BytesIO(embed.call_args.args[0])) as image:
            self.assertEqual(image.size, (80, 120))

    def test_readiness_checks_the_enabled_selector_with_bounded_timeout(self):
        matcher = self.load(input_selector=ENABLED)
        with (mock.patch("matcher.input_selector.select_photo",
                         return_value=SimpleNamespace(crop=photo())) as selector,
              mock.patch.object(type(matcher.backend), "embed", return_value=[1, 0, 0, 0])):
            matcher.check_ready()
        self.assertEqual(selector.call_args.kwargs["timeout"], READINESS_TIMEOUT_SECONDS)

    def test_group_calls_bypass_input_selection(self):
        matcher = self.load(input_selector=ENABLED)
        with (mock.patch("matcher.input_selector.select_photo") as selector,
              mock.patch.object(type(matcher.backend), "embed_many",
                                side_effect=[[[1, 0, 0, 0]], [[1, 0, 0, 0]] * 2])):
            self.assertEqual(len(matcher.match_many([photo()], 1)), 1)
            self.assertEqual(len(matcher.match_group_many([photo()], [photo()], 1)), 1)
        selector.assert_not_called()

    def test_selector_dependency_errors_propagate_without_embedding(self):
        matcher = self.load(input_selector=ENABLED)
        with (mock.patch("matcher.input_selector.select_photo",
                         side_effect=GroupMatchError(504, "timed out")),
              mock.patch.object(type(matcher.backend), "embed") as embed):
            with self.assertRaises(GroupMatchError):
                matcher.match(b"raw", 1)
        embed.assert_not_called()

    def test_cascade_config_loads_and_group_matcher_stays_disabled(self):
        catalog = write_cascade_catalog(self.root / "catalog")
        endpoints = SimpleNamespace(siglip2="http://fake", sam3="http://fake/sam3",
                                    scanner="http://fake/qr", vlm="http://fake/vlm")
        matcher = load_matcher(write_config(self.root / "config.yaml",
                              entry(catalog, endpoints, input_selector=ENABLED)))
        self.addCleanup(matcher.cascade.executor.shutdown)
        self.assertTrue(matcher.cascade.config.input_selector.enabled)
        self.assertFalse(matcher.group.input_selector.enabled)

    def test_cascade_rejects_modes_that_bypass_the_shared_detection_set(self):
        endpoints = SimpleNamespace(siglip2="http://fake", sam3="http://fake/sam3",
                                    scanner="http://fake/qr", vlm="http://fake/vlm")
        for changes in (dict(sam3=None), dict(label_only=True, whole_image=False,
                                             barcode=None, rerank=None),
                        dict(crop_view="label", whole_image=False),
                        dict(sam3={"endpoint": endpoints.sam3, "packages_first": True}),
                        dict(sam3={"endpoint": endpoints.sam3, "hand": False}),
                        dict(sam3={"endpoint": endpoints.sam3, "label": False})):
            pipeline = entry(self.root / "unused", endpoints, input_selector=ENABLED, **changes)
            with self.subTest(changes=changes), self.assertRaises(ConfigError):
                load_matcher(write_config(self.root / "config.yaml", pipeline))


class InputSelectorCoordinatesTest(unittest.TestCase):
    def test_disabled_module_never_decodes(self):
        self.assertEqual(InputSelector().prepare(b"unchanged", None), b"unchanged")
        with self.assertRaisesRegex(ValueError, "disabled"):
            InputSelector().select(Image.new("RGB", (2, 2)), [])

    def test_stretched_masks_use_original_photo_pixel_distances_and_keep_source_ids(self):
        size = (400, 200)
        detector_size = (240, 240)
        # In stretched coordinates the left bottle is nearer. In photo pixels
        # the upper bottle is nearer; neither visible mask covers photo center.
        boxes = [(80, 60, 120, 140), (190, 0, 230, 40)]
        instances = [instance("wine bottle", scale_box(b, size, detector_size), detector_size)
                     for b in boxes]
        instances.insert(0, dict(label="hand", score=0.1, box=[0, 0, 1, 1], mask_png_b64=""))
        before = deepcopy(instances)
        decision = InputSelector(True).select(Image.new("RGB", size), instances,
                                              detection_size=detector_size)
        self.assertEqual(decision.selected_id, "d2")
        self.assertEqual(decision.reason, "fallback_nearest_center")
        self.assertEqual(instances, before)

    def test_equal_coordinate_sizes_reuse_detections_without_remapping(self):
        image = Image.new("RGB", (100, 100))
        items = [instance("wine bottle", (30, 5, 70, 95), image.size)]
        with mock.patch("matcher.input_selector._remap") as remap:
            self.assertIsNotNone(InputSelector(True).select(image, items,
                                                          detection_size=image.size).crop)
        remap.assert_not_called()

    def test_rectangle_projection_rounds_outwards_and_clips(self):
        self.assertEqual(scale_box((1, 2, 9, 10), (11, 11), (20, 25)), (1, 4, 17, 23))
        self.assertEqual(scale_box((-1, -1, 12, 12), (11, 11), (20, 25)), (0, 0, 20, 25))


class CascadeInputSelectorTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake = FakeServices()
        self.addCleanup(self.fake.close)
        self.config = CascadeConfig(sam3=Sam3Config(), input_selector=InputSelector(True))
        # The new module requests wine label; the legacy fake scene uses label.
        def detector(nouns, size):
            payload = scene(tuple("label" if n == "wine label" else n for n in nouns), size)
            for item in payload["instances"]:
                if item["label"] == "label":
                    item["label"] = "wine label"
            return payload
        self.fake.segment = detector

    async def cascade(self, config=None):
        cascade = Cascade(config or self.config, make_bundle(),
                          Services(siglip2=self.fake.siglip2, sam3=self.fake.sam3,
                                   scanner=self.fake.scanner))
        await cascade.start()
        self.addAsyncCleanup(cascade.close)
        return cascade

    async def test_selected_crop_uses_one_shared_detector_request_and_no_whole_photo_embedding(self):
        cascade = await self.cascade()
        slug, trace = await cascade.predict(photo(), Budget(perf_counter()))
        self.assertEqual(slug, "wine-a")
        audit = trace["decision"]["input_selector"]
        self.assertEqual((audit["variant"], audit["selected_id"]), ("semantic-v2", "d0"))
        segments = [r for r in self.fake.requests if r["route"] == "segment"]
        self.assertEqual(len(segments), 1)
        self.assertEqual(set(segments[0]["fields"]["texts"].decode().split(", ")), set(NOUNS))
        ids = [s["id"] for s in trace["stages"]]
        self.assertEqual(ids.count("sam3_full"), 1)
        self.assertNotIn("whole", ids)
        self.assertEqual(len([r for r in self.fake.requests if r["route"] == "embed"]), 1)
        self.assertEqual(trace["decision"]["label"]["method"], "complete-context")

    async def test_no_candidates_still_embeds_the_entire_frame_as_a_crop(self):
        self.fake.segment = lambda nouns, size: dict(width=size[0], height=size[1],
                                                    count=0, instances=[])
        cascade = await self.cascade()
        pairs, trace = await cascade.match(photo(), 2, Budget(perf_counter()))
        self.assertTrue(pairs)
        self.assertEqual(trace["decision"]["package"]["box"], [0, 0, *SIZE])
        self.assertEqual(trace["decision"]["input_selector"]["crop_scope"], "original_frame")
        self.assertEqual(trace["decision"]["input_selector"]["selection_mode"], "fallback")

    async def test_dependency_failure_cannot_embed_or_scan_the_unselected_photo(self):
        self.fake.statuses["segment"] = 500
        cascade = await self.cascade(replace(self.config, barcode=BarcodeConfig()))
        with self.assertRaises(GroupMatchError):
            await cascade.match(photo(), 2, Budget(perf_counter()))
        self.assertFalse(any(r["route"] in ("embed", "scan") for r in self.fake.requests))

    async def test_hard_deadline_does_not_return_an_unselected_whole_photo_answer(self):
        self.fake.delays["segment"] = 0.3
        cascade = await self.cascade()
        now = perf_counter()
        slug, trace = await cascade.predict(photo(), Budget(now, now + 0.05, now + 0.1))
        self.assertEqual(slug, "")
        self.assertEqual(trace["decision"]["reason"], "timeout")
        self.assertFalse(any(r["route"] == "embed" for r in self.fake.requests))

    async def test_barcode_reads_only_selected_package_and_label(self):
        scans = []
        self.fake.scan = lambda image: scans.append(image.copy()) or []
        cascade = await self.cascade(replace(self.config, barcode=BarcodeConfig()))
        _, trace = await cascade.predict(photo(), Budget(perf_counter()))
        stages = {s["id"] for s in trace["stages"]}
        self.assertNotIn("scan_full", stages)
        self.assertIn("scan_package", stages)
        self.assertIn("scan_label", stages)
        self.assertEqual(len(scans), 2)
        for image in scans:
            self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))

    async def test_barcode_without_extra_crops_still_scans_the_selected_input(self):
        cascade = await self.cascade(replace(self.config, barcode=BarcodeConfig(crops=False)))
        _, trace = await cascade.predict(photo(), Budget(perf_counter()))
        stages = {s["id"] for s in trace["stages"]}
        self.assertIn("scan_package", stages)
        self.assertNotIn("scan_full", stages)
        self.assertNotIn("scan_label", stages)
        self.assertEqual(len(self.fake.routes("scan")), 1)

    async def test_cascade_crop_and_label_keep_original_rgb_pixels_at_full_resolution(self):
        cascade = await self.cascade()
        image = Image.new("RGB", (1800, 2400), "#c17f3d")
        image.paste("white", (720, 1050, 1080, 1650))
        image.paste("black", (800, 1200, 950, 1400))
        run = Run(cascade, b"unused", Budget(perf_counter()), "match")
        run.photo = image
        # Reuse detections from the stretched detector; actual photo is 3x SIZE.
        from matcher import photo as photo_module
        copy = photo_module.sam3_copy(image, 320)
        items = self.fake.segment(NOUNS, copy.image.size)["instances"]
        package, label = run._select_input(copy, items)
        self.assertLessEqual(package["crop_box"][0], PACKAGE[0] * 3)
        self.assertGreaterEqual(package["crop_box"][2], PACKAGE[2] * 3)
        lx, ly, rx, ry = label["box"]
        self.assertLessEqual(lx, LABEL[0] * 3)
        self.assertGreaterEqual(rx, LABEL[2] * 3)
        self.assertTrue(np.array_equal(np.asarray(label["image"]), np.asarray(image.crop(label["box"]))))
        self.assertEqual(label["image"].getpixel((725 - lx, 1060 - ly)), (255, 255, 255))
        run.package = package
        self.assertEqual(run._recognition_photo().size, (package["crop_box"][2] - package["crop_box"][0],
                                                        package["crop_box"][3] - package["crop_box"][1]))

    async def test_vlm_fallback_picture_uses_selected_crop_without_a_label(self):
        cascade = await self.cascade(replace(self.config, rerank=None))
        run = Run(cascade, b"unused", Budget(perf_counter()), "match")
        run.photo = Image.new("RGB", (600, 800), "gray")
        run.photo.paste("red", (20, 30, 120, 230))
        run.package = {"crop_box": (20, 30, 120, 230), "image": run.photo.crop((20, 30, 120, 230))}
        run.config = replace(run.config, rerank=RerankConfig(side=256))
        with Image.open(BytesIO(run._picture())) as picture:
            self.assertEqual(picture.getpixel((0, 0)), (255, 0, 0))
            self.assertEqual(picture.width * 2, picture.height)

    async def test_selective_ocr_full_input_uses_selected_crop(self):
        cascade = await self.cascade(replace(self.config, selective_ocr=SelectiveOCRConfig()))
        cascade.ocr = SimpleNamespace(read=mock.AsyncMock(return_value=SimpleNamespace(
            text="", words=[], cached=False)))
        run = Run(cascade, b"unused", Budget(perf_counter()), "match")
        run.photo = Image.new("RGB", (600, 800), "gray")
        selected = Image.new("RGB", (100, 200), "red")
        run.package = {"crop_box": (20, 30, 120, 230), "image": selected}
        run.ocr_audit = {}
        await run._selective_ocr(None, perf_counter() + 2)
        with Image.open(BytesIO(cascade.ocr.read.call_args.args[0])) as image:
            self.assertEqual(image.getpixel((0, 0)), (255, 0, 0))
            self.assertEqual(image.width * 2, image.height)


if __name__ == "__main__":
    unittest.main()
