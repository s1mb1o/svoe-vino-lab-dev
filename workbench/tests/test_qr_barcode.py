"""Tests of the client of the existing QR and barcode scanner service."""
import sys
import unittest
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import qr_barcode  # noqa: E402


class Response:
    def __init__(self, answer=None, status=200, text=""):
        self.answer = answer
        self.status_code = status
        self.text = text

    def json(self):
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


class Session:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


class CleanInstancesTest(unittest.TestCase):
    def test_valid_gtins_and_qr_urls_get_the_database_normal_forms(self):
        instances = [
            {"text": "4631168664979", "format": "EAN13"},
            {"text": "URL:https://Example.test:443/wine/1#label", "format": "QR Code"},
            {"text": "https://example.test/wine/1", "format": "QRCode"},
            {"text": "LOT-12", "format": "Code128"},
            {"text": "plain QR text", "format": "QR_CODE"},
        ]
        self.assertEqual(qr_barcode.clean_instances(instances), [
            {"kind": "gtin", "value": "04631168664979", "read": "4631168664979",
             "format": "EAN13"},
            {"kind": "qr_url", "value": "https://example.test/wine/1",
             "read": "URL:https://Example.test:443/wine/1#label", "format": "QR Code"},
        ])

    def test_a_malformed_answer_is_an_error(self):
        for value in (None, {}, [None], [{"text": "1"}], [{"format": "EAN13"}]):
            with self.subTest(value=value), self.assertRaises(qr_barcode.ScanUnavailable):
                qr_barcode.clean_instances(value)


class ClientTest(unittest.TestCase):
    def test_scan_uses_the_existing_service_and_auto_engine(self):
        session = Session(Response({"instances": [
            {"text": "4631168664979", "format": "EAN13"},
        ]}))
        client = qr_barcode.Client("http://scanner.test/root/", session)
        self.assertEqual(client.scan(b"image", "back.png")[0]["value"],
                         "04631168664979")
        url, request = session.calls[0]
        self.assertEqual(url, "http://scanner.test/root/scan")
        self.assertEqual(request["data"], {"engine": "auto"})
        self.assertEqual(request["files"]["image"],
                         ("back.png", b"image", "image/png"))
        self.assertEqual(request["timeout"], qr_barcode.TIMEOUT)

    def test_no_endpoint_or_no_answer_is_an_error(self):
        with self.assertRaisesRegex(qr_barcode.ScanUnavailable, "QR_SCANNER_ENDPOINT"):
            qr_barcode.Client("", Session()).scan(b"image")
        session = Session(error=requests.ConnectionError("connection refused"))
        with self.assertRaisesRegex(qr_barcode.ScanUnavailable, "did not answer"):
            qr_barcode.Client("http://scanner.test", session).scan(b"image")

    def test_http_and_json_errors_are_scanner_errors(self):
        with self.assertRaisesRegex(qr_barcode.ScanUnavailable, "HTTP 503"):
            qr_barcode.Client("http://scanner.test", Session(Response(
                status=503, text="busy"))).scan(b"image")
        with self.assertRaisesRegex(qr_barcode.ScanUnavailable, "not JSON"):
            qr_barcode.Client("http://scanner.test", Session(Response(
                ValueError("bad JSON")))).scan(b"image")


if __name__ == "__main__":
    unittest.main()
