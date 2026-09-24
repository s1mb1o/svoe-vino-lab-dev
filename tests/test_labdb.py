import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import labdb  # noqa: E402

VERSION = len(labdb.schema_files())


class LabDbTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")

    def tearDown(self):
        self.directory.cleanup()

    def query(self, sql, *args):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def schema_up_to(self, number):
        """Return a schema directory that holds the files 001 to `number`."""
        schema = self.root / ("schema-%d" % number)
        schema.mkdir()
        for n, path in labdb.schema_files()[:number]:
            source = Path(path)
            (schema / source.name).write_text(source.read_text(encoding="utf-8"),
                                              encoding="utf-8")
        return str(schema)

    def test_create_applies_the_schema(self):
        labdb.connect(self.db, create=True).close()
        self.assertEqual(VERSION, 5)
        self.assertEqual(self.query("PRAGMA user_version"), [(VERSION,)])
        conn = sqlite3.connect(self.db)
        self.assertEqual(labdb.tables(conn), ["wine_catalog", "wine_image"])
        conn.close()

    def test_connect_twice_keeps_the_version(self):
        labdb.connect(self.db, create=True).close()
        labdb.connect(self.db).close()
        self.assertEqual(self.query("PRAGMA user_version"), [(VERSION,)])

    def test_connect_needs_an_existing_file_unless_create(self):
        with self.assertRaisesRegex(labdb.SchemaError, "no database at"):
            labdb.connect(self.db)
        self.assertFalse(Path(self.db).exists())

    def test_newer_database_is_refused(self):
        labdb.connect(self.db, create=True).close()
        conn = sqlite3.connect(self.db)
        conn.execute("PRAGMA user_version = 99")
        conn.close()
        with self.assertRaises(labdb.SchemaError):
            labdb.connect(self.db)

    def test_failed_schema_file_changes_nothing(self):
        schema = self.root / "schema"
        schema.mkdir()
        (schema / "001_bad.sql").write_text(
            "CREATE TABLE a (x TEXT) STRICT;\nCREATE TABLE broken (;\n")
        with self.assertRaises(sqlite3.Error):
            labdb.connect(self.db, create=True, directory=str(schema))
        self.assertEqual(self.query("PRAGMA user_version"), [(0,)])
        self.assertEqual(self.query("SELECT name FROM sqlite_schema"), [])

    def test_version_1_database_keeps_its_rows(self):
        labdb.connect(self.db, create=True, directory=self.schema_up_to(1)).close()
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO catalog_source VALUES (1, '/x.csv', ?, 1, 't')",
                     ("0" * 64,))
        conn.execute("INSERT INTO wine_catalog VALUES "
                     "('a', 'n', 'p', 'c', 'co', 'r', NULL, 'd', 'a.webp')")
        conn.commit()
        conn.close()

        labdb.connect(self.db).close()
        self.assertEqual(self.query("PRAGMA user_version"), [(VERSION,)])
        self.assertEqual(self.query("SELECT wine_slug, csv_photo_name, state, removed_by "
                                    "FROM wine_catalog"), [("a", "a.webp", "Active", None)])
        self.assertEqual(self.query("SELECT name FROM sqlite_schema "
                                    "WHERE name = 'catalog_source'"), [])
        with self.assertRaises(sqlite3.IntegrityError):
            self.query("INSERT INTO wine_catalog (wine_slug, name, producer, category, "
                       "color, region, description, csv_photo_name) VALUES "
                       "('', 'n', 'p', 'c', 'co', 'r', 'd', 'b.webp')")

    def test_version_3_removed_wine_was_removed_by_the_import(self):
        labdb.connect(self.db, create=True, directory=self.schema_up_to(3)).close()
        conn = sqlite3.connect(self.db)
        conn.executemany("INSERT INTO wine_catalog VALUES (?, 'n', 'p', 'c', 'co', 'r', "
                         "NULL, 'd', 'x.webp', ?)",
                         [("a", "Active"), ("b", "Removed"), ("c", "Disabled")])
        conn.execute("DELETE FROM wine_catalog WHERE wine_slug = 'a'")
        conn.execute("INSERT INTO wine_catalog VALUES ('a', 'n', 'p', 'c', 'co', 'r', "
                     "NULL, 'd', 'x.webp', 'Active')")
        conn.commit()
        before = conn.execute("SELECT rowid, wine_slug FROM wine_catalog ORDER BY rowid").fetchall()
        conn.close()

        labdb.connect(self.db).close()
        self.assertEqual(self.query("SELECT rowid, wine_slug FROM wine_catalog ORDER BY rowid"),
                         before)
        self.assertEqual(self.query("SELECT wine_slug, state, removed_by FROM wine_catalog "
                                    "ORDER BY rowid"),
                         [("b", "Removed", "import"), ("c", "Disabled", None),
                          ("a", "Active", None)])

    def test_removed_by_is_set_exactly_for_a_removed_wine(self):
        labdb.connect(self.db, create=True).close()
        insert = ("INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                  "region, description, csv_photo_name, state, removed_by) "
                  "VALUES (?, 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp', ?, ?)")
        conn = sqlite3.connect(self.db)
        conn.execute(insert, ("a", "Removed", "import"))
        conn.execute(insert, ("b", "Removed", "person"))
        conn.execute(insert, ("c", "Active", None))
        for slug, state, removed_by in (("d", "Removed", None), ("e", "Active", "person"),
                                        ("f", "Disabled", "import"), ("g", "Removed", "robot")):
            with self.assertRaises(sqlite3.IntegrityError, msg=slug):
                conn.execute(insert, (slug, state, removed_by))
        conn.close()

    def test_state_accepts_the_three_states_alone(self):
        labdb.connect(self.db, create=True).close()
        insert = ("INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                  "region, description, csv_photo_name, state, removed_by) "
                  "VALUES (?, 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp', ?, ?)")
        conn = sqlite3.connect(self.db)
        for slug, state, removed_by in (("a", "Active", None), ("b", "Disabled", None),
                                        ("c", "Removed", "person")):
            conn.execute(insert, (slug, state, removed_by))
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(insert, ("d", "active", None))
        conn.close()


if __name__ == "__main__":
    unittest.main()
