import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np

import embedding_lab  # noqa: F401  (puts pipeline/ on sys.path)
from embedding_lab import FakeGateway, standard_lab

import build_embeddings  # noqa: E402
import embeddings  # noqa: E402


def quiet_backend(embedding):
    """The OpenAI backend with no waits between the tries."""
    return build_embeddings.OpenAIBackend(embedding, waits=(), timeout=10)


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.gateway = FakeGateway()
        self.lab = standard_lab(self.tmp.name, self.gateway.base_url)

    def tearDown(self):
        self.gateway.close()
        self.lab.close()
        self.tmp.cleanup()

    def build(self, name="gw", stop=None, make_backend=quiet_backend):
        """Run one build. Return (counts, events)."""
        settings = embeddings.load_settings(self.lab.config_path)
        embedding = settings.find(name)
        directory = self.lab.entry_dir(name)
        os.makedirs(directory, exist_ok=True)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            counts = build_embeddings.run(embedding, settings.db_path, directory,
                                          make_backend=make_backend, stop=stop)
        events = [json.loads(line) for line in out.getvalue().splitlines()]
        return counts, events

    def index(self, name="gw"):
        directory = self.lab.entry_dir(name)
        index = embeddings.read_index(directory)
        return index, embeddings.read_vectors(directory, index)

    def test_first_build_writes_images_vectors_and_failures(self):
        counts, events = self.build()
        # 4 full images and 1 close-up: 4 full items, 5 label items.
        self.assertEqual((counts["built"], counts["failed"], counts["todo"]), (4, 5, 9))
        self.assertEqual([event["event"] for event in events][0], "start")
        self.assertEqual(events[-1]["event"], "done")
        index, vectors = self.index()
        self.assertEqual(vectors.shape, (4, 8))
        np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1.0, rtol=1e-5)
        self.assertEqual(index["dim"], 8)
        built = {(item["source_sha256"], item["view"]) for item in index["items"]}
        self.assertEqual(built, {(self.lab.transparent, "full"), (self.lab.grey, "full"),
                                 (self.lab.patched, "full"), (self.lab.closeup, "label")})
        errors = {(failure["source_sha256"], failure["view"]): failure["error"]
                  for failure in index["failures"]}
        self.assertEqual(errors[(self.lab.unprocessed, "full")], embeddings.NO_CUT["package"])
        self.assertEqual(errors[(self.lab.grey, "label")], embeddings.NO_CUT["label"])
        for item in index["items"]:
            self.assertTrue(os.path.isfile(os.path.join(self.lab.entry_dir(), item["image"])))
        # The request holds the model and extra_body; each image is a PNG data URI.
        body = self.gateway.requests[0]
        self.assertEqual(body["model"], "fake-model")
        self.assertEqual(body["max_num_patches"], 256)
        self.assertTrue(body["input"][0].startswith("data:image/png;base64,"))

    def test_second_build_makes_nothing_again(self):
        self.build()
        sent = self.gateway.images()
        before = os.path.getmtime(os.path.join(self.lab.entry_dir(), "images",
                                               "%s_full.png" % self.lab.grey))
        counts, events = self.build()
        self.assertEqual(counts["built"], 0)
        self.assertEqual(counts["current"], 4)
        self.assertEqual(self.gateway.images(), sent)
        self.assertEqual(before, os.path.getmtime(os.path.join(
            self.lab.entry_dir(), "images", "%s_full.png" % self.lab.grey)))

    def test_a_missing_image_makes_the_item_stale(self):
        self.build()
        os.remove(os.path.join(self.lab.entry_dir(), "images", "%s_full.png" % self.lab.grey))
        counts, _ = self.build()
        self.assertEqual(counts["built"], 1)

    def test_a_change_of_extra_body_makes_each_item_stale(self):
        self.build()
        self.lab.add_entry(extra_body={"max_num_patches": 512})
        counts, _ = self.build()
        self.assertEqual(counts["built"], 4)
        self.assertEqual(self.gateway.requests[-1]["max_num_patches"], 512)

    def test_a_stopped_build_continues_with_the_rest(self):
        stop = build_embeddings.Stop()

        def stop_after_first_batch(embedding):
            backend = quiet_backend(embedding)
            embed = backend.embed

            def once(images):
                stop.requested = True
                return embed(images)
            backend.embed = once
            return backend

        counts, events = self.build(stop=stop, make_backend=stop_after_first_batch)
        self.assertEqual(events[-1]["event"], "stopped")
        index, vectors = self.index()
        first = len(index["items"])
        self.assertGreater(first, 0)
        self.assertLess(first, 4)
        counts, events = self.build()
        self.assertEqual(events[-1]["event"], "done")
        self.assertEqual(counts["current"], first)
        index, vectors = self.index()
        self.assertEqual(len(index["items"]), 4)
        self.assertEqual(vectors.shape, (4, 8))

    def test_a_failed_batch_is_tried_again_by_the_next_build(self):
        self.gateway.status = 503
        counts, _ = self.build()
        self.assertEqual(counts["built"], 0)
        index, _ = self.index()
        self.assertIn("HTTP 503", index["failures"][0]["error"])
        self.gateway.status = 200
        counts, _ = self.build()
        self.assertEqual(counts["built"], 4)

    def test_a_client_error_is_not_tried_again(self):
        self.gateway.status = 400
        backend = build_embeddings.OpenAIBackend(
            embeddings.load_settings(self.lab.config_path).find("gw"), waits=(0, 0, 0))
        with self.assertRaises(build_embeddings.BackendError):
            backend.embed([b"x"])
        self.assertEqual(len(self.gateway.requests), 1)

    def test_an_item_that_is_no_input_is_removed(self):
        self.build()
        self.lab.conn.execute("UPDATE wine_catalog SET state = 'Disabled' WHERE wine_slug = 'grey'")
        self.lab.conn.commit()
        counts, _ = self.build()
        self.assertEqual(counts["pruned"], 1)  # the vector of the full item
        index, vectors = self.index()
        self.assertNotIn(self.lab.grey, {item["source_sha256"] for item in index["items"]})
        self.assertEqual(vectors.shape, (3, 8))
        self.assertFalse(os.path.exists(os.path.join(self.lab.entry_dir(), "images",
                                                     "%s_full.png" % self.lab.grey)))

    def test_a_shared_file_is_one_item(self):
        self.build()
        index, _ = self.index()
        keys = [(item["source_sha256"], item["view"]) for item in index["items"]]
        self.assertEqual(keys.count((self.lab.transparent, "full")), 1)

    def test_progress_lines(self):
        _, events = self.build()
        progress = [event for event in events if event["event"] == "progress"]
        self.assertEqual(progress[-1]["done"], progress[-1]["todo"])
        self.assertTrue(all("t" in event and "time" in event for event in events))
        failed = [event for event in events if event["event"] == "item_failed"]
        self.assertEqual(len(failed), 5)

    def test_a_request_line_comes_before_each_model_request(self):
        _, events = self.build()
        names = [event["event"] for event in events]
        requests = [event for event in events if event["event"] == "request"]
        self.assertEqual(len(requests), len(self.gateway.requests))
        self.assertEqual(sum(event["images"] for event in requests), 4)
        self.assertLess(names.index("request"), names.index("progress"))

    def test_each_retry_writes_a_retry_line(self):
        self.gateway.status = 503
        make = lambda embedding: build_embeddings.OpenAIBackend(embedding, waits=(0, 0),
                                                                timeout=10)
        _, events = self.build(make_backend=make)
        requests = [event for event in events if event["event"] == "request"]
        retries = [event for event in events if event["event"] == "retry"]
        # Each request is tried 3 times: 2 retry lines for each request.
        self.assertEqual([(event["attempt"], event["wait"]) for event in retries],
                         [(1, 0), (2, 0)] * len(requests))
        self.assertIn("HTTP 503", retries[0]["error"])


