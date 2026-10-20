"""Tests of the VLM service keys of the re-rank: `rerank.key`, `rerank.thinking_field`,
and `rerank.format`.

A cloud VLM (the QwenCloud Token Plan) needs a bearer key and takes the thinking switch
at the top level of the body. The gx10 gateway needs no key and takes the switch in
`chat_template_kwargs`. The defaults keep the gateway form.
"""

import asyncio
from io import BytesIO
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
from time import perf_counter
import unittest
from unittest import mock

from PIL import Image

from matcher import rerank
from matcher.service import ConfigError, load_matcher
from matcher.services import Services

from cascade_fakes import FakeServices
from test_cascade_api import entry, write_cascade_catalog, write_config


KEY_VARIABLE = "SVM_TEST_VLM_KEY"
KEY_VALUE = "test-key-0123"
RULE = {"mode": "verdict", "letters": {"A": "wine-a", "B": "wine-b"},
        "rule": "The year tells the wines apart."}


class HeaderServer:
    """A chat route that records the headers and the body of each request."""

    def __init__(self):
        self.requests = []
        recorder = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                recorder.requests.append({"path": self.path, "headers": dict(self.headers),
                                          "body": json.loads(body)})
                answer = json.dumps({"choices": [{"message": {"content": '{"wine": "A"}'},
                                                  "finish_reason": "stop"}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(answer)))
                self.end_headers()
                self.wfile.write(answer)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d/v1" % self.server.server_address[1]

    def close(self):
        self.server.shutdown()
        self.server.server_close()


async def one_chat(services, payload):
    await services.start()
    try:
        return await services.chat(payload, deadline=perf_counter() + 5)
    finally:
        await services.close()


class PayloadTest(unittest.TestCase):
    def test_the_default_puts_the_switch_into_chat_template_kwargs(self):
        body = rerank.payload(RULE, b"png", "m", 256, {}, {})
        self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
        self.assertNotIn("enable_thinking", body)

    def test_top_level_puts_the_switch_at_the_top(self):
        body = rerank.payload(RULE, b"png", "m", 256, {}, {}, "top_level")
        self.assertIs(body["enable_thinking"], False)
        self.assertNotIn("chat_template_kwargs", body)

    def test_the_field_does_not_change_the_rest_of_the_body(self):
        default = rerank.payload(RULE, b"png", "m", 256, {}, {})
        top = rerank.payload(RULE, b"png", "m", 256, {}, {}, "top_level")
        default.pop("chat_template_kwargs")
        top.pop("enable_thinking")
        self.assertEqual(default, top)


class PictureTest(unittest.TestCase):
    def png(self):
        output = BytesIO()
        Image.new("RGB", (64, 48), (200, 30, 30)).save(output, "PNG")
        return output.getvalue()

    def test_a_png_gets_the_png_media_type(self):
        self.assertTrue(rerank.data_url(self.png()).startswith("data:image/png;base64,"))

    def test_jpeg_of_gives_a_jpeg_of_the_same_size(self):
        jpeg = rerank.jpeg_of(self.png())
        self.assertEqual(jpeg[:2], b"\xff\xd8")
        self.assertTrue(rerank.data_url(jpeg).startswith("data:image/jpeg;base64,"))
        with Image.open(BytesIO(jpeg)) as image:
            self.assertEqual(image.size, (64, 48))


class HeaderTest(unittest.TestCase):
    def setUp(self):
        self.server = HeaderServer()
        self.addCleanup(self.server.close)

    def test_a_key_is_sent_as_a_bearer_header(self):
        asyncio.run(one_chat(Services(vlm=self.server.url, vlm_key=KEY_VALUE), {"x": 1}))
        headers = self.server.requests[0]["headers"]
        self.assertEqual(headers["Authorization"], "Bearer " + KEY_VALUE)
        self.assertEqual(self.server.requests[0]["path"], "/v1/chat/completions")

    def test_no_key_sends_no_authorization_header(self):
        asyncio.run(one_chat(Services(vlm=self.server.url), {"x": 1}))
        self.assertNotIn("Authorization", self.server.requests[0]["headers"])


class ConfigTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.catalog = write_cascade_catalog(self.root / "catalog")
        self.fake = FakeServices()
        self.addCleanup(self.fake.close)

    def load(self, **rerank_changes):
        pipeline = entry(self.catalog, self.fake)
        pipeline["rerank"].update(rerank_changes)
        path = self.root / "config.yaml"
        write_config(path, pipeline)
        return load_matcher(path)

    def test_the_defaults_keep_the_gateway_form(self):
        matcher = self.load()
        self.assertEqual(matcher.cascade.config.rerank.thinking_field,
                         "chat_template_kwargs")
        self.assertNotIn("Authorization", matcher.cascade.services.vlm_headers)

    def test_a_key_reference_and_top_level_are_read(self):
        with mock.patch.dict("os.environ", {KEY_VARIABLE: KEY_VALUE}):
            matcher = self.load(thinking_field="top_level",
                                key="{env:%s}" % KEY_VARIABLE)
        self.assertEqual(matcher.cascade.config.rerank.thinking_field, "top_level")
        self.assertEqual(matcher.cascade.services.vlm_headers["Authorization"],
                         "Bearer " + KEY_VALUE)
        self.assertNotIn(KEY_VALUE, repr(matcher.cascade.config))

    def test_a_null_key_needs_no_variable(self):
        matcher = self.load(key=None)
        self.assertNotIn("Authorization", matcher.cascade.services.vlm_headers)

    def test_a_key_value_in_the_file_is_refused(self):
        with self.assertRaisesRegex(ConfigError, r"key MUST be an exact \{env:NAME\}"):
            self.load(key=KEY_VALUE)

    def test_a_missing_key_variable_is_refused(self):
        environ = {k: v for k, v in os.environ.items() if k != KEY_VARIABLE}
        with mock.patch.dict("os.environ", environ, clear=True):
            with self.assertRaisesRegex(ConfigError, "%s MUST be set" % KEY_VARIABLE):
                self.load(key="{env:%s}" % KEY_VARIABLE)

    def test_an_unknown_thinking_field_is_refused(self):
        with self.assertRaisesRegex(ConfigError, "thinking_field MUST be one of"):
            self.load(thinking_field="body")

    def test_the_picture_format_is_png_by_default_and_jpg_on_request(self):
        self.assertEqual(self.load().cascade.config.rerank.format, "png")
        self.assertEqual(self.load(format="jpg").cascade.config.rerank.format, "jpg")

    def test_an_unknown_picture_format_is_refused(self):
        with self.assertRaisesRegex(ConfigError, "format MUST be png or jpg"):
            self.load(format="webp")


if __name__ == "__main__":
    unittest.main()
