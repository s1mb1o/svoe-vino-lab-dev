"""Run the official shell harness against a live matcher process."""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from PIL import Image
import yaml


ROOT = Path(__file__).resolve().parents[2]
HARNESS = Path(__file__).resolve().parent / "participant_test.sh"
CONFIG = Path(__file__).resolve().parent / "config.yaml"
DATA = Path(__file__).resolve().parent / "data"
MANIFEST = Path(__file__).resolve().parent / "queries.tsv"
OPENAPI = Path(__file__).resolve().parents[1] / "openapi.yaml"
MAX_IMAGE_BYTES = 1_500_000
EXPECTED = {
    "019c68d0.webp": "tabia_pino_nuar",
    "02eef911.webp":
        "massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16",
    "096ca74e.webp": "donum_xxiv",
}
TOOLS = ("bash", "curl", "jq", "awk")
JSONL_FIELDS = (
    "query_id", "image_path", "image_sha256", "predicted_slug", "latency_ms",
)


def free_port():
    """Reserve and release one ephemeral local port."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def wait_for_server(process, port):
    """Wait until the child listens, or fail with its output."""
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


@unittest.skipUnless(all(shutil.which(tool) for tool in TOOLS),
                     "the official harness needs bash, curl, jq, and awk")
class OfficialHarnessTest(unittest.TestCase):
    def setUp(self):
        self.port = free_port()
        self.output_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.output_directory.cleanup)
        self.output_path = Path(self.output_directory.name)
        environment = os.environ.copy()
        environment["SVOE_VINO_MATCHER_CONFIG"] = str(CONFIG)
        environment["SVOE_VINO_MATCHER_OUTPUT_DIR"] = str(self.output_path)
        environment["SVOE_VINO_MATCHER_MAX_IMAGE_BYTES"] = str(MAX_IMAGE_BYTES)
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "matcher.app:app",
             "--host", "127.0.0.1", "--port", str(self.port),
             "--log-level", "info"],
            cwd=ROOT, env=environment, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True)
        self.addCleanup(self.stop, self.process)
        wait_for_server(self.process, self.port)

    def run_harness(self, directory):
        output = Path(directory) / "predictions.jsonl"
        completed = subprocess.run(
            ["bash", str(HARNESS),
             "--images-dir", str(DATA),
             "--manifest", str(MANIFEST),
             "--endpoint", "http://127.0.0.1:%d/v1/eval/predict" % self.port,
             "--output", str(output)],
            cwd=ROOT, capture_output=True, text=True, timeout=40)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return output

    def test_the_official_harness_gets_the_three_configured_slugs(self):

        openapi_response = subprocess.run(
            ["curl", "--silent", "--show-error", "--fail",
             "http://127.0.0.1:%d/openapi.json" % self.port],
            cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(openapi_response.returncode, 0,
                         openapi_response.stdout + openapi_response.stderr)
        openapi = json.loads(openapi_response.stdout)
        documented = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))
        self.assertEqual(openapi, documented)

        with tempfile.TemporaryDirectory() as directory:
            output = self.run_harness(directory)
            rows = [json.loads(line) for line in output.read_text().splitlines()]
            unknown = Path(directory) / "unknown.jpg"
            with Image.new("RGB", (1, 1), (12, 34, 56)) as generated:
                generated.save(unknown, format="JPEG")
            fallback = subprocess.run(
                ["curl", "--silent", "--show-error", "--fail",
                 "--form", "image=@%s" % unknown,
                 "http://127.0.0.1:%d/v1/eval/predict" % self.port],
                cwd=ROOT, capture_output=True, text=True, timeout=10)

        self.assertEqual(len(rows), 3)
        self.assertEqual(
            {row["image_path"]: row["predicted_slug"] for row in rows}, EXPECTED)
        self.assertTrue(all(row["latency_ms"] >= 0 for row in rows))
        self.assertEqual(fallback.returncode, 0, fallback.stdout + fallback.stderr)
        self.assertEqual(json.loads(fallback.stdout), {"slug": ""})

    def test_participant_script_writes_the_documented_jsonl_record(self):
        with tempfile.TemporaryDirectory() as directory:
            output = self.run_harness(directory)
            lines = output.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 3)
        first = json.loads(lines[0])
        self.assertEqual(tuple(first), JSONL_FIELDS)
        self.assertEqual(first["query_id"], "q-000001")
        self.assertEqual(first["image_path"], "019c68d0.webp")
        self.assertEqual(
            first["image_sha256"],
            "c975b31e13bfa77dbc402d7ae4cd3889609cf85a9dadda45778a63232b4c6acf")
        self.assertEqual(first["predicted_slug"], "tabia_pino_nuar")
        self.assertIs(type(first["latency_ms"]), int)
        self.assertGreaterEqual(first["latency_ms"], 0)

    def test_request_archive_saves_image_headers_ip_and_duration(self):
        source = DATA / "019c68d0.webp"
        response = subprocess.run(
            ["curl", "--silent", "--show-error", "--fail",
             "--header", "X-Matcher-Test: audit-example",
             "--header", "Authorization: Bearer private-test-token",
             "--form", "image=@%s" % source,
             "http://127.0.0.1:%d/v1/eval/predict" % self.port],
            cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(response.returncode, 0, response.stdout + response.stderr)

        records = list(self.output_path.rglob("request.json"))
        self.assertEqual(len(records), 1)
        record = json.loads(records[0].read_text(encoding="utf-8"))
        headers = {item["name"]: item["value"] for item in record["request"]["headers"]}
        saved_image = self.output_path / record["image"]["saved_path"]
        self.process.terminate()
        log_output = self.process.communicate(timeout=5)[0]

        self.assertEqual(record["client_ip"], "127.0.0.1")
        self.assertEqual(record["request"]["method"], "POST")
        self.assertEqual(record["request"]["path"], "/v1/eval/predict")
        self.assertEqual(headers["x-matcher-test"], "audit-example")
        self.assertEqual(headers["authorization"], "<redacted>")
        self.assertEqual(record["image"]["original_filename"], source.name)
        self.assertEqual(
            record["image"]["sha256"],
            "c975b31e13bfa77dbc402d7ae4cd3889609cf85a9dadda45778a63232b4c6acf")
        self.assertEqual(record["image"]["size_bytes"], source.stat().st_size)
        self.assertIn(record["image"]["format"], {"JPEG", "WEBP"})
        self.assertGreater(record["image"]["pixels"], 0)
        self.assertEqual(saved_image.read_bytes(), source.read_bytes())
        self.assertEqual(record["response"], {
            "status_code": 200,
            "slug": "tabia_pino_nuar",
        })
        self.assertGreaterEqual(record["duration_ms"], 0)
        self.assertTrue(record["received_at"].endswith("Z"))
        self.assertTrue(record["completed_at"].endswith("Z"))
        self.assertIn("matcher_request", log_output)
        self.assertIn(record["request_id"], log_output)

    def test_liveness_and_mock_readiness_return_the_pipeline(self):
        for path in ("healthz", "readyz"):
            with self.subTest(path=path):
                response = subprocess.run(
                    ["curl", "--silent", "--show-error", "--fail",
                     "http://127.0.0.1:%d/%s" % (self.port, path)],
                    cwd=ROOT, capture_output=True, text=True, timeout=10)
                self.assertEqual(
                    response.returncode, 0, response.stdout + response.stderr)
                self.assertEqual(json.loads(response.stdout), {
                    "status": "ok",
                    "pipeline": "official-eval-mock",
                })

    def test_missing_image_returns_422(self):
        self.assertEqual(self.post_status(["--request", "POST"]), "422")

    def test_empty_image_returns_400(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.jpg"
            path.write_bytes(b"")
            self.assertEqual(self.post_status(["--form", "image=@%s" % path]), "400")

    def test_oversized_image_returns_413(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.jpg"
            path.write_bytes(b"x" * (MAX_IMAGE_BYTES + 1))
            self.assertEqual(self.post_status(["--form", "image=@%s" % path]), "413")

    def post_status(self, arguments):
        completed = subprocess.run(
            ["curl", "--silent", "--show-error", "--output", "/dev/null",
             "--write-out", "%{http_code}", *arguments,
             "http://127.0.0.1:%d/v1/eval/predict" % self.port],
            cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout

    @staticmethod
    def stop(process):
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        finally:
            if process.stdout is not None:
                process.stdout.close()


if __name__ == "__main__":
    unittest.main()
