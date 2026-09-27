"""Test one-profile dispatch with fixtures. Never contact the lab API or a model."""
import copy
import contextlib
import datetime
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_internal_profile_queue as queue_run


class QueueTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.queue_path = self.root / "queue.json"
        self.jobs = self.root / "jobs"
        self.runs = self.root / "runs"
        self.name = "fixture-profile"
        self.query = {"query_id": "q-000001", "image_path": "wine/photo.png",
                      "image_sha256": "digest", "slug": "wine", "label": "negative", "truth": []}
        self.identity = {"profile": self.name, "set": "my", "config": str(self.root / "config.yaml"),
            "database": str(self.root / "lab.sqlite3"), "model_backend": "openai", "workers": 4,
            "has_barcode": True, "queries": [self.query]}
        self.row = {"name": self.name, "backend": "embedding", "embedding": "fixture-model",
            "model_backend": "openai", "workers": 4, "use_cache": True, "use_barcode": True,
            "authorized_to_start": True, "status": "pending", "run_id": None}
        self.queue = {"set": "my", "query_count_at_queue_time": 1, "profiles": [self.row]}
        queue_run.atomic_json(self.queue_path, self.queue)
        self.evidence = self.root / "preflight.txt"
        self.evidence.write_text("fixture evidence")
        self.gate_path = self.root / "gate.json"
        self.gate = {"recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "queue": str(self.queue_path), "profile": self.name, "set": "my",
            "identity_sha256": queue_run.fingerprint(self.identity),
            **dict.fromkeys(queue_run.FLAGS, True),
            "memory": {"available_gib": 50, "additional_required_gib": 10, "margin_gib": 20},
            "evidence": [str(self.evidence)]}
        queue_run.atomic_json(self.gate_path, self.gate)

    def launch(self, response=(202, {"pid": 1234}), error=None):
        def api(method, path, body=None):
            if method == "GET":
                return 200, {"jobs": [], "now": 0}
            saved = queue_run.read_json(self.queue_path)["profiles"][0]["attempts"][0]
            self.assertEqual(saved["state"], "launch_intent")
            self.assertIsNone(saved["pid"])
            self.assertEqual(saved["request"], body)
            if error:
                raise error
            return response
        with mock.patch.object(queue_run, "api", side_effect=api) as transport:
            attempt = queue_run.dispatch(self.queue_path, self.queue, self.identity, self.gate_path, self.jobs,
                                         lambda: self.identity)
            self.assertEqual(sum(c.args[0] == "POST" for c in transport.call_args_list), 1)
        return attempt

    def command(self):
        return (f"/fixture/python {queue_run.ROOT}/pipeline/run_job.py --config {self.identity['config']} "
                f"--name {self.name} --set my --jobs-dir {self.jobs} --workers 4")

    def events(self, attempt, *, final="done", wrong_start=None):
        start = {"event": "start", "t": attempt["intent_t"] + 1, "pid": 1234,
            "configuration": self.name, "set": "my", "workers": 4,
            "use_cache": True, "use_barcode": True, "limit": None, "todo": 1}
        start.update(wrong_start or {})
        rows = [start, {"event": "run_dir", "t": attempt["intent_t"] + 2, "run_id": "fixture-run"}]
        if final:
            rows.append({"event": final, "t": attempt["intent_t"] + 3,
                         "run_id": "fixture-run", "answered": 1, "errors": 0})
        directory = self.jobs / self.name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "job.log").write_text("".join(json.dumps(r) + "\n" for r in rows))
        return rows

    def artifacts(self):
        directory = self.runs / "fixture-run"
        directory.mkdir(parents=True)
        meta = {"run_id": "fixture-run", "configuration": self.name, "finished": "now", "answered": 1,
                "use_cache": True, "use_barcode": True,
                "options": {"database": self.identity["database"], "set": "my", "workers": 4, "limit": None}}
        queue_run.atomic_json(directory / "run.json", meta)
        queue_run.atomic_json(directory / "metrics.json", {"run_id": "fixture-run", "positive": {"recall_at_1": 1}})
        (directory / "queries.jsonl").write_text(json.dumps(self.query) + "\n")
        result = dict(self.query, error=None, predicted_slug="other", latency_ms=1.0)
        (directory / "results.jsonl").write_text(json.dumps(result) + "\n")
        prediction = {k: result[k] for k in ("query_id", "image_path", "image_sha256", "predicted_slug", "latency_ms")}
        (directory / "predictions.jsonl").write_text(json.dumps(prediction) + "\n")
        return directory

    def test_default_inspection_never_writes_or_calls_api(self):
        before = self.queue_path.read_bytes()
        with mock.patch.object(queue_run, "api") as api, mock.patch.object(queue_run, "atomic_json") as save:
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(queue_run.main(["--queue", str(self.queue_path)]), 0)
        self.assertEqual(self.queue_path.read_bytes(), before)
        api.assert_not_called()
        save.assert_not_called()
        self.assertFalse((self.root / "queue.lock").exists())

    def test_authorization_cannot_enable_external_recognizer(self):
        self.row["authorized_to_start"] = False
        with self.assertRaisesRegex(ValueError, "authorized"):
            queue_run.profile_row(self.queue, self.name)
        self.row.update(name=queue_run.FORBIDDEN, authorized_to_start=True)
        with self.assertRaisesRegex(ValueError, "authorized"):
            queue_run.profile_row(self.queue, queue_run.FORBIDDEN)

    def test_urls_reject_external_dns_credentials_and_link_local(self):
        for url in ("http://192.168.86.14:18081/v1", "http://127.0.0.1:8168", "http://[::1]:80"):
            self.assertEqual(queue_run.internal_url(url), url)
        for url in ("https://example.com", "http://8.8.8.8", "http://169.254.169.254",
                    "http://u:p@192.168.86.14", "file:///tmp/x", "http://192.168.86.14?token=x"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                queue_run.internal_url(url)

    def test_snapshot_checks_actual_config_backend_workers_and_ready_index(self):
        config_path = Path(self.identity["config"])
        raw = {"database_file": self.identity["database"], "embeddings": [{
            "name": "fixture-model", "backend": "openai", "base_url": "http://192.168.86.14:18081/v1",
            "model": "fixture-model", "views": {"full": {"steps": [{"step": "segment", "target": "package"}]}}}],
            "pipeline": [{"name": self.name, "backend": "embedding", "embedding": "fixture-model",
                          "views": {"full": {"steps": [{"step": "resize", "max_size": 512}]}}}]}
        baseline = self.root / "baseline"
        baseline.mkdir()
        (baseline / "queries.jsonl").write_text(json.dumps(self.query) + "\n")

        def save_config():
            queue_run.atomic_json(config_path, raw)
            self.queue["config_sha256_at_queue_time"] = queue_run.digest(config_path)

        save_config()
        with contextlib.ExitStack() as stack:
            ready = stack.enter_context(mock.patch.object(queue_run.embedding_run, "index_ready", return_value=True))
            backend = stack.enter_context(mock.patch.object(queue_run.embedding_run, "build_pipeline_backend"))
            stack.enter_context(mock.patch.object(queue_run.embeddings, "open_database", return_value=mock.Mock()))
            stack.enter_context(mock.patch.object(queue_run.benchmark, "build_queries", return_value=([self.query], {})))
            stack.enter_context(mock.patch.object(queue_run, "catalogue_identity", return_value="catalogue"))
            stack.enter_context(mock.patch.object(queue_run, "index_identity", return_value={"index": "fixture"}))
            stack.enter_context(mock.patch.object(queue_run.barcode.CodeLookup, "load", return_value=types.SimpleNamespace(values={})))
            result = queue_run.snapshot(self.queue, self.name, config_path, baseline)
            self.assertEqual(result["workers"], 4)
            self.assertEqual(result["endpoints"]["embedding"], raw["embeddings"][0]["base_url"])
            self.row["workers"] = 1
            with self.assertRaisesRegex(ValueError, "worker policy"):
                queue_run.snapshot(self.queue, self.name, config_path, baseline)
            self.row["workers"] = 4
            raw["embeddings"][0]["base_url"] = "https://8.8.8.8/v1"
            save_config()
            with self.assertRaisesRegex(ValueError, "internal"):
                queue_run.snapshot(self.queue, self.name, config_path, baseline)
            raw["embeddings"][0]["backend"] = "local"
            del raw["embeddings"][0]["base_url"]
            self.row.update(model_backend="local", workers=1)
            save_config()
            result = queue_run.snapshot(self.queue, self.name, config_path, baseline)
            self.assertEqual(result["workers"], 1)
            self.assertEqual(result["endpoints"], {})
            lock_path = self.root / "embeddings/fixture-model/build.lock"
            lock_path.parent.mkdir(parents=True)
            queue_run.atomic_json(lock_path, {"pid": 1234})
            with mock.patch.object(queue_run, "pid_state", return_value={"state": "unknown"}):
                with self.assertRaisesRegex(ValueError, "uncertain build"):
                    queue_run.snapshot(self.queue, self.name, config_path, baseline)
            lock_path.unlink()
            ready.return_value = False
            with self.assertRaisesRegex(ValueError, "not ready"):
                queue_run.snapshot(self.queue, self.name, config_path, baseline)
            backend.assert_not_called()

    def test_gate_binds_identity_age_memory_and_evidence(self):
        queue_run.check_gate(self.gate_path, self.queue_path, self.identity)
        changes = [{"identity_sha256": "wrong"}, {"comparisons_complete": False},
                   {"recorded_at": "2001-01-01T00:00:00+00:00"}, {"evidence": ["relative"]},
                   {"memory": {"available_gib": 25, "additional_required_gib": 10, "margin_gib": 20}}]
        for change in changes:
            queue_run.atomic_json(self.gate_path, dict(self.gate, **change))
            with self.subTest(change=change), self.assertRaises(ValueError):
                queue_run.check_gate(self.gate_path, self.queue_path, self.identity)

    def test_local_gate_requires_cached_weights(self):
        self.identity["model_backend"] = "local"
        self.gate["identity_sha256"] = queue_run.fingerprint(self.identity)
        queue_run.atomic_json(self.gate_path, self.gate)
        with self.assertRaisesRegex(ValueError, "cached weights"):
            queue_run.check_gate(self.gate_path, self.queue_path, self.identity)

    def test_durable_intent_precedes_exactly_one_post(self):
        attempt = self.launch()
        self.assertEqual(attempt["state"], "starting")
        self.assertEqual(attempt["pid"], 1234)
        saved = queue_run.read_json(self.queue_path)["profiles"][0]
        self.assertEqual(saved["attempts"][0], attempt)
        with mock.patch.object(queue_run, "api") as transport, self.assertRaisesRegex(ValueError, "already"):
            queue_run.dispatch(self.queue_path, self.queue, self.identity, self.gate_path, self.jobs, lambda: self.identity)
        transport.assert_not_called()

    def test_api_job_envelope_blocks_a_running_job(self):
        response = {"jobs": [{"name": "other", "state": "running", "pid": 99}], "now": 0}
        with mock.patch.object(queue_run, "api", return_value=(200, response)), self.assertRaisesRegex(ValueError, "active"):
            queue_run.no_active_jobs(self.queue, self.jobs)

    def test_identity_change_after_intent_prevents_post(self):
        with mock.patch.object(queue_run, "api", return_value=(200, {"jobs": [], "now": 0})) as transport:
            attempt = queue_run.dispatch(self.queue_path, self.queue, self.identity, self.gate_path,
                                         self.jobs, lambda: dict(self.identity, workers=1))
        self.assertEqual(attempt["state"], "launch_uncertain")
        self.assertIn("no POST", attempt["error"])
        self.assertEqual([c.args[0] for c in transport.call_args_list], ["GET"])
        self.assertTrue(queue_run.read_json(self.queue_path)["profiles"][0]["attempts"])

    def test_lost_response_is_retained_and_cannot_retry(self):
        attempt = self.launch(error=TimeoutError("response lost"))
        self.assertEqual(attempt["state"], "launch_uncertain")
        self.assertIsNone(attempt["pid"])
        reloaded = queue_run.read_json(self.queue_path)
        with mock.patch.object(queue_run, "api") as transport, self.assertRaises(ValueError):
            queue_run.dispatch(self.queue_path, reloaded, self.identity, self.gate_path, self.jobs, lambda: self.identity)
        transport.assert_not_called()

    def test_other_uncertain_attempt_blocks_dispatch(self):
        self.queue["profiles"].append({"name": "other", "attempts": [{"state": "launch_uncertain"}]})
        with mock.patch.object(queue_run, "api") as transport, self.assertRaisesRegex(ValueError, "reconcile"):
            queue_run.no_active_jobs(self.queue, self.jobs)
        transport.assert_not_called()

    def test_live_unknown_lock_blocks_dispatch(self):
        directory = self.jobs / "other"
        directory.mkdir(parents=True)
        queue_run.atomic_json(directory / "job.lock", {"pid": 987})
        with mock.patch.object(queue_run, "pid_state", return_value={"state": "unknown"}), self.assertRaises(ValueError):
            queue_run.no_active_jobs(self.queue, self.jobs)

    def test_ps_failure_does_not_prove_exit(self):
        with mock.patch.object(queue_run.os, "kill"), mock.patch.object(queue_run.subprocess, "run",
                return_value=types.SimpleNamespace(returncode=1, stdout="")):
            self.assertEqual(queue_run.pid_state(1234)["state"], "unknown")
        with mock.patch.object(queue_run.os, "kill", side_effect=ProcessLookupError):
            self.assertEqual(queue_run.pid_state(1234)["state"], "absent")

    def test_lost_response_recovers_matching_live_lock_before_start(self):
        attempt = self.launch(error=TimeoutError())
        directory = self.jobs / self.name
        directory.mkdir(parents=True)
        queue_run.atomic_json(directory / "job.lock", {"pid": 1234, "started_at":
            datetime.datetime.fromtimestamp(attempt["intent_t"], datetime.timezone.utc).isoformat()})
        with mock.patch.object(queue_run, "pid_state", return_value={"state": "live", "command": self.command()}):
            queue_run.reconcile(attempt, self.runs)
        self.assertEqual(attempt["state"], "running")
        self.assertEqual(attempt["pid"], 1234)

    def test_pid_status_distinguishes_zombie_live_and_malformed_output(self):
        for output, state in (("Z  <defunct>\n", "absent"),
                              ("Ss  " + self.command() + "\n", "live"),
                              ("<defunct>\n", "unknown"),
                              ("Zgarbage <defunct>\n", "unknown"),
                              ("Z <defunct>\nZ <defunct>\n", "unknown")):
            with self.subTest(output=output), mock.patch.object(queue_run.os, "kill"), \
                    mock.patch.object(queue_run.subprocess, "run",
                        return_value=types.SimpleNamespace(returncode=0, stdout=output)):
                observed = queue_run.pid_state(1234)
                self.assertEqual(observed["state"], state)
                if state == "live":
                    self.assertTrue(queue_run.matching_command(observed["command"],
                        {"identity": self.identity, "request": {"configuration": self.name,
                         "set": "my", "workers": 4}, "jobs_dir": str(self.jobs)}))
                if state == "absent":
                    self.assertEqual(observed["process_status"], "Z")

    def test_zombie_completion_still_requires_complete_artifacts(self):
        attempt = self.launch()
        valid = copy.deepcopy(attempt)
        self.events(attempt)
        with mock.patch.object(queue_run.os, "kill"), mock.patch.object(queue_run.subprocess, "run",
                return_value=types.SimpleNamespace(returncode=0, stdout="Z  <defunct>\n")):
            queue_run.reconcile(attempt, self.runs, self.identity)
        self.assertEqual(attempt["state"], "invalid_completion")
        self.assertTrue(attempt["runner_exit_verified"])
        self.artifacts()
        with mock.patch.object(queue_run.os, "kill"), mock.patch.object(queue_run.subprocess, "run",
                return_value=types.SimpleNamespace(returncode=0, stdout="Z  <defunct>\n")):
            queue_run.reconcile(valid, self.runs, self.identity)
        self.assertEqual(valid["state"], "done")

    def test_unknown_launch_never_becomes_success_from_old_log(self):
        attempt = self.launch(error=TimeoutError())
        self.events(attempt)
        log = Path(attempt["log"])
        data = log.read_text().replace(str(attempt["intent_t"] + 1), "1")
        log.write_text(data)
        with mock.patch.object(queue_run, "pid_state", return_value={"state": "unknown", "command": None}):
            queue_run.reconcile(attempt, self.runs)
        self.assertEqual(attempt["state"], "launch_uncertain")

    def test_completion_needs_exited_pid_and_full_persisted_coverage(self):
        attempt = self.launch()
        self.events(attempt)
        self.artifacts()
        with mock.patch.object(queue_run, "pid_state", return_value={"state": "live", "command": self.command()}):
            queue_run.reconcile(attempt, self.runs, self.identity)
        self.assertEqual(attempt["state"], "running")
        with mock.patch.object(queue_run, "pid_state", return_value={"state": "absent", "command": None}):
            queue_run.reconcile(attempt, self.runs, self.identity)
        self.assertEqual(attempt["state"], "done")
        self.assertTrue(attempt["runner_exit_verified"])
        self.assertEqual(attempt["metrics"]["positive"]["recall_at_1"], 1)
        self.assertTrue((Path(attempt["archive"]) / "job.log").is_file())

    def test_completion_rejects_errors_coverage_truth_and_input_drift(self):
        attempt = self.launch()
        self.events(attempt)
        directory = self.artifacts()
        valid = dict(self.query, error=None, predicted_slug="other", latency_ms=1.0)
        cases = [(dict(valid, error="failed"), self.identity),
                 (dict(valid, slug="wrong"), self.identity),
                 (valid, dict(self.identity, workers=1))]
        for result, current in cases:
            (directory / "results.jsonl").write_text(json.dumps(result) + "\n")
            candidate = copy.deepcopy(attempt)
            with mock.patch.object(queue_run, "pid_state", return_value={"state": "absent", "command": None}):
                queue_run.reconcile(candidate, self.runs, current)
            self.assertEqual(candidate["state"], "invalid_completion")

    def test_fallback_trace_error_rejects_completion_and_records_count(self):
        attempt = self.launch()
        self.events(attempt)
        directory = self.artifacts()
        result = dict(self.query, error=None, predicted_slug="other", latency_ms=1.0,
                      trace={"steps": [{"id": "cluster_rules", "out": {"error": "timeout"}}]})
        (directory / "results.jsonl").write_text(json.dumps(result) + "\n")
        with mock.patch.object(queue_run, "pid_state", return_value={"state": "absent", "command": None}):
            queue_run.reconcile(attempt, self.runs, self.identity)
        self.assertEqual(attempt["state"], "invalid_completion")
        self.assertEqual(attempt["degraded_queries"], 1)

    def test_predictions_must_exist_match_results_and_are_hashed(self):
        attempt = self.launch()
        events = self.events(attempt)
        directory = self.artifacts()
        valid = queue_run.complete_artifacts(attempt, events[-1], self.runs)
        self.assertIn("predictions.jsonl", valid["artifact_sha256"])
        path = directory / "predictions.jsonl"
        path.write_text("")
        with self.assertRaisesRegex(ValueError, "predictions"):
            queue_run.complete_artifacts(attempt, events[-1], self.runs)
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            queue_run.complete_artifacts(attempt, events[-1], self.runs)

    def test_wrong_start_policy_is_not_accepted(self):
        attempt = self.launch()
        self.events(attempt, wrong_start={"use_cache": False})
        with mock.patch.object(queue_run, "pid_state", return_value={"state": "absent", "command": None}):
            queue_run.reconcile(attempt, self.runs, self.identity)
        self.assertEqual(attempt["state"], "launch_uncertain")

    def test_stopped_job_never_counts_as_success(self):
        attempt = self.launch()
        self.events(attempt, final="stopped")
        with mock.patch.object(queue_run, "pid_state", return_value={"state": "absent", "command": None}):
            queue_run.reconcile(attempt, self.runs, self.identity)
        self.assertEqual(attempt["state"], "stopped")

    def test_terminal_attempt_is_stable_if_live_log_is_replaced(self):
        attempt = self.launch()
        attempt.update(state="done", run_id="saved")
        with mock.patch.object(queue_run.run_jobs, "read_events") as read:
            self.assertIs(queue_run.reconcile(attempt, self.runs), attempt)
        read.assert_not_called()
        self.assertEqual(attempt["state"], "done")

    def test_mismatched_run_directory_cannot_count_as_success(self):
        attempt = self.launch()
        events = self.events(attempt)
        events[1]["run_id"] = "different-run"
        Path(attempt["log"]).write_text("".join(json.dumps(e) + "\n" for e in events))
        with mock.patch.object(queue_run, "pid_state", return_value={"state": "absent", "command": None}):
            queue_run.reconcile(attempt, self.runs, self.identity)
        self.assertEqual(attempt["state"], "launch_uncertain")


if __name__ == "__main__":
    unittest.main()
