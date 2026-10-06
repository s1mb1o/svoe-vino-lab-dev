"""Check persistent summary identity, corruption, and optional-write behavior."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import summary_cache as cache


class SummaryCacheTest(unittest.TestCase):
    def test_identity_and_payload_checks(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIs(cache.load(root, "rows", "file", [1]), cache.MISS)
            cache.store(root, "rows", "file", [1], {"value": "a"})
            self.assertEqual(cache.load(root, "rows", "file", [1]), {"value": "a"})
            self.assertIs(cache.load(root, "rows", "file", [2]), cache.MISS)
            path = next(Path(root).rglob("*.json"))
            path.write_text(path.read_text().replace('"value":"a"', '"value":"b"'))
            self.assertIs(cache.load(root, "rows", "file", [1]), cache.MISS)
            path.write_text("broken")
            self.assertIs(cache.load(root, "rows", "file", [1]), cache.MISS)

    def test_cache_replaces_one_file_and_supports_null_payload(self):
        with tempfile.TemporaryDirectory() as root:
            for identity in range(10):
                cache.store(root, "kind", "same-source", identity, None)
            self.assertIsNone(cache.load(root, "kind", "same-source", 9))
            self.assertEqual(len(list(Path(root).rglob("*.json"))), 1)
            self.assertFalse(list(Path(root).rglob(".tmp-*")))

    def test_unavailable_cache_never_fails_the_request(self):
        with patch.object(cache.os, "makedirs", side_effect=PermissionError("read only")):
            cache.store("missing", "kind", "file", [1], {"value": 1})
        self.assertIs(cache.load(None, "kind", "file", [1]), cache.MISS)
