"""Test offline reporting with metadata fixtures. Read no image or live service."""
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import summarize_recognition_http as report


class ReportTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run = self.root / "run"
        self.run.mkdir()
        self.rows = [{"query_id": "q-%06d" % (n + 1), "image_sha256": "%064d" % n,
                      "label": "positive" if n < 54 else "negative", "truth": ["wine-%d" % n],
                      "selection_reasons": ["baseline_barcode_hit" if n < 24 else "other"]}
                     for n in range(64)]
        self.rows[24]["query_id"], self.rows[25]["query_id"] = "q-000483", "q-000484"
        self.rows[25]["image_sha256"] = self.rows[24]["image_sha256"]
        self.rows[55]["image_sha256"] = self.rows[27]["image_sha256"]
        self.rows[57]["image_sha256"] = self.rows[56]["image_sha256"]
        selection = [report.projection(row) for row in self.rows]
        self.frozen = {"rows": self.rows, "selection": selection,
                       "selection_fingerprint": report.digest(selection),
                       "baseline_artifact_hashes": {"queries.jsonl": "queries", "results.jsonl": "results"}}
        self.selection = self.root / "selection.json"
        self.write(self.selection, self.frozen)
        self.manifest = {"selection": selection, "selection_fingerprint": report.digest(selection),
                         "baseline_hashes": self.frozen["baseline_artifact_hashes"],
                         "profile": "test", "modes": ["persistent"], "variants": ["full"]}
        self.write(self.run / "manifest.json", self.manifest)
        self.records = []
        for n, row in enumerate(self.rows):
            slug = row["truth"][0] if row["label"] == "positive" else "not-excluded"
            self.records.append(dict(row, mode="persistent", variant="full", session_first=n == 0,
                                     client_wall_ms=4500 if n == 0 else 1000, http_status=200,
                                     response_complete=True, latency_censored=False, transport_error=None,
                                     error=None, degraded=False, startup_ms=400 if n == 0 else 0,
                                     build_ms=200 if n == 0 else 0, service_setup_ms=10 if n == 0 else 0,
                                     source_read_ms=2, json_parse_ms=1, ask_wall_ms=500,
                                     stage_ms={"barcode": 30, "cluster-rerank": 300},
                                     telemetry={"upload_ms": 15, "steps_answer_ms": 20, "process_ms": 510},
                                     answer={"event": "answer", "ask_wall_ms": 500,
                                             "candidates": [{"slug": slug}], "error": None,
                                             "http_status": 200, "trace": {"steps": []}, "decode_errors": 0}))
        self.save_records()
        self.write(self.run / "complete.json", {"manifest_fingerprint": report.digest(self.manifest)})

    def write(self, path, data):
        path.write_text(json.dumps(data))

    def save_records(self, records=None):
        (self.run / "persistent-full.jsonl").write_text("".join(json.dumps(r) + "\n" for r in
                                                               (self.records if records is None else records)))

    def build(self):
        return report.build_report(self.run, self.selection)

    def test_fixed_denominators_strata_uniques_and_conflict_sensitivity(self):
        out = self.build()
        session = out["sessions"][0]
        self.assertEqual(out["status"], "complete")
        self.assertEqual((out["selected_rows"], out["selected_unique_images"]), (64, 61))
        self.assertEqual(out["selected_labels"], {"positive": 54, "negative": 10})
        self.assertEqual(session["full"]["positive_denominator"], 54)
        self.assertEqual(session["full"]["correct_within_3s"], 53)
        self.assertEqual(session["full"]["correct_late"], 1)
        self.assertEqual(session["strata"]["baseline_barcode_hit"]["selected_rows"], 24)
        self.assertEqual(session["strata"]["other_selected_rows"]["selected_rows"], 40)
        self.assertEqual(session["sensitivity"]["positive_denominator"], 52)
        self.assertEqual(session["sensitivity"]["selected_rows"], 62)
        self.assertEqual(session["sensitivity"]["correct_within_3s"], 51)
        self.assertEqual(session["full"]["negative_forbidden_top1"], 0)

    def test_censored_and_degraded_failures_remain_in_all_denominators(self):
        failed = self.records[1]
        failed.update(client_wall_ms=25, response_complete=False, latency_censored=True,
                      transport_error="disconnected", error="disconnected", within_3s=True, correct_within_3s=True)
        self.records[2]["answer"]["decode_errors"] = 1
        self.records[54]["answer"]["candidates"] = [{"slug": self.rows[54]["truth"][0]}]
        self.save_records()
        first = self.build()["sessions"][0]
        again = self.build()["sessions"][0]
        self.assertEqual(first, again)
        self.assertEqual(first["full"]["observed_rows"], 64)
        self.assertEqual(first["full"]["positive_denominator"], 54)
        self.assertEqual(first["full"]["correct_within_3s"], 51)
        self.assertEqual(first["full"]["censored_rows"], 1)
        self.assertEqual(first["full"]["degraded"], 1)
        self.assertEqual(first["full"]["complete_within_3s"], 62)
        self.assertEqual(first["full"]["negative_forbidden_top1_share"], .1)
        self.assertEqual(first["full"]["complete_http_wall_ms"]["observations"], 63)
        self.assertEqual(first["full"]["http_wait_all_attempts_ms"]["observations"], 64)

    def test_partial_keeps_selected_denominators_and_lists_pending_rows(self):
        self.save_records(self.records[:3])
        out = self.build()
        full = out["sessions"][0]["full"]
        self.assertEqual(out["status"], "partial")
        self.assertEqual((full["observed_rows"], full["pending_rows"]), (3, 61))
        self.assertEqual(full["positive_denominator"], 54)
        self.assertEqual(full["correct_within_3s_share"], 2 / 54)
        (self.run / "persistent-full.jsonl").unlink()
        self.assertEqual(self.build()["sessions"][0]["full"]["pending_rows"], 64)

    def test_failed_child_placeholder_timings_are_missing_but_http_failure_stays(self):
        failed = self.records[3]
        failed.update(client_wall_ms=300700, http_status=503, error="child watchdog",
                      startup_ms=0, build_ms=0, ask_wall_ms=0, stage_ms={},
                      telemetry={"upload_ms": 15, "adapter_error": "child watchdog"},
                      answer={"candidates": [], "error": "child watchdog", "http_status": 503})
        self.save_records()
        out = self.build(); session = out["sessions"][0]
        full = session["full"]
        self.assertEqual((full["observed_rows"], full["positive_denominator"], full["errors"]), (64, 54, 1))
        self.assertEqual((full["correct_within_3s"], full["censored_rows"]), (52, 0))
        self.assertEqual(full["complete_http_wall_ms"]["observations"], 64)
        self.assertEqual(full["complete_http_wall_ms"]["max"], 300700)
        for key in ("startup_ms", "build_ms", "ask_wall_ms"):
            component = session["components_all_observed"][key]
            self.assertEqual((component["observations"], component["missing_observations"]), (63, 1))
            self.assertEqual(component["missing_query_ids"], [failed["query_id"]])
            after = session["components_after_session_first"][key]
            self.assertEqual((after["observations"], after["missing_observations"]), (62, 1))
        self.assertIsNone(session["observations"][3]["startup_ms"])
        self.assertIsNone(session["observations"][3]["build_ms"])
        self.assertEqual(session["components_all_observed"]["upload_ms"]["observations"], 64)
        self.assertIn("| startup_ms | 63 | 1 |", report.markdown(out))
        self.assertIn("placeholder zeros", report.markdown(out))

        # A first-request failure must also display unknown startup, not a zero.
        failed["session_first"] = True
        self.save_records()
        first = self.build()["sessions"][0]["first_requests"][1]
        self.assertIsNone(first["startup_ms"])
        self.assertIsNone(first["build_ms"])

    def test_real_child_timings_survive_error_status_and_persistent_zero_startup(self):
        record = self.records[1]
        record.update(error="later response failure", http_status=503)
        self.assertEqual(report.child_timing(record, "startup_ms"), 0)
        self.assertEqual(report.child_timing(record, "build_ms"), 0)
        self.assertEqual(report.child_timing(record, "ask_wall_ms"), 500)
        record["answer"] = {"error": "child watchdog", "http_status": 503}
        record["telemetry"]["startup_ms"] = 125
        record["startup_ms"] = 125
        self.assertEqual(report.child_timing(record, "startup_ms"), 125)
        self.assertIsNone(report.child_timing(record, "build_ms"))
        self.assertIsNone(report.child_timing(record, "ask_wall_ms"))

    def test_later_session_start_and_later_remote_cold_cost_are_retained(self):
        self.records[8].update(session_first=True, startup_ms=500, client_wall_ms=7000)
        self.records[4]["stage_ms"]["cluster-rerank"] = 210000
        self.records[4]["client_wall_ms"] = 211000
        self.save_records()
        out = self.build(); session = out["sessions"][0]
        self.assertEqual(len(session["first_requests"]), 2)
        self.assertEqual(session["after_session_first_observed"]["observed_rows"], 62)
        self.assertEqual(session["after_session_first_observed"]["complete_http_wall_ms"]["max"], 211000)
        self.assertEqual(session["observations"][4]["stage_ms"]["cluster-rerank"], 210000)
        self.assertTrue(any("does not prove warm" in note for note in out["notes"]))
        self.assertFalse(out["hard_timeout_implemented"])
        self.assertEqual(session["components_all_observed"]["upload_ms"]["median"], 15)
        self.assertEqual(session["components_all_observed"]["steps_answer_ms"]["median"], 20)

    def test_identity_changes_duplicate_queries_and_truncated_records_are_refused(self):
        bad = copy.deepcopy(self.records)
        for key, value in (("image_sha256", "changed"), ("truth", ["changed"]), ("label", "negative")):
            with self.subTest(key=key):
                bad = copy.deepcopy(self.records); bad[0][key] = value; self.save_records(bad)
                with self.assertRaisesRegex(ValueError, "identity or frozen labels"):
                    self.build()
        self.save_records(self.records + [self.records[0]])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.build()
        self.save_records()
        with (self.run / "persistent-full.jsonl").open("a") as stream:
            stream.write('{"query_id":')
        with self.assertRaisesRegex(ValueError, "no row was silently dropped"):
            self.build()

    def test_selection_baseline_and_completion_fingerprints_are_required(self):
        for key in ("selection_fingerprint", "baseline_hashes"):
            bad = copy.deepcopy(self.manifest)
            bad[key] = "bad" if key == "selection_fingerprint" else {}
            self.write(self.run / "manifest.json", bad)
            with self.assertRaises(ValueError):
                self.build()
        self.write(self.run / "manifest.json", self.manifest)
        self.write(self.run / "complete.json", {"manifest_fingerprint": "bad"})
        with self.assertRaisesRegex(ValueError, "completion marker"):
            self.build()

    def test_failure_artifact_without_complete_coverage_is_not_hidden(self):
        self.save_records(self.records[:2])
        self.write(self.run / "persistent-full.failure.json", {"query_id": "q-000003", "error": "launch failed"})
        out = self.build()
        self.assertEqual(out["status"], "partial")
        self.assertEqual(out["sessions"][0]["failure_artifact"]["error"], "launch failed")
        self.assertIn("launch failed", report.markdown(out))

    def test_cli_writes_only_offline_reports(self):
        output = self.root / "reports"
        before = {path.name: path.read_bytes() for path in self.run.iterdir()}
        with contextlib.redirect_stdout(io.StringIO()):
            code = report.main(["--run", str(self.run), "--selection", str(self.selection), "--output", str(output)])
        self.assertEqual(code, 0)
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.run.iterdir()})
        self.assertEqual({p.name for p in output.iterdir()}, {"http-comparison.json", "http-comparison.md"})
        text = (output / "http-comparison.md").read_text()
        self.assertIn("q-000483, q-000484", text)
        self.assertIn("upload_ms", text)
        self.assertIn("steps_answer_ms", text)
        self.assertIn("not a corpus estimate", text)


if __name__ == "__main__":
    unittest.main()
