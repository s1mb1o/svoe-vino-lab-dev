"""Tests for the read-only Matcher Inspector."""

import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import (  # noqa: E402
    InspectorServer,
    list_bundles,
    list_requests,
    load_request,
    render_home,
    render_request,
)


REQUEST_ID = "a" * 32


def request_document():
    return {
        "request_id": REQUEST_ID,
        "received_at": "2026-09-28T10:00:00Z",
        "completed_at": "2026-09-28T10:00:01Z",
        "duration_ms": 1000,
        "client_ip": "192.168.86.10",
        "request": {"method": "POST", "path": "/v1/eval/predict"},
        "image": {
            "original_filename": "wine.webp",
            "content_type": "image/webp",
            "size_bytes": 4,
            "sha256": "b" * 64,
            "width": 20,
            "height": 40,
        },
        "response": {"status_code": 200, "slug": "wine_slug"},
    }


def write_request(root: Path):
    directory = root / "requests" / "2026-09-28" / REQUEST_ID
    directory.mkdir(parents=True)
    (directory / "request.json").write_text(
        json.dumps(request_document()), encoding="utf-8"
    )
    (directory / "image.webp").write_bytes(b"RIFF")
    return directory


def write_bundle(root: Path, include_vectors=True):
    directory = root / "bundles" / "siglip2-p512"
    directory.mkdir(parents=True)
    if include_vectors:
        (directory / "vectors.npy").write_bytes(b"vector")
    (directory / "candidates.jsonl").write_text("{}\n", encoding="utf-8")
    manifest = {
        "format": "svoe-vino-matcher-bundle",
        "format_version": 1,
        "created_at": "2026-09-28T10:00:00Z",
        "embedding": {
            "backend": "openai",
            "model": "siglip2-test",
            "name": "siglip2-p512",
            "views": {"full": []},
        },
        "counts": {"wines": 12},
        "vectors": {"shape": [20, 8]},
        "files": {
            "vectors.npy": {"bytes": 6, "sha256": "unused"},
            "candidates.jsonl": {"bytes": 3, "sha256": "unused"},
        },
    }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


class RequestTest(unittest.TestCase):
    def test_lists_and_renders_one_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            write_request(data)
            records = list_requests(data / "requests")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].request_id, REQUEST_ID)
            self.assertEqual(records[0].image_path.name, "image.webp")
            page = render_request(records[0])
            self.assertIn("wine_slug", page)
            self.assertIn("/requests/2026-09-28/%s/image" % REQUEST_ID, page)

    def test_rejects_path_segments_outside_the_archive_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "requests"
            write_request(Path(temporary))
            self.assertIsNone(load_request(root, "..", REQUEST_ID))
            self.assertIsNone(load_request(root, "2026-09-28", "../request"))

    def test_skips_a_symlinked_request_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            source = write_request(data)
            link_id = "c" * 32
            (source.parent / link_id).symlink_to(source, target_is_directory=True)
            records = list_requests(data / "requests")
            self.assertEqual([record.request_id for record in records], [REQUEST_ID])


class BundleTest(unittest.TestCase):
    def test_lists_a_complete_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            write_bundle(data)
            records = list_bundles(data, data / "requests")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].relative_path, "bundles/siglip2-p512")
            self.assertEqual(records[0].issues, ())
            page = render_home([], records)
            self.assertIn("siglip2-test", page)
            self.assertIn("20 × 8", page)
            self.assertIn("Complete", page)

    def test_marks_a_missing_payload_as_incomplete(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            write_bundle(data, include_vectors=False)
            record = list_bundles(data, data / "requests")[0]
            self.assertIn("vectors.npy is missing", record.issues)
            self.assertIn("Incomplete", render_home([], [record]))

    def test_skips_the_request_archive_during_bundle_scan(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            write_request(data)
            request = data / "requests" / "2026-09-28" / REQUEST_ID
            (request / "manifest.json").write_text(
                json.dumps(
                    {
                        "format": "svoe-vino-matcher-bundle",
                        "files": {},
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(list_bundles(data, data / "requests"), [])


class HttpTest(unittest.TestCase):
    def test_serves_health_home_request_and_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            write_request(data)
            write_bundle(data)
            try:
                server = InspectorServer(("127.0.0.1", 0), data / "requests", data)
            except PermissionError:
                self.skipTest("the test sandbox does not permit a loopback listener")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = "http://127.0.0.1:%d" % server.server_address[1]
            try:
                with urlopen(base + "/healthz") as response:
                    health = json.load(response)
                self.assertEqual(health["status"], "ok")
                with urlopen(base + "/") as response:
                    home = response.read().decode("utf-8")
                self.assertIn("wine_slug", home)
                self.assertIn("siglip2-test", home)
                path = "/requests/2026-09-28/%s" % REQUEST_ID
                with urlopen(base + path) as response:
                    detail = response.read().decode("utf-8")
                self.assertIn("Complete request journal", detail)
                with urlopen(base + path + "/image") as response:
                    self.assertEqual(response.read(), b"RIFF")
                    self.assertEqual(response.headers.get_content_type(), "image/webp")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
