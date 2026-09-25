import base64
import hashlib
import io
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import derive  # noqa: E402
import labdb  # noqa: E402


def bottle_on_transparent(size=(60, 100), box=(20, 10, 40, 90), line=True):
    """An RGBA image: an opaque bottle box on a transparent canvas, and a thin line of
    2 pixels at the left edge."""
    image = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((box[0], box[1], box[2] - 1, box[3] - 1), fill=(90, 30, 20, 255))
    if line:
        draw.rectangle((0, 0, 1, size[1] - 1), fill=(0, 0, 0, 255))
    return image


def bottle_on_white(size=(60, 100), box=(20, 10, 40, 90)):
    image = Image.new("RGB", size, (255, 255, 255))
    ImageDraw.Draw(image).rectangle((box[0], box[1], box[2] - 1, box[3] - 1),
                                    fill=(90, 30, 20))
    return image


def box_mask(size, box):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rectangle((box[0], box[1], box[2] - 1, box[3] - 1), fill=255)
    return mask


class FakeSegmenter:
    """Answers the mask of a box, None, or a failure. Counts the calls."""

    def __init__(self, box=None, fail=False):
        self.box = box
        self.fail = fail
        self.calls = 0

    def segment(self, image):
        self.calls += 1
        if self.fail:
            raise derive.Sam3Unavailable("the fake service is down")
        return box_mask(image.size, self.box) if self.box else None


class DeriveImageTest(unittest.TestCase):
    def test_transparent_image_gets_crop_and_no_sam3_request(self):
        segmenter = FakeSegmenter(fail=True)
        method, settings, out, box = derive.derive_image(bottle_on_transparent(), segmenter)
        self.assertEqual((method, settings, box), ("crop", derive.SETTINGS_ALPHA,
                                                   (20, 10, 40, 90)))
        self.assertEqual((out.mode, out.size), ("RGBA", (20, 80)))
        self.assertEqual(segmenter.calls, 0)

    def test_thin_line_alone_keeps_its_plain_box(self):
        image = Image.new("RGBA", (30, 30), (0, 0, 0, 0))
        ImageDraw.Draw(image).line((5, 3, 5, 25), fill=(0, 0, 0, 255))
        box = derive.derive_image(image, FakeSegmenter())[3]
        self.assertEqual(box, (5, 3, 6, 26))

    def test_empty_transparent_image_keeps_the_whole_canvas(self):
        image = Image.new("RGBA", (30, 40), (0, 0, 0, 0))
        image.putpixel((0, 0), (0, 0, 0, 10))
        self.assertEqual(derive.derive_image(image, FakeSegmenter())[3], (0, 0, 30, 40))

    def test_image_with_no_transparency_gets_seg(self):
        segmenter = FakeSegmenter(box=(20, 10, 40, 90))
        method, settings, out, box = derive.derive_image(bottle_on_white(), segmenter)
        self.assertEqual((method, settings, segmenter.calls), ("seg", derive.SETTINGS_SEG, 1))
        self.assertEqual(out.mode, "RGBA")
        # The mask grows a little, so the box holds the bottle and a small rim.
        self.assertTrue(box[0] < 20 and box[1] < 10 and box[2] > 40 and box[3] > 90)
        self.assertTrue(box[0] >= 15 and box[1] >= 5 and box[2] <= 45 and box[3] <= 95)
        alpha = out.getchannel("A")
        self.assertEqual(alpha.getpixel((30 - box[0], 50 - box[1])), 255)
        self.assertEqual(alpha.getpixel((0, 0)), 0)

    def test_sam3_with_no_package_falls_back_to_the_white_rule(self):
        method, settings, out, box = derive.derive_image(bottle_on_white(), FakeSegmenter())
        self.assertEqual((method, settings, box), ("crop", derive.SETTINGS_WHITE,
                                                   (20, 10, 40, 90)))
        self.assertEqual(out.mode, "RGB")

    def test_sam3_failure_is_raised(self):
        with self.assertRaises(derive.Sam3Unavailable):
            derive.derive_image(bottle_on_white(), FakeSegmenter(fail=True))

    def test_refined_mask_is_smooth_and_grown(self):
        alpha = derive.refine_mask(box_mask((200, 400), (50, 50, 150, 350)))
        self.assertEqual(alpha.getpixel((100, 200)), 255)
        self.assertGreater(alpha.getpixel((49, 200)), 0)
        self.assertEqual(alpha.getpixel((10, 200)), 0)


# The tests of this file send no answer to the cache of the project in `data/cache/`.
_CACHE = {}


def setUpModule():
    _CACHE["directory"] = tempfile.TemporaryDirectory()
    _CACHE["root"], derive.model_cache.ROOT = (derive.model_cache.ROOT,
                                               _CACHE["directory"].name)


