"""Tests for the backend siglip2 with a fixture bundle and a fake SigLIP2 endpoint."""

import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
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

import numpy as np
from PIL import Image
import yaml

from matcher.service import ConfigError, load_matcher
from matcher.siglip2 import Siglip2Error, model_input


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "matcher" / "config.yaml"
HARNESS = Path(__file__).resolve().parent / "participant_test.sh"
DATA = Path(__file__).resolve().parent / "data"
MANIFEST = Path(__file__).resolve().parent / "queries.tsv"
MODEL = "siglip2-so400m-patch16-naflex"
TOOLS = ("bash", "curl", "jq", "awk")
# (view, vector, wine slugs) of each vector row. A label vector can have a higher cosine
# than every full vector; the backend MUST ignore it. The last row is one image of two
# wines.
ROWS = (
    ("full", (1, 0, 0, 0), ("wine-a",)),
    ("full", (0, 1, 0, 0), ("wine-b",)),
    ("label", (0, 0, 1, 0), ("wine-c",)),
    ("full", (0, 0, 0, 1), ("wine-shared-b", "wine-shared-a")),
)


def unit(values):
    vector = np.asarray(values, dtype=np.float32)
    return vector / np.linalg.norm(vector)


def write_jsonl(path, values):
    path.write_text("".join(json.dumps(value, sort_keys=True) + "\n" for value in values),
                    encoding="utf-8")


def file_record(path):
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size}


