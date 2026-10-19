"""Detector geometry/recovery contracts; no GT is supplied during inference."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np
from PIL import Image

from matcher.group import GroupMatchError
from matcher.semantic_selector import (
    RECOVERY_NOUNS, _read, select, select_photo,
)
from matcher.experiments.main_selector.fallback_suite import verify_frozen_inputs
from test_semantic_selector import SIZE, detection, png


class DetectorRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.image = Image.new("RGB", SIZE, "#697b83")

    def test_small_box_disagreement_keeps_every_visible_mask_pixel(self):
        bottle = detection("wine bottle", (70, 10, 170, 235),
                           mask_box=(69, 11, 171, 234))
        original_box = list(bottle["box"])
        item = _read(self.image, [bottle])[0]
        self.assertEqual(item["box"], (69, 11, 171, 234))
        self.assertEqual(item["reported_box"], original_box)
        self.assertEqual(item["geometry_source"], "visible_mask")
        self.assertEqual(item["area"], 102 * 223)
        self.assertEqual(bottle["box"], original_box)
        result = select(self.image, [bottle])
        self.assertTrue(result.crop)
        self.assertEqual(result.candidates[0]["geometry_source"], "visible_mask")
        self.assertTrue(np.asarray(result.keep_mask)[11:234, 69:171].all())

    def test_occluded_mask_does_not_replace_an_amodal_box(self):
        bottle = detection("wine bottle", (80, 40, 160, 200),
                           mask_box=(80, 40, 105, 200))
        item = _read(self.image, [bottle])[0]
        self.assertEqual(item["box"], (80, 40, 160, 200))
        self.assertEqual(item["geometry_source"], "detector_box")

    def test_empty_semantic_detection_retries_generic_bottle_once(self):
        recovered = detection("bottle", (80, 10, 160, 220))
        with mock.patch("matcher.semantic_selector._request_sam3",
                        side_effect=[[], [recovered]]) as request:
            result = select_photo(png(self.image), "http://sam3.test", timeout=30)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args.kwargs["nouns"], RECOVERY_NOUNS)
        self.assertLessEqual(request.call_args.args[4], 30)
        self.assertEqual(result.status, "selected")
        self.assertEqual(result.detection_recovery, "generic_bottle_found")
        self.assertTrue(result.crop)

    def test_empty_recovery_still_returns_original_pixels(self):
        with mock.patch("matcher.semantic_selector._request_sam3", return_value=[]) as request:
            result = select_photo(png(self.image), "http://sam3.test")
        self.assertEqual(request.call_count, 2)
        self.assertEqual(result.detection_recovery, "generic_bottle_empty")
        self.assertEqual(result.crop_box, (0, 0, *SIZE))
        self.assertEqual(result.selection_mode, "fallback")
        self.assertEqual(result.status, "no_target")

    def test_optional_recovery_failure_preserves_valid_original_frame(self):
        with mock.patch("matcher.semantic_selector._request_sam3",
                        side_effect=[[], GroupMatchError(504, "timeout")]):
            result = select_photo(png(self.image), "http://sam3.test")
        self.assertEqual(result.detection_recovery, "unavailable")
        self.assertEqual(result.reason, "fallback_original_frame")
        self.assertTrue(result.crop)

    def test_recovery_respects_the_shared_timeout_budget(self):
        with (mock.patch("matcher.semantic_selector._request_sam3", return_value=[]) as request,
              mock.patch("matcher.semantic_selector.monotonic", side_effect=[0, 2])):
            result = select_photo(png(self.image), "http://sam3.test", timeout=1)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(result.detection_recovery, "budget_exhausted")
        self.assertTrue(result.crop)

    def test_supplied_empty_inputs_never_trigger_inference(self):
        with mock.patch("matcher.semantic_selector._request_sam3") as request:
            result = select_photo(png(self.image), None, instances=[])
        request.assert_not_called()
        self.assertIsNone(result.detection_recovery)
        self.assertEqual(result.status, "no_target")

    def test_legacy_variant_does_not_retry(self):
        with mock.patch("matcher.semantic_selector._request_sam3", return_value=[]) as request:
            result = select_photo(png(self.image), "http://sam3.test", variant="scene-v1")
        self.assertEqual(request.call_count, 1)
        self.assertIsNone(result.detection_recovery)

    def test_recovery_replay_requires_its_own_hash_without_changing_primary_freeze(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            (out / "predictions").mkdir()
            (out / "cases.json").write_text("[]")
            frozen = out / "comparison-inputs.json"
            frozen.write_text(json.dumps({"files_sha256": {}}))
            manifest = {"annotation_inputs_sha256": hashlib.sha256(frozen.read_bytes()).hexdigest(),
                        "files_sha256": {}}
            prediction = out / "prediction-inputs.json"
            prediction.write_text(json.dumps(manifest))
            recovery = out / "detector-recovery.json"
            recovery.write_text(json.dumps({"cases": {}}))
            with self.assertRaisesRegex(RuntimeError, "recovery inputs"):
                verify_frozen_inputs(out)
            manifest["recovery_inputs_sha256"] = hashlib.sha256(recovery.read_bytes()).hexdigest()
            prediction.write_text(json.dumps(manifest))
            verify_frozen_inputs(out)
            recovery.write_text(json.dumps({"cases": {"changed": {}}}))
            with self.assertRaisesRegex(RuntimeError, "recovery inputs"):
                verify_frozen_inputs(out)


if __name__ == "__main__":
    unittest.main()
