import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import labdb  # noqa: E402
import wine_tags as WT  # noqa: E402


class WineTagsTest(unittest.TestCase):
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

    def test_tags_keep_the_order_of_the_adds(self):
        with self.conn:
            self.assertEqual(WT.add(self.conn, "wine-a", "vintage:2017",
                                    "2026-09-27T12:00:00Z"), "vintage:2017")
            WT.add(self.conn, "wine-b", "generic")
            WT.add(self.conn, "wine-a", "generic")
        self.assertEqual(WT.tags(self.conn), {"wine-a": ["vintage:2017", "generic"],
                                              "wine-b": ["generic"]})
        self.assertEqual(WT.tags(self.conn, "wine-b"), {"wine-b": ["generic"]})
        self.assertEqual(WT.tags(self.conn, "wine-none"), {})
        self.assertEqual(WT.count(self.conn), 3)
        self.assertEqual(self.conn.execute(
            "SELECT created_at FROM wine_tag WHERE tag = 'vintage:2017'").fetchone(),
            ("2026-09-27T12:00:00Z",))

    def test_the_normal_form(self):
        for text, tag in (("  Generic ", "generic"), ("VINTAGE:2017", "vintage:2017"),
                          ("Урожай_2017", "урожай_2017"), ("a.b-c", "a.b-c"),
                          ("x" * 64, "x" * 64)):
            with self.subTest(text=text):
                self.assertEqual(WT.normal(text), tag)
        for text in ("", "   ", None, 17, "two words", "a,b", "a/b", "tab\tin", "x" * 65):
            with self.subTest(text=text), self.assertRaises(WT.TagError):
                WT.normal(text)

    def test_a_second_add_of_the_same_tag_is_a_duplicate(self):
        with self.conn:
            WT.add(self.conn, "wine-a", "generic")
        for text in ("generic", " GENERIC "):
            with self.subTest(text=text), self.assertRaises(WT.DuplicateError):
                WT.add(self.conn, "wine-a", text)
        with self.conn:
            WT.add(self.conn, "wine-b", "generic")
        self.assertEqual(WT.count(self.conn), 2)

    def test_remove_takes_each_form_of_the_tag(self):
        with self.conn:
            WT.add(self.conn, "wine-a", "vintage:2017")
            self.assertTrue(WT.remove(self.conn, "wine-a", " Vintage:2017"))
            self.assertFalse(WT.remove(self.conn, "wine-a", "vintage:2017"))
        self.assertEqual(WT.tags(self.conn), {})
        with self.assertRaises(WT.TagError):
            WT.remove(self.conn, "wine-a", "")

    def test_table_checks(self):
        insert = "INSERT INTO wine_tag (wine_slug, tag, created_at) VALUES (?, ?, ?)"
        for row in (("wine-a", "", "2026-09-27T12:00:00Z"),
                    ("wine-a", "x" * 65, "2026-09-27T12:00:00Z"),
                    ("wine-none", "generic", "2026-09-27T12:00:00Z"),
                    ("wine-a", "generic", "2026-09-27 12:00")):
            with self.subTest(row=row), self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute(insert, row)
        self.conn.execute(insert, ("wine-a", "generic", "2026-09-27T12:00:00Z"))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(insert, ("wine-a", "generic", "2026-09-27T12:00:01Z"))
        self.assertEqual(WT.count(self.conn), 1)


if __name__ == "__main__":
    unittest.main()
