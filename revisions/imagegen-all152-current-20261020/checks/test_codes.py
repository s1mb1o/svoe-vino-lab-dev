"""Tests of the code rules of the backend `cascade`: normal forms, formats, the lookup."""

import unittest

from matcher.codes import (CodeError, CodeTable, check_digit, clean_gtin, clean_qr_url,
                           is_gtin13, is_unique, read)


def ean(twelve):
    return twelve + str(check_digit(twelve))


VALID = ean("460000000001")
WRONG = VALID[:-1] + str((int(VALID[-1]) + 1) % 10)
SHARED = ean("460000000002")
OTHER = ean("460000000003")


class NormalFormTest(unittest.TestCase):
    def test_gs1_check_digit(self):
        self.assertEqual(check_digit("460000000001"), 5)
        self.assertEqual(check_digit("0460000000001"), check_digit("460000000001"))
        self.assertEqual(check_digit("978020137962"), 4)
        self.assertEqual(check_digit("03600029145"), 2)

    def test_gtin_lengths_give_the_gtin_14_form(self):
        for value in ("96385074", "036000291452", VALID, "0" + VALID):
            with self.subTest(value=value):
                self.assertEqual(len(clean_gtin(value)), 14)
        self.assertEqual(clean_gtin(" %s " % VALID), "0" + VALID)

    def test_bad_gtins_are_errors(self):
        for value in (WRONG, VALID[:11], VALID[:5] + "A" + VALID[6:], "", None, int(VALID)):
            with self.subTest(value=value), self.assertRaises(CodeError):
                clean_gtin(value)

    def test_qr_url_normal_form(self):
        self.assertEqual(clean_qr_url("URL: HTTPS://Example.COM:443/a#part"),
                         "https://example.com/a")
        self.assertEqual(clean_qr_url("http://example.com:8080"), "http://example.com:8080/")
        self.assertEqual(clean_qr_url("https://пример.рф/x?y=1"),
                         "https://xn--e1afmkfd.xn--p1ai/x?y=1")
        self.assertEqual(clean_qr_url("http://[2001:DB8::1]:80/p"), "http://[2001:db8::1]/p")

    def test_bad_qr_urls_are_errors(self):
        for value in ("ftp://example.com/a", "https://user:pw@example.com/",
                      "https://exa mple.com/", "https://example.com/\x07", "", "x" * 5000):
            with self.subTest(value=value[:30]), self.assertRaises(CodeError):
                clean_qr_url(value)

    def test_gtin_13_check(self):
        self.assertTrue(is_gtin13(VALID))
        self.assertFalse(is_gtin13(WRONG))
        self.assertFalse(is_gtin13(VALID[:12]))


class ReadTest(unittest.TestCase):
    def test_kept_formats_in_reading_order_without_repeats(self):
        found = read([
            {"text": VALID, "format": "EAN-13"},
            {"text": " https://example.com/a ", "format": "QR Code"},
            {"text": VALID, "format": "Code 128"},
            {"text": "ABC-1", "format": "Code 128"},
            {"text": "96385074", "format": "EAN-8"},
            {"text": "036000291452", "format": "UPC-A"},
            {"text": VALID, "format": "EAN-13"},
        ])
        # The EAN-13 and the Code 128 of the same text are one barcode.
        self.assertEqual(found, [
            {"kind": "barcode", "format": "EAN-13", "text": VALID},
            {"kind": "qr_code", "format": "QR Code", "text": "https://example.com/a"},
        ])

    def test_a_code128_gtin_13_counts(self):
        self.assertEqual(read([{"text": VALID, "format": "Code 128"}]),
                         [{"kind": "barcode", "format": "Code 128", "text": VALID}])
        self.assertEqual(read([{"text": WRONG, "format": "Code 128"}]), [])

    def test_malformed_instances_are_errors(self):
        for instances in (None, [1], [{"text": "", "format": "EAN-13"}],
                          [{"text": VALID}], [{"format": "EAN-13", "text": 5}]):
            with self.subTest(instances=str(instances)[:30]), self.assertRaises(ValueError):
                read(instances)


class LookupTest(unittest.TestCase):
    TABLE = CodeTable({
        ("gtin", "0" + VALID): ("wine-a",),
        ("gtin", "0" + SHARED): ("wine-b", "wine-c"),
        ("qr_url", "https://example.com/shared"): ("wine-d", "wine-e"),
        ("qr_url", "https://example.com/one"): ("wine-f",),
    })

    def code(self, text, kind="barcode", fmt="EAN-13"):
        return {"kind": kind, "format": fmt, "text": text}

    def test_the_first_unique_hit_wins_over_a_shared_gtin(self):
        hit = self.TABLE.find([self.code(SHARED), self.code(VALID)])
        self.assertEqual((hit["slugs"], hit["code"], hit["read"]),
                         (["wine-a"], "0" + VALID, VALID))
        self.assertTrue(is_unique(hit))

    def test_a_shared_gtin_decides_when_no_code_is_unique(self):
        hit = self.TABLE.find([self.code(SHARED)])
        self.assertEqual(hit["slugs"], ["wine-b", "wine-c"])
        self.assertFalse(is_unique(hit))

    def test_a_shared_qr_url_never_decides_and_a_unique_qr_url_does(self):
        shared = self.code("URL:https://EXAMPLE.com/shared", "qr_code", "QR Code")
        self.assertIsNone(self.TABLE.find([shared]))
        one = self.code("https://example.com/one", "qr_code", "QR Code")
        self.assertEqual(self.TABLE.find([shared, one])["slugs"], ["wine-f"])

    def test_invalid_and_unknown_codes_give_no_hit(self):
        self.assertIsNone(self.TABLE.find([self.code(WRONG), self.code(OTHER)]))
        self.assertFalse(is_unique(None))


if __name__ == "__main__":
    unittest.main()
