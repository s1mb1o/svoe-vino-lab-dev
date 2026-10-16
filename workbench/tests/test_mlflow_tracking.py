"""Check that Workbench exports only after its local benchmark files are complete."""

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import benchmark  # noqa: E402
from matcher import mlflow_tracking  # noqa: E402


class Backend:
    id = "synthetic"
    spec = {"id": "synthetic", "workers": 1}
    top_k = 1

    def ask(self, path):
        return [{"slug": "wine", "score": 1.0}], 1, 200, None


class TrackingHookTest(unittest.TestCase):
    def test_failed_export_keeps_benchmark_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            rows = [{"query_id": "q-1", "image_path": "synthetic.jpg", "abs_path": "unused",
                     "image_sha256": "a" * 64, "slug": "wine", "label": "positive", "truth": ["wine"]}]
            def fail(uri):
                # The SDK is called only after all local results are available.
                directory = next(Path(temporary).iterdir())
                for name in ("run.json", "metrics.json", "summary.md", "results.jsonl"):
                    self.assertTrue((directory / name).is_file(), name)
                raise ConnectionError("tracking offline")
            with mock.patch.dict(os.environ, {"MLFLOW_TRACKING_ENABLED": "true",
                                              "MLFLOW_TRACKING_URI": "http://unused"}), \
                    mock.patch.object(mlflow_tracking, "make_client", side_effect=fail):
                directory, metrics = benchmark.run_benchmark(
                    "unused", "synthetic", Backend(), runs_dir=temporary,
                    queries=(rows, {}), embeddings={}, log=lambda message: None)
            self.assertEqual(metrics["positive"]["recall_at_1"], 1.0)
            self.assertEqual(json.loads((Path(directory) / "run.json").read_text())["answered"], 1)
            state = json.loads((Path(directory) / ".mlflow/state.json").read_text())
            self.assertEqual(next(iter(state["destinations"].values()))["status"], "pending")


if __name__ == "__main__":
    unittest.main()
