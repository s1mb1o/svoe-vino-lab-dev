"""Offline fixtures for the queue snapshot. No production modules are imported."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/summarize_internal_profile_queue.py"
SPEC = importlib.util.spec_from_file_location("queue_report", SCRIPT)
reporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reporter)


class QueueReportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.queue_path = self.root / "queue.json"
        self.queue = {"query_count_at_queue_time": 3, "set": "my",
                      "external_recognizer_approval": "pending", "profiles": []}

    def profile(self, name="example", state="pending"):
        row = {"name": name, "authorized_to_start": name != reporter.EXTERNAL,
               "status": state, "workers": 4, "use_cache": True, "use_barcode": True,
               "embedding": "example-index", "model_backend": "openai"}
        self.queue["profiles"].append(row)
        return row

    def done(self, row, barcode=True):
        archive = self.root / row["name"]
        archive.mkdir()
        queries = [{"query_id": "q%d" % n, "image_sha256": "image%d" % (n % 2),
                    "label": "positive" if n < 2 else "negative"} for n in range(3)]
        attempt = {"id": row["name"] + "-attempt", "state": "done", "archive": str(archive),
            "run_id": "run-" + row["name"], "pid": 10, "runner_exit_verified": True,
            "intent_t": 100, "degraded_queries": 0,
            "request": {"configuration": row["name"], "workers": 4, "set": "my", "use_cache": True, "use_barcode": True},
            "identity": {"queries": queries, "catalogue": "same-catalogue", "has_barcode": barcode},
            "final_event": {"event": "done", "run_id": "run-" + row["name"], "answered": 3, "errors": 0, "t": 106},
            "run": {"run_id": "run-" + row["name"], "configuration": row["name"], "finished": "finished", "answered": 3,
                    "use_cache": True, "use_barcode": True if barcode else None, "wall_s": 5,
                    "options": {"set": "my", "workers": 4, "limit": None},
                    "embeddings": {"items": {"current": 10, "missing": 2}}},
            "metrics": {"run_id": "run-" + row["name"], "queries": {"total": 3, "positive": 2, "negative": 1},
                "positive": {"n": 2, "errors": 0, "recall_at_1": 0.5, "recall_at_5": 1.0},
                "negative": {"n": 1, "errors": 0, "false_match_at_1": 0},
                "latency_ms": {"median": 100, "p95": 200}},
            "artifact_sha256": {name: "a" * 64 for name in reporter.ARTIFACTS}}
        row["attempts"] = [attempt]
        row["status"] = "done"
        self.archive(attempt)
        return attempt

    def archive(self, attempt):
        (Path(attempt["archive"]) / "attempt.json").write_text(json.dumps(attempt))

    def save(self):
        self.queue_path.write_text(json.dumps(self.queue))

    def build(self):
        self.save()
        return reporter.build_report(self.queue_path, expected_unique=2)

    def test_all_names_external_and_pending_remain_visible(self):
        self.profile(reporter.EXTERNAL, "awaiting_user_approval")
        for i in range(53):
            self.profile("profile-%02d" % i)
        report = self.build()
        self.assertEqual((report["profile_count"], report["authorized_profile_count"]), (54, 53))
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["profiles"][0]["state"], "awaiting_user_approval")
        text = reporter.markdown(report)
        for row in self.queue["profiles"]:
            self.assertIn(row["name"], text)
        self.assertIn("does not establish new-image demo latency", text)

    def test_done_retains_metric_scope_and_effective_barcode(self):
        self.done(self.profile(), barcode=False)
        report = self.build()
        a = report["profiles"][0]["latest_attempt"]
        self.assertTrue(a["complete"])
        self.assertFalse(a["barcode_configured"])
        self.assertTrue(a["barcode_requested"])
        self.assertEqual(a["coverage"]["identity_unique_images"], 2)
        self.assertEqual(a["run_rows_per_second"], 0.6)
        self.assertEqual((a["run_wall_s"], a["recorded_attempt_elapsed_s"]), (5, 6))
        self.assertEqual(a["positive"]["n"], 2)
        self.assertEqual(a["negative"]["n"], 1)

    def test_done_requires_terminal_coverage_and_hash_evidence(self):
        for change in [lambda a: a.pop("runner_exit_verified"),
                       lambda a: a["run"].update(answered=2),
                       lambda a: a["artifact_sha256"].pop("predictions.jsonl"),
                       lambda a: a.update(degraded_queries=1),
                       lambda a: a["metrics"]["positive"].update(n=3),
                       lambda a: a["metrics"].update(run_id="another-run")]:
            row = self.profile("p%d" % len(self.queue["profiles"]))
            a = self.done(row)
            change(a)
            self.archive(a)
        report = self.build()
        self.assertEqual(report["complete_authorized_profiles"], 0)
        self.assertTrue(all(p["state"] == "unverified_completion" for p in report["profiles"]))

    def test_archive_drift_never_confirms_complete(self):
        a = self.done(self.profile())
        a["observed_t"] = 200
        report = self.build()
        self.assertEqual(report["profiles"][0]["state"], "unverified_completion")
        self.assertIn("archived attempt differ", str(report))

    def test_queue_done_without_attempt_is_unverified(self):
        self.profile(state="done")
        report = self.build()
        self.assertEqual(report["profiles"][0]["state"], "unverified_completion")
        self.assertEqual(report["state_counts"], {"unverified_completion": 1})
        self.assertIn("no attempt records prove completion", reporter.markdown(report))

    def test_partial_progress_failed_attempts_and_missing_archive(self):
        row = self.profile(state="running")
        first = self.done(row)
        first.update(state="failed", error="model unavailable")
        self.archive(first)
        second = {"id": "second", "state": "running", "progress": {"done": 1, "errors": 0},
                  "request": {"workers": 4}, "run_id": "partial-run", "archive": str(self.root / "absent")}
        row["attempts"].append(second)
        report = self.build()
        p = report["profiles"][0]
        self.assertEqual((p["attempt_count"], p["state"]), (2, "running"))
        self.assertEqual(p["latest_attempt"]["coverage"]["observed_rows"], 1)
        self.assertIsNone(p["latest_attempt"]["run_rows_per_second"])
        self.assertIn("model unavailable", reporter.markdown(report))
        self.assertIn("Archived attempt is unavailable", reporter.markdown(report))

    def test_unavailable_terminal_profile_stays_visible(self):
        row = self.profile(state="unavailable")
        row["reason"] = "required model weights unavailable"
        report = self.build()
        self.assertEqual(report["status"], "terminal_with_failures")
        self.assertEqual(report["terminal_authorized_profiles"], 1)
        self.assertIn(row["reason"], reporter.markdown(report))

    def test_label_comparison_requires_matching_complete_inputs(self):
        base = self.done(self.profile(reporter.COUNTERPART))
        label = self.profile(reporter.LABEL)
        self.assertEqual(self.build()["label_comparison"]["state"], "pending")
        a = self.done(label)
        a["metrics"]["positive"]["recall_at_1"] = 1.0
        self.archive(a)
        result = self.build()["label_comparison"]
        self.assertEqual(result["state"], "complete")
        self.assertEqual(result["label_minus_counterpart"]["recall_at_1"], 0.5)
        a["metrics"]["positive"]["recall_at_1"] = 0.25
        self.archive(a)
        self.assertIn("-25.00 percentage points", reporter.markdown(self.build()))
        a["identity"]["catalogue"] = "different"
        self.archive(a)
        self.assertEqual(self.build()["label_comparison"]["state"], "not_comparable")

    def test_output_is_explicit_new_and_queue_stays_identical(self):
        self.profile()
        self.save()
        before = self.queue_path.read_bytes()
        output = self.root / "report"
        argv = ["--queue", str(self.queue_path), "--output", str(output), "--expected-unique", "2"]
        self.assertEqual(reporter.main(argv), 0)
        original = (output / "queue-summary.json").read_bytes()
        self.assertEqual(reporter.main(argv), 2)
        self.assertEqual((output / "queue-summary.json").read_bytes(), original)
        self.assertEqual(self.queue_path.read_bytes(), before)

    def test_duplicate_names_are_refused(self):
        self.profile()
        self.profile()
        with self.assertRaisesRegex(ValueError, "duplicate profile"):
            self.build()


if __name__ == "__main__":
    unittest.main()
