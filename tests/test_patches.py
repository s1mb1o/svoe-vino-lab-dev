import base64
import hashlib
import io
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import derive  # noqa: E402
import lab_server as LAB  # noqa: E402
import labdb  # noqa: E402
import patches  # noqa: E402

WINES = [
    ("wine-b", "Вино b", "Винодельня", "Белое", "Соломенный", "Крым",
     "Алиготе", "Описание b", "b.webp", "Active", None),
    ("wine-a", "Вино a", "Винодельня", "Красное", "Рубиновый", "Кубань",
     None, "Описание a", "a.webp", "Removed", "import"),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def picture(fmt="PNG", transparent=True, colour=(90, 30, 20)):
    """The bytes of a bottle box on a transparent or a white canvas."""
    image = Image.new("RGBA" if transparent else "RGB", (40, 80),
                      (255, 255, 255, 0) if transparent else (255, 255, 255))
    ImageDraw.Draw(image).rectangle((10, 10, 29, 69), fill=colour)
    out = io.BytesIO()
    image.save(out, fmt)
    return out.getvalue()


def label_instance():
    """Return one SAM3 label instance for the bottle box."""
    mask = Image.new("L", (40, 80), 0)
    ImageDraw.Draw(mask).rectangle((10, 25, 29, 54), fill=255)
    out = io.BytesIO()
    mask.save(out, "PNG")
    return {"label": "label", "box": [10, 25, 30, 55], "score": 0.9, "area": 600,
            "mask_png_b64": base64.b64encode(out.getvalue()).decode()}


class FakeSam3:
    """A SAM3 client with no network. It answers the mask of the bottle box."""

    def __init__(self):
        self.calls = 0
        self.instance_calls = 0

    def segment(self, image):
        self.calls += 1
        mask = Image.new("L", image.size, 0)
        ImageDraw.Draw(mask).rectangle((10, 10, 29, 69), fill=255)
        return mask

    def instances(self, image, texts, masks=True):
        self.instance_calls += 1
        return [label_instance()], 1.0


class NoPackageSam3(FakeSam3):
    """A SAM3 client that finds no package."""

    def segment(self, image):
        self.calls += 1
        return None


class NoLabelSam3(FakeSam3):
    """A SAM3 client that finds no label."""

    def instances(self, image, texts, masks=True):
        self.instance_calls += 1
        return [], 1.0


class PacketSam3(FakeSam3):
    """A SAM3 client that finds no label and classifies the package as a packet."""

    def instances(self, image, texts, masks=True):
        self.instance_calls += 1
        if texts == derive.SAM3_TEXTS:
            return [{"label": "packet", "box": [0, 0, 40, 80], "score": 0.9,
                     "area": 3200}], 1.0
        return [], 1.0


class DownSam3:
    """A SAM3 client whose service does not answer."""

    def segment(self, image):
        raise derive.Sam3Unavailable("connection refused")

    def instances(self, image, texts, masks=True):
        raise derive.Sam3Unavailable("connection refused")


class PatchRouteTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.executemany(
                "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, region, grapes, description, csv_photo_name, state, removed_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)", WINES)
        conn.close()
        self.sam3 = FakeSam3()
        self.server = LAB.make_server(self.db, port=0, segmenter=self.sam3)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def request(self, path, method="GET", body=None):
        req = urllib.request.Request(self.base + path, method=method, data=body)
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def upload(self, slug, data, name="patch.png"):
        query = urllib.parse.urlencode({"slug": slug, "name": name})
        status, body = self.request("/api/dataset-patch?" + query, "POST", data)
        return status, json.loads(body)

    def remove(self, slug):
        query = urllib.parse.urlencode({"slug": slug})
        status, body = self.request("/api/dataset-patch?" + query, "DELETE")
        return status, json.loads(body)

    def dataset(self):
        return json.loads(self.request("/api/dataset")[1])

    def patch_rows(self):
        conn = sqlite3.connect(self.db)
        try:
            return {row[0]: row[1:] for row in conn.execute(
                "SELECT wine_slug, sha256, source_name, match_method FROM wine_image "
                "WHERE image_type = 'main_patched'")}
        finally:
            conn.close()

    def derivative_rows(self, digest):
        conn = sqlite3.connect(self.db)
        try:
            return list(conn.execute(
                "SELECT kind, method FROM image_derivative WHERE source_sha256 = ? "
                "ORDER BY kind", (digest,)))
        finally:
            conn.close()

    def absence_rows(self, digest):
        conn = sqlite3.connect(self.db)
        try:
            return list(conn.execute(
                "SELECT kind, reason FROM image_derivative_absence "
                "WHERE source_sha256 = ?", (digest,)))
        finally:
            conn.close()

    def test_upload_stores_the_file_the_row_and_the_crop(self):
        data = picture()
        status, out = self.upload("wine-b", data, "Буковинка.png")
        self.assertEqual(status, 200, out)
        url = "/images/patched/%s.png" % sha(data)
        self.assertEqual((out["patched"], out["patches"], out["changed"]), (True, 1, True))
        record = out["record"]
        self.assertEqual((record["_patched"], record["_patch_url"], record["_patch_derivation"]),
                         (True, url, "crop"))
        self.assertTrue(record["_patch_image_url"].startswith("/images/cropped/"))
        # wine-b has no `main` image; the patch does not take its place on the card.
        self.assertEqual((record["main_image_type"], record["main_image_url"]), (None, None))
        self.assertNotIn("warning", out)
        self.assertEqual(self.sam3.calls, 0)
        self.assertEqual(self.sam3.instance_calls, 1)
        self.assertEqual(self.derivative_rows(sha(data)), [("label", "seg"),
                                                           ("package", "crop")])
        self.assertEqual((self.root / url.lstrip("/")).read_bytes(), data)
        self.assertEqual(self.patch_rows(),
                         {"wine-b": (sha(data), "Буковинка.png", "manual")})
        self.assertEqual(self.request(url)[1], data)
        view = self.dataset()
        self.assertEqual((view["patch_editor"], view["patches"]), (True, 1))
        self.assertNotIn("patch_dir", view)
        self.assertEqual([r["_patch_url"] for r in view["records"]], [url, None])

    def test_white_image_goes_to_sam3(self):
        status, out = self.upload("wine-b", picture("JPEG", transparent=False), "b.jpg")
        self.assertEqual(status, 200, out)
        self.assertEqual(self.sam3.calls, 1)
        self.assertEqual(self.sam3.instance_calls, 1)
        self.assertEqual(out["record"]["_patch_derivation"], "seg")
        self.assertTrue(out["record"]["_patch_url"].endswith(".jpg"))

    def test_upload_with_no_sam3_is_stored_with_a_warning(self):
        self.server.segmenter = DownSam3()
        status, out = self.upload("wine-b", picture("WEBP", transparent=False), "b.webp")
        self.assertEqual(status, 200, out)
        self.assertIn("no processed file", out["warning"])
        self.assertIn("no label cut", out["warning"])
        self.assertIn("connection refused", out["warning"])
        record = out["record"]
        self.assertEqual((out["patched"], record["_patch_derivation"]), (True, None))
        self.assertEqual(record["_patch_image_url"], record["_patch_url"])

    def test_a_crop_that_cut_nothing_gets_no_badge(self):
        # SAM3 finds no package, and the white rule finds no white border.
        self.server.segmenter = NoPackageSam3()
        out = io.BytesIO()
        Image.new("RGB", (40, 80), (90, 30, 20)).save(out, "PNG")
        status, out = self.upload("wine-b", out.getvalue())
        self.assertEqual(status, 200, out)
        record = out["record"]
        self.assertEqual((record["_patch_derivation"], record["_patch_image_url"]),
                         (None, record["_patch_url"]))

    def test_upload_with_no_label_is_stored_with_a_label_warning(self):
        self.server.segmenter = NoLabelSam3()
        data = picture()
        status, out = self.upload("wine-b", data)
        self.assertEqual(status, 200, out)
        self.assertIn("no label cut", out["warning"])
        self.assertIn("SAM3 found no label", out["warning"])
        self.assertEqual(self.derivative_rows(sha(data)), [("package", "crop")])
        retry = FakeSam3()
        self.server.segmenter = retry
        status, out = self.upload("wine-b", data)
        self.assertEqual((status, out["changed"]), (200, False))
        self.assertNotIn("warning", out)
        self.assertEqual(retry.instance_calls, 1)
        self.assertEqual(self.derivative_rows(sha(data)), [("label", "seg"),
                                                           ("package", "crop")])

    def test_a_packet_gets_no_duplicate_label_view_and_no_warning(self):
        self.server.segmenter = PacketSam3()
        data = picture()
        status, out = self.upload("wine-b", data)
        self.assertEqual(status, 200, out)
        self.assertNotIn("warning", out)
        self.assertEqual(self.derivative_rows(sha(data)), [("package", "crop")])
        self.assertEqual(self.absence_rows(sha(data)),
                         [("label", "the packet has no separate label")])

    def test_same_file_changes_nothing_and_a_new_file_replaces_the_row(self):
        first, second = picture(), picture(colour=(20, 30, 90))
        self.upload("wine-b", first)
        status, out = self.upload("wine-b", first, "again.png")
        self.assertEqual((status, out["changed"], out["patches"]), (200, False, 1))
        self.assertEqual(self.sam3.instance_calls, 1)
        self.assertEqual(self.patch_rows()["wine-b"][1], "patch.png")
        status, out = self.upload("wine-b", second)
        self.assertEqual((status, out["changed"], out["patches"]), (200, True, 1))
        self.assertEqual(self.patch_rows()["wine-b"][0], sha(second))
        self.assertTrue((self.root / "images" / "patched" / (sha(first) + ".png")).exists())

    def test_upload_reuses_a_stored_file(self):
        data = picture()
        folder = self.root / "images" / "main"
        folder.mkdir(parents=True)
        (folder / (sha(data) + ".png")).write_bytes(data)
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("INSERT INTO image VALUES (?, 'main', 'png', 40, 80)", (sha(data),))
        conn.close()
        status, out = self.upload("wine-b", data)
        self.assertEqual(status, 200, out)
        self.assertEqual(out["record"]["_patch_url"], "/images/main/%s.png" % sha(data))
        self.assertFalse((self.root / "images" / "patched").exists())

    def test_the_main_image_stays_on_the_card_under_a_patch(self):
        main = picture(colour=(20, 90, 30))
        folder = self.root / "images" / "main"
        folder.mkdir(parents=True)
        (folder / (sha(main) + ".png")).write_bytes(main)
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("INSERT INTO image VALUES (?, 'main', 'png', 40, 80)", (sha(main),))
            conn.execute("INSERT INTO wine_image VALUES ('wine-b', 'main', ?, 'b.png', "
                         "'name-unique')", (sha(main),))
        conn.close()
        main_url = "/images/main/%s.png" % sha(main)
        status, out = self.upload("wine-b", picture())
        self.assertEqual(status, 200, out)
        record = out["record"]
        self.assertEqual((record["main_image_type"], record["main_image_original_url"]),
                         ("main", main_url))
        self.assertNotEqual(record["_patch_url"], main_url)
        record = self.remove("wine-b")[1]["record"]
        self.assertEqual((record["main_image_original_url"], record["_patch_url"]),
                         (main_url, None))

    def test_a_removed_wine_gets_a_patch(self):
        status, out = self.upload("wine-a", picture())
        self.assertEqual((status, out["patched"]), (200, True))

    def test_remove_deletes_the_row_and_keeps_the_file(self):
        data = picture()
        self.upload("wine-b", data)
        status, out = self.remove("wine-b")
        self.assertEqual(status, 200, out)
        self.assertEqual((out["patched"], out["patches"], out["removed"]),
                         (False, 0, sha(data)))
        self.assertEqual((out["record"]["_patch_url"], out["record"]["main_image_type"]),
                         (None, None))
        self.assertEqual(self.patch_rows(), {})
        self.assertTrue((self.root / "images" / "patched" / (sha(data) + ".png")).exists())
        status, out = self.remove("wine-b")
        self.assertEqual(status, 404)
        self.assertIn("has no patch", out["error"])

    def test_bad_requests_are_refused(self):
        gif = io.BytesIO()
        Image.new("RGB", (4, 4)).save(gif, "GIF")
        cases = (("wine-b", b"", 400, "no image"),
                 ("wine-b", b"not an image", 400, "Pillow cannot read"),
                 ("wine-b", picture()[:60], 400, "Pillow cannot read"),
                 ("wine-b", gif.getvalue(), 400, "JPEG, PNG, or WebP"),
                 ("wine-x", picture(), 404, "no wine with the slug wine-x"),
                 ("", picture(), 400, "no wine slug"))
        for slug, data, code, text in cases:
            status, out = self.upload(slug, data)
            self.assertEqual(status, code, (slug, text))
            self.assertIn(text, out["error"])
        self.assertEqual(self.remove("wine-x")[0], 404)
        self.assertEqual(self.patch_rows(), {})
        self.assertFalse((self.root / "images" / "patched").exists())

    def test_read_image_refuses_too_many_pixels(self):
        saved = patches.MAX_PIXELS
        self.addCleanup(setattr, patches, "MAX_PIXELS", saved)
        patches.MAX_PIXELS = 100
        with self.assertRaises(patches.PatchError) as caught:
            patches.read_image(picture())
        self.assertEqual(caught.exception.code, 413)
        self.assertIn("40 × 80 pixels", str(caught.exception))

    def test_no_database_answers_503(self):
        self.server.db_path = str(self.root / "none.sqlite3")
        status, out = self.upload("wine-b", picture())
        self.assertEqual(status, 503)
        self.assertIn("no database", out["error"])

    def test_read_image_refuses_a_large_body(self):
        with self.assertRaises(patches.PatchError) as caught:
            patches.read_image(b"x" * (patches.MAX_BYTES + 1))
        self.assertEqual(caught.exception.code, 413)

    def test_source_name_is_the_base_name(self):
        self.assertEqual(patches.source_name("C:\\photos\\a.png"), "a.png")
        self.assertEqual(patches.source_name("../b.webp"), "b.webp")
        self.assertEqual(patches.source_name(None), "upload")
        self.assertEqual(patches.source_name("  "), "upload")


if __name__ == "__main__":
    unittest.main()
