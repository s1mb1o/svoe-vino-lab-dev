"""Integration tests for optional Bearer authentication."""

import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).resolve().parent / "config.token.yaml"
IMAGE = Path(__file__).resolve().parent / "data" / "019c68d0.jpg"
TOKEN = "matcher-auth-test-token"


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def wait_for_server(process, port):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.communicate()[0]
            raise AssertionError("matcher stopped before it listened:\n%s" % output)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                return
        except OSError:
            time.sleep(0.05)
    raise AssertionError("matcher did not listen within 10 seconds")


def multipart_image(path):
    boundary = "matcher-auth-boundary"
    body = (
        ("--%s\r\n" % boundary).encode("ascii")
        + b'Content-Disposition: form-data; name="image"; filename="019c68d0.jpg"\r\n'
        + b"Content-Type: image/jpeg\r\n\r\n"
        + path.read_bytes()
        + ("\r\n--%s--\r\n" % boundary).encode("ascii")
    )
    return body, "multipart/form-data; boundary=%s" % boundary


class BearerAuthenticationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = free_port()
        cls.output_directory = tempfile.TemporaryDirectory()
        environment = os.environ.copy()
        environment["SVOE_VINO_MATCHER_CONFIG"] = str(CONFIG)
        environment["SVOE_VINO_MATCHER_OUTPUT_DIR"] = cls.output_directory.name
        environment["SVOE_VINO_MATCHER_TOKEN"] = TOKEN
        cls.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "matcher.app:app",
             "--host", "127.0.0.1", "--port", str(cls.port),
             "--log-level", "info"],
            cwd=ROOT, env=environment, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True)
        try:
            wait_for_server(cls.process, cls.port)
        except Exception:
            cls.stop_server()
            cls.output_directory.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.stop_server()
        cls.output_directory.cleanup()

    @classmethod
    def stop_server(cls):
        process = getattr(cls, "process", None)
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if process.stdout is not None:
            process.stdout.close()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            result = (
                response.status,
                {name.lower(): value for name, value in response.getheaders()},
                response.read(),
            )
            return result
        finally:
            connection.close()

    def predict(self, authorization=None):
        body, content_type = multipart_image(IMAGE)
        headers = {"Content-Type": content_type}
        if authorization is not None:
            headers["Authorization"] = authorization
        return self.request("POST", "/v1/eval/predict", body, headers)

    def auth_probe(self, authorization=None):
        headers = {}
        if authorization is not None:
            headers["Authorization"] = authorization
        return self.request("POST", "/v1/eval/predict", b"", headers)

    def test_healthz_and_openapi_are_public(self):
        status, _, body = self.request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {
            "status": "ok",
            "pipeline": "official-eval-mock",
        })
        status, _, body = self.request("GET", "/openapi.json")
        self.assertEqual(status, 200)
        self.assertIn("BearerAuth", json.loads(body)["components"]["securitySchemes"])

    def test_missing_and_invalid_tokens_return_401(self):
        for authorization in (None, "", "Basic abc", "Bearer", "Bearer wrong"):
            with self.subTest(authorization=authorization):
                status, headers, body = self.auth_probe(authorization)
                self.assertEqual(status, 401)
                self.assertEqual(headers["www-authenticate"], "Bearer")
                self.assertEqual(json.loads(body), {
                    "detail": "invalid or missing bearer token",
                })

    def test_valid_bearer_token_allows_prediction(self):
        for scheme in ("Bearer", "bearer"):
            with self.subTest(scheme=scheme):
                status, _, body = self.predict("%s %s" % (scheme, TOKEN))
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body), {"slug": "tabia_pino_nuar"})


if __name__ == "__main__":
    unittest.main()
