"""Check the demo harness with fake backends and clients. Make no model requests."""
import contextlib
import io
import json
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import benchmark_recognition_latency as bench  # noqa: E402
import model_cache  # noqa: E402


def row(number, hit=False):
    return {"query_id": "q%d" % number, "image_sha256": "%064d" % number,
            "path": "/fake/%d.jpg" % number, "label": "positive", "truth": ["wine-a"],
            "baseline_latency_ms": 1000 + number, "selection_reasons": ["test"],
            "baseline_step": {"ms": number, "out": {"hit": {"slugs": ["wine-a"]}
                                                     if hit else None}}}


def answer(error=None, ms=50, slug="wine-a", stage_error=None):
    return {"event": "answer", "candidates": [{"slug": slug}], "http_status": 200,
            "error": error, "trace": {"steps": [{"id": "barcode", "ms": 20},
                                                  {"id": "embed", "ms": 30,
                                                   "error": stage_error}]},
            "ask_wall_ms": ms, "cache_read": False, "sam3_failure_after": None}


class SelectionTest(unittest.TestCase):
    def test_all_hits_are_mandatory_and_selection_is_reproducible(self):
        rows = [row(i, i < 3) for i in range(20)]
        results = {r["query_id"]: {"trace": {"steps": [
            {"id": "input", "out": {"width": 100 + n, "height": 300}},
            *([{"id": "cluster_rules"}] if n % 2 else [])]}}
                   for n, r in enumerate(rows)}
        sample = bench.select_sample(rows, results, 12)
        again = bench.select_sample(list(reversed(rows)), results, 12)
        self.assertEqual(sample, again)
        self.assertEqual(len(sample), 12)
        self.assertTrue({"q0", "q1", "q2"} <= {r["query_id"] for r in sample})
        self.assertEqual(len({r["query_id"] for r in sample}), 12)
        reasons = {reason for r in sample for reason in r["selection_reasons"]}
        self.assertTrue({"rerank", "large_image", "slow_barcode", "deterministic_spread"} <= reasons)
        with self.assertRaisesRegex(ValueError, "mandatory barcode hits"):
            bench.select_sample(rows, results, 2)
        with self.assertRaisesRegex(ValueError, "positive"):
            bench.select_sample(rows, results, 0)


class MetricTest(unittest.TestCase):
    def test_correct_late_and_failed_answers_have_separate_counts(self):
        expected = ((3000, answer(), True, False, False),
                    (3000.1, answer(), False, True, False),
                    (20, answer(error="down"), False, False, True),
                    (20, answer(stage_error="rerank failed"), False, False, True),
                    (20, answer(slug="wine-b"), False, False, False))
        for ms, response, ontime, late, failure in expected:
            with self.subTest(ms=ms, response=response):
                out = bench.classify(row(1), response, ms)
                self.assertEqual((out["correct_within_3s"], out["late_correct"], out["fast_error"]),
                                 (ontime, late, failure))

    def test_negative_and_unknown_truth_do_not_claim_correct_identification(self):
        for label in ("negative", "unlabelled", "no_match"):
            out = bench.classify(dict(row(1), label=label, truth=[]), answer(), 1)
            self.assertIsNone(out["truth_correct"])
            self.assertFalse(out["correct_within_3s"])
        self.assertEqual(bench.stage_costs({"steps": [{"id": "view", "ms": 2},
                                                     {"id": "view", "ms": 3}]}), {"view": 5})

    def test_latched_sam3_failure_is_degraded_even_if_outer_answer_is_success(self):
        out = bench.classify(row(1), dict(answer(), sam3_failure_after="down"), 1)
        self.assertTrue(out["degraded"])
        self.assertFalse(out["correct_within_3s"])

    def test_native_decoder_error_is_not_a_successful_deadline(self):
        out = bench.classify(row(1), dict(answer(), decode_errors=1), 1)
        self.assertTrue(out["degraded"])
        self.assertFalse(out["correct_within_3s"])

    def test_crop_summary_counts_fresh_calls_missing_regions_and_whole_hit_skips(self):
        records = []
        for number, status in enumerate(("skipped_unique_whole_hit", "missing_detection")):
            crop = {"status": status, "sam3_requests": number, "sam3_wall_ms": number * 2200,
                    "geometry_ms": number, "crop_decode_ms": 0}
            response = dict(answer(), crop_scan=crop)
            records.append(dict(row(number), answer=response, session_first=False,
                                client_wall_ms=2300, **bench.classify(row(number), response, 2300)))
        out = bench.summary(records)["fresh_crop"]
        self.assertEqual(out["rows"], 2)
        self.assertEqual(out["sam3_client_calls"], 1)
        self.assertEqual(out["whole_hit_skip_share"], 0.5)
        self.assertEqual(out["status_counts"], {"skipped_unique_whole_hit": 1, "missing_detection": 1})


