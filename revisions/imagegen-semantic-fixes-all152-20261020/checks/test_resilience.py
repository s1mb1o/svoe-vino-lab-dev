"""Bounded adversarial tests for matcher upload protections."""

from io import BytesIO
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
import warnings

from PIL import Image

from matcher.protection import ImageRejected, validate_image


ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).resolve().parent / "config.yaml"
MAX_IMAGE_BYTES = 32 * 1024
MAX_REQUEST_BYTES = MAX_IMAGE_BYTES + 64 * 1024
UPLOAD_TIMEOUT_SECONDS = 0.4
QUEUE_TIMEOUT_SECONDS = 1.0


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


def tiny_jpeg():
    output = BytesIO()
    with Image.new("RGB", (2, 2), (12, 34, 56)) as image:
        image.save(output, format="JPEG")
    return output.getvalue()


def tiny_gif():
    output = BytesIO()
    with Image.new("RGB", (2, 2), (12, 34, 56)) as image:
        image.save(output, format="GIF")
    return output.getvalue()


def tiny_mpo():
    output = BytesIO()
    with Image.new("RGB", (4, 3), "red") as first:
        with Image.new("RGB", (4, 3), "blue") as second:
            first.save(output, format="MPO", save_all=True, append_images=[second])
    return output.getvalue()


def jpeg_dimension_bomb(width=65535, height=65535):
    """Make a tiny JPEG that declares `width` by `height` pixels."""
    body = bytearray(tiny_jpeg())
    index = 2
    start_of_frame = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while index + 9 < len(body):
        if body[index] != 0xFF:
            index += 1
            continue
        marker = body[index + 1]
        if marker in start_of_frame:
            body[index + 5:index + 7] = height.to_bytes(2, "big")
            body[index + 7:index + 9] = width.to_bytes(2, "big")
            return bytes(body)
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            index += 2
            continue
        length = int.from_bytes(body[index + 2:index + 4], "big")
        index += 2 + length
    raise AssertionError("generated JPEG has no start-of-frame marker")


def multipart(body, filename="image.jpg", boundary="matcher-resilience"):
    payload = (
        ("--%s\r\n" % boundary).encode("ascii")
        + ('Content-Disposition: form-data; name="image"; filename="%s"\r\n'
           % filename).encode("ascii")
        + b"Content-Type: image/jpeg\r\n\r\n"
        + body
        + ("\r\n--%s--\r\n" % boundary).encode("ascii")
    )
    return payload, "multipart/form-data; boundary=%s" % boundary


def response_status(raw):
    first_line = raw.split(b"\r\n", 1)[0]
    return int(first_line.split(b" ", 2)[1])


def receive_response(connection):
    connection.settimeout(3)
    chunks = []
    while True:
        try:
            chunk = connection.recv(65536)
        except (ConnectionResetError, socket.timeout):
            break
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


