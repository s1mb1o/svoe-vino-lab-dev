"""Check cluster artifacts, notes, rules, errors, and concurrent reads."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
import unittest

from cluster_view_cache import ClusterViewCache
import clusters
import test_embedding_view_cache as fixture


class ClusterViewCacheTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.EmbeddingViewCacheTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.cache.close()
        self.fixture.cache = ClusterViewCache()
        self.addCleanup(self.fixture.cache.close)
        self.files = {key: self.fixture.directory / name for key, name in
                      (("artifact", clusters.CLUSTERS_FILE),
                       ("notes", clusters.NOTES_FILE), ("rules", clusters.RULES_FILE))}
        self.files["artifact"].write_text(json.dumps({"built": 1}))
        self.fixture.reader.side_effect = self.read_view

    def read_view(self, settings, name=None):
        view = self.fixture.read_view(settings, name)
        for key, path in self.files.items():
            view[key] = json.loads(path.read_text()) if path.exists() else None
        return view

    def get(self, name="sample"):
        return self.fixture.get(name)

    def test_artifact_replacement_preserves_exact_bytes(self):
        self.get()
        path = self.files["artifact"]
        before = path.stat()
        replacement = path.with_suffix(".new")
        replacement.write_text(json.dumps({"built": 2}))
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(path)
        self.assertEqual(self.get()["artifact"], {"built": 2})
        expected = json.dumps(self.read_view(self.fixture.settings, "sample"),
                              ensure_ascii=False).encode()
        body = self.fixture.cache.get(self.fixture.settings, "sample", self.fixture.reader,
                                      self.fixture.job, self.fixture.queue, encode_json=True)
        self.assertEqual(body, expected)

    def test_note_and_rule_changes_are_visible(self):
        self.get()
        self.files["notes"].write_text(json.dumps({"text": "note"}))
        self.assertEqual(self.get()["notes"], {"text": "note"})
        self.files["rules"].write_text(json.dumps({"name": "rule"}))
        self.assertEqual(self.get()["rules"], {"name": "rule"})
        self.files["notes"].unlink()
        self.assertIsNone(self.get()["notes"])

    def test_missing_artifact_appears_on_the_next_read(self):
        self.files["artifact"].unlink()
        self.assertIsNone(self.get()["artifact"])
        self.files["artifact"].write_text(json.dumps({"built": 3}))
        self.assertEqual(self.get()["artifact"], {"built": 3})

    def test_artifact_change_during_read_prevents_insertion(self):
        def read(settings, name):
            view = self.read_view(settings, name)
            self.files["artifact"].write_text(json.dumps({"built": view["artifact"]["built"] + 1}))
            return view
        self.fixture.reader.side_effect = read
        self.get()
        self.get()
        self.assertEqual(self.fixture.reader.call_count, 2)

    def test_current_status_error_is_not_retained(self):
        view = self.read_view(self.fixture.settings, "sample")
        view["status"] = {"current_error": "cannot read index"}
        self.fixture.reader.side_effect = None
        self.fixture.reader.return_value = view
        self.get()
        self.get()
        self.assertEqual(self.fixture.reader.call_count, 2)

    def test_concurrent_reads_build_one_view(self):
        with ThreadPoolExecutor(max_workers=8) as executor:
            values = list(executor.map(lambda _: self.get(), range(16)))
        self.assertTrue(all(value == values[0] for value in values))
        self.assertEqual(self.fixture.reader.call_count, 1)


if __name__ == "__main__":
    unittest.main()
