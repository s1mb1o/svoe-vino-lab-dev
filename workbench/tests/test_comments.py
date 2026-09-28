import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import comments as CM  # noqa: E402
import labdb  # noqa: E402
from comments import CommentError  # noqa: E402


class CleanTextTest(unittest.TestCase):
    def test_stored_form(self):
        cases = (("  ok  ", "ok"), ("a\r\nb\rc\nd", "a\nb\nc\nd"), ("\ta\tb\n", "a\tb"),
                 ("Вкус: вишня", "Вкус: вишня"), ("x" * CM.TEXT_MAX, "x" * CM.TEXT_MAX),
                 # A character outside the BMP is a valid pair, not a lone surrogate.
                 ("вино 🍷", "вино 🍷"))
        for value, stored in cases:
            with self.subTest(value=value[:20]):
                self.assertEqual(CM.clean_text(value), stored)

    def test_refused_values(self):
        for value, message in ((None, "MUST be a string"), (5, "MUST be a string"),
                               ("", "empty"), (" \n\t ", "empty"),
                               ("x" * (CM.TEXT_MAX + 1), "longer than 4000"),
                               ("a\x00b", "control character"),
                               ("a\x7fb", "control character"),
                               ("a\ud800b", "lone surrogate"),
                               ("a\udfffb", "lone surrogate")):
            with self.subTest(value=repr(value)[:20]), \
                    self.assertRaisesRegex(CommentError, message):
                CM.clean_text(value)

    def test_now_has_the_stored_form(self):
        self.assertRegex(CM.now_utc(), r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")


class TableTest(unittest.TestCase):
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

    def test_add_returns_the_stored_row(self):
        with self.conn:
            added = CM.add(self.conn, "wine-a", "  first\r\nline  ", "user",
                           "2026-09-25T08:00:00Z")
        self.assertEqual(added, {"id": added["id"], "created_at": "2026-09-25T08:00:00Z",
                                 "source": "user", "text": "first\nline"})
        self.assertEqual(CM.comments(self.conn), {"wine-a": [added]})
        self.assertEqual(CM.count(self.conn), 1)

    def test_add_uses_the_present_time(self):
        with self.conn:
            added = CM.add(self.conn, "wine-a", "x", "script")
        self.assertRegex(added["created_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_comments_are_in_time_order(self):
        with self.conn:
            late = CM.add(self.conn, "wine-a", "late", "user", "2026-09-25T09:00:00Z")
            early = CM.add(self.conn, "wine-a", "early", "script", "2026-09-25T08:00:00Z")
            # The same second keeps the order of the writes. The same text is allowed.
            same = CM.add(self.conn, "wine-a", "late", "user", "2026-09-25T09:00:00Z")
            other = CM.add(self.conn, "wine-b", "b", "user", "2026-09-25T07:00:00Z")
        self.assertEqual(CM.comments(self.conn), {"wine-a": [early, late, same],
                                                  "wine-b": [other]})
        self.assertEqual(CM.comments(self.conn, "wine-b"), {"wine-b": [other]})
        self.assertEqual(CM.comments(self.conn, "wine-none"), {})

    def test_remove_deletes_one_comment_of_the_wine(self):
        with self.conn:
            first = CM.add(self.conn, "wine-a", "same", "user", "2026-09-25T08:00:00Z")
            second = CM.add(self.conn, "wine-a", "same", "user", "2026-09-25T08:00:00Z")
            other = CM.add(self.conn, "wine-b", "b", "user", "2026-09-25T08:00:00Z")
        with self.conn:
            # The id of a comment of another wine removes nothing.
            self.assertIsNone(CM.remove(self.conn, "wine-a", other["id"]))
            self.assertIsNone(CM.remove(self.conn, "wine-a", 999))
            self.assertEqual(CM.remove(self.conn, "wine-a", first["id"]), first)
        self.assertEqual(CM.comments(self.conn), {"wine-a": [second], "wine-b": [other]})

    def test_add_needs_a_known_source(self):
        for source in ("person", None, ""):
            with self.subTest(source=source), \
                    self.assertRaisesRegex(CommentError, "unknown source"):
                CM.add(self.conn, "wine-a", "x", source)
        self.assertEqual(CM.count(self.conn), 0)

    def test_table_checks_the_form(self):
        insert = ("INSERT INTO wine_comment (wine_slug, created_at, source, text) "
                  "VALUES (?, ?, ?, ?)")
        for row in (("wine-a", "2026-09-25T08:00:00Z", "user", ""),
                    ("wine-a", "2026-09-25 08:00:00", "user", "x"),
                    ("wine-a", "2026-09-25T08:00:00+03:00", "user", "x"),
                    ("wine-a", "2026-09-25T08:00:00Z", "person", "x"),
                    ("wine-a", "2026-09-25T08:00:00Z", "user", "x" * (CM.TEXT_MAX + 1)),
                    ("wine-none", "2026-09-25T08:00:00Z", "user", "x")):
            with self.subTest(row=(row[0], row[1], row[2], row[3][:10])), \
                    self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute(insert, row)
        self.assertEqual(CM.count(self.conn), 0)


if __name__ == "__main__":
    unittest.main()
