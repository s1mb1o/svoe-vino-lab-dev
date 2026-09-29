"""Tests of plan 59: the key `rebuild_embeddings_on_run` of `config.yaml`
(`pipeline/rebuild_on_run.py`), and its calls in `pipeline/run_job.py` and
`pipeline/embedding_run.py`."""
import contextlib
import io
import json
import os
import signal
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX  # noqa: E402
import embedding_run  # noqa: E402
import embeddings  # noqa: E402
import import_testset as IT  # noqa: E402
import pipelines  # noqa: E402
import rebuild_on_run  # noqa: E402
import run_job  # noqa: E402

REAL_BUILD = rebuild_on_run.BUILD_SCRIPT
MISSING = object()
PHOTOS = {"wine-a/01.jpg": b"a1", "wine-b/01.jpg": b"b1"}
LABELS = {"wine-a": {"01.jpg": {"label": "positive"}},
          "wine-b": {"01.jpg": {"label": "positive"}}}
STEPS = {"full": {"steps": [{"step": "segment", "target": "package"}]}}
START = {"event": "start", "items": 3, "current": 1, "todo": 2, "pruned": 0}
DONE = {"event": "done", "built": 1, "failed": 1, "done": 2, "current": 1, "pruned": 0,
        "todo": 2, "seconds": 0.1}

# A stand-in of `build_embeddings.py`. Each start appends its arguments to `calls.jsonl`.
# `plan.json` holds one step for each start (the last step repeats): the lines to write,
# the exit code, and `wait_for_term` (wait for SIGTERM, then write `stopped`).
FAKE_BUILD = '''\
import json
import os
import signal
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CALLS = os.path.join(HERE, "calls.jsonl")
with open(CALLS, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(sys.argv[1:]) + "\\n")
with open(CALLS, encoding="utf-8") as fh:
    number = len(fh.read().splitlines()) - 1
with open(os.path.join(HERE, "plan.json"), encoding="utf-8") as fh:
    plan = json.load(fh)
step = plan[min(number, len(plan) - 1)]
stop = []
signal.signal(signal.SIGTERM, lambda signum, frame: stop.append(signum))
for event in step.get("events", []):
    print(json.dumps(event), flush=True)
if step.get("wait_for_term"):
    deadline = time.time() + 20
    while not stop and time.time() < deadline:
        time.sleep(0.02)
    print(json.dumps({"event": "stopped", "built": 0, "failed": 0, "done": 0}), flush=True)
sys.exit(step.get("code", 0))
'''


class FakeBackend:
    """An embedding backend of `benchmark.run_benchmark` that answers wine-a at once."""

    def __init__(self, pipeline, *args):
        self.id, self.top_k = pipeline.name, 2
        self.spec = {"id": pipeline.name, "label": "fake", "workers": 1}
        self.catalogue = mock.Mock(state={"built_at": "2026-09-27T09:00:00+0300"})

    def ask(self, path):
        return [{"slug": "wine-a", "score": 0.9, "rank": 1}], 5, 200, None


