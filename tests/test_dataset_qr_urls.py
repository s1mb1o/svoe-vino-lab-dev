import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "review_server_for_qr_url_tests", ROOT / "scripts" / "review_server.py")
SERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SERVER)


class DatasetQrUrlTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "code-map.json"
        self.old_file = SERVER.BARCODE_FILE
        self.old_barcodes = SERVER._barcodes
        self.old_qr_urls = SERVER._qr_urls
        SERVER.BARCODE_FILE = str(self.path)
        SERVER._barcodes = {}
        SERVER._qr_urls = {}
        self.catalog = {
            "wine-a": {"slug": "wine-a"},
            "wine-b": {"slug": "wine-b"},
        }

    def tearDown(self):
        SERVER.BARCODE_FILE = self.old_file
        SERVER._barcodes = self.old_barcodes
        SERVER._qr_urls = self.old_qr_urls
        self.directory.cleanup()

    def write_rows(self, rows):
        self.path.write_text(json.dumps({"version": 1, "wines": rows}),
                             encoding="utf-8")
        SERVER._reload_code_identifiers()

    def test_add_normalizes_url_and_preserves_other_fields(self):
        self.write_rows([{
            "wine_slug": "wine-a", "barcode": "111", "qr_code": None,
            "source_note": "keep this field",
        }])

        stored = SERVER.store_dataset_qr_url(
            self.catalog, "wine-a", "HTTPS://Example.test:443/wine/1#label")

        self.assertEqual(stored, "https://example.test/wine/1")
        self.assertEqual(SERVER._qr_urls, {
            "wine-a": ["https://example.test/wine/1"],
        })
        record = json.loads(self.path.read_text())["wines"][0]
        self.assertEqual(record["barcode"], "111")
        self.assertEqual(record["source_note"], "keep this field")

    def test_add_second_url_uses_a_list(self):
        self.write_rows([{
            "wine_slug": "wine-a", "barcode": None,
            "qr_code": "https://example.test/wine/1",
        }])

        SERVER.store_dataset_qr_url(
            self.catalog, "wine-a", "https://example.test/wine/2")

        record = json.loads(self.path.read_text())["wines"][0]
        self.assertEqual(record["qr_code"], [
            "https://example.test/wine/1",
            "https://example.test/wine/2",
        ])

    def test_normalized_duplicate_for_another_slug_is_rejected(self):
        self.write_rows([{
            "wine_slug": "wine-a", "barcode": None,
            "qr_code": "URL:https://Example.test:443/wine/1#label",
        }])
        before = self.path.read_bytes()

        with self.assertRaisesRegex(ValueError, "already belongs to `wine-a`"):
            SERVER.store_dataset_qr_url(
                self.catalog, "wine-b", "https://example.test/wine/1")

        self.assertEqual(self.path.read_bytes(), before)

    def test_remove_last_url_preserves_barcode_and_sets_null(self):
        self.write_rows([{
            "wine_slug": "wine-a", "barcode": "111",
            "qr_code": "URL:https://Example.test/wine/1#label",
        }])

        removed = SERVER.remove_dataset_qr_url(
            self.catalog, "wine-a", "https://example.test/wine/1")

        self.assertEqual(removed, "https://example.test/wine/1")
        self.assertEqual(SERVER._qr_urls, {})
        record = json.loads(self.path.read_text())["wines"][0]
        self.assertEqual(record["barcode"], "111")
        self.assertIsNone(record["qr_code"])

    def test_invalid_qr_urls_are_rejected(self):
        self.write_rows([])

        for value in ("wine page", "ftp://example.test/wine", "https://u:p@example.test/wine"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "QR URL"):
                    SERVER.store_dataset_qr_url(self.catalog, "wine-a", value)


if __name__ == "__main__":
    unittest.main()
