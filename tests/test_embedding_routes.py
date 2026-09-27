import contextlib
import io
import os
import sys
import tempfile
import time
import types
import unittest
import unittest.mock

import embedding_lab  # noqa: F401  (puts pipeline/ on sys.path)
from embedding_lab import FakeGateway, standard_lab

import alternatives  # noqa: E402
import build_embeddings  # noqa: E402
import embedding_routes  # noqa: E402
import embeddings  # noqa: E402

# A build that takes its lock, writes `start`, and waits for SIGTERM or 20 s. Its file
# name is the name of the build script, so the lock check accepts it.
FAKE_BUILD = r'''
import json, os, signal, sys, time
sys.path.insert(0, %(pipeline)r)
import embeddings
name = sys.argv[sys.argv.index("--name") + 1]
settings = embeddings.load_settings(sys.argv[sys.argv.index("--config") + 1])
directory = embeddings.entry_dir(settings.db_path, name)
embeddings.acquire_lock(directory)
stop = []
signal.signal(signal.SIGTERM, lambda *args: stop.append(1))
print(json.dumps({"event": "start", "pid": os.getpid(), "todo": 5, "t": time.time(),
                  "time": "now"}), flush=True)
deadline = time.time() + 20
while not stop and time.time() < deadline:
    time.sleep(0.05)
if stop:
    print(json.dumps({"event": "stopping"}), flush=True)
    print(json.dumps({"event": "stopped", "built": 0, "failed": 0, "done": 0}), flush=True)
else:
    print(json.dumps({"event": "done", "built": 5, "failed": 0, "done": 5}), flush=True)
embeddings.release_lock(directory)
'''


def wait_for(check, seconds=10):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if check():
            return True
        time.sleep(0.05)
    return False


class RoutesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.gateway = FakeGateway()
        self.lab = standard_lab(self.tmp.name, self.gateway.base_url)
        self.server = types.SimpleNamespace(db_path=self.lab.db_path,
                                            config_path=self.lab.config_path)
        self.saved_script = embedding_routes.BUILD_SCRIPT

    def tearDown(self):
        for process in embedding_routes._PROCESSES.values():
            process.kill()
            process.wait()
        embedding_routes._PROCESSES.clear()
        embedding_routes.BUILD_SCRIPT = self.saved_script
        self.gateway.close()
        self.lab.close()
        self.tmp.cleanup()

    def get(self, path, method="GET"):
        return embedding_routes.respond(self.server, method, path)

    def build(self):
        settings = embeddings.load_settings(self.lab.config_path)
        directory = self.lab.entry_dir()
        os.makedirs(directory, exist_ok=True)
        with contextlib.redirect_stdout(io.StringIO()):
            build_embeddings.run(settings.find("gw"), settings.db_path, directory,
                                 make_backend=lambda e: build_embeddings.OpenAIBackend(
                                     e, waits=(), timeout=10))

    def test_handles(self):
        for route in ("/embedding", "/api/embeddings", "/api/embeddings/gw",
                      "/api/embedding-jobs", "/embeddings/gw/images/x.png"):
            self.assertTrue(embedding_routes.handles(route), route)
        for route in ("/api/embedding", "/img/embedding", "/dataset", "/embeddingx"):
            self.assertFalse(embedding_routes.handles(route), route)

    def test_page(self):
        code, body, content_type, _ = self.get("/embedding")
        self.assertEqual(code, 200)
        self.assertIn("text/html", content_type)
        self.assertIn('class="on" href="/embedding"', body)
        self.assertNotIn("/* THEME_CSS */", body)
        self.assertIn("prefers-color-scheme: dark", body)

    def test_list_before_and_after_a_build(self):
        code, body, _, _ = self.get("/api/embeddings")
        self.assertEqual(code, 200)
        entry = body["embeddings"][0]
        self.assertEqual(entry["name"], "gw")
        self.assertEqual(entry["items"], 9)
        self.assertEqual(entry["counts"]["missing"], 9)
        self.assertIsNone(entry["job"]["state"])
        self.build()
        entry = self.get("/api/embeddings")[1]["embeddings"][0]
        self.assertEqual(entry["counts"], {"current": 4, "stale": 0, "missing": 0,
                                           "failed": 5, "not_applicable": 0})
        self.assertEqual(entry["dim"], 8)

    def test_entry_view_and_image_route(self):
        self.build()
        code, body, _, _ = self.get("/api/embeddings/gw")
        self.assertEqual(code, 200)
        records = {record["slug"]: record for record in body["records"]}
        self.assertNotIn("disabled", records)
        transparent = records["transparent"]["columns"]
        self.assertEqual([column["image_type"] for column in transparent], ["main", "label_front"])
        full = transparent[0]["cells"]["full"]
        self.assertEqual(full["status"], "current")
        self.assertEqual(transparent[0]["cells"]["label"]["status"], "failed")
        self.assertEqual(transparent[0]["cells"]["label"]["error"], embeddings.NO_CUT["label"])
        self.assertNotIn("full", transparent[1]["cells"])
        self.assertEqual(transparent[1]["cells"]["label"]["status"], "current")
        code, data, content_type, cache = self.get(full["url"])
        self.assertEqual((code, content_type), (200, "image/png"))
        self.assertTrue(data.startswith(b"\x89PNG"))
        self.assertIn("immutable", cache)
        unprocessed = records["unprocessed"]["columns"][0]["cells"]["full"]
        self.assertEqual(unprocessed["status"], "failed")
        self.assertNotIn("url", unprocessed)

    def test_a_not_applicable_label_is_named_and_not_counted_as_an_item(self):
        self.lab.conn.execute(
            "INSERT INTO image_derivative_absence VALUES (?, 'label', ?, ?)",
            (self.lab.grey, alternatives.SETTINGS_LABEL_ABSENCE,
             "the packet has no separate label"))
        self.lab.conn.commit()
        self.build()
        code, body, _, _ = self.get("/api/embeddings/gw")
        self.assertEqual(code, 200)
        self.assertEqual((body["embedding"]["items"],
                          body["embedding"]["counts"]["not_applicable"]), (8, 1))
        records = {record["slug"]: record for record in body["records"]}
        cell = records["grey"]["columns"][0]["cells"]["label"]
        self.assertEqual(cell, {"status": "not_applicable",
                                "error": "the packet has no separate label"})

    def test_a_cell_with_a_vector_row_gets_vector(self):
        self.build()
        records = {record["slug"]: record for record in self.get("/api/embeddings/gw")[1]["records"]}
        cells = records["transparent"]["columns"][0]["cells"]
        self.assertIs(cells["full"].get("vector"), True)
        self.assertNotIn("vector", cells["label"])
        # A vectors file that is gone, or shorter than the rows of the index: no badge.
        index = embeddings.read_index(self.lab.entry_dir())
        os.remove(os.path.join(self.lab.entry_dir(), index["vectors_file"]))
        records = {record["slug"]: record for record in self.get("/api/embeddings/gw")[1]["records"]}
        self.assertNotIn("vector", records["transparent"]["columns"][0]["cells"]["full"])

    def test_bad_image_paths(self):
        digest = "a" * 64
        for path in ("/embeddings/gw/images/%s_full.jpg" % digest,
                     "/embeddings/gw/images/../index.json",
                     "/embeddings/../data/images/%s_full.png" % digest,
                     "/embeddings/gw/images/%s_full.png" % digest):
            self.assertEqual(self.get(path)[0], 404, path)

    def test_unknown_and_broken_entries(self):
        self.assertEqual(self.get("/api/embeddings/none")[0], 404)
        self.lab.entries.append({"name": "bad", "backend": "grpc"})
        self.lab.write_config()
        code, body, _, _ = self.get("/api/embeddings/bad")
        self.assertEqual(code, 400)
        self.assertIn("backend MUST be", body["error"])
        entries = {entry["name"]: entry for entry in self.get("/api/embeddings")[1]["embeddings"]}
        self.assertIn("backend MUST be", entries["bad"]["error"])
        self.assertEqual(self.get("/api/embeddings/bad/build", "POST")[0], 400)

    def test_methods(self):
        self.assertEqual(self.get("/api/embeddings/gw/build")[0], 405)
        self.assertEqual(self.get("/api/embeddings", "POST")[0], 405)
        self.assertEqual(self.get("/api/embeddings/gw/stop", "POST")[0], 409)

    def test_start_second_start_and_stop(self):
        script_dir = os.path.join(self.tmp.name, "fake")
        os.makedirs(script_dir)
        script = os.path.join(script_dir, embeddings.BUILD_SCRIPT_NAME)
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(FAKE_BUILD % {"pipeline": os.path.dirname(embeddings.__file__)})
        embedding_routes.BUILD_SCRIPT = script
        self.lab.write_config(python=sys.executable)

        code, body, _, _ = self.get("/api/embeddings/gw/build", "POST")
        self.assertEqual(code, 202, body)
        self.assertEqual(self.get("/api/embeddings/gw/build", "POST")[0], 409)
        directory = self.lab.entry_dir()
        self.assertTrue(wait_for(lambda: embeddings.running_pid(directory)))
        self.assertTrue(wait_for(lambda: embeddings.job_state(directory)["todo"] == 5))
        jobs = {job["name"]: job for job in self.get("/api/embedding-jobs")[1]["jobs"]}
        self.assertEqual(jobs["gw"]["state"], "running")
        self.assertEqual(jobs["gw"]["todo"], 5)

        code, body, _, _ = self.get("/api/embeddings/gw/stop", "POST")
        self.assertEqual(code, 202, body)
        process = embedding_routes._PROCESSES[directory]
        process.wait(timeout=10)
        self.assertEqual(embeddings.job_state(directory)["state"], "stopped")
        self.assertEqual(self.get("/api/embeddings/gw/stop", "POST")[0], 409)

    def test_a_missing_interpreter_is_an_error(self):
        self.lab.write_config(python=os.path.join(self.tmp.name, "no-python"))
        code, body, _, _ = self.get("/api/embeddings/gw/build", "POST")
        self.assertEqual(code, 400)
        self.assertIn("is not a file", body["error"])


    def test_open_opens_the_directory_of_the_entry_alone(self):
        saved = embedding_routes.OPEN_COMMAND
        self.addCleanup(setattr, embedding_routes, "OPEN_COMMAND", saved)
        embedding_routes.OPEN_COMMAND = ("true",)
        code, body, _, _ = self.get("/api/embeddings/gw/open", "POST")
        self.assertEqual(code, 404)
        self.assertIn("not on disk yet", body["error"])
        os.makedirs(self.lab.entry_dir(), exist_ok=True)
        code, body, _, _ = self.get("/api/embeddings/gw/open", "POST")
        self.assertEqual((code, body["opened"]), (200, self.lab.entry_dir()))
        embedding_routes.OPEN_COMMAND = ("false",)
        code, body, _, _ = self.get("/api/embeddings/gw/open", "POST")
        self.assertEqual(code, 500)
        self.assertEqual(self.get("/api/embeddings/gw/open")[0], 405)
        self.assertEqual(self.get("/api/embeddings/nope/open", "POST")[0], 404)
        self.assertEqual(self.get("/api/embeddings/gw/open/x", "POST")[0], 404)

    def test_page_leaves_the_endpoint_out_of_the_directory_row(self):
        body = self.get("/embedding")[1]
        self.assertIn('k !== "endpoint"', body)
        self.assertIn("data-open-directory", body)
        self.assertIn("failed-count", body)

    def test_log_answers_the_text_of_the_build_log(self):
        code, body, _, _ = self.get("/api/embeddings/gw/log")
        self.assertEqual(code, 404)
        self.assertIn("no build log yet", body["error"])
        directory = self.lab.entry_dir()
        os.makedirs(directory, exist_ok=True)
        text = '{"event": "start", "pid": 1}\nTraceback (most recent call last):\n'
        with open(os.path.join(directory, embeddings.LOG), "w", encoding="utf-8") as fh:
            fh.write(text)
        code, body, content_type, cache = self.get("/api/embeddings/gw/log")
        self.assertEqual((code, body["name"], body["text"]), (200, "gw", text))
        self.assertEqual(body["file"], os.path.join(directory, embeddings.LOG))
        self.assertEqual((content_type, cache), (embedding_routes.JSON, embedding_routes.NO_STORE))
        self.assertEqual(self.get("/api/embeddings/gw/log", "POST")[0], 405)
        self.assertEqual(self.get("/api/embeddings/nope/log")[0], 404)
        self.assertEqual(self.get("/api/embeddings/gw/log/x")[0], 404)

    def test_page_has_the_build_log_dialog(self):
        body = self.get("/embedding")[1]
        self.assertIn('id="log-dialog"', body)
        self.assertIn('<button id="log" type="button" disabled', body)
        self.assertIn("/log`", body)
        self.assertIn('const LOG_HIDDEN = ["progress", "request"];', body)
        self.assertIn('<input id="log-show" type="checkbox" checked> Show progress and request', body)

    def test_page_has_the_image_preview_of_the_dataset_page(self):
        body = self.get("/embedding")[1]
        self.assertIn('id="image-preview-modal"', body)
        self.assertIn('data-preview="${esc(sha256)}_${esc(view)}"', body)
        self.assertIn('url.searchParams.set("preview", key)', body)
        self.assertIn("then(openPreviewOfUrl)", body)


