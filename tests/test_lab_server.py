import json
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

    def test_disabled_pages_keep_the_navigation(self):
        for route, name in (("/clusters", "Clusters"), ("/embedding", "Embeddings"),
                            ("/", "Testset"), ("/runs", "Runs")):
            status, _, body = self.request(route)
            self.assertEqual(status, 503, route)
            self.assertIn("The page %s is disabled for now." % name, body)
            for href, label in LAB.NAV:
                self.assertIn('href="%s">%s</a>' % (href, label), body)
            self.assertIn('class="on" href="%s"' % route, body)

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
