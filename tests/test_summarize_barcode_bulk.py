"""Use small JSON fixtures. Do not decode images or invoke a model or process."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import summarize_barcode_bulk as report


class BulkReportTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.runs = self.root / "runs"
        self.bulk = self.root / "reports" / "bulk"
        self.bulk.mkdir(parents=True)
        self.queries = [{"query_id": "q%d" % n, "image_path": "photo.jpg", "image_sha256": "same",
                         "slug": "wine", "label": "positive", "truth": ["wine"]} for n in (1, 2)]
        self.answers = [dict(q, predicted_slug="wine", rank_of_truth=1, outcome="hit", error=None,
                             candidates=[{"slug": "wine", "rank": 1}, {"slug": "other", "rank": 2}],
                             latency_ms=100, trace={"steps": [{"id": "barcode", "cached": True, "ms": 1}]})
                        for q in self.queries]
        self.baseline = self.write_run("baseline", self.answers)

    def save(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) + "\n")

    def write_rows(self, path, rows):
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    def write_run(self, name, rows):
        path = self.runs / name
        path.mkdir(parents=True, exist_ok=True)
        self.save(path / "run.json", {"run_id": name, "answered": 2, "finished": "done", "wall_s": 7.5})
        self.save(path / "metrics.json", {"queries": {"total": len(rows)}})
        self.write_rows(path / "queries.jsonl", self.queries)
        self.write_rows(path / "results.jsonl", rows)
        self.write_rows(path / "predictions.jsonl", [{key: row[key] for key in
                                                    ("query_id", "image_path", "image_sha256", "predicted_slug")}
                                                   for row in rows])
        return path

    def variant(self, name="cold-1", rows=None, supervisor_state="exited"):
        rows = self.answers if rows is None else rows
        run = self.write_run(name, rows)
        stats = report.observed_stats({row["query_id"]: row for row in rows})
        self.save(self.bulk / (name + ".summary.json"), {
            "run_id": name, "run_dir": str(run), "complete": True, "queries": len(rows),
            "unique_images": stats["unique_image_digests"], "errors": stats["errors"],
            "degraded_queries": stats["degraded_rows"], "barcode_cache_hits": stats["barcode_cache_hits"],
            "native_errors": 0, "native_calls": 0, "input_drift": False,
            "warm_cache_misses": 0 if name.startswith("warm-") else None, "wall_s": 8, "build_ms": 250})
        self.save(self.bulk / (name + ".intent.json"),
                  {"run_id": name, "status": "done", "finished": "done", "pid": 123})
        self.save(self.bulk.parent / ("bulk-" + name + "-process.json"),
                  {"state": supervisor_state, "exit_code": 0 if supervisor_state == "exited" else None,
                   "ended_at": "done" if supervisor_state == "exited" else None,
                   "process_wall_s": 10, "pid": 123})
        return run

    def build(self):
        return report.build_report(self.baseline, self.bulk, self.bulk.parent, self.runs, 2, 1)

    def test_query_join_ignores_artifact_order_and_compares_completed_variants(self):
        self.variant(rows=list(reversed(self.answers)))
        changed = copy.deepcopy(self.answers)
        changed[0].update(predicted_slug="other", rank_of_truth=2, outcome="miss")
        changed[0]["candidates"] = [{"slug": "other", "rank": 1}, {"slug": "wine", "rank": 2}]
        self.variant("warm-1", changed)
        out = self.build()
        baseline_pair = next(c for c in out["comparisons"] if c["right"] == "cold-1")
        self.assertEqual(baseline_pair["matched_rows"], 2)
        self.assertFalse(any(baseline_pair["changed_counts"].values()))
        paired = next(c for c in out["comparisons"] if c["left"] == "cold-1")
        self.assertEqual(paired["scope"], "complete paired runs")
        self.assertEqual(paired["changed_query_ids"]["rank_of_truth"], ["q1"])
        self.assertEqual(paired["changed_counts"]["candidate_ranks"], 1)
        self.assertEqual(paired["changed_counts"]["outcome"], 1)
        self.assertEqual([v["state"] for v in out["variants"]], ["complete", "complete", "missing", "missing"])
        self.assertFalse(out["all_variants_complete"])

    def test_summary_does_not_certify_missing_results_or_predictions(self):
        path = self.variant(rows=self.answers[:1])
        out = self.build()
        first = out["variants"][0]
        self.assertFalse(first["complete"])
        self.assertEqual(first["artifact_inspection"]["coverage"]["missing_result_ids"], ["q2"])
        self.assertEqual(first["observed"]["rows"], 1)
        self.assertIsNone(first["timing"]["complete_queries_per_process_s"])
        self.assertEqual(out["comparisons"][0]["scope"], "partial matched rows only")
        # The report must not change or truncate a partial result artifact.
        before = (path / "results.jsonl").read_bytes()
        self.build()
        self.assertEqual((path / "results.jsonl").read_bytes(), before)

    def test_supervisor_exit_intent_and_run_finish_are_all_required(self):
        run = self.variant(supervisor_state="running")
        first = self.build()["variants"][0]
        self.assertEqual(first["state"], "recorded_running")
        self.assertIsNone(first["timing"]["process_wall_s"])
        self.variant()
        self.save(self.bulk / "cold-1.intent.json", {"run_id": "cold-1", "status": "started", "pid": 123})
        self.assertFalse(self.build()["variants"][0]["complete"])
        self.variant()
        self.save(run / "run.json", {"run_id": "cold-1", "answered": 2})
        self.assertFalse(self.build()["variants"][0]["complete"])

    def test_process_wall_is_distinct_from_harness_and_loop_wall(self):
        self.variant()
        timing = self.build()["variants"][0]["timing"]
        self.assertEqual(timing["harness_wall_s"], 8)
        self.assertEqual(timing["process_wall_s"], 10)
        self.assertEqual(timing["benchmark_loop_wall_s"], 7.5)
        self.assertEqual(timing["outside_harness_wall_s"], 2)
        self.assertEqual(timing["complete_queries_per_process_s"], 0.2)
        self.assertIn("not pure startup", timing["note"])
        self.assertEqual(timing["first_observed_query"]["latency_ms"], 100)

    def test_missing_metrics_cannot_certify_a_complete_run(self):
        run = self.variant()
        (run / "metrics.json").unlink()
        item = self.build()["variants"][0]
        self.assertFalse(item["complete"])
        self.assertTrue(any("metrics.json" in issue for issue in item["issues"]))

    def test_warm_miss_degraded_trace_and_native_error_prevent_success(self):
        changed = copy.deepcopy(self.answers)
        changed[0]["trace"]["steps"][0]["cached"] = False
        self.variant("warm-1", changed)
        self.assertFalse(self.build()["variants"][1]["complete"])
        changed[0]["trace"]["steps"].append({"id": "cluster_rules", "out": {"error": "offline"}})
        self.variant(rows=changed)
        first = self.build()["variants"][0]
        self.assertEqual(first["observed"]["degraded_rows"], 1)
        self.assertFalse(first["complete"])
        self.variant()
        path = self.bulk / "cold-1.summary.json"
        value = json.loads(path.read_text())
        value["native_errors"] = 1
        self.save(path, value)
        self.assertFalse(self.build()["variants"][0]["complete"])

    def test_duplicate_ids_changed_identity_and_partial_final_line_stay_explicit(self):
        run = self.variant()
        rows = copy.deepcopy(self.answers)
        rows[0]["image_sha256"] = "changed"
        self.write_rows(run / "results.jsonl", rows)
        out = self.build()
        self.assertEqual(out["comparisons"][0]["matched_rows"], 1)
        self.assertFalse(out["variants"][0]["complete"])
        self.write_rows(run / "results.jsonl", self.answers + self.answers[:1])
        with (run / "results.jsonl").open("a") as stream:
            stream.write('{"query_id":')
        first = self.build()["variants"][0]
        self.assertTrue(any("Duplicate query IDs" in issue for issue in first["issues"]))
        self.assertTrue(any("Invalid record" in issue for issue in first["issues"]))
        self.assertEqual(first["observed"]["rows"], 1)
        self.assertFalse(first["complete"])

    def test_cli_writes_only_explicit_new_outputs(self):
        self.variant()
        target_json, target_md = self.root / "report.json", self.root / "report.md"
        args = ["--baseline-run", str(self.baseline), "--bulk-dir", str(self.bulk),
                "--expected-rows", "2", "--expected-digests", "1",
                "--output-json", str(target_json), "--output-md", str(target_md)]
        self.assertFalse(target_json.exists())
        self.assertEqual(report.main(args), 0)
        self.assertEqual(json.loads(target_json.read_text())["expected_unique_image_digests"], 1)
        self.assertIn("2 query rows and 1 unique image digests", target_md.read_text())
        self.assertIn("MUST verify actual PID commands", target_md.read_text())
        old = target_json.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            report.main(args)
        self.assertEqual(target_json.read_bytes(), old)


if __name__ == "__main__":
    unittest.main()
