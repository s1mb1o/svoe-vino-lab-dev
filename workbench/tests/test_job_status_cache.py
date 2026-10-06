"""Check status freshness when a log, lock, or runner changes."""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from job_status_cache import JobStatusCache


class JobStatusCacheTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.log = self.directory / "job.log"
        self.lock = self.directory / "job.lock"
        self.log.write_text("one")
        self.lock.write_text("123")
        self.cache = JobStatusCache()
        self.pid = 123
        self.calls = 0

    def runner(self, directory):
        return self.pid

    def read(self, directory):
        self.calls += 1
        return {"pid": self.pid, "message": self.log.read_text(),
                "state": "running" if self.pid else "done"}

    def get(self):
        return self.cache.get(self.directory, self.read, self.runner, ("job.log", "job.lock"))

    def test_unchanged_inputs_share_a_read_and_return_private_dicts(self):
        first = self.get()
        first["message"] = "client changed it"
        self.assertEqual(self.get()["message"], "one")
        self.assertEqual(self.calls, 1)

    def test_append_truncate_replacement_and_lock_changes_invalidate_status(self):
        self.get()
        for new_body in ("one more", "x", "two"):
            self.log.write_text(new_body)
            self.assertEqual(self.get()["message"], new_body)
        replaced = self.directory / "replacement"
        replaced.write_text("three")
        os.replace(replaced, self.log)
        self.assertEqual(self.get()["message"], "three")
        self.lock.write_text("456")
        self.get()
        self.assertEqual(self.calls, 6)

    def test_same_size_write_with_restored_mtime_invalidates_status(self):
        self.get()
        stat = self.log.stat()
        self.log.write_text("two")
        os.utime(self.log, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertEqual(self.get()["message"], "two")
        self.assertEqual(self.calls, 2)

    def test_runner_exit_and_pid_replacement_invalidate_unchanged_logs(self):
        self.get()
        self.pid = None
        self.assertEqual(self.get()["state"], "done")
        self.pid = 456
        self.assertEqual(self.get()["pid"], 456)
        self.assertEqual(self.calls, 3)

    def test_creation_and_removal_of_a_lock_invalidate_status(self):
        self.lock.unlink()
        self.get()
        self.lock.write_text("123")
        self.get()
        self.lock.unlink()
        self.get()
        self.assertEqual(self.calls, 3)

    def test_change_during_a_read_does_not_create_a_cache_entry(self):
        def changing_reader(directory):
            result = self.read(directory)
            self.log.write_text(result["message"] + "!")
            return result
        for _ in range(2):
            self.cache.get(self.directory, changing_reader, self.runner, ("job.log", "job.lock"))
        self.assertEqual(self.calls, 2)
        self.assertFalse(self.cache._entries)

    def test_concurrent_requests_parse_one_time(self):
        with ThreadPoolExecutor(8) as pool:
            list(pool.map(lambda _: self.get(), range(32)))
        self.assertEqual(self.calls, 1)

    def test_capacity_evicts_status_and_zero_disables_the_cache(self):
        self.cache.max_entries = 1
        self.get()
        other = self.directory / "other"
        other.mkdir()
        self.cache.get(other, self.read, self.runner, ("job.log", "job.lock"))
        self.get()
        self.assertEqual(self.calls, 3)
        self.cache = JobStatusCache(max_entries=0)
        self.get()
        self.get()
        self.assertEqual(self.calls, 5)

    def test_reader_error_does_not_create_a_cache_entry(self):
        def broken(directory):
            raise ValueError("bad log")
        with self.assertRaisesRegex(ValueError, "bad log"):
            self.cache.get(self.directory, broken, self.runner, ("job.log", "job.lock"))
        self.assertFalse(self.cache._entries)

    def test_stat_error_preserves_the_original_reader_behavior(self):
        with patch("job_status_cache.os.stat", side_effect=PermissionError("denied")):
            self.assertEqual(self.get()["message"], "one")
            self.assertEqual(self.get()["message"], "one")
        self.assertEqual(self.calls, 2)
        self.assertFalse(self.cache._entries)

    def test_large_status_messages_do_not_enter_the_cache(self):
        self.cache.max_entry_bytes = 1
        self.get()
        self.get()
        self.assertEqual(self.calls, 2)
        self.assertFalse(self.cache._entries)

    def test_mutable_status_fields_do_not_enter_the_cache(self):
        def mutable_reader(directory):
            value = self.read(directory)
            value["mutable"] = []
            return value
        self.cache.get(self.directory, mutable_reader, self.runner, ("job.log", "job.lock"))
        self.assertFalse(self.cache._entries)


if __name__ == "__main__":
    unittest.main()
