"""Check the selected embedding cache and the existing override contract."""

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import embeddings
import new_wine_workflow
from settings_cache import SettingsCache


class EmbeddingNameCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "config.yaml"
        self.write("first")
        self.override_cache = patch.object(new_wine_workflow, "SETTINGS_CACHE", SettingsCache())
        self.override_cache.start()
        self.addCleanup(self.override_cache.stop)

    def write(self, value):
        self.path.write_text("database_file: catalog.sqlite3\nnew_wine_embedding: " + value + "\n")

    def read(self, override=None):
        return new_wine_workflow.embedding_name(self.path, override)

    def test_repeat_reads_parse_yaml_once(self):
        with patch.object(embeddings, "read_config", wraps=embeddings.read_config) as loader:
            for _ in range(4):
                self.assertEqual(self.read(), "first")
            self.assertEqual(loader.call_count, 1)

    def test_changed_selection_appears_without_restart(self):
        self.assertEqual(self.read(), "first")
        self.write("second")
        self.assertEqual(self.read(), "second")

    def test_replacement_with_restored_mtime_is_visible(self):
        self.read()
        before = self.path.stat()
        replacement = self.path.with_suffix(".new")
        replacement.write_text(self.path.read_text().replace("first", "other"))
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(self.path)
        self.assertEqual(self.read(), "other")

    def test_invalid_selection_is_503_and_valid_config_recovers(self):
        self.read()
        for value in ("bad/name", "null", "42", "''"):
            self.write(value)
            with self.assertRaises(new_wine_workflow.WorkflowError) as caught:
                self.read()
            self.assertEqual(caught.exception.code, 503)
            self.assertIn("new_wine_embedding MUST name one embedding", str(caught.exception))
        self.write("valid")
        self.assertEqual(self.read(), "valid")

    def test_missing_or_invalid_yaml_is_503(self):
        self.read()
        self.path.unlink()
        with self.assertRaises(new_wine_workflow.WorkflowError) as caught:
            self.read()
        self.assertEqual(caught.exception.code, 503)
        self.path.write_text("[invalid YAML")
        with self.assertRaises(new_wine_workflow.WorkflowError) as caught:
            self.read()
        self.assertEqual(caught.exception.code, 503)
        self.write("valid")
        self.assertEqual(self.read(), "valid")

    def test_override_keeps_400_errors_and_checks_current_yaml(self):
        self.read()
        self.write("bad/name")
        self.assertEqual(self.read("override"), "override")
        with self.assertRaises(new_wine_workflow.WorkflowError) as caught:
            self.read("bad/name")
        self.assertEqual(caught.exception.code, 400)
        self.assertIn("--embedding MUST name one embedding", str(caught.exception))
        self.path.write_text("[invalid YAML")
        with self.assertRaises(new_wine_workflow.WorkflowError) as caught:
            self.read("override")
        self.assertEqual(caught.exception.code, 503)

    def test_lookup_does_not_add_embedding_entry_validation(self):
        self.path.write_text(self.path.read_text() + "embeddings: malformed\n")
        self.assertEqual(self.read(), "first")


if __name__ == "__main__":
    unittest.main()
