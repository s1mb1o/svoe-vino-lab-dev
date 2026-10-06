"""Check Embedding view freshness for data, configuration, files, and jobs."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from embedding_view_cache import EmbeddingViewCache
import embeddings


@contextmanager
def connect(path):
    with closing(sqlite3.connect(path)) as connection:
        with connection:
            yield connection


class EmbeddingViewCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "catalog.sqlite3"
        self.config = self.db.with_suffix(".yaml")
        self.config.write_text("first")
        with connect(self.db) as conn:
            conn.execute("CREATE TABLE items (name TEXT)")
            conn.execute("INSERT INTO items VALUES ('first')")
        self.spec = {"name": "sample", "model": "first"}
        entry = SimpleNamespace(summary=lambda: dict(self.spec))
        self.settings = SimpleNamespace(db_path=str(self.db), config_path=str(self.config),
                                         entries=[("sample", entry, None)])
        self.directory = Path(embeddings.entry_dir(self.db, "sample"))
        self.images = self.directory / embeddings.IMAGES
        self.images.mkdir(parents=True)
        self.index = self.directory / embeddings.INDEX
        self.index.write_text("first")
        self.vector = self.directory / "vectors-12345678.npy"
        self.vector.write_bytes(b"first")
        self.cache = EmbeddingViewCache()
        self.addCleanup(self.cache.close)
        self.job = Mock(return_value={"state": "done"})
        self.queue = Mock(return_value=None)
        self.reader = Mock(side_effect=self.read_view)

    def read_view(self, settings, name=None):
        with connect(settings.db_path) as conn:
            rows = [row[0] for row in conn.execute("SELECT name FROM items")]
        record = {"name": name or "sample", "index_error": None,
                  "index": self.index.read_text(), "images": sorted(p.name for p in self.images.iterdir()),
                  "vectors": self.vector.read_text() if self.vector.exists() else None,
                  "job": dict(self.job.return_value), "model": self.spec["model"]}
        if name is None:
            return {"embeddings": [record], "queue": self.queue.return_value,
                    "rows": rows, "unicode": "Вино"}
        return {"embedding": record, "rows": rows, "unicode": "Вино"}

    def get(self, name=None):
        return self.cache.get(self.settings, name, self.reader, self.job, self.queue)

    def test_exact_serialization_and_independent_views(self):
        original = json.dumps(self.read_view(self.settings), ensure_ascii=False)
        self.assertEqual(json.dumps(self.get(), ensure_ascii=False), original)
        changed = self.get()
        changed["embeddings"][0]["model"] = "changed"
        self.assertEqual(json.dumps(self.get(), ensure_ascii=False), original)
        self.assertEqual(self.reader.call_count, 1)

    def test_http_bytes_skip_json_decode_and_keep_exact_body(self):
        expected = json.dumps(self.read_view(self.settings), ensure_ascii=False).encode()
        first = self.cache.get(self.settings, None, self.reader, self.job,
                               self.queue, encode_json=True)
        with patch("embedding_view_cache.json.loads", side_effect=AssertionError("decoded body")):
            second = self.cache.get(self.settings, None, self.reader, self.job,
                                    self.queue, encode_json=True)
        self.assertEqual(first, expected)
        self.assertIs(second, first)
        self.assertEqual(self.reader.call_count, 1)

    def test_jobs_and_queue_are_checked_on_every_read(self):
        self.get()
        before = self.job.call_count
        self.get()
        self.assertGreater(self.job.call_count, before)
        self.job.return_value = {"state": "running", "pid": 123}
        self.assertEqual(self.get()["embeddings"][0]["job"], self.job.return_value)
        self.queue.return_value = {"state": "running", "index": 1}
        self.assertEqual(self.get()["queue"], self.queue.return_value)
        self.assertEqual(self.reader.call_count, 3)

    def test_normal_and_wal_commits_are_visible(self):
        self.get()
        with connect(self.db) as conn:
            conn.execute("INSERT INTO items VALUES ('second')")
        self.assertEqual(len(self.get()["rows"]), 2)
        with connect(self.db) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            self.get()
            before = self.db.stat()
            conn.execute("INSERT INTO items VALUES ('third')")
            conn.commit()
            after = self.db.stat()
            self.assertEqual((before.st_size, before.st_mtime_ns),
                             (after.st_size, after.st_mtime_ns))
            self.assertEqual(len(self.get()["rows"]), 3)

    def test_index_replacement_and_image_names_are_checked(self):
        self.get()
        before = self.index.stat()
        replacement = self.index.with_suffix(".new")
        replacement.write_text("other")
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(self.index)
        self.assertEqual(self.get()["embeddings"][0]["index"], "other")
        (self.images / "new.png").write_bytes(b"png")
        self.assertEqual(self.get()["embeddings"][0]["images"], ["new.png"])
        (self.images / "new.png").unlink()
        self.assertEqual(self.get()["embeddings"][0]["images"], [])

    def test_entry_vectors_change_without_directory_change(self):
        self.get("sample")
        before = self.vector.stat()
        self.vector.write_bytes(b"other")
        os.utime(self.vector, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(self.get("sample")["embedding"]["vectors"], "other")
        self.vector.unlink()
        self.assertIsNone(self.get("sample")["embedding"]["vectors"])

    def test_effective_settings_prevent_reuse_after_a_loader_race(self):
        self.get()
        self.config.write_text("other")
        self.get()
        self.spec["model"] = "other"
        self.assertEqual(self.get()["embeddings"][0]["model"], "other")
        self.assertEqual(self.reader.call_count, 3)

    def test_change_during_read_prevents_insertion(self):
        def read(settings):
            view = self.read_view(settings)
            self.index.write_text(self.index.read_text() + "next")
            return view
        self.reader.side_effect = read
        self.get()
        self.get()
        self.assertEqual(self.reader.call_count, 2)

    def test_concurrent_misses_build_one_view(self):
        with ThreadPoolExecutor(max_workers=8) as executor:
            answers = list(executor.map(lambda _: self.get(), range(16)))
        self.assertTrue(all(answer == answers[0] for answer in answers))
        self.assertEqual(self.reader.call_count, 1)

    def test_oversized_or_failed_index_views_are_not_retained(self):
        self.cache.max_bytes = 1
        self.get()
        self.get()
        self.assertEqual(self.reader.call_count, 2)
        self.cache.max_bytes = 1024 * 1024
        view = self.read_view(self.settings)
        view["embeddings"][0]["index_error"] = "cannot read index"
        self.reader.side_effect = None
        self.reader.return_value = view
        self.get()
        self.get()
        self.assertEqual(self.reader.call_count, 4)
        self.assertIsNone(self.cache._cached)

    def test_probe_error_preserves_the_original_reader(self):
        self.get()
        with patch.object(self.cache, "_inputs", side_effect=PermissionError):
            self.assertEqual(self.get()["rows"], ["first"])
        self.assertEqual(self.reader.call_count, 2)

    def test_database_replacement_is_visible(self):
        self.get()
        before = self.db.stat()
        replacement = self.db.with_suffix(".new")
        replacement.write_bytes(self.db.read_bytes())
        with connect(replacement) as conn:
            conn.execute("UPDATE items SET name = 'other'")
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(self.db)
        self.assertEqual(self.get()["rows"], ["other"])


if __name__ == "__main__":
    unittest.main()
