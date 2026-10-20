"""YAML loading keeps OCR options in the native cascade, with no service calls."""

import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from matcher.service import ConfigError, load_matcher
from test_cascade_api import entry, write_cascade_catalog, write_config


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.catalog = write_cascade_catalog(self.root / "catalog")
        self.endpoints = SimpleNamespace(siglip2="http://siglip", scanner="http://scanner",
                                         sam3="http://sam3", vlm="http://vlm/v1")

    def load(self, options):
        pipeline = entry(self.catalog, self.endpoints, selective_ocr=options)
        matcher = load_matcher(write_config(self.root / "config.yaml", pipeline))
        self.addCleanup(matcher.cascade.executor.shutdown, wait=False, cancel_futures=True)
        return matcher

    def test_all_backends_load_and_keep_existing_cascade_stages(self):
        for options in ({"backend": "tesseract"}, {"backend": "vlm", "endpoint": "http://vlm/v1", "model": "reader"},
                        {"backend": "paddleocr", "endpoint": "http://paddle/ocr"},
                        {"backend": "http", "endpoint": "http://reader/read"}):
            matcher = self.load({"ocr": options})
            self.assertEqual(matcher.cascade.config.selective_ocr.ocr.backend, options["backend"])
            self.assertIsNotNone(matcher.cascade.config.rerank)
            self.assertIsNotNone(matcher.cascade.config.barcode)
            self.assertEqual(matcher.cascade.config.selective_ocr.pool, 50)

    def test_endpoint_and_key_use_environment_references(self):
        with patch.dict(os.environ, {"OCR_TEST_ENDPOINT": "http://reader/read", "OCR_TEST_KEY": "test-value"}):
            matcher = self.load({"ocr": {"backend": "http", "endpoint": "{env:OCR_TEST_ENDPOINT}",
                                          "key": "{env:OCR_TEST_KEY}"}})
            self.assertEqual(matcher.cascade.config.selective_ocr.ocr.endpoint, "http://reader/read")
            self.assertNotIn("test-value", repr(matcher.cascade.config.selective_ocr))

    def test_invalid_config_fails_before_runtime(self):
        for options in ({"ocr": {"backend": "http"}}, {"ocr": {"backend": "vlm", "endpoint": "http://x/v1"}},
                        {"pool": True}, {"input": "unknown"}):
            with self.assertRaises(ConfigError):
                self.load(options)

    def test_disabled_config_does_not_construct_reader(self):
        matcher = self.load({"enabled": False})
        self.assertIsNone(matcher.cascade.ocr)
        with patch.dict(os.environ, {}, clear=True):
            matcher = self.load({"enabled": False, "ocr": {"backend": "http",
                "endpoint": "{env:UNSET_OCR_ENDPOINT}", "key": "{env:UNSET_OCR_KEY}"}})
        self.assertIsNone(matcher.cascade.ocr)
