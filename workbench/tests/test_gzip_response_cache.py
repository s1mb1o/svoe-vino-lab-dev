"""Check gzip negotiation, bounded reuse, changed bytes, and HTTP representation headers."""
import gzip
import io
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from gzip_response_cache import GzipResponseCache, accepts_gzip
import lab_server

SEND = lab_server.Handler._send


class GzipResponseCacheTest(unittest.TestCase):
    def test_negotiation(self):
        for value in ("gzip", "br, gzip;q=0.4", "*", "GZip; Q=1"):
            self.assertTrue(accepts_gzip(value), value)
        for value in ("", "br", "gzip;q=0", "*;q=1,gzip;q=0", "gzip;q=bad", "gzip;q=2"):
            self.assertFalse(accepts_gzip(value), value)

    def test_repeat_and_changed_payload(self):
        cache = GzipResponseCache()
        first = b"a" * 100000
        with patch("gzip_response_cache.gzip.compress", wraps=gzip.compress) as compress:
            saved = cache.get(first, "gzip")[0]
            self.assertEqual(cache.get(bytes(first), "gzip"), (saved, True))
            self.assertEqual(compress.call_count, 1)
            changed = b"b" * 100000
            self.assertEqual(gzip.decompress(cache.get(changed, "gzip")[0]), changed)
            self.assertEqual(compress.call_count, 2)
        self.assertEqual(cache.get(first, "gzip;q=0"), (first, False))

    def test_bounds(self):
        cache = GzipResponseCache(max_entries=1, max_bytes=20000)
        for value in (b"a" * 10000, b"b" * 10000):
            cache.get(value, "gzip")
        self.assertEqual(len(cache._entries), 1)
        cache.get(b"a" * 100000, "gzip")
        self.assertLessEqual(cache._bytes, 20000)

    def send(self, accept="gzip", command="GET", content_type="application/json", code=200):
        headers = {}
        handler = types.SimpleNamespace(
            command=command, headers={"Accept-Encoding": accept}, wfile=io.BytesIO(),
            send_response=lambda status: headers.update(status=status),
            send_header=lambda name, value: headers.update({name: value}), end_headers=lambda: None)
        SEND(handler, code, b"a" * 100000, content_type, "no-store")
        return headers, handler.wfile.getvalue()

    def test_http_length_vary_and_head(self):
        headers, body = self.send()
        self.assertEqual(headers["Vary"], "Accept-Encoding")
        self.assertEqual(headers["Content-Encoding"], "gzip")
        self.assertEqual(int(headers["Content-Length"]), len(body))
        self.assertEqual(gzip.decompress(body), b"a" * 100000)
        head, body = self.send(command="HEAD")
        self.assertEqual(head, headers)
        self.assertEqual(body, b"")

    def test_identity_and_other_content(self):
        headers, body = self.send(accept="gzip;q=0")
        self.assertEqual(body, b"a" * 100000)
        self.assertEqual(headers["Vary"], "Accept-Encoding")
        self.assertNotIn("Content-Encoding", headers)
        for args in ({"command": "POST"}, {"content_type": "image/png"}, {"code": 400}):
            headers, body = self.send(**args)
            self.assertEqual(body, b"a" * 100000)
            self.assertNotIn("Vary", headers)


if __name__ == "__main__":
    unittest.main()
