"""Check dataset payload freshness, live jobs, replacement, and memory limits."""

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
from dataset_payload_cache import DatasetPayloadCache


@contextmanager
def connect(path):
    with closing(sqlite3.connect(path)) as connection:
        with connection:
            yield connection


class DatasetPayloadCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "catalog.sqlite3"
        self.config = self.db.with_suffix(".yaml")
        self.config.write_text("first")
        with connect(self.db) as conn:
            conn.execute("CREATE TABLE items (name TEXT)")
            conn.execute("INSERT INTO items VALUES ('first')")
        self.cache = DatasetPayloadCache()
        self.addCleanup(self.cache.close)
        self.jobs = Mock(return_value={"wine": {"state": "running"}})
        self.reader = Mock(side_effect=self.read_view)

    @staticmethod
    def read_view(db, config):
        with connect(db) as conn:
            names = [row[0] for row in conn.execute("SELECT name FROM items")]
        return {"records": [{"name": name} for name in names],
                "selected": Path(config).read_text(), "unicode": "Вино"}

    def get(self):
        return self.cache.get(self.db, self.config, self.reader, self.jobs)

    def test_exact_bytes_and_live_job_states(self):
        original = self.read_view(self.db, self.config)
        original["new_wine_index"] = self.jobs.return_value
        self.assertEqual(self.get(), json.dumps(original, ensure_ascii=False).encode())
        self.jobs.return_value = {"wine": {"state": "done"}}
        value = json.loads(self.get())
        self.assertEqual(value["new_wine_index"], self.jobs.return_value)
        self.assertEqual(self.reader.call_count, 1)

    def test_empty_view_has_valid_json_and_exact_bytes(self):
        self.reader.side_effect = None
        self.reader.return_value = {}
        expected = json.dumps({"new_wine_index": self.jobs.return_value}, ensure_ascii=False).encode()
        self.assertEqual(self.get(), expected)
        self.assertEqual(self.get(), expected)

    def test_database_commit_is_visible(self):
        self.get()
        with connect(self.db) as conn:
            conn.execute("INSERT INTO items VALUES ('second')")
        self.assertEqual(len(json.loads(self.get())["records"]), 2)
        self.assertEqual(self.reader.call_count, 2)

    def test_wal_commit_is_visible_without_database_file_change(self):
        with connect(self.db) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            self.get()
            before = self.db.stat()
            conn.execute("INSERT INTO items VALUES ('second')")
            conn.commit()
            after = self.db.stat()
            self.assertEqual((before.st_size, before.st_mtime_ns), (after.st_size, after.st_mtime_ns))
            self.assertEqual(len(json.loads(self.get())["records"]), 2)

    def test_replacement_is_visible_with_equal_file_size_and_mtime(self):
        self.get()
        before = self.db.stat()
        replacement = self.db.with_suffix(".new")
        replacement.write_bytes(self.db.read_bytes())
        with connect(replacement) as conn:
            conn.execute("UPDATE items SET name = 'other'")
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(self.db)
        self.assertEqual(json.loads(self.get())["records"][0]["name"], "other")

    def test_config_change_and_missing_config_preserve_reader_behavior(self):
        self.get()
        before = self.config.stat()
        self.config.write_text("other")
        os.utime(self.config, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(json.loads(self.get())["selected"], "other")
        self.config.unlink()
        with self.assertRaises(FileNotFoundError):
            self.get()
        self.config.write_text("valid")
        self.assertEqual(json.loads(self.get())["selected"], "valid")

    def test_commit_during_read_prevents_insertion(self):
        def read(db, config):
            value = self.read_view(db, config)
            with connect(db) as conn:
                conn.execute("INSERT INTO items VALUES ('next')")
            return value
        self.reader.side_effect = read
        self.get()
        self.get()
        self.assertEqual(self.reader.call_count, 2)

    def test_concurrent_misses_read_once(self):
        with ThreadPoolExecutor(max_workers=8) as executor:
            answers = list(executor.map(lambda _: self.get(), range(16)))
        self.assertEqual(len(set(answers)), 1)
        self.assertEqual(self.reader.call_count, 1)
        self.assertEqual(self.jobs.call_count, 16)

    def test_oversized_payload_is_not_retained(self):
        self.cache.max_bytes = 1
        self.get()
        self.get()
        self.assertEqual(self.reader.call_count, 2)
        self.assertIsNone(self.cache._cached)

    def test_read_failure_is_not_cached(self):
        self.reader.side_effect = ValueError("invalid dataset")
        for _ in range(2):
            with self.assertRaisesRegex(ValueError, "invalid dataset"):
                self.get()
        self.reader.side_effect = self.read_view
        self.get()
        self.get()
        self.assertEqual(self.reader.call_count, 3)

    def test_stat_error_uses_existing_reader(self):
        self.get()
        with patch.object(self.cache, "_file", side_effect=PermissionError):
            self.assertEqual(json.loads(self.get())["selected"], "first")
        self.assertEqual(self.reader.call_count, 2)


if __name__ == "__main__":
    unittest.main()