class LockTest(unittest.TestCase):
    def test_a_live_build_holds_the_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            # A process whose command line names the build script.
            process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)",
                                        embeddings.BUILD_SCRIPT_NAME])
            try:
                with open(os.path.join(directory, embeddings.LOCK), "w") as fh:
                    json.dump({"pid": process.pid}, fh)
                with self.assertRaises(embeddings.Busy):
                    embeddings.acquire_lock(directory)
                self.assertEqual(embeddings.running_pid(directory), process.pid)
            finally:
                process.kill()
                process.wait()
            embeddings.acquire_lock(directory)
            self.assertEqual(embeddings.read_lock(directory)["pid"], os.getpid())
            embeddings.release_lock(directory)
            self.assertFalse(os.path.exists(os.path.join(directory, embeddings.LOCK)))

    def test_a_lock_of_another_program_is_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            with open(os.path.join(directory, embeddings.LOCK), "w") as fh:
                json.dump({"pid": os.getpid()}, fh)  # this test runner, not a build
            embeddings.acquire_lock(directory)
            embeddings.release_lock(directory)


class MainTest(unittest.TestCase):
    def test_an_unknown_name_is_a_configuration_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            gateway = FakeGateway()
            lab = standard_lab(tmp, gateway.base_url)
            try:
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = build_embeddings.main(["--config", lab.config_path, "--name", "none"])
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(out.getvalue())["event"], "error")
            finally:
                gateway.close()
                lab.close()


if __name__ == "__main__":
    unittest.main()
