"""Tests of the Health page (docs/plans/46_health-page.md): the check of each kind of
endpoint against a fake llama-swap gateway and a fake cloud service, the status part,
and the routes of the lab server."""
import json
import os
import socket
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import health  # noqa: E402
import labdb  # noqa: E402

KEY = "sk-accepted-secret-1234"
WRONG_KEY = "sk-refused-secret-5678"


class Fake(BaseHTTPRequestHandler):
    """A fake llama-swap gateway (`gateway` True) or a fake cloud service. A subclass
    sets the class attributes; `calls` records each request."""
    gateway = True
    running = {}      # model -> the llama-swap state
    models = ()
    key = None        # the key that the service accepts; None: no key
    slow = ()         # the models whose real call takes 1.5 s
    crash = ()        # the models whose real call gets HTTP 502 with no body
    calls = None

    def log_message(self, *args):
        pass

    def _send(self, code, value):
        data = json.dumps(value).encode()
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass  # the client stopped waiting (the timeout test)

    def _refused(self):
        if self.key is None or self.headers.get("Authorization") == "Bearer " + self.key:
            return False
        # A real service can repeat the sent key in its error text.
        self._send(401, {"error": {"message": "Incorrect API key provided: %s"
                                              % self.headers.get("Authorization")}})
        return True

    def do_GET(self):
        self.calls.append(("GET", self.path))
        if self.gateway and self.path == "/running":
            return self._send(200, {"running": [{"model": model, "state": state, "ttl": 0}
                                                for model, state in self.running.items()]})
        if self.path == "/v1/models":
            if not self._refused():
                self._send(200, {"data": [{"id": model} for model in self.models]})
            return None
        if self.path == "/upstream/sam3/health":
            return self._send(200, {"status": "ok", "model": "facebook/sam3", "device": "cuda"})
        if self.path.startswith("/v1/wines?"):
            return self._send(200, {"totalItems": 2109, "items": []})
        return self._send(404, {"error": "Cannot GET %s" % self.path})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
        self.calls.append(("POST", self.path, body))
        if self._refused():
            return None
        if body.get("model") in self.slow:
            time.sleep(1.5)
        if body.get("model") in self.crash:
            # llama-swap answers so when the model process closes the connection.
            self.send_response(502)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        if self.path == "/v1/chat/completions":
            return self._send(200, {"model": body["model"], "choices": [{
                "message": {"role": "assistant", "content": "OK"}, "finish_reason": "length"}]})
        if self.path == "/v1/embeddings":
            return self._send(200, {"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}]})
        return self._send(404, {"error": "no route"})


def serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    # A short poll interval makes `shutdown` in tearDown fast.
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05},
                     daemon=True).start()
    return server, "http://127.0.0.1:%d" % server.server_address[1]


def closed_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


CONFIG = """
rootdir: {tmp}
database_file: lab.sqlite3
embedding_python: {tmp}/python
sam3:
  endpoint: {gw}/upstream/sam3
embeddings:
  - name: gw-emb-run
    backend: openai
    base_url: {gw}/v1
    model: emb-run
    extra_body: {{max_num_patches: 256}}
    views: &v {{full: {{steps: [{{step: segment, target: package}}]}}}}
  - name: gw-emb-idle
    backend: openai
    base_url: {gw}/v1
    model: emb-idle
    views: *v
  - name: local-emb
    backend: local
    model: google/test-model
    views: *v
vlm:
  - {{name: chat-run, protocol: openai, thinking_field: chat_template_kwargs,
      endpoint: "{gw}/v1", model: chat-run}}
  - {{name: chat-idle, protocol: openai, thinking_field: chat_template_kwargs,
      endpoint: "{gw}/v1", model: chat-idle}}
  - {{name: chat-starting, protocol: openai, thinking_field: chat_template_kwargs,
      endpoint: "{gw}/v1", model: chat-starting}}
  - {{name: chat-typo, protocol: openai, thinking_field: chat_template_kwargs,
      endpoint: "{gw}/v1", model: chat-rnu}}
  - {{name: chat-slow, protocol: openai, thinking_field: chat_template_kwargs,
      endpoint: "{gw}/v1", model: chat-slow}}
  - {{name: chat-crash, protocol: openai, thinking_field: chat_template_kwargs,
      endpoint: "{gw}/v1", model: chat-crash}}
  - {{name: cloud, protocol: openai, thinking_field: top_level,
      endpoint: "{cloud}/v1", model: cloud-model, key: "{{env:HEALTH_TEST_KEY}}"}}
  - {{name: cloud-unlisted, protocol: openai, thinking_field: top_level,
      endpoint: "{cloud}/v1", model: other-model, key: "{{env:HEALTH_TEST_KEY}}"}}
  - {{name: plain, protocol: openai, thinking_field: chat_template_kwargs,
      endpoint: "{plain}/v1", model: plain-model}}
  - {{name: dead, protocol: openai, thinking_field: chat_template_kwargs,
      endpoint: "http://127.0.0.1:{closed}/v1", model: dead-model}}
"""


