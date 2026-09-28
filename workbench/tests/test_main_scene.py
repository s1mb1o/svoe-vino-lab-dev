"""Tests of the hybrid main-scene package selector of plan 69."""
import base64
import io
import sys
import unittest
from pathlib import Path

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
