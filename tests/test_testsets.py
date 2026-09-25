"""The reads and the writes of the Testset page (plan 24): `pipeline/testsets.py`."""
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX  # noqa: E402
import import_testset as IT  # noqa: E402
import testsets as TS  # noqa: E402


def jpeg(size, orientation=None):
    buffer = io.BytesIO()
    exif = Image.Exif()
    if orientation:
        exif[0x0112] = orientation
    Image.new("RGB", size, "white").save(buffer, "JPEG", exif=exif)
    return buffer.getvalue()


PHOTOS = {
    "wine-a/02_conf080.jpg": jpeg((40, 20)),
    "wine-a/01_conf095.jpg": jpeg((40, 20), orientation=6),
    "wine-c/01.jpg": jpeg((30, 30)),
    "unknown-wine/01.jpg": jpeg((10, 10)),
    "__null__/n1.jpg": jpeg((12, 12)),
}
LABELS = {"wine-a": {"02_conf080.jpg": {"label": None, "copy_to": "wine-b",
                                        "comment": "keep", "ts": "t0"}}}
CARDS = {"wine-a": {"main_image_url": "/images/main/a.webp", "_patch_url": None},
         "wine-c": {"main_image_url": "/images/main/c.webp",
                    "_patch_image_url": "/images/patched/c.webp",
                    "_patch_url": "/images/patched/c.webp"}}


class TestsetsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(
            self.root, slugs=("wine-a", "wine-b", "wine-c", "wine-d", "wine-e"))
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE wine_catalog SET state = 'Removed', removed_by = 'person' "
                     "WHERE wine_slug IN ('wine-c', 'wine-e')")
        conn.execute("UPDATE wine_catalog SET state = 'Disabled' WHERE wine_slug = 'wine-d'")
        conn.commit()
        conn.close()
        set_dir = FX.write_set(self.root, PHOTOS, LABELS, groups=[["wine-a", "wine-c"]])
        IT.import_testset(self.db, "my", set_dir, lambda m: None, self.schema)

    def tearDown(self):
        self.directory.cleanup()

    def view(self, set_name="my"):
        conn = sqlite3.connect(self.db)
        try:
            return TS.set_view(conn, set_name, lambda c: CARDS)
        finally:
            conn.close()

    def write(self, function, *args):
        conn = sqlite3.connect(self.db)
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        try:
            answer = function(conn, "my", *args)
            conn.execute("COMMIT")
            return answer
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def query(self, sql, *args):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def row(self, slug):
        return next(r for r in self.view()["rows"] if r["slug"] == slug)

    def test_the_rows_follow_the_answer_of_the_owner(self):
        rows = self.view()["rows"]
        self.assertEqual([r["slug"] for r in rows],
                         ["__null__", "__drawer__", "unknown-wine", "wine-a", "wine-b",
                          "wine-c", "wine-d"])
        by_slug = {r["slug"]: r for r in rows}
        self.assertTrue(by_slug["__null__"]["null_row"])
        self.assertEqual(by_slug["__null__"]["name"], TS.NULL_NAME)
        self.assertTrue(by_slug["__drawer__"]["drawer_row"])
        self.assertEqual((by_slug["__drawer__"]["name"], by_slug["__drawer__"]["photos"],
                          by_slug["__drawer__"]["catalog_only"]), (TS.DRAWER_NAME, [], False))
        self.assertEqual({s: r["state"] for s, r in by_slug.items()},
                         {"__null__": None, "__drawer__": None, "unknown-wine": None,
                          "wine-a": "Active",
                          "wine-b": "Active", "wine-c": "Removed", "wine-d": "Disabled"})
        self.assertFalse(by_slug["unknown-wine"]["in_catalog"])
        self.assertEqual([s for s, r in by_slug.items() if r["catalog_only"]],
                         ["wine-b", "wine-d"])

    def test_a_row_holds_the_card_image_the_group_and_the_photos(self):
        wine_a, wine_c = self.row("wine-a"), self.row("wine-c")
        self.assertEqual((wine_a["bottle_url"], wine_a["patched"]),
                         ("/images/main/a.webp", False))
        self.assertEqual((wine_c["bottle_url"], wine_c["patched"]),
                         ("/images/patched/c.webp", True))
        self.assertEqual(wine_a["group"], wine_c["group"])
        self.assertEqual(self.view()["groups"][wine_a["group"]]["slugs"], ["wine-a", "wine-c"])
        # The rank of the name gives the order, as `scan_photos` of the old tool.
        self.assertEqual([p["file"] for p in wine_a["photos"]],
                         ["01_conf095.jpg", "02_conf080.jpg"])
        self.assertEqual(wine_a["min_conf"], 80)
        photo = wine_a["photos"][1]
        self.assertRegex(photo["url"], r"^/images/testset/[0-9a-f]{64}\.jpg$")
        self.assertEqual((photo["width"], photo["height"], photo["conf"]), (40, 20, 80))
        self.assertEqual(photo["entry"], LABELS["wine-a"]["02_conf080.jpg"])

    def test_the_first_set_is_the_default_and_an_unknown_set_is_404(self):
        self.assertEqual(self.view(None)["set"], "my")
        self.assertEqual([s["name"] for s in self.view()["sets"]], ["my"])
        with self.assertRaises(TS.TestsetError) as caught:
            self.view("other")
        self.assertEqual(caught.exception.code, 404)

    def test_a_label_keeps_the_other_fields_and_leaves_extra(self):
        answer = self.write(TS.set_label, "wine-a", "02_conf080.jpg", "positive")
        entry = answer["photo"]["entry"]
        self.assertEqual({k: v for k, v in entry.items() if k != "ts"},
                         {"label": "positive", "copy_to": "wine-b", "comment": "keep"})
        self.assertNotEqual(entry["ts"], "t0")
        self.assertEqual(answer["counts"]["positive"], 1)
        self.assertIsNotNone(self.query("SELECT edited_at FROM test_set")[0][0])

    def test_the_clear_of_the_last_field_removes_the_entry(self):
        self.write(TS.set_label, "wine-c", "01.jpg", "negative")
        answer = self.write(TS.set_label, "wine-c", "01.jpg", None)
        self.assertEqual(answer["photo"]["entry"], {})
        self.assertEqual(self.query("SELECT ts FROM test_photo WHERE place = 'wine-c'"),
                         [(None,)])

    def test_label_errors(self):
        for args, code in ((("__null__", "n1.jpg", "negative"), 400),
                           (("wine-a", "02_conf080.jpg", "maybe"), 400),
                           (("wine-a", "missing.jpg", "positive"), 404),
                           (("", "01.jpg", "positive"), 400)):
            with self.assertRaises(TS.TestsetError) as caught:
                self.write(TS.set_label, *args)
            self.assertEqual(caught.exception.code, code, args)
        self.write(TS.set_label, "__null__", "n1.jpg", "unusable")
        with self.assertRaises(TS.TestsetError) as caught, \
                closing(sqlite3.connect(self.db)) as conn:
            TS.set_label(conn, "other", "wine-a", "01.jpg", "positive")
        self.assertEqual(caught.exception.code, 404)

    def test_the_delete_mark(self):
        answer = self.write(TS.set_delete, "wine-a", "01_conf095.jpg", True)
        self.assertIs(answer["photo"]["entry"]["delete"], True)
        self.assertEqual(answer["counts"]["deleting"], 1)
        answer = self.write(TS.set_delete, "wine-a", "01_conf095.jpg", False)
        self.assertEqual(answer["photo"]["entry"], {})
        with self.assertRaises(TS.TestsetError):
            self.write(TS.set_delete, "wine-a", "01_conf095.jpg", "yes")

    def test_the_comment_of_a_photo(self):
        answer = self.write(TS.set_comment, "wine-c", "01.jpg", "  line one\r\nline two  ")
        self.assertEqual(answer["photo"]["entry"]["comment"], "line one\nline two")
        answer = self.write(TS.set_comment, "wine-c", "01.jpg", "   ")
        self.assertNotIn("comment", answer["photo"]["entry"])
        for text in ("x" * (TS.TEXT_MAX + 1), "bell\x07"):
            with self.assertRaises(TS.TestsetError) as caught:
                self.write(TS.set_comment, "wine-c", "01.jpg", text)
            self.assertEqual(caught.exception.code, 400)

    def test_the_box_is_inside_the_photo_after_its_orientation(self):
        # 01_conf095.jpg is 40 x 20 in its header, and the EXIF orientation 6 turns it.
        answer = self.write(TS.set_box, "wine-a", "01_conf095.jpg", [0, 0, 20, 40])
        self.assertEqual(answer["photo"]["entry"]["box"], [0, 0, 20, 40])
        self.assertEqual(answer["counts"]["boxes"], 1)
        for box in ([0, 0, 40, 20], [5, 5, 5, 9], [0, 0, 1], [0, 0, 1.5, 2], [True, 0, 1, 1]):
            with self.assertRaises(TS.TestsetError) as caught:
                self.write(TS.set_box, "wine-a", "01_conf095.jpg", box)
            self.assertEqual(caught.exception.code, 400, box)
        answer = self.write(TS.set_box, "wine-a", "01_conf095.jpg", None)
        self.assertNotIn("box", answer["photo"]["entry"])
        self.assertEqual(TS.oriented_size(self.root / "set" / "photo" / "wine-a" /
                                          "01_conf095.jpg"), (20, 40))

    def test_the_note_of_a_wine(self):
        answer = self.write(TS.set_wine_note, "wine-c", "a removed wine keeps its note")
        self.assertEqual(answer["note"], "a removed wine keeps its note")
        self.assertEqual(self.row("wine-c")["note"], "a removed wine keeps its note")
        self.assertEqual(answer["counts"]["wine_notes"], 1)
        self.write(TS.set_wine_note, "wine-c", "")
        self.assertEqual(self.query("SELECT count(*) FROM test_wine_note"), [(0,)])
        with self.assertRaises(TS.TestsetError) as caught:
            self.write(TS.set_wine_note, "no-such-wine", "x")
        self.assertEqual(caught.exception.code, 404)

    def test_the_exclusion_needs_a_reason(self):
        with self.assertRaises(TS.TestsetError) as caught:
            self.write(TS.set_excluded, "wine-a", True, "  ")
        self.assertEqual(caught.exception.code, 400)
        with self.assertRaises(TS.TestsetError):
            self.write(TS.set_excluded, "wine-a", True, "x" * (TS.REASON_MAX + 1))
        answer = self.write(TS.set_excluded, "wine-a", True, " wrong bottle photo ")
        self.assertEqual(answer["entry"]["reason"], "wrong bottle photo")
        self.assertEqual((self.row("wine-a")["excluded"], self.row("wine-a")["exclude_reason"]),
                         (True, "wrong bottle photo"))
        self.write(TS.set_excluded, "wine-a", False, None)
        self.assertEqual(self.query("SELECT count(*) FROM test_excluded"), [(0,)])
        self.write(TS.set_excluded, "__null__", True, "the NULL wine too")

    def test_a_write_to_a_removed_wine_is_allowed(self):
        answer = self.write(TS.set_label, "wine-c", "01.jpg", "positive")
        self.assertEqual(answer["photo"]["entry"]["label"], "positive")
        self.assertEqual(self.row("wine-c")["state"], "Removed")

    def test_the_entry_columns_keep_only_exact_values(self):
        row = TS.entry_columns({"label": "positive", "confidence": 1, "box": [0, 0, 5, 5],
                                "delete": True}, (4, 4))
        self.assertEqual((row["label"], row["confidence"], row["marked_delete"], row["box_left"]),
                         ("positive", None, 1, None))
        self.assertEqual(json.loads(row["extra"]), {"confidence": 1, "box": [0, 0, 5, 5]})
        self.assertEqual(TS.entry_of(row), {"label": "positive", "delete": True,
                                            "confidence": 1, "box": [0, 0, 5, 5]})

    # The row "No Match" is the NULL place; the sidebar is the Drawer (plan 36).

    def test_a_move_to_the_null_place_and_back(self):
        self.write(TS.set_label, "wine-a", "01_conf095.jpg", "positive")
        self.write(TS.set_box, "wine-a", "01_conf095.jpg", [0, 0, 10, 10])
        answer = self.write(TS.move_photo, "wine-a", "01_conf095.jpg", TS.NULL_SLUG)
        self.assertEqual((answer["photo"]["place"], answer["photo"]["file"]),
                         (TS.NULL_SLUG, "01_conf095.jpg"))
        entry = answer["photo"]["entry"]
        self.assertNotIn("label", entry)
        self.assertEqual((entry["moved_from"], entry["box"]), ("wine-a", [0, 0, 10, 10]))
        self.assertEqual(answer["counts"]["no_match"], 2)
        null = self.row(TS.NULL_SLUG)
        self.assertEqual([p["file"] for p in null["photos"]], ["01_conf095.jpg", "n1.jpg"])
        answer = self.write(TS.move_photo, TS.NULL_SLUG, "01_conf095.jpg", "wine-b")
        self.assertEqual(answer["photo"]["entry"]["moved_from"], TS.NULL_SLUG)
        self.assertFalse(self.row("wine-b")["catalog_only"])

    def test_the_drawer_holds_a_photo_with_no_label(self):
        self.write(TS.set_label, "wine-a", "01_conf095.jpg", "positive")
        answer = self.write(TS.move_photo, "wine-a", "01_conf095.jpg", TS.DRAWER_SLUG)
        self.assertEqual(answer["photo"]["place"], TS.DRAWER_SLUG)
        self.assertNotIn("label", answer["photo"]["entry"])
        self.assertEqual((answer["counts"]["drawer"], answer["counts"]["no_match"]), (1, 1))
        self.assertEqual([p["file"] for p in self.row(TS.DRAWER_SLUG)["photos"]],
                         ["01_conf095.jpg"])
        # A Drawer photo takes no label. The comment and the delete mark stay allowed.
        for label in TS.LABELS:
            with self.assertRaises(TS.TestsetError) as caught:
                self.write(TS.set_label, TS.DRAWER_SLUG, "01_conf095.jpg", label)
            self.assertEqual(caught.exception.code, 400, label)
        self.write(TS.set_comment, TS.DRAWER_SLUG, "01_conf095.jpg", "later")
        self.write(TS.set_delete, TS.DRAWER_SLUG, "01_conf095.jpg", True)
        answer = self.write(TS.move_photo, TS.DRAWER_SLUG, "01_conf095.jpg", TS.NULL_SLUG)
        self.assertEqual((answer["photo"]["entry"]["moved_from"], answer["counts"]["drawer"],
                          answer["counts"]["no_match"]), (TS.DRAWER_SLUG, 0, 2))

    def test_an_upload_to_the_drawer(self):
        answer = self.write(TS.upload_photo, TS.DRAWER_SLUG, jpeg((25, 15)), "d.jpg")
        self.assertEqual((answer["place"], answer["file"], answer["counts"]["drawer"]),
                         (TS.DRAWER_SLUG, "d.jpg", 1))

    def test_a_taken_name_gets_a_suffix_and_the_other_fields_stay(self):
        answer = self.write(TS.move_photo, "wine-c", "01.jpg", "unknown-wine")
        self.assertEqual(answer["photo"]["file"], "01_moved2.jpg")
        answer = self.write(TS.move_photo, "wine-a", "02_conf080.jpg", "wine-c")
        entry = answer["photo"]["entry"]
        self.assertEqual({k: v for k, v in entry.items() if k != "ts"},
                         {"moved_from": "wine-a", "copy_to": "wine-b", "comment": "keep"})

    def test_move_errors(self):
        for args, code in ((("wine-a", "02_conf080.jpg", "wine-a"), 400),
                           (("wine-a", "02_conf080.jpg", "no-such-wine"), 404),
                           (("wine-a", "missing.jpg", TS.NULL_SLUG), 404),
                           (("wine-a", "02_conf080.jpg", ""), 400)):
            with self.assertRaises(TS.TestsetError) as caught:
                self.write(TS.move_photo, *args)
            self.assertEqual(caught.exception.code, code, args)


    # A drop of files from the file manager (owner answers of 2026-09-25T18:25:10).

    def png(self, size):
        buffer = io.BytesIO()
        Image.new("RGB", size, "black").save(buffer, "PNG")
        return buffer.getvalue()

    def test_an_upload_to_the_null_place_stores_the_file_with_no_label(self):
        data = jpeg((25, 15))
        answer = self.write(TS.upload_photo, TS.NULL_SLUG, data, "IMG 1.JPG")
        self.assertEqual((answer["place"], answer["file"]), (TS.NULL_SLUG, "IMG 1.jpg"))
        self.assertEqual((answer["photo"]["width"], answer["photo"]["entry"]), (25, {}))
        self.assertEqual(answer["counts"]["no_match"], 2)
        digest = answer["photo"]["sha256"]
        stored = Path(self.db).parent / "images" / "testset" / ("%s.jpg" % digest)
        self.assertEqual(stored.read_bytes(), data)
        self.assertEqual(self.query("SELECT folder, extension, width, height FROM image "
                                    "WHERE sha256 = ?", digest),
                         [("testset", "jpg", 25, 15)])
        self.assertEqual(self.query("SELECT label, ts FROM test_photo WHERE file_name = ?",
                                    "IMG 1.jpg"), [(None, None)])
        self.assertIn("IMG 1.jpg", [p["file"] for p in self.row(TS.NULL_SLUG)["photos"]])
        self.assertIsNotNone(self.query("SELECT edited_at FROM test_set")[0][0])

    def test_the_same_image_keeps_the_name_of_the_set_in_another_place(self):
        # The bytes of `__null__/n1.jpg` of the fixture.
        data = jpeg((12, 12))
        with self.assertRaises(TS.TestsetError) as caught:
            self.write(TS.upload_photo, TS.NULL_SLUG, data, "other.jpg")
        self.assertEqual(caught.exception.code, 409)
        self.assertIn("holds this image already as n1.jpg", str(caught.exception))
        answer = self.write(TS.upload_photo, "wine-b", data, "other.jpg")
        self.assertEqual(answer["file"], "n1.jpg")
        self.assertEqual(self.query("SELECT count(*) FROM image WHERE sha256 = ?",
                                    answer["photo"]["sha256"]), [(1,)])
        self.assertFalse(self.row("wine-b")["catalog_only"])

    def test_a_taken_name_of_another_image_gets_the_suffix_upload(self):
        answer = self.write(TS.upload_photo, "wine-c", jpeg((31, 31)), "01.jpg")
        self.assertEqual(answer["file"], "01_upload2.jpg")

    def test_the_file_name_comes_from_the_name_and_the_bytes(self):
        for name, data, want in (("../dir/a*b.jpeg", self.png((5, 5)), "a_b.png"),
                                 ("", jpeg((6, 6)), "upload.jpg"),
                                 (".hidden.jpg", jpeg((7, 7)), "hidden.jpg"),
                                 ("вино 2.jpg", jpeg((8, 8)), "вино 2.jpg")):
            answer = self.write(TS.upload_photo, "wine-d", data, name)
            self.assertEqual(answer["file"], want, name)

    def test_upload_errors(self):
        for args, code in (((TS.NULL_SLUG, b"", "a.jpg"), 400),
                           ((TS.NULL_SLUG, b"not an image", "a.jpg"), 400),
                           ((TS.NULL_SLUG, b"x" * (TS.UPLOAD_MAX + 1), "a.jpg"), 413),
                           (("no-such-wine", jpeg((9, 9)), "a.jpg"), 404),
                           (("", jpeg((9, 9)), "a.jpg"), 400)):
            with self.assertRaises(TS.TestsetError) as caught:
                self.write(TS.upload_photo, *args)
            self.assertEqual(caught.exception.code, code, args[0])
        conn = sqlite3.connect(self.db)
        try:
            with self.assertRaises(TS.TestsetError) as caught:
                TS.upload_photo(conn, "other", TS.NULL_SLUG, jpeg((9, 9)), "a.jpg")
            self.assertEqual(caught.exception.code, 404)
        finally:
            conn.close()
        self.assertEqual(self.query("SELECT count(*) FROM test_photo"), [(len(PHOTOS),)])


if __name__ == "__main__":
    unittest.main()
