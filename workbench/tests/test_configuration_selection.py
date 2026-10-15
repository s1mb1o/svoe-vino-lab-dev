"""Check the configuration metadata used by the shared picker."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import recognize_routes


class ConfigurationMetadataTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "config.yaml"
        self.config = {
            "database_file": "catalog.sqlite3",
            "embeddings": [{"name": "index", "backend": "openai",
                            "base_url": "http://127.0.0.1:9/v1", "model": "example-model",
                            "views": {"full": {"steps": [{"step": "segment", "target": "package"}]}}}],
            "pipeline": [{"name": "default", "backend": "embedding", "embedding": "index"},
                         {"name": "override", "backend": "embedding", "embedding": "index",
                          "views": {"full": {"steps": [{"step": "resize", "max_size": 64,
                                                       "aspect": "keep", "upscale": False}]}}},
                         {"name": "broken"}]
        }
        self.path.write_text(yaml.safe_dump(self.config))
        check = patch.object(recognize_routes.run_jobs, "runnable",
                             side_effect=lambda pipeline, error, database: (not bool(error), str(error or "")))
        check.start()
        self.addCleanup(check.stop)

    def rows(self):
        return {item["name"]: item for item in recognize_routes.pipelines_view(self.path)["pipelines"]}

    def test_summary_uses_the_actual_index_and_query_steps(self):
        row = self.rows()["default"]
        self.assertEqual((row["backend"], row["embedding_backend"], row["model"]),
                         ("embedding", "openai", "example-model"))
        self.assertEqual(row["views"]["full"], [{"step": "segment", "target": "package"}])

    def test_query_overrides_do_not_use_catalogue_steps(self):
        rows = self.rows()
        self.assertEqual(rows["override"]["views"]["full"][0]["max_size"], 64)
        self.assertNotEqual(rows["override"]["views"], rows["default"]["views"])

    def test_invalid_configuration_stays_visible_without_metadata(self):
        row = self.rows()["broken"]
        self.assertFalse(row["runnable"])
        self.assertIsNone(row["model"])
        self.assertEqual(row["views"], {})
        self.assertEqual(row["stages"], [])

    def test_a_response_does_not_change_the_cached_configuration(self):
        row = self.rows()["default"]
        row["views"]["full"][0]["target"] = "changed"
        self.assertEqual(self.rows()["default"]["views"]["full"][0]["target"], "package")

    def test_current_settings_replace_old_metadata(self):
        self.assertEqual(self.rows()["default"]["model"], "example-model")
        self.config["embeddings"][0]["model"] = "replacement-model"
        self.path.write_text(yaml.safe_dump(self.config))
        self.assertEqual(self.rows()["default"]["model"], "replacement-model")


if __name__ == "__main__":
    unittest.main()