class HealthTest(unittest.TestCase):
    def setUp(self):
        self.gateway_calls, self.cloud_calls, self.plain_calls = [], [], []
        self.Gateway = type("Gateway", (Fake,), {
            "calls": self.gateway_calls, "slow": ("chat-slow",), "crash": ("chat-crash",),
            "running": {"chat-run": "ready", "chat-slow": "ready", "chat-starting": "starting",
                        "chat-crash": "ready", "emb-run": "ready", "sam3": "ready"},
            "models": ("chat-run", "chat-idle", "chat-starting", "chat-slow", "chat-crash",
                       "emb-run", "emb-idle", "sam3")})
        cloud = type("Cloud", (Fake,), {"gateway": False, "key": KEY, "calls": self.cloud_calls,
                                        "models": ("cloud-model",)})
        plain = type("Plain", (Fake,), {"gateway": False, "calls": self.plain_calls,
                                        "models": ("plain-model",)})
        self.servers = []
        for handler in (self.Gateway, cloud, plain):
            server, base = serve(handler)
            self.servers.append((server, base))
        self.gw, self.cloud, self.plain = (base for _server, base in self.servers)
        self.directory = tempfile.TemporaryDirectory()
        self.tmp = Path(self.directory.name)
        self.config = str(self.tmp / "config.yaml")
        self.closed = closed_port()
        Path(self.config).write_text(CONFIG.format(
            tmp=self.tmp, gw=self.gw, cloud=self.cloud, plain=self.plain,
            closed=self.closed), encoding="utf-8")
        self.env = mock.patch.dict(os.environ, {"HEALTH_TEST_KEY": KEY})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        for server, _base in self.servers:
            server.shutdown()
            server.server_close()
        self.directory.cleanup()

    def check(self, kind, name):
        return health.check(self.config, kind, name)

    def posts(self, calls):
        return [call for call in calls if call[0] == "POST"]

    def test_a_vlm_that_runs_gets_one_real_call_of_one_token(self):
        row = self.check("vlm", "chat-run")
        self.assertEqual(row["status"], "ok", row)
        self.assertIn("answered in", row["summary"])
        self.assertIn('"OK"', row["summary"])
        (_method, path, body), = self.posts(self.gateway_calls)
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(body["max_tokens"], 1)
        self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
        self.assertTrue(any("finish_reason length" in line for line in row["details"]))

    def test_two_checks_never_send_the_same_prompt(self):
        # A byte-identical repeat is a full hit of the prompt cache of llama.cpp, and it
        # stopped the hybrid model qwen3.5-9b on 2026-09-26 (ggml_abort).
        self.check("vlm", "chat-run")
        self.check("vlm", "chat-run")
        prompts = [body["messages"][0]["content"] for _m, _p, body in self.posts(self.gateway_calls)]
        self.assertEqual(len(prompts), 2)
        self.assertNotEqual(prompts[0], prompts[1])
        self.assertTrue(all(prompt.endswith("Reply with OK.") for prompt in prompts))

    def test_a_502_of_the_gateway_says_that_the_model_process_stopped(self):
        row = self.check("vlm", "chat-crash")
        self.assertEqual(row["status"], "error", row)
        self.assertIn("the gateway got no answer from the model process (HTTP 502)",
                      row["summary"])
        self.assertIn(self.gw + "/logs/stream/upstream", row["summary"])
        self.assertTrue(row["summary"].endswith("(empty body)"), row["summary"])

    def test_a_vlm_that_does_not_run_gets_no_call(self):
        row = self.check("vlm", "chat-idle")
        self.assertEqual(row["status"], "idle", row)
        self.assertIn("does not run", row["summary"])
        self.assertEqual(self.posts(self.gateway_calls), [])

    def test_a_model_in_transition_gets_no_call(self):
        row = self.check("vlm", "chat-starting")
        self.assertEqual(row["status"], "warn", row)
        self.assertIn("starting", row["summary"])
        self.assertEqual(self.posts(self.gateway_calls), [])

    def test_an_unknown_model_names_the_close_models(self):
        row = self.check("vlm", "chat-typo")
        self.assertEqual(row["status"], "error", row)
        self.assertIn("has no model chat-rnu", row["summary"])
        self.assertIn("close names: chat-run", row["summary"])
        self.assertEqual(self.posts(self.gateway_calls), [])

    def test_a_closed_port_says_that_no_process_listens(self):
        row = self.check("vlm", "dead")
        self.assertEqual(row["status"], "error", row)
        self.assertIn("connection refused: no process listens on 127.0.0.1:", row["summary"])

    def test_a_server_with_no_running_route_gets_the_list_and_a_real_call(self):
        row = self.check("vlm", "plain")
        self.assertEqual(row["status"], "ok", row)
        self.assertEqual([call[:2] for call in self.plain_calls],
                         [("GET", "/running"), ("GET", "/v1/models"),
                          ("POST", "/v1/chat/completions")])
        self.assertTrue(any("not a llama-swap gateway" in line for line in row["details"]))

    def test_a_cloud_entry_without_its_variable_sends_nothing(self):
        with mock.patch.dict(os.environ, {"HEALTH_TEST_KEY": ""}):
            row = self.check("vlm", "cloud")
        self.assertEqual(row["status"], "error", row)
        self.assertIn("the variable HEALTH_TEST_KEY is not set", row["summary"])
        self.assertEqual(self.cloud_calls, [])

    def test_a_refused_key_names_the_variable_and_hides_the_key(self):
        with mock.patch.dict(os.environ, {"HEALTH_TEST_KEY": WRONG_KEY}):
            row = self.check("vlm", "cloud")
        self.assertEqual(row["status"], "error", row)
        self.assertIn("refused the key of the variable HEALTH_TEST_KEY (HTTP 401)",
                      row["summary"])
        self.assertIn("<redacted>", row["summary"])
        self.assertNotIn(WRONG_KEY, json.dumps(row))
        # No real call after a refused key, and no read of `/running` of a cloud service.
        self.assertEqual([call[:2] for call in self.cloud_calls], [("GET", "/v1/models")])

    def test_a_cloud_entry_with_an_accepted_key_gets_a_real_call(self):
        row = self.check("vlm", "cloud")
        self.assertEqual(row["status"], "ok", row)
        (_method, _path, body), = self.posts(self.cloud_calls)
        self.assertIs(body["enable_thinking"], False)
        self.assertNotIn("chat_template_kwargs", body)
        self.assertNotIn(KEY, json.dumps(row))

    def test_a_model_that_the_list_does_not_hold_is_a_warning(self):
        row = self.check("vlm", "cloud-unlisted")
        self.assertEqual(row["status"], "warn", row)
        self.assertIn("GET /models does not list the model other-model", row["summary"])

    def test_a_real_call_with_no_answer_in_time_is_an_error(self):
        with mock.patch.object(health, "CALL_TIMEOUT", 0.3):
            row = self.check("vlm", "chat-slow")
        self.assertEqual(row["status"], "error", row)
        self.assertIn("gave no answer in 0.3 s", row["summary"])

    def test_an_embedding_that_runs_gets_one_image(self):
        row = self.check("embedding", "gw-emb-run")
        self.assertEqual(row["status"], "ok", row)
        self.assertIn("one vector of 3 numbers", row["summary"])
        (_method, path, body), = self.posts(self.gateway_calls)
        self.assertEqual(path, "/v1/embeddings")
        self.assertEqual((body["model"], body["max_num_patches"]), ("emb-run", 256))
        self.assertTrue(body["input"][0].startswith("data:image/png;base64,"))

    def test_an_embedding_that_does_not_run_gets_no_call(self):
        row = self.check("embedding", "gw-emb-idle")
        self.assertEqual(row["status"], "idle", row)
        self.assertEqual(self.posts(self.gateway_calls), [])

    def test_sam3_that_runs_answers_its_health_route(self):
        row = self.check("sam3", "sam3")
        self.assertEqual(row["status"], "ok", row)
        self.assertIn("facebook/sam3", row["summary"])

    def test_sam3_that_does_not_run_gets_no_call(self):
        del self.Gateway.running["sam3"]
        row = self.check("sam3", "sam3")
        self.assertEqual(row["status"], "idle", row)
        self.assertNotIn(("GET", "/upstream/sam3/health"), self.gateway_calls)

    def test_the_sam3_endpoint_falls_back_to_the_service_of_derive(self):
        self.assertEqual(health.sam3_endpoint({}), health.derive.SAM3_ENDPOINT.rstrip("/"))
        self.assertEqual(health.sam3_endpoint({"sam3": {"endpoint": "http://h:1/upstream/sam3/"}}),
                         "http://h:1/upstream/sam3")
        with self.assertRaises(ValueError):
            health.sam3_endpoint({"sam3": {"endpoint": "sam3"}})

    def test_the_remote_api_sends_its_total(self):
        with mock.patch.object(health.import_website, "LIST_URL",
                               self.gw + "/v1/wines?page=%d&perPage=%d"):
            row = self.check("remote", health.REMOTE_NAME)
        self.assertEqual(row["status"], "ok", row)
        self.assertIn("2109 wines", row["summary"])
        self.assertIn(("GET", "/v1/wines?page=1&perPage=1"), self.gateway_calls)

    def fake_python(self, script):
        path = self.tmp / "python"
        path.write_text("#!/bin/sh\n" + script, encoding="utf-8")
        path.chmod(0o755)

    def test_the_local_backend_loads_no_model(self):
        cache = self.tmp / "hub"
        with mock.patch.dict(os.environ, {"HF_HUB_CACHE": str(cache)}):
            row = self.check("embedding", "local-emb")
            self.assertEqual(row["status"], "error", row)
            self.assertIn("is not a file", row["summary"])

            self.fake_python("echo 'ModuleNotFoundError: No module named torch' >&2; exit 1\n")
            row = self.check("embedding", "local-emb")
            self.assertEqual(row["status"], "error", row)
            self.assertIn("(exit code 1): ModuleNotFoundError: No module named torch",
                          row["summary"])

            self.fake_python("echo '{\"torch\": \"9.1\", \"transformers\": \"8.2\", "
                             "\"device\": \"cpu\"}'\n")
            row = self.check("embedding", "local-emb")
            self.assertEqual(row["status"], "warn", row)
            self.assertIn("torch 9.1, transformers 8.2, device cpu", row["summary"])
            self.assertIn("the first build downloads it", row["summary"])

            snapshot = cache / "models--google--test-model" / "snapshots" / "abc"
            snapshot.mkdir(parents=True)
            (snapshot / "config.json").write_text("{}", encoding="utf-8")
            (snapshot / "model.safetensors").write_bytes(b"x" * 1024)
            row = self.check("embedding", "local-emb")
            self.assertEqual(row["status"], "ok", row)
            self.assertIn("in the Hugging Face cache", row["summary"])
        self.assertEqual(self.gateway_calls, [])

    def test_an_unknown_endpoint_raises_key_error(self):
        for kind, name in (("vlm", "nope"), ("embedding", "nope"), ("sam3", "other"),
                           ("remote", "other")):
            with self.assertRaises(KeyError, msg=(kind, name)):
                self.check(kind, name)

    def test_the_endpoint_list_follows_the_page_order(self):
        endpoints = health.endpoint_list(self.config)
        self.assertEqual([item["kind"] for item in endpoints],
                         ["vlm"] * 10 + ["embedding"] * 3 + ["sam3", "remote"])
        cloud = next(item for item in endpoints if item["name"] == "cloud")
        self.assertEqual(cloud["key_env"], "HEALTH_TEST_KEY")
        local = next(item for item in endpoints if item["name"] == "local-emb")
        self.assertEqual(local["endpoint"], "local: %s/python" % self.tmp)
        sam3 = next(item for item in endpoints if item["kind"] == "sam3")
        self.assertEqual((sam3["endpoint"], sam3["model"]), (self.gw + "/upstream/sam3", "sam3"))
        self.assertEqual(endpoints[-1]["used_by"], ["the website import"])

    def test_the_gateway_part_marks_the_models_of_the_config(self):
        gateways = health.gateways_part(health.endpoint_list(self.config))
        # The root of `plain` is not a gateway and is left out. The root of `dead` gives
        # no answer, so it stays with its error.
        dead = "http://127.0.0.1:%d" % self.closed
        self.assertEqual([item["root"] for item in gateways], [self.gw, dead])
        used = {item["model"]: item["used"] for item in gateways[0]["running"]}
        self.assertEqual(used, {"chat-run": True, "chat-slow": True, "chat-starting": True,
                                "chat-crash": True, "emb-run": True, "sam3": True})
        self.assertIsNone(gateways[1]["running"])
        self.assertIn("no process listens", gateways[1]["error"])


class StatusPartTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.tmp = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_log_failures_keeps_the_last_hour(self):
        log = self.tmp / "describe_images.log"
        log.write_text("\n".join([
            "2026-09-26T05:00:00Z a902e43a5f77 detail failed (not counted): old",
            "2026-09-26T06:30:00Z a902e43a5f77 detail failed (not counted): timed out",
            "2026-09-26T06:40:00Z b1 ok bottle full_package front [] 2.3 s",
            "2026-09-26T06:45:00Z waiting: the database has schema version 20",
            "  a line of an earlier entry that failed",
            "2026-09-26T06:50:00Z start: watch, vlm qwen3.5-9b-nvfp4"]) + "\n",
            encoding="utf-8")
        now = datetime(2026, 9, 26, 7, 0, 0, tzinfo=timezone.utc).timestamp()
        lines, count = health.log_failures(str(log), now=now)
        self.assertEqual(count, 2)
        self.assertEqual([line[:20] for line in lines],
                         ["2026-09-26T06:30:00Z", "2026-09-26T06:45:00Z"])
        self.assertEqual(health.log_failures(str(self.tmp / "missing.log")), ([], 0))

    def test_database_part_reports_the_schema_and_the_wines(self):
        missing = health.database_part(str(self.tmp / "none.sqlite3"))
        self.assertEqual(missing["status"], "error")
        self.assertIn("no database at", missing["message"])

        path = str(self.tmp / "lab.sqlite3")
        conn = labdb.connect(path, create=True)
        with conn:
            conn.execute("INSERT INTO wine_catalog (wine_slug, name, producer, category, "
                         "color, region, description, csv_photo_name, state) VALUES "
                         "('a', 'A', 'P', 'C', 'R', 'K', 'D', 'a.webp', 'Active')")
        conn.close()
        part = health.database_part(path)
        self.assertEqual(part["status"], "ok", part)
        self.assertEqual(part["version"], part["expected_version"])
        self.assertEqual(part["states"], {"Active": 1, "Disabled": 0, "Removed": 0})

        conn = sqlite3.connect(path)
        conn.execute("PRAGMA user_version = %d" % (part["expected_version"] - 1))
        conn.close()
        part = health.database_part(path)
        self.assertEqual(part["status"], "error")
        self.assertIn("run `python3 pipeline/labdb.py", part["message"])


