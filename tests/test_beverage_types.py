import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import beverage_types as BT  # noqa: E402
import labdb  # noqa: E402


class BeverageTypesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = labdb.connect(str(Path(self.tmp.name) / "lab.sqlite3"), create=True)
        self.conn.execute("PRAGMA foreign_keys = ON")
        with self.conn:
            self.conn.executemany(
                "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                "region, description, csv_photo_name) "
                "VALUES (?, 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp')",
                [(slug,) for slug in ("wine-a", "wine-b")])

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def stored(self):
        return {slug: (code, at) for slug, code, at in self.conn.execute(
            "SELECT wine_slug, beverage_type_code, updated_at FROM wine_beverage_type")}

    def test_no_row_means_no_type(self):
        self.assertEqual(BT.types(self.conn), {})
        self.assertEqual(BT.counts(self.conn), {"4": 0, "44": 0})

    def test_set_change_and_remove(self):
        with self.conn:
            self.assertEqual(BT.set_type(self.conn, "wine-a", "4", "2026-09-26T08:00:00Z"),
                             "4")
            BT.set_type(self.conn, "wine-b", "44", "2026-09-26T08:01:00Z")
        self.assertEqual(BT.types(self.conn), {"wine-a": "4", "wine-b": "44"})
        self.assertEqual(BT.counts(self.conn), {"4": 1, "44": 1})
        with self.conn:
            BT.set_type(self.conn, "wine-a", "44", "2026-09-26T09:00:00Z")
        self.assertEqual(self.stored()["wine-a"], ("44", "2026-09-26T09:00:00Z"))
        self.assertEqual(BT.counts(self.conn), {"4": 0, "44": 2})
        with self.conn:
            self.assertIsNone(BT.set_type(self.conn, "wine-a", None))
        self.assertEqual(BT.types(self.conn), {"wine-b": "44"})

    def test_repeated_requests_change_nothing(self):
        with self.conn:
            BT.set_type(self.conn, "wine-a", "4", "2026-09-26T08:00:00Z")
            # The same code again keeps the first time.
            BT.set_type(self.conn, "wine-a", "4", "2026-09-26T09:00:00Z")
            # A remove of a missing type changes nothing.
            BT.set_type(self.conn, "wine-b", None)
        self.assertEqual(self.stored(), {"wine-a": ("4", "2026-09-26T08:00:00Z")})

    def test_set_uses_the_present_time(self):
        with self.conn:
            BT.set_type(self.conn, "wine-a", "44")
        self.assertRegex(self.stored()["wine-a"][1], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_table_checks_the_values(self):
        insert = ("INSERT INTO wine_beverage_type (wine_slug, beverage_type_code, updated_at) "
                  "VALUES (?, ?, ?)")
        for row in (("wine-none", "4", "2026-09-26T08:00:00Z"),
                    ("wine-a", "440", "2026-09-26T08:00:00Z"),
                    ("wine-a", "", "2026-09-26T08:00:00Z"),
                    ("wine-a", None, "2026-09-26T08:00:00Z"),
                    ("wine-a", "4", "2026-09-26 08:00")):
            with self.subTest(row=row), self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute(insert, row)
        with self.assertRaises(sqlite3.IntegrityError):
            BT.set_type(self.conn, "wine-a", "45")
        self.assertEqual(BT.types(self.conn), {})


if __name__ == "__main__":
    unittest.main()