def write_bundle(root, rows=ROWS):
    """Write a small bundle in the format of workbench/pipeline/matcher_bundle.py."""
    root.mkdir()
    vectors = np.vstack([unit(vector) for _, vector, _ in rows]).astype(np.float32)
    np.save(root / "vectors.npy", vectors, allow_pickle=False)
    items, candidates = [], []
    for row, (view, _, slugs) in enumerate(rows):
        digest = hashlib.sha256(b"source %d" % row).hexdigest()
        items.append({
            "vector_row": row, "source_vector_row": row, "source_sha256": digest,
            "view": view, "role": "full",
            "embedding_hash": hashlib.sha256(b"item %d" % row).hexdigest(),
            "derivative_sha256": None, "image": "images/%s_%s.png" % (digest, view),
            "width": 10, "height": 20,
        })
        candidates.extend({"vector_row": row, "wine_slug": slug, "view": view,
                           "image_type": "main_photo"} for slug in slugs)
    slugs = sorted({candidate["wine_slug"] for candidate in candidates})
    write_jsonl(root / "items.jsonl", items)
    write_jsonl(root / "candidates.jsonl", candidates)
    write_jsonl(root / "wines.jsonl", [
        {"wine_slug": slug, "name": slug, "producer": None, "category": None,
         "region": None} for slug in slugs])
    write_jsonl(root / "omissions.jsonl", [])
    payloads = ("vectors.npy", "items.jsonl", "candidates.jsonl", "wines.jsonl",
                "omissions.jsonl")
    manifest = {
        "format": "svoe-vino-matcher-bundle",
        "format_version": 1,
        "created_at": "2026-09-28T00:00:00+0300",
        "source": {"embedding": "test-siglip2"},
        "embedding": {
            "name": "test-siglip2", "backend": "openai",
            "base_url": "http://unused.invalid/v1", "model": MODEL,
            "extra_body": {"max_num_patches": 512},
            "views": {"full": [], "label": []},
        },
        "vectors": {"file": "vectors.npy", "dtype": "float32",
                    "shape": list(vectors.shape), "normalized": "l2"},
        "scoring": {"similarity": "dot_product", "item_reduction": "max",
                    "view_reduction": "mean"},
        "images": {"included": False, "manifest": None, "count": 0},
        "counts": {"planned_items": len(items), "items": len(items),
                   "candidates": len(candidates), "wines": len(slugs),
                   "omissions": 0, "images": 0},
        "files": {name: file_record(root / name) for name in payloads},
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


class FakeSiglip2:
    """A local OpenAI-compatible endpoint that returns one fixed vector per request."""

    def __init__(self, vector, status=200):
        self.vector = [float(value) for value in vector]
        self.status = status
        self.requests = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fake.requests.append((self.path, body))
                if fake.status == 200:
                    payload = {"object": "list", "model": body.get("model"), "data": [
                        {"object": "embedding", "index": index,
                         "embedding": fake.vector}
                        for index, _ in enumerate(body.get("input", []))]}
                else:
                    payload = {"error": "fake failure"}
                data = json.dumps(payload).encode("utf-8")
                self.send_response(fake.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


def image_bytes(image, format_name, **options):
    buffer = BytesIO()
    image.save(buffer, format=format_name, **options)
    return buffer.getvalue()


def sent_png(body):
    uri = body["input"][0]
    prefix = "data:image/png;base64,"
    assert uri.startswith(prefix), uri[:40]
    return Image.open(BytesIO(base64.b64decode(uri[len(prefix):])))


class Siglip2Test(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.bundle = self.directory / "bundle"
        write_bundle(self.bundle)

    def matcher(self, vector, status=200, **entry):
        fake = FakeSiglip2(vector, status)
        self.addCleanup(fake.close)
        pipeline = {"name": "test-siglip2", "backend": "siglip2",
                    "bundle": str(self.bundle), "endpoint": fake.url}
        pipeline.update(entry)
        path = self.directory / "config.yaml"
        path.write_text(yaml.safe_dump({"matcher": {"pipeline": "test-siglip2"},
                                        "pipeline": [pipeline]}), encoding="utf-8")
        return load_matcher(path), fake

    def photo(self):
        return (DATA / "02eef911.webp").read_bytes()

    def test_the_best_full_view_cosine_wins_and_label_vectors_are_ignored(self):
        matcher, _ = self.matcher((0.1, 0.5, 0.9, 0))
        self.assertEqual(matcher.pipeline, "test-siglip2")
        self.assertEqual(matcher.predict(self.photo()), "wine-b")

    def test_an_image_of_two_wines_goes_to_the_smallest_slug(self):
        matcher, _ = self.matcher((0, 0, 0, 1))
        self.assertEqual(matcher.predict(self.photo()), "wine-shared-a")

    def test_the_request_uses_the_bundle_model_and_the_lab_steps(self):
        matcher, fake = self.matcher((1, 0, 0, 0))
        image = Image.new("RGBA", (2048, 1024), (200, 20, 20, 255))
        image.paste((0, 0, 0, 0), (0, 0, 1024, 1024))
        self.assertEqual(matcher.predict(image_bytes(image, "PNG")), "wine-a")

        self.assertEqual(len(fake.requests), 1)
        path, body = fake.requests[0]
        self.assertEqual(path, "/v1/embeddings")
        self.assertEqual(set(body), {"model", "input", "max_num_patches"})
        self.assertEqual(body["model"], MODEL)
        self.assertEqual(body["max_num_patches"], 512)
        self.assertEqual(len(body["input"]), 1)
        with sent_png(body) as sent:
            self.assertEqual(sent.mode, "RGB")
            self.assertEqual(sent.size, (1024, 512))
            self.assertEqual(sent.getpixel((100, 256)), (255, 255, 255))
            self.assertEqual(sent.getpixel((900, 256)), (200, 20, 20))

    def test_a_small_photo_keeps_its_size_and_its_exif_orientation(self):
        exif = Image.Exif()
        exif[0x0112] = 6
        photo = image_bytes(Image.new("RGB", (300, 200), (10, 120, 30)), "JPEG",
                            exif=exif.tobytes())
        with Image.open(BytesIO(model_input(photo))) as sent:
            self.assertEqual(sent.format, "PNG")
            self.assertEqual(sent.mode, "RGB")
            self.assertEqual(sent.size, (200, 300))

    def test_multiple_images_use_one_embedding_request(self):
        matcher, fake = self.matcher((1, 0, 0, 0))
        photo = image_bytes(Image.new("RGB", (20, 30), "red"), "PNG")
        vectors = matcher.backend.embed_many(
            [model_input(photo), model_input(photo)])
        self.assertEqual(len(vectors), 2)
        self.assertTrue(all(np.allclose(vector, unit((1, 0, 0, 0)))
                            for vector in vectors))
        self.assertEqual(len(fake.requests), 1)
        self.assertEqual(len(fake.requests[0][1]["input"]), 2)

    def test_a_large_image_batch_uses_bounded_embedding_requests(self):
        matcher, fake = self.matcher((1, 0, 0, 0))
        photo = image_bytes(Image.new("RGB", (20, 30), "red"), "PNG")
        vectors = matcher.backend.embed_many([photo] * 65)

        self.assertEqual(len(vectors), 65)
        self.assertEqual([len(request[1]["input"]) for request in fake.requests], [64, 1])
        self.assertTrue(all(np.allclose(vector, unit((1, 0, 0, 0)))
                            for vector in vectors))

    def test_an_endpoint_error_raises_siglip2_error(self):
        for vector, status, pattern in (
                ((1, 0, 0, 0), 500, "HTTP 500 from .*fake failure"),
                ((1, 0, 0), 200, "shape"),
                ((0, 0, 0, 0), 200, "length")):
            with self.subTest(status=status, vector=vector):
                matcher, _ = self.matcher(vector, status)
                with self.assertRaisesRegex(Siglip2Error, pattern):
                    matcher.predict(self.photo())

    def test_an_invalid_pipeline_entry_is_rejected(self):
        with mock.patch.dict(os.environ, {"MATCHER_TEST_SIGLIP2": ""}):
            for entry, pattern in (
                    ({"bundle": ""}, "bundle MUST be a non-empty path"),
                    ({"bundle": str(self.directory / "missing")}, "not a directory"),
                    ({"endpoint": "{env:MATCHER_TEST_SIGLIP2}"},
                     "MATCHER_TEST_SIGLIP2 MUST be set"),
                    ({"endpoint": "{env:MISSING_MATCHER_TEST_SIGLIP2}"},
                     "MISSING_MATCHER_TEST_SIGLIP2 MUST be set"),
                    ({"endpoint": "x{env:GOOD}"}, "exact \\{env:NAME\\} reference"),
                    ({"endpoint": "192.168.86.14:18081"}, "http:// or https://")):
                with self.subTest(entry=entry):
                    with self.assertRaisesRegex(ConfigError, pattern):
                        self.matcher((1, 0, 0, 0), **entry)

    def test_the_endpoint_environment_reference_is_resolved(self):
        fake = FakeSiglip2((0, 1, 0, 0))
        self.addCleanup(fake.close)
        with mock.patch.dict(os.environ, {"MATCHER_TEST_SIGLIP2": fake.url + "/"}):
            matcher, _ = self.matcher((1, 0, 0, 0),
                                      endpoint="{env:MATCHER_TEST_SIGLIP2}")
        self.assertEqual(matcher.predict(self.photo()), "wine-b")
        self.assertEqual(len(fake.requests), 1)

    def test_a_changed_or_unsupported_bundle_is_rejected(self):
        manifest_path = self.bundle / "manifest.json"
        original = manifest_path.read_text(encoding="utf-8")
        for change, pattern in (
                (lambda m: m.update(format_version=3), "unsupported bundle format"),
                (lambda m: m["files"]["vectors.npy"].update(sha256="0" * 64),
                 "vectors.npy does not match"),
                (lambda m: m["vectors"].update(shape=[3, 4]), "declared float32 shape"),
                (lambda m: m["embedding"].update(backend="local"), "openai embedding")):
            with self.subTest(pattern=pattern):
                manifest = json.loads(original)
                change(manifest)
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaisesRegex(ConfigError, pattern):
                    self.matcher((1, 0, 0, 0))
        manifest_path.write_text(original, encoding="utf-8")

        shutil.rmtree(self.bundle)
        write_bundle(self.bundle, rows=ROWS[2:3])
        with self.assertRaisesRegex(ConfigError, "no vector of the view full"):
            self.matcher((1, 0, 0, 0))

    def test_the_default_config_selects_the_siglip2_pipeline(self):
        config = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["matcher"], {
            "pipeline": "siglip2-p512-as-is",
            "output_dir": "{env:SVOE_VINO_MATCHER_OUTPUT_DIR}",
        })
        self.assertEqual(config["pipeline"], [{
            "name": "siglip2-p512-as-is",
            "backend": "siglip2",
            "bundle": "matcher/data/gx10-siglip2-so400m-patch16-naflex-p512",
            "endpoint": "{env:SIGLIP2_ENDPOINT}",
        }])


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


@unittest.skipUnless(all(shutil.which(tool) for tool in TOOLS),
                     "the official harness needs bash, curl, jq, and awk")
class Siglip2HarnessTest(unittest.TestCase):
    def test_the_official_harness_runs_the_siglip2_pipeline(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        write_bundle(root / "bundle")
        fake = FakeSiglip2((0.2, 1, 0, 0))
        self.addCleanup(fake.close)
        config = root / "config.yaml"
        config.write_text(yaml.safe_dump({
            "matcher": {"pipeline": "harness-siglip2",
                        "output_dir": str(root / "requests")},
            "pipeline": [{"name": "harness-siglip2", "backend": "siglip2",
                          "bundle": str(root / "bundle"),
                          "endpoint": "{env:SIGLIP2_ENDPOINT}"}],
        }), encoding="utf-8")
        environment = os.environ.copy()
        environment["SVOE_VINO_MATCHER_CONFIG"] = str(config)
        environment["SIGLIP2_ENDPOINT"] = fake.url
        port = free_port()
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "matcher.app:app",
             "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
            cwd=ROOT, env=environment, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True)
        self.addCleanup(self.stop, process)
        wait_for_server(process, port)

        health = subprocess.run(
            ["curl", "--silent", "--show-error", "--fail",
             "http://127.0.0.1:%d/healthz" % port],
            capture_output=True, text=True, timeout=10)
        output = root / "predictions.jsonl"
        completed = subprocess.run(
            ["bash", str(HARNESS), "--images-dir", str(DATA), "--manifest", str(MANIFEST),
             "--endpoint", "http://127.0.0.1:%d/v1/eval/predict" % port,
             "--output", str(output)],
            cwd=ROOT, capture_output=True, text=True, timeout=40)

        self.assertEqual(health.returncode, 0, health.stdout + health.stderr)
        self.assertEqual(json.loads(health.stdout),
                         {"status": "ok", "pipeline": "harness-siglip2"})
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        rows = [json.loads(line) for line in output.read_text().splitlines()]
        self.assertEqual([row["predicted_slug"] for row in rows], ["wine-b"] * 3)
        self.assertEqual(len(fake.requests), 3)
        self.assertEqual(len(list((root / "requests").rglob("request.json"))), 3)

    @staticmethod
    def stop(process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if process.stdout is not None:
            process.stdout.close()


if __name__ == "__main__":
    unittest.main()
