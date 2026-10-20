"""OCR wire contracts and cancellation. All HTTP responses use a local transport."""

import asyncio
import base64
import json
from time import perf_counter
import unittest
from unittest.mock import patch

import httpx

from matcher.ocr import (OCRError, Reader, config, generic_result, paddle_result,
                         tesseract_result)
from matcher.services import Services


TSV = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
       "5\t1\t1\t1\t1\t1\t10\t20\t30\t40\t90\tCabernet\n")


class ReaderTests(unittest.IsolatedAsyncioTestCase):
    async def make_reader(self, options, answer, status=200):
        self.requests = []
        async def handler(request):
            self.requests.append(request)
            return httpx.Response(status, json=answer)
        services = Services()
        services.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        self.addAsyncCleanup(services.close)
        return Reader(config(options), services)

    async def test_paddle_wire_and_confidence_filter(self):
        reader = await self.make_reader({"backend": "paddleocr", "endpoint": "http://ocr/ocr",
            "min_confidence": .8}, {"errorCode": 0, "result": {"ocrResults": [{"prunedResult": {
                "rec_texts": ["Cabernet", "noise"], "rec_scores": [.95, .2],
                "rec_boxes": [[1, 2, 30, 40], [40, 2, 70, 40]]}}]}})
        result = await reader.read(b"test image", perf_counter() + 1)
        self.assertEqual(result.text, "Cabernet")
        self.assertEqual(result.words[0].box, (1, 2, 30, 40))
        payload = json.loads(self.requests[0].content)
        self.assertEqual(payload, {"file": base64.b64encode(b"test image").decode(),
                                   "fileType": 1, "visualize": False})
        self.assertTrue((await reader.read(b"test image", perf_counter() + 1)).cached)
        self.assertEqual(len(self.requests), 1)

    async def test_vlm_transcribes_without_candidate_names_and_rejects_truncation(self):
        reader = await self.make_reader({"backend": "vlm", "endpoint": "http://vlm/v1",
            "model": "test-vlm"}, {"choices": [{"message": {"content": '{"text":"Estate"}'},
                                                "finish_reason": "stop"}]})
        result = await reader.read(b"image", perf_counter() + 1)
        self.assertEqual(result.text, "Estate")
        request = self.requests[0]
        self.assertEqual(request.url.path, "/v1/chat/completions")
        payload = json.loads(request.content)
        self.assertEqual(payload["response_format"]["json_schema"]["schema"]["required"], ["text"])
        self.assertFalse(payload["chat_template_kwargs"]["enable_thinking"])
        reader = await self.make_reader({"backend": "vlm", "endpoint": "http://vlm/v1",
            "model": "test-vlm"}, {"choices": [{"message": {"content": '{"text":"Estate"}'},
                                                "finish_reason": "length"}]})
        with self.assertRaises(OCRError):
            await reader.read(b"image", perf_counter() + 1)

    async def test_vlm_without_thinking_extension(self):
        reader = await self.make_reader({"backend": "vlm", "endpoint": "http://vlm/v1",
            "model": "test-vlm", "thinking_field": "none"}, {"choices": [{
                "message": {"content": '{"text":"Estate"}'}, "finish_reason": "stop"}]})
        await reader.read(b"image", perf_counter() + 1)
        payload = json.loads(self.requests[0].content)
        self.assertNotIn("enable_thinking", payload)
        self.assertNotIn("chat_template_kwargs", payload)

    async def test_http_adapter_and_cache_do_not_mix_images_or_backends(self):
        options = {"backend": "http", "endpoint": "http://reader/read"}
        first = await self.make_reader(options, {"text": "first"})
        second = await self.make_reader(options, {"text": "second"})
        self.assertEqual((await first.read(b"one", perf_counter() + 1)).text, "first")
        self.assertEqual((await second.read(b"one", perf_counter() + 1)).text, "second")
        await second.read(b"two", perf_counter() + 1)
        self.assertEqual(len(second.cache), 2)
        with self.assertRaises(OCRError):
            await first.read(b"one", perf_counter() - 1)

    async def test_unavailable_http_and_invalid_output_fail_cleanly(self):
        for body, status in (({"text": "ignored"}, 503), ({"text": []}, 200), ({}, 200)):
            reader = await self.make_reader({"backend": "http", "endpoint": "http://reader/read"}, body, status)
            with self.assertRaises(OCRError):
                await reader.read(b"image", perf_counter() + 1)
            self.assertFalse(reader.cache)

    async def test_tesseract_stdin_and_process_kill_on_cancellation(self):
        class Process:
            returncode = None
            killed = False
            async def communicate(self, body):
                self.body = body
                await asyncio.sleep(10)
            def kill(self):
                self.killed = True
                self.returncode = -9
            async def wait(self):
                return self.returncode
        process = Process()
        with patch("matcher.ocr.asyncio.create_subprocess_exec", return_value=process) as spawn:
            reader = Reader(config({}), Services())
            task = asyncio.create_task(reader.read(b"image", perf_counter() + 20))
            await asyncio.sleep(.02)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(process.killed)
            self.assertEqual(process.body, b"image")
            self.assertEqual(spawn.call_args.args[:3], ("tesseract", "stdin", "stdout"))

    async def test_async_timeout_cancels_http_handler(self):
        cancelled = asyncio.Event()
        async def delayed(request):
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.set()
        services = Services()
        services.client = httpx.AsyncClient(transport=httpx.MockTransport(delayed))
        self.addAsyncCleanup(services.close)
        reader = Reader(config({"backend": "http", "endpoint": "http://reader/read"}), services)
        with self.assertRaises(OCRError):
            await reader.read(b"image", perf_counter() + .03)
        self.assertTrue(cancelled.is_set())


class ParseTests(unittest.TestCase):
    def test_tsv_word_confidence_and_coordinates(self):
        result = tesseract_result(TSV)
        self.assertEqual(result.text, "Cabernet")
        self.assertEqual(result.words[0].confidence, .9)
        self.assertEqual(result.words[0].box, (10, 20, 40, 60))

    def test_malformed_paddle_arrays_and_word_values(self):
        for body in ({"result": {"ocrResults": []}}, {"result": {"ocrResults": [{
                "prunedResult": {"rec_texts": ["x"], "rec_scores": []}}]}}):
            with self.assertRaises(ValueError):
                paddle_result(body)
        with self.assertRaises(ValueError):
            generic_result({"text": "x", "words": [{"text": "x", "confidence": float("nan")} ]})

    def test_config_rejects_unknown_keys_wrong_backend_options_and_literal_keys(self):
        for raw in ({"backend": "unknown"}, {"backend": "tesseract", "endpoint": "http://x"},
                    {"psm": True}, {"min_confidence": float("nan")},
                    {"backend": "vlm", "endpoint": "http://x/v1", "model": "m", "key": "literal"},
                    {"backend": "paddleocr", "endpoint": "file:///tmp/ocr"}):
            with self.assertRaises(ValueError):
                config(raw)
