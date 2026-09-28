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
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tests"))
import alternatives  # noqa: E402
import lab_server as LAB  # noqa: E402
import labdb  # noqa: E402
import manual_wines  # noqa: E402
from test_patches import WINES, DownSam3, FakeSam3, NoLabelSam3  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def picture(fmt="PNG", transparent=True):
    """The bytes of a bottle box on a transparent or a white canvas."""
    image = Image.new("RGBA" if transparent else "RGB", (40, 80),
                      (255, 255, 255, 0) if transparent else (255, 255, 255))
    ImageDraw.Draw(image).rectangle((10, 10, 29, 69), fill=(90, 30, 20))
    out = io.BytesIO()
    image.save(out, fmt)
    return out.getvalue()


def form(data=None, **values):
    """The body of `POST /api/wine`: a valid wine unless `values` change it."""
    body = {"slug": "__my-wine", "name": "Моё вино", "producer": "Винодельня",
            "category": "Белое", "color": "Соломенный", "region": "Крым",
            "grapes": "Алиготе", "description": "Описание",
            "image_name": "IMG_1.png",
            "image": base64.b64encode(picture() if data is None else data).decode("ascii")}
    body.update(values)
    return body


class ManualSlugTest(unittest.TestCase):
    def test_is_manual_needs_the_prefix(self):
        self.assertTrue(manual_wines.is_manual("__a"))
        self.assertFalse(manual_wines.is_manual("a__b"))
        self.assertFalse(manual_wines.is_manual("_a"))

    def test_check_slug(self):
        self.assertEqual(manual_wines.check_slug(" __a-b_1 "), "__a-b_1")
        for slug in ("a", "_a", "__", "__-a", "__A", "__a b", "__ä", "__" + "a" * 199, 7,
                     None, "__null__", "__drawer__"):
            with self.subTest(slug=slug):
                with self.assertRaises(manual_wines.WineError) as error:
                    manual_wines.check_slug(slug)
                self.assertEqual(error.exception.code, 400)
        self.assertEqual(len(manual_wines.check_slug("__" + "a" * 198)), 200)

    def test_text_fields_refuse_a_lone_surrogate(self):
        for field in ("name", "image_name"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(manual_wines.WineError,
                                            "`%s` holds a character" % field):
                    manual_wines._text({field: "a\ud800"}, field)
        with self.assertRaisesRegex(manual_wines.WineError, "`image_name` MUST be text"):
            manual_wines._text({"image_name": ["x"]}, "image_name")
        self.assertIsNone(manual_wines._text({}, "grapes"))


class AddWineRouteTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.executemany("INSERT INTO wine_catalog (%s) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
                             % ", ".join(LAB.CATALOG_COLUMNS), WINES)
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

    def request(self, path, method="GET", body=None, headers=None):
        req = urllib.request.Request(self.base + path, method=method, data=body,
                                     headers=headers or {})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def add(self, body):
        status, out = self.request("/api/wine", "POST", json.dumps(body).encode("utf-8"),
                                   {"Content-Type": "application/json"})
        return status, json.loads(out)

    def query(self, sql, *args):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def wine_count(self):
        return self.query("SELECT count(*) FROM wine_catalog")[0][0]

    def test_add_stores_the_wine_its_main_image_and_the_crop(self):
        data = picture()
        status, out = self.add(form(data))
        self.assertEqual(status, 200, out)
        self.assertEqual((out["ok"], out["slug"]), (True, "__my-wine"))
        self.assertNotIn("warning", out)
        self.assertEqual(
            self.query("SELECT wine_slug, name, producer, category, color, region, grapes, "
                       "description, csv_photo_name, state, removed_by FROM wine_catalog "
                       "WHERE wine_slug = '__my-wine'"),
            [("__my-wine", "Моё вино", "Винодельня", "Белое", "Соломенный", "Крым",
              "Алиготе", "Описание", "IMG_1.png", "Active", None)])
        self.assertEqual(
            self.query("SELECT image_type, sha256, source_name, match_method FROM wine_image "
                       "WHERE wine_slug = '__my-wine'"),
            [("main", sha(data), "IMG_1.png", "manual")])
        self.assertEqual(self.query("SELECT folder, extension, width, height FROM image "
                                    "WHERE sha256 = ?", sha(data)),
                         [("main", "png", 40, 80)])
        url = "/images/main/%s.png" % sha(data)
        self.assertEqual((self.root / url.lstrip("/")).read_bytes(), data)
        record = out["record"]
        self.assertEqual((record["slug"], record["state"], record["main_image_type"],
                          record["main_image_original_url"], record["main_image_derivation"],
                          record["main_image_match_method"]),
                         ("__my-wine", "Active", "main", url, "crop", "manual"))
        self.assertTrue(record["main_image_url"].startswith("/images/cropped/"))
        # The new wine is the last record of the catalogue order.
        dataset = json.loads(self.request("/api/dataset")[1])
        self.assertEqual(dataset["records"][-1]["slug"], "__my-wine")
        self.assertIs(dataset["wine_editor"], True)

    def test_values_are_trimmed_and_empty_optional_fields_are_null(self):
        status, out = self.add(form(slug=" __trim ", name="  Имя ", grapes="  ",
                                    description=" "))
        self.assertEqual(status, 200, out)
        self.assertEqual(self.query("SELECT name, grapes, description FROM wine_catalog "
                                    "WHERE wine_slug = '__trim'"), [("Имя", None, None)])
        self.assertIsNone(out["record"]["description"])
        status, out = self.add(form(slug="__no-optional", grapes=None, description=None))
        self.assertEqual(status, 200, out)

    def test_bad_slugs_are_refused(self):
        for slug in ("my-wine", "__My-Wine", "__a b", "__" + "a" * 199, ""):
            with self.subTest(slug=slug):
                status, out = self.add(form(slug=slug))
                self.assertEqual(status, 400, out)
        self.assertEqual(self.wine_count(), 2)

    def test_slug_of_the_database_is_a_conflict(self):
        self.assertEqual(self.add(form())[0], 200)
        status, out = self.add(form(name="Другое"))
        self.assertEqual(status, 409, out)
        self.assertIn("__my-wine", out["error"])
        self.assertEqual(self.query("SELECT name FROM wine_catalog "
                                    "WHERE wine_slug = '__my-wine'"), [("Моё вино",)])

    def test_slug_of_a_removed_wine_is_a_conflict(self):
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("INSERT INTO wine_catalog (wine_slug, name, producer, category, "
                         "color, region, csv_photo_name, state, removed_by) VALUES "
                         "('__gone', 'n', 'p', 'Белое', 'c', 'r', 'x.jpg', 'Removed', "
                         "'person')")
        conn.close()
        status, out = self.add(form(slug="__gone"))
        self.assertEqual(status, 409, out)
        self.assertEqual(self.query("SELECT name, state FROM wine_catalog "
                                    "WHERE wine_slug = '__gone'"), [("n", "Removed")])

    def test_bad_fields_and_images_are_refused(self):
        cases = {
            "empty name": (form(name="  "), "`name` is empty"),
            "no producer": (form(producer=None), "`producer` is empty"),
            "field not text": (form(region=5), "`region` MUST be text"),
            "image name not text": (form(image_name=5), "`image_name` MUST be text"),
            "image name a list": (form(image_name=["x"]), "`image_name` MUST be text"),
            # `_json_body` of the lab server refuses a lone surrogate in any JSON body.
            "lone surrogate": (form(name="\ud800"), "lone surrogate"),
            "lone surrogate in the image name": (form(image_name="a\udfff.png"),
                                                 "lone surrogate"),
            "reserved slug": (form(slug="__null__"), "is reserved"),
            "no image": (form(image=""), "no main image"),
            "not base64": (form(image="%%%"), "not base64"),
            "not an image": (form(b"not an image"), "Pillow cannot read"),
            "gif": (form(picture("GIF")), "MUST be JPEG, PNG, or WebP"),
        }
        for name, (body, error) in cases.items():
            with self.subTest(name):
                status, out = self.add(body)
                self.assertEqual(status, 400, out)
                self.assertIn(error, out["error"])
        self.assertEqual(self.wine_count(), 2)
        self.assertEqual(self.query("SELECT count(*) FROM image"), [(0,)])

    def test_body_over_the_limit_is_refused(self):
        headers = {"Content-Type": "application/json",
                   "Content-Length": str(manual_wines.MAX_BODY + 1)}
        req = urllib.request.Request(self.base + "/api/wine", method="POST", data=b"{}",
                                     headers=headers)
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(req)
        self.assertEqual(error.exception.code, 413)
        self.assertEqual(self.wine_count(), 2)

    def test_add_with_no_sam3_is_stored_with_a_warning(self):
        self.server.segmenter = DownSam3()
        status, out = self.add(form(picture("JPEG", transparent=False), image_name="a.jpg"))
        self.assertEqual(status, 200, out)
        self.assertIn("no processed file", out["warning"])
        self.assertIn("connection refused", out["warning"])
        record = out["record"]
        self.assertEqual(record["main_image_derivation"], None)
        self.assertEqual(record["main_image_url"], record["main_image_original_url"])
        self.assertEqual(self.query("SELECT csv_photo_name FROM wine_catalog "
                                    "WHERE wine_slug = '__my-wine'"), [("a.jpg",)])
        self.assertIn(alternatives.NO_LABEL_CUT, out["warning"])

    # The main image also gets the label cut of `seed_label_cuts.py` (owner answer of
    # 2026-09-27T21:26:58+0300), for the view `label` of the Embeddings page.

    def test_add_makes_the_label_cut_of_the_main_image(self):
        data = picture()
        status, out = self.add(form(data))
        self.assertEqual(status, 200, out)
        self.assertNotIn("warning", out)
        self.assertEqual(self.query("SELECT method, settings FROM image_derivative WHERE "
                                    "source_sha256 = ? AND kind = 'label'", sha(data)),
                         [("seg", alternatives.SETTINGS_LABEL)])

    def test_add_with_no_label_is_stored_with_a_label_warning(self):
        self.server.segmenter = NoLabelSam3()
        data = picture()
        status, out = self.add(form(data))
        self.assertEqual(status, 200, out)
        self.assertIn(alternatives.NO_LABEL_CUT, out["warning"])
        self.assertEqual(self.query("SELECT kind FROM image_derivative WHERE "
                                    "source_sha256 = ?", sha(data)), [("package",)])

    def test_image_with_no_name_gets_the_default_name(self):
        status, out = self.add(form(image_name=None))
        self.assertEqual(status, 200, out)
        self.assertEqual(self.query("SELECT csv_photo_name FROM wine_catalog "
                                    "WHERE wine_slug = '__my-wine'"), [("upload",)])


if __name__ == "__main__":
    unittest.main()
