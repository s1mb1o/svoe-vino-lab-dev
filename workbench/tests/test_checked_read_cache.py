"""Check replacement, unstable reads, failures, caller copies, and memory bounds."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from checked_read_cache import CheckedReadCache


class CheckedReadCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "source"
        self.path.write_text("one")
        self.cache = CheckedReadCache()
        self.reads = 0

    def get(self):
        def load():
            self.reads += 1
            return {"text": self.path.read_text()}
        return self.cache.get("source", [self.path], load)

    def test_reuse_and_caller_mutation(self):
        self.get()["text"] = "changed"
        self.assertEqual(self.get(), {"text": "one"})
        self.assertEqual(self.reads, 1)

    def test_replacement_with_preserved_mtime_and_deletion(self):
        self.get()
        before = self.path.stat()
        replacement = self.path.with_suffix(".new")
        replacement.write_text("two")
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(self.path)
        self.assertEqual(self.get()["text"], "two")
        self.path.unlink()
        with self.assertRaises(FileNotFoundError):
            self.get()
        self.path.write_text("new")
        self.assertEqual(self.get()["text"], "new")

    def test_a_write_during_load_is_not_saved(self):
        def load():
            self.path.write_text("after")
            return {"text": "before"}
        self.cache.get("source", [self.path], load)
        self.assertEqual(self.get()["text"], "after")
        self.assertEqual(self.reads, 1)

    def test_directory_membership_invalidates(self):
        directory = self.path.parent
        def read():
            return sorted(p.name for p in directory.iterdir())
        self.assertEqual(self.cache.get("dir", [directory], read), ["source"])
        (directory / "added").touch()
        self.assertEqual(self.cache.get("dir", [directory], read), ["added", "source"])

    def test_lru_and_oversize_limits(self):
        self.cache = CheckedReadCache(max_entries=1, max_bytes=256)
        for key in ("a", "b", "a"):
            self.cache.get(key, [self.path], lambda: "small")
        self.assertEqual(list(self.cache._entries), ["a"])
        self.cache.get("large", [self.path], lambda: "x" * 1024)
        self.assertNotIn("large", self.cache._entries)
        self.assertLessEqual(self.cache._bytes, 256)

    def test_concurrent_readers_keep_bounds(self):
        with ThreadPoolExecutor(max_workers=8) as workers:
            results = list(workers.map(lambda _: self.get(), range(32)))
        self.assertTrue(all(value == {"text": "one"} for value in results))
        self.assertEqual(len(self.cache._entries), 1)
        self.assertGreater(self.cache._bytes, 0)


if __name__ == "__main__":
    unittest.main()
