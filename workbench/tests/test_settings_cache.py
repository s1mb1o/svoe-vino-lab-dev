"""Check settings isolation, file freshness, and polling route behavior."""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import embedding_routes
import embeddings
import run_jobs
from settings_cache import SettingsCache
import settings_cache


class SettingsCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "config.yaml"
        self.path.write_text("old")
        self.loader = Mock(side_effect=lambda path: SimpleNamespace(
            values=[{"text": Path(path).read_text()}]))
        self.cache = SettingsCache()

    def read(self):
        return self.cache.get(self.path, self.loader).values[0]["text"]

    def test_callers_receive_independent_settings(self):
        first = self.cache.get(self.path, self.loader)
        first.values[0]["text"] = "changed"
        second = self.cache.get(self.path, self.loader)
        second.values.append({"text": "extra"})
        third = self.cache.get(self.path, self.loader)
        self.assertEqual(third.values, [{"text": "old"}])
        self.assertEqual(self.loader.call_count, 1)

    def test_check_does_not_copy_or_expose_cached_settings(self):
        self.read()
        with patch.object(settings_cache, "deepcopy", side_effect=AssertionError("unexpected copy")):
            self.assertIsNone(self.cache.check(self.path, self.loader))
        self.assertEqual(self.loader.call_count, 1)
        self.path.write_text("new")
        self.assertIsNone(self.cache.check(self.path, self.loader))
        self.assertEqual(self.read(), "new")
        self.assertEqual(self.loader.call_count, 2)

    def test_append_and_truncation_are_visible(self):
        self.assertEqual(self.read(), "old")
        with self.path.open("a") as stream:
            stream.write(" more")
        self.assertEqual(self.read(), "old more")
        self.path.write_text("x")
        self.assertEqual(self.read(), "x")
        self.assertEqual(self.loader.call_count, 3)

    def test_equal_size_edit_with_restored_mtime_is_visible(self):
        self.read()
        before = self.path.stat()
        self.path.write_text("new")
        os.utime(self.path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(self.read(), "new")
        self.assertEqual(self.loader.call_count, 2)

    def test_atomic_replacement_with_restored_mtime_is_visible(self):
        self.read()
        before = self.path.stat()
        replacement = self.path.with_suffix(".new")
        replacement.write_text("new")
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(self.path)
        self.assertEqual(self.read(), "new")
        self.assertEqual(self.loader.call_count, 2)

    def test_missing_file_retains_loader_error_and_recovers(self):
        self.read()
        self.path.unlink()
        with self.assertRaises(FileNotFoundError):
            self.read()
        self.path.write_text("new")
        self.assertEqual(self.read(), "new")
        self.assertEqual(self.loader.call_count, 3)

    def test_stat_error_uses_existing_loader(self):
        self.read()
        with patch.object(self.cache, "_signature", side_effect=PermissionError):
            self.assertEqual(self.read(), "old")
        self.read()
        self.assertEqual(self.loader.call_count, 3)

    def test_file_change_during_load_prevents_insertion(self):
        def load(path):
            value = Path(path).read_text()
            Path(path).write_text("new")
            return value
        loader = Mock(side_effect=load)
        self.assertEqual(self.cache.get(self.path, loader), "old")
        self.assertEqual(self.cache.get(self.path, loader), "new")
        self.assertEqual(loader.call_count, 2)

    def test_stat_error_after_load_prevents_insertion(self):
        signature = self.cache._signature(self.path)
        with patch.object(self.cache, "_signature", side_effect=[signature, PermissionError]):
            self.assertEqual(self.read(), "old")
        self.read()
        self.assertEqual(self.loader.call_count, 2)

    def test_loader_errors_are_not_cached(self):
        self.loader.side_effect = ValueError("invalid config")
        for _ in range(2):
            with self.assertRaisesRegex(ValueError, "invalid config"):
                self.read()
        self.loader.side_effect = lambda path: SimpleNamespace(values=[{"text": "valid"}])
        self.assertEqual(self.read(), "valid")
        self.assertEqual(self.loader.call_count, 3)

    def test_cache_capacity_evicts_old_settings(self):
        self.cache = SettingsCache(max_entries=1)
        self.read()
        second = self.path.with_name("second.yaml")
        second.write_text("second")
        self.cache.get(second, self.loader)
        self.read()
        self.assertEqual(self.loader.call_count, 3)
        self.assertEqual(len(self.cache._entries), 1)

    def test_zero_limit_and_large_config_bypass_cache(self):
        for cache in (SettingsCache(max_entries=0), SettingsCache(max_config_bytes=2)):
            self.loader.reset_mock()
            cache.get(self.path, self.loader)
            cache.get(self.path, self.loader)
            self.assertEqual(self.loader.call_count, 2)

    def test_each_loader_has_its_own_settings_type(self):
        other = Mock(return_value="pipeline settings")
        self.read()
        self.assertEqual(self.cache.get(self.path, other), "pipeline settings")
        self.read()
        self.assertEqual(self.loader.call_count, 1)
        self.assertEqual(other.call_count, 1)

    def test_concurrent_misses_load_once_and_return_independent_values(self):
        with ThreadPoolExecutor(max_workers=8) as executor:
            values = list(executor.map(lambda _: self.cache.get(self.path, self.loader), range(32)))
        self.assertEqual(self.loader.call_count, 1)
        values[0].values[0]["text"] = "changed"
        self.assertTrue(all(value.values[0]["text"] == "old" for value in values[1:]))


class PollingSettingsTest(unittest.TestCase):
    def test_both_routes_reuse_settings_and_observe_config_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            path.write_text("database_file: catalog.sqlite3\nembeddings: []\npipeline: []\n")
            server = SimpleNamespace(config_path=str(path), run_jobs_dir=directory)
            cache = SettingsCache()
            with patch.object(embedding_routes, "SETTINGS_CACHE", cache), \
                    patch.object(run_jobs, "SETTINGS_CACHE", cache), \
                    patch.object(embeddings, "load_settings", wraps=embeddings.load_settings) as embedding_load, \
                    patch.object(run_jobs.pipelines, "load", wraps=run_jobs.pipelines.load) as pipeline_load:
                for _ in range(3):
                    self.assertEqual(embedding_routes.respond(server, "GET", "/api/embedding-jobs")[0], 200)
                    self.assertEqual(run_jobs.respond(server, "GET", "/api/run-jobs", None)[0], 200)
                self.assertEqual(embedding_load.call_count, 1)
                self.assertEqual(pipeline_load.call_count, 1)
                path.write_text("[invalid YAML")
                self.assertEqual(embedding_routes.respond(server, "GET", "/api/embedding-jobs")[0], 503)
                self.assertEqual(run_jobs.respond(server, "GET", "/api/run-jobs", None)[0], 503)
                path.write_text("database_file: catalog.sqlite3\nembeddings: []\npipeline: []\n")
                self.assertEqual(embedding_routes.respond(server, "GET", "/api/embedding-jobs")[0], 200)
                self.assertEqual(run_jobs.respond(server, "GET", "/api/run-jobs", None)[0], 200)
                self.assertEqual(embedding_load.call_count, 3)
                self.assertEqual(pipeline_load.call_count, 3)


if __name__ == "__main__":
    unittest.main()