class HealthRouteTest(unittest.TestCase):
    """The routes, through the lab server."""

    def setUp(self):
        import lab_server
        self.lab_server = lab_server
        self.directory = tempfile.TemporaryDirectory()
        self.tmp = Path(self.directory.name)
        self.db = str(self.tmp / "lab.sqlite3")
        labdb.connect(self.db, create=True).close()
        self.config = str(self.tmp / "config.yaml")
        Path(self.config).write_text(
            "rootdir: %s\ndatabase_file: lab.sqlite3\nsam3:\n  endpoint: http://127.0.0.1:%d"
            "/upstream/sam3\nvlm:\n  - {name: dead, protocol: openai, thinking_field: "
            "chat_template_kwargs, endpoint: \"http://127.0.0.1:%d/v1\", model: m}\n"
            % (self.tmp, closed_port(), closed_port()), encoding="utf-8")
        self.server = lab_server.make_server(self.db, port=0, config_path=self.config)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def request(self, path, method="GET", body=None):
        req = urllib.request.Request(self.base + path, method=method, data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    def test_the_page_has_the_link_on(self):
        status, body = self.request("/health")
        self.assertEqual(status, 200)
        self.assertIn('<a class="on"\n      href="/health">Health</a>', body)
        self.assertIn(("/health", "Health"), self.lab_server.NAV)

    def test_the_status_route_sends_each_part(self):
        status, body = self.request("/api/health")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(sorted(data["status"]),
                         ["database", "gateways", "jobs", "server", "watcher"])
        self.assertEqual(data["status"]["database"]["status"], "ok")
        self.assertIsNotNone(data["status"]["server"]["started_at"])
        self.assertEqual([item["kind"] for item in data["endpoints"]], ["vlm", "sam3", "remote"])
        # The roots with no answer give an error in the gateway part, not a failed page.
        self.assertTrue(all(item["error"] for item in data["status"]["gateways"]))

    def test_the_check_route(self):
        for body, code in ((b"", 400), (b"[]", 400), (b'{"kind": "x", "name": "dead"}', 400),
                           (b'{"kind": "vlm"}', 400), (b'{"kind": "vlm", "name": "nope"}', 404)):
            status, text = self.request("/api/health/check", "POST", body)
            self.assertEqual(status, code, (body, text))
            self.assertIn("error", json.loads(text))
        status, text = self.request("/api/health/check", "POST",
                                    b'{"kind": "vlm", "name": "dead"}')
        self.assertEqual(status, 200)
        row = json.loads(text)
        self.assertEqual((row["status"], row["name"]), ("error", "dead"))
        self.assertIn("no process listens", row["summary"])
        self.assertEqual(self.request("/api/health/check")[0], 405)


if __name__ == "__main__":
    unittest.main()