class JobStateTest(unittest.TestCase):
    def write_log(self, directory, lines):
        with open(os.path.join(directory, embeddings.LOG), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    def test_states_from_the_log(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(embeddings.job_state(directory)["state"])
            start = '{"event": "start", "pid": 1, "todo": 3}'
            self.write_log(directory, [start, '{"event": "done", "built": 3, "failed": 0}'])
            self.assertEqual(embeddings.job_state(directory)["state"], "done")
            self.write_log(directory, [start, '{"event": "progress", "done": 1, "todo": 3}',
                                       "Traceback (most recent call last):", "KeyError: 'x'"])
            job = embeddings.job_state(directory)
            self.assertEqual((job["state"], job["message"], job["done"]), ("failed", "KeyError: 'x'", 1))
            self.write_log(directory, ['{"event": "error", "message": "no database"}'])
            job = embeddings.job_state(directory)
            self.assertEqual((job["state"], job["message"]), ("failed", "no database"))

    def test_the_phase_of_a_running_build(self):
        # The lock check accepts a build process alone; this test stands in for one.
        alive = unittest.mock.patch.object(embeddings, "build_alive", return_value=True)
        with tempfile.TemporaryDirectory() as directory, alive:
            with open(os.path.join(directory, embeddings.LOCK), "w", encoding="utf-8") as fh:
                fh.write('{"pid": %d}' % os.getpid())
            start = '{"event": "start", "pid": %d, "todo": 32, "t": 1.0}' % os.getpid()
            request = '{"event": "request", "images": 16, "t": 2.0}'
            self.write_log(directory, [start, request])
            job = embeddings.job_state(directory)
            self.assertEqual((job["state"], job["phase"], job["phase_event"], job["phase_t"]),
                             ("running", "waiting for the model", "request", 2.0))
            retry = ('{"event": "retry", "attempt": 1, "wait": 2, "error": "HTTP 503 from x",'
                     ' "t": 3.0}')
            self.write_log(directory, [start, request, retry])
            job = embeddings.job_state(directory)
            self.assertEqual((job["phase"], job["phase_event"]),
                             ("retry 1 in 2 s: HTTP 503 from x", "retry"))
            progress = '{"event": "progress", "done": 16, "todo": 32, "t": 4.0}'
            self.write_log(directory, [start, request, retry, progress])
            job = embeddings.job_state(directory)
            self.assertEqual((job["done"], job["phase"], job["phase_t"]), (16, None, None))
            # A build that ended has no phase.
            os.remove(os.path.join(directory, embeddings.LOCK))
            self.write_log(directory, [start, request])
            self.assertIsNone(embeddings.job_state(directory)["phase"])


class BuildAllTest(unittest.TestCase):
    """The queue of `Build All` (plan 60)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.gateway = FakeGateway()
        self.lab = standard_lab(self.tmp.name, self.gateway.base_url)
        self.lab.add_entry("gw2")
        self.lab.entries.append({"name": "bad", "backend": "grpc"})
        self.lab.write_config(python=sys.executable)
        self.server = types.SimpleNamespace(db_path=self.lab.db_path,
                                            config_path=self.lab.config_path)
        self.saved = (embedding_routes.BUILD_SCRIPT, embedding_routes.QUEUE_POLL_SECONDS)
        embedding_routes.QUEUE_POLL_SECONDS = 0.05
        self.fast = self.script("fast", 0.3)
        self.slow = self.script("slow", 20)

    def tearDown(self):
        # A killed build fails, and the queue starts the next entry: kill until it ends.
        deadline = time.time() + 10
        while True:
            for process in list(embedding_routes._PROCESSES.values()):
                process.kill()
                process.wait()
            queue = embedding_routes.queue_view()
            if not queue or queue["state"] != "running" or time.time() > deadline:
                break
            time.sleep(0.05)
        embedding_routes._PROCESSES.clear()
        embedding_routes._QUEUE = None
        embedding_routes.BUILD_SCRIPT, embedding_routes.QUEUE_POLL_SECONDS = self.saved
        self.gateway.close()
        self.lab.close()
        self.tmp.cleanup()

    def script(self, folder, seconds):
        """A fake build that ends as `done` after `seconds`, or as `stopped` at SIGTERM."""
        directory = os.path.join(self.tmp.name, folder)
        os.makedirs(directory)
        path = os.path.join(directory, embeddings.BUILD_SCRIPT_NAME)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(FAKE_BUILD.replace("time.time() + 20", "time.time() + %r" % seconds)
                     % {"pipeline": os.path.dirname(embeddings.__file__)})
        return path

    def get(self, path, method="GET"):
        return embedding_routes.respond(self.server, method, path)

    def queue_ends(self):
        return wait_for(lambda: embedding_routes.queue_view()["state"] != "running", 15)

    def test_each_entry_is_built_one_at_a_time_in_config_order(self):
        embedding_routes.BUILD_SCRIPT = self.fast
        code, body, _, _ = self.get("/api/embeddings/build-all", "POST")
        self.assertEqual(code, 202, body)
        # The entry with a configuration error is not in the queue.
        self.assertEqual(body["queue"]["names"], ["gw", "gw2"])
        self.assertEqual(body["queue"]["state"], "running")
        code, body, _, _ = self.get("/api/embeddings/build-all", "POST")
        self.assertEqual(code, 409)
        self.assertIn("Build All runs", body["error"])
        self.assertTrue(self.queue_ends())
        queue = self.get("/api/embedding-jobs")[1]["queue"]
        self.assertEqual(queue["state"], "done")
        self.assertEqual([(r["name"], r["state"], r["built"]) for r in queue["results"]],
                         [("gw", "done", 5), ("gw2", "done", 5)])
        self.assertIsNotNone(queue["ended_t"])
        self.assertEqual(self.get("/api/embeddings")[1]["queue"]["state"], "done")
        # A GET of the path stays the view of an entry `build-all`.
        self.assertEqual(self.get("/api/embeddings/build-all")[0], 404)
        # The queue that ended does not block a new one.
        self.assertEqual(self.get("/api/embeddings/build-all", "POST")[0], 202)
        self.assertTrue(self.queue_ends())

    def test_a_stop_of_its_build_stops_the_queue(self):
        embedding_routes.BUILD_SCRIPT = self.slow
        self.assertEqual(self.get("/api/embeddings/build-all", "POST")[0], 202)
        self.assertTrue(wait_for(lambda: embeddings.running_pid(self.lab.entry_dir())))
        self.assertEqual(self.get("/api/embeddings/gw/stop", "POST")[0], 202)
        self.assertTrue(self.queue_ends())
        queue = embedding_routes.queue_view()
        self.assertEqual(queue["state"], "stopped")
        self.assertEqual(queue["current"], "gw")
        self.assertEqual([(r["name"], r["state"]) for r in queue["results"]],
                         [("gw", "stopped")])
        self.assertFalse(os.path.exists(os.path.join(self.lab.entry_dir("gw2"),
                                                     embeddings.LOG)))

    def test_a_build_that_runs_already_is_waited_for(self):
        embedding_routes.BUILD_SCRIPT = self.slow
        self.assertEqual(self.get("/api/embeddings/gw/build", "POST")[0], 202)
        self.assertTrue(wait_for(lambda: embeddings.running_pid(self.lab.entry_dir())))
        embedding_routes.BUILD_SCRIPT = self.fast
        self.assertEqual(self.get("/api/embeddings/build-all", "POST")[0], 202)
        time.sleep(0.3)
        self.assertEqual(embedding_routes.queue_view()["results"], [])
        # The stop of the other build does not stop the queue: it builds gw itself.
        self.assertEqual(self.get("/api/embeddings/gw/stop", "POST")[0], 202)
        self.assertTrue(self.queue_ends())
        queue = embedding_routes.queue_view()
        self.assertEqual(queue["state"], "done")
        self.assertEqual([(r["name"], r["state"]) for r in queue["results"]],
                         [("gw", "done"), ("gw2", "done")])

    def test_a_missing_interpreter_is_an_error(self):
        self.lab.write_config(python=os.path.join(self.tmp.name, "no-python"))
        code, body, _, _ = self.get("/api/embeddings/build-all", "POST")
        self.assertEqual(code, 400)
        self.assertIn("is not a file", body["error"])
        self.assertIsNone(embedding_routes.queue_view())

    def test_the_page_has_the_button(self):
        page = self.get("/embedding")[1]
        self.assertIn('id="build-all"', page)
        self.assertIn("/api/embeddings/build-all", page)


if __name__ == "__main__":
    unittest.main()
