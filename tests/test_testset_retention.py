"""A wine of a test set keeps its test set rows when its state becomes `Removed`.

The owner set this rule on 2026-09-25T17:10:55+0300: a wine that is in a test set stays
there when it is removed, so that a restore finds it again. A removal writes the columns
`state` and `removed_by` of `wine_catalog` alone, and `test_photo` holds no foreign key to
`wine_catalog`. These tests stop a later change from breaking the rule. They check the two
writers of the state `Removed`: a person (`lab_server.change_state`, the route
`POST /api/wine-state`) and the catalogue import (`import_catalog.py`).
"""
import csv
import io
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX  # noqa: E402
import import_catalog  # noqa: E402
import import_testset  # noqa: E402
import lab_server  # noqa: E402

PHOTOS = {
    "wine-a/01.jpg": b"photo a1",
    "wine-a/02.jpg": b"photo a2",
    "wine-b/01.jpg": b"photo b1",
}
LABELS = {
    "wine-a": {"01.jpg": {"label": "positive"}, "02.jpg": {"label": "negative", "delete": True}},
    "wine-b": {"01.jpg": {"label": "positive"}},
}
EXCLUDED = {"wine-a": {"reason": "a reason", "ts": "2026-09-25T17:00:00+0300"}}
GROUPS = [["wine-a", "wine-b"]]
# The tables of a test set, and `image`, which holds the rows of the photo files.
TABLES = ("test_set", "test_photo", "test_excluded", "test_variant", "image")
# The values of the CSV of the catalogue import: the values of `FX.make_database`.
VALUES = {"name": "n", "producer": "p", "category": "c", "color": "co", "region": "r",
          "grapes": "", "description": "d", "csv_photo_name": "x.webp"}


class RemovedWineKeepsTestsetTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(self.root)
        set_dir = FX.write_set(self.root, PHOTOS, LABELS, EXCLUDED, GROUPS)
        import_testset.import_testset(self.db, "my", set_dir, lambda _: None, self.schema)
        self.before = self.rows()

    def tearDown(self):
        self.directory.cleanup()

    def query(self, sql, *args):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def rows(self):
        return {table: self.query("SELECT * FROM %s ORDER BY 1, 2" % table)
                for table in TABLES}

    def state(self, slug):
        return self.query("SELECT state, removed_by FROM wine_catalog WHERE wine_slug = ?",
                          slug)[0]

    def write_csv(self, slugs):
        out = io.StringIO(newline="")
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow([header for _, header in import_catalog.COLUMNS])
        for slug in slugs:
            writer.writerow([slug if column == "wine_slug" else VALUES[column]
                             for column, _ in import_catalog.COLUMNS])
        path = self.root / ("catalog-%d.csv" % len(slugs))
        path.write_bytes(out.getvalue().encode("utf-8"))
        return str(path)

    def assert_kept(self):
        self.assertEqual(self.rows(), self.before)

    def test_the_set_holds_the_wine(self):
        self.assertEqual(
            self.query("SELECT file_name FROM test_photo WHERE place = 'wine-a' ORDER BY 1"),
            [("01.jpg",), ("02.jpg",)])
        self.assertEqual(self.query("SELECT wine_slug FROM test_excluded"), [("wine-a",)])
        self.assertEqual(self.query("SELECT wine_slug FROM test_variant ORDER BY 1"),
                         [("wine-a",), ("wine-b",)])

    def test_remove_and_restore_by_a_person(self):
        lab_server.change_state(self.db, "wine-a", "remove")
        self.assertEqual(self.state("wine-a"), ("Removed", "person"))
        self.assert_kept()
        lab_server.change_state(self.db, "wine-a", "restore")
        self.assertEqual(self.state("wine-a"), ("Active", None))
        self.assert_kept()

    def test_disable_and_remove_by_a_person(self):
        lab_server.change_state(self.db, "wine-a", "disable")
        lab_server.change_state(self.db, "wine-a", "remove")
        self.assertEqual(self.state("wine-a"), ("Removed", "person"))
        self.assert_kept()

    def test_remove_and_restore_by_the_catalogue_import(self):
        import_catalog.import_catalog(self.db, self.write_csv(("wine-b", "wine-c")))
        self.assertEqual(self.state("wine-a"), ("Removed", "import"))
        self.assert_kept()
        import_catalog.import_catalog(self.db, self.write_csv(("wine-a", "wine-b", "wine-c")))
        self.assertEqual(self.state("wine-a"), ("Active", None))
        self.assert_kept()


if __name__ == "__main__":
    unittest.main()
