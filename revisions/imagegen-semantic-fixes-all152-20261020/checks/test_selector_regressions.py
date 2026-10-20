"""Frozen failure replays plus positive controls for the optional semantic selector.

These masks are development regressions, not independent accuracy evidence.
Original RGB/pixel retention is also checked by the full frozen-photo replay.
"""

import base64
from io import BytesIO
import json
from pathlib import Path
import unittest

import numpy as np
from PIL import Image

from matcher.semantic_selector import select
from test_semantic_selector import rotate_inputs


class SelectorRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((Path(__file__).parent /
                              "data/semantic-v2-regressions-20261019.json").read_text())["rows"]

    def rows_for(self, *ids):
        return [r for r in self.rows if r["case_id"] in ids]

    def photo(self, row):
        width, height = row["size"]
        y, x = np.indices((height, width))
        pixels = np.stack(((x * 3 + y) % 251, (x + y * 2) % 251,
                           (x * 2 + y * 3) % 251), axis=-1).astype("uint8")
        return Image.fromarray(pixels)

    def check_crop(self, photo, result):
        self.assertTrue(result.crop)
        self.assertIsNotNone(result.crop_box)
        with Image.open(BytesIO(result.crop)) as crop:
            x, y, X, Y = result.crop_box
            self.assertEqual(crop.size, (X - x, Y - y))
            expected = np.asarray(photo.crop(result.crop_box))
            kept = np.asarray(result.keep_mask.crop(result.crop_box)) > 0
            np.testing.assert_array_equal(np.asarray(crop)[kept], expected[kept])

    def check_labels(self, row, result, rotation=None):
        owner = row["detector_owners"].get(result.selected_id)
        if owner is None:
            return
        for encoded in row["labels_by_gt_owner"].get(str(owner), []):
            with Image.open(BytesIO(base64.b64decode(encoded))) as original:
                mask = original.transpose(rotation) if rotation else original.copy()
            label = np.asarray(mask) > 0
            kept = np.asarray(result.keep_mask) > 0
            self.assertTrue(np.all(kept[label]), "Selected subject label pixels were removed")
            x, y, X, Y = result.crop_box
            inside = np.zeros(label.shape, dtype=bool)
            inside[y:Y, x:X] = True
            self.assertTrue(np.all(inside[label]), "Selected subject label extends outside crop")

    def test_recorded_foreground_and_tool_failures_select_the_subject(self):
        for row in self.rows_for("hc-085", "hc-093", "hc-107", "hc-152", "real-312192"):
            with self.subTest(case=row["case_id"], mode=row["mode"]):
                photo = self.photo(row)
                result = select(photo, row["instances"])
                self.assertIn(result.selected_id, row["target_detection_ids"])
                self.check_crop(photo, result)
                self.check_labels(row, result)

    def test_foreground_regressions_survive_camera_roll(self):
        for row in self.rows_for("hc-085", "hc-093", "hc-152"):
            for rotation in (Image.Transpose.ROTATE_90, Image.Transpose.ROTATE_180,
                             Image.Transpose.ROTATE_270):
                with self.subTest(case=row["case_id"], mode=row["mode"], rotation=rotation):
                    photo, items = rotate_inputs(self.photo(row), row["instances"], rotation)
                    result = select(photo, items)
                    self.assertIn(result.selected_id, row["target_detection_ids"])
                    self.check_crop(photo, result)
                    self.check_labels(row, result, rotation)

    def test_neck_and_base_projection_do_not_certify_a_grip(self):
        for row in self.rows_for("hc-145", "hc-146"):
            for rotation in (None, Image.Transpose.ROTATE_90, Image.Transpose.ROTATE_180,
                             Image.Transpose.ROTATE_270):
                with self.subTest(case=row["case_id"], mode=row["mode"], rotation=rotation):
                    photo = self.photo(row)
                    photo, items = (rotate_inputs(photo, row["instances"], rotation)
                                    if rotation else (photo, row["instances"]))
                    result = select(photo, items)
                    self.assertEqual(result.selection_mode, "fallback")
                    self.assertNotEqual(result.reason, "unique_visible_hand_contact")
                    # The detector can break a GT tie differently. Require honest
                    # fallback and complete labels, not a fabricated GT winner.
                    self.check_crop(photo, result)
                    self.check_labels(row, result, rotation)

    def test_visible_mask_bounds_resolve_recorded_terminal_hand_box_jitter(self):
        for row in self.rows_for("hc-145", "hc-146"):
            with self.subTest(case=row["case_id"], mode=row["mode"]):
                photo = self.photo(row)
                result = select(photo, row["instances"])
                self.assertEqual(result.selection_mode, "fallback")
                self.assertIn(result.selected_id, row["target_detection_ids"])
                self.check_crop(photo, result)
                self.check_labels(row, result)

    def test_lying_bottle_on_a_separate_support_plane_uses_fallback(self):
        for row in self.rows_for("hc-143"):
            with self.subTest(mode=row["mode"]):
                photo = self.photo(row)
                result = select(photo, row["instances"])
                self.assertEqual(result.selection_mode, "fallback")
                self.assertIn(result.selected_id, row["target_detection_ids"])
                self.check_crop(photo, result)
                self.check_labels(row, result)

    def test_real_pouring_grip_and_lying_foreground_controls_still_work(self):
        for row in self.rows_for("hc-061", "hc-069", "hc-147", "real-541773"):
            with self.subTest(case=row["case_id"], mode=row["mode"]):
                photo = self.photo(row)
                result = select(photo, row["instances"])
                self.assertIn(result.selected_id, row["target_detection_ids"])
                self.check_crop(photo, result)
                self.check_labels(row, result)
                if row["case_id"] == "real-541773":
                    self.assertEqual(result.reason, "unique_visible_hand_contact")

    def test_a_misclassified_slender_tool_does_not_get_automatic_hand_priority(self):
        row = next(r for r in self.rows_for("hc-107") if r["mode"] == "controlled")
        photo = self.photo(row)
        result = select(photo, row["instances"])
        evidence = [e for c in result.candidates
                    for e in c["signals"]["grip_evidence"].values()
                    if e.get("slender_unlabelled_object")]
        self.assertTrue(evidence)
        self.assertTrue(all(not e["confirmed"] for e in evidence))
        self.assertIn(result.selected_id, row["target_detection_ids"])

    def test_an_explicit_tap_still_overrides_the_slender_object_heuristic(self):
        row = next(r for r in self.rows_for("hc-107") if r["mode"] == "controlled")
        tool = row["instances"][3]
        with Image.open(BytesIO(base64.b64decode(tool["mask_png_b64"]))) as mask:
            y, x = np.nonzero(np.asarray(mask))
        at = len(x) // 2
        tap = ((float(x[at]) + .5) / row["size"][0],
               (float(y[at]) + .5) / row["size"][1])
        result = select(self.photo(row), row["instances"], tap=tap)
        self.assertEqual((result.selected_id, result.reason), ("d3", "explicit_tap"))

    def test_a_missed_carafe_detection_keeps_the_entire_photo(self):
        row = self.rows_for("real-520871")[0]
        photo = self.photo(row)
        result = select(photo, row["instances"])
        self.assertEqual(result.status, "no_target")
        self.assertIsNone(result.selected_id)
        self.assertEqual(result.selection_mode, "fallback")
        self.assertEqual(result.crop_box, (0, 0, *photo.size))
        self.check_crop(photo, result)
        with Image.open(BytesIO(result.crop)) as crop:
            np.testing.assert_array_equal(crop, photo)


if __name__ == "__main__":
    unittest.main()
