"""Check committed watcher counts and fresh watcher state."""

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
from watcher_count_cache import WatcherCountCache
import image_descriptions as descriptions


@contextmanager
def connect(path):
    with closing(sqlite3.connect(path)) as connection:
        with connection:
            yield connection


class WatcherCountCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "catalog.sqlite3"
        with connect(self.db) as conn:
            conn.execute("CREATE TABLE items (name TEXT)")
            conn.execute("INSERT INTO items VALUES ('first')")
        self.conn = sqlite3.connect(self.db)
        self.addCleanup(self.conn.close)
        self.cache = WatcherCountCache()
        self.addCleanup(self.cache.close)
        self.reader = Mock(side_effect=self.read_counts)
        self.readers = (self.reader,)

    @staticmethod
    def read_counts(conn, max_attempts):
        return {"linked": conn.execute("SELECT count(*) FROM items").fetchone()[0],
                "max_attempts_value": max_attempts}

    def get(self, max_attempts=3):
        return self.cache.get(self.conn, max_attempts, self.readers)

    def test_counts_are_equal_and_independent(self):
        expected = self.read_counts(self.conn, 3)
        self.assertEqual(self.get(), expected)
        changed = self.get()
        changed["linked"] = 999
        self.assertEqual(self.get(), expected)
        self.assertEqual(self.reader.call_count, 1)

    def test_max_attempts_and_reader_identity_are_checked(self):
        self.get()
        self.assertEqual(self.get(5)["max_attempts_value"], 5)
        self.readers = (Mock(side_effect=self.read_counts),)
        self.get(5)
        self.assertEqual(self.readers[0].call_count, 1)

    def test_normal_and_wal_commits_are_visible(self):
        self.get()
        with connect(self.db) as writer:
            writer.execute("INSERT INTO items VALUES ('second')")
        self.assertEqual(self.get()["linked"], 2)
        with connect(self.db) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            self.get()
            before = self.db.stat()
            writer.execute("INSERT INTO items VALUES ('third')")
            writer.commit()
            after = self.db.stat()
            self.assertEqual((before.st_size, before.st_mtime_ns),
                             (after.st_size, after.st_mtime_ns))
            self.assertEqual(self.get()["linked"], 3)

    def test_uncommitted_transactions_preserve_caller_data(self):
        self.get()
        self.conn.execute("INSERT INTO items VALUES ('second')")
        self.assertEqual(self.get()["linked"], 2)
        self.conn.rollback()
        self.assertEqual(self.get()["linked"], 1)

    def test_memory_databases_use_the_original_reader(self):
        with closing(sqlite3.connect(":memory:")) as memory:
            memory.execute("CREATE TABLE items (name TEXT)")
            for _ in range(2):
                self.assertEqual(self.cache.get(memory, 3, self.readers)["linked"], 0)
        self.assertEqual(self.reader.call_count, 2)

    def test_change_during_read_prevents_insertion(self):
        def read(conn, max_attempts):
            value = self.read_counts(conn, max_attempts)
            with connect(self.db) as writer:
                writer.execute("INSERT INTO items VALUES ('next')")
            return value
        self.reader.side_effect = read
        self.get()
        self.get()
        self.assertEqual(self.reader.call_count, 2)

    def test_replacement_is_visible_to_the_next_connection(self):
        self.get()
        self.conn.close()
        before = self.db.stat()
        replacement = self.db.with_suffix(".new")
        replacement.write_bytes(self.db.read_bytes())
        with connect(replacement) as writer:
            writer.execute("INSERT INTO items VALUES ('second')")
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(self.db)
        self.conn = sqlite3.connect(self.db)
        self.addCleanup(self.conn.close)
        self.assertEqual(self.get()["linked"], 2)

    def test_concurrent_connections_build_one_snapshot(self):
        def get(_):
            with closing(sqlite3.connect(self.db)) as conn:
                return self.cache.get(conn, 3, self.readers)
        with ThreadPoolExecutor(max_workers=8) as executor:
            answers = list(executor.map(get, range(16)))
        self.assertTrue(all(answer == answers[0] for answer in answers))
        self.assertEqual(self.reader.call_count, 1)

    def test_probe_error_and_size_limit_preserve_the_reader(self):
        self.get()
        with patch.object(self.cache, "_signature", side_effect=sqlite3.DatabaseError):
            self.assertEqual(self.get()["linked"], 1)
        self.cache.max_bytes = 1
        self.get()
        self.get()
        self.assertEqual(self.reader.call_count, 4)
        self.assertIsNone(self.cache._cached)

    def test_watcher_state_and_elapsed_time_stay_fresh(self):
        status = self.db.with_suffix(".status.json")
        stamp = "2026-10-06T00:00:00Z"
        value = {"state": "working", "pid": os.getpid(), "max_attempts": 3,
                 "running": [{"sha256": "a" * 64, "stage": "class", "started_at": stamp}]}
        status.write_text(json.dumps(value))
        age = {"seconds": 1}
        with patch.object(descriptions, "WATCHER_COUNT_CACHE", self.cache), \
                patch.object(descriptions, "counts", self.reader), \
                patch.object(descriptions.image_details, "counts", return_value={}), \
                patch.object(descriptions.label_descriptions, "counts", return_value={}), \
                patch.object(descriptions, "call_view", side_effect=lambda *args: {}), \
                patch.object(descriptions, "_seconds_between",
                             side_effect=lambda text, now: age["seconds"] if text == stamp else None):
            first = descriptions.watcher_status(self.conn, status)
            age["seconds"] = 2
            second = descriptions.watcher_status(self.conn, status)
            self.assertEqual(first["running"][0]["seconds"], 1)
            self.assertEqual(second["running"][0]["seconds"], 2)
            value["state"] = "idle"
            status.write_text(json.dumps(value))
            self.assertEqual(descriptions.watcher_status(self.conn, status)["state"], "idle")
            self.assertEqual(self.reader.call_count, 1)


if __name__ == "__main__":
    unittest.main()
