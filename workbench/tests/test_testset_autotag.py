"""The resumable four-category Autotag batch of the Testset page."""
import hashlib
import io
import json
import os
import sqlite3
import sys
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "pipeline"))
import testset_fixture as FX  # noqa: E402
import describe_images  # noqa: E402
import image_tags  # noqa: E402
import import_testset as IT  # noqa: E402
import testset_autotag as AUTOTAG  # noqa: E402
import vlm_config  # noqa: E402


def jpeg(colour):
    output = io.BytesIO()
    Image.new("RGB", (20, 40), colour).save(output, "JPEG")
    return output.getvalue()


RED = jpeg("red")
GREEN = jpeg("green")
BLUE = jpeg("blue")
PHOTOS = {"wine-a/01.jpg": RED, "wine-a/02.jpg": GREEN,
          "wine-b/01.jpg": RED, "wine-b/02.jpg": BLUE}


class AutotagBatchTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(self.root)
        IT.import_testset(self.db, "my", FX.write_set(self.root, PHOTOS, {}),
                          lambda message: None, self.schema)
        self.status = self.root / "autotag.status.json"
        self.entry = vlm_config.Entry(
            "fake-vlm", "openai", "chat_template_kwargs",
            "http://vlm.invalid/v1", "fake-model", "", 100)
        self.by_digest = {
            hashlib.sha256(RED).hexdigest(): "isolated_product",
            hashlib.sha256(GREEN).hexdigest(): "scene_photo",
            hashlib.sha256(BLUE).hexdigest(): "label_back",
        }

    def tearDown(self):
        self.directory.cleanup()

    def connection(self):
        conn = sqlite3.connect(self.db)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def tags(self):
        with closing(self.connection()) as conn:
            return image_tags.tags(conn)

    def classifier(self, _entry, path, max_side):
        self.assertEqual(max_side, 512)
        digest = Path(path).stem
        return self.by_digest[digest], "served-model", 25.4, False

    def test_pending_is_distinct_and_skips_an_existing_category(self):
        green = hashlib.sha256(GREEN).hexdigest()
        with closing(self.connection()) as conn:
            with conn:
                image_tags.add(conn, green, "manual-note")
                rows = AUTOTAG.pending(conn, "my")
                self.assertEqual(len(rows), 3)  # RED occurs twice but is one image.
                self.assertEqual(next(row for row in rows if row["sha256"] ==
                                      hashlib.sha256(RED).hexdigest())["occurrences"], 2)
                image_tags.add(conn, green, "scene_photo")
            self.assertNotIn(green, {row["sha256"] for row in AUTOTAG.pending(conn, "my")})

    def test_the_batch_adds_one_category_and_preserves_other_tags(self):
        green = hashlib.sha256(GREEN).hexdigest()
        with closing(self.connection()) as conn:
            with conn:
                image_tags.add(conn, green, "manual-note")
        status = AUTOTAG.run_batch(
            self.db, "my", self.entry, 512, 2, status_path=str(self.status),
            classifier=self.classifier)
        self.assertEqual((status["state"], status["total"], status["done"],
                          status["tagged"], status["errors"]),
                         ("done", 3, 3, 3, 0))
        tags = self.tags()
        self.assertEqual(tags[green], ["manual-note", "scene_photo"])
        self.assertEqual(tags[hashlib.sha256(RED).hexdigest()], ["isolated_product"])
        self.assertEqual(tags[hashlib.sha256(BLUE).hexdigest()], ["label_back"])
        self.assertEqual(AUTOTAG.read_status(str(self.status))["counts"], {
            "label_back": 1, "label_front": 0,
            "isolated_product": 1, "scene_photo": 1})

        again = AUTOTAG.run_batch(
            self.db, "my", self.entry, 512, 2, status_path=str(self.status),
            classifier=lambda *_: self.fail("a completed image was classified again"))
        self.assertEqual((again["state"], again["total"], again["tagged"]),
                         ("done", 0, 0))

    def test_a_per_image_error_is_retryable(self):
        blue = hashlib.sha256(BLUE).hexdigest()

        def first(_entry, path, _max_side):
            if Path(path).stem == blue:
                raise describe_images.DescribeError("bad image answer")
            return "label_front", "served-model", 10, True

        status = AUTOTAG.run_batch(
            self.db, "my", self.entry, 512, 1, status_path=str(self.status), classifier=first)
        self.assertEqual((status["state"], status["errors"], status["cached"]),
                         ("done", 1, 2))
        with closing(self.connection()) as conn:
            self.assertEqual([row["sha256"] for row in AUTOTAG.pending(conn, "my")], [blue])

        retry = AUTOTAG.run_batch(
            self.db, "my", self.entry, 512, 1, status_path=str(self.status),
            classifier=lambda *_: ("label_back", "served-model", 12, False))
        self.assertEqual((retry["total"], retry["tagged"], retry["errors"]), (1, 1, 0))

    def test_a_service_failure_waits_and_retries_without_losing_progress(self):
        attempts = {}
        sleeps = []
        waiting = []

        def intermittent(_entry, path, _max_side):
            digest = Path(path).stem
            attempts[digest] = attempts.get(digest, 0) + 1
            if attempts[digest] == 1:
                raise describe_images.DescribeError("HTTP 429: busy", counted=False)
            return self.by_digest[digest], "served-model", 10, False

        def sleep(seconds):
            sleeps.append(seconds)
            waiting.append(AUTOTAG.read_status(str(self.status)))

        status = AUTOTAG.run_batch(
            self.db, "my", self.entry, 512, 1, status_path=str(self.status),
            classifier=intermittent, sleeper=sleep,
            backoff_seconds=3, backoff_max_seconds=12)
        self.assertEqual((status["state"], status["done"], status["tagged"],
                          status["errors"], status["retries"], status["waits"]),
                         ("done", 3, 3, 0, 3, 3))
        self.assertEqual([round(seconds) for seconds in sleeps], [3, 3, 3])
        self.assertEqual([item["state"] for item in waiting], ["waiting"] * 3)
        self.assertTrue(all(item["done"] in (0, 1, 2) for item in waiting))
        self.assertTrue(all(item["backoff_seconds"] == 3 for item in waiting))
        self.assertTrue(all(item["retry_at"] for item in waiting))
        self.assertEqual(set(self.tags()), set(self.by_digest))

    def test_repeated_service_failures_use_exponential_backoff(self):
        attempts = 0
        sleeps = []

        def intermittent(*_args):
            nonlocal attempts
            attempts += 1
            if attempts <= 3:
                raise describe_images.DescribeError("VLM is down", counted=False)
            return "label_front", "served-model", 10, False

        status = AUTOTAG.run_batch(
            self.db, "my", self.entry, 512, 1, status_path=str(self.status),
            classifier=intermittent, sleeper=sleeps.append,
            backoff_seconds=2, backoff_max_seconds=4)
        self.assertEqual([round(seconds) for seconds in sleeps[:3]], [2, 4, 4])
        self.assertEqual((status["state"], status["done"], status["errors"],
                          status["retries"]), ("done", 3, 0, 3))

    def test_an_in_flight_success_is_committed_before_the_service_wait(self):
        red = hashlib.sha256(RED).hexdigest()
        green = hashlib.sha256(GREEN).hexdigest()
        failed = threading.Event()
        red_attempts = 0
        waits = []

        def concurrent(_entry, path, _max_side):
            nonlocal red_attempts
            digest = Path(path).stem
            if digest == red:
                red_attempts += 1
                if red_attempts == 1:
                    failed.set()
                    raise describe_images.DescribeError("HTTP 503: busy", counted=False)
            if digest == green:
                self.assertTrue(failed.wait(1))
            return self.by_digest[digest], "served-model", 10, False

        def sleep(seconds):
            waits.append(seconds)
            saved = AUTOTAG.read_status(str(self.status))
            self.assertEqual((saved["state"], saved["done"], saved["tagged"]),
                             ("waiting", 1, 1))
            self.assertEqual(self.tags()[green], ["scene_photo"])

        status = AUTOTAG.run_batch(
            self.db, "my", self.entry, 512, 2, status_path=str(self.status),
            classifier=concurrent, sleeper=sleep,
            backoff_seconds=2, backoff_max_seconds=4)
        self.assertEqual(len(waits), 1)
        self.assertEqual((status["state"], status["done"], status["tagged"],
                          status["errors"]), ("done", 3, 3, 0))

    def test_the_schema_accepts_only_the_four_exact_tags(self):
        for tag in AUTOTAG.TAGS:
            AUTOTAG.describe_images.parse_answer(json.dumps({"tag": tag}),
                                                  AUTOTAG.VALIDATOR)
        with self.assertRaises(describe_images.DescribeError):
            AUTOTAG.describe_images.parse_answer('{"tag":"front"}', AUTOTAG.VALIDATOR)


class AutotagStatusTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = str(Path(self.directory.name) / "status.json")

    def tearDown(self):
        self.directory.cleanup()

    def test_a_dead_running_job_is_reported_as_failed(self):
        AUTOTAG.write_status({"state": "running", "set": "my", "pid": 999999999,
                              "job_id": "j1"}, self.path)
        status = AUTOTAG.job_status(self.path)
        self.assertEqual((status["state"], status["set"]), ("failed", "my"))
        self.assertIn("without a final status", status["message"])

    def test_waiting_is_an_active_state_and_a_dead_wait_is_failed(self):
        AUTOTAG.write_status({"state": "waiting", "set": "my", "pid": 999999999,
                              "job_id": "j1"}, self.path)
        self.assertEqual(AUTOTAG.job_status(self.path)["state"], "failed")

        AUTOTAG.write_status({"state": "waiting", "set": "my", "pid": os.getpid(),
                              "job_id": "j2"}, self.path)
        self.assertEqual(AUTOTAG.job_status(self.path)["state"], "waiting")

    def test_a_finished_job_of_another_set_does_not_cover_this_set(self):
        AUTOTAG.write_status({"state": "done", "set": "other", "job_id": "j1"}, self.path)
        self.assertEqual(AUTOTAG.job_view("my", self.path)["state"], "idle")


if __name__ == "__main__":
    unittest.main()
