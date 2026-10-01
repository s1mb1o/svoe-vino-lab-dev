import argparse
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import normalize_glass  # noqa: E402


class NormalizeGlassTest(unittest.TestCase):
    def test_parse_colour(self):
        self.assertEqual(normalize_glass.parse_colour("#13271f"), (19, 39, 31))
        with self.assertRaises(argparse.ArgumentTypeError):
            normalize_glass.parse_colour("green")

    def test_placed_alpha_restores_the_derivative_coordinates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cut.png"
            cut = Image.new("RGBA", (3, 2), (10, 20, 30, 0))
            cut.putalpha(Image.fromarray(np.asarray([[0, 64, 255], [255, 64, 0]],
                                                    dtype=np.uint8), "L"))
            cut.save(path)
            mask = normalize_glass.placed_alpha(path, (2, 3, 5, 5), (8, 9))
        self.assertEqual(mask.getpixel((2, 3)), 0)
        self.assertEqual(mask.getpixel((4, 3)), 255)
        self.assertEqual(mask.getpixel((2, 4)), 255)
        self.assertEqual(mask.getpixel((0, 0)), 0)

    def test_only_glass_outside_the_label_is_normalized(self):
        source = Image.new("RGBA", (20, 24), (30, 60, 180, 255))
        pixels = source.load()
        # Red bottle, a white cap, and a white label on a blue background.
        for y in range(2, 23):
            for x in range(3, 17):
                pixels[x, y] = (185, 28, 22, 255)
        for y in range(2, 6):
            for x in range(7, 13):
                pixels[x, y] = (236, 234, 230, 255)
        for y in range(13, 19):
            for x in range(5, 15):
                pixels[x, y] = (244, 240, 228, 255)

        package = Image.new("L", source.size, 0)
        package.paste(255, (3, 2, 17, 23))
        label = Image.new("L", source.size, 0)
        label.paste(255, (5, 13, 15, 19))

        result, statistics = normalize_glass.normalize_image(
            source, package, label, target=(19, 39, 31), strength=1.0,
            label_margin=0.0)

        # Background and the segmented label are byte-identical.
        self.assertEqual(result.getpixel((1, 10)), source.getpixel((1, 10)))
        self.assertEqual(result.getpixel((10, 16)), source.getpixel((10, 16)))
        # Red glass becomes dark neutral-green while the bright cap is largely protected.
        red, green, blue, _ = result.getpixel((4, 10))
        self.assertLess(red, 70)
        self.assertGreater(green, red)
        self.assertLess(blue, 70)
        self.assertGreater(result.getpixel((10, 3))[0], 190)
        self.assertEqual(result.getchannel("A").tobytes(), source.getchannel("A").tobytes())
        self.assertGreater(statistics["normalized_pixels"], 100)
        self.assertGreater(statistics["protected_label_pixels"], 50)

    def test_comparison_writes_a_before_after_sheet(self):
        with tempfile.TemporaryDirectory() as directory:
            before = Path(directory) / "before.png"
            after = Path(directory) / "after.png"
            sheet = Path(directory) / "comparison.png"
            Image.new("RGBA", (20, 40), (180, 20, 20, 255)).save(before)
            Image.new("RGBA", (20, 40), (19, 39, 31, 255)).save(after)
            normalize_glass.comparison([("wine", before, after)], sheet, cell=(80, 100))
            with Image.open(sheet) as image:
                self.assertEqual(image.size, (160, 158))


if __name__ == "__main__":
    unittest.main()
