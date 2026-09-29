"""Tests of the image steps of the backend `cascade`: the label rule, the refined mask
box of the lab, the request images, and the unchanged SigLIP2 input."""

from io import BytesIO
import unittest

from PIL import Image

from matcher import labels, photo
from matcher.siglip2 import model_input, model_png

from cascade_fakes import instance, mask_png_b64


SIZE = (300, 400)
PACKAGE = (100, 50, 200, 350)


def rgb(size=SIZE, boxes=()):
    image = Image.new("RGB", size, (128, 128, 128))
    for box, colour in boxes:
        image.paste(colour, box)
    return image


def full_image_box(item, image, copy):
    """The lab rule on the whole photo: resize the mask, keep >= 128, refine, bbox."""
    with Image.open(BytesIO(__import__("base64").b64decode(item["mask_png_b64"]))) as opened:
        mask = opened.convert("L")
    mask = mask.resize(image.size, Image.Resampling.BILINEAR)
    mask = mask.point(lambda value: 255 if value >= 128 else 0)
    alpha = photo.refine_mask(mask)
    return alpha.point(lambda value: 255 if value > 0 else 0).getbbox()


class LabelRuleTest(unittest.TestCase):
    def test_the_largest_label_on_the_package_wins(self):
        instances = [instance("wine bottle", PACKAGE, SIZE),
                     instance("label", (120, 150, 180, 250), SIZE),
                     instance("label", (220, 150, 290, 260), SIZE),   # beside the package
                     instance("label", (135, 60, 165, 85), SIZE)]     # a small neck label
        choice = labels.choose(instances, PACKAGE, *SIZE)
        self.assertEqual(choice.main["box"], [120, 150, 180, 250])
        self.assertEqual(choice.others, ())

    def test_a_label_that_is_the_package_does_not_count(self):
        instances = [instance("label", (101, 51, 199, 349), SIZE),
                     instance("label", (120, 150, 180, 250), SIZE)]
        self.assertEqual(labels.choose(instances, PACKAGE, *SIZE).main["box"],
                         [120, 150, 180, 250])
        only = [instance("label", (101, 51, 199, 349), SIZE)]
        self.assertEqual(labels.choose(only, PACKAGE, *SIZE).main["box"], [101, 51, 199, 349])

    def test_a_second_body_label_gives_the_box_of_both(self):
        instances = [instance("label", (110, 140, 190, 230), SIZE),
                     instance("label", (115, 240, 185, 300), SIZE)]
        choice = labels.choose(instances, PACKAGE, *SIZE)
        self.assertEqual(len(choice.others), 1)
        image = rgb()
        copy = photo.sam3_copy(image)
        cut, box = labels.cut(choice, copy, image)
        self.assertEqual(box, (110, 140, 190, 300))
        self.assertEqual(cut.size, (80, 160))

    def test_duplicates_keep_the_larger_label(self):
        instances = [instance("label", (120, 150, 180, 250), SIZE, 0.7),
                     instance("label", (121, 151, 180, 250), SIZE, 0.95)]
        self.assertEqual(labels.choose(instances, PACKAGE, *SIZE).main["box"],
                         [120, 150, 180, 250])

    def test_a_close_up_takes_the_largest_label_with_no_package_test(self):
        instances = [instance("label", (0, 0, 300, 400), SIZE),
                     instance("label", (50, 50, 100, 100), SIZE)]
        self.assertEqual(labels.choose(instances, None, *SIZE).main["box"], [0, 0, 300, 400])

    def test_no_label_on_the_package_gives_none(self):
        instances = [instance("label", (220, 150, 290, 260), SIZE)]
        self.assertIsNone(labels.choose(instances, PACKAGE, *SIZE))
        self.assertIsNone(labels.choose([instance("hand", PACKAGE, SIZE)], PACKAGE, *SIZE))

    def test_one_label_gets_its_masked_cut_on_white(self):
        image = rgb(boxes=[((100, 50, 200, 350), (200, 0, 0)), ((120, 150, 180, 250), (0, 0, 200))])
        copy = photo.sam3_copy(image)
        choice = labels.choose([instance("label", (120, 150, 180, 250), SIZE)], PACKAGE, *SIZE)
        cut, box = labels.cut(choice, copy, image)
        self.assertLessEqual(box[0], 120)
        self.assertGreaterEqual(box[2], 180)
        self.assertEqual(cut.getpixel((cut.width // 2, cut.height // 2)), (0, 0, 200))
        # The corner of the soft mask edge is almost white.
        self.assertTrue(all(value >= 230 for value in cut.getpixel((0, 0))))


class ImageStepTest(unittest.TestCase):
    def test_the_region_box_equals_the_lab_rule_on_the_whole_photo(self):
        for size, box in (((300, 400), (100, 50, 200, 350)),
                          ((2400, 3200), (800, 400, 1600, 2800)),
                          ((3024, 4032), (5, 7, 3019, 4029))):
            with self.subTest(size=size):
                image = rgb(size)
                copy = photo.sam3_copy(image)
                scale = copy.image.width / size[0]
                copy_box = tuple(round(value * scale) for value in box)
                item = instance("wine bottle", copy_box, copy.image.size)
                expected = full_image_box(item, image, copy)
                got = photo.refined_box(item, copy, image)
                for a, b in zip(got, expected):
                    self.assertLessEqual(abs(a - b), 1)

    def test_an_empty_mask_gives_no_box(self):
        image = rgb()
        copy = photo.sam3_copy(image)
        item = {"box": [10, 10, 20, 20], "mask_png_b64": mask_png_b64(SIZE, (0, 0, 0, 0))}
        self.assertIsNone(photo.refined_box(item, copy, image))

    def test_the_sam3_copy_limits_the_long_side_to_1600(self):
        copy = photo.sam3_copy(rgb((2000, 3000)))
        self.assertEqual(copy.image.size, (1067, 1600))
        self.assertAlmostEqual(copy.scale_y, 3000 / 1600)
        with Image.open(BytesIO(copy.jpeg)) as opened:
            self.assertEqual((opened.format, opened.size), ("JPEG", (1067, 1600)))
        small = photo.sam3_copy(rgb((300, 400)))
        self.assertEqual((small.image.size, small.scale_x), ((300, 400), 1.0))

    def test_scan_images_scale_down_and_up_to_1600(self):
        for size, expected in (((3024, 4032), (1200, 1600)), ((300, 400), (1200, 1600)),
                               ((1600, 900), (1600, 900))):
            with self.subTest(size=size):
                with Image.open(BytesIO(photo.scaled_png(rgb(size)))) as opened:
                    self.assertEqual(opened.size, expected)

    def test_the_vlm_picture_has_the_long_side_1536(self):
        with Image.open(BytesIO(photo.side_png(rgb((200, 100)), 1536))) as opened:
            self.assertEqual(opened.size, (1536, 768))

    def test_a_crop_with_a_margin_stays_inside_the_photo(self):
        image = rgb()
        self.assertEqual(photo.crop(image, (100, 50, 200, 350), 0.1).size, (120, 360))
        self.assertEqual(photo.crop(image, (0, 0, 300, 400), 0.1).size, (300, 400))

    def test_the_siglip2_input_does_not_change(self):
        for size, mode in (((3024, 4032), "RGB"), ((500, 300), "RGBA"), ((800, 600), "RGB")):
            with self.subTest(size=size, mode=mode):
                image = Image.new(mode, size, (10, 20, 30, 128) if mode == "RGBA" else (10, 20, 30))
                output = BytesIO()
                image.save(output, "PNG")
                body = output.getvalue()
                self.assertEqual(model_png(photo.decode(body)), model_input(body))
                with Image.open(BytesIO(model_png(photo.decode(body), 1))) as fast, \
                        Image.open(BytesIO(model_input(body))) as slow:
                    self.assertEqual(fast.tobytes(), slow.tobytes())


if __name__ == "__main__":
    unittest.main()
