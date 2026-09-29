"""Tests for shelf segmentation and POST /v1/group/match."""

import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

from PIL import Image

from matcher.group import GroupMatchError, segment_group
import test_siglip2
from test_match import TOKEN, multipart, write_bundle_v2, write_config
from test_siglip2 import free_port, wait_for_server


ROOT = Path(__file__).resolve().parents[2]


def image_bytes(image, format_name="JPEG", **options):
    output = BytesIO()
    image.save(output, format_name, **options)
    return output.getvalue()


def mask(width, height, box, stray=False):
    image = Image.new("L", (width, height), 0)
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            image.putpixel((x, y), 255)
    if stray:
        image.putpixel((width - 1, height - 1), 255)
    return base64.b64encode(image_bytes(image, "PNG")).decode("ascii")


def sam3_answer(width=60, height=40):
    instances = [
        {"label": "wine bottle", "score": 0.8, "box": [-2, 3, 15, 34],
         "mask_png_b64": mask(width, height, (0, 4, 14, 33), stray=True)},
        {"label": "wine bottle", "score": 0.9, "box": [35, 2, 54, 35],
         "mask_png_b64": mask(width, height, (36, 3, 53, 34))},
        {"label": "wine bottle", "score": 0.7, "box": [35.1, 2.1, 54.1, 35.1],
         "mask_png_b64": mask(width, height, (36, 3, 53, 34))},
        {"label": "wine label", "score": 0.88, "box": [2, 15, 12, 27],
         "mask_png_b64": mask(width, height, (2, 15, 12, 27))},
        {"label": "wine label", "score": 0.91, "box": [38, 16, 51, 29],
         "mask_png_b64": mask(width, height, (38, 16, 51, 29))},
    ]
    return {"width": width, "height": height,
            "count": len(instances), "instances": instances}


class FakeResponse:
    def __init__(self, body):
        self.body = body
        self.headers = {"Content-Length": str(len(body))}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.body[:limit]


class FakeOpener:
    def __init__(self, *bodies):
        self.bodies = list(bodies)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        return FakeResponse(self.bodies.pop(0))


