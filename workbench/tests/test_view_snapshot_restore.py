"""Check response restoration across connections and WAL commits."""

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from embedding_view_cache import EmbeddingViewCache
from cluster_view_cache import ClusterViewCache
import test_embedding_view_cache as fixture


class ViewSnapshotRestoreTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.EmbeddingViewCacheTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.directory = Path(self.fixture.tmp.name) / "responses"
        self.reads = 0
        self.caches = []
        self.addCleanup(lambda: [cache.close() for cache in self.caches])

    def reader(self, settings, name=None):
        self.reads += 1
        return self.fixture.read_view(settings, name)

    def job(self, directory):
        return dict(self.fixture.job.return_value)

    def queue(self):
        return self.fixture.queue.return_value

    def cache(self, cls=EmbeddingViewCache):
        value = cls(disk_kind="test-view-v1", cache_directory=self.directory)
        self.caches.append(value)
        return value

    def get(self, cache):
        return cache.get(self.fixture.settings, None, self.reader, self.job,
                         self.queue, encode_json=True)

    def test_new_connection_restores_exact_bytes_without_rebuilding(self):
        first = self.cache()
        body = self.get(first)
        first.close()
        self.assertEqual(self.get(self.cache()), body)
        self.assertEqual(self.reads, 1)

    def test_cluster_connection_local_version_does_not_enter_disk_key(self):
        first = self.cache(ClusterViewCache)
        self.get(first)
        with closing(sqlite3.connect(self.fixture.db)) as writer:
            writer.execute("INSERT INTO items VALUES ('second')")
            writer.commit()
        body = self.get(first)
        first.close()
        self.assertEqual(self.get(self.cache(ClusterViewCache)), body)
        self.assertEqual(self.reads, 2)

    def test_wal_commit_invalidates_saved_bytes_without_database_file_change(self):
        with closing(sqlite3.connect(self.fixture.db)) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            first = self.cache()
            self.get(first)
            before = self.fixture.db.stat()
            first.close()
            writer.execute("INSERT INTO items VALUES ('second')")
            writer.commit()
            after = self.fixture.db.stat()
            self.assertEqual((before.st_size, before.st_mtime_ns),
                             (after.st_size, after.st_mtime_ns))
            self.assertEqual(json.loads(self.get(self.cache()))["rows"], ["first", "second"])
            self.assertEqual(self.reads, 2)

    def test_corrupt_snapshot_uses_the_original_reader(self):
        first = self.cache()
        body = self.get(first)
        first.close()
        path = next(self.directory.rglob("*.json"))
        path.write_text("invalid cache")
        self.assertEqual(self.get(self.cache()), body)
        self.assertEqual(self.reads, 2)

    def test_source_revision_and_job_state_invalidate_saved_bytes(self):
        first = self.cache()
        self.get(first)
        first.close()
        with patch("embedding_view_cache._SOURCE_REVISION", "other"):
            self.get(self.cache())
        self.fixture.job.return_value = {"state": "running", "pid": 123}
        self.get(self.cache())
        self.assertEqual(self.reads, 3)


if __name__ == "__main__":
    unittest.main()
