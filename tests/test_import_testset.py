import hashlib
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX  # noqa: E402
import import_testset as IT  # noqa: E402

PHOTOS = {
    "wine-a/01.jpg": b"photo a1",
    "wine-a/02.jpg": b"photo a2",
    "wine-b/01.png": b"photo b1",
    "wine-b/02.jpg": b"photo a1",          # the bytes of wine-a/01.jpg
    "wine-c/01.jpg": b"photo c1",
    "__null__/n1.jpg": b"photo n1",
    "unknown-wine/01.jpg": b"photo u1",
    "wine-a/notes.txt": b"not a photo",
    "wine-a/.hidden.jpg": b"hidden",
    "loose.jpg": b"loose",
}
LABELS = {
    "wine-a": {"01.jpg": {"label": "positive"}, "02.jpg": {"label": "negative", "delete": True},
               "99.jpg": {"label": "positive"}},
    "wine-b": {"01.png": {"label": "variant"}, "02.jpg": {"proposed": "positive"}},
    "wine-c": {"01.jpg": {"label": "unusable"}},
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ImportTestsetTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(self.root)
        self.messages = []

    def tearDown(self):
        self.directory.cleanup()

    def run_import(self, set_dir, set_name="my"):
        self.messages = []
        return IT.import_testset(self.db, set_name, set_dir, self.messages.append, self.schema)

    def query(self, sql, *args):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def photos(self, set_name="my"):
        return {(p, f): (s, l, d) for p, f, s, l, d in self.query(
            "SELECT place, file_name, sha256, label, marked_delete FROM test_photo "
            "WHERE set_name = ?", set_name)}

    def standard_set(self):
        return FX.write_set(self.root, PHOTOS, LABELS, excluded={"wine-c": {"reason": "r", "ts": "t"}},
                            groups=[["wine-a", "wine-b"]])

    def test_import_holds_each_photo_with_its_label(self):
        report = self.run_import(self.standard_set())
        self.assertEqual(self.photos(), {
            ("wine-a", "01.jpg"): (sha(b"photo a1"), "positive", 0),
            ("wine-a", "02.jpg"): (sha(b"photo a2"), "negative", 1),
            ("wine-b", "01.png"): (sha(b"photo b1"), "variant", 0),
            ("wine-b", "02.jpg"): (sha(b"photo a1"), None, 0),
            ("wine-c", "01.jpg"): (sha(b"photo c1"), "unusable", 0),
            ("__null__", "n1.jpg"): (sha(b"photo n1"), None, 0),
            ("unknown-wine", "01.jpg"): (sha(b"photo u1"), None, 0),
        })
        self.assertEqual((report.photos, report.loose, report.no_file), (7, 1, 1))
        self.assertEqual(report.unknown_places, ["unknown-wine"])
        self.assertEqual(self.query("SELECT wine_slug, reason, ts FROM test_excluded"),
                         [("wine-c", "r", "t")])
        self.assertEqual(self.query("SELECT wine_slug, group_no FROM test_variant ORDER BY 1"),
                         [("wine-a", 0), ("wine-b", 0)])
        self.assertEqual(self.query("SELECT set_name FROM test_set"), [("my",)])

    def test_same_bytes_are_stored_one_time(self):
        report = self.run_import(self.standard_set())
        self.assertEqual((report.written, report.present), (6, 1))
        self.assertEqual(self.query("SELECT count(*) FROM image"), [(6,)])
        path = IT.photo_path(self.db, sha(b"photo a1"), "jpg")
        self.assertEqual(Path(path).read_bytes(), b"photo a1")
        self.assertEqual(Path(path).parent.name, "testset")
        self.assertEqual(self.query("SELECT DISTINCT folder FROM image"), [("testset",)])

    def test_a_second_import_follows_the_files(self):
        set_dir = self.standard_set()
        self.run_import(set_dir)
        labels = json.loads(json.dumps(LABELS))
        labels["wine-a"]["01.jpg"] = {"label": "negative"}
        (Path(set_dir) / "review-labels.json").write_text(json.dumps({"labels": labels}))
        (Path(set_dir) / "photo" / "wine-c" / "01.jpg").unlink()
        (Path(set_dir) / "excluded-slugs.json").unlink()
        report = self.run_import(set_dir)
        photos = self.photos()
        self.assertEqual(photos[("wine-a", "01.jpg")][1], "negative")
        self.assertNotIn(("wine-c", "01.jpg"), photos)
        self.assertEqual(self.query("SELECT count(*) FROM test_excluded"), [(0,)])
        self.assertEqual(report.written, 0)

    def test_labels_are_per_set(self):
        first = self.standard_set()
        self.run_import(first, "my")
        labels = json.loads(json.dumps(LABELS))
        labels["wine-a"]["01.jpg"] = {"label": "negative"}
        second = FX.write_set(self.root, PHOTOS, labels, name="other")
        self.run_import(second, "other")
        self.assertEqual(self.photos("my")[("wine-a", "01.jpg")][1], "positive")
        self.assertEqual(self.photos("other")[("wine-a", "01.jpg")][1], "negative")
        self.assertEqual(self.query("SELECT count(*) FROM image"), [(6,)])

    def test_unknown_label_stops_the_import_and_writes_nothing(self):
        set_dir = FX.write_set(self.root, PHOTOS, {"wine-a": {"01.jpg": {"label": "maybe"}}})
        with self.assertRaisesRegex(IT.TestsetError, "unknown label values: maybe"):
            self.run_import(set_dir)
        self.assertEqual(self.query("SELECT count(*) FROM test_photo"), [(0,)])

    def test_missing_labels_file_stops_the_import(self):
        set_dir = FX.write_set(self.root, PHOTOS, {})
        (Path(set_dir) / "review-labels.json").unlink()
        with self.assertRaisesRegex(IT.TestsetError, "no file .*review-labels.json"):
            self.run_import(set_dir)

    def test_bad_set_name_is_refused(self):
        with self.assertRaisesRegex(IT.TestsetError, "set name"):
            self.run_import(self.standard_set(), "My Set")

    def test_a_file_that_image_holds_is_not_stored_again(self):
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO image (sha256, folder, extension, width, height) "
                     "VALUES (?, 'main', 'jpg', 1, 1)", (sha(b"photo a1"),))
        conn.commit()
        conn.close()
        report = self.run_import(self.standard_set())
        self.assertEqual((report.written, report.present), (5, 2))
        self.assertFalse(Path(IT.photo_path(self.db, sha(b"photo a1"), "jpg")).exists())
        self.assertEqual(self.query("SELECT folder FROM image WHERE sha256 = ?",
                                    sha(b"photo a1")), [("main",)])

    def test_a_real_picture_gets_its_pixel_size(self):
        from PIL import Image
        buffer = io.BytesIO()
        Image.new("RGB", (30, 20), "white").save(buffer, "PNG")
        set_dir = FX.write_set(self.root, {"wine-a/01.png": buffer.getvalue()},
                               {"wine-a": {"01.png": {"label": "positive"}}})
        report = self.run_import(set_dir)
        self.assertEqual(report.unsized, 0)
        self.assertEqual(self.query("SELECT width, height FROM image"), [(30, 20)])

    def test_the_set_directory_is_not_changed(self):
        set_dir = self.standard_set()
        before = {str(p): p.read_bytes() for p in Path(set_dir).rglob("*") if p.is_file()}
        self.run_import(set_dir)
        after = {str(p): p.read_bytes() for p in Path(set_dir).rglob("*") if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
