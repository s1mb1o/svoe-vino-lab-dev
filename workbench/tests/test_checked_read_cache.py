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



class SharedLoadsTest(unittest.TestCase):
    setUp = CheckedReadCacheTest.setUp
    get = CheckedReadCacheTest.get
    def test_eight_cold_readers_share_one_loader_and_keep_independent_copies(self):
        import threading
        from concurrent.futures import Future
        from unittest.mock import patch
        started, joined, release = threading.Event(), threading.Event(), threading.Event()
        lock, waiting = threading.Lock(), []
        class ObservedFuture(Future):
            def result(self, *args, **kwargs):
                with lock:
                    waiting.append(1)
                    if len(waiting) == 7:
                        joined.set()
                return super().result(*args, **kwargs)
        def load():
            self.reads += 1
            started.set()
            self.assertTrue(release.wait(5))
            return {'value': []}
        with patch('checked_read_cache.Future', ObservedFuture), ThreadPoolExecutor(max_workers=8) as pool:
            leader = pool.submit(self.cache.get, 'key', [self.path], load)
            self.assertTrue(started.wait(5))
            others = [pool.submit(self.cache.get, 'key', [self.path], load) for _ in range(7)]
            try:
                self.assertTrue(joined.wait(5))
            finally:
                release.set()
            results = [leader.result()] + [one.result() for one in others]
        self.assertEqual(self.reads, 1)
        results[0]['value'].append('edit')
        self.assertTrue(all(result == {'value': []} for result in results[1:]))
        self.assertEqual(self.cache._flights._pending, {})

    def test_shared_failure_releases_waiters_and_next_attempt_can_succeed(self):
        import threading
        from concurrent.futures import Future
        from unittest.mock import patch
        joined, started = threading.Event(), threading.Event()
        class ObservedFuture(Future):
            def result(self, *args, **kwargs):
                joined.set()
                return super().result(*args, **kwargs)
        def fail():
            self.reads += 1
            started.set()
            self.assertTrue(joined.wait(5))
            raise ValueError('failed read')
        with patch('checked_read_cache.Future', ObservedFuture), ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.cache.get, 'key', [self.path], fail)
            self.assertTrue(started.wait(5))
            second = pool.submit(self.cache.get, 'key', [self.path], fail)
            for future in (first, second):
                with self.assertRaisesRegex(ValueError, 'failed read'):
                    future.result(timeout=5)
        self.assertEqual(self.reads, 1)
        self.assertEqual(self.cache._flights._pending, {})
        self.assertEqual(self.get(), {'text': 'one'})

    def test_clear_during_load_prevents_old_publication(self):
        import threading
        started, release = threading.Event(), threading.Event()
        def old():
            started.set()
            self.assertTrue(release.wait(5))
            return 'old'
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.cache.get, 'key', [self.path], old)
            self.assertTrue(started.wait(5))
            self.cache.clear()
            current = self.cache.get('key', [self.path], lambda: 'new')
            release.set()
            self.assertEqual(first.result(), 'old')
        self.assertEqual(current, 'new')
        self.assertEqual(self.cache.get('key', [self.path], lambda: 'wrong'), 'new')

    def test_flight_bound_independent_keys_and_recursive_owner(self):
        import threading
        from checked_read_cache import ReadFlights
        flights = ReadFlights(max_pending=1)
        started, release = threading.Event(), threading.Event()
        def slow():
            started.set()
            self.assertTrue(release.wait(5))
            return 'a'
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(flights.run, 'a', slow)
            self.assertTrue(started.wait(5))
            self.assertEqual(pool.submit(flights.run, 'b', lambda: 'b').result(timeout=1), 'b')
            self.assertEqual(len(flights._pending), 1)
            release.set()
            self.assertEqual(first.result(), 'a')
        self.assertEqual(flights.run('a', lambda: flights.run('a', lambda: 'nested')), 'nested')
        self.assertEqual(flights._pending, {})


if __name__ == "__main__":
    unittest.main()
