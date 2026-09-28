"""Additional-image uploads scan and fill the GTIN and QR URL fields."""
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import lab_server  # noqa: E402
import labdb  # noqa: E402
import qr_barcode  # noqa: E402


WINE = ("wine-a", "Wine A", "Winery", "Wine", "Red", "Region", None,
        "Description", "a.webp", "Active", None)


def picture(colour=(90, 30, 20)):
    image = Image.new("RGBA", (40, 80), (255, 255, 255, 0))
    ImageDraw.Draw(image).rectangle((10, 10, 29, 69), fill=colour)
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class Segmenter:
    """A detector that classifies the transparent test image as a full front image."""

    answer = [
        {"label": "bottle", "box": [10, 10, 30, 70], "score": 0.9, "area": 1200},
        {"label": "bottle neck", "box": [16, 12, 24, 30], "score": 0.9,
         "area": 144},
        {"label": "packet", "box": [0, 0, 40, 80], "score": 0.8, "area": 3200},
    ]

    def instances(self, image, texts, masks=True):
        return list(self.answer), 1.0

    def segment(self, image):
        raise AssertionError("the transparent test image MUST use the alpha cut")


class Scanner:
    def __init__(self):
        self.calls = []
        self.error = None

    def scan(self, data, name=None):
        self.calls.append((data, name))
        if self.error:
            raise self.error
        return [
            {"kind": "gtin", "value": "04631168664979", "read": "4631168664979",
             "format": "EAN13"},
            {"kind": "qr_url", "value": "https://example.test/wine/1",
             "read": "https://example.test/wine/1", "format": "QR Code"},
        ]


class AlternativeCodeTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = str(Path(self.directory.name) / "lab.sqlite3")
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.execute("INSERT INTO wine_catalog (%s) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
                         % ", ".join(lab_server.CATALOG_COLUMNS), WINE)
        conn.close()
        self.scanner = Scanner()
        self.segmenter = Segmenter()

    def tearDown(self):
        self.directory.cleanup()

    def upload(self, data, name="back.png"):
        answer = lab_server.store_alternative(
            self.db, "wine-a", data, name, self.segmenter, self.scanner)
        # Exercise the JSON form that the HTTP handler sends to the page.
        return 200, json.loads(json.dumps(answer))

    def stored_codes(self):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(
                "SELECT kind, value FROM wine_code ORDER BY rowid").fetchall()
        finally:
            conn.close()

    def test_upload_fills_both_code_fields_before_the_response(self):
        data = picture()
        status, answer = self.upload(data)
        self.assertEqual(status, 200)
        self.assertEqual(answer["record"]["_gtins"], ["04631168664979"])
        self.assertEqual(answer["record"]["_qr_urls"],
                         ["https://example.test/wine/1"])
        self.assertEqual(self.stored_codes(), [
            ("gtin", "04631168664979"),
            ("qr_url", "https://example.test/wine/1"),
        ])
        self.assertEqual(self.scanner.calls, [(data, "back.png")])

    def test_a_repeated_upload_scans_again_and_adds_no_duplicate(self):
        data = picture()
        self.upload(data)
        status, answer = self.upload(data, "again.png")
        self.assertEqual((status, answer["changed"], len(self.scanner.calls)),
                         (200, False, 2))
        self.assertEqual(len(self.stored_codes()), 2)

    def test_a_scanner_failure_keeps_the_additional_image(self):
        self.scanner.error = qr_barcode.ScanUnavailable("service unavailable")
        status, answer = self.upload(picture((20, 30, 90)))
        self.assertEqual(status, 200)
        self.assertEqual(len(answer["record"]["_alternatives"]), 1)
        self.assertEqual(self.stored_codes(), [])
        self.assertIn("QR/barcode scan failed", answer["warning"])
        self.assertIn("photo is stored without new code fields", answer["warning"])


if __name__ == "__main__":
    unittest.main()
