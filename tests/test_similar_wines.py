import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import labdb  # noqa: E402
import similar_wines as SW  # noqa: E402


class SimilarWinesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = labdb.connect(str(Path(self.tmp.name) / "lab.sqlite3"), create=True)
        self.conn.execute("PRAGMA foreign_keys = ON")
        with self.conn:
            self.conn.executemany(
                "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                "region, description, csv_photo_name) "
                "VALUES (?, 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp')",
                [(slug,) for slug in ("wine-a", "wine-b", "wine-c")])

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_a_pair_has_no_direction(self):
        with self.conn:
            self.assertEqual(SW.add(self.conn, "wine-b", "wine-a", "2026-09-27T12:00:00Z"),
                             ("wine-a", "wine-b"))
            SW.add(self.conn, "wine-a", "wine-c")
        self.assertEqual(SW.partners(self.conn), {"wine-a": ["wine-b", "wine-c"],
                                                  "wine-b": ["wine-a"], "wine-c": ["wine-a"]})
        self.assertEqual(SW.partners(self.conn, "wine-b"), {"wine-b": ["wine-a"]})
        self.assertEqual(SW.partners(self.conn, "wine-a"), {"wine-a": ["wine-b", "wine-c"]})
        self.assertEqual(SW.pairs(self.conn), [("wine-a", "wine-b"), ("wine-a", "wine-c")])
        self.assertEqual(SW.count(self.conn), 2)
        self.assertEqual(self.conn.execute(
            "SELECT created_at FROM wine_similar WHERE wine_slug_b = 'wine-b'").fetchone(),
            ("2026-09-27T12:00:00Z",))

    def test_a_second_add_of_either_order_is_a_duplicate(self):
        with self.conn:
            SW.add(self.conn, "wine-a", "wine-b")
        for slug, other in (("wine-a", "wine-b"), ("wine-b", "wine-a")):
            with self.subTest(slug=slug), self.assertRaises(SW.DuplicateError):
                SW.add(self.conn, slug, other)
        self.assertEqual(SW.count(self.conn), 1)

    def test_remove_takes_either_order(self):
        with self.conn:
            SW.add(self.conn, "wine-a", "wine-b")
            self.assertTrue(SW.remove(self.conn, "wine-b", "wine-a"))
            self.assertFalse(SW.remove(self.conn, "wine-a", "wine-b"))
        self.assertEqual(SW.partners(self.conn), {})

    def test_a_wine_is_not_similar_to_itself(self):
        with self.assertRaises(SW.SimilarError):
            SW.add(self.conn, "wine-a", "wine-a")

    def test_table_checks(self):
        insert = ("INSERT INTO wine_similar (wine_slug_a, wine_slug_b, created_at) "
                  "VALUES (?, ?, ?)")
        for row in (("wine-b", "wine-a", "2026-09-27T12:00:00Z"),
                    ("wine-a", "wine-a", "2026-09-27T12:00:00Z"),
                    ("wine-a", "wine-none", "2026-09-27T12:00:00Z"),
                    ("wine-a", "wine-b", "2026-09-27 12:00")):
            with self.subTest(row=row), self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute(insert, row)
        self.assertEqual(SW.count(self.conn), 0)


if __name__ == "__main__":
    unittest.main()
