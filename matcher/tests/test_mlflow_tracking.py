"""Check optional experiment export without model inference or a tracking server."""

import hashlib
import json
import os
from pathlib import Path
from types import ModuleType, SimpleNamespace
import tempfile
import unittest
from unittest import mock

from matcher import mlflow_tracking as tracking


class Entity:
    def __init__(self, key, value, timestamp=None, step=None):
        self.key, self.value, self.timestamp, self.step = key, value, timestamp, step


class Client:
    def __init__(self):
        self.runs, self.artifacts, self.params, self.metrics = {}, {}, {}, []
        self.fail_artifact = False
        self.lost_response = False
        self.scheme = "file:///tmp/artifacts"

    def get_experiment_by_name(self, name):
        return SimpleNamespace(experiment_id="1", lifecycle_stage="active")

    def search_runs(self, experiments, expression, max_results):
        source = expression.split("'")[1]
        return [r for r in self.runs.values() if r.tags["svoe_vino.source_id"] == source]

    def create_run(self, experiment, start_time, tags):
        run_id = str(len(self.runs) + 1)
        run = SimpleNamespace(info=SimpleNamespace(run_id=run_id, artifact_uri=self.scheme), tags=tags)
        self.runs[run_id] = run
        if self.lost_response:
            self.lost_response = False
            raise ConnectionError("response lost")
        return run

    def get_run(self, run_id):
        return self.runs[run_id]

    def log_batch(self, run_id, params=(), metrics=(), tags=(), synchronous=True):
        self.params.update({p.key: p.value for p in params})
        self.metrics.extend(metrics)

    def log_artifact(self, run_id, path, artifact_path):
        if self.fail_artifact:
            raise ConnectionError("Bearer SUPER_SECRET at https://user:password@host/?token=secret")
        name = str(Path(artifact_path or "") / Path(path).name)
        self.artifacts[name] = Path(path).read_bytes()

    def set_terminated(self, run_id, status, end_time):
        self.runs[run_id].status = status


def workbench_fixture(root):
    meta = {"run_id": "test-run", "started": "2026-10-17T00:00:00+03:00",
            "finished": "2026-10-17T00:01:00+03:00", "git_commit": "abc123",
            "options": {"set": "synthetic", "workers": 1}, "answered": 1,
            "query_set": {"total": 1}, "embeddings": {"model": "synthetic-model"},
            "backend": {"api_key": "SUPER_SECRET", "headers": {"Authorization": "secret"},
                        "url": "https://user:password@host/match?token=secret"}}
    metrics = {"positive": {"recall_at_1": 1.0, "empty": None},
               "latency_ms": {"p95": 12}, "invalid": float("nan"), "bool": True}
    for name, data in (("run.json", meta), ("metrics.json", metrics)):
        (root / name).write_text(json.dumps(data))
    (root / "results.jsonl").write_text(json.dumps({
        "query_id": "q-1", "image_sha256": "a" * 64, "error": "SUPER_SECRET",
        "trace": {"secret": "SUPER_SECRET"}, "body": "image body", "outcome": "hit"}) + "\n")
    (root / "private.log").write_text("SUPER_SECRET")


class ExportTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        workbench_fixture(self.root)
        self.before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.client = Client()
        entities = ModuleType("mlflow.entities")
        entities.Metric = entities.Param = entities.RunTag = Entity
        self.addCleanup(mock.patch.stopall)
        mock.patch.dict("sys.modules", {"mlflow.entities": entities}).start()
        self.factory = mock.patch.object(tracking, "make_client", return_value=self.client).start()
        mock.patch.dict(os.environ, {"MLFLOW_TRACKING_URI": "http://localhost:5000",
                                    "MLFLOW_EXPERIMENT_NAME": "test",
                                    "MLFLOW_TRACKING_ENABLED": "true"}).start()
        self.logs = []

    def export(self, **kwargs):
        return tracking.export_run(self.root, log=self.logs.append, **kwargs)

    def test_disabled_does_not_create_state_or_load_sdk(self):
        self.assertEqual(self.export(enabled=False), {"status": "disabled"})
        self.assertFalse((self.root / ".mlflow").exists())
        self.factory.assert_not_called()

    def test_export_metrics_provenance_hashes_and_sanitization(self):
        result = self.export()
        self.assertEqual(result["status"], "synced")
        self.assertEqual(self.client.runs["1"].status, "FINISHED")
        values = {m.key: m.value for m in self.client.metrics}
        self.assertEqual(values, {"latency_ms.p95": 12.0, "positive.recall_at_1": 1.0})
        self.assertEqual(self.client.params["backend.url"], "https://host/match")
        artifacts = self.client.artifacts
        self.assertNotIn("private.log", artifacts)
        for body in artifacts.values():
            for secret in (b"SUPER_SECRET", b"user:password", b"image body", b"?token=secret"):
                self.assertNotIn(secret, body)
        manifest = json.loads(artifacts["manifest.json"])
        for name, info in manifest["files"].items():
            self.assertEqual(info["sha256"], hashlib.sha256(artifacts[name]).hexdigest())
        self.assertEqual(self.before, {n: (self.root / n).read_bytes() for n in self.before})

    def test_repeated_export_has_no_duplicate(self):
        first = self.export()
        count = len(self.client.metrics)
        self.assertEqual(self.export(), first)
        self.assertEqual(len(self.client.runs), 1)
        self.assertEqual(len(self.client.metrics), count)

    def test_failed_upload_retries_same_run_without_secret_in_state(self):
        self.client.fail_artifact = True
        failed = self.export()
        self.assertEqual(failed["status"], "pending")
        self.assertEqual(failed["error"], "ConnectionError")
        self.assertNotIn("SUPER_SECRET", (self.root / ".mlflow/state.json").read_text())
        self.assertNotIn("SUPER_SECRET", str(self.logs))
        self.client.fail_artifact = False
        result = self.export()
        self.assertEqual(result["run_id"], failed["run_id"])
        self.assertEqual(result["status"], "synced")
        self.assertEqual(len(self.client.runs), 1)

    def test_lost_create_response_recovers_by_source_tag(self):
        self.client.lost_response = True
        self.assertEqual(self.export()["status"], "pending")
        self.assertEqual(self.export()["status"], "synced")
        self.assertEqual(len(self.client.runs), 1)

    def test_sdk_missing_preserves_results(self):
        self.factory.side_effect = ModuleNotFoundError("no mlflow")
        self.assertEqual(self.export()["status"], "pending")
        self.assertEqual(self.before, {n: (self.root / n).read_bytes() for n in self.before})

    def test_destination_change_creates_an_independent_run(self):
        first = self.export()
        with mock.patch.dict(os.environ, {"MLFLOW_TRACKING_URI": "http://another-host"}):
            second = self.export()
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(self.export(), first)

    def test_changed_source_cannot_overwrite_remote_artifacts(self):
        self.export()
        before = dict(self.client.artifacts)
        (self.root / "metrics.json").write_text('{"changed": 10}')
        self.assertEqual(self.export()["status"], "pending")
        self.assertEqual(self.client.artifacts, before)

    def test_direct_s3_is_refused(self):
        self.client.scheme = "s3://bucket/artifacts"
        self.assertEqual(self.export()["status"], "pending")
        self.assertFalse(self.client.artifacts)

    def test_local_lock_prevents_concurrent_duplicate(self):
        folder = self.root / ".mlflow"
        folder.mkdir()
        with tracking.locked(folder / "export.lock"):
            self.assertEqual(self.export()["status"], "pending")
        self.assertFalse(self.client.runs)

    def test_missing_uri_does_not_fall_back_to_a_local_store(self):
        with mock.patch.dict(os.environ, {"MLFLOW_TRACKING_URI": ""}):
            self.assertEqual(self.export()["status"], "pending")
        self.factory.assert_not_called()

    def test_incomplete_benchmark_is_killed(self):
        meta = json.loads((self.root / "run.json").read_text())
        meta["answered"] = 0
        (self.root / "run.json").write_text(json.dumps(meta))
        self.export()
        self.assertEqual(self.client.runs["1"].status, "KILLED")

    def test_matcher_cells_export_configuration_and_failed_status(self):
        for p in self.root.iterdir():
            p.unlink()
        (self.root / "provenance.json").write_text('{"commit": "abc", "archive_sha256": "123"}')
        (self.root / "summary.json").write_text('{"runs": {"cell": {"errors": 1, "accepted_hits": 3}}}')
        (self.root / "cell").mkdir()
        (self.root / "cell/config.yaml").write_text('pipeline:\n  - model: test\n    api_key: SUPER_SECRET\n')
        (self.root / "cell/results.jsonl").write_text('{"trace": {"body": "secret"}, "error": "secret"}\n')
        self.assertEqual(self.export()["status"], "synced")
        self.assertEqual(self.client.runs["1"].status, "FAILED")
        self.assertIn("cell/config.yaml.json", self.client.artifacts)
        self.assertIn("runs.cell.accepted_hits", {m.key for m in self.client.metrics})

    def test_arcface_records_settings_and_epoch_metrics(self):
        (self.root / "training-snapshot.json").write_text('{"features_sha256": "123"}')
        (self.root / "report.json").write_text(json.dumps({
            "settings": {"seed": 42}, "selected_epoch": 2,
            "history": [{"epoch": 1, "loss": 0.8}, {"epoch": 2, "loss": 0.4}]}))
        self.assertEqual(self.export(kind="arcface")["status"], "synced")
        self.assertEqual(self.client.params["settings.seed"], "42")
        self.assertEqual([(m.step, m.value) for m in self.client.metrics if m.key == "history.loss"],
                         [(1, 0.8), (2, 0.4)])

    def test_symlink_artifact_is_refused(self):
        target = self.root / "private.log"
        (self.root / "results.jsonl").unlink()
        (self.root / "results.jsonl").symlink_to(target)
        self.assertEqual(self.export()["status"], "pending")
        self.assertFalse(self.client.artifacts)

    def test_flat_keys_do_not_collide(self):
        values = dict(tracking.flat({"recall@1": 1, "recall_1": 2, "a.b": 3, "a": {"b": 4}}))
        self.assertEqual(len(values), 4)

    def test_long_keys_do_not_collide(self):
        values = dict(tracking.flat({"x" * 300: 1, "x" * 301: 2}))
        self.assertEqual(len(values), 2)
        self.assertTrue(all(len(k) <= 250 for k in values))

    def test_redaction_keeps_model_token_parameters(self):
        result = tracking.sanitize({"max_tokens": 100, "tokenizer": "model", "accessToken": "secret",
                                    "token": "secret", "apiKey": "secret", "data_base64": "body"})
        self.assertEqual(result, {"max_tokens": 100, "tokenizer": "model", "accessToken": "<redacted>",
                                  "token": "<redacted>", "apiKey": "<redacted>"})


if __name__ == "__main__":
    unittest.main()
