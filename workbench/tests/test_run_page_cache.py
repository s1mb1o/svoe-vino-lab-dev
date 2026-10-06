"""Check persisted run responses, live SQLite changes, and cache bounds."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import labdb
import lab_server
import run_page_cache as PC
import run_routes as RR


class RunPageCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = str(self.root / "lab.sqlite3")
        self.photo, self.main = [hashlib.sha256(value).hexdigest()
                                 for value in (b"photo", b"main")]
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.execute("INSERT INTO wine_catalog (wine_slug, name, producer, category, "
                         "color, region, description, csv_photo_name) "
                         "VALUES ('a', 'A', 'p', 'c', 'co', 'r', 'd', 'x.webp')")
            conn.executemany("INSERT INTO image (sha256, folder, extension) "
                             "VALUES (?, ?, 'webp')", [(self.photo, "testset"),
                                                       (self.main, "main")])
            conn.execute("INSERT INTO wine_image (wine_slug, image_type, sha256, "
                         "source_name, match_method) VALUES ('a', 'main', ?, 'x', 'manual')",
                         (self.main,))
        conn.close()
        self.runs = self.root / "runs"
        self.row = {"query_id": "q1", "image_sha256": self.photo, "slug": "a",
                    "label": "positive", "predicted_slug": "a", "rank_of_truth": 1,
                    "trace": [{"data": "complete trace"}],
                    "candidates": [{"slug": "a", "rank": 1, "score": .9,
                                    "items": ["complete item"]}]}
        self.write_run("run")
        PC._CACHE.clear()

    def tearDown(self):
        self.tmp.cleanup()

    def write_run(self, name):
        directory = self.runs / name
        directory.mkdir(parents=True)
        (directory / "run.json").write_text(json.dumps({"started": "old"}))
        (directory / "metrics.json").write_text(json.dumps({"positive": {"n": 1}}))
        (directory / "results.jsonl").write_text(json.dumps(self.row) + "\n")

    def read(self, name="run", callback=lab_server.card_images, **options):
        query = {"id": [name], **{key: [str(value)] for key, value in options.items()}}
        code, body, _, _ = RR.run_view(str(self.runs), self.db, query, callback)
        self.assertEqual(code, 200)
        return json.loads(body) if isinstance(body, bytes) else body

    def test_memory_and_disk_hits_skip_rows_and_image_queries(self):
        expected = self.read()
        for disk in (False, True):
            if disk:
                PC._CACHE.clear()
            with patch.object(RR, "_connect", side_effect=AssertionError("SQL lookup")), \
                    patch.object(RR.run_files, "run_rows",
                                 side_effect=AssertionError("row lookup")):
                self.assertEqual(self.read(), expected)
        self.assertNotIn("trace", expected["rows"][0])
        self.assertNotIn("items", expected["rows"][0]["candidates"][0])

    def test_client_mutations_cannot_change_the_saved_page(self):
        expected = self.read()
        other = self.read()
        other["rows"][0]["candidates"].clear()
        other["bottles"].clear()
        self.assertEqual(self.read(), expected)

    def test_wal_commits_refresh_image_locations(self):
        writer = sqlite3.connect(self.db)
        try:
            writer.execute("PRAGMA journal_mode=WAL")
            before = self.read()
            with writer:
                if hasattr(RR, "image_tags"):
                    RR.image_tags.add(writer, self.photo, "updated")
                writer.execute("UPDATE image SET folder='main' WHERE sha256=?", (self.photo,))
            after = self.read()
            self.assertNotEqual(before["rows"][0]["photo_url"], after["rows"][0]["photo_url"])
            if hasattr(RR, "image_tags"):
                self.assertEqual(after["rows"][0]["tags"], ["updated"])
                self.assertEqual(after["tag_names"], [{"tag": "updated", "images": 1}])
        finally:
            writer.close()

    def test_run_metadata_metrics_and_replaced_rows_are_fresh(self):
        self.read()
        directory = self.runs / "run"
        for name, old, new in [("run.json", b'"old"', b'"new"'),
                               ("metrics.json", b'"n": 1', b'"n": 2')]:
            path = directory / name
            stat = path.stat()
            path.write_bytes(path.read_bytes().replace(old, new))
            os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            page = self.read()
            if name == "run.json":
                self.assertEqual(page["run"]["started"], "new")
                self.assertEqual(page["head"]["started"], "new")
            else:
                self.assertEqual(page["metrics"]["positive"]["n"], 2)
                self.assertEqual(page["head"]["positive"], 2)
        path = directory / "results.jsonl"
        stat = path.stat()
        other = path.with_suffix(".new")
        other.write_bytes(path.read_bytes().replace(b'"predicted_slug": "a"',
                                                   b'"predicted_slug": "b"'))
        os.utime(other, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        other.replace(path)
        self.assertEqual(self.read()["rows"][0]["predicted_slug"], "b")

    def test_corrupt_page_falls_back_and_failed_lookups_are_not_saved(self):
        with patch.object(RR, "_connect", side_effect=sqlite3.OperationalError("busy")):
            self.assertIn("busy", self.read()["images_error"])
        directory = self.runs / ".row-index-cache" / "pages-v1"
        self.assertFalse(directory.exists())
        expected = self.read()
        PC._CACHE.clear()
        next(directory.glob("*.json")).write_text("invalid")
        self.assertEqual(self.read(), expected)

    def test_options_replace_one_page_per_run_and_memory_is_bounded(self):
        self.read()
        empty = self.read(q="absent", offset=1, limit=5, sort="path")
        self.assertEqual(empty["rows"], [])
        with patch.object(RR.run_files, "run_rows", side_effect=AssertionError("row lookup")):
            self.assertEqual(self.read(q="absent", offset=1, limit=5, sort="path"), empty)
        directory = self.runs / ".row-index-cache" / "pages-v1"
        self.assertEqual(len(list(directory.glob("*.json"))), 1)
        self.assertEqual(len(self.read()["rows"]), 1)
        for index in range(4):
            name = "run-" + str(index)
            self.write_run(name)
            self.read(name)
        self.assertLessEqual(len(PC._CACHE), PC._MAX_PAGES)
        self.assertLessEqual(sum(record[2] for record in PC._CACHE.values()), PC._MAX_BYTES)

    def test_custom_renderers_and_oversized_pages_stay_uncached(self):
        urls = ["first"]
        def render(conn):
            return {"a": {"main_image_url": urls[0]}}
        self.assertEqual(self.read(callback=render)["bottles"], {"a": "first"})
        urls[0] = "second"
        self.assertEqual(self.read(callback=render)["bottles"], {"a": "second"})
        key = PC.token(str(self.runs), "run", self.db, lab_server.card_images, ("large",))
        PC.store(key, {"images_error": None, "data": "x" * (PC._MAX_PAGE_BYTES + 1)})
        self.assertIsNone(PC.load(key))


if __name__ == "__main__":
    unittest.main()
