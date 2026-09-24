import csv
import io
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import labdb  # noqa: E402
import seed_catalog as SEED  # noqa: E402

# The column order of strapi_output0709.csv.
HEADERS = ["Название вина", "Категория", "Цвет", "Регион", "Сорт винограда",
           "Описание", "Винодельня", "Slug", "Название фото"]


def wine(slug, **values):
    row = {
        "Название вина": "Вино " + slug,
        "Категория": "Белое",
        "Цвет": "Соломенный",
        "Регион": "Крым",
        "Сорт винограда": "Алиготе, Кокур Белый",
        "Описание": "Описание " + slug,
        "Винодельня": "Винодельня",
        "Slug": slug,
        "Название фото": slug + ".webp",
    }
    row.update(values)
    return row


class SeedCatalogTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")

    def tearDown(self):
        self.directory.cleanup()

    def write_csv(self, rows, name="catalog.csv", headers=HEADERS):
        out = io.StringIO(newline="")
        writer = csv.DictWriter(out, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})
        path = self.root / name
        # The official file starts with no byte order mark; utf-8-sig reads both.
        path.write_bytes(out.getvalue().encode("utf-8"))
        return str(path)

    def create_db(self):
        labdb.connect(self.db, create=True).close()

    def query(self, sql, *args):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def test_create_applies_the_schema(self):
        self.create_db()
        self.assertEqual(self.query("PRAGMA user_version"), [(1,)])
        conn = sqlite3.connect(self.db)
        self.assertEqual(labdb.tables(conn), ["catalog_source", "wine_catalog"])
        conn.close()

    def test_connect_twice_keeps_the_version(self):
        self.create_db()
        labdb.connect(self.db).close()
        self.assertEqual(self.query("PRAGMA user_version"), [(1,)])

    def test_newer_database_is_refused(self):
        self.create_db()
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

    def test_seed_needs_an_existing_database(self):
        path = self.write_csv([wine("a")])
        with self.assertRaises(labdb.SchemaError):
            SEED.seed(self.db, path)
        self.assertFalse(Path(self.db).exists())

    def test_seed_stores_unique_wines(self):
        self.create_db()
        path = self.write_csv([
            wine("a"),
            wine("a"),
            wine("b", **{"Название вина": "  Вино b ", "Сорт винограда": " "}),
        ])
        catalog, digest, stored = SEED.seed(self.db, path, now="2026-09-24T21:00:00+0300")
        self.assertTrue(stored)
        self.assertEqual((catalog.rows, catalog.duplicates, len(catalog.wines)), (3, 1, 2))
        self.assertEqual(catalog.trimmed, 2)
        self.assertEqual(catalog.empty_grapes, 1)
        self.assertEqual(
            self.query("SELECT slug, name, grapes, csv_photo_name FROM wine_catalog "
                       "ORDER BY slug"),
            [("a", "Вино a", "Алиготе, Кокур Белый", "a.webp"),
             ("b", "Вино b", None, "b.webp")])
        self.assertEqual(
            self.query("SELECT source_path, source_sha256, source_rows, imported_at "
                       "FROM catalog_source"),
            [(path, digest, 3, "2026-09-24T21:00:00+0300")])

    def test_rows_that_differ_only_in_white_space_are_one_wine(self):
        self.create_db()
        path = self.write_csv([wine("a"), wine("a", **{"Описание": " Описание a  "})])
        catalog, _, _ = SEED.seed(self.db, path)
        self.assertEqual((len(catalog.wines), catalog.duplicates), (1, 1))

    def test_different_rows_for_one_slug_stop_the_seed(self):
        self.create_db()
        path = self.write_csv([wine("a"), wine("a", **{"Регион": "Кубань"})])
        with self.assertRaisesRegex(SEED.CatalogError, "1 slugs have different rows: a"):
            SEED.seed(self.db, path)
        self.assertEqual(self.query("SELECT count(*) FROM wine_catalog"), [(0,)])
        self.assertEqual(self.query("SELECT count(*) FROM catalog_source"), [(0,)])

    def test_missing_column_stops_the_seed(self):
        self.create_db()
        headers = [h for h in HEADERS if h != "Цвет"]
        path = self.write_csv([wine("a")], headers=headers)
        with self.assertRaisesRegex(SEED.CatalogError, "missing: \\['Цвет'\\]"):
            SEED.seed(self.db, path)

    def test_empty_required_value_stops_the_seed(self):
        self.create_db()
        path = self.write_csv([wine("a"), wine("b", **{"Описание": "  "})])
        with self.assertRaisesRegex(SEED.CatalogError, "line 3: Описание"):
            SEED.seed(self.db, path)
        self.assertEqual(self.query("SELECT count(*) FROM wine_catalog"), [(0,)])

    def test_second_seed_from_the_same_file_changes_nothing(self):
        self.create_db()
        path = self.write_csv([wine("a"), wine("b")])
        SEED.seed(self.db, path, now="2026-09-24T21:00:00+0300")
        _, _, stored = SEED.seed(self.db, path, now="2026-09-25T09:00:00+0300")
        self.assertFalse(stored)
        self.assertEqual(self.query("SELECT imported_at FROM catalog_source"),
                         [("2026-09-24T21:00:00+0300",)])
        self.assertEqual(self.query("SELECT count(*) FROM wine_catalog"), [(2,)])

    def test_seed_from_another_file_is_refused(self):
        self.create_db()
        SEED.seed(self.db, self.write_csv([wine("a")], name="one.csv"))
        other = self.write_csv([wine("a"), wine("b")], name="two.csv")
        with self.assertRaisesRegex(SEED.CatalogError, "holds another delivery"):
            SEED.seed(self.db, other)
        self.assertEqual(self.query("SELECT slug FROM wine_catalog"), [("a",)])

    def test_main_reports_the_counts(self):
        self.create_db()
        path = self.write_csv([wine("a"), wine("a")])
        out = io.StringIO()
        stdout, sys.stdout = sys.stdout, out
        try:
            code = SEED.main([path, "--db", self.db])
        finally:
            sys.stdout = stdout
        self.assertEqual(code, 0)
        self.assertIn("duplicate rows: 1", out.getvalue())
        self.assertIn("result: stored 1 wines", out.getvalue())


if __name__ == "__main__":
    unittest.main()
