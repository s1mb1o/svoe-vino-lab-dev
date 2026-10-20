"""Recorded development regressions plus independent shape/transport controls.

Frozen scene expectations remain development targets. Pixel invariants do not
approve proposal ownership, label legibility or real-world accuracy.
"""

import ast
import base64
import hashlib
from io import BytesIO
import json
from pathlib import Path
import unittest
from unittest import mock

import numpy as np
from PIL import Image, ImageDraw

from matcher.group import GroupMatchError
from matcher.semantic_context import CONTEXT_NOUNS
from matcher.semantic_selector import select, select_photo
from test_semantic_selector import detection, png, rotate_inputs


def pixels(item):
    with Image.open(BytesIO(base64.b64decode(item["mask_png_b64"]))) as opened:
        return np.asarray(opened.convert("L")) >= 128


class ImageGenFixesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads(
            (
                Path(__file__).parent / "data/semantic-v2-imagegen-fixes-20261020.json"
            ).read_text()
        )["rows"]
        cls.outputs = {}
        for row in cls.rows:
            width, height = row["size"]
            y, x = np.indices((height, width))
            photo = Image.fromarray(
                np.stack(
                    ((x + y) % 251, (x + 3 * y) % 251, (2 * x + y) % 251), axis=-1
                ).astype("uint8")
            )
            cls.outputs[row["case_id"]] = (photo, select(photo, row["instances"]))

    def test_recorded_selection_targets_remain_frozen(self):
        for row in self.rows:
            with self.subTest(case=row["case_id"]):
                photo, result = self.outputs[row["case_id"]]
                if "full_context" in row["accepted_targets"]:
                    self.assertEqual(result.crop_box, (0, 0, *photo.size))
                    self.assertTrue((np.asarray(result.keep_mask) == 255).all())
                else:
                    self.assertIn(result.selected_id, row["accepted_targets"])
                self.assertTrue(result.crop)
                with Image.open(BytesIO(result.crop)) as crop:
                    visible = np.asarray(result.keep_mask.crop(result.crop_box)) == 255
                    np.testing.assert_array_equal(
                        np.asarray(crop)[visible],
                        np.asarray(photo.crop(result.crop_box))[visible],
                    )

    def test_every_returned_attached_label_mask_and_rgb_are_complete(self):
        for row in self.rows:
            with self.subTest(case=row["case_id"]):
                _, result = self.outputs[row["case_id"]]
                candidate = next(
                    c for c in result.candidates if c["id"] == result.selected_id
                )
                keep = np.zeros((row["size"][1], row["size"][0]), bool)
                x, y, X, Y = result.crop_box
                keep[y:Y, x:X] = np.asarray(result.keep_mask)[y:Y, x:X] == 255
                for ident in candidate["label_ids"]:
                    self.assertTrue(
                        keep[pixels(row["instances"][int(ident[1:])])].all(), ident
                    )

    def test_isolation_keeps_subject_and_removes_detected_neighbors(self):
        for row in self.rows:
            if row["case_id"].endswith(("CT09", "CT10")):
                continue
            with self.subTest(case=row["case_id"]):
                _, result = self.outputs[row["case_id"]]
                expected = pixels(row["instances"][int(result.selected_id[1:])])
                x, y, X, Y = result.crop_box
                keep = np.zeros(expected.shape, bool)
                keep[y:Y, x:X] = np.asarray(result.keep_mask)[y:Y, x:X] >= 128
                self.assertGreaterEqual((keep & expected).sum() / expected.sum(), 0.95)
                for item in row["instances"][: row["primary_count"]]:
                    if item["label"] not in ("wine bottle", "bottle"):
                        continue
                    other = pixels(item)
                    if (expected & other).sum() / max(
                        1, (expected | other).sum()
                    ) >= 0.5:
                        continue
                    self.assertLessEqual(
                        (keep & other).sum() / max(1, other.sum()), 0.1
                    )

    def test_pointing_and_window_carrier_survive_camera_roll(self):
        for ident in ("hardcases-v2--PT01", "diverse-v3--WP05"):
            row = next(r for r in self.rows if r["case_id"] == ident)
            photo, _ = self.outputs[ident]
            for rotation in (
                Image.Transpose.ROTATE_90,
                Image.Transpose.ROTATE_180,
                Image.Transpose.ROTATE_270,
            ):
                with self.subTest(case=ident, rotation=rotation):
                    image, items = rotate_inputs(photo, row["instances"], rotation)
                    self.assertIn(
                        select(image, items).selected_id, row["accepted_targets"]
                    )