class GroupSegmentationTest(unittest.TestCase):
    def photo(self):
        return image_bytes(Image.new("RGB", (60, 40), (220, 30, 20)))

    def opener(self, answer=None):
        payload = json.dumps(answer or sam3_answer()).encode("utf-8")
        return FakeOpener(payload)

    def test_normalized_boxes_cropped_masks_deduplication_and_order(self):
        opener = self.opener()
        result = segment_group(self.photo(), "http://sam3.test/base", opener=opener)
        self.assertEqual((result.width, result.height), (60, 40))
        self.assertEqual(result.detected_count, 3)
        self.assertFalse(result.truncated)
        self.assertEqual([bottle.id for bottle in result.bottles], ["b1", "b2"])
        self.assertEqual([bottle.segmentation_score for bottle in result.bottles],
                         [0.8, 0.9])
        self.assertEqual(result.bottles[0].box, (0, 3 / 40, 15 / 60, 34 / 40))
        self.assertEqual(result.bottles[1].box, (35 / 60, 2 / 40, 54 / 60, 35 / 40))

        request, timeout = opener.requests[0]
        self.assertEqual(request.full_url, "http://sam3.test/base/segment_multi")
        self.assertGreater(timeout, 0)
        self.assertIn(
            b'name="texts"\r\n\r\nwine bottle, wine label', request.data)
        self.assertIn(b'name="threshold"\r\n\r\n0.4', request.data)
        self.assertIn(b'name="mask_threshold"\r\n\r\n0.5', request.data)
        self.assertIn(b'name="return_masks"\r\n\r\ntrue', request.data)

        preview = base64.b64decode(result.preview.split(",", 1)[1])
        with Image.open(BytesIO(preview)) as image:
            self.assertEqual((image.format, image.size, image.mode),
                             ("JPEG", (60, 40), "RGB"))
            self.assertFalse(image.getexif())
        first_mask = base64.b64decode(result.bottles[0].mask.split(",", 1)[1])
        with Image.open(BytesIO(first_mask)) as image:
            self.assertEqual((image.format, image.size, image.mode),
                             ("PNG", (15, 31), "RGBA"))
            self.assertEqual(image.getpixel((14, 30))[3], 0)
            self.assertEqual(image.getpixel((1, 1))[3], 255)
        with Image.open(BytesIO(result.bottles[0].crop)) as crop:
            self.assertEqual(crop.format, "JPEG")
            self.assertEqual(crop.mode, "RGB")
            red, green, blue = crop.getpixel((0, 0))
            self.assertGreater(red, 240)
            self.assertGreater(green, 240)
            self.assertGreater(blue, 240)
        with Image.open(BytesIO(result.bottles[0].label_crop)) as label_crop:
            self.assertEqual(label_crop.format, "JPEG")
            self.assertEqual(label_crop.mode, "RGB")
            self.assertGreater(label_crop.width, 10)
            self.assertGreater(label_crop.height, 12)

    def test_bottles_without_a_usable_label_are_not_returned(self):
        answer = sam3_answer()
        answer["instances"] = [
            instance for instance in answer["instances"]
            if instance["label"] == "wine bottle"
        ]
        answer["count"] = len(answer["instances"])
        result = segment_group(
            self.photo(), "http://sam3.test", opener=self.opener(answer))
        self.assertEqual(result.detected_count, 3)
        self.assertEqual(result.bottles, ())

    def test_tiny_and_outside_labels_are_not_usable(self):
        width = height = 100
        instances = [
            {"label": "wine bottle", "score": 0.9, "box": [10, 5, 45, 95],
             "mask_png_b64": mask(width, height, (10, 5, 45, 95))},
            {"label": "wine label", "score": 0.9, "box": [20, 50, 21, 51],
             "mask_png_b64": mask(width, height, (20, 50, 21, 51))},
            {"label": "wine label", "score": 0.9, "box": [60, 45, 80, 65],
             "mask_png_b64": mask(width, height, (60, 45, 80, 65))},
        ]
        answer = {"width": width, "height": height,
                  "count": len(instances), "instances": instances}
        photo = image_bytes(Image.new("RGB", (width, height), "red"))
        result = segment_group(
            photo, "http://sam3.test", opener=self.opener(answer))
        self.assertEqual(result.detected_count, 1)
        self.assertEqual(result.bottles, ())

    def test_rear_scale_and_bottom_edge_fragments_are_filtered(self):
        width = height = 100
        instances = [
            {"label": "wine bottle", "score": 0.95, "box": [5, 10, 35, 80],
             "mask_png_b64": mask(width, height, (5, 10, 35, 80))},
            {"label": "wine label", "score": 0.95, "box": [10, 50, 30, 70],
             "mask_png_b64": mask(width, height, (10, 50, 30, 70))},
            {"label": "wine bottle", "score": 0.85, "box": [45, 12, 60, 37],
             "mask_png_b64": mask(width, height, (45, 12, 60, 37))},
            {"label": "wine label", "score": 0.85, "box": [48, 24, 57, 33],
             "mask_png_b64": mask(width, height, (48, 24, 57, 33))},
            {"label": "wine bottle", "score": 0.9, "box": [70, 88, 95, 100],
             "mask_png_b64": mask(width, height, (70, 88, 95, 100))},
            {"label": "wine label", "score": 0.9, "box": [75, 91, 90, 99],
             "mask_png_b64": mask(width, height, (75, 91, 90, 99))},
        ]
        answer = {"width": width, "height": height,
                  "count": len(instances), "instances": instances}
        photo = image_bytes(Image.new("RGB", (width, height), "red"))
        result = segment_group(
            photo, "http://sam3.test", opener=self.opener(answer))
        self.assertEqual(result.detected_count, 3)
        self.assertEqual(len(result.bottles), 1)
        self.assertEqual(result.bottles[0].box, (0.05, 0.1, 0.35, 0.8))

    def test_exif_orientation_is_applied_before_sam3(self):
        exif = Image.Exif()
        exif[0x0112] = 6
        photo = image_bytes(Image.new("RGB", (30, 20), "red"), "JPEG",
                            exif=exif.tobytes())
        answer = {"width": 20, "height": 30, "count": 0, "instances": []}
        result = segment_group(photo, "http://sam3.test", opener=self.opener(answer))
        self.assertEqual((result.width, result.height), (20, 30))
        self.assertEqual(result.bottles, ())

    def test_a_multi_picture_jpeg_uses_its_first_frame(self):
        first = Image.new("RGB", (4, 3), "red")
        second = Image.new("RGB", (4, 3), "blue")
        photo = test_siglip2.mpo_bytes(first, second)
        answer = {"width": 4, "height": 3, "count": 0, "instances": []}
        result = segment_group(photo, "http://sam3.test", opener=self.opener(answer))
        preview = base64.b64decode(result.preview.split(",", 1)[1])
        with Image.open(BytesIO(preview)) as sent:
            red, green, blue = sent.getpixel((0, 0))
            self.assertGreater(red, 240)
            self.assertLess(green, 10)
            self.assertLess(blue, 10)

    def test_empty_response_is_retried_once(self):
        payload = json.dumps(sam3_answer()).encode("utf-8")
        opener = FakeOpener(b"", payload)
        result = segment_group(self.photo(), "http://sam3.test", opener=opener)
        self.assertEqual(len(result.bottles), 2)
        self.assertEqual(len(opener.requests), 2)

    def test_invalid_endpoints_and_service_data_are_rejected(self):
        for endpoint in (None, "", "sam3.test", "http://sam3.test:bad",
                         "http://user:secret@sam3.test"):
            with self.subTest(endpoint=endpoint):
                with self.assertRaisesRegex(GroupMatchError, "SAM3_ENDPOINT") as caught:
                    segment_group(self.photo(), endpoint, opener=self.opener())
                self.assertEqual(caught.exception.status_code, 503)

        bad = sam3_answer()
        bad["instances"][0]["mask_png_b64"] = mask(10, 10, (1, 1, 5, 8))
        with self.assertRaisesRegex(GroupMatchError, "mask dimensions") as caught:
            segment_group(self.photo(), "http://sam3.test", opener=self.opener(bad))
        self.assertEqual(caught.exception.status_code, 502)

    def test_bottle_and_media_limits_report_truncation(self):
        with mock.patch("matcher.group.MAX_BOTTLES", 1):
            result = segment_group(
                self.photo(), "http://sam3.test", opener=self.opener())
        self.assertEqual(len(result.bottles), 1)
        self.assertTrue(result.truncated)

        with mock.patch("matcher.group.MAX_RESPONSE_MEDIA_BYTES", 1):
            result = segment_group(
                self.photo(), "http://sam3.test", opener=self.opener())
        self.assertEqual(len(result.bottles), 0)
        self.assertTrue(result.truncated)


