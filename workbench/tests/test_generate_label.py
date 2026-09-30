"""Plan 94: the checkbox `generate label` turns off the SAM3 label cut of one image.

Run from the workbench root:
    python3 -m unittest discover -s tests -p 'test_generate_label.py'
"""
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tests"))
import alternatives  # noqa: E402
import derive  # noqa: E402
import embeddings  # noqa: E402
import image_descriptions as DESC  # noqa: E402
import lab_server as LAB  # noqa: E402
import labdb  # noqa: E402
import seed_label_cuts  # noqa: E402
from test_alternatives import DownSam3, FakeSam3, WINES, picture, sha  # noqa: E402

WINE_COLUMNS = ("wine_slug, name, producer, category, color, region, grapes, description, "
                "csv_photo_name, state, removed_by")
NOW = "2026-09-30T19:00:00Z"
MANUAL_SETTINGS = alternatives.MANUAL_HEAD + "[[1, 1], [30, 1], [30, 60]]"


class GenerateLabelCase(unittest.TestCase):
    """A database with the Active wine `wine-b`: a `main` image and a `label_front`
    close-up."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")
        self.make_database(self.db)
        conn = self.connect()
        self.main = self.store(conn, "wine-b", "main", "main", picture(colour=(90, 30, 20)))
        self.close_up = self.store(conn, "wine-b", "label_front", "additional",
                                   picture(colour=(20, 90, 30)))
        conn.close()

    def tearDown(self):
        self.directory.cleanup()

    def make_database(self, path, directory=labdb.SCHEMA_DIR):
        conn = labdb.connect(path, create=True, directory=directory)
        with conn:
            conn.executemany("INSERT INTO wine_catalog (%s) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
                             % WINE_COLUMNS, WINES)
        conn.close()

    def connect(self, path=None):
        conn = sqlite3.connect(path or self.db)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def store(self, conn, slug, image_type, folder, data, path=None):
        digest = sha(data)
        file = alternatives.file_path(path or self.db, folder, digest, "png")
        os.makedirs(os.path.dirname(file), exist_ok=True)
        Path(file).write_bytes(data)
        with conn:
            conn.execute("INSERT INTO image (sha256, folder, extension, width, height) "
                         "VALUES (?, ?, 'png', 40, 80) ON CONFLICT DO NOTHING",
                         (digest, folder))
            conn.execute("INSERT INTO wine_image (wine_slug, image_type, sha256, source_name, "
                         "match_method) VALUES (?, ?, ?, 'x.png', 'slug-name')",
                         (slug, image_type, digest))
        return digest

    def add_cut(self, digest, settings=alternatives.SETTINGS_LABEL, colour=(1, 2, 3)):
        """Write a label cut row of `digest` with a processed file of its own."""
        derived = sha(picture(colour=colour))
        conn = self.connect()
        with conn:
            conn.execute("INSERT INTO image (sha256, folder, extension, width, height) "
                         "VALUES (?, 'cropped', 'png', 20, 20) ON CONFLICT DO NOTHING",
                         (derived,))
            conn.execute("INSERT INTO image_derivative (source_sha256, method, settings, "
                         "sha256, box_left, box_top, box_right, box_bottom, kind) "
                         "VALUES (?, 'seg', ?, ?, 0, 0, 20, 20, 'label')",
                         (digest, settings, derived))
        conn.close()

    def label_cut(self, digest):
        conn = self.connect()
        try:
            return conn.execute("SELECT settings FROM image_derivative WHERE "
                                "source_sha256 = ? AND kind = 'label'", (digest,)).fetchone()
        finally:
            conn.close()

    def turn(self, digest, value):
        conn = self.connect()
        with conn:
            DESC.set_values(conn, digest, {DESC.GENERATE_LABEL: value}, now=NOW)
        conn.close()


class ValueTest(GenerateLabelCase):
    def test_the_schema_adds_a_column_with_a_check(self):
        conn = self.connect()
        try:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(image_description)")]
            self.assertEqual(columns[-2:], ["presentation_mode", "generate_label"])
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO image_description (sha256, created_by, created_at, "
                             "updated_at, generate_label) VALUES (?, 'manual', ?, ?, 2)",
                             (self.main, NOW, NOW))
        finally:
            conn.close()

    def test_check_value_takes_a_boolean_or_null(self):
        for value in (True, False, None):
            self.assertIs(DESC.check_value("generate_label", value), value)
        for value in (1, 0, "false", []):
            with self.assertRaises(DESC.DescriptionError):
                DESC.check_value("generate_label", value)

    def test_the_value_is_not_a_field_of_the_vlm(self):
        self.assertNotIn("generate_label", DESC.FIELDS)
        self.assertEqual(DESC.preset({**dict.fromkeys(DESC.COLUMNS), "generate_label": False}),
                         {})

    def test_set_values_stores_the_value_and_keeps_it(self):
        conn = self.connect()
        with conn:
            self.assertIs(DESC.set_values(conn, self.main, {"generate_label": False})
                          ["generate_label"], False)
            self.assertEqual(conn.execute("SELECT generate_label FROM image_description "
                                          "WHERE sha256 = ?", (self.main,)).fetchone(), (0,))
            # A save of the other fields leaves the value as it is.
            row = DESC.set_values(conn, self.main, {"package_type": "bottle"})
            self.assertIs(row["generate_label"], False)
            self.assertIs(DESC.set_values(conn, self.main, {"generate_label": True})
                          ["generate_label"], True)
            self.assertIsNone(DESC.set_values(conn, self.main, {"generate_label": None})
                              ["generate_label"])
            self.assertIsNone(DESC.set_values(conn, self.close_up, {"package_type": "bottle"})
                              ["generate_label"])
        conn.close()

    def test_label_cut_off_is_true_for_zero_alone(self):
        conn = self.connect()
        try:
            self.assertFalse(alternatives.label_cut_off(conn, self.main))  # no row
            for value, off in ((None, False), (True, False), (False, True)):
                with conn:
                    DESC.set_values(conn, self.main, {"generate_label": value})
                self.assertIs(alternatives.label_cut_off(conn, self.main), off)
        finally:
            conn.close()


class WriterTest(GenerateLabelCase):
    def path(self, digest, folder="main"):
        return alternatives.file_path(self.db, folder, digest, "png")

    def test_a_turned_off_image_gets_no_sam3_request_and_no_row(self):
        self.turn(self.main, False)
        sam3 = FakeSam3()
        conn = self.connect()
        conn.isolation_level = None
        try:
            warnings = []
            out = alternatives.process_image(conn, self.db, self.main, self.path(self.main),
                                             "label", sam3, warnings)
            self.assertTrue(out.turned_off)
            self.assertEqual((out.links, out.present, warnings), ([], 0, []))
            self.assertEqual(sam3.instances_calls, [])
        finally:
            conn.close()

    def test_a_turned_off_result_keeps_the_not_applicable_marker(self):
        conn = self.connect()
        with conn:
            conn.execute("INSERT INTO image_derivative_absence (source_sha256, kind, settings, "
                         "reason) VALUES (?, 'label', ?, 'the packet has no separate label')",
                         (self.main, alternatives.SETTINGS_LABEL_ABSENCE))
            DESC.set_values(conn, self.main, {"generate_label": False})
        out = alternatives.process_image(conn, self.db, self.main, self.path(self.main),
                                         "label", FakeSam3(), [])
        with conn:
            alternatives.write_processed_rows(conn, out)
        self.assertEqual(conn.execute("SELECT count(*) FROM image_derivative_absence")
                         .fetchone(), (1,))
        conn.close()

    def test_no_warning_names_a_turned_off_label_cut(self):
        conn = self.connect()
        try:
            warnings = []
            alternatives.full_label_cut(conn, self.db, self.main, self.path(self.main),
                                        DownSam3(), warnings)
            self.assertIn(alternatives.NO_LABEL_CUT, warnings)
            with conn:
                DESC.set_values(conn, self.main, {"generate_label": False})
            warnings = []
            out = alternatives.full_label_cut(conn, self.db, self.main, self.path(self.main),
                                              DownSam3(), warnings)
            self.assertEqual(warnings, [])
            alternatives._warn(out, warnings)
            self.assertEqual(warnings, [])
        finally:
            conn.close()

    def test_a_turned_off_close_up_has_its_current_cuts(self):
        conn = self.connect()
        try:
            self.assertFalse(alternatives.has_current_cuts(conn, self.close_up, "label"))
            with conn:
                DESC.set_values(conn, self.close_up, {"generate_label": False})
            self.assertTrue(alternatives.has_current_cuts(conn, self.close_up, "label"))
        finally:
            conn.close()

    def test_remove_label_cut_deletes_the_automatic_cut_alone(self):
        self.add_cut(self.main)
        self.add_cut(self.close_up, MANUAL_SETTINGS, colour=(4, 5, 6))
        conn = self.connect()
        with conn:
            self.assertTrue(alternatives.remove_label_cut(conn, self.main))
            self.assertFalse(alternatives.remove_label_cut(conn, self.main))
            self.assertFalse(alternatives.remove_label_cut(conn, self.close_up))
        conn.close()
        self.assertIsNone(self.label_cut(self.main))
        self.assertEqual(self.label_cut(self.close_up), (MANUAL_SETTINGS,))

    def test_seed_label_cuts_leaves_a_turned_off_original_out(self):
        self.turn(self.main, False)
        sam3 = FakeSam3()
        logs = []
        report = seed_label_cuts.seed_label_cuts(self.db, logs.append, sam3)
        self.assertEqual((report.originals, report.turned_off, report.written), (1, 1, 0))
        self.assertEqual(sam3.instances_calls, [])
        self.assertIn("label cut turned off: 1", logs[0])
        self.assertIsNone(self.label_cut(self.main))
        # Turned on again, the next run cuts the label.
        self.turn(self.main, True)
        report = seed_label_cuts.seed_label_cuts(self.db, logs.append, FakeSam3())
        self.assertEqual((report.turned_off, report.written), (0, 1))
        self.assertEqual(self.label_cut(self.main), (alternatives.SETTINGS_LABEL,))


class RouteTest(GenerateLabelCase):
    def test_false_removes_the_automatic_cut_and_sends_the_records(self):
        self.add_cut(self.main)
        answer = LAB.set_image_description(self.db, self.main, {"generate_label": False})
        self.assertIs(answer["description"]["generate_label"], False)
        self.assertIs(answer["label_cut_removed"], True)
        self.assertEqual(list(answer["records"]), ["wine-b"])
        self.assertIsNone(self.label_cut(self.main))

    def test_false_keeps_a_manual_cut(self):
        self.add_cut(self.close_up, MANUAL_SETTINGS)
        answer = LAB.set_image_description(self.db, self.close_up, {"generate_label": False})
        self.assertIs(answer["label_cut_removed"], False)
        self.assertNotIn("records", answer)
        self.assertEqual(self.label_cut(self.close_up), (MANUAL_SETTINGS,))

    def test_true_and_null_change_no_cut(self):
        self.add_cut(self.main)
        for value in (True, None):
            answer = LAB.set_image_description(self.db, self.main, {"generate_label": value})
            self.assertIs(answer["description"]["generate_label"], value)
            self.assertIs(answer["label_cut_removed"], False)
        self.assertEqual(self.label_cut(self.main), (alternatives.SETTINGS_LABEL,))

    def test_a_save_of_the_other_fields_keeps_the_value_and_the_cut(self):
        self.add_cut(self.main)
        answer = LAB.set_image_description(self.db, self.main, {"package_type": "bottle"})
        self.assertIsNone(answer["description"]["generate_label"])
        self.assertIs(answer["label_cut_removed"], False)
        self.assertEqual(self.label_cut(self.main), (alternatives.SETTINGS_LABEL,))

    def test_a_bad_value_is_http_400_and_changes_nothing(self):
        self.add_cut(self.main)
        with self.assertRaises(LAB.StateError) as caught:
            LAB.set_image_description(self.db, self.main, {"generate_label": "no"})
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(self.label_cut(self.main), (alternatives.SETTINGS_LABEL,))


class EmbeddingInputTest(GenerateLabelCase):
    VIEWS = type("Embedding", (), {"views": {
        "full": [{"step": "segment", "target": "package"}],
        "label": [{"step": "segment", "target": "label"}]}})()

    def sources(self, path=None):
        conn = self.connect(path)
        try:
            return embeddings.read_inputs(conn, path or self.db)[1]
        finally:
            conn.close()

    def test_a_turned_off_original_has_no_label_view(self):
        self.assertIsNone(self.sources()[self.main]["not_applicable"]["label"])
        self.turn(self.main, False)
        source = self.sources()[self.main]
        self.assertEqual(source["not_applicable"]["label"], embeddings.LABEL_TURNED_OFF)
        self.assertEqual(embeddings.not_applicable_reason(self.VIEWS, source, "label"),
                         embeddings.LABEL_TURNED_OFF)
        self.assertIsNone(embeddings.not_applicable_reason(self.VIEWS, source, "full"))

    def test_a_manual_cut_keeps_the_label_view(self):
        self.add_cut(self.main, MANUAL_SETTINGS)
        self.turn(self.main, False)
        source = self.sources()[self.main]
        self.assertIsNone(source["not_applicable"]["label"])
        self.assertIsNotNone(source["cuts"]["label"])

    def test_a_database_before_schema_033_still_reads(self):
        old = self.root / "old-schema"
        old.mkdir()
        for name in os.listdir(labdb.SCHEMA_DIR):
            if name.endswith(".sql") and name < "033_":
                shutil.copy(os.path.join(labdb.SCHEMA_DIR, name), old / name)
        path = str(self.root / "old" / "lab.sqlite3")
        os.makedirs(os.path.dirname(path))
        self.make_database(path, directory=str(old))
        conn = self.connect(path)
        digest = self.store(conn, "wine-b", "main", "main", picture(colour=(7, 8, 9)), path)
        conn.close()
        self.assertIsNone(self.sources(path)[digest]["not_applicable"]["label"])


if __name__ == "__main__":
    unittest.main()
