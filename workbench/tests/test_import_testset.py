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
        # The reason of an old exclusion is a wine comment (plan 51). "t" is no time.
        self.assertEqual(self.query("SELECT wine_slug, source, text FROM wine_comment"),
                         [("wine-c", "user", "Excluded from the benchmark: r")])
        self.assertEqual((report.excluded, report.wine_comments), (1, 1))
        self.assertEqual(self.query("SELECT wine_slug, group_no FROM test_variant ORDER BY 1"),
                         [("wine-a", 0), ("wine-b", 0)])
        self.assertEqual(self.query("SELECT set_name FROM test_set"), [("my",)])

    def test_same_bytes_are_stored_one_time(self):
        report = self.run_import(self.standard_set())
        self.assertEqual((report.written, report.present), (6, 1))
        self.assertEqual(self.query("SELECT count(*) FROM image"), [(6,)])
        path = IT.photo_path(self.db, sha(b"photo a1"), "jpg")
        self.assertEqual(Path(path).read_bytes(), b"photo a1")
        self.assertEqual(Path(path).parent.parts[-2:], ("testsets", "images"))
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
        # A wine comment belongs to no set: a new import does not remove it.
        self.assertEqual(self.query("SELECT count(*) FROM wine_comment"), [(1,)])
        self.assertEqual(report.written, 0)

    def test_a_second_import_adds_no_wine_comment_again(self):
        set_dir = self.standard_set()
        self.run_import(set_dir)
        report = self.run_import(set_dir)
        self.assertEqual((report.wine_comments, report.wine_comments_present), (0, 1))
        self.assertEqual(self.query("SELECT count(*) FROM wine_comment"), [(1,)])

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

    # Plan 24: the database is the source of the labels, so the import keeps each field.

    def columns(self, place, name):
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        try:
            return dict(conn.execute("SELECT * FROM test_photo WHERE place = ? AND "
                                     "file_name = ?", (place, name)).fetchone())
        finally:
            conn.close()

    def test_import_keeps_every_field_of_an_entry(self):
        entry = {"label": "positive", "comment": "a note", "ts": "2026-09-25T10:00:00+0300",
                 "proposed": "variant", "by": "kimi", "confidence": 0.75,
                 "source_url": "https://example.org/p", "moved_from": "wine-c",
                 "copied_from": "wine-b", "reassign_to": "__null__",
                 "prefilled_from": {"rank": 1, "run_id": "r", "score": 0.5},
                 "copy_to": "wine-b", "later": [1, 2]}
        odd = {"label": None, "delete": False, "comment": "", "confidence": 1}
        set_dir = FX.write_set(self.root, PHOTOS, {"wine-a": {"01.jpg": entry, "02.jpg": odd}})
        report = self.run_import(set_dir)
        row = self.columns("wine-a", "01.jpg")
        self.assertNotIn("comment", row)
        self.assertEqual((row["label"], row["proposed"], row["proposed_by"],
                          row["confidence"], row["reassign_to"]),
                         ("positive", "variant", "kimi", 0.75, "__null__"))
        self.assertEqual(json.loads(row["prefilled_from"]), entry["prefilled_from"])
        self.assertEqual(json.loads(row["extra"]), {"copy_to": "wine-b", "later": [1, 2]})
        # The old field `comment` is a comment of the photo. `by` makes its source a
        # script, and `ts` gives its time in UTC (plan 51).
        self.assertEqual(self.query("SELECT place, file_name, created_at, source, text FROM "
                                    "test_photo_comment"),
                         [("wine-a", "01.jpg", "2026-09-25T07:00:00Z", "script", "a note")])
        self.assertEqual(report.photo_comments, 1)
        # A value that its column cannot keep exactly goes into `extra`. So does an empty
        # comment.
        row = self.columns("wine-a", "02.jpg")
        self.assertEqual((row["label"], row["marked_delete"]), (None, 0))
        self.assertEqual(json.loads(row["extra"]), odd)
        self.assertEqual(report.extra, 2)

    def test_import_reads_the_comments_of_an_entry(self):
        items = [{"created_at": "2026-09-26T09:00:00Z", "source": "user", "text": "one"},
                 {"created_at": "2026-09-26T08:00:00Z", "source": "script", "text": "two"}]
        set_dir = FX.write_set(self.root, PHOTOS, {"wine-a": {"01.jpg": {"comments": items}}})
        self.run_import(set_dir)
        self.assertEqual(self.query("SELECT created_at, source, text FROM test_photo_comment "
                                    "ORDER BY created_at"),
                         [("2026-09-26T08:00:00Z", "script", "two"),
                          ("2026-09-26T09:00:00Z", "user", "one")])
        self.assertIsNone(self.columns("wine-a", "01.jpg")["extra"])

    def test_import_makes_wine_comments_of_the_old_notes_of_the_wines(self):
        set_dir = self.standard_set()
        document = {"version": 2, "note": "the note", "labels": LABELS,
                    "wines": {"wine-a": {"comment": "whole wine",
                                         "ts": "2026-09-16T01:33:53+0300"},
                              "wine-b": {"comment": "hunter-01: nothing", "ts": "t2", "by": "x"},
                              "no-wine": {"comment": "lost", "ts": "t3"},
                              "wine-c": {"ts": "t4"}}}
        (Path(set_dir) / "review-labels.json").write_text(json.dumps(document))
        report = self.run_import(set_dir)
        self.assertEqual((report.wine_notes, report.wine_comments,
                          report.wine_comments_left_out), (4, 3, 1))
        rows = self.query("SELECT wine_slug, created_at, source, text FROM wine_comment "
                          "ORDER BY wine_slug, text")
        self.assertEqual([row[:1] + row[2:] for row in rows],
                         [("wine-a", "user", "whole wine"),
                          ("wine-b", "script", "hunter-01: nothing"),
                          ("wine-c", "user", "Excluded from the benchmark: r")])
        self.assertEqual(rows[0][1], "2026-09-15T22:33:53Z")
        self.assertIn("left out: a wine comment of no-wine: wine_catalog holds no wine with "
                      "this slug", self.messages)
        self.assertEqual(self.query("SELECT label_note, edited_at FROM test_set"),
                         [("the note", None)])

    def test_a_set_with_page_edits_is_refused_unless_force(self):
        set_dir = self.standard_set()
        self.run_import(set_dir)
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE test_photo SET label = 'unusable' WHERE place = 'wine-a' AND "
                     "file_name = '01.jpg'")
        conn.execute("UPDATE test_set SET edited_at = '2026-09-25T18:00:00+0300'")
        conn.commit()
        conn.close()
        with self.assertRaisesRegex(IT.TestsetError, "edits of the Testset page"):
            self.run_import(set_dir)
        self.assertEqual(self.photos()[("wine-a", "01.jpg")][1], "unusable")
        IT.import_testset(self.db, "my", set_dir, self.messages.append, self.schema, force=True)
        self.assertEqual(self.photos()[("wine-a", "01.jpg")][1], "positive")
        self.assertEqual(self.query("SELECT edited_at FROM test_set"), [(None,)])

    def test_an_entry_that_is_not_an_object_stops_the_import(self):
        set_dir = FX.write_set(self.root, PHOTOS, {"wine-a": {"01.jpg": "positive"}})
        with self.assertRaisesRegex(IT.TestsetError, "wine-a/01.jpg is not a JSON object"):
            self.run_import(set_dir)

    def test_import_adds_the_tags_of_an_entry_to_the_image(self):
        # Plan 66: wine-b/02.jpg holds the bytes of wine-a/01.jpg, so both show the tags.
        labels = {"wine-a": {"01.jpg": {"label": "positive", "tags": ["Blurry", "back"]}},
                  "wine-b": {"02.jpg": {"tags": ["blurry", "glare"]}}}
        report = self.run_import(FX.write_set(self.root, PHOTOS, labels))
        # `blurry` of the two entries is one tag of one image.
        self.assertEqual((report.image_tags, report.image_tags_present), (3, 0))
        self.assertEqual(self.query("SELECT sha256, tag FROM image_tag ORDER BY rowid"),
                         [(sha(b"photo a1"), "blurry"), (sha(b"photo a1"), "back"),
                          (sha(b"photo a1"), "glare")])
        # The field leaves the entry: it goes into no column and not into `extra`.
        self.assertEqual(self.query("SELECT label, extra, ts FROM test_photo WHERE "
                                    "place = 'wine-b' AND file_name = '02.jpg'"),
                         [(None, None, None)])
        self.assertEqual(self.photos()[("wine-a", "01.jpg")][1], "positive")
        # A second import adds no row, and an import with no tags removes no tag.
        report = self.run_import(FX.write_set(self.root, PHOTOS, labels, name="again"),
                                 "two")
        self.assertEqual((report.image_tags, report.image_tags_present), (0, 3))
        self.run_import(FX.write_set(self.root, PHOTOS, {}, name="bare"), "three")
        self.assertEqual(self.query("SELECT count(*) FROM image_tag"), [(3,)])

    def test_a_bad_tags_value_stops_the_import_and_writes_nothing(self):
        for value, message in (("blurry", "is not a list"), (["two words"], "white space"),
                               ([""], "empty"), ([7], "empty")):
            with self.subTest(value=value):
                set_dir = FX.write_set(self.root, PHOTOS,
                                       {"wine-a": {"01.jpg": {"tags": value}}},
                                       name="bad-%s" % len(str(value)))
                with self.assertRaisesRegex(IT.TestsetError,
                                            "the field tags of the entry wine-a/01.jpg.*"
                                            + message):
                    self.run_import(set_dir)
        self.assertEqual(self.query("SELECT count(*) FROM test_photo"), [(0,)])
        self.assertEqual(self.query("SELECT count(*) FROM image_tag"), [(0,)])


if __name__ == "__main__":
    unittest.main()
