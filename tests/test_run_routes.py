"""Tests of the Runs page on the lab server (plan 23): `pipeline/run_routes.py` through
`pipeline/lab_server.py`."""
import hashlib
import json
import re
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(1, str(ROOT / "tests"))
import lab_pages  # noqa: E402
import lab_server as LAB  # noqa: E402
import labdb  # noqa: E402
import run_routes as RR  # noqa: E402
from embedding_lab import VIEWS_C_F  # noqa: E402

MOCK_RUN = "2026-09-25T110000Z-lab-mock-my"
OLD_RUN = "2026-09-25T100000Z-old"


class RunRoutesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.executemany(
                "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                "region, description, csv_photo_name) VALUES (?, ?, 'p', 'c', 'co', 'r', "
                "'d', 'x.webp')", [("wine-a", "Вино a"), ("wine-b", "Вино b")])
        conn.close()
        self.photo = self.store("testset", b"photo bytes")
        self.main_a = self.store("main", b"a main", slug="wine-a", image_type="main")
        self.store("main", b"b main", slug="wine-b", image_type="main")
        self.patch_b = self.store("patched", b"b patch", slug="wine-b",
                                  image_type="main_patched")
        self.runs = self.root / "runs"
        row = {"query_id": "q-1", "image_path": "wine-a/01.jpg",
               "image_sha256": hashlib.sha256(b"photo bytes").hexdigest(),
               "slug": "wine-a", "label": "positive", "truth": ["wine-a"],
               "rank_of_truth": 2, "outcome": "rank_2", "latency_ms": 40,
               "candidates": [{"slug": "wine-b", "rank": 1, "score": 0.9},
                              {"slug": "wine-a", "rank": 2, "score": 0.4}]}
        missing = dict(row, query_id="q-2", image_path="wine-a/02.jpg",
                       image_sha256="0" * 64)
        self.write_run(MOCK_RUN, {"configuration": "mock", "backend": {"id": "mock",
                                                                       "url": None},
                                  "options": {"set": "my"}},
                       [row, missing])
        self.write_run(OLD_RUN, {"options": {"backend": "svm-x"}}, [row])
        self.config = self.root / "config.yaml"
        self.config.write_text(json.dumps({
            "rootdir": str(self.root), "database_file": "lab.sqlite3",
            "embeddings": [{"name": "gw", "backend": "openai", "base_url": "http://x/v1",
                            "model": "m", "views": VIEWS_C_F}],
            "pipeline": [{"name": "bad", "backend": "none"},
                         {"name": "remote", "backend": "svoe-vino-ru",
                          "url": "http://127.0.0.1:9/v1/wines/search-by-photo"}]}),
            encoding="utf-8")
        self.server = LAB.make_server(self.db, port=0, config_path=str(self.config))
        self.server.runs_dir = str(self.runs)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def store(self, folder, data, slug=None, image_type=None):
        """Store `data` in the image store. Return its URL on the lab server."""
        digest = hashlib.sha256(data).hexdigest()
        path = self.root / "images" / folder / ("%s.webp" % digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("INSERT INTO image (sha256, folder, extension) VALUES (?, ?, 'webp')",
                         (digest, folder))
            if slug:
                conn.execute("INSERT INTO wine_image (wine_slug, image_type, sha256, "
                             "source_name, match_method) VALUES (?, ?, ?, 'x', 'manual')",
                             (slug, image_type, digest))
        conn.close()
        return "/images/%s/%s.webp" % (folder, digest)

    def write_run(self, run_id, meta, rows):
        directory = self.runs / run_id
        directory.mkdir(parents=True)
        (directory / "run.json").write_text(json.dumps(meta), encoding="utf-8")
        (directory / "metrics.json").write_text(json.dumps({"positive": {"n": len(rows)}}),
                                                encoding="utf-8")
        (directory / "results.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    def request(self, path, method="GET"):
        req = urllib.request.Request(self.base + path, method=method,
                                     data=b"{}" if method == "POST" else None)
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, response.headers, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers, exc.read().decode("utf-8")

    def get_json(self, path):
        status, _, body = self.request(path)
        return status, json.loads(body)

    def test_the_runs_page_is_on(self):
        status, headers, body = self.request("/runs")
        self.assertEqual(status, 200)
        self.assertEqual(body, lab_pages.page("runs.html"))
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn('id="configuration"', body)
        nav = re.search(r'<nav class="nav">(.*?)</nav>', body, re.S).group(1)
        self.assertEqual(re.findall(r'href="([^"]*)"', nav), [href for href, _ in LAB.NAV])
        self.assertNotIn("/runs", LAB.DISABLED_PAGES)

    def test_api_runs_sends_the_runs_and_the_configurations(self):
        status, data = self.get_json("/api/runs")
        self.assertEqual(status, 200)
        self.assertEqual([(r["id"], r["configuration"]) for r in data["runs"]],
                         [(MOCK_RUN, "mock"), (OLD_RUN, None)])
        # The test set of `options.set` (the filter `Testset`); an old run has none.
        self.assertEqual([r["set"] for r in data["runs"]], ["my", None])
        # The pipelines alone (plan 34): the embedding `gw` is not in the list.
        self.assertEqual([(c["name"], c["backend"]) for c in data["configurations"]],
                         [("bad", None), ("remote", "svoe-vino-ru")])
        self.assertIn("backend MUST be one of", data["configurations"][0]["error"])
        self.assertIsNone(data["config_error"])

    def test_api_run_sends_the_photo_and_the_catalogue_images(self):
        status, data = self.get_json("/api/run?id=" + MOCK_RUN)
        self.assertEqual(status, 200)
        self.assertEqual([r["photo_url"] for r in data["rows"]], [self.photo, None])
        # wine-b has a patch: the page shows it, with the mark `patched`.
        self.assertEqual(data["bottles"], {"wine-a": self.main_a, "wine-b": self.patch_b})
        self.assertEqual(data["patched"], ["wine-b"])
        self.assertEqual(data["run"]["configuration"], "mock")
        self.assertEqual(data["head"]["configuration"], "mock")
        self.assertIsNone(data["images_error"])

    def test_the_test_photo_folder_is_served(self):
        status, headers, _ = self.request(self.photo)
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "image/webp")

    def test_api_run_checks_its_parameters(self):
        self.assertEqual(self.get_json("/api/run?id=..")[0], 400)
        self.assertEqual(self.get_json("/api/run?id=2026-01-01-none")[0], 404)
        self.assertEqual(self.get_json("/api/run?id=%s&sort=x" % MOCK_RUN)[0], 400)
        self.assertEqual(self.get_json("/api/run?id=%s&limit=x" % MOCK_RUN)[0], 400)
        status, data = self.get_json("/api/run?id=%s&filter=hit" % MOCK_RUN)
        self.assertEqual((status, data["total"]), (200, 0))

    def test_a_run_without_a_backend_url_has_no_model_input(self):
        status, data = self.get_json("/api/run-inputs?id=%s&query=q-1" % MOCK_RUN)
        self.assertEqual((status, data["inputs"]), (200, []))
        self.assertIn("no model input", data["notes"][0])
        self.assertEqual(self.get_json("/api/run-inputs?id=%s&query=q-9" % MOCK_RUN)[0], 404)
        self.assertEqual(self.get_json("/api/run-inputs?id=none&query=q-1")[0], 404)

    def test_api_run_clusters_reads_the_clusters_of_the_run_embedding(self):
        # Plan 43: a pipeline run names its embedding in `backend.embedding`; a run of an
        # embedding configuration from before plan 34 names it in `backend.id`.
        pipe_run, old_run = "2026-09-25T120000Z-lab-pipe-my", "2026-09-25T090000Z-lab-gw-my"
        self.write_run(pipe_run, {"configuration": "pipe", "backend": {
            "kind": "embedding", "id": "pipe", "embedding": "gw"}}, [])
        self.write_run(old_run, {"configuration": "gw", "backend": {
            "kind": "embedding", "id": "gw"}}, [])
        self.assertEqual(self.get_json("/api/run-clusters?id=none")[0], 404)
        status, data = self.get_json("/api/run-clusters?id=%s" % MOCK_RUN)
        self.assertEqual((status, data["embedding"], data["clusters"]), (200, None, []))
        status, data = self.get_json("/api/run-clusters?id=%s" % pipe_run)
        self.assertEqual((status, data["embedding"], data["exists"]), (200, "gw", False))
        directory = self.root / "embeddings" / "gw"
        directory.mkdir(parents=True)
        key = "0123456789ab"
        cluster = {"id": "c001", "key": key, "kind": "mixed", "size": 2,
                   "signals": ["full", "label"], "slugs": ["wine-a", "wine-b"], "links": []}
        (directory / "clusters.json").write_text(json.dumps({
            "version": 1, "built_at": "2026-09-26T08:00:00+0300", "input_hash": "old",
            "spaces": {"full": {"clusters": []}, "label": {"clusters": []},
                       "combined": {"clusters": [cluster]}}}), encoding="utf-8")
        (directory / "cluster-rules.json").write_text(json.dumps({"version": 1, "spaces": {
            "label": {key: {"mode": "sheet", "questions": [{"id": "q1", "valid": True}],
                            "raw_reply": "x"}},
            "full": {key: {"mode": "verdict"}}}}), encoding="utf-8")
        for run_id in (pipe_run, old_run):
            status, data = self.get_json("/api/run-clusters?id=%s" % run_id)
            self.assertEqual((status, data["embedding"], data["space"], data["exists"]),
                             (200, "gw", "combined", True))
            self.assertEqual(data["clusters"], [{
                "id": "c001", "key": key, "kind": "mixed", "size": 2,
                "slugs": ["wine-a", "wine-b"],
                "rule": {"mode": "sheet", "questions": [{"id": "q1", "valid": True}]}}])
            self.assertEqual(data["cards"], {"wine-a": {"name": "Вино a"},
                                             "wine-b": {"name": "Вино b"}})
            self.assertIs(data["stale"], True)


if __name__ == "__main__":
    unittest.main()
