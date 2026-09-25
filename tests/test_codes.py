import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import codes  # noqa: E402
from codes import CodeError  # noqa: E402


class CheckDigitTest(unittest.TestCase):
    def test_known_numbers(self):
        # EAN-13 of code-map.json, EAN-8 and UPC-A examples.
        self.assertEqual(codes.check_digit("463116866497"), 9)
        self.assertEqual(codes.check_digit("9638507"), 4)
        self.assertEqual(codes.check_digit("03600029145"), 2)

    def test_leading_zeros_do_not_change_the_digit(self):
        self.assertEqual(codes.check_digit("0463116866497"), codes.check_digit("463116866497"))


class GtinTest(unittest.TestCase):
    def test_each_length_becomes_gtin_14(self):
        self.assertEqual(codes.clean_gtin("96385074"), "00000096385074")
        self.assertEqual(codes.clean_gtin("036000291452"), "00036000291452")
        self.assertEqual(codes.clean_gtin("4631168664979"), "04631168664979")
        self.assertEqual(codes.clean_gtin("04630037251630"), "04630037251630")

    def test_ean_13_and_datamatrix_give_one_form(self):
        self.assertEqual(codes.clean_gtin("4630037251630"), codes.clean_gtin("04630037251630"))

    def test_white_space_is_removed(self):
        self.assertEqual(codes.clean_gtin(" 4 631168 664979\t"), "04631168664979")

    def test_wrong_check_digit_names_both_digits(self):
        with self.assertRaisesRegex(CodeError, r"^wrong check digit 0; expected 9$"):
            codes.clean_gtin("4631168664970")

    def test_refused_forms(self):
        for value, message in (("", "empty"), ("   ", "empty"), (4631168664979, "string"),
                               ("463116866497X", "digits alone"),
                               ("٤٦٣١١٦٨٦٦٤٩٧٩", "digits alone"),
                               ("46311686649", "it has 11"),
                               ("046311686649790", "it has 15")):
            with self.subTest(value=value), self.assertRaisesRegex(CodeError, message):
                codes.clean_gtin(value)


class QrUrlTest(unittest.TestCase):
    def test_normal_form(self):
        cases = (
            ("URL:https://chateautamagne.ru/ru/catalog/wine/111",
             "https://chateautamagne.ru/ru/catalog/wine/111"),
            ("HTTPS://Example.COM:443#top", "https://example.com/"),
            ("http://example.com:80/a", "http://example.com/a"),
            ("http://example.com:8080/a?b=1&utm=qr", "http://example.com:8080/a?b=1&utm=qr"),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(codes.clean_qr_url(value), expected)

    def test_ipv6_host_keeps_its_brackets(self):
        for value, expected in (("http://[::1]:8080/x", "http://[::1]:8080/x"),
                                ("https://[2001:DB8::1]/", "https://[2001:db8::1]/"),
                                ("http://[::1]:80/", "http://[::1]/")):
            with self.subTest(value=value):
                self.assertEqual(codes.clean_qr_url(value), expected)

    def test_international_host_becomes_idna(self):
        value = codes.clean_qr_url("https://пример.рф/вино")
        self.assertTrue(value.startswith("https://xn--"), value)
        self.assertTrue(value.endswith("/вино"), value)

    def test_refused_forms(self):
        for value, message in (("", "empty"), ("URL:", "empty"), (None, "string"),
                               ("https://a.ru/" + "x" * 4096, "longer than 4096"),
                               ("https://a.ru/a b", "white space"),
                               ("ftp://a.ru/", "http or https"), ("https:///path", "http or https"),
                               ("https://user:pw@a.ru/", "user information"),
                               ("https://a.ru:99999/", "host or port")):
            with self.subTest(value=value), self.assertRaisesRegex(CodeError, message):
                codes.clean_qr_url(value)


class DispatchTest(unittest.TestCase):
    def test_clean_uses_the_kind(self):
        self.assertEqual(codes.clean("gtin", "4631168664979"), "04631168664979")
        self.assertEqual(codes.clean("qr_url", "https://A.ru"), "https://a.ru/")
        with self.assertRaisesRegex(CodeError, "unknown kind"):
            codes.clean("ean", "1")

    def test_barcode_is_not_a_kind(self):
        # The lab keeps GTINs alone (owner choice of 2026-09-25).
        self.assertEqual(codes.KINDS, ("gtin", "qr_url"))
        with self.assertRaisesRegex(CodeError, "unknown kind 'barcode'"):
            codes.clean("barcode", "AB1")


if __name__ == "__main__":
    unittest.main()
