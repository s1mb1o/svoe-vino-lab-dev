import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX  # noqa: E402
import import_testset as IT  # noqa: E402
import import_testsets as ITS  # noqa: E402

PHOTOS = {"wine-a/01.jpg": b"photo a1", "__null__/n1.jpg": b"photo n1"}
LABELS = {"wine-a": {"01.jpg": {"label": "positive"}}}


class ImportTestsetsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(self.root)
        self.source = self.root / "dataset"

    def tearDown(self):
        self.directory.cleanup()

    def query(self, sql):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql).fetchall()
        finally:
            conn.close()

    def test_the_three_sets_are_imported_under_their_directory_names(self):
        for name in ITS.SETS:
            FX.write_set(self.source, PHOTOS, LABELS, name=name)
        done = ITS.import_all(self.db, str(self.source), lambda m: None, self.schema)
        self.assertEqual([name for name, _, _ in done],
                         ["my", "official-real-photos", "vlmrerank-8b-failed"])
        self.assertEqual(self.query("SELECT set_name, count(*) FROM test_photo "
                                    "GROUP BY set_name ORDER BY set_name"),
                         [("my", 2), ("official-real-photos", 2), ("vlmrerank-8b-failed", 2)])
        # The same bytes in three sets are stored one time.
        self.assertEqual(self.query("SELECT count(*) FROM image"), [(2,)])

    def test_a_missing_set_directory_stops_before_any_import(self):
        FX.write_set(self.source, PHOTOS, LABELS, name="my")
        with self.assertRaisesRegex(IT.TestsetError,
                                    "official-real-photos, vlmrerank-8b-failed"):
            ITS.import_all(self.db, str(self.source), lambda m: None, self.schema)
        self.assertEqual(self.query("SELECT count(*) FROM test_set"), [(0,)])

    def test_the_default_source_is_the_dataset_of_svoe_vino_testset(self):
        self.assertEqual(Path(ITS.SOURCE_DIR).parts[-2:], ("svoe-vino-testset", "dataset"))
        self.assertEqual(Path(ITS.SOURCE_DIR).parent.parent,
                         Path(__file__).resolve().parents[2])


if __name__ == "__main__":
    unittest.main()
