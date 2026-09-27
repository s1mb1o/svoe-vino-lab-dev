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
        self.assertEqual(VERSION, 26)
        self.assertEqual(self.query("PRAGMA user_version"), [(VERSION,)])
        conn = sqlite3.connect(self.db)
        self.assertEqual(labdb.tables(conn),
                         ["image", "image_derivative", "image_derivative_absence",
                          "image_description", "image_detail", "test_photo",
                          "test_photo_comment", "test_set", "test_variant", "website_refusal",
                          "wine_atlas_binding", "wine_beverage_type", "wine_catalog",
                          "wine_code", "wine_comment", "wine_favorite", "wine_image"])
        conn.close()

    def test_derivative_absence_needs_an_image_and_a_reason(self):
        conn = labdb.connect(self.db, create=True)
        conn.execute("INSERT INTO image VALUES (?, 'main', 'png', 1, 1)", ("a" * 64,))
        conn.execute("INSERT INTO image_derivative_absence VALUES "
                     "(?, 'label', 'settings', 'the packet has no separate label')",
                     ("a" * 64,))
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO image_derivative_absence VALUES "
                         "(?, 'label', 'settings', 'reason')", ("b" * 64,))
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO image_derivative_absence VALUES "
                         "(?, 'label', 'settings', '')", ("a" * 64,))
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

    def test_schema_file_may_build_a_parent_table_again(self):
        schema = self.root / "schema"
        schema.mkdir()
        (schema / "001_a.sql").write_text(
            "CREATE TABLE p (k TEXT PRIMARY KEY) STRICT;\n"
            "CREATE TABLE c (k TEXT NOT NULL REFERENCES p (k)) STRICT;\n"
            "INSERT INTO p VALUES ('a');\nINSERT INTO c VALUES ('a');\n")
        (schema / "002_b.sql").write_text(
            "CREATE TABLE p_new (k TEXT PRIMARY KEY, v TEXT) STRICT;\n"
            "INSERT INTO p_new (k) SELECT k FROM p;\nDROP TABLE p;\n"
            "ALTER TABLE p_new RENAME TO p;\n")
        conn = labdb.connect(self.db, create=True, directory=str(schema))
        self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone(), (1,))
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO c VALUES ('none')")
        conn.close()
        self.assertEqual(self.query("PRAGMA user_version"), [(2,)])
        self.assertEqual(self.query("SELECT k FROM c"), [("a",)])

    def test_schema_file_that_breaks_a_link_changes_nothing(self):
        schema = self.root / "schema"
        schema.mkdir()
        (schema / "001_a.sql").write_text(
            "CREATE TABLE p (k TEXT PRIMARY KEY) STRICT;\n"
            "CREATE TABLE c (k TEXT NOT NULL REFERENCES p (k)) STRICT;\n"
            "INSERT INTO p VALUES ('a');\nINSERT INTO c VALUES ('a');\n")
        labdb.connect(self.db, create=True, directory=str(schema)).close()
        (schema / "002_b.sql").write_text("DELETE FROM p;\n")
        with self.assertRaisesRegex(labdb.SchemaError, "002_b.sql breaks 1 foreign keys"):
            labdb.connect(self.db, directory=str(schema))
        self.assertEqual(self.query("PRAGMA user_version"), [(1,)])
        self.assertEqual(self.query("SELECT k FROM p"), [("a",)])

    def test_version_13_wines_keep_their_rows_and_links(self):
        labdb.connect(self.db, create=True, directory=self.schema_up_to(13)).close()
        conn = sqlite3.connect(self.db)
        conn.executemany("INSERT INTO wine_catalog (wine_slug, name, producer, category, "
                         "color, region, description, csv_photo_name) "
                         "VALUES (?, 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp')",
                         [("b",), ("a",)])
        conn.execute("INSERT INTO wine_code (wine_slug, kind, value) "
                     "VALUES ('a', 'gtin', '04600000000008')")
        conn.commit()
        conn.close()
        labdb.connect(self.db).close()
        self.assertEqual(self.query("PRAGMA user_version"), [(VERSION,)])
        self.assertEqual(self.query("SELECT wine_slug FROM wine_catalog ORDER BY rowid"),
                         [("b",), ("a",)])
        self.assertEqual(self.query("SELECT wine_slug FROM wine_code"), [("a",)])
        self.assertEqual(self.query("PRAGMA foreign_key_check"), [])
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("INSERT INTO wine_catalog (wine_slug, name, producer, category, "
                         "color, region, csv_photo_name) "
                         "VALUES ('c', 'n', 'p', 'c', 'co', 'r', 'x.webp')")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO wine_catalog (wine_slug, name, producer, category, "
                         "color, region, description, csv_photo_name) "
                         "VALUES ('d', 'n', 'p', 'c', 'co', 'r', '', 'x.webp')")
        conn.close()

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

    def test_version_6_images_move_to_the_image_table(self):
        labdb.connect(self.db, create=True, directory=self.schema_up_to(6)).close()
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                     "region, description, csv_photo_name) VALUES ('a', 'n', 'p', 'c', "
                     "'co', 'r', 'd', 'x.webp'), ('b', 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp')")
        conn.executemany("INSERT INTO wine_image VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
            ("a", "main", "1" * 64, "webp", "a.webp", "name-unique", 10, 20),
            ("b", "main", "1" * 64, "webp", "a.webp", "name-identical", 10, 20),
            ("a", "main_patched", "2" * 64, "png", "a.png", "slug-name", None, None)])
        conn.commit()
        conn.close()

        labdb.connect(self.db).close()
        self.assertEqual(self.query("SELECT * FROM image ORDER BY sha256"),
                         [("1" * 64, "main", "webp", 10, 20),
                          ("2" * 64, "patched", "png", None, None)])
        self.assertEqual(self.query("SELECT * FROM wine_image ORDER BY wine_slug, image_type"),
                         [("a", "main", "1" * 64, "a.webp", "name-unique"),
                          ("a", "main_patched", "2" * 64, "a.png", "slug-name"),
                          ("b", "main", "1" * 64, "a.webp", "name-identical")])
        self.assertEqual(self.query("PRAGMA foreign_key_check"), [])
        with self.assertRaises(sqlite3.IntegrityError):
            self.query("INSERT INTO wine_image VALUES ('b', 'main', ?, 'x', 'y')", "3" * 64)

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

    def test_wine_code_checks_the_form_and_allows_shared_values(self):
        labdb.connect(self.db, create=True).close()
        conn = sqlite3.connect(self.db)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executemany("INSERT INTO wine_catalog (wine_slug, name, producer, category, "
                         "color, region, description, csv_photo_name) "
                         "VALUES (?, 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp')", [("a",), ("b",)])
        insert = "INSERT INTO wine_code (wine_slug, kind, value) VALUES (?, ?, ?)"
        for row in (("a", "gtin", "04631168664979"), ("b", "gtin", "04631168664979"),
                    ("a", "barcode", "AB-1"), ("a", "qr_url", "https://a.ru/")):
            conn.execute(insert, row)
        for row in (("a", "gtin", "04631168664979"),   # the same value twice for one wine
                    ("a", "gtin", "4631168664979"),    # not the GTIN-14 form
                    ("a", "gtin", "0463116866497X"),
                    ("a", "barcode", "A" * 129),
                    ("a", "qr_url", "ftp://a.ru/"),
                    ("a", "ean", "1"),
                    ("a", "barcode", ""),
                    ("x", "barcode", "AB-1")):         # no such wine
            with self.assertRaises(sqlite3.IntegrityError, msg=row):
                conn.execute(insert, row)
        conn.close()

    def test_wine_code_insert_sets_the_time(self):
        labdb.connect(self.db, create=True).close()
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO wine_catalog (wine_slug, name, producer, category, "
                     "color, region, description, csv_photo_name) "
                     "VALUES ('a', 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp')")
        insert = ("INSERT INTO wine_code (wine_slug, kind, value, modified_at) "
                  "VALUES (?, ?, ?, ?)")
        conn.execute(insert, ("a", "gtin", "04631168664979", None))
        # An explicit time stays, as in a restore of db_export.py.
        conn.execute(insert, ("a", "qr_url", "https://a.ru/", "2026-01-02T03:04:05Z"))
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(insert, ("a", "gtin", "04640005351194", "2026-01-02 03:04:05"))
        times = dict(conn.execute("SELECT kind, modified_at FROM wine_code"))
        self.assertRegex(times["gtin"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(times["qr_url"], "2026-01-02T03:04:05Z")
        conn.close()

    def test_version_25_codes_keep_no_time(self):
        labdb.connect(self.db, create=True, directory=self.schema_up_to(25)).close()
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO wine_catalog (wine_slug, name, producer, category, "
                     "color, region, description, csv_photo_name) "
                     "VALUES ('a', 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp')")
        conn.execute("INSERT INTO wine_code (wine_slug, kind, value) "
                     "VALUES ('a', 'gtin', '04631168664979')")
        conn.commit()
        conn.close()
        labdb.connect(self.db).close()
        self.assertEqual(self.query("PRAGMA user_version"), [(VERSION,)])
        self.assertEqual(self.query("SELECT modified_at FROM wine_code"), [(None,)])


if __name__ == "__main__":
    unittest.main()
