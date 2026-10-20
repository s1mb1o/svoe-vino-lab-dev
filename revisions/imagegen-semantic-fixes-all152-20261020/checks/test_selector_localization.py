"""Image-only localization/recovery regressions under frozen selection policy."""

import base64
from io import BytesIO
import json
from pathlib import Path
import unittest
from unittest import mock

import numpy as np
from PIL import Image, ImageDraw

from matcher.group import GroupMatchError
from matcher.semantic_selector import (
    _read,
    _upright_bottle_geometry,
    select,
    select_photo,
)
from matcher.selector_detection import enhance, request_optional, small_scene
import test_selector_regressions as recorded
from test_semantic_selector import SIZE, detection, png


class SelectorLocalizationTest(unittest.TestCase):
    photo = recorded.SelectorRegressionTest.photo
    check_crop = recorded.SelectorRegressionTest.check_crop
    check_labels = recorded.SelectorRegressionTest.check_labels

    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads(
            (
                Path(__file__).parent
                / "data/semantic-v2-localization-regressions-20261020.json"
            ).read_text()
        )["rows"]

    def test_five_recorded_neck_asymmetries_choose_frozen_targets(self):
        for row in self.rows[:5]:
            with self.subTest(case=row["case_id"]):
                photo = self.photo(row)
                result = select(photo, row["instances"])
                self.assertIn(result.selected_id, row["target_detection_ids"])
                self.assertEqual(result.selection_mode, "fallback")
                self.assertTrue(
                    any(c["geometry_source"] == "neck_axis" for c in result.candidates)
                )
                self.check_crop(photo, result)
                self.check_labels(row, result)

    def test_recorded_central_and_tracker_recovery_run_through_byte_adapter(self):
        for row in self.rows[5:7]:
            with self.subTest(case=row["case_id"]):
                photo = self.photo(row)
                with (
                    mock.patch(
                        "matcher.semantic_selector._request_sam3",
                        return_value=row["primary"],
                    ),
                    mock.patch(
                        "matcher.selector_detection.request_optional",
                        side_effect=row["responses"],
                    ) as request,
                ):
                    result = select_photo(png(photo), "http://sam3.test")
                self.assertEqual(request.call_count, len(row["responses"]))
                self.assertIn(result.selected_id, row["target_detection_ids"])
                self.assertEqual(result.selection_mode, "fallback")
                self.assertIsNotNone(result.detection_refinement)
                self.check_crop(photo, result)

    def test_unannotated_bar_bottles_are_not_suppressed_to_force_a_gt_pass(self):
        row = self.rows[-1]
        result = select(self.photo(row), row["instances"])
        self.assertEqual(result.selection_mode, "fallback")
        self.assertNotIn(result.selected_id, row["target_detection_ids"])
        self.assertTrue(result.crop)

    def test_axis_fit_expands_only_and_translates_with_the_object(self):
        image = Image.new("RGB", (320, 400), "gray")
        mask = Image.new("L", image.size)
        draw = ImageDraw.Draw(mask)
        draw.rectangle((145, 40, 164, 100), fill=255)
        draw.rectangle((127, 100, 180, 310), fill=255)
        item = dict(
            label="bottle",
            score=0.9,
            box=mask.getbbox(),
            mask_png_b64=base64.b64encode(png(mask)).decode(),
        )
        self.assertEqual(
            _upright_bottle_geometry(image, item)["box"], (127, 40, 183, 311)
        )
        shifted = Image.new("L", image.size)
        shifted.paste(mask, (13, 0))
        moved = dict(
            item,
            box=shifted.getbbox(),
            mask_png_b64=base64.b64encode(png(shifted)).decode(),
        )
        self.assertEqual(
            _upright_bottle_geometry(image, moved)["box"], (140, 40, 196, 311)
        )
        self.assertEqual(item["box"], mask.getbbox())

    def test_rectangular_and_substantially_occluded_boxes_keep_their_geometry(self):
        image = Image.new("RGB", SIZE)
        for item in [
            detection("bottle", (80, 10, 130, 220)),
            detection("bottle", (80, 10, 130, 220), mask_box=(80, 10, 100, 220)),
        ]:
            self.assertEqual(_upright_bottle_geometry(image, item)["box"], item["box"])

    def test_optional_unavailable_or_exhausted_recovery_keeps_a_crop(self):
        row = self.rows[5]
        photo = self.photo(row)
        decision = select(photo, row["primary"])
        for deadline in (-1, float("inf")):
            request = mock.Mock(side_effect=GroupMatchError(502, "offline"))
            effective, audit = enhance(
                photo, row["primary"], decision, request, deadline=deadline
            )
            self.assertEqual(effective, row["primary"])
            self.assertTrue(select(photo, effective).crop)
            self.assertIsNotNone(audit)
            if deadline == -1:
                request.assert_not_called()

    def test_supplied_instances_do_not_start_optional_model_requests(self):
        row = self.rows[5]
        with mock.patch("matcher.selector_detection.request_optional") as request:
            result = select_photo(png(self.photo(row)), None, instances=row["primary"])
        request.assert_not_called()
        self.assertTrue(result.crop)

    def test_large_bottle_scenes_do_not_start_recovery(self):
        row = self.rows[0]
        photo = self.photo(row)
        decision = select(photo, row["instances"])
        self.assertFalse(small_scene(photo, decision))
        request = mock.Mock()
        self.assertEqual(
            enhance(photo, row["instances"], decision, request, deadline=float("inf")),
            (row["instances"], None),
        )
        request.assert_not_called()

    def test_refined_crop_keeps_the_entire_original_rectangle(self):
        row = self.rows[6]
        photo = self.photo(row)
        result = select(photo, row["instances"])
        item = row["instances"][int(result.selected_id[1:])]
        self.assertIn("preserve_box", item)
        left, top, right, bottom = item["preserve_box"]
        self.assertTrue(np.asarray(result.keep_mask)[top:bottom, left:right].all())
        self.check_crop(photo, result)

    def test_optional_transport_uses_png_points_and_validates_dimensions(self):
        image = Image.new("RGB", (160, 160))
        response = dict(width=160, height=160, count=0, instances=[])
        opener = mock.Mock()
        opener.open.return_value = BytesIO(json.dumps(response).encode())
        self.assertEqual(
            request_optional(
                image,
                "http://sam3.test",
                5,
                points=[[10, 10], [11, 11], [12, 12]],
                opener=opener,
            ),
            [],
        )
        request = opener.open.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/segment_point"))
        self.assertIn(b"Content-Type: image/png", request.data)
        self.assertIn(b'name="points"', request.data)
        response["width"] = 159
        opener.open.return_value = BytesIO(json.dumps(response).encode())
        with self.assertRaises(GroupMatchError):
            request_optional(image, "http://sam3.test", 5, opener=opener)

    def test_optional_transport_bounds_response_size(self):
        opener = mock.Mock()
        opener.open.return_value = BytesIO(b"x" * 9)
        with (
            mock.patch("matcher.selector_detection.MAX_SAM3_RESPONSE_BYTES", 8),
            self.assertRaises(GroupMatchError),
        ):
            request_optional(
                Image.new("RGB", (160, 160)), "http://sam3.test", 5, opener=opener
            )

    def test_tracker_keeps_original_reported_box_and_exposes_its_geometry_source(self):
        row = self.rows[6]
        read = {d["id"]: d for d in _read(self.photo(row), row["instances"])}
        target = next(d for d in row["target_detection_ids"] if d in read)
        self.assertEqual(read[target]["geometry_source"], "local_tracker")
        self.assertEqual(
            read[target]["reported_box"], row["primary"][int(target[1:])]["box"]
        )
