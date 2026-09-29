"""Tests of plan 84: the background index jobs of the new wines and their routes."""
import json
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tests"))
import lab_server as LAB  # noqa: E402
import labdb  # noqa: E402
import new_wine_jobs  # noqa: E402
import new_wine_workflow  # noqa: E402
from test_manual_wines import form  # noqa: E402
from test_patches import WINES, FakeSam3  # noqa: E402

SELECTED = ("settings", "gw", "before")
ACTIVE = {"name": "gw", "state": "active", "items": 2}
FAILED = {"name": "gw", "state": "failed", "error": "model unavailable"}


class FakeUpdate:
    """A stand-in of `new_wine_workflow.update_index`. A call waits for `release`."""

    def __init__(self, result=ACTIVE, error=None):
        self.release = threading.Event()
        self.calls = []
        self.result = result
        self.error = error

    def __call__(self, selected, config_path, slug, **_options):
        self.calls.append((selected, config_path, slug))
        self.release.wait(5)
        if self.error:
            raise self.error
        return dict(self.result), None


def wait_for_end(read):
    """Call `read` until the job leaves the state `indexing`. Return the job."""
    for _ in range(500):
        job = read()
        if job and job["state"] != new_wine_jobs.INDEXING:
            return job
        time.sleep(0.01)
    raise AssertionError("the job did not end")


class IndexJobsTest(unittest.TestCase):
    def setUp(self):
        self.jobs = new_wine_jobs.IndexJobs(log=lambda message: None)

    def run_job(self, fake, slug="__w"):
        with mock.patch.object(new_wine_workflow, "update_index", fake):
            job = self.jobs.start(slug, SELECTED, "config.yaml")
            fake.release.set()
            return job, wait_for_end(lambda: self.jobs.get(slug))

    def test_a_job_goes_from_indexing_to_active(self):
        fake = FakeUpdate()
        with mock.patch.object(new_wine_workflow, "update_index", fake):
            job = self.jobs.start("__w", SELECTED, "config.yaml")
            self.assertEqual((job["name"], job["state"]), ("gw", "indexing"))
            self.assertEqual(self.jobs.states(), {"__w": {"state": "indexing", "error": None}})
            fake.release.set()
            done = wait_for_end(lambda: self.jobs.get("__w"))
        self.assertEqual((done["state"], done["items"]), ("active", 2))
        self.assertIsNone(done["error"])
        self.assertIsNotNone(done["finished_at"])
        self.assertEqual(fake.calls, [(SELECTED, "config.yaml", "__w")])

    def test_a_failed_update_gives_the_state_failed_and_the_error(self):
        _job, done = self.run_job(FakeUpdate(FAILED))
        self.assertEqual((done["state"], done["error"]), ("failed", "model unavailable"))
        self.assertEqual(self.jobs.states()["__w"],
                         {"state": "failed", "error": "model unavailable"})

    def test_an_exception_gives_the_state_failed(self):
        _job, done = self.run_job(FakeUpdate(error=KeyError("items")))
        self.assertEqual(done["state"], "failed")
        self.assertTrue(done["error"].startswith("internal error"), done)

    def test_a_second_start_during_indexing_starts_no_second_update(self):
        fake = FakeUpdate()
        with mock.patch.object(new_wine_workflow, "update_index", fake):
            first = self.jobs.start("__w", SELECTED, "config.yaml")
            second = self.jobs.start("__w", SELECTED, "config.yaml")
            fake.release.set()
            wait_for_end(lambda: self.jobs.get("__w"))
        self.assertEqual(second["started_at"], first["started_at"])
        self.assertEqual(len(fake.calls), 1)

    def test_a_start_after_a_failed_job_starts_a_new_job(self):
        fake = FakeUpdate(FAILED)
        self.run_job(fake)
        fake.result = ACTIVE
        job, done = self.run_job(fake)
        self.assertEqual(job["state"], "indexing")
        self.assertEqual(done["state"], "active")
        self.assertEqual(len(fake.calls), 2)


class WineIndexRouteTest(unittest.TestCase):
    """`POST /api/wine`, `GET /api/wine-index`, `POST /api/wine-index`, and the key
    `new_wine_index` of `GET /api/dataset` on a server with a configuration."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db = str(Path(self.directory.name) / "lab.sqlite3")
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.executemany("INSERT INTO wine_catalog (%s) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
                             % ", ".join(LAB.CATALOG_COLUMNS), WINES)
        conn.close()
        self.server = LAB.make_server(self.db, port=0, segmenter=FakeSam3(),
                                      config_path="/tmp/test-config.yaml")
        self.server.new_wine_jobs.log = lambda message: None
        self.fake = FakeUpdate()
        for name, value in (("preflight", ("settings", "gw", "directory", "before")),
                            ("embedding_name", "gw")):
            patcher = mock.patch.object(new_wine_workflow, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(new_wine_workflow, "update_index", self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.fake.release.set)
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def request(self, path, method="GET", body=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.base + path, method=method, data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def job(self, slug="__my-wine"):
        status, out = self.request("/api/wine-index?slug=" + slug)
        return out if status == 200 else None

    def test_post_answers_before_the_index_update_ends(self):
        status, out = self.request("/api/wine", "POST", form())
        self.assertEqual(status, 200, out)
        self.assertEqual((out["slug"], out["index"]["state"]), ("__my-wine", "indexing"))
        self.assertEqual(out["record"]["slug"], "__my-wine")
        self.assertEqual(self.job()["state"], "indexing")
        status, view = self.request("/api/dataset")
        self.assertEqual(status, 200, view)
        self.assertEqual(view["new_wine_index"],
                         {"__my-wine": {"state": "indexing", "error": None}})
        self.fake.release.set()
        self.assertEqual(wait_for_end(self.job)["state"], "active")
        self.assertEqual(self.fake.calls,
                         [(("settings", "gw", "before"), "/tmp/test-config.yaml",
                           "__my-wine")])

    def test_get_answers_404_for_a_slug_with_no_job(self):
        status, out = self.request("/api/wine-index?slug=__nothing")
        self.assertEqual(status, 404, out)

    def test_retry_starts_a_new_job_after_a_failed_job(self):
        self.fake.result = FAILED
        self.fake.release.set()
        self.request("/api/wine", "POST", form())
        self.assertEqual(wait_for_end(self.job)["error"], "model unavailable")
        self.fake.result = ACTIVE
        status, out = self.request("/api/wine-index", "POST", {"slug": "__my-wine"})
        self.assertEqual(status, 200, out)
        self.assertEqual(out["state"], "indexing")
        self.assertEqual(wait_for_end(self.job)["state"], "active")
        self.assertEqual(len(self.fake.calls), 2)

    def test_retry_refuses_an_unknown_wine_and_a_body_with_no_slug(self):
        status, out = self.request("/api/wine-index", "POST", {"slug": "__nothing"})
        self.assertEqual(status, 404, out)
        status, out = self.request("/api/wine-index", "POST", {"other": 1})
        self.assertEqual(status, 400, out)
        self.assertEqual(self.fake.calls, [])

    def test_a_server_with_no_config_starts_no_job(self):
        self.server.config_path = None
        status, out = self.request("/api/wine", "POST", form())
        self.assertEqual(status, 200, out)
        self.assertNotIn("index", out)
        self.assertIsNone(self.job())
        self.assertEqual(self.fake.calls, [])


if __name__ == "__main__":
    unittest.main()
