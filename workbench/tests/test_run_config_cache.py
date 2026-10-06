"""Check that Runs configuration caching observes file edits."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import run_routes


class RunConfigCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "config.yaml"
        self.path.write_text("database_file: catalog.sqlite3\npipeline: []\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_repeat_requests_do_not_parse_unchanged_yaml(self):
        with patch.object(run_routes.pipelines, "load", wraps=run_routes.pipelines.load) as read:
            first = run_routes.configurations(self.path)
            second = run_routes.configurations(self.path)
        self.assertEqual(read.call_count, 1)
        self.assertEqual(first, ([], None))
        self.assertEqual(second, first)

    def test_replacement_and_invalid_config_are_visible(self):
        self.assertEqual(run_routes.configurations(self.path), ([], None))
        stat = self.path.stat()
        replacement = self.path.with_suffix(".new")
        replacement.write_text("database_file: catalog.sqlite3\npipeline: nope\n")
        os.utime(replacement, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        replacement.replace(self.path)
        self.assertIn("MUST be a list", run_routes.configurations(self.path)[1])
        self.path.write_text("database_file: catalog.sqlite3\npipeline: []\n")
        self.assertEqual(run_routes.configurations(self.path), ([], None))
        self.path.unlink()
        self.assertIsNotNone(run_routes.configurations(self.path)[1])

    def test_callers_cannot_modify_cached_summaries(self):
        self.path.write_text("database_file: catalog.sqlite3\npipeline:\n  - name: invalid\n")
        entries, error = run_routes.configurations(self.path)
        self.assertIsNone(error)
        entries[0]["name"] = "changed"
        self.assertEqual(run_routes.configurations(self.path)[0][0]["name"], "invalid")


if __name__ == "__main__":
    unittest.main()