class ExperimentTest(unittest.TestCase):
    def test_external_endpoint_guard_runs_before_backend_construction(self):
        import embedding_run
        import embeddings
        import benchmark_bulk_cache as bulk
        with mock.patch.object(embeddings, "load_settings", return_value=object()), \
                mock.patch.object(bulk, "internal_profile", side_effect=ValueError("external endpoint")), \
                mock.patch.object(embedding_run, "build_pipeline_backend") as build:
            with self.assertRaisesRegex(ValueError, "external endpoint"):
                with bench.build_experiment({"profile": "p", "config": "fake", "variant": "full"}):
                    pass
            build.assert_not_called()

    def test_parallel_decoder_pool_has_four_workers_and_shuts_down(self):
        import types
        import barcode
        import embedding_run
        import embeddings
        import benchmark_bulk_cache as bulk
        import benchmark_barcode_variants as scans

        class Decoder:
            def __init__(self, options):
                self.options, self.binarizers = options, (1, 2)

        profile = types.SimpleNamespace(barcode={"test": True})
        def build(*args):
            return types.SimpleNamespace(decoder=barcode.Decoder({}), spec={})

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fake.jpg"
            path.write_bytes(b"fake image")
            original = barcode.Decoder
            with mock.patch.object(embeddings, "load_settings", return_value=object()), \
                    mock.patch.object(bulk, "internal_profile", return_value=(profile, object())), \
                    mock.patch.object(scans, "MeasuredDecoder", Decoder), \
                    mock.patch.object(embedding_run, "build_pipeline_backend", side_effect=build), \
                    mock.patch.object(barcode.derive, "open_image", return_value=(mock.Mock(), None)), \
                    mock.patch.object(model_cache, "store"), \
                    mock.patch.object(scans, "scan_stages", return_value=([], None)) as scan:
                with bench.build_experiment({"profile": "p", "config": "fake", "variant": "photo4"}) as backend:
                    backend.decoder.scan_file(path, None)
                    pool = scan.call_args.args[-1]
                    self.assertEqual(pool._max_workers, 4)
                    self.assertEqual(scan.call_args.args[-2], 35)
                self.assertTrue(pool._shutdown)
                self.assertIs(barcode.Decoder, original)


