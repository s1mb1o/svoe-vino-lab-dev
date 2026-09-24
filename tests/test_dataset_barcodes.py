import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "review_server_for_barcode_tests", ROOT / "scripts" / "review_server.py")
SERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SERVER)


class DatasetBarcodeTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "code-map.json"
        self.old_file = SERVER.BARCODE_FILE
        self.old_barcodes = SERVER._barcodes
        SERVER.BARCODE_FILE = str(self.path)
        SERVER._barcodes = {}
        self.catalog = {
            "wine-a": {"slug": "wine-a"},
            "wine-b": {"slug": "wine-b"},
        }

    def tearDown(self):
        SERVER.BARCODE_FILE = self.old_file
        SERVER._barcodes = self.old_barcodes
        self.directory.cleanup()

    def write_map(self):
        self.path.write_text(json.dumps({"version": 1, "wines": [{
            "wine_slug": "wine-a",
            "barcode": "111",
            "qr_code": "https://example.test/a",
            "source_note": "keep this field",
        }]}), encoding="utf-8")
        SERVER._barcodes = SERVER.load_barcodes()

    def test_add_normalizes_value_and_preserves_other_fields(self):
        self.write_map()

        stored = SERVER.store_dataset_barcode(
            self.catalog, "wine-a", " 2 22 ")

        self.assertEqual(stored, "222")
        self.assertEqual(SERVER._barcodes["wine-a"], ["111", "222"])
        document = json.loads(self.path.read_text(encoding="utf-8"))
        record = document["wines"][0]
        self.assertEqual(record["barcode"], ["111", "222"])
        self.assertEqual(record["qr_code"], "https://example.test/a")
        self.assertEqual(record["source_note"], "keep this field")

    def test_add_creates_record_for_another_slug(self):
        self.write_map()

        SERVER.store_dataset_barcode(self.catalog, "wine-b", "333")

        self.assertEqual(SERVER._barcodes["wine-b"], ["333"])
        document = json.loads(self.path.read_text(encoding="utf-8"))
        record = next(item for item in document["wines"]
                      if item["wine_slug"] == "wine-b")
        self.assertEqual(record, {
            "wine_slug": "wine-b", "barcode": "333", "qr_code": None,
        })

    def test_duplicate_barcode_for_another_slug_is_rejected(self):
        self.write_map()
        before = self.path.read_bytes()

        with self.assertRaisesRegex(ValueError, "already belongs to `wine-a`"):
            SERVER.store_dataset_barcode(self.catalog, "wine-b", "111")

        self.assertEqual(self.path.read_bytes(), before)

    def test_empty_value_and_unknown_slug_are_rejected(self):
        self.write_map()

        with self.assertRaisesRegex(ValueError, "barcode is empty"):
            SERVER.store_dataset_barcode(self.catalog, "wine-a", "  ")
        with self.assertRaisesRegex(ValueError, "unknown wine slug"):
            SERVER.store_dataset_barcode(self.catalog, "missing", "444")


if __name__ == "__main__":
    unittest.main()
