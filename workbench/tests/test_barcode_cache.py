"""Barcode cache controls. Each test uses temporary images and cache records."""
import concurrent.futures
import json
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import barcode
import model_cache


CODE = {"kind": "barcode", "format": "EAN13", "text": "4631168664979"}
OTHER = {"kind": "barcode", "format": "EAN13", "text": "4600682000181"}
KEY = ("gtin", "04631168664979")
OTHER_KEY = ("gtin", "04600682000181")


class BarcodeCacheTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.photo = self.root / "photo.png"
        Image.new("RGB", (300, 200), "white").save(self.photo)
        patcher = mock.patch.multiple(model_cache, ROOT=str(self.root / "cache"), READ=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.lookup = barcode.CodeLookup({KEY: ["wine-a"]})

    def decoder(self, found=(), **options):
        decoder = object.__new__(barcode.Decoder)
        options = dict({"tile_scan": True}, **options)
        decoder.options = barcode.check_options(options)
        decoder.scanner = types.SimpleNamespace(endpoint="http://scanner.test",
                                                engine="auto")
        decoder._last = threading.local()
        decoder.read = mock.Mock(return_value=list(found))
        return decoder

    def records(self):
        return list((self.root / "cache").rglob("*.json"))

    def test_empty_scan_is_reused_without_opening_or_decoding_image(self):
        decoder = self.decoder()
        self.assertEqual(decoder.scan_file(self.photo, self.lookup), ([], None, False))
        self.assertEqual(decoder.read.call_count, 35)
        fresh = self.decoder()
        with mock.patch.object(barcode.derive, "open_image", side_effect=AssertionError):
            self.assertEqual(fresh.scan_file(self.photo, self.lookup), ([], None, True))
        fresh.read.assert_not_called()
        self.assertEqual(len(self.records()), 1)

    def test_cached_codes_use_the_new_wine_lookup(self):
        decoder = self.decoder([CODE])
        self.assertEqual(decoder.scan_file(self.photo, self.lookup)[1]["slugs"], ["wine-a"])
        changed = barcode.CodeLookup({KEY: ["wine-b"]})
        found, hit, cached = decoder.scan_file(self.photo, changed)
        self.assertEqual((found, hit["slugs"], cached), ([CODE], ["wine-b"], True))
        self.assertEqual(decoder.read.call_count, 1)
        record = json.loads(self.records()[0].read_text())
        self.assertNotIn("wine-a", json.dumps(record))

    def test_removed_unique_code_resumes_the_unscanned_tiles(self):
        decoder = self.decoder([CODE])
        decoder.scan_file(self.photo, self.lookup)
        decoder.read.return_value = [OTHER]
        changed = barcode.CodeLookup({OTHER_KEY: ["wine-b"]})
        found, hit, cached = decoder.scan_file(self.photo, changed)
        self.assertEqual((found, hit["slugs"], cached), ([CODE, OTHER], ["wine-b"], False))
        self.assertEqual(decoder.read.call_count, 2)
        self.assertTrue(decoder.scan_file(self.photo, changed)[2])
        self.assertEqual(decoder.read.call_count, 2)

    def test_unique_code_that_becomes_shared_continues_to_another_unique_code(self):
        decoder = self.decoder([CODE])
        decoder.scan_file(self.photo, self.lookup)
        decoder.read.return_value = [OTHER]
        changed = barcode.CodeLookup({KEY: ["wine-a", "wine-b"], OTHER_KEY: ["wine-c"]})
        _, hit, cached = decoder.scan_file(self.photo, changed)
        self.assertEqual((hit["slugs"], cached), (["wine-c"], False))
        self.assertEqual(decoder.read.call_count, 2)

    def test_exhausted_cache_replays_the_original_early_stop_order(self):
        decoder = self.decoder()
        decoder.read.side_effect = [[CODE], [OTHER]] + [[]] * 33
        decoder.scan_file(self.photo, barcode.CodeLookup({}))
        found, hit, cached = decoder.scan_file(
            self.photo, barcode.CodeLookup({KEY: ["wine-a"], OTHER_KEY: ["wine-b"]}))
        self.assertEqual((found, hit["slugs"], cached), ([CODE], ["wine-a"], True))
        self.assertEqual(decoder.read.call_count, 35)

    def test_no_cache_reads_still_refresh_the_record(self):
        decoder = self.decoder([CODE], tile_scan=False)
        decoder.scan_file(self.photo, self.lookup)
        decoder.read.return_value = []
        with mock.patch.object(model_cache, "READ", False):
            self.assertEqual(decoder.scan_file(self.photo, self.lookup), ([], None, False))
        self.assertEqual(decoder.scan_file(self.photo, self.lookup), ([], None, True))
        self.assertEqual(decoder.read.call_count, 2)

    def test_source_bytes_options_endpoint_engine_and_revision_invalidate_cache(self):
        decoder = self.decoder([CODE])
        decoder.scan_file(self.photo, self.lookup)
        for options in ({"tile_scan": False}, {"max_side": 1024}, {"upscale": True},
                        {"qr": False}, {"code128_gtin_only": True}, {"formats": ["EAN13"]}):
            with self.subTest(options=options):
                changed = self.decoder([CODE], **options)
                self.assertFalse(changed.scan_file(self.photo, self.lookup)[2])
                changed.read.assert_called_once()
        decoder.scanner.endpoint = "http://scanner-next.test"
        self.assertFalse(decoder.scan_file(self.photo, self.lookup)[2])
        decoder.scanner.endpoint = "http://scanner.test"
        decoder.scanner.engine = "zxing-cpp"
        self.assertFalse(decoder.scan_file(self.photo, self.lookup)[2])
        with mock.patch.object(barcode, "CACHE_REVISION", 99):
            self.assertFalse(decoder.scan_file(self.photo, self.lookup)[2])
        with mock.patch.object(barcode, "PILLOW_VERSION", "test-next"):
            self.assertFalse(decoder.scan_file(self.photo, self.lookup)[2])
        Image.new("RGB", (300, 200), "black").save(self.photo)
        self.assertFalse(decoder.scan_file(self.photo, self.lookup)[2])

    def test_broken_or_malformed_cache_is_recomputed(self):
        decoder = self.decoder(tile_scan=False)
        decoder.scan_file(self.photo, self.lookup)
        path = self.records()[0]
        valid = json.loads(path.read_text())
        for answer in (None, {"batches": []}, {"batches": [[{}]]}, {"batches": [[], []]},
                       {"batches": [[dict(CODE, kind=[])]]},
                       {"batches": [[dict(CODE, kind={})]]}):
            with self.subTest(answer=answer):
                path.write_text(json.dumps(dict(valid, answer=answer)))
                self.assertFalse(decoder.scan_file(self.photo, self.lookup)[2])
        path.write_text("{broken")
        self.assertFalse(decoder.scan_file(self.photo, self.lookup)[2])
        self.assertTrue(decoder.scan_file(self.photo, self.lookup)[2])

    def test_decoder_exception_does_not_cache_a_false_negative(self):
        decoder = self.decoder(tile_scan=False)
        decoder.read.side_effect = RuntimeError("decoder failed")
        with self.assertRaisesRegex(RuntimeError, "decoder failed"):
            decoder.scan_file(self.photo, self.lookup)
        self.assertEqual(self.records(), [])
        decoder.read.side_effect = None
        self.assertFalse(decoder.scan_file(self.photo, self.lookup)[2])
        self.assertTrue(decoder.scan_file(self.photo, self.lookup)[2])

    def test_http_scanner_failure_does_not_cache_a_false_negative(self):
        decoder = barcode.Decoder(barcode.check_options({"tile_scan": False}))
        decoder.scanner = types.SimpleNamespace(
            endpoint="http://scanner.test", engine="auto",
            decode=mock.Mock(side_effect=RuntimeError("scanner failed")))
        with self.assertRaisesRegex(RuntimeError, "scanner failed"):
            decoder.scan_file(self.photo, self.lookup)
        self.assertEqual(self.records(), [])

    def test_four_workers_leave_a_valid_shared_record(self):
        decoder = self.decoder(tile_scan=False)
        barrier = threading.Barrier(4)

        def read(image):
            barrier.wait(timeout=5)
            return [CODE]

        decoder.read.side_effect = read
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            answers = list(pool.map(lambda _: decoder.scan_file(self.photo, self.lookup),
                                    range(4)))
        self.assertTrue(all(answer[1]["slugs"] == ["wine-a"] for answer in answers))
        self.assertEqual(len(self.records()), 1)
        decoder.read.side_effect = AssertionError("warm scan decoded again")
        self.assertTrue(decoder.scan_file(self.photo, self.lookup)[2])
        self.assertEqual(list((self.root / "cache").rglob("*.tmp")), [])

    def test_code_first_trace_reports_cache_hit_and_current_match(self):
        inner = types.SimpleNamespace(id="test", top_k=10, catalogue=None, spec={},
                                      ask=mock.Mock(return_value=([], 0, 200, None)))
        backend = barcode.CodeFirst(inner, barcode.check_options({}), None,
                                    decoder=self.decoder([CODE]), lookup=self.lookup)
        first, second = backend.ask(self.photo), backend.ask(self.photo)
        self.assertFalse(first[4]["steps"][0]["cached"])
        self.assertTrue(second[4]["steps"][0]["cached"])
        self.assertEqual(first[0], second[0])
        inner.ask.assert_not_called()


if __name__ == "__main__":
    unittest.main()
