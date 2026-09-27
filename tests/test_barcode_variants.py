"""Check benchmark gates and variants with fake decoders. Never scan a real image."""
import concurrent.futures
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import benchmark_barcode_variants as bench  # noqa: E402

CODE = {"kind": "barcode", "format": "EAN13", "text": "4631168664979"}
OTHER = {"kind": "barcode", "format": "EAN13", "text": "4600682000181"}
LOOKUP = bench.barcode.CodeLookup({("gtin", "04631168664979"): ["wine-a"],
                                   ("gtin", "04600682000181"): ["wine-b"]})


class FakeDecoder:
    def __init__(self, options):
        self.options = options
        self.binarizers = (1, 2)
        self.calls = self.decode_errors = 0
        self.lock = threading.Lock()

    def scaled(self, image):
        return image

    def read(self, image):
        with self.lock:
            self.calls += len(self.binarizers)
        return []

    def scan_file(self, path, lookup):
        cache = Path(bench.model_cache.ROOT) / (Path(path).name + ".json")
        if bench.model_cache.READ and cache.exists():
            return [], None, True
        self.calls += 70
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text("{}")
        return [], None, False


def row(number=1):
    return {"query_id": "q-%d" % number, "image_sha256": str(number),
            "image_path": "wine-a/%d.jpg" % number, "path": "/fake/%d.jpg" % number,
            "label": "positive", "slug": "wine-a", "truth": ["wine-a"], "baseline_latency_ms": 1500,
            "baseline_step": {"id": "barcode", "ms": 500, "out": {"codes": [], "hit": None}}}


class VariantTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.options = bench.barcode.check_options({})
        patcher = mock.patch.object(bench.barcode, "tiles", side_effect=lambda image: iter(range(34)))
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(bench.barcode.derive, "open_image", return_value=("whole", None))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_pass_caps_and_single_binarizer(self):
        for variant, count in (("whole1", 1), ("whole", 2), ("tiles3", 20), ("full", 70)):
            with self.subTest(variant=variant):
                answer = bench.measure_one(row(), variant, self.options, LOOKUP, factory=FakeDecoder)
                self.assertIsNone(answer["error"])
                self.assertEqual(answer["calls"], count)

    def test_parallel_scan_preserves_order_and_bounds_active_decodes(self):
        decoder = FakeDecoder(self.options)
        active = peak = 0
        lock = threading.Lock()
        later_done = threading.Event()

        def read(image):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            try:
                if image == "whole":
                    return []
                if image == 0:
                    self.assertTrue(later_done.wait(2))
                    return [CODE]
                if image == 1:
                    later_done.set()
                    return [OTHER]
                return []
            finally:
                with lock:
                    active -= 1

        decoder.read = read
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            codes, hit = bench.scan_stages(decoder, "whole", LOOKUP, 35, pool)
        self.assertEqual(codes, [CODE])
        self.assertEqual(hit["slugs"], ["wine-a"])
        self.assertLessEqual(peak, 4)
        self.assertGreaterEqual(peak, 2)

    def test_four_image_workers_are_bounded_and_warm_cache_does_not_decode(self):
        active = peak = 0
        lock, barrier = threading.Lock(), threading.Barrier(4)

        class ConcurrentDecoder(FakeDecoder):
            def scan_file(self, path, lookup):
                nonlocal active, peak
                if not bench.model_cache.READ:
                    with lock:
                        active += 1
                        peak = max(peak, active)
                    barrier.wait(2)
                    try:
                        return super().scan_file(path, lookup)
                    finally:
                        with lock:
                            active -= 1
                return super().scan_file(path, lookup)

        rows = [row(i) for i in range(4)]
        old = bench.model_cache.ROOT, bench.model_cache.READ
        cold = bench.run_variant("cache-cold-4", rows, self.options, LOOKUP, self.root,
                                 False, ConcurrentDecoder)
        warm = bench.run_variant("cache-warm-4", rows, self.options, LOOKUP, self.root,
                                 False, ConcurrentDecoder)
        self.assertEqual(peak, 4)
        self.assertEqual(cold["native_calls"], 280)
        self.assertEqual((warm["native_calls"], warm["cache_hits"]), (0, 4))
        self.assertEqual((bench.model_cache.ROOT, bench.model_cache.READ), old)

    def test_resume_skips_saved_photos_and_rejects_unprimed_warm_variant(self):
        rows = [row(1), row(2)]
        bench.run_variant("whole", rows[:1], self.options, LOOKUP, self.root, False, FakeDecoder)
        factory = mock.Mock(side_effect=FakeDecoder)
        summary = bench.run_variant("whole", rows, self.options, LOOKUP, self.root, True, factory)
        self.assertEqual((summary["photos"], summary["native_calls"]), (2, 4))
        factory.assert_called_once()
        with self.assertRaisesRegex(ValueError, "needs its cold variant"):
            bench.run_variant("cache-warm-1", rows, self.options, LOOKUP, self.root, False, factory)

    def test_truth_and_baseline_conflict_are_separate(self):
        query = row()
        query["baseline_step"]["out"]["hit"] = LOOKUP.find([CODE])

        class WrongDecoder(FakeDecoder):
            def read(self, image):
                self.calls += 2
                return [OTHER]

        answer = bench.measure_one(query, "whole", self.options, LOOKUP, factory=WrongDecoder)
        self.assertTrue(answer["conflict"])
        self.assertTrue(answer["truth_wrong"])
        summary = bench.summarize([answer])
        self.assertEqual(summary["paired_correct_delta"], -1)
        self.assertEqual(summary["paired_lost"], 1)
        self.assertEqual(summary["conflicts"], 1)

    def test_negative_labels_only_prove_the_rejected_wine_is_wrong(self):
        class HitDecoder(FakeDecoder):
            def read(self, image):
                self.calls += 2
                return [CODE]

        for label, rejected, expected in (("negative", "wine-a", True),
                                           ("negative", "wine-b", None),
                                           ("no_match", "wine-b", True),
                                           ("unlabelled", "wine-a", None)):
            with self.subTest(label=label, rejected=rejected):
                query = dict(row(), label=label, slug=rejected, truth=[])
                answer = bench.measure_one(query, "whole", self.options, LOOKUP, factory=HitDecoder)
                self.assertIs(answer["truth_wrong"], expected)

    def test_resumed_interrupted_timing_never_claims_a_complete_wall_total(self):
        bench.run_variant("whole", [row()], self.options, LOOKUP, self.root, False, FakeDecoder)
        timing = self.root / "whole.timing.json"
        segments = json.loads(timing.read_text())
        segments[0]["complete"] = False
        timing.write_text(json.dumps(segments))
        result = bench.run_variant("whole", [row(), row(2)], self.options, LOOKUP,
                                   self.root, True, FakeDecoder)
        self.assertTrue(result["elapsed_incomplete"])
        self.assertIsNone(result["wall_total_s"])
        self.assertIsNone(result["photos_per_second"])
        self.assertIn("p99", result["barcode_ms"])
        self.assertEqual(result["barcode_within_3s_share"], 1.0)


class GateTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run = self.root / "baseline"
        self.run.mkdir()
        self.log = self.root / "job.log"
        self.log.write_text(json.dumps({"event": "progress", "done": 1}))

    def test_missing_metadata_and_nonfinal_or_wrong_run_log_refuse_scans(self):
        with self.assertRaisesRegex(ValueError, "run.json is absent"):
            bench.require_finished(self.run, self.log)
        (self.run / "run.json").write_text(json.dumps({"run_id": "baseline", "finished": "now"}))
        for event in ({"event": "progress"}, {"event": "stopped", "run_id": "baseline"},
                      {"event": "done", "run_id": "other"}):
            self.log.write_text(json.dumps(event))
            with self.assertRaisesRegex(ValueError, "does not end with done"):
                bench.require_finished(self.run, self.log)
        self.log.write_text(json.dumps({"event": "done", "run_id": "baseline"}))
        self.assertEqual(bench.require_finished(self.run, self.log)["run_id"], "baseline")

    def test_cli_gate_runs_before_loading_photos_or_decoder(self):
        with mock.patch.object(bench, "load_photos") as photos, \
                mock.patch.object(bench, "run_variant") as measure, \
                contextlib.redirect_stderr(io.StringIO()):
            code = bench.main(["--baseline-run", str(self.run), "--baseline-log", str(self.log),
                               "--output", str(self.root / "output")])
        self.assertEqual(code, 2)
        photos.assert_not_called()
        measure.assert_not_called()

    def test_digest_mapping_ignores_original_photo_name(self):
        images = self.root / "images" / "testset"
        images.mkdir(parents=True)
        query = row()
        query["image_sha256"] = hashlib.sha256(b"photo").hexdigest()
        photo = images / (query["image_sha256"] + ".jpg")
        photo.write_bytes(b"photo")
        (self.run / "queries.jsonl").write_text(json.dumps(query) + "\n")
        result = dict(query, latency_ms=1500, trace={"steps": [query["baseline_step"]]})
        (self.run / "results.jsonl").write_text(json.dumps(result) + "\n")
        loaded = bench.load_photos(self.run, images.parent)
        self.assertEqual(loaded[0]["path"], str(photo))

    def test_interrupted_final_record_is_removed_on_resume(self):
        path = self.root / "full.jsonl"
        path.write_text('{"query_id":"q-1"}\n{"query_id":')
        self.assertEqual(bench.records_for_resume(path), [{"query_id": "q-1"}])
        self.assertEqual(bench.read_jsonl(path), [{"query_id": "q-1"}])


if __name__ == "__main__":
    unittest.main()
