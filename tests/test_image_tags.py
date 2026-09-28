"""The tags of an image (plan 66): `pipeline/image_tags.py` and the table `image_tag`."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import image_tags as IG  # noqa: E402
import labdb  # noqa: E402

A, B = "a" * 64, "b" * 64


class ImageTagsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = labdb.connect(str(Path(self.tmp.name) / "lab.sqlite3"), create=True)
        self.conn.execute("PRAGMA foreign_keys = ON")
        with self.conn:
            self.conn.executemany("INSERT INTO image (sha256, folder, extension) "
                                  "VALUES (?, 'testset', 'jpg')", [(A,), (B,)])

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_tags_keep_the_order_of_the_adds(self):
        with self.conn:
            self.assertEqual(IG.add(self.conn, A, " Blurry ", "2026-09-28T00:00:00Z"),
                             "blurry")
            IG.add(self.conn, B, "back_label")
            IG.add(self.conn, A, "back_label")
        self.assertEqual(IG.tags(self.conn), {A: ["blurry", "back_label"], B: ["back_label"]})
        self.assertEqual(IG.tags(self.conn, {B}), {B: ["back_label"]})
        self.assertEqual(IG.tags(self.conn, ["c" * 64]), {})
        self.assertEqual(IG.names(self.conn), [{"tag": "back_label", "images": 2},
                                               {"tag": "blurry", "images": 1}])
        self.assertEqual(self.conn.execute(
            "SELECT created_at FROM image_tag WHERE tag = 'blurry'").fetchone(),
            ("2026-09-28T00:00:00Z",))

    def test_the_form_is_the_form_of_a_wine_tag(self):
        self.assertEqual(IG.normal("Урожай:2017"), "урожай:2017")
        for text in ("", "two words", "a/b", "x" * 65, None):
            with self.subTest(text=text), self.assertRaises(IG.TagError):
                IG.add(self.conn, A, text)
        self.assertEqual(IG.tags(self.conn), {})

    def test_a_second_add_of_the_same_tag_is_a_duplicate(self):
        with self.conn:
            IG.add(self.conn, A, "blurry")
        with self.assertRaises(IG.DuplicateError):
            IG.add(self.conn, A, "BLURRY")
        with self.conn:
            IG.add(self.conn, B, "blurry")
        self.assertEqual(IG.names(self.conn), [{"tag": "blurry", "images": 2}])

    def test_remove_takes_each_form_of_the_tag(self):
        with self.conn:
            IG.add(self.conn, A, "blurry")
            self.assertTrue(IG.remove(self.conn, A, " Blurry"))
            self.assertFalse(IG.remove(self.conn, A, "blurry"))
        self.assertEqual(IG.tags(self.conn), {})
        with self.assertRaises(IG.TagError):
            IG.remove(self.conn, A, "")

    def test_table_checks(self):
        insert = "INSERT INTO image_tag (sha256, tag, created_at) VALUES (?, ?, ?)"
        for row in ((A, "", "2026-09-28T00:00:00Z"),
                    (A, "x" * 65, "2026-09-28T00:00:00Z"),
                    ("c" * 64, "blurry", "2026-09-28T00:00:00Z"),
                    (A, "blurry", "2026-09-28 00:00")):
            with self.subTest(row=row), self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute(insert, row)


if __name__ == "__main__":
    unittest.main()
