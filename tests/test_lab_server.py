import hashlib
import json
import re
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path


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


class LabServerTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.executemany("INSERT INTO wine_catalog VALUES (?,?,?,?,?,?,?,?,?,?,?)", WINES)
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
        self.assertEqual((first["_barcodes"], first["_patched"]), ([], False))
        self.assertEqual(data["database_file"], self.db)
        self.assertEqual((data["patches"], data["barcodes"]), (0, 0))

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
            conn.execute("INSERT INTO image_derivative VALUES (?, ?, 'test', ?, 0, 0, ?, ?)",
                         (source, method, digest) + size)
        conn.close()
        return "/images/cropped/%s.png" % digest

    def test_api_dataset_sends_the_card_image(self):
        main_b = self.add_image("wine-b", "main", b"b main")
        self.add_image("wine-a", "main", b"a main")
        patched_a = self.add_image("wine-a", "main_patched", b"a patched", "png")
        self.add_image("wine-a", "front", b"a front")
        records = json.loads(self.request("/api/dataset")[2])["records"]
        self.assertEqual([(r["main_image_url"], r["main_image_type"],
                           r["main_image_match_method"]) for r in records],
                         [(main_b, "main", "manual"), (patched_a, "main_patched", "manual")])

    def test_api_dataset_sends_the_size_of_the_card_image(self):
        self.add_image("wine-b", "main", b"b main", size=(300, 900))
        self.add_image("wine-a", "main", b"a main", size=(100, 200))
        self.add_image("wine-a", "main_patched", b"a patched")
        records = json.loads(self.request("/api/dataset")[2])["records"]
        self.assertEqual([(r["main_image_width"], r["main_image_height"]) for r in records],
                         [(300, 900), (None, None)])

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

    def test_disabled_pages_keep_the_navigation(self):
        for route, name in (("/clusters", "Clusters"), ("/", "Testset"), ("/runs", "Runs")):
            status, _, body = self.request(route)
            self.assertEqual(status, 503, route)
            self.assertIn("The page %s is disabled for now." % name, body)
            for href, label in LAB.NAV:
                self.assertIn('href="%s">%s</a>' % (href, label), body)
            self.assertIn('class="on" href="%s"' % route, body)

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

    def test_old_embedding_routes_stay_disabled(self):
        for path in ("/api/embedding", "/img/embedding/a.png"):
            status, _, body = self.request(path)
            self.assertEqual(status, 503, path)
            self.assertIn("disabled for now", body)

    def test_pages_keep_the_navigation_order(self):
        # Dataset first, Embeddings second: owner message of 2026-09-25T06:50:29+0300.
        self.assertEqual([label for _, label in LAB.NAV][:2], ["Dataset", "Embeddings"])
        hrefs = [href for href, _ in LAB.NAV]
        pages = {name: lab_pages.page(name) for name in ("dataset.html", "embedding.html")}
        pages["/runs"] = self.request("/runs")[2]
        for name, body in pages.items():
            nav = re.search(r'<nav class="nav">(.*?)</nav>', body, re.S).group(1)
            self.assertEqual(re.findall(r'href="([^"]*)"', nav), hrefs, name)

    def test_other_api_routes_are_disabled(self):
        for path, method in (("/api/runs", "GET"), ("/api/rows", "GET"),
                             ("/api/dataset-validation", "GET"),
                             ("/api/dataset-barcode", "POST"),
                             ("/api/dataset-patch?slug=wine-a", "DELETE")):
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


if __name__ == "__main__":
    unittest.main()
