import importlib.util
import io
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/merge_competitor_testsets.py"
SPEC = importlib.util.spec_from_file_location("competitor_merge", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


# (set, place, file_name, sha256, label, source image, width, height)
ROWS = [
    # One source photo in two sizes; the sets give it two slugs and __null__.
    ("a-scored", "slug-a", "aaa-p1.webp", "a" * 64, "positive", "/r/a/p1.webp", 300, 400),
    ("b-provisional", "slug-b", "bbb-p1.jpg", "b" * 64, "positive", "/r/b/p1.jpg", 30, 40),
    ("b-provisional", "__null__", "bbb-p1.jpg", "b" * 64, "negative", "/r/b/p1.jpg", 30, 40),
    # The same bytes under another file name, at the same place.
    ("c-provisional", "slug-a", "aaa-q-000001.webp", "a" * 64, "positive",
     "/r/c/q-000001.webp", 300, 400),
    # A photo that one set alone holds, in the Drawer.
    ("c-provisional", "__drawer__", "ccc-p2.jpg", "c" * 64, "unusable", "/r/c/p2.jpg", 10, 10),
]


class CompetitorMergeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.db = str(root / "catalog" / "catalog.sqlite3")
        os.makedirs(os.path.dirname(self.db))
        self.snapshot = root / "snapshot"
        conn = MODULE.labdb.connect(self.db, create=True)
        manifests = {}
        for set_name, place, name, digest, label, source, width, height in ROWS:
            conn.execute("INSERT OR IGNORE INTO image (sha256, folder, extension, width, "
                         "height) VALUES (?, 'testset', 'jpg', ?, ?)", (digest, width, height))
            conn.execute("INSERT OR IGNORE INTO test_set (set_name, source_dir) VALUES (?, ?)",
                         (set_name, str(self.snapshot / set_name)))
            conn.execute("INSERT INTO test_photo (set_name, place, file_name, sha256, label, "
                         "extra) VALUES (?, ?, ?, ?, ?, ?)",
                         (set_name, place, name, digest, label, json.dumps({"tier": "x"})))
            manifests.setdefault(set_name, []).append(
                {"place": place, "file_name": name, "source_image_path": source})
        conn.execute("INSERT INTO test_set (set_name, source_dir) VALUES ('my', '/elsewhere')")
        conn.commit()
        conn.close()
        for set_name, rows in manifests.items():
            (self.snapshot / set_name).mkdir(parents=True)
            (self.snapshot / set_name / "manifest.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in rows))

    def tearDown(self):
        self.temp.cleanup()

    def run_main(self, *extra):
        out = io.StringIO()
        with redirect_stdout(out):
            MODULE.main(["--db", self.db, "--snapshot", str(self.snapshot), *extra])
        return json.loads(out.getvalue())

    def test_merge_keeps_every_place_and_removes_the_sources(self):
        report = self.run_main()
        self.assertEqual(["a-scored", "b-provisional", "c-provisional"], report["source_sets"])
        self.assertEqual(2, report["photos"])
        self.assertEqual(1, report["photos_in_more_than_one_place"])
        self.assertTrue(os.path.isfile(report["backup"]))
        conn = sqlite3.connect(self.db)
        rows = conn.execute("SELECT place, file_name, sha256, label FROM test_photo "
                            "WHERE set_name = 'competitors' ORDER BY place").fetchall()
        # The largest copy stays and keeps one file name at each place.
        self.assertEqual([
            ("__drawer__", "ccc-p2.jpg", "c" * 64, "unusable"),
            ("__null__", "aaa-p1.webp", "a" * 64, "negative"),
            ("slug-a", "aaa-p1.webp", "a" * 64, "positive"),
            ("slug-b", "aaa-p1.webp", "a" * 64, "positive"),
        ], rows)
        extra = json.loads(conn.execute(
            "SELECT extra FROM test_photo WHERE set_name = 'competitors' AND "
            "place = 'slug-a'").fetchone()[0])
        self.assertEqual(["a-scored", "c-provisional"],
                         [r["set_name"] for r in extra["merged_from"]])
        self.assertEqual(["competitors", "my"], [r[0] for r in conn.execute(
            "SELECT set_name FROM test_set ORDER BY set_name")])
        conn.close()

    def test_dry_run_writes_nothing(self):
        report = self.run_main("--dry-run")
        self.assertEqual(4, report["rows"])
        conn = sqlite3.connect(self.db)
        self.assertEqual(5, conn.execute("SELECT count(*) FROM test_photo").fetchone()[0])
        conn.close()

    def test_label_conflict_at_one_place_stops_the_merge(self):
        rows = [
            {"set_name": "a", "place": "s", "file_name": "f", "sha256": "1", "label": "positive",
             "marked_delete": 0, "extra": None, "area": 1, "stem": "p"},
            {"set_name": "b", "place": "s", "file_name": "g", "sha256": "2", "label": "unusable",
             "marked_delete": 0, "extra": None, "area": 1, "stem": "p"},
        ]
        with self.assertRaises(MODULE.MergeError):
            MODULE.merge(rows)


if __name__ == "__main__":
    unittest.main()