def tearDownModule():
    derive.model_cache.ROOT = _CACHE["root"]
    _CACHE["directory"].cleanup()


class Sam3ClientTest(unittest.TestCase):
    def mask_b64(self, size, box):
        out = io.BytesIO()
        box_mask(size, box).save(out, "PNG")
        return base64.b64encode(out.getvalue()).decode()

    def test_client_takes_the_largest_instance_and_scales_the_mask(self):
        client = derive.Sam3Client("http://sam3.invalid")
        sent = []

        def post(data):
            sent.append(Image.open(io.BytesIO(data)).size)
            small = sent[0]
            return {"instances": [
                {"label": "can", "score": 0.9, "area": 10,
                 "mask_png_b64": self.mask_b64(small, (0, 0, 2, 5))},
                {"label": "wine bottle", "score": 0.5, "area": 900,
                 "mask_png_b64": self.mask_b64(small, (100, 100, 400, 1400))}]}

        client._post = post
        mask = client.segment(bottle_on_white(size=(1000, 3072)))
        self.assertEqual(sent, [(500, 1536)])
        self.assertEqual(mask.size, (1000, 3072))
        self.assertEqual(mask.getbbox(), (200, 200, 800, 2800))

    def test_client_answers_none_for_no_instance(self):
        client = derive.Sam3Client("http://sam3.invalid")
        client._post = lambda data: {"instances": []}
        self.assertIsNone(client.segment(bottle_on_white()))

    def test_client_raises_after_the_retries(self):
        import requests
        client = derive.Sam3Client("http://sam3.invalid")
        calls = []

        def fail(*args, **kwargs):
            calls.append(1)
            raise requests.ConnectionError("refused")

        client.session.post = fail
        old = (derive.SAM3_RETRIES, derive.time.sleep)
        derive.SAM3_RETRIES, derive.time.sleep = 2, lambda seconds: None
        try:
            with self.assertRaisesRegex(derive.Sam3Unavailable, "refused"):
                client.segment(bottle_on_white())
        finally:
            derive.SAM3_RETRIES, derive.time.sleep = old
        self.assertEqual(len(calls), 3)

    def test_with_the_reads_off_a_repeated_post_asks_sam3_again(self):
        # The checkbox `Use caches` of the dialog `Run>`, off (plan 39): the fresh answer
        # is stored, so the next call with the reads on gets the newest answer.
        client = derive.Sam3Client("http://sam3-live.invalid")
        calls = []

        class Response:
            status_code = 200

            def json(self):
                return {"instances": [{"label": "can", "area": len(calls)}]}

        def post(url, files=None, data=None, timeout=None):
            calls.append(files["image"][1])
            return Response()

        client.session.post = post
        self.addCleanup(setattr, derive.model_cache, "READ", True)
        client._post(b"png-live", "bottle")
        derive.model_cache.READ = False
        second = client._post(b"png-live", "bottle")
        self.assertEqual(len(calls), 2)
        derive.model_cache.READ = True
        self.assertEqual(client._post(b"png-live", "bottle"), second)
        self.assertEqual(len(calls), 2)

    def test_repeated_post_reads_the_cache_and_a_failure_is_not_stored(self):
        import requests
        client = derive.Sam3Client("http://sam3-cache.invalid")
        calls = []

        class Response:
            status_code = 200

            def json(self):
                return {"instances": [{"label": "can", "area": len(calls)}]}

        def post(url, files=None, data=None, timeout=None):
            calls.append((files["image"][1], data["texts"], data["return_masks"]))
            return Response()

        client.session.post = post
        first = client._post(b"png-1", "bottle")
        self.assertEqual(client._post(b"png-1", "bottle"), first)
        self.assertEqual(len(calls), 1)
        client._post(b"png-1", "can")
        client._post(b"png-2", "bottle")
        client._post(b"png-1", "bottle", False)
        self.assertEqual(len(calls), 4)

        def fail(*args, **kwargs):
            raise requests.ConnectionError("refused")

        client.session.post = fail
        old = derive.SAM3_RETRIES
        derive.SAM3_RETRIES = 0
        try:
            with self.assertRaises(derive.Sam3Unavailable):
                client._post(b"png-3", "bottle")
        finally:
            derive.SAM3_RETRIES = old
        client.session.post = post
        client._post(b"png-3", "bottle")
        self.assertEqual(calls[-1], (b"png-3", "bottle", "true"))
        self.assertEqual(len(calls), 5)


class DeriveAllTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")
        self.conn = labdb.connect(self.db, create=True)
        self.conn.isolation_level = None
        self.main = self.root / "images" / "main"
        self.main.mkdir(parents=True)
        self.messages = []

    def tearDown(self):
        self.conn.close()
        self.directory.cleanup()

    def original(self, image):
        out = io.BytesIO()
        image.save(out, "PNG")
        data = out.getvalue()
        digest = hashlib.sha256(data).hexdigest()
        path = self.main / (digest + ".png")
        path.write_bytes(data)
        self.conn.execute("INSERT INTO image VALUES (?, 'main', 'png', ?, ?)",
                          (digest,) + image.size)
        return digest, str(path)

    def run_all(self, originals, segmenter):
        out = derive.derive_all(self.conn, self.db, dict(originals), segmenter,
                                self.messages.append)
        self.conn.execute("BEGIN")
        derive.write_rows(self.conn, out)
        self.conn.execute("COMMIT")
        return out

    def links(self):
        return self.conn.execute("SELECT source_sha256, method, sha256, box_left, box_top, "
                                 "box_right, box_bottom FROM image_derivative").fetchall()

    def test_processed_file_and_rows_are_stored_once(self):
        digest, path = self.original(bottle_on_transparent())
        out = self.run_all([(digest, path)], FakeSegmenter(fail=True))
        self.assertEqual((dict(out.methods), out.written), ({"crop": 1}, 1))
        [(source, method, derived, *box)] = self.links()
        self.assertEqual((source, method, box), (digest, "crop", [20, 10, 40, 90]))
        self.assertEqual(self.conn.execute(
            "SELECT folder, extension, width, height FROM image WHERE sha256 = ?",
            (derived,)).fetchone(), ("cropped", "png", 20, 80))
        stored = self.root / "images" / "cropped" / (derived + ".png")
        self.assertEqual(hashlib.sha256(stored.read_bytes()).hexdigest(), derived)
        again = self.run_all([(digest, path)], FakeSegmenter(fail=True))
        self.assertEqual((again.processed(), again.present, again.written), (0, 1, 0))

    def test_after_the_first_sam3_failure_the_run_asks_no_more(self):
        first = self.original(bottle_on_white())
        second = self.original(bottle_on_white(box=(10, 10, 30, 60)))
        segmenter = FakeSegmenter(fail=True)
        out = self.run_all([first, second], segmenter)
        self.assertEqual((segmenter.calls, out.unavailable, out.processed()), (1, 2, 0))
        self.assertEqual(self.links(), [])
        self.assertEqual(len(self.messages), 2)
        retry = self.run_all([first, second], FakeSegmenter(box=(20, 10, 40, 90)))
        self.assertEqual(dict(retry.methods), {"seg": 2})

    def test_file_that_is_no_image_is_counted_and_skipped(self):
        path = self.main / ("0" * 64 + ".webp")
        path.write_bytes(b"not an image")
        out = self.run_all([("0" * 64, str(path))], FakeSegmenter())
        self.assertEqual((out.unreadable, out.errors, out.processed()), (1, 0, 0))

    def test_row_with_old_settings_is_processed_again(self):
        digest, path = self.original(bottle_on_transparent())
        self.run_all([(digest, path)], FakeSegmenter())
        self.conn.execute("UPDATE image_derivative SET settings = 'old'")
        out = self.run_all([(digest, path)], FakeSegmenter())
        self.assertEqual(out.processed(), 1)
        self.assertEqual(self.conn.execute("SELECT settings FROM image_derivative")
                         .fetchall(), [(derive.SETTINGS_ALPHA,)])



class Sam3InstancesTest(unittest.TestCase):
    def test_instances_sends_the_texts_and_answers_each_instance_and_the_scale(self):
        client = derive.Sam3Client("http://sam3.invalid")
        sent = []
        answer = {"instances": [{"label": "bottle neck", "box": [1, 2, 3, 4], "score": 0.8,
                                 "area": 4},
                                {"label": "label", "box": [5, 6, 7, 8], "score": 0.7,
                                 "area": 4}]}

        def post(data, texts, masks):
            sent.append((Image.open(io.BytesIO(data)).size, texts, masks))
            return answer

        client._post = post
        found, scale = client.instances(bottle_on_white(size=(1000, 3072)), "bottle, label",
                                        masks=False)
        self.assertEqual(sent, [((500, 1536), "bottle, label", False)])
        self.assertEqual(found, answer["instances"])
        self.assertEqual(scale, 0.5)

    def test_post_sends_the_texts_and_the_mask_switch(self):
        client = derive.Sam3Client("http://sam3.invalid")
        forms = []

        class Response:
            status_code = 200

            def json(self):
                return {"instances": []}

        def post(url, files=None, data=None, timeout=None):
            forms.append(data)
            return Response()

        client.session.post = post
        client._post(b"png", "bottle neck", False)
        client._post(b"png")
        self.assertEqual([(f["texts"], f["return_masks"]) for f in forms],
                         [("bottle neck", "false"), (derive.SAM3_TEXTS, "true")])

if __name__ == "__main__":
    unittest.main()
