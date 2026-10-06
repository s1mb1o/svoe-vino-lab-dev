"""Check current settings and one readiness check per embedding per request."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import embedding_run
import recognize_routes


class RecognizeChoiceCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "config.yaml"
        self.path.write_text("""database_file: catalog.sqlite3
pipeline:
  - {name: first, backend: embedding, embedding: gw}
  - {name: second, backend: embedding, embedding: gw}
  - {name: other, backend: embedding, embedding: other}
  - {name: broken}
""")
        config = yaml.safe_load(self.path.read_text())
        config["embeddings"] = [
            {"name": name, "backend": "openai", "base_url": "http://127.0.0.1:9/v1",
             "model": "fake", "views": {"full": {"steps": [{"step": "segment", "target": "package"}]}}}
            for name in ("gw", "other")]
        self.path.write_text(yaml.safe_dump(config))

    def test_config_reuse_and_request_local_readiness(self):
        with patch.object(recognize_routes.pipelines, "load", wraps=recognize_routes.pipelines.load) as load, \
                patch.object(embedding_run, "index_ready", return_value=True) as ready:
            first = recognize_routes.pipelines_view(self.path)
            second = recognize_routes.pipelines_view(self.path)
            self.assertEqual(first, second)
            self.assertEqual(load.call_count, 1)
            self.assertEqual(ready.call_count, 4)
            ready.return_value = False
            third = recognize_routes.pipelines_view(self.path)
            self.assertFalse(third["pipelines"][0]["runnable"])
            self.assertIn("configuration error", third["pipelines"][-1]["reason"])

    def test_current_config_and_independent_responses(self):
        with patch.object(embedding_run, "index_ready", return_value=True):
            first = recognize_routes.pipelines_view(self.path)
            first["pipelines"][0]["name"] = "changed"
            self.assertEqual(recognize_routes.pipelines_view(self.path)["pipelines"][0]["name"], "first")
            self.path.write_text("database_file: catalog.sqlite3\npipeline: []\n")
            self.assertEqual(recognize_routes.pipelines_view(self.path), {"pipelines": []})


if __name__ == "__main__":
    unittest.main()
