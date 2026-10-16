"""Opt-in check against a real temporary MLflow SQLite store and local artifacts."""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from matcher import mlflow_tracking as tracking


@unittest.skipUnless(os.environ.get("MLFLOW_TEST_INTEGRATION") == "1",
                     "set MLFLOW_TEST_INTEGRATION=1 and install MLflow, SQLAlchemy, and Alembic")
class LocalStoreTest(unittest.TestCase):
    def test_real_store_export_retry_and_artifact_hashes(self):
        from mlflow import MlflowClient

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "experiment"
            source.mkdir()
            (source / "run.json").write_text(json.dumps({
                "run_id": "synthetic", "git_commit": "test-revision", "answered": 1,
                "query_set": {"total": 1}, "options": {"set": "synthetic"},
                "backend": {"api_key": "do-not-export"}}))
            (source / "metrics.json").write_text('{"positive": {"recall_at_1": 1.0}}')
            (source / "queries.jsonl").write_text('{"query_id": "q-1", "image_sha256": "abc"}\n')
            uri = "sqlite:///" + str(root / "tracking.db")
            client = MlflowClient(tracking_uri=uri)
            experiment_id = client.create_experiment("integration", artifact_location=(root / "artifacts").as_uri())
            with mock.patch.dict(os.environ, {"MLFLOW_TRACKING_URI": uri,
                                              "MLFLOW_EXPERIMENT_NAME": "integration"}):
                with mock.patch.object(tracking, "make_client", return_value=client), \
                        mock.patch.object(client, "log_artifact", side_effect=ConnectionError("offline")):
                    failed = tracking.export_run(source, enabled=True, log=lambda message: None)
                self.assertEqual(failed["status"], "pending")
                result = tracking.export_run(source, enabled=True, log=lambda message: None)
                self.assertEqual(result["status"], "synced")
                self.assertEqual(result["run_id"], failed["run_id"])
                repeated = tracking.export_run(source, enabled=True, log=lambda message: None)
                self.assertEqual(repeated, result)
            saved = client.get_run(result["run_id"])
            self.assertEqual(saved.info.status, "FINISHED")
            self.assertEqual(saved.data.metrics["positive.recall_at_1"], 1.0)
            self.assertEqual(saved.data.params["backend.api_key"], "<redacted>")
            self.assertEqual(saved.data.tags["mlflow.source.git.commit"], "test-revision")
            self.assertEqual(len(client.search_runs([experiment_id])), 1)
            self.assertEqual(len(client.get_metric_history(result["run_id"], "positive.recall_at_1")), 1)
            manifest = json.loads(Path(client.download_artifacts(result["run_id"], "manifest.json")).read_text())
            for name, metadata in manifest["files"].items():
                body = Path(client.download_artifacts(result["run_id"], name)).read_bytes()
                self.assertEqual(hashlib.sha256(body).hexdigest(), metadata["sha256"])
                self.assertNotIn(b"do-not-export", body)


if __name__ == "__main__":
    unittest.main()
