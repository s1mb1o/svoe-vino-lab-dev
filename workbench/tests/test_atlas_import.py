""""New from Atlas" of plan 95: `atlas_import.py`, `atlas_import_routes.py`, and
`lab_server.start_atlas_wine`, against a fake Atlas web UI."""
import io
import json
import re
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tests"))
import atlas_import as A  # noqa: E402
import lab_server as LAB  # noqa: E402
import labdb  # noqa: E402
from test_patches import WINES, FakeSam3  # noqa: E402

UUID = "a3b3d69b-71e5-4f38-9a76-411c6203c873"


def bottle(colour, size=(60, 100), margin=0, fmt="PNG"):
    """The bytes of a coloured bottle box on a white canvas with `margin` white pixels."""
    width, height = size
    image = Image.new("RGB", (width + 2 * margin, height + 2 * margin), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((margin, margin, margin + width - 1, margin + height - 1),
                   fill=(230, 220, 200))
    draw.rectangle((margin + width // 4, margin + 10, margin + 3 * width // 4,
                    margin + height - 10), fill=colour)
    out = io.BytesIO()
    image.save(out, fmt)
    return out.getvalue()


RED, BLUE = bottle((150, 20, 20)), bottle((20, 40, 160))


def _scaled(data, size):
    out = io.BytesIO()
    Image.open(io.BytesIO(data)).resize(size, Image.LANCZOS).save(out, "PNG")
    return out.getvalue()


BIG_BLUE = _scaled(BLUE, (120, 200))


def pattern(size=320, seed=0):
    """A smooth picture with no white field."""
    y, x = np.mgrid[0:size, 0:size] / size
    rng = np.random.default_rng(seed)
    a, b = rng.uniform(2, 6, 2)
    red = 120 + 100 * np.sin(a * np.pi * x) * np.cos(b * np.pi * y)
    green = 120 + 100 * np.cos(b * np.pi * x + y)
    blue = 120 + 80 * np.sin((a + b) * np.pi * (x + y))
    return Image.fromarray(np.dstack([red, green, blue]).clip(0, 230).astype(np.uint8))


def png(image):
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


class FakeAtlas:
    """The state of the fake Atlas web UI: the product, the tasks, and the files."""

    def __init__(self):
        self.stage_one_done = False
        self.tasks = {}          # media id -> list of tasks
        self.requests = []       # (profile, media id, headers)
        self.next_id = 100
        self.files = {1: RED, 2: RED, 3: BLUE, 11: RED, 5: BIG_BLUE}

    def product(self):
        assets = [
            {"media_id": 1, "kind": "image", "content_type": "image/png",
             "width_px": 60, "height_px": 100, "content_length": 900, "pdf_sources": []},
            {"media_id": 2, "kind": "image", "content_type": "image/png",
             "width_px": 60, "height_px": 100, "content_length": 800, "pdf_sources": []},
            {"media_id": 2, "kind": "image", "content_type": "image/png",
             "width_px": 60, "height_px": 100, "content_length": 800, "pdf_sources": []},
            {"media_id": 3, "kind": "image", "content_type": "image/png",
             "width_px": 60, "height_px": 100, "content_length": 700, "pdf_sources": []},
            {"media_id": 4, "kind": "document", "content_type": "application/pdf",
             "width_px": None, "height_px": None, "pdf_sources": []},
        ]
        if self.stage_one_done:
            assets[0]["crop"] = {"x": 0, "y": 0, "width": 60, "height": 100,
                                 "derived_media_id": 11}
            assets.append({"media_id": 5, "kind": "image", "content_type": "image/png",
                           "width_px": 120, "height_px": 200, "content_length": 600,
                           "pdf_sources": [{"source_media_id": 4}]})
        return {"uuid": UUID, "display_name": "ЛЕКИФ «Кубань» — розовое полусухое вино",
                "brand": "ЛЕКИФ", "beverage_type_code": "404",
                "producers": [{"name": "Фанагория"}],
                "wine_profile": {"wine_color_code": "rose"},
                "grapes_and_harvest": ["каберне совиньон 2025"], "assets": assets}

    def finish(self, status="succeeded", profile=None):
        for items in self.tasks.values():
            for task in items:
                if profile is None or task["profile"] == profile:
                    task["status"] = status


def atlas_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            parts = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(parts.query)
            if parts.path == "/api/v1/products/" + UUID:
                return self.send(200, state.product())
            if parts.path == "/api/enrichment/tasks":
                media = int(query["media_id"][0])
                return self.send(200, {"items": state.tasks.get(media, [])})
            match = re.match(r"^/api/v1/assets/(\d+)/(thumbnail|content|crop)$", parts.path)
            if match and int(match.group(1)) in state.files:
                return self.send(200, state.files[int(match.group(1))], "image/png")
            return self.send(404, {"error": "not found"})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if (self.path != "/api/enrichment/requests"
                    or self.headers.get("X-Atlas-Action") != "enrichment"
                    or self.headers.get("Origin") != "http://" + self.headers["Host"]):
                return self.send(403, {"error": "refused"})
            media = body["params"]["media_id"]
            state.next_id += 1
            task = {"id": state.next_id, "profile": body["profile"], "status": "queued",
                    "queue_position": 3, "media_id": None}
            state.tasks.setdefault(media, []).append(task)
            state.requests.append((body["profile"], media))
            return self.send(202, {"items": [{"product_uuid": UUID,
                                              "task_id": task["id"], "status": "queued",
                                              "reused": False}]})
    return Handler


class ParseTest(unittest.TestCase):
    def test_parse_url(self):
        origin, product, hidden = A.parse_url(
            " http://127.0.0.1:8157/products/%s?include_hidden=true " % UUID.upper())
        self.assertEqual((origin, product, hidden), ("http://127.0.0.1:8157", UUID, True))
        self.assertEqual(A.parse_url("http://localhost:8157/products/%s/" % UUID)[2], False)
        for url in (None, "", "ftp://127.0.0.1/products/%s" % UUID,
                    "http://192.168.86.12:8157/products/%s" % UUID,
                    "http://127.0.0.1:8157/assets/%s" % UUID,
                    "http://127.0.0.1:8157/products/not-a-uuid-not-a-uuid-not-a-uuid-xx"):
            with self.subTest(url=url):
                with self.assertRaises(A.AtlasError) as caught:
                    A.parse_url(url)
                self.assertEqual(caught.exception.code, 400)

    def test_prefill(self):
        values = A.prefill(FakeAtlas().product())
        self.assertEqual(values["name"], "ЛЕКИФ «Кубань» — розовое полусухое вино")
        self.assertEqual(values["producer"], "Фанагория")
        self.assertEqual(values["category"], "Розовое")
        self.assertEqual(values["beverage_type_code"], "4")
        self.assertEqual(values["grapes"], "каберне совиньон 2025")
        self.assertEqual((values["color"], values["region"]), ("", ""))
        self.assertEqual([A.beverage_type(code) for code in ("404", "440", "451", "500", None)],
                         ["4", "44", "44", "", ""])

    def test_steps(self):
        state = FakeAtlas()
        self.assertEqual(A.stage_one(state.product()),
                         [(A.CLEAN, 1), (A.CLEAN, 2), (A.CLEAN, 3), (A.PDF, 4)])
        state.stage_one_done = True
        self.assertEqual([media for _profile, media in A.stage_two(state.product())],
                         [1, 11, 2, 3, 5])


class SimilarTest(unittest.TestCase):
    def test_outer_white_bounds(self):
        rgb = np.full((50, 40, 3), 255, dtype=np.uint8)
        rgb[5:45, 10:30] = 40
        self.assertEqual(A.outer_white_bounds(rgb), (10, 5, 20, 40))
        self.assertEqual(A.outer_white_bounds(np.full((4, 4, 3), 255, np.uint8)),
                         (0, 0, 4, 4))

    def test_white_margin_and_duplicates_group(self):
        plain = A.fingerprint(RED, True)
        framed = A.fingerprint(bottle((150, 20, 20), margin=30), True)
        other = A.fingerprint(BLUE, True)
        self.assertLess(A.distance(plain, framed), 0.02)
        self.assertTrue(A.similar(plain, framed))
        self.assertFalse(A.similar(plain, other))

    def test_crop_of_an_original_matches_a_pdf_image(self):
        image = pattern()
        original = A.fingerprint(png(image), True)
        crop = A.fingerprint(png(image.crop((20, 30, 300, 290))), False)
        self.assertGreater(A.distance(original, crop), A.DISTANCE)
        self.assertTrue(A.similar(original, crop))
        # Two originals do not use the crop match.
        self.assertFalse(A.similar(original, dict(crop, original=True)))
        self.assertFalse(A.similar(original, A.fingerprint(png(pattern(seed=5)), False)))

    def test_group_order_and_quality(self):
        assets = [{"media_id": 7, "width_px": 60, "height_px": 100, "content_length": 5},
                  {"media_id": 3, "width_px": 60, "height_px": 100, "content_length": 5},
                  {"media_id": 9, "width_px": 10, "height_px": 10},
                  {"media_id": 4, "width_px": 60, "height_px": 100, "content_length": 1,
                   "crop": {"width": 80, "height": 100}}]
        same = A.fingerprint(RED, True)
        groups = A.group(assets, {7: same, 3: same, 4: same})
        self.assertEqual([[item["media_id"] for item in items] for items in groups],
                         [[4, 3, 7], [9]])

    def test_turn(self):
        data = png(Image.new("RGB", (4, 2), (255, 0, 0)))
        turned = Image.open(io.BytesIO(A._turn(data, 90, "mirror_horizontal")))
        self.assertEqual(turned.size, (2, 4))
        with self.assertRaises(A.AtlasError):
            A._turn(data, 45, None)

    def test_stored_form(self):
        gif = io.BytesIO()
        Image.new("RGB", (3, 3)).save(gif, "GIF")
        data, extension = A._stored_form(gif.getvalue())
        self.assertEqual((Image.open(io.BytesIO(data)).format, extension), ("PNG", "png"))
        self.assertEqual(A._stored_form(RED), (RED, "png"))


class AtlasRouteTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = str(Path(self.directory.name) / "lab.sqlite3")
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.executemany("INSERT INTO wine_catalog (%s) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
                             % ", ".join(LAB.CATALOG_COLUMNS), WINES)
        conn.close()
        self.atlas = FakeAtlas()
        self.atlas_server = ThreadingHTTPServer(("127.0.0.1", 0), atlas_handler(self.atlas))
        threading.Thread(target=self.atlas_server.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d/products/%s" % (self.atlas_server.server_address[1],
                                                        UUID)
        self.server = LAB.make_server(self.db, port=0, segmenter=FakeSam3())
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        for server in (self.server, self.atlas_server):
            server.shutdown()
            server.server_close()
        self.directory.cleanup()

    def request(self, path, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base + path, data=data,
                                     method="POST" if body is not None else "GET",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def advance(self):
        status, out = self.request("/api/atlas-import/advance", {"url": self.url})
        self.assertEqual(status, 200, out)
        return out

    def form(self, media_ids, **values):
        body = {"url": self.url, "media_ids": media_ids, "slug": "__lekif-kuban",
                "name": "ЛЕКИФ «Кубань»", "producer": "Фанагория",
                "beverage_type_code": "4", "category": "Розовое", "color": "Розовое",
                "region": "Кубань", "grapes": "", "description": ""}
        body.update(values)
        return body

    def query(self, sql, *args):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def test_advance_runs_the_stages_once(self):
        out = self.advance()
        self.assertEqual(out["stage"], "clean")
        self.assertEqual(out["prefill"]["category"], "Розовое")
        self.assertEqual(self.atlas.requests,
                         [(A.CLEAN, 1), (A.CLEAN, 2), (A.CLEAN, 3), (A.PDF, 4)])
        self.assertTrue(all(step["submitted"] for step in out["steps"]))
        out = self.advance()
        self.assertEqual(len(self.atlas.requests), 4)
        self.assertFalse(any(step["submitted"] for step in out["steps"]))
        self.assertEqual(out["steps"][0]["status"], "queued")

        self.atlas.finish()
        self.atlas.stage_one_done = True
        out = self.advance()
        self.assertEqual(out["stage"], "barcode")
        self.assertEqual(self.atlas.requests[4:],
                         [(A.BARCODE, 1), (A.BARCODE, 11), (A.BARCODE, 2), (A.BARCODE, 3),
                          (A.BARCODE, 5)])
        self.atlas.finish("failed", A.BARCODE)
        out = self.advance()
        self.assertTrue(out["done"])
        self.assertEqual(len(self.atlas.requests), 9)
        self.assertEqual({step["status"] for step in out["steps"][4:]}, {"failed"})

    def test_add_photos_to_an_existing_wine_runs_no_atlas_step(self):
        self.atlas.stage_one_done = True
        status, out = self.request("/api/atlas-import/photos?url="
                                   + urllib.parse.quote(self.url, safe=""))
        self.assertEqual(out["product"]["display_name"],
                         "ЛЕКИФ «Кубань» — розовое полусухое вино")
        body = {"slug": "wine-b", "url": self.url,
                "media_ids": [item["media_id"] for item in out["photos"]]}
        status, out = self.request("/api/atlas-import/add", body)
        self.assertEqual(status, 200, out)
        self.assertEqual(out["added"], 2)
        self.assertEqual(len(out["record"]["_alternatives"]), 2)
        self.assertEqual(self.query("SELECT image_type FROM wine_image WHERE wine_slug = "
                                    "'wine-b' AND image_type IN ('main', 'main_patched')"),
                         [])
        status, out = self.request("/api/atlas-import/add", body)
        self.assertEqual((status, out["added"]), (200, 0))
        self.assertEqual(len(out["record"]["_alternatives"]), 2)
        for changed, code in (({"slug": "no-wine"}, 404), ({"slug": ""}, 400),
                              ({"media_ids": [99]}, 400)):
            with self.subTest(changed=changed):
                self.assertEqual(self.request("/api/atlas-import/add",
                                              dict(body, **changed))[0], code)
        self.assertEqual(self.atlas.requests, [])

    def test_photos_and_create(self):
        self.atlas.stage_one_done = True
        status, out = self.request("/api/atlas-import/photos?url="
                                   + urllib.parse.quote(self.url, safe=""))
        self.assertEqual(status, 200, out)
        self.assertEqual([(item["media_id"], item["group"]) for item in out["photos"]],
                         [(1, [1, 2]), (5, [5, 3])])
        status, out = self.request("/api/atlas-import/create", self.form([1, 5]))
        self.assertEqual(status, 200, out)
        self.assertEqual(out["slug"], "__lekif-kuban")
        self.assertIsNone(out["record"].get("main_image_url"))
        self.assertEqual(len(out["record"]["_alternatives"]), 2)
        self.assertEqual(self.query("SELECT csv_photo_name, state FROM wine_catalog WHERE "
                                    "wine_slug = '__lekif-kuban'"),
                         [("atlas-%s" % UUID, "Active")])
        self.assertEqual(self.query("SELECT source_name FROM wine_image WHERE wine_slug = "
                                    "'__lekif-kuban' ORDER BY rowid"),
                         [("atlas-1.png",), ("atlas-5.png",)])
        self.assertEqual(self.query("SELECT source, product_uuid FROM wine_atlas_binding "
                                    "WHERE wine_slug = '__lekif-kuban'"),
                         [("manual", UUID)])
        self.assertEqual(self.query("SELECT count(*) FROM wine_image WHERE wine_slug = "
                                    "'__lekif-kuban' AND image_type IN ('main', "
                                    "'main_patched')"), [(0,)])
        # The derived crop of media 1 is the file of the photo.
        stored = self.query("SELECT sha256 FROM wine_image WHERE source_name = "
                            "'atlas-1.png'")[0][0]
        import hashlib
        self.assertEqual(stored, hashlib.sha256(RED).hexdigest())
        status, out = self.request("/api/atlas-import/create", self.form([1]))
        self.assertEqual(status, 409, out)

    def test_create_refusals(self):
        cases = [(self.form([1, 99]), 400, "has no image 99"),
                 (self.form([]), 400, "media_ids"),
                 (self.form([4]), 400, "has no image 4"),
                 (self.form([1], slug="no-prefix"), 400, "MUST start with __"),
                 (self.form([1], region=""), 400, "`region` is empty"),
                 (self.form([1], url="http://10.0.0.1/products/%s" % UUID), 400, "loopback")]
        for body, code, text in cases:
            with self.subTest(text=text):
                status, out = self.request("/api/atlas-import/create", body)
                self.assertEqual(status, code, out)
                self.assertIn(text, out["error"])
        self.assertEqual(self.query("SELECT count(*) FROM wine_catalog WHERE wine_slug "
                                    "LIKE '\\_\\_%' ESCAPE '\\'"), [(0,)])

    def test_atlas_down_creates_nothing(self):
        self.atlas_server.shutdown()
        self.atlas_server.server_close()
        status, out = self.request("/api/atlas-import/create", self.form([1]))
        self.assertEqual(status, 502, out)
        self.assertIn("cannot reach Drink Atlas", out["error"])
        self.assertEqual(self.query("SELECT count(*) FROM wine_catalog"), [(len(WINES),)])

    def test_routes_and_methods(self):
        status, _out = self.request("/api/atlas-import/advance")
        self.assertEqual(status, 405)
        status, out = self.request("/api/atlas-import/advance", {"url": "x"})
        self.assertEqual(status, 400, out)
        with urllib.request.urlopen(self.base + "/atlas-import.js") as response:
            self.assertEqual(response.status, 200)
            self.assertIn("javascript", response.headers["Content-Type"])


if __name__ == "__main__":
    unittest.main()