class ContextControlsTest(unittest.TestCase):
    photo = Image.new("RGB", (240, 240), "#987654")

    def test_frozen_fallback_function_is_unchanged(self):
        import matcher.semantic_selector as selector

        tree = ast.parse(Path(selector.__file__).read_text())
        node = next(
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "_fallback"
        )
        self.assertEqual(
            hashlib.sha256(
                ast.dump(node, include_attributes=False).encode()
            ).hexdigest(),
            "a3af54508263fe7e9ca85249cee58b5ea97a71b28d0fae7ec1832853579d48f3",
        )

    def test_a_held_bottle_text_mask_alone_cannot_create_a_grip(self):
        first = detection("wine bottle", (10, 20, 80, 230))
        second = detection("wine bottle", (160, 20, 230, 230))
        result = select(
            self.photo, [first, second, dict(second, label="bottle held in hand")]
        )
        self.assertEqual(result.selection_mode, "fallback")
        self.assertFalse(
            any(c["signals"]["confirmed_hand_owner"] for c in result.candidates)
        )

    def test_frame_holes_exclude_depictions_but_protect_a_touching_foreground_bottle(
        self,
    ):
        first = detection("wine bottle", (10, 20, 75, 230))
        second = detection("wine bottle", (140, 55, 190, 205))
        frame = detection("screen", (105, 10, 240, 230), holes=[(130, 40, 205, 215)])
        result = select(self.photo, [first, second, frame])
        self.assertEqual(result.selected_id, "d0")
        self.assertTrue(
            any(
                r["id"] == "d1" and r["reason"] == "depiction_in_screen"
                for r in result.rejected
            )
        )
        hand = detection("hand", (160, 110, 205, 180))
        foreground = select(self.photo, [first, second, frame, hand], tap=(0.7, 0.6))
        self.assertEqual(foreground.selected_id, "d1")
        self.assertFalse(
            any(
                r["id"] == "d1" and r["reason"] == "depiction_in_screen"
                for r in foreground.rejected
            )
        )
        filled_frame = detection("screen", (105, 10, 240, 230))
        foreground = select(
            self.photo, [first, second, filled_frame, hand], tap=(0.7, 0.6)
        )
        self.assertEqual(foreground.selected_id, "d1")
        self.assertFalse(
            any(
                r["id"] == "d1" and r["reason"] == "depiction_in_screen"
                for r in foreground.rejected
            )
        )

    def test_remote_label_pixels_survive_without_expanding_the_paper_rectangle(self):
        bottle = detection("wine bottle", (70, 10, 170, 235))
        label = detection("wine label", (75, 100, 165, 200))
        mask = Image.fromarray(pixels(label).astype("uint8") * 255)
        ImageDraw.Draw(mask).rectangle((223, 219, 225, 221), fill=255)
        label = dict(label, mask_png_b64=base64.b64encode(png(mask)).decode())
        result = select(self.photo, [bottle, label])
        self.assertEqual(result.candidates[0]["label_boxes"], [[75, 100, 165, 200]])
        self.assertTrue((np.asarray(result.keep_mask)[pixels(label)] == 255).all())
        self.assertGreaterEqual(result.crop_box[2], 226)

    def test_optional_context_failure_keeps_a_crop_and_primary_instances(self):
        items = [
            detection("wine bottle", (10, 20, 80, 230)),
            detection("wine bottle", (160, 20, 230, 230)),
        ]
        with mock.patch(
            "matcher.semantic_selector._request_sam3",
            side_effect=[items, GroupMatchError(502, "unavailable")],
        ) as request:
            result = select_photo(png(self.photo), "http://sam3.test", timeout=10)
        self.assertTrue(result.crop)
        self.assertEqual(result.detection_context["status"], "unavailable")
        self.assertEqual(request.call_args_list[1].kwargs["nouns"], CONTEXT_NOUNS)
        self.assertLessEqual(request.call_args_list[1].args[4], 10)

    def test_optional_context_cannot_exceed_the_shared_deadline(self):
        items = [
            detection("wine bottle", (10, 20, 80, 230)),
            detection("wine bottle", (160, 20, 230, 230)),
        ]
        with (
            mock.patch(
                "matcher.semantic_selector._request_sam3", return_value=items
            ) as request,
            mock.patch("matcher.semantic_selector.monotonic", side_effect=[0, 11]),
        ):
            result = select_photo(png(self.photo), "http://sam3.test", timeout=10)
        self.assertEqual(request.call_count, 1)
        self.assertTrue(result.crop)
        self.assertEqual(result.detection_context["status"], "budget_exhausted")

    def test_supplied_instances_remain_an_offline_replay_contract(self):
        items = [
            detection("wine bottle", (10, 20, 80, 230)),
            detection("wine bottle", (160, 20, 230, 230)),
        ]
        with mock.patch("matcher.semantic_selector._request_sam3") as request:
            result = select_photo(png(self.photo), None, instances=items)
        request.assert_not_called()
        self.assertTrue(result.crop)

    def test_tiny_unlabelled_fragment_keeps_context_without_changing_its_owner(self):
        photo = Image.new("RGB", (1200, 800), "#987654")
        mask = Image.new("L", photo.size)
        ImageDraw.Draw(mask).rectangle((590, 390, 609, 413), fill=255)
        item = dict(
            label="wine bottle",
            score=0.9,
            box=[590, 390, 610, 414],
            mask_png_b64=base64.b64encode(png(mask)).decode(),
        )
        result = select(photo, [item])
        self.assertEqual(result.selected_id, "d0")
        self.assertEqual(result.crop_scope, "context_frame")
        self.assertEqual(result.crop_box, (0, 0, *photo.size))


if __name__ == "__main__":
    unittest.main()