class MatcherResilienceTest(unittest.TestCase):
    def setUp(self):
        self.port = free_port()
        self.output_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.output_directory.cleanup)
        environment = os.environ.copy()
        environment["SVOE_VINO_MATCHER_CONFIG"] = str(CONFIG)
        environment["SVOE_VINO_MATCHER_OUTPUT_DIR"] = self.output_directory.name
        environment["SVOE_VINO_MATCHER_MAX_IMAGE_BYTES"] = str(MAX_IMAGE_BYTES)
        environment["SVOE_VINO_MATCHER_MAX_IMAGE_PIXELS"] = "1000000"
        environment["SVOE_VINO_MATCHER_UPLOAD_TIMEOUT_SECONDS"] = str(
            UPLOAD_TIMEOUT_SECONDS)
        environment["SVOE_VINO_MATCHER_MAX_INFLIGHT_REQUESTS"] = "2"
        environment["SVOE_VINO_MATCHER_MAX_QUEUED_REQUESTS"] = "1"
        environment["SVOE_VINO_MATCHER_QUEUE_TIMEOUT_SECONDS"] = str(
            QUEUE_TIMEOUT_SECONDS)
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "matcher.app:app",
             "--host", "127.0.0.1", "--port", str(self.port),
             "--log-level", "info"],
            cwd=ROOT, env=environment, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True)
        self.addCleanup(self.stop_server)
        wait_for_server(self.process, self.port)

    def stop_server(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.process.stdout is not None:
            self.process.stdout.close()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            result = response.status, response.read()
            return result
        finally:
            connection.close()

    def predict(self, image):
        body, content_type = multipart(image)
        return self.request(
            "POST", "/v1/eval/predict", body,
            {"Content-Type": content_type},
        )

    def assert_service_survives(self):
        status, body = self.request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")
        status, body = self.predict(tiny_jpeg())
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"slug": ""})

    def open_slow_upload(self):
        connection = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        prefix = (
            "POST /v1/eval/predict HTTP/1.1\r\n"
            "Host: 127.0.0.1\r\n"
            "Content-Type: multipart/form-data; boundary=slow\r\n"
            "Content-Length: 10000\r\n"
            "Connection: close\r\n\r\n"
            "--slow\r\n"
            "Content-Disposition: form-data; name=\"image\"; filename=\"slow.jpg\"\r\n"
            "Content-Type: image/jpeg\r\n\r\n"
        ).encode("ascii")
        connection.sendall(prefix + b"x")
        return connection

    def test_jpeg_dimension_bomb_is_rejected(self):
        bomb = jpeg_dimension_bomb()
        self.assertLess(len(bomb), 4096)
        status, body = self.predict(bomb)
        self.assertEqual(status, 413)
        self.assertIn("pixel count", json.loads(body)["detail"])
        self.assert_service_survives()

    def test_damaged_image_is_rejected(self):
        status, body = self.predict(b"not an image")
        self.assertEqual(status, 422)
        self.assertIn("invalid or damaged", json.loads(body)["detail"])
        self.assert_service_survives()

    def test_unsupported_image_format_is_rejected(self):
        status, body = self.predict(tiny_gif())
        self.assertEqual(status, 415)
        self.assertIn("JPEG (including MPO), PNG, or WEBP",
                      json.loads(body)["detail"])
        self.assert_service_survives()

    def test_mpo_is_accepted_as_a_jpeg_family_image(self):
        status, body = self.predict(tiny_mpo())
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"slug": ""})
        records = list(Path(self.output_directory.name).rglob("request.json"))
        self.assertEqual(len(records), 1)
        record = json.loads(records[0].read_text(encoding="utf-8"))
        self.assertEqual(record["image"]["format"], "MPO")
        self.assertEqual((record["image"]["width"], record["image"]["height"]),
                         (4, 3))

    @unittest.skipUnless(shutil.which("curl"), "the sparse upload test needs curl")
    def test_one_gibibyte_sparse_upload_is_rejected_before_transfer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sparse.jpg"
            with path.open("wb") as output:
                output.truncate(1024 ** 3)
            self.assertEqual(path.stat().st_size, 1024 ** 3)
            started_at = time.monotonic()
            result = subprocess.run(
                ["curl", "--silent", "--show-error", "--output", "/dev/null",
                 "--write-out", "%{http_code}",
                 "--header", "Expect: 100-continue",
                 "--form", "image=@%s" % path,
                 "http://127.0.0.1:%d/v1/eval/predict" % self.port],
                cwd=ROOT, capture_output=True, text=True, timeout=10)
            duration = time.monotonic() - started_at
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "413")
        self.assertLess(duration, 5)
        self.assert_service_survives()

    def test_slow_upload_times_out(self):
        connection = self.open_slow_upload()
        self.addCleanup(connection.close)
        time.sleep(UPLOAD_TIMEOUT_SECONDS + 0.25)
        response = receive_response(connection)
        self.assertEqual(response_status(response), 408, response)
        self.assert_service_survives()

    def test_full_queue_returns_503_while_healthz_stays_available(self):
        slow = [self.open_slow_upload(), self.open_slow_upload(),
                self.open_slow_upload()]
        for connection in slow:
            self.addCleanup(connection.close)
        time.sleep(0.1)
        started_at = time.monotonic()
        status, body = self.predict(tiny_jpeg())
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body)["detail"], "matcher is busy")
        self.assertLess(time.monotonic() - started_at, UPLOAD_TIMEOUT_SECONDS)
        status, _ = self.request("GET", "/healthz")
        self.assertEqual(status, 200)

    def test_chunked_body_above_limit_is_rejected(self):
        connection = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        self.addCleanup(connection.close)
        connection.sendall(
            b"POST /v1/eval/predict HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Content-Type: multipart/form-data; boundary=chunked\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"Connection: close\r\n\r\n"
        )
        prefix = (
            b"--chunked\r\nContent-Disposition: form-data; name=\"image\"; "
            b"filename=\"large.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n"
        )
        connection.sendall(
            ("%x\r\n" % len(prefix)).encode("ascii") + prefix + b"\r\n")
        chunk = b"x" * 4096
        for _ in range((MAX_REQUEST_BYTES // len(chunk)) + 3):
            try:
                connection.sendall(b"1000\r\n" + chunk + b"\r\n")
            except OSError:
                break
        response = receive_response(connection)
        self.assertEqual(response_status(response), 413, response)
        self.assert_service_survives()


class ImageValidationTest(unittest.TestCase):
    """Check `validate_image` and the pixel limit setting without a matcher server."""

    def test_parallel_checks_leave_the_warnings_filters_unchanged(self):
        # Force this order: check A enters, check B enters, A leaves, B leaves. A check
        # that saves and restores the global filter list leaks the filter of A here.
        open_image = Image.open
        a_opened, b_opened, a_done = threading.Event(), threading.Event(), threading.Event()

        def ordered_open(source):
            if threading.current_thread().name == "a":
                a_opened.set()
                b_opened.wait(5)
            else:
                b_opened.set()
                a_done.wait(5)
            return open_image(source)

        def check_a():
            try:
                validate_image(tiny_jpeg(), 1000)
            finally:
                a_done.set()

        check_b = threading.Thread(
            target=validate_image, args=(tiny_jpeg(), 1000), name="b")
        with warnings.catch_warnings():
            before = list(warnings.filters)
            with mock.patch.object(Image, "open", side_effect=ordered_open):
                check_a_thread = threading.Thread(target=check_a, name="a")
                check_a_thread.start()
                self.assertTrue(a_opened.wait(5))
                check_b.start()
                check_a_thread.join(5)
                check_b.join(5)
            after = list(warnings.filters)
        self.assertEqual(after, before)

    def test_a_header_above_the_pillow_warning_limit_is_rejected(self):
        # 100,000,000 pixels: Pillow warns and does not raise. The pixel check rejects it.
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            with self.assertRaises(ImageRejected) as caught:
                validate_image(jpeg_dimension_bomb(10_000, 10_000), 1_000_000)
        self.assertEqual(caught.exception.status_code, 413)

    def test_a_pixel_limit_above_the_pillow_limit_stops_the_start(self):
        limit = Image.MAX_IMAGE_PIXELS
        for value, stops in ((limit, False), (limit + 1, True)):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                environment = os.environ.copy()
                environment["SVOE_VINO_MATCHER_CONFIG"] = str(CONFIG)
                environment["SVOE_VINO_MATCHER_OUTPUT_DIR"] = directory
                environment["SVOE_VINO_MATCHER_MAX_IMAGE_PIXELS"] = str(value)
                result = subprocess.run(
                    [sys.executable, "-c", "import matcher.app"], cwd=ROOT,
                    env=environment, capture_output=True, text=True, timeout=60)
                if stops:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("MUST NOT exceed the Pillow limit %d" % limit,
                                  result.stderr)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
