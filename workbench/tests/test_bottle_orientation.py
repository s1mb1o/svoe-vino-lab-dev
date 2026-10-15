"""Verify bottle geometry, direction, and the embedding input contract."""

from pathlib import Path
import sys
import unittest
from unittest import mock

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import bottle_orientation as orientation
import embeddings


def bottle(angle=0, size=(160, 400)):
    alpha = Image.new("L", size, 0)
    ImageDraw.Draw(alpha).polygon(
        [(62, 12), (98, 12), (98, 94), (125, 150), (125, 379),
         (118, 387), (42, 387), (35, 379), (35, 150), (62, 94)], fill=255)
    image = Image.new("RGBA", size, (24, 92, 45, 255))
    ImageDraw.Draw(image).rectangle((40, 200, 120, 300), fill=(237, 211, 170, 255))
    image.putalpha(alpha)
    if angle:
        image = image.rotate(angle, Image.Resampling.BICUBIC, expand=True)
    box = image.getchannel("A").getbbox()
    return image.crop(box)


class BottleOrientationTest(unittest.TestCase):
    def test_all_72_camera_rotations_become_portrait_with_neck_at_top(self):
        for angle in range(0, 360, 5):
            with self.subTest(angle=angle):
                source = bottle(angle)
                result, audit = orientation.normalize(source)
                self.assertTrue(audit["applied"])
                self.assertTrue(audit["direction_confident"])
                self.assertEqual(audit["neck"], "top")
                self.assertGreater(result.height, 3*result.width)
                error = (angle+audit["angle_degrees"]+180) % 360-180
                self.assertLess(abs(error), 1)
                values = np.asarray(result.getchannel("A")) >= 128
                self.assertLess(values[:100].sum(), values[-100:].sum())
                self.assertGreaterEqual(audit["mask_crop_iou_after"]+.012,
                                        audit["mask_crop_iou_before"])

    def test_diagonal_bottle_removes_most_white_crop_area(self):
        source = bottle(45)
        result, audit = orientation.normalize(source)
        self.assertLess(result.width*result.height, .45*source.width*source.height)
        self.assertGreater(audit["mask_crop_iou_after"], .72)
        self.assertLess(audit["mask_crop_iou_before"], .4)

    def test_upright_bottle_keeps_exact_pixels(self):
        source = bottle()
        result, audit = orientation.normalize(source)
        self.assertEqual(audit["angle_degrees"], 0)
        self.assertEqual(result.tobytes(), source.tobytes())

    def test_upside_down_bottle_uses_a_lossless_half_turn(self):
        result, audit = orientation.normalize(bottle(180))
        self.assertEqual(audit["angle_degrees"], -180)
        self.assertEqual(result.tobytes(), bottle().tobytes())

    def test_small_tilt_cannot_cancel_a_required_neck_up_half_turn(self):
        with mock.patch.object(orientation, "_angle", return_value=(179.0, 4)):
            result, audit = orientation.normalize(bottle(180))
        self.assertTrue(audit["applied"])
        self.assertEqual(audit["angle_degrees"], -180)
        self.assertEqual(result.tobytes(), bottle().tobytes())
        self.assertEqual(audit["crop_area_ratio"], 1)

    def test_rotation_preserves_mask_area_and_soft_edges(self):
        source = bottle(33)
        result, _audit = orientation.normalize(source)
        before = np.asarray(source.getchannel("A"), dtype=float).sum()
        after = np.asarray(result.getchannel("A"), dtype=float).sum()
        self.assertLess(abs(after-before)/before, .01)
        self.assertTrue(((np.asarray(result.getchannel("A")) > 0) &
                         (np.asarray(result.getchannel("A")) < 255)).any())

    def test_symmetric_body_without_neck_keeps_direction_unknown(self):
        source = Image.new("RGBA", (80, 300), (20, 90, 30, 255)).rotate(
            135, Image.Resampling.BICUBIC, expand=True)
        result, audit = orientation.normalize(source)
        self.assertGreater(result.height, 3*result.width)
        self.assertEqual(audit["neck"], "unknown")
        self.assertFalse(audit["direction_confident"])
        self.assertLessEqual(abs(audit["angle_degrees"]), 90)

    def test_broad_label_close_up_keeps_exact_pixels(self):
        source = Image.new("RGBA", (210, 190), (160, 140, 120, 255))
        result, audit = orientation.normalize(source)
        self.assertIs(result, source)
        self.assertFalse(audit["applied"])

    def test_absent_empty_and_tiny_masks_keep_input(self):
        for source in (Image.new("RGB", (20, 30), "red"),
                       Image.new("RGBA", (20, 30), (255, 0, 0, 0))):
            result, audit = orientation.normalize(source)
            self.assertIs(result, source)
            self.assertFalse(audit["applied"])
        source = Image.new("RGBA", (20, 30), (255, 0, 0, 0))
        source.putpixel((10, 10), (255, 0, 0, 255))
        self.assertIs(orientation.normalize(source)[0], source)

    def test_explicit_mask_preserves_input_and_removes_background(self):
        source = bottle(35)
        rgb = source.convert("RGB")
        pixels = rgb.tobytes()
        result, _audit = orientation.normalize(rgb, source.getchannel("A"))
        self.assertEqual(rgb.tobytes(), pixels)
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.getchannel("A").getextrema(), (0, 255))

    def test_mismatched_mask_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "sizes differ"):
            orientation.normalize(bottle(), Image.new("L", (10, 10)))

    def test_masked_view_embeds_rotated_canvas_before_resize(self):
        source = bottle(45)
        processed, _audit = orientation.normalize(source)
        steps = [{"step": "segment", "target": "package"},
                 {"step": "remove_background"}, {"step": "white_background"},
                 {"step": "resize", "max_size": 128, "aspect": "keep",
                  "upscale": False}]
        image, box = orientation.embedding_source(source, steps,
                                                  (0, 0, *source.size), processed)
        result = embeddings.apply_steps(image, steps, box, lambda: processed)
        self.assertEqual(result.mode, "RGB")
        self.assertGreater(result.height, 3*result.width)
        self.assertEqual(result.getpixel((0, 0)), (255, 255, 255))

    def test_rectangle_only_view_keeps_original_coordinates(self):
        source = bottle(45)
        processed, _audit = orientation.normalize(source)
        steps = [{"step": "segment", "target": "package"}]
        original_box = (0, 0, *source.size)
        image, box = orientation.embedding_source(source, steps, original_box, processed)
        self.assertIs(image, source)
        self.assertEqual(box, original_box)


if __name__ == "__main__":
    unittest.main()
