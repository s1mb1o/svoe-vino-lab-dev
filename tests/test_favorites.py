import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import favorites as FV  # noqa: E402
import labdb  # noqa: E402


class FavoritesTest(unittest.TestCase):
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

    def test_mark_and_remove(self):
        with self.conn:
            self.assertTrue(FV.set_favorite(self.conn, "wine-a", True, "2026-09-25T08:00:00Z"))
            FV.set_favorite(self.conn, "wine-b", True, "2026-09-25T08:01:00Z")
        self.assertEqual(FV.favorites(self.conn), {"wine-a": "2026-09-25T08:00:00Z",
                                                   "wine-b": "2026-09-25T08:01:00Z"})
        self.assertEqual(FV.count(self.conn), 2)
        with self.conn:
            self.assertFalse(FV.set_favorite(self.conn, "wine-a", False))
        self.assertEqual(FV.favorites(self.conn), {"wine-b": "2026-09-25T08:01:00Z"})

    def test_repeated_requests_change_nothing(self):
        with self.conn:
            FV.set_favorite(self.conn, "wine-a", True, "2026-09-25T08:00:00Z")
            # A second mark keeps the first time.
            FV.set_favorite(self.conn, "wine-a", True, "2026-09-25T09:00:00Z")
            FV.set_favorite(self.conn, "wine-b", False)
        self.assertEqual(FV.favorites(self.conn), {"wine-a": "2026-09-25T08:00:00Z"})

    def test_mark_uses_the_present_time(self):
        with self.conn:
            FV.set_favorite(self.conn, "wine-a", True)
        self.assertRegex(FV.favorites(self.conn)["wine-a"],
                         r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_table_checks_the_form(self):
        insert = "INSERT INTO wine_favorite (wine_slug, created_at) VALUES (?, ?)"
        for row in (("wine-none", "2026-09-25T08:00:00Z"), ("wine-a", "2026-09-25 08:00")):
            with self.subTest(row=row), self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute(insert, row)
        self.assertEqual(FV.count(self.conn), 0)


if __name__ == "__main__":
    unittest.main()
