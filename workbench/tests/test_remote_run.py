"""Tests of the remote pipeline (plans 31 and 34): the backend `svoe-vino-ru` of
`pipeline/pipelines.py`, `pipeline/remote_run.py`, the refusal of a build, and the model
inputs of a remote run on the Runs page."""
import contextlib
import http.server
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX  # noqa: E402
import build_embeddings  # noqa: E402
import embedding_routes  # noqa: E402
import embeddings  # noqa: E402
import import_testset as IT  # noqa: E402
import match_backends  # noqa: E402
import pipelines  # noqa: E402
import remote_run as RR  # noqa: E402
import run_routes  # noqa: E402

NAME = "vino-svoe-search-by-photo"
PHOTOS = {"wine-a/01.jpg": b"a1", "wine-b/01.jpg": b"b1", "wine-b/02.jpg": b"b2"}
LABELS = {"wine-a": {"01.jpg": {"label": "positive"}},
          "wine-b": {"01.jpg": {"label": "positive"}, "02.jpg": {"label": "negative"}}}


def remote_entry(**keys):
    return dict({"name": NAME, "backend": "svoe-vino-ru",
                 "url": "https://api.example.test/v1/wines/search-by-photo"}, **keys)


GW = {"name": "gw", "backend": "openai", "base_url": "http://x/v1", "model": "m",
      "views": {"full": {"steps": [{"step": "segment", "target": "package"}]}}}


def write_config(root, db, entries, models=()):
    path = Path(root) / "config.yaml"
    path.write_text(json.dumps({"rootdir": str(root), "database_file": db,
                                "embeddings": list(models), "pipeline": entries}),
                    encoding="utf-8")
    return str(path)


class RemoteEntryTest(unittest.TestCase):
    def test_a_remote_entry_takes_the_defaults_of_the_http_backend(self):
        entry = pipelines.Pipeline(remote_entry())
        self.assertEqual((entry.name, entry.backend), (NAME, "svoe-vino-ru"))
        self.assertEqual(entry.remote, {
            "url": "https://api.example.test/v1/wines/search-by-photo", "field": "image",
            "response": "auto", "query": {}, "top_k": 1, "timeout_s": 30, "workers": 1,
            "headers": {}})

    def test_the_request_keys_of_the_entry_win(self):
        entry = pipelines.Pipeline(remote_entry(top_k=10, query={"limit": 10}))
        self.assertEqual((entry.remote["top_k"], entry.remote["query"]), (10, {"limit": 10}))

    def test_a_device_entry_requires_and_binds_an_ipv4_address(self):
        entry = pipelines.Pipeline(remote_entry(
            url="http://{device_ip}:18088/v1/match", device_ip=True))
        self.assertTrue(entry.device_ip)
        self.assertEqual(pipelines.bind_device_ip(entry, "192.168.86.42"), "192.168.86.42")
        self.assertEqual(entry.remote["url"], "http://192.168.86.42:18088/v1/match")
        for value in (None, "phone.local", "::1", "224.0.0.1"):
            with self.subTest(value=value):
                fresh = pipelines.Pipeline(remote_entry(
                    url="http://{device_ip}:18088/v1/match", device_ip=True))
                with self.assertRaisesRegex(embeddings.ConfigError, "device_ip"):
                    pipelines.bind_device_ip(fresh, value)

    def test_a_device_entry_requires_a_matching_url_placeholder(self):
        wrong = [
            ({"device_ip": True}, "url MUST contain"),
            ({"url": "http://{device_ip}:18088/v1/match"}, "device_ip MUST be true"),
            ({"device_ip": "yes"}, "true or false"),
        ]
        for keys, message in wrong:
            with self.subTest(keys=keys):
                with self.assertRaisesRegex(embeddings.ConfigError, message):
                    pipelines.Pipeline(remote_entry(**keys))

    def test_a_remote_entry_refuses_views_and_the_keys_of_a_model(self):
        wrong = [
            ({"views": {"full": None}}, "takes no views"),
            ({"base_url": "http://x/v1"}, "takes no base_url"),
            ({"model": "m"}, "takes no model"),
            ({"batch_size": 4}, "takes no batch_size"),
            ({"url": "ftp://x"}, "url MUST"),
            ({"response": "xml"}, "response MUST"),
            ({"top_k": 0}, "top_k MUST"),
            ({"workers": True}, "workers MUST"),
            ({"timeout_s": 0}, "timeout_s MUST"),
            ({"query": ["limit"]}, "query MUST"),
            ({"headers": {"X-Key": {"a": 1}}}, "headers MUST"),
            ({"field": ""}, "field MUST"),
        ]
        for keys, message in wrong:
            with self.subTest(keys=keys):
                with self.assertRaisesRegex(embeddings.ConfigError, message):
                    pipelines.Pipeline(remote_entry(**keys))
        with self.assertRaisesRegex(embeddings.ConfigError, "url MUST"):
            pipelines.Pipeline({"name": NAME, "backend": "svoe-vino-ru"})

    def test_an_embedding_entry_refuses_the_backend(self):
        with self.assertRaisesRegex(embeddings.ConfigError, "the key `pipeline`"):
            embeddings.Embedding(remote_entry())

    def test_the_shapes_equal_the_shapes_of_match_backends(self):
        self.assertEqual(pipelines.REMOTE_SHAPES, match_backends.SHAPES)

    def test_the_project_config_holds_the_official_entry(self):
        entry, _ = RR.find_entry(NAME)
        self.assertEqual(entry.remote["url"],
                         "https://api.vino-svoe.ru/v1/wines/search-by-photo")
        self.assertEqual((entry.remote["top_k"], entry.remote["query"]), (10, {"limit": 10}))

    def test_the_project_config_holds_the_two_android_device_entries(self):
        for name, suffix, response, top_k in (
                ("android-device-eval-predict", "/v1/eval/predict", "slug-object", 1),
                ("android-device-match-k20", "/v1/match", "candidates", 20)):
            with self.subTest(name=name):
                entry, _ = RR.find_entry(name)
                self.assertTrue(entry.device_ip)
                self.assertEqual(entry.remote["url"], "http://{device_ip}:18088" + suffix)
                self.assertEqual((entry.remote["response"], entry.remote["top_k"]),
                                 (response, top_k))


class RefusalTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.config = write_config(self.root, "lab.sqlite3", [
            remote_entry(), {"name": "emb", "backend": "embedding", "embedding": "gw"}], [GW])

    def tearDown(self):
        self.directory.cleanup()

    def test_the_build_route_does_not_know_a_pipeline(self):
        code, body, _, _ = embedding_routes.start(embeddings.load_settings(self.config), NAME)
        self.assertEqual(code, 404)
        self.assertIn("no embedding %s" % NAME, body["error"])

    def test_the_build_script_does_not_know_a_pipeline(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = build_embeddings.main(["--config", self.config, "--name", NAME])
        self.assertEqual(code, 2)
        self.assertIn("no embedding %s" % NAME, out.getvalue())
        db_path = embeddings.load_settings(self.config).db_path
        self.assertFalse(Path(embeddings.entry_dir(db_path, NAME)).exists())

    def test_find_entry_refuses_another_backend_and_an_unknown_name(self):
        with self.assertRaisesRegex(embeddings.ConfigError, "backend embedding"):
            RR.find_entry("emb", self.config)
        with self.assertRaisesRegex(embeddings.ConfigError, "no pipeline other"):
            RR.find_entry("other", self.config)


class Matcher(http.server.BaseHTTPRequestHandler):
    """A matcher that answers a bare ranked list with no score, as the official API."""

    requests = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        Matcher.requests.append((self.path, body))
        answer = json.dumps([{"slug": "wine-b"}, {"slug": "wine-a"}, {"slug": "wine-c"}])
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(answer.encode())

    def log_message(self, *args):
        pass


class RemoteRunTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(self.root)
        IT.import_testset(self.db, "my", FX.write_set(self.root, PHOTOS, LABELS),
                          lambda m: None, self.schema)
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Matcher)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        Matcher.requests = []
        url = "http://127.0.0.1:%d/v1/wines/search-by-photo" % self.server.server_port
        self.config = write_config(self.root, self.db, [
            remote_entry(url=url, query={"limit": 10}, top_k=2, workers=2)])
        self.runs = self.root / "runs"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def run_main(self, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = RR.main(["--name", NAME, "--set", "my", "--config", self.config,
                            "--runs-dir", str(self.runs), *extra])
        return code, out.getvalue()

    def only_run(self):
        (run_dir,) = self.runs.iterdir()
        return run_dir

    def test_a_run_sends_each_photo_as_it_is_and_records_the_configuration(self):
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        self.assertEqual(len(Matcher.requests), 3)
        bodies = [body for _, body in Matcher.requests]
        self.assertTrue(all(b'name="image"' in body for body in bodies))
        for data in PHOTOS.values():
            # The bytes of the photo, unchanged, between the part head and the boundary.
            self.assertEqual(sum(b"\r\n\r\n" + data + b"\r\n--" in body for body in bodies), 1)
        self.assertTrue(all(path == "/v1/wines/search-by-photo?limit=10"
                            for path, _ in Matcher.requests))
        run_dir = self.only_run()
        self.assertTrue(run_dir.name.endswith("-lab-%s-my" % NAME))
        meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["configuration"], NAME)
        self.assertEqual((meta["backend"]["id"], meta["backend"]["kind"]), (NAME, "remote"))
        self.assertEqual(meta["options"]["workers"], 2)
        self.assertIsNone(meta["embeddings"]["built_at"])
        rows = [json.loads(line) for line in
                (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([[c["slug"] for c in row["candidates"]] for row in rows],
                         [["wine-b", "wine-a"]] * 3)
        self.assertEqual({row["http_status"] for row in rows}, {201})
        by_path = {row["image_path"]: row for row in rows}
        self.assertEqual(by_path["wine-a/01.jpg"]["rank_of_truth"], 2)
        self.assertEqual(by_path["wine-b/01.jpg"]["rank_of_truth"], 1)
        self.assertIn("run: %s" % run_dir, out)

    def test_workers_and_limit_of_the_command_line_win(self):
        code, out = self.run_main("--workers", "1", "--limit", "1", "--label", "probe")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(Matcher.requests), 1)
        run_dir = self.only_run()
        self.assertTrue(run_dir.name.endswith("-my-probe"))
        meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual((meta["options"]["workers"], meta["options"]["limit"]), (1, 1))

    def test_an_empty_header_variable_stops_the_run(self):
        os.environ.pop("SVL_TEST_EMPTY_VARIABLE", None)
        self.config = write_config(self.root, self.db, [remote_entry(
            headers={"Authorization": "env:SVL_TEST_EMPTY_VARIABLE"})])
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, _ = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("SVL_TEST_EMPTY_VARIABLE", err.getvalue())
        self.assertFalse(self.runs.exists())

    def test_the_runs_page_answers_a_note_for_the_model_inputs(self):
        self.assertEqual(self.run_main()[0], 0)
        run_id = self.only_run().name
        code, body, _, _ = run_routes.inputs_view(
            str(self.runs), self.db, {"id": [run_id], "query": ["q-000001"]})
        self.assertEqual(code, 200)
        self.assertEqual(body["inputs"], [])
        self.assertIn("remote matcher", body["notes"][0])


if __name__ == "__main__":
    unittest.main()