class Lab(unittest.TestCase):
    """A database with the set `my`, and a config.yaml with the embedding `gw`, its
    pipeline `emb`, and the pipeline `remote`. `gw` has an index, and the stand-in takes
    the place of the build script."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(self.root)
        IT.import_testset(self.db, "my", FX.write_set(self.root, PHOTOS, LABELS),
                          lambda m: None, self.schema)
        self.config = self.root / "config.yaml"
        self.write_config(True)
        self.entry = Path(embeddings.entry_dir(self.db, "gw"))
        self.entry.mkdir(parents=True)
        (self.entry / embeddings.INDEX).write_text("{}", encoding="utf-8")
        (self.entry / "vectors-00000000.npy").write_bytes(b"")
        self.fake = self.root / "fake" / "fake_build.py"
        self.fake.parent.mkdir()
        self.fake.write_text(FAKE_BUILD, encoding="utf-8")
        self.plan([{"events": [START, DONE]}])
        patcher = mock.patch.object(rebuild_on_run, "BUILD_SCRIPT", str(self.fake))
        patcher.start()
        self.addCleanup(patcher.stop)
        # `run_job.main` puts its own SIGTERM handler in place.
        self.addCleanup(signal.signal, signal.SIGTERM, signal.getsignal(signal.SIGTERM))
        self.jobs, self.runs = str(self.root / "jobs"), str(self.root / "runs")
        self.lines = []

    def write_config(self, value=MISSING, **extra):
        config = {"rootdir": str(self.root), "database_file": self.db, "embeddings": [
            {"name": "gw", "backend": "openai", "base_url": "http://127.0.0.1:9/v1",
             "model": "m", "views": STEPS}], "pipeline": [
            {"name": "emb", "backend": "embedding", "embedding": "gw"},
            {"name": "remote", "backend": "svoe-vino-ru", "url": "http://127.0.0.1:9/x"}]}
        if value is not MISSING:
            config[rebuild_on_run.KEY] = value
        config.update(extra)
        self.config.write_text(json.dumps(config), encoding="utf-8")

    def plan(self, steps):
        (self.fake.parent / "plan.json").write_text(json.dumps(steps), encoding="utf-8")

    def calls(self):
        path = self.fake.parent / "calls.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text("utf-8").splitlines()]

    def before_run(self, name, sleep=time.sleep):
        pipeline = pipelines.load(str(self.config)).find(name)
        return rebuild_on_run.before_run(pipeline, str(self.config), self.lines.append,
                                         sleep)

    def run_main(self, *argv):
        # A real file: the SIGTERM handler of `run_job` writes to the file descriptor.
        path = self.root / "stdout.jsonl"
        with open(path, "w", encoding="utf-8") as out, contextlib.redirect_stdout(out):
            code = run_job.main(["--config", str(self.config), "--jobs-dir", self.jobs,
                                 "--runs-dir", self.runs, *argv])
        return code, [json.loads(line) for line in path.read_text("utf-8").splitlines()]


class KeyTest(Lab):
    def test_a_missing_key_or_null_is_false_and_a_boolean_is_its_value(self):
        for value, expected in ((MISSING, False), (None, False), (False, False),
                                (True, True)):
            with self.subTest(value=value):
                self.write_config(value)
                self.assertIs(rebuild_on_run.enabled(str(self.config)), expected)

    def test_another_value_is_an_error(self):
        for value in ("true", 1, [True]):
            with self.subTest(value=value):
                self.write_config(value)
                with self.assertRaisesRegex(embeddings.ConfigError,
                                            "rebuild_embeddings_on_run MUST be true or false"):
                    rebuild_on_run.enabled(str(self.config))


class BeforeRunTest(Lab):
    def test_no_build_when_the_key_is_false(self):
        self.write_config(False)
        self.assertIsNone(self.before_run("emb"))
        self.assertEqual(self.calls(), [])

    def test_no_build_for_a_pipeline_with_no_embedding(self):
        self.assertIsNone(self.before_run("remote"))
        self.assertEqual(self.calls(), [])

    def test_no_build_for_an_embedding_with_no_index(self):
        # The first build stays an action on /embedding (owner answers of 08:53:00).
        (self.entry / "vectors-00000000.npy").unlink()
        self.assertIsNone(self.before_run("emb"))
        self.assertIn("the embedding gw has no index", self.lines[-1])
        self.assertEqual(self.calls(), [])

    def test_the_build_gets_the_config_and_the_name_and_writes_at_the_end_of_build_log(self):
        self.write_config(True, embedding_python=sys.executable)
        log = self.entry / embeddings.LOG
        log.write_text('{"event": "done", "built": 9}\n', encoding="utf-8")
        final = self.before_run("emb")
        self.assertEqual(final["event"], "done")
        self.assertEqual(self.calls(), [["--config", str(self.config), "--name", "gw"]])
        lines = [json.loads(line) for line in log.read_text("utf-8").splitlines()]
        self.assertEqual(lines[0], {"event": "done", "built": 9})  # the old lines stay
        self.assertEqual([line["event"] for line in lines[1:]], ["start", "done"])
        # The Embeddings page reads the lines after the last `start`.
        self.assertEqual(embeddings.job_state(str(self.entry))["state"], "done")
        self.assertIn("rebuild_embeddings_on_run: the build of gw starts", self.lines[0])
        # A failed item does not stop the run.
        self.assertIn("1 items were current, 1 built, 1 failed, 0 removed", self.lines[-1])

    def test_an_error_an_exit_with_no_final_line_and_a_stop_raise_an_error(self):
        error = {"event": "error", "message": "boom"}
        cases = (
            ({"events": [START, error], "code": 1}, "the build of gw failed: boom"),
            ({"events": [START], "code": 1},
             "the build of gw failed: exit code 1 and no final line"),
            ({"events": [START, DONE], "code": 1},
             "the build of gw failed: exit code 1 after the event done"),
            ({"events": [START, {"event": "stopped", "built": 0}]},
             "the build of gw stopped before its end; the run did not start"))
        for step, message in cases:
            with self.subTest(message=message):
                self.plan([step])
                with self.assertRaises(embeddings.ConfigError) as caught:
                    self.before_run("emb")
                self.assertEqual(str(caught.exception), message)

    def test_exit_code_3_makes_the_run_wait_and_start_again(self):
        busy = {"event": "error", "message": "another build of this embedding runs: PID 7"}
        self.plan([{"events": [busy], "code": 3}, {"events": [START, DONE]}])
        self.assertEqual(self.before_run("emb")["event"], "done")
        self.assertEqual(len(self.calls()), 2)
        self.assertTrue(any("took the lock first" in line for line in self.lines))

    def test_a_running_build_is_waited_for(self):
        sleeps = []
        with mock.patch.object(embeddings, "running_pid", side_effect=[4242, 4242, None]):
            final = self.before_run("emb", sleep=sleeps.append)
        self.assertEqual(final["event"], "done")
        self.assertEqual(sleeps, [rebuild_on_run.POLL_SECONDS] * 2)
        self.assertIn("a build of gw runs: PID 4242", self.lines[0])
        self.assertEqual(len(self.calls()), 1)

    def test_a_new_build_pid_gets_a_new_line(self):
        # Plan 88: a stop of the build, and a new build of the `Build All` queue.
        with mock.patch.object(embeddings, "running_pid",
                               side_effect=[4242, 4242, 5151, None]):
            self.before_run("emb", sleep=lambda seconds: None)
        waits = [line for line in self.lines if "the run waits for its end" in line]
        self.assertEqual(len(waits), 2)
        self.assertIn("PID 4242", waits[0])
        self.assertIn("PID 5151", waits[1])

    def test_an_embedding_python_that_is_not_a_file_is_an_error(self):
        self.write_config(True, embedding_python=str(self.root / "no-python"))
        with self.assertRaisesRegex(embeddings.ConfigError, "embedding_python .* is not a file"):
            self.before_run("emb")
        self.assertEqual(self.calls(), [])


class RunJobTest(Lab):
    def test_the_real_build_updates_the_index_before_the_event_start(self):
        with mock.patch.object(rebuild_on_run, "BUILD_SCRIPT", REAL_BUILD), \
                mock.patch.object(embedding_run, "build_pipeline_backend",
                                  side_effect=FakeBackend):
            code, events = self.run_main("--name", "emb", "--set", "my", "--limit", "1")
        self.assertEqual((code, events[-1]["event"]), (0, "done"), events[-1])
        kinds = [event["event"] for event in events]
        before = [event["message"] for event in events[:kinds.index("start")]
                  if event["event"] == "log"]
        self.assertTrue(any("the build of gw ended: 0 items were current, 0 built, 0 failed"
                            in message for message in before), before)
        # The real build wrote its lines into build.log and a checkpoint of 0 items.
        self.assertEqual(embeddings.read_events(str(self.entry))[0][-1]["event"], "done")
        self.assertEqual(embeddings.read_index(str(self.entry))["name"], "gw")

    def test_with_the_key_false_the_run_starts_no_build(self):
        self.write_config(False)
        with mock.patch.object(embedding_run, "build_pipeline_backend",
                               side_effect=FakeBackend):
            code, events = self.run_main("--name", "emb", "--set", "my", "--limit", "1")
        self.assertEqual((code, events[-1]["event"]), (0, "done"), events[-1])
        self.assertEqual(self.calls(), [])
        self.assertFalse((self.entry / embeddings.LOG).exists())

    def test_a_failed_build_fails_the_job_before_the_event_start(self):
        self.plan([{"events": [START, {"event": "error", "message": "boom"}], "code": 1}])
        with mock.patch.object(embedding_run, "build_pipeline_backend") as backend:
            code, events = self.run_main("--name", "emb", "--set", "my")
        self.assertEqual(code, 1)
        self.assertEqual((events[-1]["event"], events[-1]["message"]),
                         ("failed", "the build of gw failed: boom"))
        self.assertNotIn("start", [event["event"] for event in events])
        backend.assert_not_called()
        self.assertFalse(Path(self.runs).exists())

    def test_an_unknown_set_fails_before_a_build(self):
        code, events = self.run_main("--name", "emb", "--set", "nope")
        self.assertEqual((code, events[-1]["event"]), (1, "failed"))
        self.assertEqual(self.calls(), [])

    def test_sigterm_during_the_build_stops_the_build_and_the_job(self):
        self.plan([{"events": [START], "wait_for_term": True}])
        log = self.entry / embeddings.LOG

        def stop_when_the_build_runs():
            deadline = time.time() + 10
            while time.time() < deadline:
                if log.exists() and '"start"' in log.read_text("utf-8"):
                    os.kill(os.getpid(), signal.SIGTERM)
                    return
                time.sleep(0.02)

        threading.Thread(target=stop_when_the_build_runs, daemon=True).start()
        with mock.patch.object(embedding_run, "build_pipeline_backend") as backend:
            code, events = self.run_main("--name", "emb", "--set", "my")
        self.assertEqual(code, 0)
        self.assertEqual([event["event"] for event in events][-2:], ["stopping", "stopped"])
        self.assertEqual(events[-1]["message"], "stopped before the first answer")
        backend.assert_not_called()
        # The stand-in got SIGTERM from the run, so its last line is `stopped`.
        self.assertEqual(embeddings.read_events(str(self.entry))[0][-1]["event"], "stopped")


class EmbeddingRunTest(Lab):
    def main(self):
        return embedding_run.main(["--name", "emb", "--set", "my", "--config",
                                   str(self.config), "--runs-dir", self.runs])

    def test_the_update_comes_before_the_index_is_read(self):
        order = []

        def update(pipeline, config_path, log):
            order.append(("update", pipeline.name, config_path))

        def backend(pipeline, config_path, top_k):
            order.append(("backend", pipeline.name))
            raise embeddings.ConfigError("stop here")

        with mock.patch.object(rebuild_on_run, "before_run", side_effect=update), \
                mock.patch.object(embedding_run, "build_pipeline_backend",
                                  side_effect=backend), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.main(), 1)
        self.assertEqual(order, [("update", "emb", str(self.config)), ("backend", "emb")])

    def test_a_failed_update_stops_the_cli(self):
        err = io.StringIO()
        self.plan([{"events": [START, {"event": "error", "message": "boom"}], "code": 1}])
        with mock.patch.object(embedding_run, "build_pipeline_backend") as backend, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(self.main(), 1)
        backend.assert_not_called()
        self.assertIn("error: the build of gw failed: boom", err.getvalue())


if __name__ == "__main__":
    unittest.main()
