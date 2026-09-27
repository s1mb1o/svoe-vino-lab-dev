import hashlib
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
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import lab_pages  # noqa: E402
import lab_server as LAB  # noqa: E402
import labdb  # noqa: E402

WINES = [
    ("wine-b", "Вино b", "Винодельня", "Белое", "Соломенный", "Крым",
     "Алиготе", "Описание b", "b.webp", "Active", None),
    ("wine-a", "Вино a", "Винодельня", "Красное", "Рубиновый", "Кубань",
     None, "Описание a", "a.webp", "Removed", "import"),
]
# The form of `wine_code.modified_at` (schema 026).
CODE_TIME_RE = r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$"


class LabServerTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.executemany("INSERT INTO wine_catalog (%s) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
                             % ", ".join(LAB.CATALOG_COLUMNS), WINES)
        conn.close()
        self.server = LAB.make_server(self.db, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def request(self, path, method="GET", body=None):
        data = body if body is not None else (b"{}" if method == "POST" else None)
        req = urllib.request.Request(self.base + path, method=method, data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, response.headers, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers, exc.read().decode("utf-8")

    def test_dataset_page_is_the_shared_page(self):
        status, headers, body = self.request("/dataset")
        self.assertEqual(status, 200)
        self.assertEqual(body, lab_pages.page("dataset.html"))
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn(lab_pages.theme_css(), body)

    def test_dataset_preview_paths_send_the_page(self):
        for path in ("/dataset/wine-a", "/dataset/wine-a/patch", "/dataset/wine%20a",
                     "/dataset/wine-a/alternative/" + "a" * 64):
            status, _, body = self.request(path)
            self.assertEqual(status, 200, path)
            self.assertEqual(body, lab_pages.page("dataset.html"), path)
        for path in ("/dataset/", "/dataset/wine-a/other", "/dataset/wine-a/patch/x",
                     "/dataset/wine-a/alternative", "/dataset/wine-a/alternative/abc"):
            self.assertEqual(self.request(path)[0], 404, path)

    def test_api_dataset_sends_the_wines_in_import_order(self):
        status, _, body = self.request("/api/dataset")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual([r["slug"] for r in data["records"]], ["wine-b", "wine-a"])
        first = data["records"][0]
        self.assertNotIn("wine_slug", first)
        self.assertEqual((first["name"], first["grapes"], first["csv_photo_name"]),
                         ("Вино b", "Алиготе", "b.webp"))
        self.assertIsNone(data["records"][1]["grapes"])
        self.assertEqual([(r["state"], r["removed_by"]) for r in data["records"]],
                         [("Active", None), ("Removed", "import")])
        self.assertFalse(first["_patched"])
        self.assertNotIn("_barcodes", first)
        self.assertEqual(data["database_file"], self.db)
        self.assertEqual(data["patches"], 0)
        self.assertNotIn("barcodes", data)
        # The page shows the Barcodes editor only for an answer with `barcode_file`.
        self.assertNotIn("barcode_file", data)

    def add_image(self, slug, image_type, data, extension="webp", size=(None, None)):
        """Store `data` as an image of `slug`. Return its URL on the lab server."""
        digest = hashlib.sha256(data).hexdigest()
        folder = self.root / "images" / labdb.IMAGE_FOLDERS[image_type]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / ("%s.%s" % (digest, extension))).write_bytes(data)
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("INSERT INTO image (sha256, folder, extension, width, height) "
                         "VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                         (digest, labdb.IMAGE_FOLDERS[image_type], extension) + size)
            conn.execute("INSERT INTO wine_image (wine_slug, image_type, sha256, "
                         "source_name, match_method) VALUES (?, ?, ?, 'x', 'manual')",
                         (slug, image_type, digest))
        conn.close()
        return "/images/%s/%s.%s" % (labdb.IMAGE_FOLDERS[image_type], digest, extension)

    def add_derivative(self, original_url, method, data, size):
        """Store `data` as the processed file of an original. Return its URL."""
        source = original_url.rsplit("/", 1)[1].split(".")[0]
        digest = hashlib.sha256(data).hexdigest()
        folder = self.root / "images" / labdb.DERIVED_FOLDER
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (digest + ".png")).write_bytes(data)
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("INSERT INTO image VALUES (?, 'cropped', 'png', ?, ?)",
                         (digest,) + size)
            conn.execute("INSERT INTO image_derivative (source_sha256, method, settings, "
                         "sha256, box_left, box_top, box_right, box_bottom) "
                         "VALUES (?, ?, 'test', ?, 0, 0, ?, ?)",
                         (source, method, digest) + size)
        conn.close()
        return "/images/cropped/%s.png" % digest

    def test_api_dataset_sends_the_card_image(self):
        main_b = self.add_image("wine-b", "main", b"b main")
        main_a = self.add_image("wine-a", "main", b"a main")
        patched_a = self.add_image("wine-a", "main_patched", b"a patched", "png")
        self.add_image("wine-a", "full_front", b"a front")
        records = json.loads(self.request("/api/dataset")[2])["records"]
        # The patch stands beside the `main` image on the card; it does not replace it.
        self.assertEqual([(r["main_image_url"], r["main_image_type"],
                           r["main_image_match_method"]) for r in records],
                         [(main_b, "main", "manual"), (main_a, "main", "manual")])
        self.assertEqual([(r["_patched"], r["_patch_url"], r["_patch_image_url"],
                           r["_patch_derivation"]) for r in records],
                         [(False, None, None, None), (True, patched_a, patched_a, None)])

    def test_api_dataset_sends_the_size_of_the_card_image(self):
        self.add_image("wine-b", "main", b"b main", size=(300, 900))
        self.add_image("wine-a", "main", b"a main", size=(100, 200))
        self.add_image("wine-a", "main_patched", b"a patched")
        records = json.loads(self.request("/api/dataset")[2])["records"]
        self.assertEqual([(r["main_image_width"], r["main_image_height"]) for r in records],
                         [(300, 900), (100, 200)])

    def test_api_dataset_sends_the_processed_file_and_its_badge(self):
        original = self.add_image("wine-b", "main", b"b main", size=(300, 900))
        processed = self.add_derivative(original, "seg", b"b processed", (120, 700))
        records = json.loads(self.request("/api/dataset")[2])["records"]
        first = records[0]
        self.assertEqual((first["main_image_url"], first["main_image_original_url"],
                          first["main_image_derivation"]), (processed, original, "seg"))
        self.assertEqual((first["main_image_width"], first["main_image_height"]), (120, 700))
        self.assertEqual(records[1]["main_image_derivation"], None)
        status, headers, _ = self.request(processed, "HEAD")
        self.assertEqual((status, headers["Content-Type"]), (200, "image/png"))

    def test_a_crop_that_cut_nothing_gets_no_badge(self):
        original = self.add_image("wine-b", "main", b"b main", size=(300, 900))
        self.add_derivative(original, "crop", b"b same pixels", (300, 900))
        seg_original = self.add_image("wine-a", "main", b"a main", size=(300, 900))
        seg = self.add_derivative(seg_original, "seg", b"a seg", (300, 900))
        first, second = json.loads(self.request("/api/dataset")[2])["records"]
        self.assertEqual((first["main_image_url"], first["main_image_derivation"],
                          first["main_image_width"], first["main_image_height"]),
                         (original, None, 300, 900))
        # A `seg` file changes the pixels, so it keeps its badge with the whole box.
        self.assertEqual((second["main_image_url"], second["main_image_derivation"]),
                         (seg, "seg"))

    def test_cut_nothing_knows_a_turned_image(self):
        self.assertTrue(LAB.cut_nothing("crop", (0, 0, 300, 900), 300, 900))
        self.assertTrue(LAB.cut_nothing("crop", (0, 0, 900, 300), 300, 900))
        self.assertFalse(LAB.cut_nothing("crop", (0, 0, 299, 900), 300, 900))
        self.assertFalse(LAB.cut_nothing("crop", (1, 0, 300, 900), 300, 900))
        self.assertFalse(LAB.cut_nothing("seg", (0, 0, 300, 900), 300, 900))
        self.assertFalse(LAB.cut_nothing("crop", (0, 0, 300, 900), None, None))

    def test_api_dataset_sends_no_card_image_for_a_wine_with_none(self):
        records = json.loads(self.request("/api/dataset")[2])["records"]
        self.assertEqual([(r["main_image_url"], r["main_image_type"],
                           r["main_image_match_method"]) for r in records],
                         [(None, None, None)] * 2)

    def test_image_route_sends_the_stored_file(self):
        url = self.add_image("wine-b", "main", b"b main")
        req = urllib.request.Request(self.base + url)
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.read(), b"b main")
            self.assertEqual(response.headers["Content-Type"], "image/webp")
            self.assertEqual(response.headers["Cache-Control"],
                             "public, max-age=31536000, immutable")
        url = self.add_image("wine-a", "main_patched", b"a patched", "png")
        status, headers, _ = self.request(url, "HEAD")
        self.assertEqual((status, headers["Content-Type"]), (200, "image/png"))

    def test_image_route_sends_no_other_file(self):
        url = self.add_image("wine-b", "main", b"b main")
        digest = url.rsplit("/", 1)[1]
        for path in ("/images/main/../../lab.sqlite3", "/images/main/%2e%2e%2flab.sqlite3",
                     "/images/other/" + digest, "/images/main/" + digest.upper(),
                     "/images/main/" + "0" * 64 + ".webp", "/images/main/",
                     "/images/" + digest):
            self.assertEqual(self.request(path)[0], 404, path)

    def test_clusters_page_is_on(self):
        status, headers, body = self.request("/clusters")
        self.assertEqual(status, 200)
        self.assertEqual(body, lab_pages.page("clusters.html"))
        self.assertIn("text/html", headers["Content-Type"])

    def test_embedding_page_is_on(self):
        status, headers, body = self.request("/embedding")
        self.assertEqual(status, 200)
        self.assertEqual(body, lab_pages.page("embedding.html"))
        self.assertIn("text/html", headers["Content-Type"])

    def test_embedding_routes_read_the_config_path(self):
        missing = str(self.root / "missing.yaml")
        self.server.config_path = missing
        for path, method in (("/api/embeddings", "GET"), ("/api/embedding-jobs", "GET"),
                             ("/api/embeddings/gx10-a/build", "POST"),
                             ("/api/embeddings/gx10-a/stop", "POST")):
            status, _, body = self.request(path, method)
            self.assertEqual(status, 503, path)
            self.assertIn(missing, json.loads(body)["error"])

    def test_cluster_routes_read_the_config_path(self):
        missing = str(self.root / "missing.yaml")
        self.server.config_path = missing
        for path, method in (("/api/clusters", "GET"),
                             ("/api/clusters/gx10-a/build", "POST")):
            status, _, body = self.request(path, method)
            self.assertEqual(status, 503, path)
            self.assertIn(missing, json.loads(body)["error"])

    def test_old_embedding_routes_stay_disabled(self):
        for path in ("/api/embedding", "/img/embedding/a.png"):
            status, _, body = self.request(path)
            self.assertEqual(status, 503, path)
            self.assertIn("disabled for now", body)

    def test_pages_keep_the_navigation_order(self):
        # Dataset first, Embeddings second: owner message of 2026-09-25T06:50:29+0300.
        self.assertEqual([label for _, label in LAB.NAV][:2], ["Dataset", "Embeddings"])
        hrefs = [href for href, _ in LAB.NAV]
        pages = {name: lab_pages.page(name) for name in
                 ("dataset.html", "embedding.html", "clusters.html")}
        pages["/runs"] = self.request("/runs")[2]
        pages["/testset"] = self.request("/testset")[2]
        pages["/health"] = self.request("/health")[2]
        for name, body in pages.items():
            nav = re.search(r'<nav class="nav">(.*?)</nav>', body, re.S).group(1)
            self.assertEqual(re.findall(r'href="([^"]*)"', nav), hrefs, name)

    def test_other_api_routes_are_disabled(self):
        for path, method in (("/api/rows", "GET"),
                             ("/api/dataset-validation", "GET"),
                             ("/api/exclude", "POST")):
            status, _, body = self.request(path, method)
            self.assertEqual(status, 503, path)
            self.assertIn("disabled for now", json.loads(body)["error"])

    def post_state(self, slug, action):
        status, _, body = self.request("/api/wine-state", "POST",
                                       json.dumps({"slug": slug, "action": action}).encode())
        return status, json.loads(body)

    def stored(self, slug):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute("SELECT state, removed_by FROM wine_catalog "
                                "WHERE wine_slug = ?", (slug,)).fetchone()
        finally:
            conn.close()

    def test_state_actions_follow_the_allowed_transitions(self):
        steps = [("disable", "Disabled", None), ("enable", "Active", None),
                 ("disable", "Disabled", None), ("remove", "Removed", "person"),
                 ("restore", "Active", None), ("remove", "Removed", "person")]
        for action, state, removed_by in steps:
            status, body = self.post_state("wine-b", action)
            self.assertEqual(status, 200, action)
            self.assertEqual(body, {"slug": "wine-b", "state": state, "removed_by": removed_by})
            self.assertEqual(self.stored("wine-b"), (state, removed_by), action)

    def test_restore_of_a_wine_that_the_import_removed(self):
        self.assertEqual(self.post_state("wine-a", "restore")[0], 200)
        self.assertEqual(self.stored("wine-a"), ("Active", None))

    def test_state_action_from_a_wrong_state_is_a_conflict(self):
        for slug, action in (("wine-b", "enable"), ("wine-b", "restore"),
                             ("wine-a", "disable"), ("wine-a", "remove")):
            status, body = self.post_state(slug, action)
            self.assertEqual(status, 409, (slug, action))
            self.assertIn("needs", body["error"])
        self.assertEqual(self.stored("wine-b"), ("Active", None))
        self.assertEqual(self.stored("wine-a"), ("Removed", "import"))

    def test_state_request_errors(self):
        self.assertEqual(self.post_state("wine-none", "disable")[0], 404)
        self.assertEqual(self.post_state("wine-b", "delete")[0], 400)
        self.assertEqual(self.post_state("", "disable")[0], 400)
        self.assertEqual(self.request("/api/wine-state", "POST", b"not json")[0], 400)
        self.assertEqual(self.request("/api/wine-state", "POST", b"[1]")[0], 400)
        self.assertEqual(self.request("/api/wine-state", "POST", b"x" * 5000)[0], 400)
        self.assertEqual(self.request("/api/wine-state", "DELETE")[0], 503)
        self.assertEqual(self.stored("wine-b"), ("Active", None))

    def post_code(self, route, slug, key, value):
        status, _, body = self.request(route, "POST",
                                       json.dumps({"slug": slug, key: value}).encode())
        return status, json.loads(body)

    def delete_code(self, route, slug, key, value):
        query = urllib.parse.urlencode({"slug": slug, key: value})
        status, _, body = self.request("%s?%s" % (route, query), "DELETE")
        return status, json.loads(body)

    def codes(self):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(
                "SELECT wine_slug, kind, value FROM wine_code ORDER BY rowid").fetchall()
        finally:
            conn.close()

    def test_code_routes_add_values_in_their_normal_form(self):
        cases = (("/api/dataset-gtin", "gtin", "4631168664979", "04631168664979", "gtins"),
                 ("/api/dataset-qr-url", "url", "URL:https://A.ru/w#x", "https://a.ru/w",
                  "qr_urls"))
        for route, key, value, stored, list_key in cases:
            status, body = self.post_code(route, "wine-b", key, value)
            self.assertEqual(status, 200, route)
            added = body.pop("modified_at")
            self.assertEqual(list(added), [stored])
            self.assertRegex(added[stored], CODE_TIME_RE)
            self.assertEqual(body, {"ok": True, "slug": "wine-b", key: stored,
                                    list_key: [stored], "total": 1})
        data = json.loads(self.request("/api/dataset")[2])
        first = data["records"][0]
        self.assertEqual((first["_gtins"], first["_qr_urls"]),
                         (["04631168664979"], ["https://a.ru/w"]))
        self.assertEqual(data["records"][1]["_gtins"], [])
        self.assertEqual((data["gtins"], data["qr_urls"]), (1, 1))

    def test_lab_has_no_barcode_route(self):
        # The lab keeps GTINs alone (owner choice of 2026-09-25). The route answers like
        # each other API route that the lab server does not serve.
        status, body = self.post_code("/api/dataset-barcode", "wine-b", "barcode", "AB-12")
        self.assertEqual(status, 503)
        self.assertIn("disabled", body["error"])
        self.assertEqual(self.codes(), [])

    def test_code_values_keep_the_order_of_the_writes(self):
        for value in ("4640005351194", "4640005350852"):
            self.assertEqual(self.post_code("/api/dataset-gtin", "wine-b", "gtin", value)[0], 200)
        data = json.loads(self.request("/api/dataset")[2])
        self.assertEqual(data["records"][0]["_gtins"], ["04640005351194", "04640005350852"])

    def test_code_times_give_the_insert_time_of_each_value(self):
        # Schema 026: a trigger sets `modified_at` at the insert. A row that is older than
        # 026 keeps NULL.
        for value in ("4640005351194", "4640005350852"):
            self.post_code("/api/dataset-gtin", "wine-b", "gtin", value)
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("UPDATE wine_code SET modified_at = NULL WHERE value = ?",
                         ("04640005350852",))
        conn.close()
        data = json.loads(self.request("/api/dataset")[2])
        times = data["records"][0]["_code_times"]
        self.assertEqual(set(times), {"gtin", "qr_url"})
        self.assertEqual(sorted(times["gtin"]), ["04640005350852", "04640005351194"])
        self.assertRegex(times["gtin"]["04640005351194"], CODE_TIME_RE)
        self.assertIsNone(times["gtin"]["04640005350852"])
        self.assertEqual(times["qr_url"], {})
        self.assertEqual(data["records"][1]["_code_times"], {"gtin": {}, "qr_url": {}})

    def test_two_wines_share_one_value(self):
        # wine-a is Removed. A write is allowed for a wine in each state.
        for slug, total in (("wine-b", 1), ("wine-a", 2)):
            status, body = self.post_code("/api/dataset-gtin", slug, "gtin", "4631168664979")
            self.assertEqual((status, body["total"]), (200, total), slug)
        self.assertEqual(self.codes(), [("wine-b", "gtin", "04631168664979"),
                                        ("wine-a", "gtin", "04631168664979")])

    def test_same_value_for_the_same_wine_is_a_conflict(self):
        self.post_code("/api/dataset-gtin", "wine-b", "gtin", "4631168664979")
        # The GTIN-14 form of the same GTIN is the same value.
        status, body = self.post_code("/api/dataset-gtin", "wine-b", "gtin", "04631168664979")
        self.assertEqual(status, 409)
        self.assertIn("already has the gtin 04631168664979", body["error"])
        self.assertEqual(len(self.codes()), 1)

    def test_code_values_are_checked(self):
        cases = (("/api/dataset-gtin", "gtin", "4631168664970",
                  "wrong check digit 0; expected 9"),
                 ("/api/dataset-gtin", "gtin", "46311686649", "it has 11"),
                 ("/api/dataset-qr-url", "url", "ftp://a.ru/", "http or https"),
                 ("/api/dataset-gtin", "gtin", "", "holds no `gtin`"),
                 ("/api/dataset-qr-url", "url", 5, "holds no `url`"))
        for route, key, value, message in cases:
            status, body = self.post_code(route, "wine-b", key, value)
            self.assertEqual(status, 400, (route, value))
            self.assertIn(message, body["error"])
        self.assertEqual(self.codes(), [])

    def test_code_request_errors(self):
        route = "/api/dataset-gtin"
        self.assertEqual(self.post_code(route, "wine-none", "gtin", "4631168664979")[0], 404)
        self.assertEqual(self.post_code(route, "", "gtin", "4631168664979")[0], 400)
        self.assertEqual(self.request(route, "POST", b"not json")[0], 400)
        self.assertEqual(self.request(route, "POST", b"[1]")[0], 400)
        self.assertEqual(self.request(route, "POST", b"x" * 20000)[0], 400)
        self.assertEqual(self.request(route, "PUT")[0], 503)
        self.assertEqual(self.codes(), [])

    def test_delete_removes_one_stored_value(self):
        for value in ("4640005351194", "4640005350852"):
            self.post_code("/api/dataset-gtin", "wine-b", "gtin", value)
        self.post_code("/api/dataset-gtin", "wine-a", "gtin", "4640005351194")
        status, body = self.delete_code("/api/dataset-gtin", "wine-b", "gtin", "04640005351194")
        self.assertEqual(status, 200)
        self.assertEqual(list(body.pop("modified_at")), ["04640005350852"])
        self.assertEqual(body, {"ok": True, "slug": "wine-b", "removed": "04640005351194",
                                "gtins": ["04640005350852"], "total": 2})
        self.assertEqual(self.codes(), [("wine-b", "gtin", "04640005350852"),
                                        ("wine-a", "gtin", "04640005351194")])

    def test_delete_errors(self):
        self.post_code("/api/dataset-qr-url", "wine-b", "url", "https://a.ru/")
        cases = (("wine-b", "https://b.ru/", 404, "has no url"),
                 ("wine-none", "https://a.ru/", 404, "no wine"),
                 ("wine-b", "", 400, "holds no `url`"))
        for slug, value, code, message in cases:
            status, body = self.delete_code("/api/dataset-qr-url", slug, "url", value)
            self.assertEqual(status, code, (slug, value))
            self.assertIn(message, body["error"])
        # A GTIN MUST be sent in its stored form.
        self.post_code("/api/dataset-gtin", "wine-b", "gtin", "4631168664979")
        self.assertEqual(
            self.delete_code("/api/dataset-gtin", "wine-b", "gtin", "4631168664979")[0], 404)
        self.assertEqual(len(self.codes()), 2)

    # The Atlas Core products of a wine: plans 15 and 54.
    UUID_1 = "6062ada1-1c2b-4f3e-9a8b-0123456789ab"
    UUID_2 = "7a1b2c3d-0000-4000-8000-00000000000f"
    UUID_3 = "00000000-1111-4222-8333-444444444444"

    def post_atlas(self, slug, product_uuid):
        status, _, body = self.request("/api/dataset-atlas-binding", "POST", json.dumps(
            {"slug": slug, "product_uuid": product_uuid}).encode())
        return status, json.loads(body)

    def delete_atlas(self, slug, product_uuid):
        query = urllib.parse.urlencode({"slug": slug, "product_uuid": product_uuid})
        status, _, body = self.request("/api/dataset-atlas-binding?" + query, "DELETE")
        return status, json.loads(body)

    def add_automatic(self, slug, product_uuid):
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("INSERT INTO wine_atlas_binding VALUES (?, 'automatic', ?)",
                         (slug, product_uuid))
        conn.close()

    def atlas_rows(self):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute("SELECT wine_slug, source, product_uuid FROM "
                                "wine_atlas_binding ORDER BY wine_slug, source").fetchall()
        finally:
            conn.close()

    def test_api_dataset_sends_the_atlas_bindings(self):
        self.add_automatic("wine-b", self.UUID_1)
        data = json.loads(self.request("/api/dataset")[2])
        self.assertTrue(data["atlas_binding_editor"])
        self.assertEqual((data["atlas_bindings"], data["atlas_manual_bindings"]), (1, 0))
        first, second = data["records"]
        self.assertEqual(first["_atlas_products"],
                         [{"product_uuid": self.UUID_1, "source": "automatic"}])
        self.assertEqual(second["_atlas_products"], [])
        self.assertNotIn("_atlas_product_uuid", first)

    def test_a_manual_product_adds_to_the_automatic_one(self):
        self.add_automatic("wine-b", self.UUID_1)
        status, body = self.post_atlas("wine-b", " %s " % self.UUID_2.upper())
        self.assertEqual(status, 200)
        self.assertEqual(body, {"ok": True, "slug": "wine-b", "product_uuid": self.UUID_2,
                                "source": "manual",
                                "products": [
                                    {"product_uuid": self.UUID_1, "source": "automatic"},
                                    {"product_uuid": self.UUID_2, "source": "manual"}],
                                "total": 2, "manual": 1})
        record = json.loads(self.request("/api/dataset")[2])["records"][0]
        self.assertEqual(record["_atlas_products"], body["products"])
        # A third product. A UUID that the wine has, of either source, answers 409.
        self.assertEqual(self.post_atlas("wine-b", self.UUID_3)[1]["total"], 3)
        for product in (self.UUID_1, self.UUID_3.upper()):
            status, body = self.post_atlas("wine-b", product)
            self.assertEqual(status, 409)
            self.assertIn("already has the Atlas product", body["error"])
        # A DELETE removes one product of either source.
        status, body = self.delete_atlas("wine-b", self.UUID_1.upper())
        self.assertEqual(status, 200)
        self.assertEqual(body, {"ok": True, "slug": "wine-b", "removed": self.UUID_1,
                                "removed_source": "automatic",
                                "products": [
                                    {"product_uuid": self.UUID_2, "source": "manual"},
                                    {"product_uuid": self.UUID_3, "source": "manual"}],
                                "total": 2, "manual": 2})
        self.assertEqual(self.atlas_rows(), [("wine-b", "manual", self.UUID_3),
                                             ("wine-b", "manual", self.UUID_2)])
        status, body = self.delete_atlas("wine-b", self.UUID_2)
        self.assertEqual((status, body["removed_source"], body["total"], body["manual"]),
                         (200, "manual", 1, 1))
        self.assertEqual(self.atlas_rows(), [("wine-b", "manual", self.UUID_3)])

    def test_remove_of_the_only_binding_leaves_none(self):
        # wine-a is Removed. A write is allowed for a wine in each state.
        self.assertEqual(self.post_atlas("wine-a", self.UUID_1)[0], 200)
        status, body = self.delete_atlas("wine-a", self.UUID_1)
        self.assertEqual((status, body["products"], body["total"]), (200, [], 0))
        self.assertEqual(self.atlas_rows(), [])

    def test_atlas_binding_errors(self):
        self.add_automatic("wine-b", self.UUID_1)
        cases = ((self.post_atlas("wine-b", "not-a-uuid"), 400, "not a valid UUID"),
                 (self.post_atlas("wine-b", " "), 400, "empty"),
                 (self.post_atlas("wine-b", 5), 400, "MUST be a string"),
                 (self.post_atlas("", self.UUID_1), 400, "no wine slug"),
                 (self.post_atlas("wine-none", self.UUID_1), 404, "no wine"),
                 (self.delete_atlas("wine-b", "not-a-uuid"), 400, "not a valid UUID"),
                 # wine-a has no row. wine-b has no row of UUID_2.
                 (self.delete_atlas("wine-a", self.UUID_1), 404, "has no Atlas product"),
                 (self.delete_atlas("wine-b", self.UUID_2), 404, "has no Atlas product"),
                 (self.delete_atlas("wine-none", self.UUID_1), 404, "no wine"))
        for (status, body), code, message in cases:
            self.assertEqual(status, code, message)
            self.assertIn(message, body["error"])
        self.assertEqual(self.request("/api/dataset-atlas-binding", "DELETE")[0], 400)
        self.assertEqual(self.request("/api/dataset-atlas-binding?slug=wine-b", "DELETE")[0],
                         400)
        self.assertEqual(self.request("/api/dataset-atlas-binding", "PUT")[0], 503)
        self.assertEqual(self.atlas_rows(), [("wine-b", "automatic", self.UUID_1)])

    # The comments of a wine: plan 17.
    def post_comment(self, slug, text, **extra):
        status, _, body = self.request("/api/dataset-comment", "POST", json.dumps(
            dict({"slug": slug, "text": text}, **extra)).encode())
        return status, json.loads(body)

    def delete_comment(self, slug, comment_id):
        query = urllib.parse.urlencode({"slug": slug, "id": comment_id})
        status, _, body = self.request("/api/dataset-comment?" + query, "DELETE")
        return status, json.loads(body)

    def comment_rows(self):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute("SELECT wine_slug, source, text FROM wine_comment "
                                "ORDER BY id").fetchall()
        finally:
            conn.close()

    def test_comment_route_adds_a_user_comment(self):
        status, body = self.post_comment("wine-b", "  Пробка\r\nсухая  ")
        self.assertEqual(status, 200)
        comment = body["comment"]
        self.assertRegex(comment["created_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(comment, {"id": comment["id"], "created_at": comment["created_at"],
                                   "source": "user", "text": "Пробка\nсухая"})
        self.assertEqual(body, {"ok": True, "slug": "wine-b", "comment": comment,
                                "comments": [comment], "total": 1})
        data = json.loads(self.request("/api/dataset")[2])
        self.assertEqual(data["comments"], 1)
        self.assertEqual([r["_comments"] for r in data["records"]], [[comment], []])

    def test_comment_route_takes_the_script_source(self):
        # wine-a is Removed. A comment is allowed for a wine in each state.
        status, body = self.post_comment("wine-a", "checked by a script", source="script")
        self.assertEqual((status, body["comment"]["source"]), (200, "script"))
        self.assertEqual(self.comment_rows(), [("wine-a", "script", "checked by a script")])

    def test_longest_comment_fits_the_body_limit(self):
        # json.dumps writes each Cyrillic character as a 6-byte escape.
        self.assertEqual(self.post_comment("wine-b", "я" * 4000)[0], 200)

    def test_comments_are_sent_in_time_order(self):
        conn = sqlite3.connect(self.db)
        with conn:
            conn.executemany("INSERT INTO wine_comment (wine_slug, created_at, source, text) "
                             "VALUES ('wine-b', ?, 'user', ?)",
                             [("2020-01-01T09:00:00Z", "late"),
                              ("2020-01-01T08:00:00Z", "early")])
        conn.close()
        record = json.loads(self.request("/api/dataset")[2])["records"][0]
        self.assertEqual([c["text"] for c in record["_comments"]], ["early", "late"])
        # A new comment has the present time, so it comes last.
        body = self.post_comment("wine-b", "new")[1]
        self.assertEqual([c["text"] for c in body["comments"]], ["early", "late", "new"])

    def test_delete_removes_one_comment(self):
        first = self.post_comment("wine-b", "same")[1]["comment"]
        second = self.post_comment("wine-b", "same")[1]["comment"]
        self.post_comment("wine-a", "other")
        status, body = self.delete_comment("wine-b", first["id"])
        self.assertEqual(status, 200)
        self.assertEqual(body, {"ok": True, "slug": "wine-b", "removed": first["id"],
                                "comments": [second], "total": 2})
        self.assertEqual(self.comment_rows(), [("wine-b", "user", "same"),
                                               ("wine-a", "user", "other")])

    def test_comment_errors(self):
        other = self.post_comment("wine-a", "other")[1]["comment"]
        cases = ((self.post_comment("wine-b", " \n "), 400, "empty"),
                 (self.post_comment("wine-b", 5), 400, "MUST be a string"),
                 (self.post_comment("wine-b", "x" * 4001), 400, "longer than 4000"),
                 # JSON allows "\ud800" alone; SQLite cannot store it (review, 2026-09-25).
                 (self.post_comment("wine-b", "a\ud800b"), 400, "lone surrogate"),
                 (self.post_comment("wine-b", "x", source="person"), 400, "unknown source"),
                 (self.post_comment("wine-b", "x", source=None), 400, "unknown source"),
                 (self.post_comment("", "x"), 400, "no wine slug"),
                 (self.post_comment("wine-none", "x"), 404, "no wine"),
                 # The id of a comment of another wine removes nothing.
                 (self.delete_comment("wine-b", other["id"]), 404, "has no comment"),
                 (self.delete_comment("wine-b", "x"), 400, "no valid comment `id`"),
                 (self.delete_comment("wine-b", "-1"), 400, "no valid comment `id`"),
                 (self.delete_comment("wine-b", "9" * 19), 400, "no valid comment `id`"),
                 (self.delete_comment("wine-none", other["id"]), 404, "no wine"))
        for (status, body), code, message in cases:
            self.assertEqual(status, code, message)
            self.assertIn(message, body["error"])
        self.assertEqual(self.request("/api/dataset-comment", "DELETE")[0], 400)
        self.assertEqual(self.request("/api/dataset-comment", "POST", b"not json")[0], 400)
        self.assertEqual(self.request("/api/dataset-comment", "PUT")[0], 503)
        self.assertEqual(self.comment_rows(), [("wine-a", "user", "other")])

    # The favorite wines: plan 19.
    def post_favorite(self, slug, favorite):
        status, _, body = self.request("/api/dataset-favorite", "POST", json.dumps(
            {"slug": slug, "favorite": favorite}).encode())
        return status, json.loads(body)

    def test_favorite_route_marks_and_removes(self):
        # wine-a is Removed. A favorite MAY have each state.
        status, body = self.post_favorite("wine-a", True)
        self.assertEqual((status, body),
                         (200, {"ok": True, "slug": "wine-a", "favorite": True, "total": 1}))
        data = json.loads(self.request("/api/dataset")[2])
        self.assertEqual(data["favorites"], 1)
        self.assertEqual([r["_favorite"] for r in data["records"]], [False, True])
        # The body names the new value, so a repeated request gives the same result.
        self.assertEqual(self.post_favorite("wine-a", True)[1]["total"], 1)
        status, body = self.post_favorite("wine-a", False)
        self.assertEqual((status, body["favorite"], body["total"]), (200, False, 0))
        self.assertEqual(self.post_favorite("wine-a", False)[1]["total"], 0)
        data = json.loads(self.request("/api/dataset")[2])
        self.assertEqual([r["_favorite"] for r in data["records"]], [False, False])

    def test_favorite_errors(self):
        cases = ((self.post_favorite("wine-b", 1), 400, "true or false"),
                 (self.post_favorite("wine-b", "true"), 400, "true or false"),
                 (self.post_favorite("wine-b", None), 400, "true or false"),
                 (self.post_favorite("", True), 400, "no wine slug"),
                 (self.post_favorite("wine-none", True), 404, "no wine"))
        for (status, body), code, message in cases:
            self.assertEqual(status, code, message)
            self.assertIn(message, body["error"])
        self.assertEqual(self.request("/api/dataset-favorite", "POST", b"not json")[0], 400)
        self.assertEqual(self.request("/api/dataset-favorite", "DELETE")[0], 503)
        self.assertEqual(json.loads(self.request("/api/dataset")[2])["favorites"], 0)

    # The wine type: plan 52.
    def post_beverage_type(self, body):
        status, _, text = self.request("/api/dataset-beverage-type", "POST",
                                       json.dumps(body).encode())
        return status, json.loads(text)

    def test_beverage_type_route_sets_changes_and_removes(self):
        data = json.loads(self.request("/api/dataset")[2])
        self.assertEqual(data["beverage_types"], {"4": 0, "44": 0})
        self.assertEqual([r["_beverage_type_code"] for r in data["records"]], [None, None])
        # wine-a is Removed. A wine type MAY have each state.
        status, body = self.post_beverage_type({"slug": "wine-a", "beverage_type_code": "44"})
        self.assertEqual((status, body), (200, {
            "ok": True, "slug": "wine-a", "beverage_type_code": "44",
            "beverage_types": {"4": 0, "44": 1}}))
        self.post_beverage_type({"slug": "wine-b", "beverage_type_code": "4"})
        data = json.loads(self.request("/api/dataset")[2])
        self.assertEqual(data["beverage_types"], {"4": 1, "44": 1})
        self.assertEqual([r["_beverage_type_code"] for r in data["records"]], ["4", "44"])
        # The body names the new value, so a repeated request gives the same result.
        body = self.post_beverage_type({"slug": "wine-a", "beverage_type_code": "44"})[1]
        self.assertEqual(body["beverage_types"], {"4": 1, "44": 1})
        body = self.post_beverage_type({"slug": "wine-a", "beverage_type_code": "4"})[1]
        self.assertEqual(body["beverage_types"], {"4": 2, "44": 0})
        status, body = self.post_beverage_type({"slug": "wine-a", "beverage_type_code": None})
        self.assertEqual((status, body["beverage_type_code"], body["beverage_types"]),
                         (200, None, {"4": 1, "44": 0}))
        self.assertEqual(self.post_beverage_type(
            {"slug": "wine-a", "beverage_type_code": None})[0], 200)
        data = json.loads(self.request("/api/dataset")[2])
        self.assertEqual([r["_beverage_type_code"] for r in data["records"]], ["4", None])

    def test_beverage_type_errors(self):
        cases = (({"slug": "wine-b", "beverage_type_code": 4}, 400, '"4", "44", or null'),
                 ({"slug": "wine-b", "beverage_type_code": "440"}, 400, '"4", "44", or null'),
                 ({"slug": "wine-b", "beverage_type_code": ""}, 400, '"4", "44", or null'),
                 ({"slug": "wine-b", "beverage_type_code": ["4"]}, 400, '"4", "44", or null'),
                 # A body with no key is an error, not a remove of the type.
                 ({"slug": "wine-b"}, 400, '"4", "44", or null'),
                 ({"slug": "", "beverage_type_code": "4"}, 400, "no wine slug"),
                 ({"beverage_type_code": "4"}, 400, "no wine slug"),
                 ({"slug": "wine-none", "beverage_type_code": "4"}, 404, "no wine"))
        for body, code, message in cases:
            with self.subTest(body=body):
                status, answer = self.post_beverage_type(body)
                self.assertEqual(status, code)
                self.assertIn(message, answer["error"])
        self.assertEqual(self.request("/api/dataset-beverage-type", "POST", b"not json")[0],
                         400)
        self.assertEqual(self.request("/api/dataset-beverage-type", "DELETE")[0], 503)
        self.assertEqual(json.loads(self.request("/api/dataset")[2])["beverage_types"],
                         {"4": 0, "44": 0})

    def test_unknown_route_is_not_found(self):
        self.assertEqual(self.request("/nothing")[0], 404)

    def test_head_sends_no_body(self):
        status, headers, body = self.request("/dataset", "HEAD")
        self.assertEqual(status, 200)
        self.assertEqual(body, "")
        self.assertGreater(int(headers["Content-Length"]), 0)

    def test_database_is_opened_read_only(self):
        conn = LAB.open_database(self.db)
        with self.assertRaises(sqlite3.OperationalError):
            conn.execute("DELETE FROM wine_catalog")
        conn.close()

    def test_old_schema_version_names_the_upgrade_command(self):
        conn = sqlite3.connect(self.db)
        conn.execute("PRAGMA user_version = 3")
        conn.close()
        with self.assertRaisesRegex(LAB.ConfigError, "pipeline/labdb.py"):
            LAB.open_database(self.db)
        status, _, body = self.request("/api/dataset")
        self.assertEqual(status, 503)
        self.assertIn("schema version 3", json.loads(body)["error"])
        self.assertEqual(self.post_state("wine-b", "disable")[0], 503)

    def test_state_counts_follow_the_order_of_the_states(self):
        conn = LAB.open_database(self.db)
        self.assertEqual(list(LAB.state_counts(conn).items()),
                         [("Active", 1), ("Disabled", 0), ("Removed", 1)])
        conn.close()

    def test_missing_database_is_an_error(self):
        with self.assertRaisesRegex(LAB.ConfigError, "no database at"):
            LAB.open_database(str(self.root / "none.sqlite3"))

    def test_config_resolves_the_database_against_rootdir(self):
        config = self.root / "config.yaml"
        config.write_text("rootdir: %s\ndatabase_file: data/lab.sqlite3\n" % self.root)
        self.assertEqual(LAB.load_config(str(config)), str(self.root / "data" / "lab.sqlite3"))
        config.write_text("rootdir: %s\n" % self.root)
        with self.assertRaisesRegex(LAB.ConfigError, "database_file"):
            LAB.load_config(str(config))

    def test_the_website_import_routes_and_the_change_times(self):
        import website_import_routes
        saved, website_import_routes.WORK = website_import_routes.WORK, str(self.root / "work")
        try:
            status, _, body = self.request("/api/website-import")
            self.assertEqual((status, json.loads(body)), (200, {"state": "none"}))
            status, headers, _ = self.request("/website-import.js")
            self.assertEqual((status, headers["Content-Type"]),
                             (200, "text/javascript; charset=utf-8"))
            self.assertEqual(self.request("/api/website-import", method="POST")[0], 405)
        finally:
            website_import_routes.WORK = saved
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("UPDATE wine_catalog SET website_modified_at = "
                         "'2026-09-22T15:36:48.000Z' WHERE wine_slug = 'wine-b'")
        conn.close()
        records = {r["slug"]: r for r in json.loads(self.request("/api/dataset")[2])["records"]}
        self.assertEqual(records["wine-b"]["_website_modified_at"], "2026-09-22T15:36:48.000Z")
        self.assertRegex(records["wine-b"]["_modified_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    # The image descriptions: plan 26.
    def link_image(self, slug, sha256, image_type="main"):
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("INSERT OR IGNORE INTO image (sha256, folder, extension) "
                         "VALUES (?, 'main', 'png')", (sha256,))
            if slug:
                conn.execute("INSERT INTO wine_image (wine_slug, image_type, sha256, "
                             "source_name, match_method) VALUES (?, ?, ?, 'b.webp', 'test')",
                             (slug, image_type, sha256))
        conn.close()

    def post_description(self, sha256, values):
        status, _, body = self.request("/api/image-description", "POST", json.dumps(
            {"sha256": sha256, "values": values}).encode())
        return status, json.loads(body)

    def test_the_image_description_route_sets_values_by_hand(self):
        sha = "a" * 64
        self.link_image("wine-b", sha)
        status, answer = self.post_description(sha, {"package_type": "tetra_pak"})
        self.assertEqual(status, 200)
        row = answer["description"]
        self.assertEqual((row["package_type"], row["subject_scope"], row["created_by"],
                          row["vlm_at"]), ("tetra_pak", None, "manual", None))
        status, answer = self.post_description(sha, {"package_view": "back",
                                                     "content_roles": ["back_label"]})
        row = answer["description"]
        self.assertEqual((row["package_type"], row["package_view"], row["content_roles"]),
                         ("tetra_pak", "back", ["back_label"]))
        status, answer = self.post_description(sha, {"package_type": None})
        self.assertIsNone(answer["description"]["package_type"])
        data = json.loads(self.request("/api/dataset")[2])
        self.assertTrue(data["image_description_editor"])
        self.assertEqual(data["image_descriptions"][sha]["package_view"], "back")

    def test_the_image_description_route_refuses_a_bad_request(self):
        linked, loose = "b" * 64, "c" * 64
        self.link_image("wine-b", linked, "full_back")
        self.link_image(None, loose)
        for sha, values, code in (("B" * 64, {"package_type": "can"}, 400),
                                  (linked, {}, 400), (linked, None, 400),
                                  (linked, {"package_type": "carton"}, 400),
                                  (linked, {"color": "red"}, 400),
                                  (linked, {"content_roles": ["unknown", "back_label"]}, 400),
                                  (loose, {"package_type": "can"}, 404)):
            with self.subTest(sha=sha[:1], values=values):
                self.assertEqual(self.post_description(sha, values)[0], code)
        self.assertEqual(self.post_description(linked, {"package_view": "back"})[0], 200)
        self.assertEqual(json.loads(self.request("/api/dataset")[2])["image_descriptions"]
                         [linked]["package_view"], "back")

    def test_the_watcher_starts_only_with_watch_true(self):
        config = self.root / "config.yaml"
        started = []
        with mock.patch.object(LAB.subprocess, "Popen",
                               lambda args, **kw: started.append(args) or "process"), \
                mock.patch.object(LAB, "WATCHER_LOG", str(self.root / "w.log")):
            for text in ("database_file: x\n", "image_description:\n  watch: false\n",
                         "image_description: on\n"):
                config.write_text(text)
                self.assertIsNone(LAB.start_watcher(str(config)))
            self.assertIsNone(LAB.start_watcher(str(self.root / "missing.yaml")))
            config.write_text("image_description:\n  watch: true\n")
            self.assertEqual(LAB.start_watcher(str(config)), "process")
        self.assertEqual(len(started), 1)
        self.assertEqual(started[0][1:5], [LAB.WATCHER, "--watch", "--parent-pid",
                                           str(LAB.os.getpid())])

    def test_stop_watcher_ends_the_process(self):
        import subprocess
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        LAB.stop_watcher(process)
        self.assertIsNotNone(process.poll())
        LAB.stop_watcher(process)
        LAB.stop_watcher(None)

    def test_the_status_route_of_the_watcher(self):
        import image_descriptions
        path = str(self.root / "status.json")
        sha = "d" * 64
        self.link_image("wine-b", sha)
        with mock.patch.object(image_descriptions, "STATUS_PATH", path):
            status, _, body = self.request("/api/image-description-status")
            answer = json.loads(body)
            self.assertEqual(status, 200)
            self.assertEqual((answer["state"], answer["linked"], answer["pending"]),
                             ("stopped", 1, 1))
            image_descriptions.write_status({"pid": LAB.os.getpid(), "state": "working",
                                             "sha256": sha, "vlm": "vlm-a",
                                             "seconds_per_image": 2.5})
            answer = json.loads(self.request("/api/image-description-status")[2])
            self.assertEqual((answer["state"], answer["slug"], answer["seconds_per_image"]),
                             ("working", "wine-b", 2.5))
        self.assertEqual(self.request("/api/image-description-status", "POST")[0], 503)

    def test_the_status_route_sends_the_log_tail_on_request(self):
        # Plan 49: the dialog of the watcher asks `log=30`.
        import image_descriptions
        log = self.root / "w.log"
        log.write_text("".join("2026-09-26T07:00:%02dZ line %d\n" % (i, i) for i in range(40)),
                       encoding="utf-8")
        with mock.patch.object(image_descriptions, "STATUS_PATH",
                               str(self.root / "status.json")), \
                mock.patch.object(LAB, "WATCHER_LOG", str(log)):
            answer = json.loads(self.request("/api/image-description-status")[2])
            self.assertNotIn("log", answer)
            status, _, body = self.request("/api/image-description-status?log=30")
            self.assertEqual(status, 200)
            answer = json.loads(body)
            self.assertEqual((len(answer["log"]), answer["log"][-1]),
                             (30, "2026-09-26T07:00:39Z line 39"))
            self.assertEqual(answer["log_file"], LAB.os.path.relpath(str(log), LAB.ROOT))
            for bad in ("0", "201", "x", "-1"):
                status, _, body = self.request("/api/image-description-status?log=" + bad)
                self.assertEqual(status, 400, bad)
                self.assertIn("`log` MUST be a whole number", json.loads(body)["error"])

    def test_the_route_of_the_failed_details(self):
        import image_descriptions
        with mock.patch.object(image_descriptions, "STATUS_PATH",
                               str(self.root / "status.json")), \
                mock.patch.object(LAB, "WATCHER_LOG", str(self.root / "w.log")):
            status, _, body = self.request("/api/image-detail-failures")
        self.assertEqual(status, 200)
        answer = json.loads(body)
        self.assertEqual((answer["max_attempts"], answer["failures"]), (3, []))

    # Plan 24: the Testset page is at /testset, and / goes to the Dataset page.

    def test_root_redirects_to_the_dataset_page(self):
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None

        opener = urllib.request.build_opener(NoRedirect)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            opener.open(self.base + "/")
        self.assertEqual(caught.exception.code, 302)
        self.assertEqual(caught.exception.headers["Location"], "/dataset")
        self.assertEqual(self.request("/")[0], 200)

    def test_the_testset_page_is_on(self):
        status, headers, body = self.request("/testset")
        self.assertEqual(status, 200)
        self.assertEqual(body, lab_pages.page("testset.html"))
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn('class="on" href="/testset"', body)
        # The database of this test holds no test set.
        status, _, body = self.request("/api/testset")
        self.assertEqual(status, 404)
        self.assertIn("no test set", json.loads(body)["error"])

    # The raw VLM reply of the dialog "Image description" (owner message of about 17:58).

    def test_the_raw_reply_route(self):
        import describe_images
        import image_descriptions
        route = "/api/image-description-reply?sha256="
        sha = "e" * 64
        self.link_image("wine-b", sha)
        self.assertEqual(self.request(route + "xyz")[0], 400)
        self.assertEqual(self.request(route + "f" * 64)[0], 404)
        answer = json.loads(self.request(route + sha)[2])
        self.assertEqual((answer["found"], answer["reason"]),
                         (False, "the VLM has not filled this image"))
        conn = sqlite3.connect(self.db)
        with conn:
            image_descriptions.record_vlm(conn, sha, {
                "package_type": "can", "subject_scope": "full_package",
                "package_view": "front", "content_roles": ["front_label"],
                "presentation_mode": "on_package"}, "qwen3.5-9b-nvfp4", "Model")
        conn.close()
        record = {"key": "k", "created": "t", "ms": 5, "request": {"prompt": []},
                  "answer": {"choices": [{"message": {"content": "{}"}}]}}
        with mock.patch.object(describe_images, "cached_reply", return_value=record):
            status, _, body = self.request(route + sha)
        answer = json.loads(body)
        self.assertEqual((status, answer["found"], answer["reply"], answer["ms"]),
                         (200, True, record["answer"], 5))
        with mock.patch.object(describe_images, "cached_reply", return_value=None):
            answer = json.loads(self.request(route + sha)[2])
        self.assertEqual((answer["found"], answer["reason"]),
                         (False, "no record in data/cache/ matches this image"))


if __name__ == "__main__":
    unittest.main()
