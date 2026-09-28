"""Check HTTP experiment boundaries with fakes. Bind no socket. Process no image."""
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import benchmark_recognition_http as bench  # noqa: E402


def raw_answer(cache, error=None):
    return {"candidates": [{"slug": "wine-a", "rank": 1, "score": 0.9}],
            "http_status": 200, "error": error, "trace": {"steps": [{"id": "barcode", "ms": 5}]},
            "latency_ms": 5, "ask_wall_ms": 6, "cache_read": False, "cache_root": cache,
            "decode_errors": 0, "sam3_failure_after": None}


def route_body(row, raw):
    return {"pipeline": "profile", "sha256": row["image_sha256"], "answer": raw["candidates"],
            "row": {"error": raw.get("error")}, "rounds": [], "notes": []}


class Temporary(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.data = b"fake image bytes; no decoder reads these bytes"
        self.photo = self.root / "source.jpg"
        self.photo.write_bytes(self.data)
        self.options = {"profile": "profile", "config": str(self.root / "config.yaml"),
                        "database": str(self.root / "lab.sqlite3"), "watchdog_s": 10}
        self.workers, self.calls = [], []

        outer = self

        class Worker:
            startup_ms = 100
            ready = {"build_ms": 60, "worker_import_ms": 40, "spec": {"id": "profile"},
                     "python": "/fake/worker-python",
                     "scanner": {"endpoint": "http://scanner.test", "engine": "auto"},
                     "pillow_version": "fake"}

            def __init__(self, options, log, timeout):
                self.options, self.closed = options, False
                outer.workers.append(self)

            def ask(self, row):
                outer.calls.append(dict(row))
                return raw_answer(row["cache_root"]), 10

            def close(self, force=False):
                self.closed = True

        self.Worker = Worker

    def row(self, number):
        return {"query_id": "q%d" % number, "image_sha256": hashlib.sha256(self.data).hexdigest(),
                "image_path": "test/photo.jpg", "path": str(self.photo), "truth": ["wine-a"],
                "label": "positive", "selection_reasons": ["baseline_barcode_hit" if number == 1
                                                               else "deterministic_spread"]}

    def adapter(self, mode="persistent"):
        return bench.RouteAdapter(mode, "full", self.options, self.root, factory=self.Worker)


class AdapterTest(Temporary):
    def test_fresh_crop_variants_preserve_worker_telemetry(self):
        crop = {"source": "fresh_sam3", "sam3_wall_ms": 2000, "status": "available"}
        self.Worker.ask = lambda self, row: (dict(raw_answer(row["cache_root"]), crop_scan=crop), 2010)
        for variant in bench.cli.CROP_VARIANTS:
            with self.subTest(variant=variant):
                adapter = bench.RouteAdapter("process", variant, self.options, self.root, factory=self.Worker)
                active = adapter.begin(self.row(1))
                result, _elapsed = adapter("/fake/python", self.options["config"], "profile",
                                           Path(active["upload_dir"]) / "uploaded.jpg")
                telemetry = adapter.finish()
                self.assertEqual(self.workers[-1].options["variant"], variant)
                self.assertEqual(result["crop_scan"], crop)
                self.assertEqual(telemetry["raw_answer"]["crop_scan"], crop)
                self.assertEqual(telemetry["worker_request_ms"], 2010)
                adapter.close()

    def test_modes_honor_route_interpreter_and_use_fresh_cache_and_upload_paths(self):
        for mode in bench.cli.MODES:
            with self.subTest(mode=mode):
                self.workers, self.calls = [], []
                adapter = self.adapter(mode)
                requests = []
                builds = []
                for n in (1, 2):
                    request = adapter.begin(self.row(n))
                    requests.append(request)
                    photo = Path(request["upload_dir"]) / "uploaded.jpg"
                    answer, process_ms = adapter("/fake/route-python", self.options["config"], "profile", photo)
                    builds.append(answer["build_ms"])
                    self.assertEqual(answer["spec"], {"id": "profile"})
                    self.assertGreaterEqual(process_ms, 0)
                    self.assertEqual(answer["cache_root"], request["cache_root"])
                    adapter.finish()
                adapter.close()
                self.assertNotEqual(requests[0]["upload_dir"], requests[1]["upload_dir"])
                self.assertNotEqual(requests[0]["cache_root"], requests[1]["cache_root"])
                self.assertEqual(len(self.workers), 2 if mode == "process" else 1)
                self.assertTrue(all(w.closed for w in self.workers))
                self.assertTrue(all(w.options["python"] == "/fake/route-python" for w in self.workers))
                self.assertEqual(builds, [60, 60] if mode == "process" else [60, 0])

    def test_an_active_request_prevents_a_second_request(self):
        adapter = self.adapter()
        adapter.begin(self.row(1))
        with self.assertRaisesRegex(RuntimeError, "active or failed"):
            adapter.begin(self.row(2))

    def test_bad_worker_cache_confirmation_closes_worker_and_blocks_next_request(self):
        import recognize_routes
        adapter = self.adapter()
        active = adapter.begin(self.row(1))
        self.Worker.ask = lambda self, row: (raw_answer("/wrong/cache"), 1)
        with self.assertRaises(recognize_routes.RecognizeError):
            adapter("/fake/python", self.options["config"], "profile", Path(active["upload_dir"]) / "x.jpg")
        self.assertTrue(adapter.blocked)
        self.assertTrue(self.workers[0].closed)
        self.assertIn("isolated cache", adapter.telemetry["adapter_error"])


class ServerScopeTest(Temporary):
    def test_production_route_runs_with_reconstruction_only_cache_reads_and_no_real_server(self):
        import lab_server
        import model_cache
        import recognize_routes
        original_cache = model_cache.ROOT, model_cache.READ
        adapter = self.adapter()
        server = types.SimpleNamespace(server_address=("127.0.0.1", 43210), serve_forever=mock.Mock(),
                                       shutdown=mock.Mock(), server_close=mock.Mock(),
                                       db_path=self.options["database"], config_path=self.options["config"])
        observed = []

        def store(data, directory):
            observed.append(("upload", model_cache.READ, model_cache.ROOT))
            return hashlib.sha256(data).hexdigest(), "jpg", str(Path(directory) / "uploaded.jpg")

        def steps(db_path, name, file_name, digest, extension, path, answer, card_images):
            observed.append(("steps", model_cache.READ, model_cache.ROOT))
            return route_body(adapter.active, answer)

        with mock.patch.object(recognize_routes, "store_upload", side_effect=store), \
                mock.patch.object(recognize_routes, "steps_answer", side_effect=steps), \
                mock.patch.object(recognize_routes, "find_pipeline",
                                  return_value=(types.SimpleNamespace(config_path=self.options["config"]), object())), \
                mock.patch.object(recognize_routes.run_jobs, "interpreter", return_value="/fake/route-python"), \
                mock.patch.object(lab_server, "start_watcher") as watcher, \
                mock.patch.object(bench.threading, "Thread") as thread:
            factory = mock.Mock(return_value=server)
            with bench.isolated_server(adapter, server_factory=factory) as (actual, setup_ms):
                self.assertIs(actual, server)
                self.assertGreaterEqual(setup_ms, 0)
                for n in (1, 2):
                    active = adapter.begin(self.row(n))
                    server.recognize_dir = active["upload_dir"]
                    code, body, ctype, cache = recognize_routes.respond(
                        server, "POST", "/api/recognize?pipeline=profile", lambda limit: self.data,
                        lab_server.card_images)
                    self.assertEqual(code, 200)
                    self.assertEqual(body["answer"][0]["slug"], "wine-a")
                    self.assertIn("process_ms", body)
                    self.assertIs(model_cache.READ, False)
                    metrics = adapter.finish()
                    self.assertIn("upload_ms", metrics)
                    self.assertIn("steps_answer_ms", metrics)
            factory.assert_called_once_with(self.options["database"], host="127.0.0.1", port=0,
                                            config_path=self.options["config"])
            watcher.assert_not_called()
            thread.return_value.start.assert_called_once()
            server.serve_forever.assert_not_called()  # The mocked thread binds no socket.
        self.assertEqual((model_cache.ROOT, model_cache.READ), original_cache)
        self.assertEqual([x[1] for x in observed], [False, True, False, True])
        self.assertNotEqual(observed[1][2], observed[3][2])
        self.assertTrue(all(w.closed for w in self.workers))

    def test_failed_server_start_restores_functions_and_cache(self):
        import recognize_routes
        import model_cache
        before = recognize_routes.run_script, model_cache.ROOT, model_cache.READ
        with self.assertRaisesRegex(OSError, "cannot bind"):
            with bench.isolated_server(self.adapter(), server_factory=mock.Mock(side_effect=OSError("cannot bind"))):
                pass
        self.assertEqual((recognize_routes.run_script, model_cache.ROOT, model_cache.READ), before)

    def test_client_failure_stops_accepting_then_aborts_and_joins_before_restoring_routes(self):
        import recognize_routes
        adapter, order = self.adapter(), []
        original = recognize_routes.run_script
        adapter.begin(self.row(1))
        fake_worker = mock.Mock()
        fake_worker.close.side_effect = lambda **kwargs: order.append(("close", kwargs["force"]))
        adapter.worker = fake_worker

        def join_handlers():
            self.assertIs(recognize_routes.run_script, adapter)
            self.assertIsNotNone(adapter.active)
            adapter.close()  # Simulate the handler's second cleanup after abort.
            order.append("join_handlers")

        server = types.SimpleNamespace(serve_forever=mock.Mock(),
                                       shutdown=lambda: order.append("shutdown"),
                                       server_close=join_handlers)
        with mock.patch.object(bench.threading, "Thread"), self.assertRaisesRegex(TimeoutError, "client"):
            with bench.isolated_server(adapter, server_factory=lambda *a, **k: server):
                raise TimeoutError("client failed")
        self.assertEqual(order, ["shutdown", ("close", True), "join_handlers"])
        self.assertIs(recognize_routes.run_script, original)
        fake_worker.close.assert_called_once_with(force=True)

    def test_worker_constructed_during_handler_join_is_closed_after_join(self):
        import recognize_routes
        adapter, order = self.adapter(), []
        original = recognize_routes.run_script
        adapter.begin(self.row(1))
        late_worker = mock.Mock()
        late_worker.close.side_effect = lambda **kwargs: order.append(("late_close", kwargs["force"]))

        def join_handlers():
            self.assertIs(recognize_routes.run_script, adapter)
            self.assertIsNone(adapter.worker)
            adapter.worker = late_worker  # Worker.__init__ finished in the active handler.
            order.append("handler_joined")

        server = types.SimpleNamespace(serve_forever=mock.Mock(),
                                       shutdown=lambda: order.append("shutdown"),
                                       server_close=join_handlers)
        with mock.patch.object(bench.threading, "Thread"), self.assertRaisesRegex(TimeoutError, "client"):
            with bench.isolated_server(adapter, server_factory=lambda *a, **k: server):
                raise TimeoutError("client failed during worker startup")
        self.assertEqual(order, ["shutdown", "handler_joined", ("late_close", True)])
        self.assertIsNone(adapter.worker)
        self.assertIs(recognize_routes.run_script, original)


class TimingTest(unittest.TestCase):
    def test_http_clock_includes_request_and_all_response_bytes_but_not_json_or_close(self):
        now = [0.0]
        sent = []

        class Response:
            status = 200

            def read(self):
                now[0] += 0.7
                return b'{"answer": []}'

        class Connection:
            def __init__(self, host, port, timeout):
                sent.append((host, port, timeout))

            def request(self, *args, **kwargs):
                now[0] += 0.2
                sent.append((args, kwargs))

            def getresponse(self):
                now[0] += 0.3
                return Response()

            def close(self):
                now[0] += 5  # Closing the client after its full response is outside the timer.

        out = bench.post_image(("127.0.0.1", 12345), {"pipeline": "p"}, b"not decoded", 50,
                               connection_factory=Connection, clock=lambda: now[0])
        self.assertAlmostEqual(out["client_wall_ms"], 1200)
        self.assertEqual(out["json_parse_ms"], 0)
        self.assertEqual(out["response_bytes"], len(b'{"answer": []}'))
        self.assertEqual(sent[0], ("127.0.0.1", 12345, 50))
        self.assertEqual(sent[1][0], ("POST", "/api/recognize?pipeline=p"))

    def test_route_shape_and_reconstruction_failures_stay_visible(self):
        row = {"image_sha256": "abc"}
        raw = raw_answer("cache")
        body = route_body(row, raw)
        response = {"http_status": 200, "body": body}
        self.assertEqual(bench.response_problems(response, raw, row), [])
        body["rounds"] = [{"steps": [{"artifacts": [{"check": "changed"}],
                                     "notes": ["The cut cannot be made again: missing cache."]}]}]
        self.assertEqual(len(bench.response_problems(response, raw, row)), 2)
        body["answer"] = []
        self.assertIn("HTTP candidates differ", " ".join(bench.response_problems(response, raw, row)))


class SessionTest(Temporary):
    def harness(self, fail=False):
        adapters, requests = [], []
        server = types.SimpleNamespace(server_address=("127.0.0.1", 12345))

        def factory(mode, variant, options, output):
            adapter = bench.RouteAdapter(mode, variant, options, output, factory=self.Worker)
            adapters.append(adapter)
            return adapter

        @contextlib.contextmanager
        def context(adapter):
            try:
                yield server, 123
            finally:
                adapter.close()

        def post(address, query, data, timeout):
            adapter = adapters[-1]
            requests.append(dict(adapter.active))
            raw, _ = adapter("/fake/python", self.options["config"], "profile",
                             Path(server.recognize_dir) / "uploaded.jpg")
            if fail:
                raw["decode_errors"] = 1
            return {"http_status": 200, "body": route_body(adapter.active, raw),
                    "client_wall_ms": 2900 if len(requests) == 1 else 3100,
                    "json_parse_ms": 2, "response_bytes": 1234}

        return factory, context, post, requests

    def test_sequential_http_checkpoints_use_http_wall_and_keep_duplicate_upload_cost(self):
        factory, context, post, requests = self.harness()
        with contextlib.redirect_stdout(io.StringIO()):
            out = bench.run_session("persistent", "full", [self.row(1), self.row(2)], self.options,
                                    self.root, False, factory, context, post)
        self.assertEqual(out["correct_within_3s"], 1)
        self.assertEqual(out["late_correct"], 1)
        self.assertEqual(out["scope"], bench.SCOPE)
        self.assertEqual(out["selection_strata"]["baseline_barcode_hit"]["rows"], 1)
        self.assertEqual(out["selection_strata"]["other_selected_rows"]["positive_labelled_rows"], 1)
        self.assertEqual(out["unique_images"], 1)
        self.assertNotEqual(requests[0]["upload_dir"], requests[1]["upload_dir"])
        self.assertNotEqual(requests[0]["cache_root"], requests[1]["cache_root"])
        saved = [json.loads(s) for s in (self.root / "persistent-full.jsonl").read_text().splitlines()]
        self.assertEqual([r["http_plus_json_ms"] for r in saved], [2902, 3102])
        self.assertTrue(all(Path(r["response_file"]).is_file() for r in saved))
        self.assertEqual(len(self.workers), 1)
        self.assertTrue(self.workers[0].closed)

    def test_degraded_answer_is_saved_then_prevents_the_next_http_request(self):
        factory, context, post, requests = self.harness(fail=True)
        with contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaisesRegex(RuntimeError, "failed or degraded"):
            bench.run_session("persistent", "full", [self.row(1), self.row(2)], self.options,
                              self.root, False, factory, context, post)
        self.assertEqual(len(requests), 1)
        record = json.loads((self.root / "persistent-full.jsonl").read_text())
        self.assertFalse(record["correct_within_3s"])
        self.assertTrue(record["degraded"])
        self.assertTrue((self.root / "persistent-full.failure.json").is_file())

    def test_transport_failure_is_censored_and_resume_keeps_it_without_retry(self):
        factory, context, good_post, requests = self.harness()
        attempts = []

        def failed_post(*args, **kwargs):
            attempts.append("q1")
            raise TimeoutError("client socket timed out")

        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, "failed or degraded"):
            bench.run_session("persistent", "full", [self.row(1), self.row(2)], self.options,
                              self.root, False, factory, context, failed_post)
        failed = json.loads((self.root / "persistent-full.jsonl").read_text())
        self.assertTrue(failed["latency_censored"])
        self.assertFalse(failed["response_complete"])
        self.assertFalse(failed["within_3s"])
        self.assertIsNone(failed["response_file"])
        self.assertGreaterEqual(failed["client_wall_ms"], 0)
        with contextlib.redirect_stdout(io.StringIO()):
            out = bench.run_session("persistent", "full", [self.row(1), self.row(2)], self.options,
                                    self.root, True, factory, context, good_post)
        self.assertEqual(attempts, ["q1"])
        self.assertEqual([r["query_id"] for r in requests], ["q2"])
        self.assertEqual((out["rows"], out["errors"], out["transport_failures"], out["censored_wall_rows"]),
                         (2, 1, 1, 1))


class GateTest(unittest.TestCase):
    def test_active_stage1_prevents_metadata_process_server_and_photo_preparation(self):
        import benchmark_barcode_crops as crops
        import benchmark_barcode_variants as scans
        with mock.patch.object(scans, "require_finished", return_value={}), \
                mock.patch.object(scans, "read_jsonl", return_value=[{"query_id": "q1"}]), \
                mock.patch.object(crops, "require_stage1", side_effect=ValueError("stage 1 active")), \
                mock.patch.object(scans, "load_photos") as photos, \
                mock.patch.object(bench, "worker_identity") as identity, \
                mock.patch.object(bench, "run_session") as run, \
                contextlib.redirect_stderr(io.StringIO()):
            code = bench.main(["--baseline-run", "/fake/run", "--baseline-log", "/fake/log",
                               "--stage1", "/fake/stage1", "--output", "/fake/http"])
        self.assertEqual(code, 2)
        photos.assert_not_called()
        identity.assert_not_called()
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
