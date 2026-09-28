"""Check crop geometry and benchmark safety with fake images and decoders."""
import json
import contextlib
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import benchmark_barcode_crops as bench

CODE = {"kind": "barcode", "format": "EAN13", "text": "4631168664979"}
UNKNOWN = {"kind": "barcode", "format": "EAN13", "text": "4600682000181"}
LOOKUP = bench.base.barcode.CodeLookup({("gtin", "04631168664979"): ["wine-a"]})


class FakeImage:
    size = (1000, 1000)

    def __init__(self, name="whole"):
        self.name = name

    def crop(self, box):
        return FakeImage(tuple(box))

    def close(self):
        pass


class FakeDecoder:
    answers = {}
    seen = []

    def __init__(self, options):
        self.calls = self.decode_errors = 0

    def scaled(self, image):
        return image

    def read(self, image):
        self.seen.append(image.name)
        self.calls += 2
        return self.answers.get(image.name, [])


def prepared(status="available"):
    boxes = [[10, 20, 30, 40], [50, 60, 70, 80]] if status == "available" else []
    return {"image_sha256": "abc", "path": "/fake/image.jpg", "prep_ms": 17,
            "regions": {name: {"status": status, "boxes": boxes} for name in bench.REGIONS}}


def query(label="positive", truth=None):
    return {"query_id": "q-1", "image_sha256": "abc", "label": label,
            "truth": ["wine-a"] if truth is None else truth, "slug": "wine-a",
            "baseline_step": {"out": {"hit": LOOKUP.find([CODE])}}}


class CropTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        FakeDecoder.answers, FakeDecoder.seen = {}, []

    def test_axis_ratios_rounding_margin_and_clamping(self):
        self.assertEqual(bench.rectangle([33, 25, 66, 50], (1000, 1000), (333, 250)),
                         [99, 100, 199, 200])
        self.assertEqual(bench.rectangle([10, 20, 50, 40], (200, 300), (100, 100), .1),
                         [12, 54, 108, 126])
        self.assertEqual(bench.rectangle([-10, -20, 110, 120], (100, 100)), [0, 0, 100, 100])
        for box in ([3, 3, 2, 4], [100, 1, 101, 2], [0, 0, float("nan"), 2], [1, 2]):
            with self.subTest(box=box), self.assertRaises(ValueError):
                bench.rectangle(box, (100, 100))

    def test_detection_order_and_unavailable_states(self):
        answer = {"width": 100, "height": 100, "instances": [
            {"label": "barcode", "box": [40, 40, 60, 60], "score": .8},
            {"label": "barcode", "box": [0, 0, 10, 10], "score": .9},
            {"label": "barcode", "box": [20, 20, 40, 40], "score": .9},
            {"label": "barcode", "box": [5, 5, 1, 1]}]}
        result = bench.detected_boxes(answer, "barcode", (100, 100))
        self.assertEqual(result["boxes"], [[20, 20, 40, 40], [40, 40, 60, 60], [0, 0, 10, 10]])
        self.assertEqual(result["invalid_boxes"], 1)
        self.assertEqual(bench.detected_boxes(answer, "bottle", (100, 100))["status"], "missing_detection")
        self.assertEqual(bench.detected_boxes({"instances": []}, "bottle", (100, 100))["status"], "invalid_answer_dimensions")
        answer["instances"] = [{"label": "bottle", "box": [3, 2, 1, 4]}]
        self.assertEqual(bench.detected_boxes(answer, "bottle", (100, 100))["status"], "invalid_box")

    def test_cache_client_blocks_network_and_store_and_requires_reads(self):
        client = bench.ReadOnlySam3()
        answer = {"width": 100, "height": 90, "instances": []}
        with mock.patch.object(client.session, "post") as network, \
                mock.patch.object(bench.model_cache, "store") as store, \
                mock.patch.object(Path, "exists", return_value=True), \
                mock.patch.object(bench.model_cache, "lookup", return_value={"answer": answer}):
            with mock.patch.object(bench.model_cache, "READ", False):
                with self.assertRaisesRegex(ValueError, "READ=True"):
                    client._post(b"fake")
                with bench.cache_reads():
                    self.assertIs(client._post(b"fake"), answer)
                self.assertFalse(bench.model_cache.READ)
            with self.assertRaises(bench.derive.Sam3Unavailable):
                client._send(b"fake", {})
            network.assert_not_called()
            store.assert_not_called()
        with mock.patch.object(Path, "exists", return_value=False):
            with self.assertRaisesRegex(bench.derive.Sam3Unavailable, "missing_cache"):
                client._post(b"fake")
        with mock.patch.object(Path, "exists", return_value=True), \
                mock.patch.object(bench.model_cache, "lookup", return_value=None):
            with self.assertRaisesRegex(bench.derive.Sam3Unavailable, "invalid_cache"):
                client._post(b"fake")

    def test_preparation_uses_faithful_label_box_and_preserves_package(self):
        instances = [{"label": "label", "box": [1, 2, 3, 4]}]
        client = types.SimpleNamespace(instances=mock.Mock(return_value=(instances, .5)),
                                       answer={"width": 333, "height": 250, "instances": instances},
                                       cache_identity={"key": "cached"})
        row = {"image_sha256": "abc", "path": "/fake.jpg", "package_box": [0, 0, 900, 950]}
        with mock.patch.object(bench, "digest_file", return_value="abc"), \
                mock.patch.object(bench.derive, "open_image", return_value=(FakeImage(), None)), \
                mock.patch.object(bench.alternatives, "label_cut_of", return_value=("crop", None, [10, 20, 500, 800])) as cut:
            result = bench.prepare_one(row, client)
        self.assertEqual(result["regions"]["label"]["boxes"], [[10, 20, 500, 800]])
        self.assertEqual(result["regions"]["label"]["method"], "crop")
        self.assertEqual(result["regions"]["package"]["boxes"], [[0, 0, 900, 950]])
        self.assertEqual(result["regions"]["barcode"]["status"], "missing_detection")
        self.assertIs(cut.call_args.args[1], instances)

    def test_missing_cache_is_explicit_and_does_not_remove_package(self):
        client = types.SimpleNamespace(instances=mock.Mock(side_effect=bench.derive.Sam3Unavailable("missing_cache")))
        row = {"image_sha256": "abc", "path": "/fake.jpg", "package_box": [0, 0, 900, 950]}
        with mock.patch.object(bench, "digest_file", return_value="abc"), \
                mock.patch.object(bench.derive, "open_image", return_value=(FakeImage(), None)):
            result = bench.prepare_one(row, client)
        self.assertEqual(result["regions"]["package"]["status"], "available")
        for name in ("bottle", "label", "barcode"):
            self.assertEqual(result["regions"][name]["status"], "missing_cache")

    def test_malformed_cached_instances_are_unavailable_without_stopping_preparation(self):
        client = types.SimpleNamespace(instances=mock.Mock(return_value=([None], .5)),
                                       answer={"width": 333, "height": 250, "instances": [None]},
                                       cache_identity={"key": "bad"})
        row = {"image_sha256": "abc", "path": "/fake.jpg", "package_box": [0, 0, 900, 950]}
        with mock.patch.object(bench, "digest_file", return_value="abc"), \
                mock.patch.object(bench.derive, "open_image", return_value=(FakeImage(), None)), \
                mock.patch.object(bench.alternatives, "label_cut_of") as label:
            result = bench.prepare_one(row, client)
        label.assert_not_called()
        self.assertEqual(result["regions"]["package"]["status"], "available")
        for name in ("bottle", "label", "barcode"):
            self.assertEqual(result["regions"][name]["status"], "invalid_cache")

    def test_scan_whole_first_order_early_exit_and_uncached_budget(self):
        FakeDecoder.answers = {"whole": [UNKNOWN], (10, 20, 30, 40): [CODE]}
        with mock.patch.object(bench.derive, "open_image", return_value=(FakeImage(), None)):
            result = bench.scan_prepared(prepared(), "whole-barcode", {}, LOOKUP, FakeDecoder)
        self.assertEqual(FakeDecoder.seen, ["whole", (10, 20, 30, 40)])
        self.assertEqual(result["codes"], [UNKNOWN, CODE])
        self.assertEqual(result["hit"]["slugs"], ["wine-a"])
        self.assertEqual((result["calls"], result["call_budget"]), (4, 6))
        FakeDecoder.answers, FakeDecoder.seen = {"whole": [CODE]}, []
        with mock.patch.object(bench.derive, "open_image", return_value=(FakeImage(), None)):
            result = bench.scan_prepared(prepared(), "whole-barcode", {}, LOOKUP, FakeDecoder)
        self.assertEqual(FakeDecoder.seen, ["whole"])
        self.assertEqual(result["calls"], 2)

    def test_unavailable_standalone_does_not_scan_whole_but_fallback_does(self):
        with mock.patch.object(bench.derive, "open_image", return_value=(FakeImage(), None)) as opening:
            result = bench.scan_prepared(prepared("missing_cache"), "label", {}, LOOKUP, FakeDecoder)
            opening.assert_not_called()
            self.assertEqual(result["calls"], 0)
            result = bench.scan_prepared(prepared("missing_cache"), "whole-label", {}, LOOKUP, FakeDecoder)
        self.assertEqual(result["calls"], 2)
        self.assertEqual(result["region_status"], "missing_cache")

    def test_negative_truth_and_row_unique_denominators(self):
        with mock.patch.object(bench.derive, "open_image", return_value=(FakeImage(), None)):
            FakeDecoder.answers = {"whole": [CODE]}
            result = bench.scan_prepared(prepared(), "whole-label", {}, LOOKUP, FakeDecoder)
        good = bench.compare(query(), result)
        wrong = bench.compare(query("negative", []), result)
        unknown = bench.compare(dict(query("negative", []), slug="wine-b"), result)
        self.assertTrue(good["truth_correct"])
        self.assertTrue(wrong["truth_wrong"])
        self.assertIsNone(unknown["truth_wrong"])
        summary = bench.summary([good, wrong, unknown], [result])
        self.assertEqual((summary["query_rows"], summary["unique_images"]), (3, 1))
        self.assertEqual(summary["native_calls"], 2)
        self.assertEqual(summary["truth_wrong_rows"], 1)

    def stage1(self):
        directory = self.root / "stage1"
        directory.mkdir()
        (directory / "manifest.json").write_text("{}")
        for variant in bench.base.VARIANTS:
            (directory / (variant + ".summary.json")).write_text(json.dumps({
                "photos": 1, "wall_segments": [{"complete": True}], "errors": 0}))
            (directory / (variant + ".jsonl")).write_text(json.dumps({"query_id": "q-1", "image_sha256": "abc"}) + "\n")
        return directory

    def test_stage1_gate_requires_all_nine_full_result_sets(self):
        directory = self.stage1()
        self.assertEqual(len(bench.require_stage1(directory, ["q-1"])["summaries"]), 9)
        (directory / "cache-warm-4.summary.json").unlink()
        with self.assertRaises(OSError):
            bench.require_stage1(directory, ["q-1"])
        (directory / "cache-warm-4.summary.json").write_text('{"photos": 1, "wall_segments": [{"complete": true}]}')
        (directory / "cache-warm-4.jsonl").write_text('{"query_id": "q-2", "image_sha256": "abc"}\n')
        with self.assertRaisesRegex(ValueError, "complete baseline"):
            bench.require_stage1(directory, ["q-1"])

    def test_stage1_live_pid_refuses_before_reading_summaries(self):
        directory = self.root / "stage1"
        (self.root / "stage1-process.json").write_text('{"pid": 78862}')
        with mock.patch.object(bench.os, "kill"), mock.patch.object(bench.subprocess, "run", return_value=types.SimpleNamespace(returncode=0, stdout="python benchmark_barcode_variants.py")):
            with self.assertRaisesRegex(ValueError, "still running"):
                bench.require_stage1(directory, ["q-1"])

    def test_stage1_unknown_pid_state_and_incomplete_timing_fail_closed(self):
        directory = self.stage1()
        (self.root / "stage1-process.json").write_text('{"pid": 78862}')
        with mock.patch.object(bench.os, "kill"), mock.patch.object(bench.subprocess, "run", return_value=types.SimpleNamespace(returncode=1, stdout="")):
            with self.assertRaisesRegex(ValueError, "cannot verify"):
                bench.require_stage1(directory, ["q-1"])
        (self.root / "stage1-process.json").unlink()
        (directory / "full.summary.json").write_text('{"photos": 1, "wall_segments": [{"complete": false}]}')
        with self.assertRaisesRegex(ValueError, "incomplete timing"):
            bench.require_stage1(directory, ["q-1"])

    def test_stage1_baseline_binding_and_resume_source_verification(self):
        directory = self.stage1()
        baseline = self.root / "baseline"
        baseline.mkdir()
        files = ("run.json", "queries.jsonl", "results.jsonl")
        for name in files:
            (baseline / name).write_text("fake")
        manifest = {"baseline": str(baseline.resolve()),
                    "files": {name: bench.digest_file(baseline / name) for name in files}}
        (directory / "manifest.json").write_text(json.dumps(manifest))
        bench.require_stage1(directory, ["q-1"], baseline_run=baseline)
        (baseline / "queries.jsonl").write_text("changed")
        with self.assertRaisesRegex(ValueError, "artifact hashes"):
            bench.require_stage1(directory, ["q-1"], baseline_run=baseline)
        with mock.patch.object(bench, "digest_file", return_value="changed"), \
                mock.patch.object(bench.derive, "open_image") as decode:
            with self.assertRaisesRegex(ValueError, "source digest changed"):
                bench.verify_source({"path": "/fake.jpg", "image_sha256": "original"})
            decode.assert_not_called()

    def test_shared_measurement_lock_and_resume_identity(self):
        directory = self.root / "stage1"
        with bench.measurement_lock(directory):
            with self.assertRaisesRegex(ValueError, "another crop or demo"):
                with bench.measurement_lock(directory):
                    self.fail("second holder entered")
        output = self.root / "output"
        bench.check_manifest(output, {"selection": ["q-1"]}, False)
        bench.check_manifest(output, {"selection": ["q-1"]}, True)
        with self.assertRaisesRegex(ValueError, "same selection"):
            bench.check_manifest(output, {"selection": ["q-2"]}, True)

    def test_lookup_must_match_stage1(self):
        expected = {"lookup": [["gtin", "04631168664979", ["wine-a"]]]}
        self.assertEqual(bench.require_lookup(LOOKUP, expected), expected["lookup"])
        changed = bench.base.barcode.CodeLookup({("gtin", "04631168664979"): ["wine-b"]})
        with self.assertRaisesRegex(ValueError, "lookup differs from stage 1"):
            bench.require_lookup(changed, expected)

    def test_frozen_preparation_rejects_edits_and_unindexed_interruption(self):
        directory = self.root / "prepared"
        directory.mkdir()
        index = bench.preparation_index(directory, ["abc", "def"])
        bench.freeze_preparation(directory, prepared(), index)
        restored = bench.preparation_index(directory, ["abc", "def"])
        self.assertFalse(restored["complete"])
        self.assertEqual(restored["records"], index["records"])
        (directory / "def.json").write_text('{"interrupted": true}')
        with self.assertRaisesRegex(ValueError, "unindexed or missing"):
            bench.preparation_index(directory, ["abc", "def"])
        (directory / "def.json").unlink()
        edited = prepared()
        edited["regions"]["label"]["boxes"] = [[1, 2, 3, 4]]
        (directory / "abc.json").write_text(json.dumps(edited))
        with self.assertRaisesRegex(ValueError, "frozen preparation file changed"):
            bench.preparation_index(directory, ["abc", "def"])

    def test_cli_prepare_then_resume_skips_saved_preparation_and_scans(self):
        stage1 = self.root / "stage1"
        stage1.mkdir()
        (stage1 / "manifest.json").write_text("{}")
        baseline = self.root / "baseline"
        output = self.root / "output"
        source = dict(query(), path="/fake/image.jpg")
        meta = {"answered": 1, "query_set": {"total": 1},
                "backend": {"barcode": {
                    "scanner": {"endpoint": "http://scanner.test", "engine": "auto"}}},
                "options": {"database": "fake"}}
        gate = {"manifest": {"baseline": str(baseline.resolve()), "files": {},
                             "lookup": [["gtin", "04631168664979", ["wine-a"]]]}}
        args = ["--baseline-run", str(baseline), "--baseline-log", str(self.root / "baseline.log"),
                "--stage1", str(stage1), "--output", str(output), "--variants", "label"]
        measured = {"image_sha256": "abc", "variant": "label", "region_status": "available",
                    "available": True, "regions_scanned": 1, "prep_ms": 17,
                    "hit": LOOKUP.find([CODE]), "codes": [CODE], "calls": 2,
                    "decode_errors": 0, "error": None, "scan_ms": 10, "wall_ms": 12, "load_ms": 2}
        with contextlib.ExitStack() as stack:
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(mock.patch.object(bench.base, "require_finished", return_value=meta))
            stack.enter_context(mock.patch.object(bench.base, "load_photos", return_value=[source]))
            stack.enter_context(mock.patch.object(bench, "require_stage1", return_value=gate))
            stack.enter_context(mock.patch.object(bench, "grouped_rows", return_value=[source]))
            stack.enter_context(mock.patch.object(bench, "verify_source"))
            stack.enter_context(mock.patch.object(bench.model_cache, "ROOT", str(self.root / "production-cache")))
            loading = stack.enter_context(mock.patch.object(bench.base.barcode.CodeLookup, "load", return_value=LOOKUP))
            prepare = stack.enter_context(mock.patch.object(bench, "prepare_one", return_value=prepared()))
            scan = stack.enter_context(mock.patch.object(bench, "scan_prepared", return_value=measured))
            self.assertEqual(bench.main(args + ["--prepare-only"]), 0)
            scan.assert_not_called()
            unrelated = self.root / "production-cache" / "sam3" / "other.json"
            unrelated.parent.mkdir(parents=True)
            unrelated.write_text('{"unrelated": true}')
            self.assertEqual(bench.main(args + ["--resume"]), 0)
            unrelated.write_text('{"unrelated": "changed"}')
            self.assertEqual(bench.main(args + ["--resume"]), 0)
            self.assertEqual(prepare.call_count, 1)
            self.assertEqual(scan.call_count, 1)
            self.assertEqual(loading.call_count, 6)  # start and completion of each invocation
            (output / "completion.json").unlink()
            changed = bench.base.barcode.CodeLookup({("gtin", "04631168664979"): ["wine-b"]})
            loading.side_effect = [LOOKUP, changed]
            with contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(bench.main(args + ["--resume"]), 2)
            self.assertIn("lookup differs from stage 1", error.getvalue())
            self.assertFalse((output / "completion.json").exists())
        rows = bench.base.read_jsonl(output / "label.jsonl")
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["truth_correct"])


if __name__ == "__main__":
    unittest.main()
