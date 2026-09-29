"""Plan 89: the edited name `name_patched` of a card and `POST /api/wine-name`."""
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import cluster_rerank  # noqa: E402
import clusters  # noqa: E402
import import_website  # noqa: E402
import lab_server as LAB  # noqa: E402
import labdb  # noqa: E402

WINES = [
    ("wine-b", "Вино b", "Винодельня", "Белое", "Соломенный", "Крым",
     "Алиготе", "Описание b", "b.webp", "Active", None),
    ("wine-a", "Вино a", "Винодельня", "Красное", "Рубиновый", "Кубань",
     None, "Описание a", "a.webp", "Removed", "import"),
]


class WineNameTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = str(Path(self.directory.name) / "catalog.sqlite3")
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

    def post(self, body):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self.base + "/api/wine-name", method="POST", data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def row(self, slug):
        with closing(sqlite3.connect(self.db)) as conn:
            return conn.execute("SELECT name, name_patched FROM wine_catalog "
                                "WHERE wine_slug = ?", (slug,)).fetchone()

    def records(self):
        with urllib.request.urlopen(self.base + "/api/dataset") as response:
            return {r["slug"]: r for r in json.loads(response.read())["records"]}

    def test_a_save_sets_name_patched_and_keeps_name(self):
        status, answer = self.post({"slug": "wine-b", "name": "Вино b 2023"})
        self.assertEqual(status, 200)
        self.assertEqual(answer, {"slug": "wine-b", "name": "Вино b 2023",
                                  "catalog_name": "Вино b", "name_patched": True})
        self.assertEqual(self.row("wine-b"), ("Вино b", "Вино b 2023"))

    def test_the_catalogue_name_clears_the_edit(self):
        self.post({"slug": "wine-b", "name": "Вино b 2023"})
        status, answer = self.post({"slug": "wine-b", "name": " Вино b "})
        self.assertEqual(status, 200)
        self.assertEqual(answer["name_patched"], False)
        self.assertEqual(answer["name"], "Вино b")
        self.assertEqual(self.row("wine-b"), ("Вино b", None))

    def test_the_name_loses_its_outer_white_space(self):
        self.post({"slug": "wine-b", "name": "  Вино b 2024\n"})
        self.assertEqual(self.row("wine-b"), ("Вино b", "Вино b 2024"))

    def test_a_bad_name_is_refused(self):
        for name in ("", "   ", None, 5, "x" * (LAB.MAX_NAME + 1)):
            status, answer = self.post({"slug": "wine-b", "name": name})
            self.assertEqual(status, 400, name)
            self.assertIn("error", answer)
        status, _ = self.post({"slug": "wine-b", "name": "x" * LAB.MAX_NAME})
        self.assertEqual(status, 200)

    def test_an_unknown_slug_is_404(self):
        status, _ = self.post({"slug": "wine-z", "name": "Вино"})
        self.assertEqual(status, 404)
        status, _ = self.post({"name": "Вино"})
        self.assertEqual(status, 400)

    def test_a_removed_wine_allows_an_edit(self):
        status, _ = self.post({"slug": "wine-a", "name": "Вино a 2021"})
        self.assertEqual(status, 200)
        self.assertEqual(self.row("wine-a"), ("Вино a", "Вино a 2021"))

    def test_the_dataset_record_holds_the_name_in_use(self):
        self.post({"slug": "wine-b", "name": "Вино b 2023"})
        records = self.records()
        self.assertEqual(records["wine-b"]["name"], "Вино b 2023")
        self.assertEqual(records["wine-b"]["_catalog_name"], "Вино b")
        self.assertIs(records["wine-b"]["_name_patched"], True)
        self.assertEqual(records["wine-a"]["name"], "Вино a")
        self.assertEqual(records["wine-a"]["_catalog_name"], "Вино a")
        self.assertIs(records["wine-a"]["_name_patched"], False)

    def test_an_edit_sets_modified_at(self):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("UPDATE wine_catalog SET modified_at = NULL")
        self.post({"slug": "wine-b", "name": "Вино b 2023"})
        with closing(sqlite3.connect(self.db)) as conn:
            changed = dict(conn.execute("SELECT wine_slug, modified_at FROM wine_catalog"))
        self.assertRegex(changed["wine-b"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertIsNone(changed["wine-a"])

    def test_the_readers_read_the_name_in_use(self):
        self.post({"slug": "wine-b", "name": "Вино b 2023"})
        with closing(sqlite3.connect(self.db)) as conn:
            view = conn.execute("SELECT wine_slug, name FROM matcher_wine").fetchall()
            catalog = clusters._catalog(conn)
        self.assertEqual(view, [("wine-b", "Вино b 2023")])
        self.assertEqual(catalog["wine-b"]["name"], "Вино b 2023")
        self.assertEqual(cluster_rerank.catalogue_names(self.db)["wine-b"], "Вино b 2023")

    def test_a_website_import_keeps_the_edit(self):
        self.post({"slug": "wine-b", "name": "Вино b 2023"})
        conn = labdb.connect(self.db)
        try:
            snapshot = import_website.State(conn).digest()
        finally:
            conn.close()
        key = "text:wine-b:name"
        # The keys of `import_website.compare` that `write` reads.
        diff = {"problems": [], "changes": [], "stale": [], "times": {}, "website": 1,
                "images": 0, "requests": 0, "bytes": 0, "refused": 0, "unchanged": 1,
                "snapshot": snapshot, "conflicts": [
                    {"id": key, "slug": "wine-b", "kind": "text", "field": "name",
                     "state": "Active", "name": "Вино b", "database": "Вино b",
                     "website": "Вино b сайт"}]}
        import_website.write(self.db, diff, {}, {"conflicts": {key: "website"}},
                             segmenter=object(), log=lambda *_: None)
        self.assertEqual(self.row("wine-b"), ("Вино b сайт", "Вино b 2023"))
        self.assertEqual(self.records()["wine-b"]["name"], "Вино b 2023")


if __name__ == "__main__":
    unittest.main()