class FakeSam3:
    """A local SAM3-compatible endpoint for the API integration test."""

    def __init__(self):
        self.requests = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                fake.requests.append((self.path, self.headers, body))
                payload = json.dumps(sam3_answer()).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:%d/upstream/sam3" % self.server.server_address[1]

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class GroupEndpointTest(unittest.TestCase):
    def start(self, sam3_endpoint, token=True):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        write_bundle_v2(root / "bundle")
        pipeline = {"name": "group-mock", "backend": "mock", "answers": {},
                    "bundle": str(root / "bundle")}
        config = write_config(root / "config.yaml", pipeline, token)
        environment = os.environ.copy()
        environment["SVOE_VINO_MATCHER_CONFIG"] = str(config)
        environment["SVOE_VINO_MATCHER_TOKEN"] = TOKEN
        if sam3_endpoint is None:
            environment.pop("SAM3_ENDPOINT", None)
        else:
            environment["SAM3_ENDPOINT"] = sam3_endpoint
        port = free_port()
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "matcher.app:app",
             "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
            cwd=ROOT, env=environment, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True)
        self.addCleanup(test_siglip2.Siglip2HarnessTest.stop, process)
        wait_for_server(process, port)
        return port, root

    def post(self, port, token=TOKEN, query=""):
        photo = image_bytes(Image.new("RGB", (60, 40), (220, 30, 20)))
        payload, content_type = multipart(photo)
        headers = {"Content-Type": content_type}
        if token:
            headers["Authorization"] = "Bearer %s" % token
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        try:
            connection.request("POST", "/v1/group/match" + query, body=payload,
                               headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read() or b"null")
        finally:
            connection.close()

    def test_group_endpoint_returns_masks_coordinates_and_wine_cards(self):
        sam3 = FakeSam3()
        self.addCleanup(sam3.close)
        port, root = self.start(sam3.url)
        status, answer = self.post(port)
        self.assertEqual(status, 200, answer)
        self.assertEqual(set(answer), {
            "pipeline", "latency_ms", "image", "detected_count", "truncated", "bottles"})
        self.assertEqual(answer["pipeline"], "group-mock")
        self.assertEqual(answer["image"]["width"], 60)
        self.assertEqual(answer["image"]["height"], 40)
        self.assertTrue(answer["image"]["preview"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(answer["detected_count"], 3)
        self.assertFalse(answer["truncated"])
        self.assertEqual([bottle["id"] for bottle in answer["bottles"]], ["b1", "b2"])
        for bottle in answer["bottles"]:
            self.assertEqual(set(bottle), {
                "id", "segmentation_score", "box", "mask", "match", "candidates"})
            self.assertTrue(bottle["mask"].startswith("data:image/png;base64,"))
            self.assertEqual(bottle["match"]["rank"], 1)
            self.assertEqual(bottle["candidates"], [bottle["match"]])
            self.assertIn("name", bottle["match"]["wine"])
            self.assertIn("page_url", bottle["match"]["wine"])
        self.assertEqual(len(sam3.requests), 1)
        self.assertEqual(sam3.requests[0][0], "/upstream/sam3/segment_multi")

        records = [json.loads(path.read_text(encoding="utf-8"))
                   for path in (root / "requests").rglob("request.json")]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["response"]["detected_count"], 3)
        self.assertEqual(records[0]["response"]["matched_count"], 2)
        self.assertEqual(records[0]["response"]["unmatched_count"], 0)
        self.assertEqual(len(records[0]["response"]["bottles"]), 2)

        self.assertEqual(self.post(port, token=None)[0], 401)

    def test_group_endpoint_returns_k_candidates_for_each_bottle(self):
        sam3 = FakeSam3()
        self.addCleanup(sam3.close)
        port, _root = self.start(sam3.url)
        status, answer = self.post(port, query="?k=3")
        self.assertEqual(status, 200, answer)
        self.assertEqual(len(answer["bottles"]), 2)
        for bottle in answer["bottles"]:
            candidates = bottle["candidates"]
            self.assertEqual([c["rank"] for c in candidates], [1, 2, 3])
            self.assertEqual(len({c["slug"] for c in candidates}), 3)
            scores = [c["score"] for c in candidates]
            self.assertEqual(scores, sorted(scores, reverse=True))
            self.assertEqual(candidates[0], bottle["match"])
            self.assertIn("name", candidates[2]["wine"])
        # The test bundle has 5 wines with a card, so a larger k gives 5 candidates.
        status, answer = self.post(port, query="?k=20")
        self.assertEqual(status, 200, answer)
        self.assertEqual([len(b["candidates"]) for b in answer["bottles"]], [5, 5])
        for query in ("?k=0", "?k=21", "?k=x"):
            self.assertEqual(self.post(port, query=query)[0], 422, query)

    def test_group_endpoint_requires_sam3(self):
        port, root = self.start(None, token=False)
        status, answer = self.post(port, token=None)
        self.assertEqual(status, 503, answer)
        self.assertIn("SAM3_ENDPOINT", answer["detail"])
        records = [json.loads(path.read_text(encoding="utf-8"))
                   for path in (root / "requests").rglob("request.json")]
        self.assertEqual(records[0]["response"]["status_code"], 503)


if __name__ == "__main__":
    unittest.main()
