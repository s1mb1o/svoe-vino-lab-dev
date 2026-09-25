import contextlib
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import labdb  # noqa: E402
import seed_codes as SC  # noqa: E402

CODE_MAP = {"version": 1, "wines": [
    {"wine_slug": "wine-a", "barcode": "4631168664979", "qr_code": None},
    {"wine_slug": "wine-b", "barcode": ["4640005351194", "4640005350852"],
     "qr_code": "URL:https://Chateau.RU/wine/111#label"},
    {"wine_slug": "wine-c", "barcode": None, "qr_code": ["https://c.ru/a"],
     "source_note": "not copied"},
]}


class SeedCodesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = str(self.root / "lab.sqlite3")
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.executemany(
                "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                "region, description, csv_photo_name) "
                "VALUES (?, 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp')",
                [(slug,) for slug in ("wine-a", "wine-b", "wine-c")])
        conn.close()
        self.log = []

    def tearDown(self):
        self.tmp.cleanup()

    def write_map(self, document):
        path = self.root / "code-map.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return str(path)

    def seed(self, document=CODE_MAP, force=False):
        return SC.seed_codes(self.db, self.write_map(document), log=self.log.append,
                             force=force)

    def rows(self):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(
                "SELECT wine_slug, kind, value FROM wine_code ORDER BY rowid").fetchall()
        finally:
            conn.close()

    def test_seed_splits_the_kinds(self):
        read, added, missing = self.seed()
        self.assertEqual(self.rows(), [
            ("wine-a", "gtin", "04631168664979"),
            ("wine-b", "gtin", "04640005351194"),
            ("wine-b", "gtin", "04640005350852"),
            ("wine-b", "qr_url", "https://chateau.ru/wine/111"),
            ("wine-c", "qr_url", "https://c.ru/a"),
        ])
        self.assertEqual(read, {"gtin": 3, "qr_url": 2})
        self.assertEqual(added, read)
        self.assertEqual(missing, [])

    def test_second_run_is_refused_unless_force(self):
        # The owner chose on 2026-09-25: a second run MUST NOT add back a removed value.
        self.seed()
        with self.assertRaisesRegex(SC.SeedError, "wine_code already holds 5 rows.*--force"):
            self.seed()
        _read, added, _missing = self.seed(force=True)
        self.assertEqual(added, {"gtin": 0, "qr_url": 0})
        self.assertEqual(len(self.rows()), 5)

    def test_ean_13_and_gtin_14_of_one_wine_give_one_row(self):
        self.seed({"wines": [{"wine_slug": "wine-a",
                              "barcode": ["4631168664979", "04631168664979"]}]})
        self.assertEqual(self.rows(), [("wine-a", "gtin", "04631168664979")])

    def test_two_wines_share_one_value(self):
        self.seed({"wines": [{"wine_slug": "wine-a", "barcode": "4631168664979"},
                             {"wine_slug": "wine-b", "barcode": "4631168664979"}]})
        self.assertEqual(self.rows(), [("wine-a", "gtin", "04631168664979"),
                                       ("wine-b", "gtin", "04631168664979")])

    def test_wrong_check_digit_stops_the_seed_with_no_write(self):
        document = {"wines": [{"wine_slug": "wine-a", "barcode": "4631168664979"},
                              {"wine_slug": "wine-b", "barcode": "4631168664970"}]}
        with self.assertRaisesRegex(SC.SeedError,
                                    r"record 2 \(wine-b\): `barcode` '4631168664970': wrong check digit 0; expected 9"):
            self.seed(document)
        self.assertEqual(self.rows(), [])

    def test_barcode_that_is_not_a_gtin_stops_the_seed(self):
        # The lab keeps GTINs alone (owner choice of 2026-09-25).
        with self.assertRaisesRegex(SC.SeedError,
                                    r"record 1 \(wine-a\): `barcode` 'AB-12 34': GTIN MUST hold digits alone"):
            self.seed({"wines": [{"wine_slug": "wine-a", "barcode": "AB-12 34"}]})
        self.assertEqual(self.rows(), [])

    def test_bad_qr_url_stops_the_seed(self):
        with self.assertRaisesRegex(SC.SeedError, r"record 1 \(wine-a\): `qr_code` 'ftp://a.ru/': QR URL MUST use"):
            self.seed({"wines": [{"wine_slug": "wine-a", "qr_code": "ftp://a.ru/"}]})
        self.assertEqual(self.rows(), [])

    def test_bad_shapes(self):
        for document, message in (([], "`wines` list"), ({"wines": {}}, "`wines` list"),
                                  ({"wines": ["x"]}, "record 1 MUST be an object"),
                                  ({"wines": [{"barcode": "1"}]}, "MUST name `wine_slug`"),
                                  ({"wines": [{"wine_slug": "wine-a", "barcode": 4631168664979}]},
                                   "string, a list of strings, or null")):
            with self.subTest(document=document), self.assertRaisesRegex(SC.SeedError, message):
                self.seed(document)

    def test_slug_with_no_wine_is_skipped(self):
        _read, added, missing = self.seed(
            {"wines": [{"wine_slug": "wine-x", "barcode": "4631168664979"},
                       {"wine_slug": "wine-a", "qr_code": "https://a.ru/"}]})
        self.assertEqual(missing, ["wine-x"])
        self.assertEqual(self.log, ["no wine: wine-x"])
        self.assertEqual(added, {"gtin": 0, "qr_url": 1})
        self.assertEqual(self.rows(), [("wine-a", "qr_url", "https://a.ru/")])

    def test_main_refuses_a_second_run_unless_force(self):
        path = self.write_map(CODE_MAP)
        outputs = []
        for argv, code in ((["--db", self.db, path], 0), (["--db", self.db, path], 1),
                           (["--db", self.db, "--force", path], 0)):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(SC.main(argv), code)
            outputs.append(out.getvalue() + err.getvalue())
        self.assertIn("added: gtin 3, qr_url 2\n", outputs[0])
        self.assertIn("result: seeded\n", outputs[0])
        self.assertIn("error: wine_code already holds 5 rows", outputs[1])
        self.assertIn("added: gtin 0, qr_url 0\n", outputs[2])
        self.assertIn("result: no change\n", outputs[2])

    def test_row_of_the_page_blocks_the_seed(self):
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("INSERT INTO wine_code VALUES ('wine-a', 'gtin', '04631168664979')")
        conn.close()
        with self.assertRaisesRegex(SC.SeedError, "already holds 1 rows"):
            self.seed()
        self.assertEqual(len(self.rows()), 1)


if __name__ == "__main__":
    unittest.main()
