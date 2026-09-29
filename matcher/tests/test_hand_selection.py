"""Hand-aware single-image selection and strict isolation of shelf matching."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
from io import BytesIO
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

from matcher.group import GroupMatchError
from matcher.main_scene import TEXTS, rank_packages, select_main_package
from matcher.service import ConfigError, load_matcher
from test_group import FakeOpener, image_bytes, mask, sam3_answer
from test_match import TOKEN, multipart, write_bundle_v2, write_config
import test_siglip2
from test_siglip2 import FakeSiglip2, free_port, sent_png, wait_for_server


ROOT = Path(__file__).resolve().parents[2]
SIZE = (60, 40)


def instance(label, box, score=0.9, size=SIZE):
    return {"label": label, "box": list(box), "score": score,
            "area": (box[2] - box[0]) * (box[3] - box[1]),
            "mask_png_b64": mask(*size, box)}


def scene_answer():
    # Two equal packages. The hand overlaps only the right package.
    instances = [instance("wine bottle", (5, 5, 20, 35)),
                 instance("wine bottle", (40, 5, 55, 35)),
                 instance("hand", (38, 12, 58, 37))]
    return {"width": 60, "height": 40, "count": len(instances), "instances": instances}


def photo():
    image = Image.new("RGB", SIZE, "black")
    image.paste("red", (5, 5, 20, 35))
    image.paste("blue", (40, 5, 55, 35))
    return image_bytes(image, "PNG")


class HandSelectionTest(unittest.TestCase):
    def select(self, answer, source=None):
        opener = FakeOpener(json.dumps(answer).encode())
        result = select_main_package(source or photo(), "http://sam3.test", opener=opener)
        self.assertEqual(len(opener.requests), 1)
        self.assertIn(('name="text"\r\n\r\n%s\r\n' % TEXTS).encode(),
                      opener.requests[0][0].data)
        return result

    def test_hand_changes_the_selected_package_and_never_becomes_a_candidate(self):
        answer = scene_answer()
        image = Image.new("RGB", SIZE, "gray")
        without = rank_packages(image, answer["instances"][:2])
        with_hand = rank_packages(image, answer["instances"])
        self.assertIs(without[0], answer["instances"][0])
        self.assertIs(with_hand[0], answer["instances"][1])
        self.assertEqual(len(with_hand), 2)
        with Image.open(BytesIO(self.select(answer))) as crop:
            self.assertEqual((crop.format, crop.size, crop.mode), ("PNG", (15, 30), "RGB"))
            self.assertEqual(crop.getpixel((7, 10)), (0, 0, 255))

    def test_low_confidence_hand_does_not_change_selection(self):
        answer = scene_answer()
        answer["instances"][2]["score"] = 0.39
        ranked = rank_packages(Image.new("RGB", SIZE, "gray"), answer["instances"])
        self.assertIs(ranked[0], answer["instances"][0])

    def test_no_hand_uses_scene_ranking(self):
        packages = [instance("wine bottle", (1, 1, 8, 18), 0.99),
                    instance("wine bottle", (20, 2, 39, 38), 0.8)]
        self.assertIs(rank_packages(Image.new("RGB", SIZE), packages)[0], packages[1])

    def test_small_shelf_bottle_inside_hand_box_does_not_win(self):
        packages = [instance("can", (12, 2, 36, 37), 0.91),
                    instance("wine bottle", (46, 30, 49, 36), 0.99),
                    instance("hand", (8, 18, 55, 40), 0.97)]
        self.assertIs(rank_packages(Image.new("RGB", SIZE), packages)[0], packages[0])

    def test_background_outside_selected_mask_is_white(self):
        answer = scene_answer()
        answer["instances"][1]["mask_png_b64"] = mask(*SIZE, (43, 7, 52, 33), stray=True)
        with Image.open(BytesIO(self.select(answer))) as crop:
            self.assertEqual(crop.size, (15, 30))
            self.assertEqual(crop.getpixel((0, 0)), (255, 255, 255))
            self.assertEqual(crop.getpixel((5, 10)), (0, 0, 255))

    def test_empty_or_hand_only_detections_keep_original_bytes(self):
        for instances in ([], [scene_answer()["instances"][2]],
                          [instance("label", (10, 10, 20, 20))],
                          [instance("wine bottle", (5, 5, 20, 35), 0.39)]):
            with self.subTest(instances=len(instances)):
                answer = dict(scene_answer(), instances=instances, count=len(instances))
                self.assertEqual(self.select(answer), photo())

    def test_empty_mask_tries_next_package_then_original(self):
        answer = scene_answer()
        empty = mask(*SIZE, (0, 0, 0, 0))
        answer["instances"][1]["mask_png_b64"] = empty
        with Image.open(BytesIO(self.select(answer))) as crop:
            self.assertEqual(crop.getpixel((7, 10)), (255, 0, 0))
        answer["instances"][0]["mask_png_b64"] = empty
        self.assertEqual(self.select(answer), photo())

    def test_exif_orientation_and_segmentation_size_limit(self):
        exif = Image.Exif()
        exif[0x0112] = 6
        source = image_bytes(Image.new("RGB", (2000, 1000)), "JPEG", exif=exif.tobytes())
        answer = {"width": 800, "height": 1600, "count": 0, "instances": []}
        self.assertEqual(self.select(answer, source), source)

    def test_invalid_labels_areas_and_masks_are_explicit_errors(self):
        for field, value in (("label", None), ("label", ""), ("area", float("nan")),
                             ("area", -1), ("area", True), ("area", 2401),
                             ("mask_png_b64", "not-base64"),
                             ("mask_png_b64", mask(2, 2, (0, 0, 2, 2)))):
            with self.subTest(field=field, value=str(value)[:20]):
                answer = scene_answer()
                answer["instances"][1][field] = value
                with self.assertRaises(GroupMatchError) as caught:
                    self.select(answer)
                self.assertEqual(caught.exception.status_code, 502)

    def test_timeout_returns_504_and_has_bounded_retries(self):
        opener = mock.Mock()
        opener.open.side_effect = TimeoutError()
        with self.assertRaises(GroupMatchError) as caught:
            select_main_package(photo(), "http://sam3.test", opener=opener)
        self.assertEqual(caught.exception.status_code, 504)
        self.assertEqual(opener.open.call_count, 2)


class HandSelectionConfigTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        write_bundle_v2(self.root / "bundle")
        self.pipeline = {"name": "hand-test", "backend": "siglip2",
                         "bundle": str(self.root / "bundle"),
                         "endpoint": "http://embedding.test"}

    def matcher(self, **entry):
        pipeline = dict(self.pipeline, **entry)
        return load_matcher(write_config(self.root / "config.yaml", pipeline))

    def test_default_and_explicit_booleans(self):
        self.assertFalse(self.matcher().hand_selection)
        self.assertFalse(self.matcher(hand_selection=False).hand_selection)
        self.assertTrue(self.matcher(hand_selection=True).hand_selection)

    def test_non_boolean_values_and_enabled_mock_are_rejected(self):
        for value in (None, 0, 1, "true", "false", {}, []):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ConfigError, "hand_selection MUST be a boolean"):
                    self.matcher(hand_selection=value)
        with self.assertRaisesRegex(ConfigError, "hand_selection requires backend siglip2"):
            self.matcher(hand_selection=True, backend="mock", answers={})

    def test_default_single_routes_do_not_call_selector(self):
        matcher = self.matcher()
        with mock.patch("matcher.service.select_main_package") as selector, \
                mock.patch.object(type(matcher.backend), "embed", return_value=[1, 0, 0, 0]):
            self.assertEqual(matcher.predict(photo()), "wine-a")
            self.assertEqual(matcher.match(photo(), 1)[0][0], "wine-a")
        selector.assert_not_called()

    def test_enabled_single_methods_share_the_selector(self):
        matcher = self.matcher(hand_selection=True)
        with mock.patch.dict(os.environ, {"SAM3_ENDPOINT": "http://sam3.test"}), \
                mock.patch("matcher.service.select_main_package", return_value=photo()) as selector, \
                mock.patch.object(type(matcher.backend), "embed", return_value=[1, 0, 0, 0]):
            self.assertEqual(matcher.predict(photo()), "wine-a")
            self.assertEqual(matcher.match(photo(), 1)[0][0], "wine-a")
        self.assertEqual(selector.call_args_list,
                         [mock.call(photo(), "http://sam3.test")] * 2)

    def test_enabled_batch_never_calls_selector_and_keeps_all_inputs(self):
        matcher = self.matcher(hand_selection=True)
        with mock.patch("matcher.service.select_main_package") as selector, \
                mock.patch.object(type(matcher.backend), "embed_many",
                                  return_value=[[1, 0, 0, 0]] * 3) as embed:
            self.assertEqual(len(matcher.match_many([photo()] * 3, 1)), 3)
        selector.assert_not_called()
        self.assertEqual(len(embed.call_args.args[0]), 3)


class FakeHandSam3:
    """A local endpoint that distinguishes single-image and group prompts."""

    def __init__(self):
        self.requests = []
        self.answer = scene_answer()
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                fake.requests.append(body)
                answer = fake.answer if TEXTS.encode() in body else sam3_answer()
                payload = json.dumps(answer).encode()
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
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class HandSelectionEndpointTest(unittest.TestCase):
    def start(self, sam3_endpoint, enabled=True, embedding_status=200):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        write_bundle_v2(root / "bundle")
        embedding = FakeSiglip2((1, 0, 0, 0), status=embedding_status)
        self.addCleanup(embedding.close)
        pipeline = {"name": "hand-test", "backend": "siglip2", "hand_selection": enabled,
                    "bundle": str(root / "bundle"), "endpoint": embedding.url}
        config = write_config(root / "config.yaml", pipeline, token=True)
        environment = dict(os.environ, SVOE_VINO_MATCHER_CONFIG=str(config),
                           SVOE_VINO_MATCHER_TOKEN=TOKEN)
        environment.pop("SAM3_ENDPOINT", None)
        if sam3_endpoint is not None:
            environment["SAM3_ENDPOINT"] = sam3_endpoint
        port = free_port()
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "matcher.app:app",
             "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
            cwd=ROOT, env=environment, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True)
        self.addCleanup(test_siglip2.Siglip2HarnessTest.stop, process)
        wait_for_server(process, port)
        return port, root, embedding

    def post(self, port, path, token=TOKEN):
        payload, content_type = multipart(photo())
        headers = {"Content-Type": content_type}
        if token:
            headers["Authorization"] = "Bearer %s" % token
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        try:
            connection.request("POST", path, body=payload, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def get(self, port, path):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def sam3(self):
        sam3 = FakeHandSam3()
        self.addCleanup(sam3.close)
        return sam3

    def test_both_single_endpoints_embed_the_held_package(self):
        sam3 = self.sam3()
        port, _, embedding = self.start(sam3.url)
        for path in ("/v1/eval/predict", "/v1/match"):
            with self.subTest(path=path):
                status, answer = self.post(port, path)
                self.assertEqual(status, 200, answer)
                with sent_png(embedding.requests[-1][1]) as image:
                    self.assertEqual(image.size, (15, 30))
                    self.assertEqual(image.getpixel((7, 10)), (0, 0, 255))
        self.assertEqual(len(sam3.requests), 2)
        self.assertEqual(len(embedding.requests), 2)

    def test_readiness_checks_siglip2_and_configured_hand_selection(self):
        sam3 = self.sam3()
        port, _, embedding = self.start(sam3.url)

        status, answer = self.get(port, "/readyz")

        self.assertEqual(status, 200, answer)
        self.assertEqual(answer, {"status": "ok", "pipeline": "hand-test"})
        self.assertEqual(len(sam3.requests), 1)
        self.assertEqual(len(embedding.requests), 1)

    def test_readiness_does_not_require_sam3_when_hand_selection_is_disabled(self):
        port, _, embedding = self.start(None, enabled=False)

        status, answer = self.get(port, "/readyz")

        self.assertEqual(status, 200, answer)
        self.assertEqual(answer, {"status": "ok", "pipeline": "hand-test"})
        self.assertEqual(len(embedding.requests), 1)

    def test_readiness_returns_503_when_a_required_dependency_fails(self):
        port, _, embedding = self.start(None, enabled=False, embedding_status=500)

        health_status, health = self.get(port, "/healthz")
        status, answer = self.get(port, "/readyz")

        self.assertEqual(health_status, 200, health)
        self.assertEqual(status, 503, answer)
        self.assertEqual(answer["detail"], "SigLIP2 service returned HTTP 500")
        self.assertEqual(len(embedding.requests), 1)

    def test_group_ignores_enabled_hand_selection_and_embeds_every_bottle(self):
        sam3 = self.sam3()
        port, _, embedding = self.start(sam3.url)
        status, answer = self.post(port, "/v1/group/match")
        self.assertEqual(status, 200, answer)
        self.assertEqual(len(answer["bottles"]), 2)
        self.assertEqual(answer["detected_count"], 3)
        self.assertTrue(all(bottle["match"]["slug"] == "wine-a" for bottle in answer["bottles"]))
        self.assertEqual(len(sam3.requests), 1)
        self.assertIn(b'name="text"\r\n\r\nwine bottle\r\n', sam3.requests[0])
        self.assertNotIn(b", hand", sam3.requests[0])
        self.assertEqual(len(embedding.requests), 1)
        self.assertEqual(len(embedding.requests[0][1]["input"]), 2)

    def test_disabled_option_needs_no_sam3_and_keeps_full_photo(self):
        port, _, embedding = self.start(None, enabled=False)
        for path in ("/v1/eval/predict", "/v1/match"):
            self.assertEqual(self.post(port, path)[0], 200)
            with sent_png(embedding.requests[-1][1]) as image:
                self.assertEqual(image.size, SIZE)

    def test_missing_sam3_is_503_on_both_routes_and_in_audit(self):
        port, root, embedding = self.start(None)
        status, answer = self.get(port, "/readyz")
        self.assertEqual(status, 503, answer)
        self.assertIn("SAM3_ENDPOINT", answer["detail"])
        for path in ("/v1/eval/predict", "/v1/match"):
            status, answer = self.post(port, path)
            self.assertEqual(status, 503, answer)
            self.assertIn("SAM3_ENDPOINT", answer["detail"])
        self.assertEqual(embedding.requests, [])
        records = [json.loads(path.read_text())
                   for path in (root / "requests").rglob("request.json")]
        self.assertEqual(len(records), 2)
        self.assertTrue(all(record["response"]["status_code"] == 503 for record in records))

    def test_invalid_sam3_is_502_without_embedding_or_silent_fallback(self):
        sam3 = self.sam3()
        sam3.answer["instances"][1]["mask_png_b64"] = "broken"
        port, _, embedding = self.start(sam3.url)
        for path in ("/v1/eval/predict", "/v1/match"):
            status, answer = self.post(port, path)
            self.assertEqual(status, 502, answer)
        self.assertEqual(embedding.requests, [])

    def test_siglip2_failure_is_502_on_both_routes_and_in_audit(self):
        port, root, embedding = self.start(None, enabled=False, embedding_status=500)
        for path in ("/v1/eval/predict", "/v1/match"):
            status, answer = self.post(port, path)
            self.assertEqual(status, 502, answer)
            self.assertEqual(answer["detail"], "SigLIP2 service returned HTTP 500")
        self.assertEqual(len(embedding.requests), 2)
        records = [json.loads(path.read_text())
                   for path in (root / "requests").rglob("request.json")]
        self.assertEqual(len(records), 2)
        self.assertTrue(all(record["response"]["status_code"] == 502
                            for record in records))
        self.assertTrue(all(record["response"]["error_type"] == "Siglip2Error"
                            for record in records))

    def test_unauthorized_single_requests_do_not_reach_sam3(self):
        sam3 = self.sam3()
        port, _, embedding = self.start(sam3.url)
        for path in ("/v1/eval/predict", "/v1/match"):
            self.assertEqual(self.post(port, path, token=None)[0], 401)
        self.assertEqual(sam3.requests, [])
        self.assertEqual(embedding.requests, [])


if __name__ == "__main__":
    unittest.main()
