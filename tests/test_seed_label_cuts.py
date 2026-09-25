import os
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tests"))
import alternatives  # noqa: E402
import embeddings  # noqa: E402
import labdb  # noqa: E402
import seed_label_cuts  # noqa: E402
from test_alternatives import DownSam3, FakeSam3, instance, picture, sha  # noqa: E402

WINE_COLUMNS = ("wine_slug, name, producer, category, color, region, grapes, description, "
                "csv_photo_name, state, removed_by")
WINES = [("wine-a", "Вино a", "Винодельня", "Белое", "Соломенный", "Крым", None,
          "Описание a", "a.webp", "Active", None),
         ("wine-b", "Вино b", "Винодельня", "Красное", "Рубиновый", "Кубань", None,
          "Описание b", "b.webp", "Active", None)]
LABEL_STEPS = [{"step": "segment", "target": "label"}, {"step": "remove_background"},
               {"step": "white_background"}]


class SeedLabelCutsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.directory.name, "lab.sqlite3")
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.executemany("INSERT INTO wine_catalog (%s) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
                             % WINE_COLUMNS, WINES)
        # Two full originals (a card image and a full_front photo) and one close-up.
        self.main = self.store(conn, "wine-a", "main", "main", picture(colour=(90, 30, 20)))
        self.front = self.store(conn, "wine-b", "full_front", "additional",
                                picture(colour=(20, 30, 90)))
        self.close_up = self.store(conn, "wine-b", "label_front", "additional",
                                   picture(colour=(20, 90, 30)))
        conn.close()
        self.logs = []

    def tearDown(self):
        self.directory.cleanup()

    def store(self, conn, slug, image_type, folder, data):
        digest = sha(data)
        path = alternatives.file_path(self.db, folder, digest, "png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Path(path).write_bytes(data)
        with conn:
            conn.execute("INSERT INTO image (sha256, folder, extension, width, height) "
                         "VALUES (?, ?, 'png', 40, 80) ON CONFLICT DO NOTHING",
                         (digest, folder))
            conn.execute("INSERT INTO wine_image (wine_slug, image_type, sha256, source_name, "
                         "match_method) VALUES (?, ?, ?, 'x.png', 'slug-name')",
                         (slug, image_type, digest))
        return digest

    def seed(self, segmenter, limit=None):
        return seed_label_cuts.seed_label_cuts(self.db, self.logs.append, segmenter, limit)

    def label_rows(self):
        with closing(labdb.connect(self.db)) as conn:
            return {row[0]: row[1:] for row in conn.execute(
                "SELECT source_sha256, method, settings, sha256, box_left, box_top, "
                "box_right, box_bottom FROM image_derivative WHERE kind = 'label'")}

    def test_each_full_original_gets_a_label_cut(self):
        sam3 = FakeSam3()
        report = self.seed(sam3)
        self.assertEqual((report.originals, report.written, report.present), (2, 2, 0))
        self.assertEqual(sam3.instances_calls, [alternatives.DETECT_TEXTS] * 2)
        rows = self.label_rows()
        self.assertEqual(set(rows), {self.main, self.front})
        method, settings, derived, *box = rows[self.main]
        self.assertEqual((method, settings), ("seg", alternatives.SETTINGS_LABEL))
        # The cut lies inside the bottle of the picture (10, 10, 30, 70), at the label.
        left, top, right, bottom = box
        self.assertTrue(10 <= left < right <= 30 and 35 <= top < bottom <= 65, box)
        path = alternatives.file_path(self.db, labdb.DERIVED_FOLDER, derived, "png")
        with Image.open(path) as cut:
            self.assertEqual(cut.size, (right - left, bottom - top))

    def test_a_second_run_asks_sam3_for_nothing(self):
        self.seed(FakeSam3())
        sam3 = FakeSam3()
        report = self.seed(sam3)
        self.assertEqual((report.written, report.present), (0, 2))
        self.assertEqual(sam3.instances_calls, [])

    def test_a_package_row_does_not_count_as_a_label_cut(self):
        with closing(labdb.connect(self.db)) as conn, conn:
            conn.execute("INSERT INTO image (sha256, folder, extension, width, height) "
                         "VALUES (?, 'cropped', 'png', 20, 60)", ("c" * 64,))
            conn.execute("INSERT INTO image_derivative (source_sha256, kind, method, settings, "
                         "sha256, box_left, box_top, box_right, box_bottom) "
                         "VALUES (?, 'package', 'crop', 'x', ?, 10, 10, 30, 70)",
                         (self.main, "c" * 64))
        self.assertEqual(self.seed(FakeSam3()).written, 2)
        with closing(labdb.connect(self.db)) as conn:
            kinds = [row[0] for row in conn.execute(
                "SELECT kind FROM image_derivative WHERE source_sha256 = ? ORDER BY kind",
                (self.main,))]
        self.assertEqual(kinds, ["label", "package"])

    def test_no_label_gives_no_row_and_the_next_run_asks_again(self):
        report = self.seed(FakeSam3([instance("bottle", (10, 10, 30, 70))]))
        self.assertEqual((report.written, sorted(report.no_label)),
                         (0, sorted([self.main, self.front])))
        self.assertEqual(self.label_rows(), {})
        sam3 = FakeSam3()
        self.assertEqual(self.seed(sam3).written, 2)
        self.assertEqual(len(sam3.instances_calls), 2)

    def test_sam3_down_stops_the_run(self):
        report = self.seed(DownSam3())
        self.assertIn("connection refused", report.unavailable)
        self.assertEqual(report.written, 0)
        self.assertEqual(self.label_rows(), {})

    def test_limit(self):
        self.assertEqual(self.seed(FakeSam3(), limit=1).written, 1)
        self.assertEqual(len(self.label_rows()), 1)

    def test_the_embeddings_read_the_label_cut(self):
        self.seed(FakeSam3())
        with closing(embeddings.open_database(self.db)) as conn:
            _wines, sources = embeddings.read_inputs(conn, self.db)
        cut = sources[self.main]["cuts"]["label"]
        derived = self.label_rows()[self.main][2]
        self.assertEqual(cut["sha256"], derived)
        self.assertIsNone(sources[self.main]["cuts"]["package"])
        # The steps of the view `label` make the model input from the cut.
        image = embeddings.prepare({"steps": LABEL_STEPS, "cut": cut},
                                   sources[self.main]["path"])
        self.assertEqual((image.mode, image.size),
                         ("RGB", (cut["box"][2] - cut["box"][0], cut["box"][3] - cut["box"][1])))


if __name__ == "__main__":
    unittest.main()
