import contextlib
import hashlib
import io
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import labdb  # noqa: E402
import seed_images as SEED  # noqa: E402

# The script whose match rule `seed_images.py` copies.
BUILD_CATALOG = ROOT.parent / "svoe-wino-hackaton" / "scripts" / "build_catalog.py"


def sha(data):
    return hashlib.sha256(data).hexdigest()


class SeedImagesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")
        self.uploads = self.root / "uploads"
        self.uploads.mkdir()
        self.store = self.root / "images" / "main"
        labdb.connect(self.db, create=True).close()

    def tearDown(self):
        self.directory.cleanup()

    def add_wine(self, slug, photo, state="Active"):
        conn = sqlite3.connect(self.db)
        conn.execute(
            "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
            "region, grapes, description, csv_photo_name, state, removed_by) "
            "VALUES (?, 'Вино', 'Винодельня', 'Белое', 'Соломенный', 'Крым', NULL, "
            "'Описание', ?, ?, ?)",
            (slug, photo, state, "import" if state == "Removed" else None))
        conn.commit()
        conn.close()

    def upload(self, name, data):
        (self.uploads / name).write_bytes(data)
        return sha(data)

    def run_seed(self):
        messages = []
        report = SEED.seed_images(self.db, str(self.uploads), messages.append)
        return report, messages

    def query(self, sql, *args):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def images(self):
        return self.query("SELECT wine_slug, image_type, sha256, extension, source_name, "
                          "match_method FROM wine_image ORDER BY wine_slug")

    # -- the match

    def test_unique_name_match_stores_the_file_and_the_row(self):
        self.add_wine("beloe", "Вино Белое.webp")
        digest = self.upload("Vino_Beloe_0123456789.webp", b"bottle")
        report, messages = self.run_seed()
        self.assertEqual(messages, [])
        self.assertEqual(dict(report.methods), {"name-unique": 1})
        self.assertEqual((report.added, report.written), (1, 1))
        self.assertEqual(self.images(), [("beloe", "main", digest, "webp",
                                          "Vino_Beloe_0123456789.webp", "name-unique")])
        self.assertEqual((self.store / (digest + ".webp")).read_bytes(), b"bottle")

    def test_extension_is_lower_case(self):
        self.add_wine("beloe", "Вино Белое.JPG")
        digest = self.upload("Vino_Beloe_0123456789.JPG", b"bottle")
        self.run_seed()
        self.assertEqual(self.images()[0][3], "jpg")
        self.assertTrue((self.store / (digest + ".jpg")).is_file())

    def test_second_lookup_keeps_the_extension_of_the_photo_name(self):
        # Strapi converted `label.png` to WebP and kept `png` in the name.
        self.add_wine("label", "label.png")
        digest = self.upload("label_png_0123456789.webp", b"label")
        self.run_seed()
        self.assertEqual(self.images(), [("label", "main", digest, "webp",
                                          "label_png_0123456789.webp", "name-unique")])

    def test_resized_variant_and_name_without_suffix_are_left_out(self):
        self.add_wine("beloe", "Вино Белое.webp")
        self.upload("thumbnail_Vino_Beloe_0123456789.webp", b"small")
        self.upload("Vino_Beloe.webp", b"no suffix")
        report, messages = self.run_seed()
        self.assertEqual(dict(report.no_match), {"no candidate": 1})
        self.assertEqual(messages, ["no match: beloe: no upload file fits the photo "
                                    "name 'Вино Белое.webp'"])
        self.assertEqual(self.images(), [])

    def test_identical_copies_match_with_the_first_name(self):
        self.add_wine("muskat", "Агора_Мускат.webp")
        digest = self.upload("Agora_Muskat_bbbbbbbbbb.webp", b"same")
        self.upload("Agora_Muskat_aaaaaaaaaa.webp", b"same")
        report, messages = self.run_seed()
        self.assertEqual(messages, [])
        self.assertEqual(self.images(), [("muskat", "main", digest, "webp",
                                          "Agora_Muskat_aaaaaaaaaa.webp", "name-identical")])
        self.assertEqual(report.written, 1)

    def test_different_copies_give_no_match_and_the_run_goes_on(self):
        self.add_wine("muskat", "Агора_Мускат.webp")
        self.add_wine("beloe", "Вино Белое.webp")
        self.upload("Agora_Muskat_aaaaaaaaaa.webp", b"one")
        self.upload("Agora_Muskat_bbbbbbbbbb.webp", b"two")
        digest = self.upload("Vino_Beloe_0123456789.webp", b"bottle")
        report, messages = self.run_seed()
        self.assertEqual(dict(report.no_match), {"different bytes": 1})
        self.assertEqual(len(messages), 1)
        self.assertTrue(messages[0].startswith("no match: muskat: 2 upload files fit"))
        self.assertEqual([row[:3] for row in self.images()], [("beloe", "main", digest)])
        self.assertEqual(os.listdir(self.store), [digest + ".webp"])

    def test_wines_that_share_a_file_get_one_file_and_two_rows(self):
        self.add_wine("a", "Вино Белое.webp")
        self.add_wine("b", "Вино Белое.webp")
        digest = self.upload("Vino_Beloe_0123456789.webp", b"bottle")
        report, _ = self.run_seed()
        self.assertEqual((report.added, report.written, report.present), (2, 1, 0))
        self.assertEqual([row[:3] for row in self.images()],
                         [("a", "main", digest), ("b", "main", digest)])

    def test_each_state_gets_an_image(self):
        self.add_wine("a", "a.webp")
        self.add_wine("d", "d.webp", "Disabled")
        self.add_wine("r", "r.webp", "Removed")
        for slug in "adr":
            self.upload("%s_0123456789.webp" % slug, slug.encode())
        self.run_seed()
        self.assertEqual([row[0] for row in self.images()], ["a", "d", "r"])

    # -- a second run

    def test_second_run_changes_nothing(self):
        self.add_wine("beloe", "Вино Белое.webp")
        self.upload("Vino_Beloe_0123456789.webp", b"bottle")
        self.run_seed()
        report, messages = self.run_seed()
        self.assertEqual(messages, [])
        self.assertEqual((report.added, report.unchanged), (0, 1))
        self.assertEqual((report.written, report.present), (0, 1))
        self.assertEqual(len(self.images()), 1)

    def test_second_run_writes_a_missing_file_again(self):
        self.add_wine("beloe", "Вино Белое.webp")
        digest = self.upload("Vino_Beloe_0123456789.webp", b"bottle")
        self.run_seed()
        (self.store / (digest + ".webp")).unlink()
        report, _ = self.run_seed()
        self.assertEqual((report.added, report.unchanged, report.written), (0, 1, 1))
        self.assertTrue((self.store / (digest + ".webp")).is_file())

    def test_other_main_row_stays_and_is_a_conflict(self):
        self.add_wine("beloe", "Вино Белое.webp")
        self.upload("Vino_Beloe_0123456789.webp", b"bottle")
        old = sha(b"old")
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO wine_image VALUES ('beloe', 'main', ?, 'webp', "
                     "'old.webp', 'name-unique')", (old,))
        conn.commit()
        conn.close()
        report, messages = self.run_seed()
        self.assertEqual((report.conflicts, report.added, report.written), (1, 0, 0))
        self.assertTrue(messages[0].startswith("conflict: beloe: the database holds main"))
        self.assertEqual([row[2] for row in self.images()], [old])
        self.assertFalse(self.store.exists() and os.listdir(self.store))

    def test_stored_file_with_other_bytes_is_an_error_and_stays(self):
        self.add_wine("beloe", "Вино Белое.webp")
        digest = self.upload("Vino_Beloe_0123456789.webp", b"bottle")
        self.store.mkdir(parents=True)
        (self.store / (digest + ".webp")).write_bytes(b"damaged")
        report, messages = self.run_seed()
        self.assertEqual((report.errors, report.added), (1, 0))
        self.assertIn("the stored bytes do not agree with the name", messages[0])
        self.assertEqual((self.store / (digest + ".webp")).read_bytes(), b"damaged")
        self.assertEqual(self.images(), [])

    # -- the command

    def test_main_reports_and_exits_0_with_no_match(self):
        self.add_wine("beloe", "Вино Белое.webp")
        self.add_wine("none", "Нет.webp")
        self.upload("Vino_Beloe_0123456789.webp", b"bottle")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = SEED.main(["--db", self.db, str(self.uploads)])
        self.assertEqual(status, 0)
        text = out.getvalue()
        self.assertIn("no match: none: no upload file fits", text)
        self.assertIn("matched: 1 (name-unique 1)", text)
        self.assertIn("no match: 1 (no candidate 1)", text)
        self.assertIn("rows added: 1", text)
        self.assertIn("result: stored", text)

    def test_main_exits_1_on_a_store_error(self):
        self.add_wine("beloe", "Вино Белое.webp")
        digest = self.upload("Vino_Beloe_0123456789.webp", b"bottle")
        self.store.mkdir(parents=True)
        (self.store / (digest + ".webp")).write_bytes(b"damaged")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(SEED.main(["--db", self.db, str(self.uploads)]), 1)

    def test_missing_uploads_folder_stops_the_run(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            status = SEED.main(["--db", self.db, str(self.root / "nothing")])
        self.assertEqual(status, 1)
        self.assertIn("no uploads folder at", err.getvalue())

    def test_missing_database_stops_the_run_and_creates_no_file(self):
        db = self.root / "other.sqlite3"
        with contextlib.redirect_stderr(io.StringIO()):
            status = SEED.main(["--db", str(db), str(self.uploads)])
        self.assertEqual(status, 1)
        self.assertFalse(db.exists())

    # -- the table

    def insert(self, slug, image_type, data):
        conn = sqlite3.connect(self.db)
        try:
            conn.execute("INSERT INTO wine_image VALUES (?, ?, ?, 'webp', 'x.webp', "
                         "'manual')", (slug, image_type, sha(data)))
            conn.commit()
        finally:
            conn.close()

    def test_table_holds_one_main_and_one_main_patched_for_each_wine(self):
        self.add_wine("a", "a.webp")
        self.insert("a", "main", b"1")
        self.insert("a", "main_patched", b"2")
        self.insert("a", "front", b"3")
        self.insert("a", "front", b"4")
        for image_type in ("main", "main_patched"):
            with self.assertRaises(sqlite3.IntegrityError):
                self.insert("a", image_type, b"5")

    def test_table_refuses_an_unknown_type_and_an_unknown_wine(self):
        self.add_wine("a", "a.webp")
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert("a", "testset", b"1")
        conn = labdb.connect(self.db)
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO wine_image VALUES ('b', 'main', ?, 'webp', "
                         "'x.webp', 'manual')", (sha(b"1"),))
        conn.close()

    @unittest.skipUnless(BUILD_CATALOG.is_file(), "build_catalog.py is not present")
    def test_match_rule_is_equal_to_build_catalog(self):
        sys.path.insert(0, str(BUILD_CATALOG.parent))
        try:
            import build_catalog as BC
        finally:
            sys.path.remove(str(BUILD_CATALOG.parent))
        self.assertEqual((SEED.RU, SEED.HASH.pattern, SEED.VARIANT.pattern),
                         (BC.RU, BC.HASH.pattern, BC.VARIANT.pattern))
        for name in ("Агора Резерв Яхтинг Совиньон — копия.webp", "Arie 2020 KFB.webp",
                     "KATHARON Мезенка: Рислинг сухое.webp", "label.png", "Щёчка ЪЫЬ.JPG"):
            for keep_ext in (False, True):
                self.assertEqual(SEED.norm(name, keep_ext), BC.norm(name, keep_ext))
        for name in ("Vino_Beloe_0123456789.webp", "thumbnail_a_0123456789.webp", "a.webp"):
            self.upload(name, b"x")
        self.assertEqual(SEED.index_uploads(str(self.uploads)),
                         BC.index_uploads(str(self.uploads)))


if __name__ == "__main__":
    unittest.main()
