import hashlib
import io
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import derive  # noqa: E402
import labdb  # noqa: E402
import seed_patched as SP  # noqa: E402

WINES = ("wine-a", "wine-b", "wine-c")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def picture(size=(40, 80), transparent=True):
    """The PNG bytes of a bottle box on a transparent or a white canvas."""
    image = Image.new("RGBA" if transparent else "RGB", size,
                      (255, 255, 255, 0) if transparent else (255, 255, 255))
    ImageDraw.Draw(image).rectangle((10, 10, 29, 69), fill=(90, 30, 20))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


class FakeSam3:
    """A SAM3 client with no network. It answers the mask of the bottle box."""

    calls = 0

    def __init__(self, endpoint=None):
        pass

    def segment(self, image):
        FakeSam3.calls += 1
        mask = Image.new("L", image.size, 0)
        ImageDraw.Draw(mask).rectangle((10, 10, 29, 69), fill=255)
        return mask


class SeedPatchedTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "data" / "lab.sqlite3")
        os.makedirs(os.path.dirname(self.db))
        self.folder = self.root / "patched"
        self.folder.mkdir()
        self.real_client, derive.Sam3Client = derive.Sam3Client, FakeSam3
        FakeSam3.calls = 0
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.executemany(
                "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                "region, description, csv_photo_name, state, removed_by) VALUES "
                "(?, 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp', ?, ?)",
                [("wine-a", "Active", None), ("wine-b", "Disabled", None),
                 ("wine-c", "Removed", "import")])
            conn.execute("INSERT INTO image (sha256, folder, extension) "
                         "VALUES (?, 'main', 'webp')", (sha(b"main a"),))
            conn.execute("INSERT INTO wine_image (wine_slug, image_type, sha256, "
                         "source_name, match_method) VALUES ('wine-a', 'main', ?, "
                         "'a_0123456789.webp', 'name-unique')", (sha(b"main a"),))
        conn.close()
        self.messages = []

    def tearDown(self):
        derive.Sam3Client = self.real_client
        self.directory.cleanup()

    def patch(self, name, data):
        (self.folder / name).write_bytes(data)

    def run_seed(self):
        self.messages = []
        return SP.seed_patched(self.db, str(self.folder), self.messages.append, FakeSam3())

    def rows(self):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(
                "SELECT w.wine_slug, w.image_type, w.sha256, i.extension, w.source_name, "
                "w.match_method FROM wine_image w JOIN image i ON i.sha256 = w.sha256 "
                "ORDER BY w.wine_slug, w.image_type").fetchall()
        finally:
            conn.close()

    def patched(self):
        return {row[0]: row[2:] for row in self.rows() if row[1] == "main_patched"}

    def stored(self, data, extension):
        return Path(SP.store_of(self.db)) / ("%s.%s" % (sha(data), extension))

    def test_first_run_adds_a_row_and_a_file_for_each_patch(self):
        self.patch("wine-a.webp", b"patch a")
        self.patch("wine-b.PNG", b"patch b")
        self.patch("wine-c.png", b"patch c")
        report = self.run_seed()
        self.assertEqual((report.files, sorted(report.added), report.written), (3, list(WINES), 3))
        self.assertEqual(self.patched(), {
            "wine-a": (sha(b"patch a"), "webp", "wine-a.webp", "slug-name"),
            "wine-b": (sha(b"patch b"), "png", "wine-b.PNG", "slug-name"),
            "wine-c": (sha(b"patch c"), "png", "wine-c.png", "slug-name"),
        })
        self.assertEqual(self.stored(b"patch b", "png").read_bytes(), b"patch b")
        self.assertEqual(Path(SP.store_of(self.db)).name, "patched")

    def test_main_rows_stay(self):
        self.patch("wine-a.webp", b"patch a")
        self.run_seed()
        self.assertIn(("wine-a", "main", sha(b"main a"), "webp", "a_0123456789.webp",
                       "name-unique"), self.rows())

    def test_second_run_changes_nothing(self):
        self.patch("wine-a.webp", b"patch a")
        self.run_seed()
        report = self.run_seed()
        self.assertFalse(report.changed())
        self.assertEqual((report.unchanged, report.present), (1, 1))

    def test_new_bytes_replace_the_row_and_keep_the_old_file(self):
        self.patch("wine-a.webp", b"patch a")
        self.run_seed()
        (self.folder / "wine-a.webp").unlink()
        self.patch("wine-a.png", b"better patch a")
        report = self.run_seed()
        self.assertEqual((report.replaced, report.added, report.deleted), (["wine-a"], [], []))
        self.assertEqual(self.patched()["wine-a"],
                         (sha(b"better patch a"), "png", "wine-a.png", "slug-name"))
        self.assertTrue(self.stored(b"patch a", "webp").exists())
        self.assertTrue(any(m.startswith("replaced: wine-a") for m in self.messages))

    def test_missing_patch_file_deletes_the_row(self):
        self.patch("wine-a.webp", b"patch a")
        self.patch("wine-b.webp", b"patch b")
        self.run_seed()
        (self.folder / "wine-b.webp").unlink()
        report = self.run_seed()
        self.assertEqual(report.deleted, ["wine-b"])
        self.assertEqual(set(self.patched()), {"wine-a"})
        self.assertTrue(self.stored(b"patch b", "webp").exists())

    def test_two_files_for_one_wine_are_an_error_and_the_row_stays(self):
        self.patch("wine-a.webp", b"patch a")
        self.run_seed()
        self.patch("wine-a.png", b"other patch a")
        report = self.run_seed()
        self.assertEqual((report.errors, report.deleted, report.replaced), (1, [], []))
        self.assertEqual(self.patched()["wine-a"][0], sha(b"patch a"))

    def test_unknown_slug_gets_no_row(self):
        self.patch("wine-x.webp", b"patch x")
        report = self.run_seed()
        self.assertEqual((report.unknown, report.errors, report.written), (["wine-x"], 0, 0))
        self.assertEqual(self.patched(), {})

    def test_other_names_are_skipped(self):
        self.patch("README.md", b"# readme")
        self.patch(".DS_Store", b"x")
        self.patch("notes.txt", b"x")
        (self.folder / "_originals").mkdir()
        (self.folder / "_originals" / "wine-a.webp").write_bytes(b"old patch a")
        report = self.run_seed()
        self.assertEqual((report.files, report.skipped), (0, ["README.md", "notes.txt"]))
        self.assertEqual(self.patched(), {})

    def test_stored_file_with_wrong_bytes_is_an_error(self):
        self.patch("wine-a.webp", b"patch a")
        target = self.stored(b"patch a", "webp")
        target.parent.mkdir(parents=True)
        target.write_bytes(b"broken")
        report = self.run_seed()
        self.assertEqual((report.errors, report.added), (1, []))
        self.assertEqual(target.read_bytes(), b"broken")

    def test_main_reports_and_sets_the_exit_status(self):
        self.patch("wine-a.webp", b"patch a")
        self.patch("README.md", b"# readme")
        out = io.StringIO()
        stdout, sys.stdout = sys.stdout, out
        try:
            code = SP.main([str(self.folder), "--db", self.db])
            self.patch("wine-a.png", b"second file")
            code_error = SP.main([str(self.folder), "--db", self.db])
        finally:
            sys.stdout = stdout
        text = out.getvalue()
        self.assertEqual((code, code_error), (0, 1))
        self.assertIn("patch files: 1", text)
        self.assertIn("skipped names: 1: README.md", text)
        self.assertIn("rows added: 1", text)
        self.assertIn("result: stored", text)

    def query(self, sql, *args):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def test_patch_gets_its_pixel_size_and_a_crop(self):
        data = picture()
        self.patch("wine-a.png", data)
        report = self.run_seed()
        self.assertEqual(self.query("SELECT folder, extension, width, height FROM image "
                                    "WHERE sha256 = ?", sha(data)), [("patched", "png", 40, 80)])
        [(method, box)] = [(m, (l, t, r, b)) for m, l, t, r, b in self.query(
            "SELECT method, box_left, box_top, box_right, box_bottom FROM image_derivative "
            "WHERE source_sha256 = ?", sha(data))]
        self.assertEqual((method, box), ("crop", (10, 10, 30, 70)))
        self.assertEqual((dict(report.derivatives.methods), FakeSam3.calls), ({"crop": 1}, 0))
        self.assertEqual(self.run_seed().derivatives.present, 1)

    def test_patch_with_no_transparency_goes_to_sam3(self):
        self.patch("wine-a.png", picture(transparent=False))
        report = self.run_seed()
        self.assertEqual((dict(report.derivatives.methods), FakeSam3.calls), ({"seg": 1}, 1))

    def test_file_that_is_no_image_gets_a_row_and_no_processing(self):
        self.patch("wine-a.webp", b"patch a")
        report = self.run_seed()
        self.assertEqual((report.added, report.errors), (["wine-a"], 0))
        self.assertEqual(report.derivatives.unreadable, 1)
        self.assertEqual(self.query("SELECT width FROM image WHERE sha256 = ?",
                                    sha(b"patch a")), [(None,)])

    def test_missing_folder_stops_the_run(self):
        with self.assertRaisesRegex(SP.SeedError, "no patch folder"):
            SP.seed_patched(self.db, str(self.root / "none"))


if __name__ == "__main__":
    unittest.main()
