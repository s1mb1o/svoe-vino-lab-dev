"""The photo moves of plan 95: `POST /api/dataset-photo-move` and `photo_moves.move`."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tests"))
import alternatives  # noqa: E402
import lab_server as LAB  # noqa: E402
import labdb  # noqa: E402
from test_manual_wines import form, picture, sha  # noqa: E402
from test_patches import WINES, DownSam3, FakeSam3  # noqa: E402


class PhotoMoveRouteTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = str(Path(self.directory.name) / "lab.sqlite3")
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.executemany("INSERT INTO wine_catalog (%s) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
                             % ", ".join(LAB.CATALOG_COLUMNS), WINES)
        conn.close()
        self.sam3 = FakeSam3()
        self.server = LAB.make_server(self.db, port=0, segmenter=self.sam3)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def request(self, path, method="GET", body=None, json_body=None):
        headers = {}
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, method=method, data=body,
                                     headers=headers)
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def rows(self, slug="__my-wine"):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute("SELECT image_type, sha256 FROM wine_image WHERE "
                                "wine_slug = ? ORDER BY rowid", (slug,)).fetchall()
        finally:
            conn.close()

    def add_wine(self):
        status, out = self.request("/api/wine", "POST", json_body=form())
        self.assertEqual(status, 200, out)
        return sha(picture())

    def add_alternative(self, colour, slug="__my-wine"):
        from test_patches import picture as coloured
        data = coloured(colour=colour)
        status, out = self.request("/api/dataset-alternative?slug=%s&name=p.png"
                                   % urllib.parse.quote(slug), "POST", data)
        self.assertEqual(status, 200, out)
        return sha(data)

    def move(self, digest, source, target, slug="__my-wine"):
        return self.request("/api/dataset-photo-move", "POST", json_body={
            "slug": slug, "sha256": digest, "from": source, "to": target})

    def test_additional_to_main_swaps_the_old_main(self):
        main = self.add_wine()
        photo = self.add_alternative((10, 120, 30))
        status, out = self.move(photo, "additional", "main")
        self.assertEqual(status, 200, out)
        self.assertEqual(out["swapped"], main)
        rows = self.rows()
        self.assertIn(("main", photo), rows)
        self.assertEqual(rows[-1], ("full_front", main))
        self.assertNotIn(photo, [digest for kind, digest in rows if kind != "main"])
        self.assertTrue(out["record"]["main_image_url"])
        self.assertEqual([item["sha256"] for item in out["record"]["_alternatives"]], [main])

    def test_additional_to_main_of_a_wine_with_no_main(self):
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("DELETE FROM wine_image")
        conn.close()
        photo = self.add_alternative((10, 120, 30), slug="wine-b")
        status, out = self.move(photo, "additional", "main", slug="wine-b")
        self.assertEqual(status, 200, out)
        self.assertIsNone(out["swapped"])
        self.assertEqual(self.rows("wine-b"), [("main", photo)])
        conn = labdb.connect(self.db)
        try:
            self.assertTrue(alternatives.has_current_cuts(conn, photo, "full"))
        finally:
            conn.close()

    def test_main_to_additional_leaves_no_main(self):
        main = self.add_wine()
        status, out = self.move(main, "main", "additional")
        self.assertEqual(status, 200, out)
        self.assertEqual(self.rows(), [("full_front", main)])
        self.assertIsNone(out["record"].get("main_image_url"))

    def test_additional_to_patched_and_back(self):
        self.add_wine()
        first = self.add_alternative((10, 120, 30))
        second = self.add_alternative((20, 20, 160))
        self.assertEqual(self.move(first, "additional", "patched")[0], 200)
        status, out = self.move(second, "additional", "patched")
        self.assertEqual(status, 200, out)
        self.assertEqual(out["swapped"], first)
        rows = self.rows()
        self.assertIn(("main_patched", second), rows)
        self.assertEqual(rows[-1], ("full_front", first))
        status, out = self.move(second, "patched", "additional")
        self.assertEqual(status, 200, out)
        self.assertNotIn("main_patched", [kind for kind, _digest in self.rows()])
        self.assertEqual(self.rows()[-1], ("full_front", second))

    def test_a_photo_in_both_rows_loses_the_other_row(self):
        main = self.add_wine()
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("INSERT INTO wine_image VALUES ('__my-wine', 'label_back', ?, "
                         "'x.png', 'manual')", (main,))
        conn.close()
        status, out = self.move(main, "main", "additional")
        self.assertEqual(status, 200, out)
        self.assertEqual(self.rows(), [("label_back", main)])

    def test_sam3_down_moves_with_a_warning(self):
        self.server.segmenter = DownSam3()
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("INSERT INTO image VALUES (?, 'additional', 'png', 40, 80)",
                         ("a" * 64,))
            conn.execute("INSERT INTO wine_image VALUES ('wine-b', 'full_front', ?, "
                         "'x.png', 'manual')", ("a" * 64,))
        conn.close()
        path = Path(labdb.image_dir(self.db, "additional")) / ("a" * 64 + ".png")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(picture())
        status, out = self.move("a" * 64, "additional", "main", slug="wine-b")
        self.assertEqual(status, 200, out)
        self.assertIn("connection refused", out["warning"])
        self.assertEqual(self.rows("wine-b"), [("main", "a" * 64)])

    def test_bad_requests(self):
        main = self.add_wine()
        for source, target in (("main", "patched"), ("additional", "additional"),
                               ("additional", "label"), (None, "main")):
            with self.subTest(source=source, target=target):
                self.assertEqual(self.move(main, source, target)[0], 400)
        self.assertEqual(self.move(main, "additional", "main")[0], 404)
        self.assertEqual(self.move(main, "patched", "additional")[0], 404)
        self.assertEqual(self.move(main, "main", "additional", slug="no-wine")[0], 404)
        self.assertEqual(self.move("", "main", "additional")[0], 400)


if __name__ == "__main__":
    unittest.main()
