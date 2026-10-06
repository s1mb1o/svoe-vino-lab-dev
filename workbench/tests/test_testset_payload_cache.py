"""Check Testset response freshness, selection, errors, and memory limits."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from testset_payload_cache import TestsetPayloadCache, TESTSET_PAYLOAD_CACHE
import testset_routes
import testsets


@contextmanager
def connect(path):
    with closing(sqlite3.connect(path)) as connection:
        with connection:
            yield connection


class TestsetPayloadCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "catalog.sqlite3"
        with connect(self.db) as conn:
            conn.execute("CREATE TABLE items (name TEXT)")
            conn.execute("INSERT INTO items VALUES ('first')")
        self.cache = TestsetPayloadCache()
        self.addCleanup(self.cache.close)
        self.cards = Mock()
        self.reader = Mock(side_effect=self.read_view)
        self.patch = patch.object(testsets, "set_view", self.reader)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    @staticmethod
    def read_view(conn, set_name, cards):
        names = [row[0] for row in conn.execute("SELECT name FROM items")]
        return {"set": set_name, "rows": names, "unicode": "Вино"}

    def get(self, set_name="my"):
        return self.cache.get(self.db, set_name, sqlite3.connect, self.cards)

    def test_exact_immutable_bytes_reuse(self):
        with connect(self.db) as conn:
            expected = json.dumps(self.read_view(conn, "my", self.cards),
                                  ensure_ascii=False).encode()
        first = self.get()
        self.assertEqual(first, expected)
        self.assertIs(self.get(), first)
        self.assertEqual(self.reader.call_count, 1)

    def test_set_selection_and_reader_identity_are_checked(self):
        self.get("my")
        self.assertEqual(json.loads(self.get("other"))["set"], "other")
        self.assertIsNone(json.loads(self.get(None))["set"])
        self.cards = Mock()
        self.get(None)
        self.assertEqual(self.reader.call_count, 4)

    def test_normal_and_wal_commits_are_visible(self):
        self.get()
        with connect(self.db) as conn:
            conn.execute("INSERT INTO items VALUES ('second')")
        self.assertEqual(len(json.loads(self.get())["rows"]), 2)
        with connect(self.db) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            self.get()
            before = self.db.stat()
            conn.execute("INSERT INTO items VALUES ('third')")
            conn.commit()
            after = self.db.stat()
            self.assertEqual((before.st_size, before.st_mtime_ns),
                             (after.st_size, after.st_mtime_ns))
            self.assertEqual(len(json.loads(self.get())["rows"]), 3)

    def test_replacement_with_equal_size_and_mtime_is_visible(self):
        self.get()
        before = self.db.stat()
        replacement = self.db.with_suffix(".new")
        replacement.write_bytes(self.db.read_bytes())
        with connect(replacement) as conn:
            conn.execute("UPDATE items SET name = 'other'")
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(self.db)
        self.assertEqual(json.loads(self.get())["rows"], ["other"])

    def test_commit_during_read_prevents_insertion(self):
        def read(conn, set_name, cards):
            value = self.read_view(conn, set_name, cards)
            with connect(self.db) as writer:
                writer.execute("INSERT INTO items VALUES ('next')")
            return value
        self.reader.side_effect = read
        self.get()
        self.get()
        self.assertEqual(self.reader.call_count, 2)

    def test_concurrent_misses_build_one_response(self):
        with ThreadPoolExecutor(max_workers=8) as executor:
            answers = list(executor.map(lambda _: self.get(), range(16)))
        self.assertEqual(len(set(answers)), 1)
        self.assertEqual(self.reader.call_count, 1)

    def test_oversized_payload_is_not_retained(self):
        self.cache.max_bytes = 1
        self.get()
        self.get()
        self.assertEqual(self.reader.call_count, 2)
        self.assertIsNone(self.cache._cached)

    def test_reader_error_and_probe_error_preserve_behavior(self):
        self.reader.side_effect = testsets.TestsetError(404, "missing set")
        for _ in range(2):
            with self.assertRaisesRegex(testsets.TestsetError, "missing set"):
                self.get()
        self.reader.side_effect = self.read_view
        self.get()
        with patch.object(self.cache, "_signature", side_effect=sqlite3.DatabaseError):
            self.assertEqual(json.loads(self.get())["rows"], ["first"])
        self.assertEqual(self.reader.call_count, 4)

    def test_route_preserves_errors_and_head_bytes(self):
        from types import SimpleNamespace
        server = SimpleNamespace(db_path=self.db)
        with patch.object(testset_routes, "TESTSET_PAYLOAD_CACHE", self.cache):
            answer = testset_routes.respond(server, "HEAD", "/api/testset?set=my",
                                            lambda _: None, sqlite3.connect, self.cards)
            self.assertEqual(answer, (200, self.get(), testset_routes.JSON_TYPE, "no-store"))
            self.reader.side_effect = testsets.TestsetError(404, "missing set")
            answer = testset_routes.respond(server, "GET", "/api/testset?set=missing",
                                            lambda _: None, sqlite3.connect, self.cards)
            self.assertEqual(answer[:2], (404, {"error": "missing set"}))


class TestsetPayloadLiveMutationTest(unittest.TestCase):
    """Use HTTP fixtures to check edits after a cached response."""

    def setUp(self):
        import test_testset_routes as fixture
        self.fixture = fixture.TestsetRoutesTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.addCleanup(TESTSET_PAYLOAD_CACHE.close)

    def test_label_and_dataset_favorite_change_cached_response(self):
        self.fixture.get_view()
        code, answer = self.fixture.post("/api/testset-label", place="wine-a",
                                         file="01.jpg", label="negative")
        self.assertEqual(code, 200, answer)
        row = next(row for row in self.fixture.get_view()["rows"]
                   if row["slug"] == "wine-a")
        self.assertEqual(row["photos"][0]["entry"]["label"], "negative")
        code, body = self.fixture.request("/api/dataset-favorite", "POST",
                                          {"slug": "wine-a", "favorite": True})
        self.assertEqual(code, 200, body)
        row = next(row for row in self.fixture.get_view()["rows"]
                   if row["slug"] == "wine-a")
        self.assertTrue(row["_favorite"])


if __name__ == "__main__":
    unittest.main()
