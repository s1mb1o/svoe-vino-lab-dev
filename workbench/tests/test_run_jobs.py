"""Tests of the run jobs of the Testset page (plan 32): `pipeline/run_jobs.py` (the job
state, the start, the stop, the routes) and `pipeline/run_job.py` (the runner). The jobs
run the pipelines of the key `pipeline` alone (plan 34)."""
import contextlib
import http.server
import io
import json
import os
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX  # noqa: E402
import embedding_run  # noqa: E402
import import_testset as IT  # noqa: E402
import model_cache  # noqa: E402
import pipelines  # noqa: E402
import run_job  # noqa: E402
import run_jobs  # noqa: E402

REMOTE = "vino-svoe-search-by-photo"
PHOTOS = {"wine-a/%02d.jpg" % i: b"a%d" % i for i in range(1, 7)}
PHOTOS["wine-b/01.jpg"] = b"b1"
LABELS = {"wine-a": {"%02d.jpg" % i: {"label": "positive"} for i in range(1, 7)},
          "wine-b": {"01.jpg": {"label": "positive"}}}
STEPS = {"full": {"steps": [{"step": "segment", "target": "package"}]}}


class Matcher(http.server.BaseHTTPRequestHandler):
    """A matcher that answers a bare ranked list, after `delay` seconds."""

    delay = 0.0

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        time.sleep(Matcher.delay)
        body = json.dumps([{"slug": "wine-a"}, {"slug": "wine-b"}]).encode()
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class Lab(unittest.TestCase):
    """A database with the set `my`, a matcher, and a config.yaml with one embedding and
    three pipelines. The embedding `gw` has no index."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(self.root)
        IT.import_testset(self.db, "my", FX.write_set(self.root, PHOTOS, LABELS),
                          lambda m: None, self.schema)
        Matcher.delay = 0.0
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Matcher)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        url = "http://127.0.0.1:%d/v1/wines/search-by-photo" % self.server.server_port
        self.config = self.root / "config.yaml"
        self.config.write_text(json.dumps({
            "rootdir": str(self.root), "database_file": self.db, "embeddings": [
                {"name": "gw", "backend": "openai", "base_url": "http://x/v1",
                 "model": "m", "views": STEPS}], "pipeline": [
                {"name": REMOTE, "backend": "svoe-vino-ru", "url": url, "top_k": 2,
                 "workers": 2, "query": {"limit": 10}},
                {"name": "broken", "backend": "nothing"},
                {"name": "emb", "backend": "embedding", "embedding": "gw"}]}),
            encoding="utf-8")
        self.jobs = str(self.root / "jobs")
        self.runs = str(self.root / "runs")
        run_jobs._PROCESSES.clear()

    def tearDown(self):
        for process in list(run_jobs._PROCESSES.values()):
            if process.poll() is None:
                process.kill()
                process.wait()
        run_jobs._PROCESSES.clear()
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def settings(self):
        return pipelines.load(str(self.config))

    def run_main(self, name, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = run_job.main(["--config", str(self.config), "--name", name, "--set", "my",
                                 "--jobs-dir", self.jobs, "--runs-dir", self.runs, *extra])
        return code, [json.loads(line) for line in out.getvalue().splitlines()]


class JobStateTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.dir = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def write(self, *events):
        (self.dir / run_jobs.LOG).write_text(
            "".join(json.dumps(e) + "\n" for e in events) + "not an event\n", encoding="utf-8")

    def test_no_log_is_no_job(self):
        self.assertIsNone(run_jobs.job_state(str(self.dir))["state"])

    def test_a_final_event_gives_the_state_the_counts_and_the_run(self):
        self.write({"event": "start", "pid": 1, "set": "my", "todo": 5, "t": 10},
                   {"event": "run_dir", "run_id": "r1", "t": 11},
                   {"event": "progress", "done": 5, "todo": 5, "errors": 1, "t": 12},
                   {"event": "done", "run_id": "r1", "message": "ok", "t": 13})
        job = run_jobs.job_state(str(self.dir))
        self.assertEqual((job["state"], job["set"], job["done"], job["todo"], job["errors"]),
                         ("done", "my", 5, 5, 1))
        self.assertEqual((job["run_id"], job["started_t"], job["ended_t"]), ("r1", 10, 13))

    def test_a_runner_that_ended_with_no_final_event_failed(self):
        self.write({"event": "start", "pid": 999999999, "set": "my", "todo": 5, "t": 10},
                   {"event": "progress", "done": 2, "todo": 5, "errors": 0, "t": 11})
        job = run_jobs.job_state(str(self.dir))
        self.assertEqual(job["state"], "failed")
        self.assertIn("no final event", job["message"])

    def test_a_failure_before_the_start_event_is_failed(self):
        self.write({"event": "failed", "message": "--limit MUST be 1 or more", "t": 3})
        job = run_jobs.job_state(str(self.dir))
        self.assertEqual((job["state"], job["message"]), ("failed", "--limit MUST be 1 or more"))

    def test_a_lock_of_a_dead_process_is_not_a_running_job(self):
        (self.dir / run_jobs.LOCK).write_text(json.dumps({"pid": 999999999}), encoding="utf-8")
        self.write({"event": "start", "pid": 999999999, "set": "my", "todo": 5, "t": 10})
        self.assertEqual(run_jobs.job_state(str(self.dir))["state"], "failed")
        self.assertFalse(run_jobs.runner_alive(os.getpid()))  # this process is no runner


class ConfigurationsTest(Lab):
    def test_every_pipeline_is_listed_and_the_valid_ones_are_enabled(self):
        view = run_jobs.configurations_view(self.settings(), self.jobs, "my")
        self.assertEqual(view["queries"], 7)
        rows = {c["name"]: c for c in view["configurations"]}
        # The embedding `gw` is not a pipeline, so the dialog does not list it.
        self.assertEqual(list(rows), [REMOTE, "broken", "emb"])
        self.assertFalse(rows["broken"]["runnable"])
        self.assertEqual((rows["emb"]["runnable"], rows["emb"]["reason"], rows["emb"]["workers"]),
                         (False, embedding_run.NO_INDEX, 1))
        self.assertTrue(rows["broken"]["reason"].startswith("configuration error"))
        self.assertEqual((rows[REMOTE]["runnable"], rows[REMOTE]["workers"]), (True, 2))
        self.assertFalse(rows[REMOTE]["device_ip"])
        self.assertIsNone(rows[REMOTE]["job"]["state"])

    def test_a_device_pipeline_requires_an_ip_and_puts_it_into_the_command(self):
        config = json.loads(self.config.read_text(encoding="utf-8"))
        config["pipeline"].append({
            "name": "android-device-match-k20", "backend": "svoe-vino-ru",
            "url": "http://{device_ip}:18088/v1/match", "device_ip": True,
            "response": "candidates", "query": {"k": 20}, "top_k": 20,
            "timeout_s": 120, "workers": 1})
        self.config.write_text(json.dumps(config), encoding="utf-8")
        settings = self.settings()
        rows = {row["name"]: row for row in
                run_jobs.configurations_view(settings, self.jobs, "my")["configurations"]}
        self.assertTrue(rows["android-device-match-k20"]["device_ip"])
        for body, text in (({"configuration": "android-device-match-k20", "set": "my"},
                            "device_ip is required"),
                           ({"configuration": "android-device-match-k20", "set": "my",
                             "device_ip": "pixel.local"}, "IPv4"),
                           ({"configuration": REMOTE, "set": "my",
                             "device_ip": "192.168.86.42"}, "not valid")):
            with self.subTest(body=body):
                code, answer = run_jobs.start(settings, self.jobs, body, self.runs)
                self.assertEqual(code, 400)
                self.assertIn(text, answer["error"])
        with mock.patch.object(run_jobs.subprocess, "Popen") as popen:
            popen.return_value.pid = 4321
            popen.return_value.poll.return_value = 0
            code, answer = run_jobs.start(
                settings, self.jobs,
                {"configuration": "android-device-match-k20", "set": "my",
                 "device_ip": "192.168.86.42"}, self.runs)
        self.assertEqual(code, 202, answer)
        command = popen.call_args[0][0]
        self.assertEqual(command[command.index("--device-ip") + 1], "192.168.86.42")
        self.assertEqual(answer["device_ip"], "192.168.86.42")

    def test_the_new_run_dialog_has_the_device_ip_parameter(self):
        page = (Path(run_jobs.__file__).parent / "pages" / "testset.html").read_text("utf-8")
        self.assertIn('id="run-device-ip"', page)
        self.assertIn("body.device_ip = address", page)

    def test_an_unknown_set_is_an_error(self):
        with self.assertRaises(run_jobs.benchmark.BenchmarkError):
            run_jobs.configurations_view(self.settings(), self.jobs, "nope")

    def test_an_embedding_pipeline_runs_with_embedding_python(self):
        settings = self.settings()
        self.assertEqual(run_jobs.interpreter(settings, settings.find(REMOTE)), sys.executable)
        config = json.loads(self.config.read_text(encoding="utf-8"))
        for python, code in ((str(self.root / "no-python"), 400), (sys.executable, None)):
            with self.subTest(python=python):
                self.config.write_text(json.dumps(dict(config, embedding_python=python)),
                                       encoding="utf-8")
                settings = self.settings()
                if code is None:
                    self.assertEqual(run_jobs.interpreter(settings, settings.find("emb")),
                                     sys.executable)
                    continue
                with mock.patch.object(embedding_run, "index_ready", return_value=True):
                    got, answer = run_jobs.start(settings, self.jobs,
                                                 {"configuration": "emb", "set": "my"}, self.runs)
                self.assertEqual(got, code)
                self.assertIn("is not a file", answer["error"])
        self.assertEqual(run_jobs._PROCESSES, {})

    def test_a_start_checks_the_body_before_it_starts_a_process(self):
        wrong = [
            ({"set": "my"}, 400, "MUST name"),
            ({"configuration": REMOTE, "set": "my", "limit": 0}, 400, "limit MUST"),
            ({"configuration": REMOTE, "set": "my", "workers": 99}, 400, "workers MUST"),
            ({"configuration": REMOTE, "set": "my", "workers": True}, 400, "workers MUST"),
            ({"configuration": REMOTE, "set": "my", "use_cache": "no"}, 400, "use_cache MUST"),
            ({"configuration": "other", "set": "my"}, 404, "no pipeline other"),
            ({"configuration": "gw", "set": "my"}, 404, "no pipeline gw"),
            ({"configuration": "broken", "set": "my"}, 400, "pipeline broken"),
            ({"configuration": "emb", "set": "my"}, 400, embedding_run.NO_INDEX),
            ({"configuration": REMOTE, "set": "nope"}, 404, "no test set"),
        ]
        for body, code, text in wrong:
            with self.subTest(body=body):
                got, answer = run_jobs.start(self.settings(), self.jobs, body, self.runs)
                self.assertEqual(got, code)
                self.assertIn(text, answer["error"])
        self.assertEqual(run_jobs._PROCESSES, {})


class RunnerTest(Lab):
    def test_a_remote_run_writes_its_events_and_the_run_files(self):
        code, events = self.run_main(REMOTE, "--limit", "3")
        self.assertEqual(code, 0)
        kinds = [e["event"] for e in events]
        self.assertEqual(kinds[0], "start")
        self.assertEqual(kinds[-1], "done")
        self.assertIn("run_dir", kinds)
        start, done = events[0], events[-1]
        self.assertEqual((start["set"], start["todo"], start["workers"], start["limit"]),
                         ("my", 3, 2, 3))
        progress = [e for e in events if e["event"] == "progress"]
        self.assertEqual([e["done"] for e in progress], [1, 2, 3])
        self.assertEqual(done["answered"], 3)
        meta = json.loads((Path(self.runs) / done["run_id"] / "run.json").read_text("utf-8"))
        self.assertEqual((meta["configuration"], meta["answered"]), (REMOTE, 3))
        self.assertFalse((Path(self.jobs) / REMOTE / run_jobs.LOCK).exists())

    def test_an_embedding_entry_is_not_a_pipeline(self):
        code, events = self.run_main("gw")
        self.assertEqual(code, 1)
        self.assertEqual(events[-1]["event"], "failed")
        self.assertIn("config.yaml has no pipeline gw", events[-1]["message"])
        self.assertFalse(Path(self.runs).exists())

    def test_no_cache_turns_off_the_reads_and_goes_into_the_start_event_and_run_json(self):
        # Plan 39: the checkbox `Use caches` of the dialog; on by default.
        self.addCleanup(setattr, model_cache, "READ", True)
        for extra, use_cache in (((), True), (("--no-cache",), False)):
            with self.subTest(extra=extra):
                code, events = self.run_main(REMOTE, "--limit", "1", *extra)
                self.assertEqual(code, 0)
                self.assertIs(model_cache.READ, use_cache)
                self.assertIs(events[0]["use_cache"], use_cache)
                meta = json.loads((Path(self.runs) / events[-1]["run_id"] / "run.json")
                                  .read_text("utf-8"))
                self.assertIs(meta["use_cache"], use_cache)


class RoutesTest(Lab):
    class Server:
        def __init__(self, config, jobs, runs):
            self.config_path, self.run_jobs_dir, self.runs_dir = config, jobs, runs

    def respond(self, method, path, body=None):
        server = self.Server(str(self.config), self.jobs, self.runs)
        raw = json.dumps(body).encode() if body is not None else None
        code, answer, _, _ = run_jobs.respond(server, method, path, lambda limit: raw)
        return code, answer

    def test_the_routes(self):
        self.assertTrue(run_jobs.handles("/api/run-jobs"))
        self.assertTrue(run_jobs.handles("/api/run-jobs/%s/stop" % REMOTE))
        self.assertFalse(run_jobs.handles("/api/runs"))
        self.assertEqual(self.respond("GET", "/api/run-configurations")[0], 400)
        code, answer = self.respond("GET", "/api/run-configurations?set=my")
        self.assertEqual((code, answer["queries"]), (200, 7))
        self.assertEqual(self.respond("GET", "/api/run-configurations?set=nope")[0], 404)
        code, answer = self.respond("GET", "/api/run-jobs")
        self.assertEqual((code, answer["jobs"]), (200, []))
        self.assertEqual(self.respond("POST", "/api/run-jobs")[0], 400)
        self.assertEqual(self.respond("GET", "/api/run-jobs/%s/stop" % REMOTE)[0], 405)
        self.assertEqual(self.respond("POST", "/api/run-jobs/%s/stop" % REMOTE)[0], 409)

    def wait_for(self, name, test, seconds=30):
        deadline = time.time() + seconds
        while time.time() < deadline:
            job = run_jobs.job(self.jobs, name)
            if test(job):
                return job
            time.sleep(0.1)
        self.fail("the job of %s never reached the state: %s" % (name, job))

    def test_a_job_runs_as_a_process_and_the_stop_button_stops_it(self):
        Matcher.delay = 0.4
        code, answer = self.respond("POST", "/api/run-jobs",
                                    {"configuration": REMOTE, "set": "my", "workers": 1})
        self.assertEqual(code, 202, answer)
        self.assertEqual(self.respond("POST", "/api/run-jobs",
                                      {"configuration": REMOTE, "set": "my"})[0], 409)
        running = self.wait_for(REMOTE, lambda j: j["state"] == "running" and j["done"] >= 1)
        self.assertEqual((running["todo"], running["set"], running["workers"]), (7, "my", 1))
        self.assertIn(REMOTE, [j["name"] for j in self.respond("GET", "/api/run-jobs")[1]["jobs"]])
        self.assertEqual(self.respond("POST", "/api/run-jobs/%s/stop" % REMOTE)[0], 202)
        stopped = self.wait_for(REMOTE, lambda j: j["state"] not in run_jobs.ACTIVE)
        self.assertEqual(stopped["state"], "stopped", stopped)
        meta = json.loads((Path(self.runs) / stopped["run_id"] / "run.json").read_text("utf-8"))
        self.assertEqual(meta["configuration"], REMOTE)
        self.assertLess(meta["answered"], 7)
        self.assertEqual(self.respond("POST", "/api/run-jobs/%s/stop" % REMOTE)[0], 409)

    def test_a_job_that_ends_is_done_with_its_run(self):
        code, answer = self.respond("POST", "/api/run-jobs",
                                    {"configuration": REMOTE, "set": "my", "limit": 4})
        self.assertEqual(code, 202, answer)
        job = self.wait_for(REMOTE, lambda j: j["state"] not in run_jobs.ACTIVE)
        self.assertEqual((job["state"], job["done"], job["todo"]), ("done", 4, 4), job)
        self.assertTrue((Path(self.runs) / job["run_id"] / "metrics.json").exists())


class UseCacheTest(Lab):
    """Plan 39: the checkbox `Use caches` of the dialog `Run>`."""

    def command(self, **extra):
        body = dict({"configuration": REMOTE, "set": "my"}, **extra)
        with mock.patch.object(run_jobs.subprocess, "Popen") as popen:
            popen.return_value.pid = 4321
            popen.return_value.poll.return_value = 0
            code, answer = run_jobs.start(self.settings(), self.jobs, body, self.runs)
        self.assertEqual(code, 202, answer)
        return popen.call_args[0][0]

    def test_use_cache_false_alone_puts_no_cache_into_the_command(self):
        self.assertIn("--no-cache", self.command(use_cache=False))
        for extra in ({}, {"use_cache": True}, {"use_cache": None}):
            with self.subTest(extra=extra):
                self.assertNotIn("--no-cache", self.command(**extra))


BARCODE = "emb-barcode"


class FakeBackend:
    """An embedding backend of `benchmark.run_benchmark` that answers wine-a at once."""

    def __init__(self, pipeline):
        self.id, self.top_k = pipeline.name, 2
        self.spec = {"id": pipeline.name, "label": "fake", "workers": 1}
        self.catalogue = mock.Mock(state={"built": "2026-09-26T19:00:00+0300"})

    def ask(self, path):
        return [{"slug": "wine-a", "score": 0.9, "rank": 1}], 5, 200, None


class UseBarcodeTest(Lab):
    """Plan 53: the checkbox `Disable barcode fast path` of the dialog `Run>`. The Lab
    config gets one more pipeline, with the key `barcode`."""

    def setUp(self):
        super().setUp()
        config = json.loads(self.config.read_text(encoding="utf-8"))
        config["pipeline"].append({"name": BARCODE, "backend": "embedding",
                                   "embedding": "gw", "barcode": {}})
        self.config.write_text(json.dumps(config), encoding="utf-8")

    def command(self, name, **extra):
        body = dict({"configuration": name, "set": "my"}, **extra)
        with mock.patch.object(run_jobs.subprocess, "Popen") as popen, \
                mock.patch.object(embedding_run, "index_ready", return_value=True):
            popen.return_value.pid = 4321
            popen.return_value.poll.return_value = 0
            code, answer = run_jobs.start(self.settings(), self.jobs, body, self.runs)
        self.assertEqual(code, 202, answer)
        run_jobs._PROCESSES.clear()
        return popen.call_args[0][0]

    def test_each_pipeline_tells_whether_it_has_the_barcode_step(self):
        view = run_jobs.configurations_view(self.settings(), self.jobs, "my")
        self.assertEqual({c["name"]: c["barcode"] for c in view["configurations"]},
                         {REMOTE: False, "broken": False, "emb": False, BARCODE: True})

    def test_use_barcode_false_gives_no_barcode_to_a_barcode_pipeline_alone(self):
        self.assertIn("--no-barcode", self.command(BARCODE, use_barcode=False))
        self.assertNotIn("--no-barcode", self.command(REMOTE, use_barcode=False))
        for extra in ({}, {"use_barcode": True}, {"use_barcode": None}):
            with self.subTest(extra=extra):
                self.assertNotIn("--no-barcode", self.command(BARCODE, **extra))

    def test_use_barcode_MUST_be_a_boolean(self):
        code, answer = run_jobs.start(self.settings(), self.jobs, {
            "configuration": BARCODE, "set": "my", "use_barcode": "no"}, self.runs)
        self.assertEqual(code, 400)
        self.assertIn("use_barcode MUST", answer["error"])
        self.assertEqual(run_jobs._PROCESSES, {})

    def test_no_barcode_drops_the_step_and_goes_into_the_start_event_and_run_json(self):
        seen = []

        def build(pipeline, config_path):
            seen.append(pipeline.barcode)
            return FakeBackend(pipeline)

        with mock.patch.object(embedding_run, "build_pipeline_backend", side_effect=build):
            for extra, use_barcode in (((), True), (("--no-barcode",), False)):
                with self.subTest(extra=extra):
                    code, events = self.run_main(BARCODE, "--limit", "1", *extra)
                    self.assertEqual((code, events[-1]["event"]), (0, "done"), events[-1])
                    self.assertIs(events[0]["use_barcode"], use_barcode)
                    meta = json.loads((Path(self.runs) / events[-1]["run_id"] / "run.json")
                                      .read_text("utf-8"))
                    self.assertIs(meta["use_barcode"], use_barcode)
        # The step options reach `build` alone when the box is off.
        self.assertIsInstance(seen[0], dict)
        self.assertIsNone(seen[1])

    def test_a_pipeline_with_no_barcode_step_records_nothing(self):
        code, events = self.run_main(REMOTE, "--limit", "1", "--no-barcode")
        self.assertEqual(code, 0)
        self.assertIsNone(events[0]["use_barcode"])
        meta = json.loads((Path(self.runs) / events[-1]["run_id"] / "run.json")
                          .read_text("utf-8"))
        self.assertNotIn("use_barcode", meta)


class SelftestJobTest(Lab):
    """Plan 67: the button `Selftest` of `/embedding`. `POST /api/run-jobs` with the key
    `selftest` starts `run_job.py --selftest`; the job is `selftest-<embedding>`."""

    ROWS = [{"query_id": "q-%06d" % number, "image_path": "wine-a/main-%012d.png" % number,
             "abs_path": "/nowhere/%d.png" % number, "image_sha256": "%064d" % number,
             "slug": "wine-a", "image_type": "main", "label": "positive",
             "truth": ["wine-a"]} for number in (1, 2)]

    def start(self, body):
        with mock.patch.object(run_jobs.subprocess, "Popen") as popen, \
                mock.patch.object(embedding_run, "index_ready", return_value=True):
            popen.return_value.pid = 4321
            popen.return_value.poll.return_value = 0
            code, answer = run_jobs.start(self.settings(), self.jobs, body, self.runs)
        run_jobs._PROCESSES.clear()
        return code, answer, popen.call_args[0][0] if popen.called else None

    def test_the_key_selftest_starts_run_job_with_selftest(self):
        code, answer, command = self.start({"selftest": "gw", "limit": 5, "workers": 2,
                                            "use_cache": False})
        self.assertEqual(code, 202, answer)
        self.assertEqual((answer["name"], answer["set"]), ("selftest-gw", "dataset"))
        self.assertEqual(command[1:], [
            run_jobs.RUNNER, "--config", str(self.config), "--selftest", "--name", "gw",
            "--jobs-dir", self.jobs, "--limit", "5", "--workers", "2", "--no-cache",
            "--runs-dir", self.runs])
        self.assertTrue(os.path.isdir(os.path.join(self.jobs, "selftest-gw")))

    def test_a_selftest_checks_the_body_before_it_starts_a_process(self):
        wrong = [
            ({"selftest": 5}, 400, "selftest MUST name"),
            ({"selftest": "Bad Name"}, 400, "selftest MUST name"),
            ({"selftest": "gw", "set": "my"}, 400, "no configuration and no set"),
            ({"selftest": "gw", "configuration": "emb"}, 400, "no configuration and no set"),
            ({"selftest": "gw", "device_ip": "192.168.86.42"}, 400,
             "not valid for a self-test"),
            ({"selftest": "gw", "limit": 0}, 400, "limit MUST"),
            ({"selftest": "gw", "use_cache": "no"}, 400, "use_cache MUST"),
            ({"selftest": "nope"}, 404, "no embedding nope"),
        ]
        for body, code, text in wrong:
            with self.subTest(body=body):
                got, answer, command = self.start(body)
                self.assertEqual(got, code)
                self.assertIn(text, answer["error"])
                self.assertIsNone(command)
        # With no mock, the embedding `gw` has no index.
        got, answer = run_jobs.start(self.settings(), self.jobs, {"selftest": "gw"}, self.runs)
        self.assertEqual(got, 400)
        self.assertIn(embedding_run.NO_INDEX, answer["error"])
        self.assertEqual(run_jobs._PROCESSES, {})

    def test_the_runner_writes_a_run_of_the_set_dataset_with_no_barcode(self):
        import selftest
        seen = []

        def build(embedding, config_path, rows):
            seen.append((embedding, len(rows)))
            return FakeBackend(types.SimpleNamespace(name="selftest-" + embedding))

        out = io.StringIO()
        with mock.patch.object(selftest, "read_queries", return_value=(self.ROWS, {})), \
                mock.patch.object(selftest, "build_backend", side_effect=build), \
                contextlib.redirect_stdout(out):
            code = run_job.main(["--config", str(self.config), "--selftest", "--name", "gw",
                                 "--jobs-dir", self.jobs, "--runs-dir", self.runs])
        events = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual((code, events[-1]["event"]), (0, "done"), events[-1])
        self.assertEqual(seen, [("gw", 2)])
        start = next(e for e in events if e["event"] == "start")
        self.assertEqual((start["configuration"], start["set"], start["todo"],
                          start["use_barcode"]), ("selftest-gw", "dataset", 2, False))
        run_dir = Path(self.runs) / events[-1]["run_id"]
        self.assertTrue(run_dir.name.endswith("-lab-selftest-gw-dataset"))
        meta = json.loads((run_dir / "run.json").read_text("utf-8"))
        self.assertEqual((meta["configuration"], meta["options"]["set"], meta["use_barcode"]),
                         ("selftest-gw", "dataset", False))
        # The lock of the job is in the directory of `selftest-gw`, and the end frees it.
        directory = os.path.join(self.jobs, "selftest-gw")
        self.assertTrue(os.path.isdir(directory))
        self.assertIsNone(run_jobs.read_lock(directory))

    def test_the_runner_refuses_a_set_with_selftest_and_needs_a_set_without_it(self):
        for args, text in ((["--selftest", "--name", "gw", "--set", "my"], "takes no --set"),
                           (["--name", REMOTE], "--set is required")):
            with self.subTest(args=args):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = run_job.main(["--config", str(self.config), "--jobs-dir",
                                         self.jobs, *args])
                event = json.loads(out.getvalue().splitlines()[-1])
                self.assertEqual((code, event["event"]), (2, "failed"))
                self.assertIn(text, event["message"])


if __name__ == "__main__":
    unittest.main()