class FreshCropTest(unittest.TestCase):
    """Use image and service doubles. Do not prepare or decode image bytes."""

    def setUp(self):
        self.image = mock.Mock(size=(4000, 3000))
        self.client = mock.Mock(refresh=True, endpoint="http://192.168.86.14:18081/upstream/sam3")
        self.client._sent_copy.return_value = (b"fake PNG", 0.333)
        self.client._post.return_value = {"width": 1333, "height": 1000, "instances": []}
        self.decoder = mock.Mock(crop_failure=None)
        self.decoder.scaled.side_effect = lambda image: image
        self.decoder.read.return_value = []
        self.lookup = mock.Mock()
        self.lookup.find.return_value = None
        patcher = mock.patch.object(model_cache, "READ", False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_fresh_bottle_maps_axes_separately_and_uses_largest_box(self):
        self.client._post.return_value["instances"] = [
            {"label": "bottle", "box": [0, 0, 100, 100]},
            {"label": "bottle", "box": [100, 100, 1233, 900]}]
        bench.scan_fresh_crops(self.decoder, self.image, self.lookup, "fresh-bottle", self.client)
        self.assertEqual(self.decoder.crop_scan["boxes"], [[300, 300, 3700, 2700]])
        self.image.crop.assert_called_once_with([300, 300, 3700, 2700])
        self.assertEqual(self.decoder.crop_scan["sam3_requests"], 1)
        self.assertEqual(self.decoder.crop_scan["regions_scanned"], 1)
        self.image.crop.return_value.close.assert_called_once()

    def test_barcode_grows_original_rectangle_and_scans_until_unique_hit(self):
        self.client._post.return_value.update(width=4000, height=3000, instances=[
            {"label": "barcode", "box": [100, 100, 200, 200]},
            {"label": "barcode", "box": [100, 100, 300, 300]}])
        self.lookup.find.return_value = {"slugs": ["wine-a"]}
        bench.scan_fresh_crops(self.decoder, self.image, self.lookup, "fresh-barcode", self.client)
        self.assertEqual(self.decoder.crop_scan["boxes"], [[80, 80, 320, 320], [90, 90, 210, 210]])
        self.image.crop.assert_called_once_with([80, 80, 320, 320])

    def test_label_uses_production_union_and_scans_unmasked_original_rectangle(self):
        import alternatives
        processed = mock.Mock()
        with mock.patch.object(alternatives, "label_cut_of",
                               return_value=("crop", processed, (21, 31, 500, 700))) as label:
            bench.scan_fresh_crops(self.decoder, self.image, self.lookup, "fresh-label", self.client)
        label.assert_called_once_with(self.image, [])
        self.image.crop.assert_called_once_with([21, 31, 500, 700])
        processed.close.assert_called_once()
        self.assertEqual(self.decoder.crop_scan["method"], "crop")

    def test_whole_unique_hit_skips_sam3_but_shared_hit_continues(self):
        self.lookup.find.return_value = {"slugs": ["wine-a"]}
        bench.scan_fresh_crops(self.decoder, self.image, self.lookup, "whole-fresh-barcode", self.client)
        self.client._post.assert_not_called()
        self.assertEqual(self.decoder.crop_scan["status"], "skipped_unique_whole_hit")
        self.lookup.find.return_value = {"slugs": ["wine-a", "wine-b"]}
        bench.scan_fresh_crops(self.decoder, self.image, self.lookup, "whole-fresh-barcode", self.client)
        self.client._post.assert_called_once()
        self.assertEqual(self.decoder.crop_scan["status"], "missing_detection")

    def test_duplicate_requests_send_fresh_geometry_and_charge_service_time(self):
        now = [0.0]
        def post(*args):
            now[0] += 2.0
            return {"width": 1333, "height": 1000, "instances": []}
        self.client._post.side_effect = post
        for _ in range(2):
            bench.scan_fresh_crops(self.decoder, self.image, self.lookup, "fresh-bottle",
                                   self.client, clock=lambda: now[0])
            self.assertEqual(self.decoder.crop_scan["sam3_wall_ms"], 2000)
            self.assertEqual(self.decoder.crop_scan["wall_ms"], 2000)
            self.assertEqual(self.decoder.crop_scan["sam3_requests"], 1)
        self.assertEqual(self.client._post.call_count, 2)
        self.client.refresh = False
        with self.assertRaisesRegex(RuntimeError, "refresh=True"):
            bench.scan_fresh_crops(self.decoder, self.image, self.lookup, "fresh-bottle", self.client)
        self.assertEqual(self.client._post.call_count, 2)

    def test_invalid_dimensions_are_an_error_instead_of_a_fast_missing_region(self):
        self.client._post.return_value["width"] = None
        with self.assertRaisesRegex(ValueError, "invalid fresh SAM3 geometry"):
            bench.scan_fresh_crops(self.decoder, self.image, self.lookup, "fresh-barcode", self.client)
        self.assertIn("invalid fresh SAM3 geometry", self.decoder.crop_failure)
        self.assertEqual(self.decoder.crop_scan["status"], "error")

    def test_outage_retains_barcode_trace_and_prevents_fallback_model_calls(self):
        import barcode
        import embedding_run
        import embeddings
        import benchmark_bulk_cache as bulk
        import benchmark_barcode_variants as scans

        class Decoder:
            def __init__(self, options):
                self.options, self.binarizers = options, (1, 2)
                self.calls = self.decode_errors = 0

        inner = types.SimpleNamespace(ask=mock.Mock(), id="p", top_k=5, catalogue=None, spec={})
        original_ask = inner.ask
        lookup = mock.Mock(values={"present": True}, counts={})
        lookup.hits.return_value = []
        def build(*args):
            return barcode.CodeFirst(inner, {}, "unused", lookup=lookup)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fake.jpg"
            path.write_bytes(b"not an image")
            with mock.patch.object(embeddings, "load_settings", return_value=object()), \
                    mock.patch.object(bulk, "internal_profile", return_value=(object(), object())), \
                    mock.patch.object(scans, "MeasuredDecoder", Decoder), \
                    mock.patch.object(embedding_run, "build_pipeline_backend", side_effect=build), \
                    mock.patch.object(barcode.derive, "Sam3Client", return_value=self.client) as client, \
                    mock.patch.object(barcode.derive, "open_image", return_value=(self.image, None)), \
                    mock.patch.object(model_cache, "store") as store:
                self.client._post.side_effect = barcode.derive.Sam3Unavailable("offline")
                with bench.build_experiment({"profile": "p", "config": "fake", "variant": "fresh-barcode"}) as backend:
                    result = backend.ask(path)
                    self.assertIn("offline", result[3])
                    self.assertIn("offline", result[4]["steps"][0]["error"])
                    self.assertEqual(backend.decoder.crop_scan["sam3_requests"], 1)
                    self.assertTrue(client.call_args.kwargs["refresh"])
                    original_ask.assert_not_called()
                    store.assert_not_called()
            self.assertIs(inner.ask, original_ask)
            self.client.session.close.assert_called_once()
            self.image.close.assert_called_once()


class WorkerTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_worker_disables_reads_inside_child_context_before_build_and_each_ask(self):
        previous = model_cache.ROOT, model_cache.READ
        observations = []

        class Backend:
            spec = {"test": True}
            decoder = types.SimpleNamespace(calls=0, decode_errors=0, crop_scan=None)

            def ask(self, path):
                observations.append((path, model_cache.READ, model_cache.ROOT))
                if path == "one":
                    self.decoder.crop_scan = {"source": "fresh_sam3", "sam3_wall_ms": 2000}
                return [{"slug": "wine-a", "items": ["large"]}], 1, 200, None, {"steps": []}

        @contextlib.contextmanager
        def build(options):
            observations.append(("build", model_cache.READ, model_cache.ROOT))
            yield Backend()

        options = {"cache_root": str(self.root / "cache")}
        source = io.StringIO("\n".join(json.dumps(v) for v in
                             (options, {"query_id": "a", "path": "one"},
                              {"query_id": "b", "path": "two"}, {"stop": True})) + "\n")
        sink = io.StringIO()
        bench.worker_loop(source, sink, build)
        out = [json.loads(s) for s in sink.getvalue().splitlines()]
        self.assertEqual([v["event"] for v in out], ["ready", "answer", "answer"])
        self.assertTrue(all(v[1:] == (False, str((self.root / "cache").resolve())) for v in observations))
        self.assertEqual((model_cache.ROOT, model_cache.READ), previous)
        self.assertNotIn("items", out[1]["candidates"][0])
        self.assertEqual(out[1]["crop_scan"]["sam3_wall_ms"], 2000)
        self.assertIsNone(out[2]["crop_scan"])

    def test_worker_stops_after_sam3_failure_instead_of_fast_failing_remaining_photos(self):
        called = []

        class Backend:
            spec = {}
            segmenter = type("Segmenter", (), {"failure": None})()

            def ask(self, path):
                called.append(path)
                self.segmenter.failure = "unavailable"
                return [], 2, None, "unavailable", {"steps": []}

        @contextlib.contextmanager
        def build(options):
            yield Backend()

        source = io.StringIO("\n".join(json.dumps(v) for v in
                            ({"cache_root": str(self.root / "cache")},
                             {"query_id": "a", "path": "one"},
                             {"query_id": "b", "path": "two"})) + "\n")
        sink = io.StringIO()
        bench.worker_loop(source, sink, build)
        self.assertEqual(called, ["one"])
        self.assertEqual(json.loads(sink.getvalue().splitlines()[-1])["sam3_failure_after"],
                         "unavailable")

    def test_worker_refuses_production_cache_before_build(self):
        builder = mock.Mock()
        with self.assertRaisesRegex(ValueError, "outside the production cache"):
            bench.worker_loop(io.StringIO(json.dumps({"cache_root": str(bench.ROOT / "data/cache")})
                                          + "\n"), io.StringIO(), builder)
        builder.assert_not_called()

    def test_persistent_requests_switch_cache_roots_inside_the_declared_boundary(self):
        observed = []

        class Backend:
            spec = {}

            def ask(self, path):
                observed.append((path, model_cache.ROOT, model_cache.READ))
                return [], 1, 200, None, {"steps": []}

        @contextlib.contextmanager
        def build(options):
            yield Backend()

        base = (self.root / "cache").resolve()
        source = io.StringIO("\n".join(json.dumps(v) for v in (
            {"cache_root": str(base / "first"), "cache_boundary": str(base)},
            {"query_id": "q1", "path": "one", "cache_root": str(base / "first")},
            {"query_id": "q2", "path": "two", "cache_root": str(base / "second")},
        )) + "\n")
        bench.worker_loop(source, io.StringIO(), build)
        self.assertEqual(observed, [("one", str(base / "first"), False),
                                    ("two", str(base / "second"), False)])
        bad = io.StringIO("\n".join(json.dumps(v) for v in (
            {"cache_root": str(base / "first"), "cache_boundary": str(base)},
            {"query_id": "q3", "path": "three", "cache_root": str(self.root / "outside")},
        )) + "\n")
        with self.assertRaisesRegex(ValueError, "experiment cache boundary"):
            bench.worker_loop(bad, io.StringIO(), build)
        self.assertEqual(len(observed), 2)

    def test_worker_uses_route_supplied_interpreter_without_starting_a_real_process(self):
        cache = str((self.root / "cache").resolve())
        process = mock.Mock()
        process.poll.return_value = 0
        with mock.patch.object(bench.subprocess, "Popen", return_value=process) as popen, \
                mock.patch.object(bench.Worker, "_receive", return_value={
                    "event": "ready", "cache_read": False, "cache_root": cache}):
            worker = bench.Worker({"cache_root": cache, "python": "/fake/configured-python"},
                                  self.root / "worker.log")
            worker.close()
        self.assertEqual(popen.call_args.args[0][0], "/fake/configured-python")

    def test_concurrent_cleanup_closes_a_mock_child_only_once(self):
        worker = object.__new__(bench.Worker)
        worker.timeout, worker._close_lock = 2, threading.RLock()
        worker.process, worker.log = mock.Mock(), mock.Mock()
        process, log = worker.process, worker.log
        process.poll.return_value = None
        entered, release = threading.Event(), threading.Event()

        def wait(*args, **kwargs):
            entered.set()
            self.assertTrue(release.wait(2))

        process.wait.side_effect = wait
        failures = []

        def close():
            try:
                worker.close(force=True)
            except BaseException as exc:
                failures.append(exc)

        first = threading.Thread(target=close)
        second = threading.Thread(target=close)
        first.start()
        self.assertTrue(entered.wait(2))
        second.start()
        release.set()
        first.join(2)
        second.join(2)
        self.assertFalse(first.is_alive() or second.is_alive())
        self.assertEqual(failures, [])
        process.kill.assert_called_once()
        process.stdin.close.assert_called_once()
        process.stdout.close.assert_called_once()
        log.close.assert_called_once()
        self.assertIsNone(worker.process)


class SessionTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def factory(self):
        events = []
        active = 0
        peak = 0

        class Client:
            startup_ms = 100
            ready = {"build_ms": 60, "worker_import_ms": 40, "spec": {}}

            def __init__(self, options, log, timeout):
                nonlocal active, peak
                active += 1
                peak = max(peak, active)
                self.closed = False
                events.append("start")

            def ask(self, query):
                events.append(query["query_id"])
                return answer(), 50

            def close(self, force=False):
                nonlocal active
                if not self.closed:
                    self.closed = True
                    active -= 1
                    events.append("close")

        return Client, events, lambda: (active, peak)

    def test_modes_are_sequential_and_startup_is_charged_to_correct_requests(self):
        for mode in bench.MODES:
            with self.subTest(mode=mode), contextlib.redirect_stdout(io.StringIO()):
                output = self.root / mode
                output.mkdir()
                factory, events, state = self.factory()
                out = bench.run_session(mode, "whole", [row(1), row(2)], {"watchdog_s": 10},
                                        output, False, factory)
                records = [json.loads(s) for s in (output / (mode + "-whole.jsonl"))
                           .read_text().splitlines()]
                self.assertEqual(state(), (0, 1))
                self.assertEqual(out["rows"], 2)
                self.assertEqual(len(out["first_requests"]), 1)
                self.assertFalse(out["hard_timeout_implemented"])
                if mode == "process":
                    self.assertEqual(events, ["start", "q1", "close", "start", "q2", "close"])
                    self.assertTrue(all(r["client_wall_ms"] >= 150 for r in records))
                else:
                    self.assertEqual(events, ["start", "q1", "q2", "close"])
                    self.assertEqual([r["client_wall_ms"] for r in records], [150, 50])
                    self.assertEqual(out["steady_client_wall_ms"]["median"], 50)
                    self.assertEqual([r["build_ms"] for r in records], [60, 0])
                    self.assertEqual([r["backend_initial_build_ms"] for r in records], [60, 60])

    def test_resume_skips_checkpoints_and_marks_new_worker_first_request(self):
        factory, events, state = self.factory()
        with contextlib.redirect_stdout(io.StringIO()):
            bench.run_session("persistent", "full", [row(1)], {"watchdog_s": 10},
                              self.root, False, factory)
            out = bench.run_session("persistent", "full", [row(1), row(2)], {"watchdog_s": 10},
                                    self.root, True, factory)
        self.assertEqual(events.count("q1"), 1)
        self.assertEqual(events.count("q2"), 1)
        self.assertEqual(len(out["first_requests"]), 2)
        self.assertEqual(state(), (0, 1))

    def test_error_is_checkpointed_before_experiment_stops(self):
        factory, events, state = self.factory()
        factory.ask = lambda self, row: (answer(error="service failed"), 10)
        with contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaisesRegex(RuntimeError, "stop before another image"):
            bench.run_session("persistent", "full", [row(1), row(2)], {"watchdog_s": 10},
                              self.root, False, factory)
        saved = (self.root / "persistent-full.jsonl").read_text().splitlines()
        self.assertEqual(len(saved), 1)
        self.assertEqual(json.loads(saved[0])["error"], "service failed")
        self.assertEqual(state(), (0, 1))

    def test_watchdog_closes_worker_and_records_failure_without_a_next_image(self):
        factory, events, state = self.factory()
        def timeout(self, query):
            events.append(query["query_id"])
            raise TimeoutError("watchdog")
        factory.ask = timeout
        with self.assertRaisesRegex(TimeoutError, "watchdog"):
            bench.run_session("persistent", "full", [row(1), row(2)], {"watchdog_s": 10},
                              self.root, False, factory)
        failure = json.loads((self.root / "persistent-full.failure.json").read_text())
        self.assertEqual(failure["query_id"], "q1")
        self.assertTrue(failure["outstanding_remote_work_possible"])
        self.assertNotIn("q2", events)
        self.assertEqual(state(), (0, 1))


class GateTest(unittest.TestCase):
    def test_stage1_from_another_baseline_stops_before_model_or_photo_preparation(self):
        import benchmark_barcode_crops as crops
        import benchmark_barcode_variants as scans
        with mock.patch.object(scans, "require_finished", return_value={"answered": 1}), \
                mock.patch.object(scans, "read_jsonl", return_value=[row(1)]), \
                mock.patch.object(scans, "load_photos") as photos, \
                mock.patch.object(crops, "require_stage1", return_value={"manifest": {"baseline": "other"}}), \
                mock.patch.object(crops, "measurement_lock", side_effect=lambda *a: contextlib.nullcontext()), \
                mock.patch.object(bench, "file_hash", return_value="hash"), \
                mock.patch.object(bench, "input_identity") as identity, \
                mock.patch.object(bench, "Worker") as worker, \
                contextlib.redirect_stderr(io.StringIO()):
            code = bench.main(["--baseline-run", "/fake/run", "--baseline-log", "/fake/log",
                               "--stage1", "/fake/stage1", "--output", "/fake/output"])
        self.assertEqual(code, 2)
        photos.assert_not_called()
        identity.assert_not_called()
        worker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
