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
from unittest import mock
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
                          "url": "http://127.0.0.1:9/v1/match",
                          "query": {"k": 20}, "endpoint_override": True}]}),
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
        path = Path(labdb.image_dir(self.db, folder)) / ("%s.webp" % digest)
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

    def request(self, path, method="GET", body=None):
        data = (json.dumps({} if body is None else body).encode("utf-8")
                if method == "POST" else None)
        req = urllib.request.Request(self.base + path, method=method, data=data,
                                     headers={"Content-Type": "application/json"}
                                     if data is not None else {})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, response.headers, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            answer = exc.code, exc.headers, exc.read().decode("utf-8")
            exc.close()
            return answer

    def get_json(self, path):
        status, _, body = self.request(path)
        return status, json.loads(body)

    def test_the_runs_page_is_on(self):
        status, headers, body = self.request("/runs")
        self.assertEqual(status, 200)
        self.assertEqual(body, lab_pages.page("runs.html"))
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn('id="configuration"', body)
        self.assertIn("URL override", body)
        self.assertIn("r.endpoint_override_url", body)
        nav = re.search(r'<nav class="nav"[^>]*>(.*?)</nav>', body, re.S).group(1)
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
        self.assertEqual(data["configurations"][1]["endpoint"], "http://127.0.0.1:9")
        self.assertIsNone(data["config_error"])

    def test_run_charts_page_and_method_contract(self):
        status, headers, body = self.request("/runs/charts?set=my&mode=history&pipeline=mock")
        self.assertEqual(status, 200)
        self.assertEqual(body, lab_pages.page("run_charts.html"))
        self.assertIn("text/html", headers["Content-Type"])
        self.assertEqual(headers["Cache-Control"], "no-store")
        nav = re.search(r'<nav[^>]*>(.*?)</nav>', body, re.S).group(1)
        self.assertEqual(re.findall(r'href="([^"]*)"', nav), [href for href, _ in LAB.NAV])
        status, _, body = self.request("/runs/charts", method="HEAD")
        self.assertEqual((status, body), (200, ""))
        status, _, body = self.request("/runs/charts", method="POST")
        self.assertEqual(status, 405)
        self.assertIn("GET alone", json.loads(body)["error"])

    def test_api_runs_marks_only_a_changed_endpoint_origin(self):
        default = "2026-09-25T120000Z-lab-remote-my"
        override = "2026-09-25T130000Z-lab-remote-my"
        explicit = "2026-09-25T140000Z-lab-remote-my"
        self.write_run(default, {
            "configuration": "remote", "options": {"backend": "remote", "set": "my"},
            "backend": {"url": "http://127.0.0.1:9/v1/match", "query": {"k": 20}}
        }, [])
        self.write_run(override, {
            "configuration": "remote", "options": {"backend": "remote", "set": "my"},
            "backend": {"url": "https://matcher.example/v1/match", "query": {"k": 20}}
        }, [])
        self.write_run(explicit, {
            "configuration": "remote", "options": {"backend": "remote", "set": "my"},
            "endpoint_override": "http://127.0.0.1:9",
            "backend": {"url": "http://127.0.0.1:9/v1/match", "query": {"k": 20}}
        }, [])
        status, data = self.get_json("/api/runs")
        by_id = {run["id"]: run for run in data["runs"]}
        self.assertEqual(status, 200)
        self.assertIsNone(by_id[default]["endpoint_override_url"])
        self.assertEqual(by_id[override]["endpoint_override_url"],
                         "https://matcher.example/v1/match?k=20")
        self.assertEqual(by_id[explicit]["endpoint_override_url"],
                         "http://127.0.0.1:9/v1/match?k=20")

    def test_api_run_sends_the_photo_and_the_catalogue_images(self):
        status, data = self.get_json("/api/run?id=" + MOCK_RUN)
        self.assertEqual(status, 200)
        self.assertEqual([r["photo_url"] for r in data["rows"]], [self.photo, None])
        self.assertEqual([r["tags"] for r in data["rows"]], [[], []])
        self.assertEqual(data["tag_names"], [])
        # wine-b has a patch: the page shows it, with the mark `patched`.
        self.assertEqual(data["bottles"], {"wine-a": self.main_a, "wine-b": self.patch_b})
        self.assertEqual(data["patched"], ["wine-b"])
        self.assertEqual(data["run"]["configuration"], "mock")
        self.assertEqual(data["head"]["configuration"], "mock")
        self.assertIsNone(data["images_error"])

    def test_drawer_runs_are_listed_and_a_top_k_choice_moves_with_positive(self):
        run_id = "2026-10-03T120000Z-lab-mock-my-drawer"
        digest = hashlib.sha256(b"photo bytes").hexdigest()
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("INSERT INTO test_set (set_name, source_dir) VALUES ('my', 'test')")
            conn.execute("INSERT INTO test_photo (set_name, place, file_name, sha256) "
                         "VALUES ('my', '__drawer__', 'drawer.webp', ?)", (digest,))
        conn.close()
        row = {"query_id": "q-000001", "image_path": "__drawer__/drawer.webp",
               "image_sha256": digest, "slug": "__drawer__", "label": "unlabelled",
               "truth": [], "rank_of_truth": None, "outcome": "answered", "latency_ms": 5,
               "candidates": [{"slug": "wine-b", "rank": 1, "score": 0.9}]}
        self.write_run(run_id, {"configuration": "mock", "query_scope": "drawer",
                                "options": {"set": "my"}}, [row])
        status, data = self.get_json("/api/drawer-runs?set=my")
        self.assertEqual((status, [run["id"] for run in data["runs"]]), (200, [run_id]))
        status, _, raw = self.request("/api/drawer-match-accept", "POST", {
            "id": run_id, "query": "q-000001", "set": "my", "to": "wine-a"})
        self.assertEqual(status, 400, raw)
        self.assertIn("not a candidate", json.loads(raw)["error"])
        status, _, raw = self.request("/api/drawer-match-accept", "POST", {
            "id": run_id, "query": "q-000001", "set": "my", "to": "wine-b"})
        answer = json.loads(raw)
        self.assertEqual((status, answer["from"], answer["to"],
                          answer["photo"]["entry"]["label"]),
                         (200, "__drawer__", "wine-b", "positive"))
        conn = sqlite3.connect(self.db)
        try:
            saved = conn.execute("SELECT place, label FROM test_photo WHERE set_name = 'my'")\
                .fetchone()
        finally:
            conn.close()
        self.assertEqual(saved, ("wine-b", "positive"))

    def test_testset_page_has_drawer_matching_review_and_side_by_side_preview(self):
        status, _, body = self.request("/testset")
        self.assertEqual(status, 200)
        for fragment in ('id="drawer-match"', 'id="drawer-results"',
                         'id="drawer-preview-query"', 'id="drawer-preview-candidate"',
                         'Matched image and catalog image', 'drawer-query-preview',
                         'V · Move here and mark positive'):
            self.assertIn(fragment, body)

    def test_a_run_query_image_shows_and_accepts_shared_image_tags(self):
        route = "/api/run-image-tag"
        status, _, raw = self.request(route, "POST", {
            "id": MOCK_RUN, "query": "q-1", "tag": " Blurry ",
        })
        answer = json.loads(raw)
        digest = hashlib.sha256(b"photo bytes").hexdigest()
        self.assertEqual((status, answer["sha256"], answer["added"], answer["tags"]),
                         (200, digest, "blurry", ["blurry"]))
        self.assertEqual(answer["tag_names"], [{"tag": "blurry", "images": 1}])
        status, view = self.get_json("/api/run?id=" + MOCK_RUN)
        self.assertEqual((status, view["rows"][0]["tags"], view["tag_names"]),
                         (200, ["blurry"], [{"tag": "blurry", "images": 1}]))

        for body, code, text in (({"id": MOCK_RUN, "query": "q-1", "tag": "blurry"},
                                 409, "has the tag"),
                                 ({"id": MOCK_RUN, "query": "q-1", "tag": "two words"},
                                  400, "holds only"),
                                 ({"id": MOCK_RUN, "query": "q-2", "tag": "shelf"},
                                  404, "not in the lab image store"),
                                 ({"id": MOCK_RUN, "query": "missing", "tag": "shelf"},
                                  404, "unknown query")):
            with self.subTest(body=body):
                status, _, raw = self.request(route, "POST", body)
                self.assertEqual(status, code, raw)
                self.assertIn(text, json.loads(raw)["error"])
        self.assertEqual(self.request(route)[0], 405)

    def test_removing_a_run_image_tag_updates_shared_copies_and_preserves_other_tags(self):
        original = {path: path.read_bytes() for path in self.runs.rglob("*") if path.is_file()}
        for tag in ("blurry", "label_front"):
            self.assertEqual(self.request("/api/run-image-tag", "POST", {
                "id": MOCK_RUN, "query": "q-1", "tag": tag,
            })[0], 200)
        unrelated = hashlib.sha256(b"a main").hexdigest()
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO image_tag (sha256, tag, created_at) VALUES (?, ?, ?)",
                         (unrelated, "blurry", "2026-09-25T10:00:00Z"))

        route = "/api/run-image-tag-remove"
        body = {"id": MOCK_RUN, "query": "q-1", "tag": " Blurry ", "sha256": unrelated}
        # The recorded query selects the image. A supplied digest cannot redirect removal.
        for _ in range(2):
            status, _, raw = self.request(route, "POST", body)
            answer = json.loads(raw)
            self.assertEqual((status, answer["removed"], answer["tags"]),
                             (200, "blurry", ["label_front"]))
            self.assertEqual(answer["sha256"], hashlib.sha256(b"photo bytes").hexdigest())
        for run in (MOCK_RUN, OLD_RUN):
            self.assertEqual(self.get_json("/api/run?id=" + run)[1]["rows"][0]["tags"],
                             ["label_front"])
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT tag FROM image_tag WHERE sha256 = ?",
                                          (unrelated,)).fetchall(), [("blurry",)])
        # GET may create a derived page cache. Every original run file stays identical.
        self.assertEqual({path: path.read_bytes() for path in original}, original)

    def test_run_image_tag_removal_checks_the_query_and_tag(self):
        route = "/api/run-image-tag-remove"
        for body, code in (({}, 404), ([], 400), ("not an object", 400),
                           ({"id": "unknown", "query": "q-1", "tag": "blurry"}, 404),
                           ({"id": MOCK_RUN, "tag": "blurry"}, 400),
                           ({"id": MOCK_RUN, "query": "missing", "tag": "blurry"}, 404),
                           ({"id": MOCK_RUN, "query": "q-2", "tag": "blurry"}, 404),
                           ({"id": MOCK_RUN, "query": "q-1", "tag": "two words"}, 400)):
            with self.subTest(body=body):
                self.assertEqual(self.request(route, "POST", body)[0], code)
        self.assertEqual(self.request(route)[0], 405)

    def test_the_test_photo_folder_is_served(self):
        status, headers, _ = self.request(self.photo)
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "image/webp")

    def test_wine_merge_preview_and_write_transfer_a_manual_wine(self):
        source = "__manual-wine"
        digest = hashlib.sha256(b"photo bytes").hexdigest()
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO wine_catalog (wine_slug,name,producer,category,color,"
                         "region,csv_photo_name) VALUES (?, 'Manual', 'p','c','co','r','x.jpg')",
                         (source,))
            conn.execute("INSERT INTO test_set (set_name,source_dir) VALUES ('my','my')")
            conn.execute("INSERT INTO test_photo (set_name,place,file_name,sha256,label) "
                         "VALUES ('my',?,'01.jpg',?,'positive')", (source, digest))
        original = {path: path.read_bytes() for path in self.runs.rglob("*") if path.is_file()}
        config = json.loads(self.config.read_text(encoding="utf-8"))
        config["new_wine_embedding"] = "gw"
        self.config.write_text(json.dumps(config), encoding="utf-8")
        cached_dataset = self.get_json("/api/dataset")[1]
        self.assertIn(source, [wine["slug"] for wine in cached_dataset["records"]])
        before = self.get_json("/api/testset?set=my")[1]
        self.assertEqual(next(row for row in before["rows"] if row["slug"] == source)
                         ["photos"][0]["entry"]["label"], "positive")
        status, data = self.get_json("/api/wine-merge?slug=" + source)
        self.assertEqual((status, data["source"]["wine_slug"], data["photos"]), (200, source, 1))
        self.assertEqual({wine["slug"] for wine in data["targets"]}, {"wine-a", "wine-b"})
        with mock.patch.object(self.server.new_wine_jobs, "get", return_value={"state": "indexing"}):
            self.assertEqual(self.request("/api/wine-merge", "POST",
                                          {"slug": source, "to": "wine-a"})[0], 409)
        status, _, raw = self.request("/api/wine-merge", "POST", {"slug": source, "to": "wine-a"})
        result = json.loads(raw)
        self.assertEqual((status, result["from"], result["to"], result["removed"]),
                         (200, source, "wine-a", True))
        with sqlite3.connect(self.db) as conn:
            self.assertIsNone(conn.execute("SELECT 1 FROM wine_catalog WHERE wine_slug = ?",
                                           (source,)).fetchone())
            self.assertEqual(conn.execute("SELECT place,label FROM test_photo").fetchone(),
                             ("wine-a", "positive"))
        self.assertEqual(self.get_json("/api/wine-merge?slug=" + source)[0], 404)
        after = self.get_json("/api/testset?set=my")[1]
        self.assertNotIn(source, [row["slug"] for row in after["rows"]])
        self.assertEqual(next(row for row in after["rows"] if row["slug"] == "wine-a")
                         ["photos"][0]["entry"]["label"], "positive")
        self.assertNotIn(source, [wine["slug"] for wine in
                                  self.get_json("/api/dataset")[1]["records"]])
        self.assertEqual({path: path.read_bytes() for path in original}, original)

    def test_wine_merge_rejects_invalid_requests(self):
        self.assertEqual(self.get_json("/api/wine-merge")[0], 400)
        self.assertEqual(self.get_json("/api/wine-merge?slug=__null__")[0], 400)
        self.assertEqual(self.get_json("/api/wine-merge?slug=__missing")[0], 404)
        for body in ({}, [], {"slug": "wine-a", "to": "wine-b"},
                     {"slug": "__drawer__", "to": "wine-a"}):
            self.assertEqual(self.request("/api/wine-merge", "POST", body)[0], 400)
        self.assertEqual(self.request("/api/wine-merge", "DELETE")[0], 405)

    def test_api_run_checks_its_parameters(self):
        self.assertEqual(self.get_json("/api/run?id=..")[0], 400)
        self.assertEqual(self.get_json("/api/run?id=2026-01-01-none")[0], 404)
        self.assertEqual(self.get_json("/api/run?id=%s&sort=x" % MOCK_RUN)[0], 400)
        self.assertEqual(self.get_json("/api/run?id=%s&limit=x" % MOCK_RUN)[0], 400)
        status, data = self.get_json("/api/run?id=%s&filter=hit" % MOCK_RUN)
        self.assertEqual((status, data["total"]), (200, 0))

    def test_predictions_export_is_complete_stable_and_keeps_saved_values(self):
        # More than the row endpoint limit. Page filters MUST NOT reduce this export.
        rows = [{"query_id": "q-%06d" % i, "image_path": "Вино/%04d.webp" % i,
                 "image_sha256": "%064x" % i, "predicted_slug": None if i == 1 else "wine-a",
                 "latency_ms": i, "extra": "not part of the prediction format"}
                for i in range(1002, 0, -1)]
        path = self.runs / MOCK_RUN / "predictions.jsonl"
        original = "".join(json.dumps(row) + "\n" for row in rows)
        path.write_text(original, encoding="utf-8")
        url = "/api/run-predictions?id=%s&filter=hit&sort=worst&q=absent&limit=1" % MOCK_RUN
        status, headers, body = self.request(url)
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/x-ndjson; charset=utf-8")
        self.assertEqual(headers["Cache-Control"], "no-store")
        exported = [json.loads(line) for line in body.splitlines()]
        self.assertEqual(len(exported), 1002)
        self.assertEqual(exported[0], {"query_id": "q-000001", "image_path": "Вино/0001.webp",
                                      "image_sha256": "%064x" % 1,
                                      "predicted_slug": None, "latency_ms": 1})
        self.assertEqual(exported[-1]["query_id"], "q-001002")
        self.assertEqual(body, "".join(json.dumps(row, ensure_ascii=False,
                                                separators=(",", ":")) + "\n"
                                       for row in exported))
        self.assertEqual(self.request(url)[2], body)
        self.assertEqual(path.read_text(encoding="utf-8"), original)
        status, headers, body_head = self.request(url, "HEAD")
        self.assertEqual((status, body_head), (200, ""))
        self.assertEqual(int(headers["Content-Length"]), len(body.encode("utf-8")))

    def test_official_predictions_use_photo_numbers_including_gaps(self):
        meta_path = self.runs / MOCK_RUN / "run.json"
        meta_path.write_text(json.dumps({"options": {"set": "official-test-2026-10-01"}}))
        rows = [{"query_id": "q-000001", "image_path": "wine-b/077.webp",
                 "image_sha256": "7" * 64, "predicted_slug": "wine-b", "latency_ms": 12},
                {"query_id": "q-000002", "image_path": "__null__/001.webp",
                 "image_sha256": "1" * 64, "predicted_slug": None, "latency_ms": 0}]
        path = self.runs / MOCK_RUN / "predictions.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        status, _, body = self.request("/api/run-predictions?id=" + MOCK_RUN)
        self.assertEqual(status, 200)
        self.assertEqual([json.loads(line) for line in body.splitlines()], [
            dict(rows[1], query_id="q-000001", image_path="eval_photo_001.webp"),
            dict(rows[0], query_id="q-000077", image_path="eval_photo_077.webp")])

    def test_predictions_export_rejects_invalid_paths_and_missing_files(self):
        for run_id, code in (("", 400), ("..", 400), ("..%2Foutside", 400),
                             ("unknown", 404), (MOCK_RUN, 404)):
            with self.subTest(run_id=run_id):
                self.assertEqual(self.request("/api/run-predictions?id=" + run_id)[0], code)
        outside = self.root / "outside.jsonl"
        outside.write_text('sensitive file outside runs\n')
        (self.runs / MOCK_RUN / "predictions.jsonl").symlink_to(outside)
        status, _, body = self.request("/api/run-predictions?id=" + MOCK_RUN)
        self.assertEqual(status, 400)
        self.assertNotIn("sensitive", body)
        self.assertEqual(RR.respond(self.server, "POST", "/api/run-predictions?id=" + MOCK_RUN,
                                    LAB.card_images)[0], 405)

    def test_predictions_export_reports_incomplete_records_instead_of_silently_skipping(self):
        path = self.runs / MOCK_RUN / "predictions.jsonl"
        for content in ('{"query_id":', '{}\n', 'null\n'):
            with self.subTest(content=content):
                path.write_text(content)
                status, data = self.get_json("/api/run-predictions?id=" + MOCK_RUN)
                self.assertEqual(status, 409)
                self.assertIn("cannot export predictions.jsonl", data["error"])

    def test_official_predictions_reject_ambiguous_photo_names(self):
        (self.runs / MOCK_RUN / "run.json").write_text(json.dumps({
            "options": {"set": "official-test-2026-10-01"}}))
        row = {"query_id": "q-000001", "image_path": "wine-a/001.webp",
               "image_sha256": "1" * 64, "predicted_slug": "wine-a", "latency_ms": 4}
        for other_path in ("wine-b/001.webp", "wine-b/missing.webp", "wine-b/000.webp"):
            with self.subTest(path=other_path):
                (self.runs / MOCK_RUN / "predictions.jsonl").write_text(
                    json.dumps(row) + "\n" + json.dumps(dict(row, image_path=other_path)) + "\n")
                self.assertEqual(self.request("/api/run-predictions?id=" + MOCK_RUN)[0], 409)

    def test_expected_export_uses_truth_and_zero_latency(self):
        rows = [
            {"query_id": "q-000002", "image_path": "wine-a/02.webp",
             "image_sha256": "2" * 64, "truth": ["wine-a"], "label": "positive"},
            {"query_id": "q-000001", "image_path": "__null__/01.webp",
             "image_sha256": "1" * 64, "truth": [], "label": "no_match"},
            {"query_id": "q-000003", "image_path": "wine-b/03.webp",
             "image_sha256": "3" * 64, "truth": [], "label": "negative"},
        ]
        path = self.runs / MOCK_RUN / "queries.jsonl"
        original = "".join(json.dumps(row) + "\n" for row in rows)
        path.write_text(original, encoding="utf-8")
        url = "/api/run-expected?id=%s&filter=hit&sort=worst&q=absent&limit=1" % MOCK_RUN
        status, headers, body = self.request(url)
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/x-ndjson; charset=utf-8")
        exported = [json.loads(line) for line in body.splitlines()]
        self.assertEqual(exported, [
            {"query_id": "q-000001", "image_path": "__null__/01.webp",
             "image_sha256": "1" * 64, "predicted_slug": None, "latency_ms": 0},
            {"query_id": "q-000002", "image_path": "wine-a/02.webp",
             "image_sha256": "2" * 64, "predicted_slug": "wine-a", "latency_ms": 0},
            {"query_id": "q-000003", "image_path": "wine-b/03.webp",
             "image_sha256": "3" * 64, "predicted_slug": None, "latency_ms": 0},
        ])
        self.assertEqual(body, "".join(json.dumps(row, separators=(",", ":")) + "\n"
                                       for row in exported))
        self.assertEqual(self.request(url)[2], body)
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_official_expected_export_uses_photo_numbers(self):
        (self.runs / MOCK_RUN / "run.json").write_text(json.dumps({
            "options": {"set": "official-test-2026-10-01"}}))
        rows = [
            {"query_id": "q-000001", "image_path": "wine-b/077.webp",
             "image_sha256": "7" * 64, "truth": ["wine-b"]},
            {"query_id": "q-000002", "image_path": "__null__/001.webp",
             "image_sha256": "1" * 64, "truth": []},
        ]
        (self.runs / MOCK_RUN / "queries.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows))
        status, _, body = self.request("/api/run-expected?id=" + MOCK_RUN)
        self.assertEqual(status, 200)
        self.assertEqual([json.loads(line) for line in body.splitlines()], [
            {"query_id": "q-000001", "image_path": "eval_photo_001.webp",
             "image_sha256": "1" * 64, "predicted_slug": None, "latency_ms": 0},
            {"query_id": "q-000077", "image_path": "eval_photo_077.webp",
             "image_sha256": "7" * 64, "predicted_slug": "wine-b", "latency_ms": 0},
        ])

    def test_expected_export_of_more_accepted_slugs_uses_the_query_slug(self):
        rows = [
            {"query_id": "q-000001", "image_path": "wine-b/01.webp", "image_sha256": "1" * 64,
             "slug": "wine-b", "truth": ["wine-a", "wine-b"], "label": "positive"},
            {"query_id": "q-000002", "image_path": "wine-a/01.webp", "image_sha256": "1" * 64,
             "slug": "wine-a", "truth": ["wine-a", "wine-b"], "label": "positive"},
        ]
        (self.runs / MOCK_RUN / "queries.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows))
        status, _, body = self.request("/api/run-expected?id=" + MOCK_RUN)
        self.assertEqual(status, 200)
        self.assertEqual([json.loads(line)["predicted_slug"] for line in body.splitlines()],
                         ["wine-b", "wine-a"])

    def test_expected_export_rejects_missing_or_invalid_truth(self):
        path = self.runs / MOCK_RUN / "queries.jsonl"
        self.assertEqual(self.request("/api/run-expected?id=" + MOCK_RUN)[0], 404)
        base = {"query_id": "q-1", "image_path": "a.webp", "image_sha256": "1" * 64}
        for truth, slug in ((None, None), ("wine-a", None), (["wine-a", "wine-b"], None),
                            (["wine-a", "wine-b"], "wine-c"), ([""], None),
                            (["wine-a", ""], "wine-a")):
            with self.subTest(truth=truth, slug=slug):
                path.write_text(json.dumps(dict(base, truth=truth, slug=slug)) + "\n")
                status, data = self.get_json("/api/run-expected?id=" + MOCK_RUN)
                self.assertEqual(status, 409)
                self.assertIn("cannot export queries.jsonl", data["error"])
        self.assertEqual(RR.respond(self.server, "POST", "/api/run-expected?id=" + MOCK_RUN,
                                    LAB.card_images)[0], 405)

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
