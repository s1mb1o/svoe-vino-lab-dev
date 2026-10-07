"""Tests of the hybrid main-scene package selector of plan 69."""
import base64
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import derive  # noqa: E402
import main_scene  # noqa: E402


def mask_b64(size, box):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rectangle((box[0], box[1], box[2] - 1, box[3] - 1), fill=255)
    out = io.BytesIO()
    mask.save(out, "PNG")
    return base64.b64encode(out.getvalue()).decode("ascii")


def instance(label, size, box, score=0.9, area=None):
    return {"label": label, "box": list(box), "score": score,
            "area": area or (box[2] - box[0]) * (box[3] - box[1]),
            "mask_png_b64": mask_b64(size, box)}


def scene(size=(400, 600)):
    image = Image.new("RGB", size, (45, 48, 55))
    draw = ImageDraw.Draw(image)
    for x in range(0, size[0], 20):
        draw.line((x, 0, size[0] - x // 3, size[1]), fill=(70, 75, 82), width=2)
    return image


class FakeSegmenter:
    endpoint = "http://fake-sam3"

    def __init__(self, instances):
        self.answer = instances
        self.calls = []

    def instances(self, image, texts, masks=True):
        self.calls.append((texts, masks))
        return self.answer, 1.0


class MainSceneRankTest(unittest.TestCase):
    def test_a_weak_glass_detection_does_not_beat_a_strong_bottle_detection(self):
        size = (800, 479)
        bottle = instance("wine bottle", size, (90, 0, 261, 477), 0.952637)
        glass = instance("wine bottle", size, (423, 155, 581, 396), 0.370605)
        with mock.patch.object(main_scene, "_sharpness", side_effect=[18.9153, 19.9781]):
            selected, audit = main_scene.rank(scene(size), [bottle, glass], 1.0)
        self.assertIs(selected, bottle)
        self.assertEqual(audit["rejected"][0]["reason"], "detector_confidence_gap")
        self.assertAlmostEqual(audit["rejected"][0]["confidence_gap"], 0.582032)
        for version in (1, 2):
            with mock.patch.object(main_scene, "_sharpness", side_effect=[18.9153, 19.9781]):
                old, old_audit = main_scene.rank(scene(size), [bottle, glass], 1.0, version)
            self.assertIs(old, glass)
            self.assertEqual(old_audit["version"], version)
            self.assertNotIn("confidence_gap_limit", old_audit)

    def test_a_confidence_gap_does_not_create_package_class_priority(self):
        size = (400, 600)
        can = instance("can", size, (110, 70, 300, 570), 0.4)
        bottle = instance("wine bottle", size, (330, 500, 370, 585), 0.99)
        selected, audit = main_scene.rank(scene(size), [can, bottle], 1.0)
        self.assertIs(selected, can)
        self.assertEqual(audit["rejected"], [])

    def test_hand_scene_keeps_a_held_bottle_with_low_detector_confidence(self):
        size = (400, 600)
        held = instance("wine bottle", size, (110, 70, 300, 570), 0.4)
        shelf = instance("wine bottle", size, (330, 40, 370, 200), 0.99)
        hand = instance("hand", size, (40, 250, 390, 600), 0.97)
        selected, audit = main_scene.rank(scene(size), [held, shelf, hand], 1.0)
        self.assertIs(selected, held)
        self.assertEqual(audit["rejected"], [])

    def test_a_lone_low_confidence_package_remains_eligible(self):
        size = (200, 200)
        bottle = instance("wine bottle", size, (50, 0, 150, 200), 0.36)
        selected, audit = main_scene.rank(scene(size), [bottle], 1.0)
        self.assertIs(selected, bottle)
        self.assertEqual(audit["rejected"], [])

    def test_a_rejected_secondary_detection_keeps_other_scene_scores(self):
        size = (400, 600)
        candidates = [instance("wine bottle", size, (130, 35, 275, 585), 0.95),
                      instance("wine bottle", size, (10, 20, 65, 230), 0.93),
                      instance("wine bottle", size, (0, 0, 400, 600), 0.36)]
        image = scene(size)
        _selected, old = main_scene.rank(image, candidates, 1.0, version=2)
        _selected, new = main_scene.rank(image, candidates, 1.0)
        old_by_box = {tuple(c["box"]): c for c in old["candidates"]}
        self.assertEqual(len(new["rejected"]), 1)
        for candidate in new["candidates"]:
            previous = old_by_box[tuple(candidate["box"])]
            self.assertEqual(candidate["signals"], previous["signals"])
            self.assertEqual(candidate["scene_score"], previous["scene_score"])

    def test_a_sparse_mask_cannot_win_with_full_relative_area_credit(self):
        size = (200, 200)
        sparse = instance("wine bottle", size, (0, 0, 200, 200), 0.99, area=80)
        selected, audit = main_scene.rank(scene(size), [sparse], 1.0)
        self.assertIsNone(selected)
        self.assertEqual(audit["candidates"], [])
        self.assertEqual(audit["rejected"][0]["reason"], "mask_fill_below_minimum")
        self.assertAlmostEqual(audit["rejected"][0]["mask_fill"], 0.002)
        old, old_audit = main_scene.rank(scene(size), [sparse], 1.0, version=1)
        self.assertIs(old, sparse)
        self.assertEqual(old_audit["version"], 1)
        self.assertNotIn("rejected", old_audit)

    def test_a_valid_package_remains_after_a_sparse_mask_is_rejected(self):
        size = (200, 200)
        sparse = instance("wine bottle", size, (0, 0, 200, 200), 0.99, area=80)
        valid = instance("can", size, (60, 20, 140, 180), 0.8)
        selected, audit = main_scene.rank(scene(size), [sparse, valid], 1.0)
        self.assertIs(selected, valid)
        self.assertEqual(len(audit["rejected"]), 1)

    def test_an_empty_mask_is_rejected(self):
        size = (200, 200)
        empty = instance("wine bottle", size, (0, 0, 200, 200))
        empty["area"] = 0
        selected, audit = main_scene.rank(scene(size), [empty], 1.0)
        self.assertIsNone(selected)
        self.assertEqual(audit["rejected"][0]["mask_fill"], 0)

    def test_a_held_can_beats_many_shelf_bottles(self):
        size = (400, 600)
        candidates = [
            instance("wine bottle", size, (10 + i * 48, 20, 42 + i * 48, 210), 0.97)
            for i in range(8)
        ]
        candidates += [
            instance("can", size, (120, 85, 300, 590), 0.95),
            instance("hand", size, (60, 265, 350, 600), 0.96),
        ]
        selected, audit = main_scene.rank(scene(size), candidates, 1.0)
        self.assertEqual((selected["label"], audit["selected"]["label"]), ("can", "can"))
        self.assertEqual((audit["mode"], audit["hands"]), ("hand", 1))
        self.assertGreater(audit["candidates"][0]["scene_score"],
                           audit["candidates"][1]["scene_score"])
        self.assertEqual(set(audit["candidates"][0]["signals"]),
                         set(main_scene.HAND_WEIGHTS))

    def test_a_small_bottle_inside_the_hand_box_does_not_win(self):
        size = (400, 600)
        candidates = [
            instance("can", size, (110, 70, 300, 570), 0.91),
            instance("wine bottle", size, (330, 500, 370, 585), 0.99),
            instance("hand", size, (40, 250, 390, 600), 0.97),
        ]
        _selected, audit = main_scene.rank(scene(size), candidates, 1.0)
        self.assertEqual(audit["selected"]["label"], "can")
        bottle = next(item for item in audit["candidates"] if item["label"] == "wine bottle")
        self.assertLess(bottle["signals"]["hand_contact"], 0.1)

    def test_the_main_bottle_wins_among_many_bottles_without_a_hand(self):
        size = (400, 600)
        candidates = [
            instance("wine bottle", size, (130, 35, 275, 585), 0.91),
            instance("wine bottle", size, (10, 20, 65, 230), 0.98),
            instance("wine bottle", size, (75, 25, 125, 225), 0.97),
            instance("wine bottle", size, (290, 30, 345, 235), 0.99),
            instance("wine bottle", size, (345, 35, 395, 230), 0.96),
        ]
        selected, audit = main_scene.rank(scene(size), candidates, 1.0)
        self.assertEqual(selected["box"], [130, 35, 275, 585])
        self.assertEqual((audit["mode"], audit["hands"]), ("scene", 0))
        self.assertEqual(set(audit["weights"]), set(main_scene.SCENE_WEIGHTS))

    def test_an_exact_tie_uses_the_source_order(self):
        size = (200, 200)
        first = instance("can", size, (20, 50, 80, 150), 0.9)
        second = instance("can", size, (120, 50, 180, 150), 0.9)
        selected, audit = main_scene.rank(Image.new("RGB", size, "gray"),
                                          [first, second], 1.0)
        self.assertIs(selected, first)
        self.assertEqual([item["rank"] for item in audit["candidates"]], [1, 2])


class MainSceneCutTest(unittest.TestCase):
    def test_label_holes_are_restored_without_joining_external_background(self):
        size = (200, 200)
        image = scene(size)
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rectangle((20, 10, 179, 189), fill=255)
        draw.rectangle((65, 70, 135, 140), fill=0)  # Printed label removed by SAM3.
        draw.rectangle((20, 25, 45, 55), fill=0)  # Exterior gap stays transparent.
        buffer = io.BytesIO()
        mask.save(buffer, "PNG")
        item = instance("wine bottle", size, (20, 10, 180, 190), area=22000)
        item["mask_png_b64"] = base64.b64encode(buffer.getvalue()).decode("ascii")
        _method, _settings, new, box, audit = main_scene.cut(image, FakeSegmenter([item]))
        self.assertEqual(audit["mask_policy"], "restore_enclosed_holes")
        self.assertEqual(audit["mask_holes_restored_pixels"], 71 * 71)
        alpha = new.getchannel("A")
        self.assertEqual(alpha.getpixel((100-box[0], 100-box[1])), 255)
        self.assertEqual(alpha.getpixel((30-box[0], 40-box[1])), 0)
        for version in (1, 2, 3):
            _method, settings, old, old_box, old_audit = main_scene.cut(
                image, FakeSegmenter([item]), version=version)
            self.assertEqual(settings, main_scene.settings_for(version))
            self.assertEqual(old.getchannel("A").getpixel(
                (100-old_box[0], 100-old_box[1])), 0)
            self.assertNotIn("mask_holes_restored_pixels", old_audit)

    def test_diagonally_connected_background_is_not_a_hole(self):
        mask = Image.new("L", (20, 20), 255)
        draw = ImageDraw.Draw(mask)
        draw.rectangle((5, 5, 10, 10), fill=0)
        for i in range(5):
            mask.putpixel((i, i), 0)
        repaired, restored = main_scene._restore_mask_holes(mask)
        self.assertEqual(restored, 0)
        self.assertEqual(repaired.tobytes(), mask.tobytes())

    def test_mask_holes_do_not_change_box_or_packet_handle_cutouts(self):
        size = (200, 200)
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rectangle((20, 10, 179, 189), fill=255)
        draw.rectangle((65, 70, 135, 140), fill=0)
        buffer = io.BytesIO()
        mask.save(buffer, "PNG")
        for label in ("box", "packet"):
            item = instance(label, size, (20, 10, 180, 190), area=22000)
            item["mask_png_b64"] = base64.b64encode(buffer.getvalue()).decode("ascii")
            _method, _settings, processed, box, audit = main_scene.cut(
                scene(size), FakeSegmenter([item]))
            self.assertEqual(processed.getchannel("A").getpixel(
                (100-box[0], 100-box[1])), 0)
            self.assertNotIn("mask_holes_restored_pixels", audit)

    def test_sparse_detection_keeps_the_label_photo(self):
        image = scene((200, 200))
        sparse = instance("wine bottle", image.size, (0, 0, 200, 200), area=80)
        method, settings, processed, box, audit = main_scene.cut(
            image, FakeSegmenter([sparse]))
        self.assertEqual((method, settings, box, audit["selected"]),
                         ("crop", main_scene.SETTINGS_REJECTED, (0, 0, 200, 200), None))
        self.assertEqual(processed.tobytes(), image.tobytes())
        self.assertEqual(audit["fallback_reason"], "no_valid_package_mask")

    def test_a_full_frame_mask_that_removes_the_label_keeps_context(self):
        size = (200, 200)
        image = scene(size)
        # The glass surrounds a large label. SAM3 excludes the label from its mask.
        mask = Image.new("L", size, 255)
        ImageDraw.Draw(mask).rectangle((10, 10, 189, 189), fill=0)
        buffer = io.BytesIO()
        mask.save(buffer, "PNG")
        item = instance("wine bottle", size, (0, 0, 200, 200), area=7600)
        item["mask_png_b64"] = base64.b64encode(buffer.getvalue()).decode("ascii")
        method, settings, processed, box, audit = main_scene.cut(
            image, FakeSegmenter([item]))
        self.assertEqual((method, settings, box),
                         ("crop", main_scene.SETTINGS_CONTEXT, (0, 0, 200, 200)))
        self.assertEqual(processed.tobytes(), image.tobytes())
        self.assertEqual(audit["mask_policy"], "preserve_context")
        old_method, old_settings, old_image, _box, old_audit = main_scene.cut(
            image, FakeSegmenter([item]), version=1)
        self.assertEqual((old_method, old_settings, old_audit["version"]),
                         ("seg", main_scene.SETTINGS_V1, 1))
        self.assertLess(old_image.getchannel("A").getpixel((100, 100)), 10)

    def test_a_full_frame_dense_mask_still_segments(self):
        size = (200, 200)
        item = instance("wine bottle", size, (0, 0, 200, 200), area=35000)
        method, settings, _processed, _box, audit = main_scene.cut(
            scene(size), FakeSegmenter([item]))
        self.assertEqual((method, settings), ("seg", main_scene.SETTINGS))
        self.assertNotIn("fallback_reason", audit)

    def test_a_diagonal_bottle_with_background_still_segments(self):
        size = (200, 200)
        item = instance("wine bottle", size, (10, 10, 190, 190), area=6500)
        method, _settings, _processed, _box, audit = main_scene.cut(
            scene(size), FakeSegmenter([item]))
        self.assertEqual(method, "seg")
        self.assertNotIn("fallback_reason", audit)

    def test_the_selected_mask_makes_the_package_cut(self):
        size = (240, 360)
        can = instance("can", size, (70, 40, 180, 345), 0.95)
        hand = instance("hand", size, (20, 190, 220, 360), 0.94)
        segmenter = FakeSegmenter([can, hand])
        method, settings, processed, box, audit = main_scene.cut(scene(size), segmenter)
        self.assertEqual((method, settings, audit["selected"]["label"]),
                         ("seg", main_scene.SETTINGS, "can"))
        self.assertEqual(segmenter.calls, [(main_scene.TEXTS, True)])
        self.assertEqual(processed.mode, "RGBA")
        self.assertTrue(box[0] < 70 and box[1] < 40 and box[2] > 180 and box[3] >= 345)

    def test_no_package_uses_the_white_fallback(self):
        image = Image.new("RGB", (100, 120), "white")
        ImageDraw.Draw(image).rectangle((25, 20, 74, 109), fill="navy")
        method, settings, processed, box, audit = main_scene.cut(
            image, FakeSegmenter([instance("hand", image.size, (5, 60, 95, 120))]))
        self.assertEqual((method, settings, box, processed.size, audit["mode"]),
                         ("crop", derive.SETTINGS_WHITE, (25, 20, 75, 110), (50, 90), "white"))

    def test_a_transparent_photo_sends_no_sam3_request(self):
        image = Image.new("RGBA", (100, 120), (255, 255, 255, 0))
        ImageDraw.Draw(image).rectangle((25, 20, 74, 109), fill=(10, 20, 30, 255))
        segmenter = FakeSegmenter([])
        method, settings, processed, box, audit = main_scene.cut(image, segmenter)
        self.assertEqual((method, settings, box, processed.size, audit["mode"]),
                         ("crop", derive.SETTINGS_ALPHA, (25, 20, 75, 110), (50, 90), "alpha"))
        self.assertEqual(segmenter.calls, [])


if __name__ == "__main__":
    unittest.main()
