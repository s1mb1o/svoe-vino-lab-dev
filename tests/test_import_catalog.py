import csv
import io
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import import_catalog as IMP  # noqa: E402
import labdb  # noqa: E402

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


class ImportCatalogTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")
        self.files = 0

    def tearDown(self):
        self.directory.cleanup()

    def write_csv(self, rows, headers=HEADERS):
        out = io.StringIO(newline="")
        writer = csv.DictWriter(out, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})
        self.files += 1
        path = self.root / ("catalog-%d.csv" % self.files)
        path.write_bytes(out.getvalue().encode("utf-8"))
        return str(path)

    def create_db(self):
        labdb.connect(self.db, create=True).close()

    def run_import(self, rows):
        return IMP.import_catalog(self.db, self.write_csv(rows))

    def query(self, sql, *args):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def states(self):
        return dict(self.query("SELECT wine_slug, state FROM wine_catalog"))

    def removed_by(self):
        return dict(self.query("SELECT wine_slug, removed_by FROM wine_catalog "
                               "WHERE state = 'Removed'"))

    def set_state(self, slug, state, removed_by=None):
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE wine_catalog SET state = ?, removed_by = ? WHERE wine_slug = ?",
                     (state, removed_by, slug))
        conn.commit()
        conn.close()

    # -- the CSV

    def test_first_import_adds_unique_wines(self):
        self.create_db()
        catalog, _, changes, states = self.run_import([
            wine("a"),
            wine("a"),
            wine("b", **{"Название вина": "  Вино b ", "Сорт винограда": " "}),
        ])
        self.assertEqual((catalog.rows, catalog.duplicates, len(catalog.wines)), (3, 1, 2))
        self.assertEqual((catalog.trimmed, catalog.empty_grapes), (2, 1))
        self.assertEqual(([r[0] for r in changes.added], changes.removed), (["a", "b"], []))
        self.assertEqual(states, {"Active": 2, "Disabled": 0, "Removed": 0})
        self.assertEqual(
            self.query("SELECT wine_slug, name, grapes, csv_photo_name, state "
                       "FROM wine_catalog ORDER BY rowid"),
            [("a", "Вино a", "Алиготе, Кокур Белый", "a.webp", "Active"),
             ("b", "Вино b", None, "b.webp", "Active")])

    def test_rows_that_differ_only_in_white_space_are_one_wine(self):
        self.create_db()
        catalog, _, _, _ = self.run_import(
            [wine("a"), wine("a", **{"Описание": " Описание a  "})])
        self.assertEqual((len(catalog.wines), catalog.duplicates), (1, 1))

    def test_different_rows_for_one_slug_stop_the_import(self):
        self.create_db()
        with self.assertRaisesRegex(IMP.CatalogError, "1 slugs have different rows: a"):
            self.run_import([wine("a"), wine("a", **{"Регион": "Кубань"})])
        self.assertEqual(self.query("SELECT count(*) FROM wine_catalog"), [(0,)])

    def test_missing_column_stops_the_import(self):
        self.create_db()
        path = self.write_csv([wine("a")], headers=[h for h in HEADERS if h != "Цвет"])
        with self.assertRaisesRegex(IMP.CatalogError, "missing: \\['Цвет'\\]"):
            IMP.import_catalog(self.db, path)

    def test_empty_required_value_stops_the_import(self):
        self.create_db()
        with self.assertRaisesRegex(IMP.CatalogError, "line 3: Описание"):
            self.run_import([wine("a"), wine("b", **{"Описание": "  "})])
        self.assertEqual(self.query("SELECT count(*) FROM wine_catalog"), [(0,)])

    def test_import_needs_an_existing_database(self):
        with self.assertRaises(labdb.SchemaError):
            self.run_import([wine("a")])
        self.assertFalse(Path(self.db).exists())

    # -- add and remove

    def test_same_file_again_changes_nothing(self):
        self.create_db()
        self.run_import([wine("a"), wine("b")])
        _, _, changes, _ = self.run_import([wine("a"), wine("b")])
        self.assertTrue(changes.empty())
        self.assertEqual(changes.unchanged, 2)
        self.assertEqual(self.states(), {"a": "Active", "b": "Active"})

    def test_new_wine_is_added_and_missing_wine_is_removed(self):
        self.create_db()
        self.run_import([wine("a"), wine("b"), wine("c")])
        _, _, changes, states = self.run_import([wine("a"), wine("c"), wine("d")])
        self.assertEqual(([r[0] for r in changes.added], changes.removed,
                          changes.restored, changes.unchanged), (["d"], ["b"], [], 2))
        self.assertEqual(self.states(),
                         {"a": "Active", "b": "Removed", "c": "Active", "d": "Active"})
        self.assertEqual(self.removed_by(), {"b": "import"})
        self.assertEqual(states, {"Active": 3, "Disabled": 0, "Removed": 1})
        self.assertEqual([r[0] for r in self.query(
            "SELECT wine_slug FROM wine_catalog ORDER BY rowid")], ["a", "b", "c", "d"])

    def test_removed_wine_comes_back_as_active(self):
        self.create_db()
        self.run_import([wine("a"), wine("b")])
        self.run_import([wine("a")])
        _, _, changes, _ = self.run_import([wine("a"), wine("b")])
        self.assertEqual((changes.restored, changes.added, changes.removed), (["b"], [], []))
        self.assertEqual(self.states(), {"a": "Active", "b": "Active"})

    def test_removed_wine_stays_removed_while_missing(self):
        self.create_db()
        self.run_import([wine("a"), wine("b")])
        self.run_import([wine("a")])
        _, _, changes, _ = self.run_import([wine("a")])
        self.assertTrue(changes.empty())
        self.assertEqual(self.states(), {"a": "Active", "b": "Removed"})

    def test_disabled_wine_stays_disabled_while_present(self):
        self.create_db()
        self.run_import([wine("a"), wine("b")])
        self.set_state("b", "Disabled")
        _, _, changes, states = self.run_import([wine("a"), wine("b")])
        self.assertTrue(changes.empty())
        self.assertEqual(self.states(), {"a": "Active", "b": "Disabled"})
        self.assertEqual(states["Disabled"], 1)

    def test_disabled_wine_becomes_removed_when_missing(self):
        self.create_db()
        self.run_import([wine("a"), wine("b")])
        self.set_state("b", "Disabled")
        _, _, changes, _ = self.run_import([wine("a")])
        self.assertEqual(changes.removed, ["b"])
        self.assertEqual(self.states(), {"a": "Active", "b": "Removed"})

    def test_wine_removed_by_a_person_stays_removed_while_present(self):
        self.create_db()
        self.run_import([wine("a"), wine("b")])
        self.set_state("b", "Removed", "person")
        _, _, changes, _ = self.run_import([wine("a"), wine("b")])
        self.assertTrue(changes.empty())
        self.assertEqual((changes.kept, changes.restored, changes.unchanged), (["b"], [], 1))
        self.assertEqual(self.removed_by(), {"b": "person"})

    def test_wine_removed_by_a_person_keeps_it_when_missing_and_back(self):
        self.create_db()
        self.run_import([wine("a"), wine("b")])
        self.set_state("b", "Removed", "person")
        _, _, changes, _ = self.run_import([wine("a")])
        self.assertEqual(changes.removed, [])
        _, _, changes, _ = self.run_import([wine("a"), wine("b")])
        self.assertEqual((changes.kept, changes.restored), (["b"], []))
        self.assertEqual(self.removed_by(), {"b": "person"})

    def test_restore_clears_removed_by(self):
        self.create_db()
        self.run_import([wine("a"), wine("b")])
        self.run_import([wine("a")])
        self.assertEqual(self.removed_by(), {"b": "import"})
        self.run_import([wine("a"), wine("b")])
        self.assertEqual(self.query("SELECT state, removed_by FROM wine_catalog "
                                    "WHERE wine_slug = 'b'"), [("Active", None)])

    # -- a changed wine

    def test_changed_field_stops_the_import_and_writes_nothing(self):
        self.create_db()
        self.run_import([wine("a"), wine("b")])
        with self.assertRaises(IMP.CatalogError) as error:
            self.run_import([wine("a", **{"Регион": "Кубань"}), wine("c")])
        message = str(error.exception)
        self.assertIn("1 wines of the CSV differ from the database", message)
        self.assertIn("a (Active): region 'Крым' -> 'Кубань'", message)
        # The same import holds an add and a remove. Neither is written.
        self.assertEqual(self.states(), {"a": "Active", "b": "Active"})

    def test_changed_field_of_a_removed_wine_stops_the_import(self):
        self.create_db()
        self.run_import([wine("a"), wine("b")])
        self.run_import([wine("a")])
        with self.assertRaisesRegex(IMP.CatalogError, "b \\(Removed\\): csv_photo_name"):
            self.run_import([wine("a"), wine("b", **{"Название фото": "new.webp"})])
        self.assertEqual(self.states(), {"a": "Active", "b": "Removed"})

    def test_grapes_from_null_to_a_value_is_a_change(self):
        self.create_db()
        self.run_import([wine("a", **{"Сорт винограда": ""})])
        with self.assertRaisesRegex(IMP.CatalogError, "grapes NULL -> 'Мерло'"):
            self.run_import([wine("a", **{"Сорт винограда": "Мерло"})])

    def test_main_reports_the_changes(self):
        self.create_db()
        self.run_import([wine("a"), wine("b")])
        path = self.write_csv([wine("a"), wine("c")])
        out = io.StringIO()
        stdout, sys.stdout = sys.stdout, out
        try:
            code = IMP.main([path, "--db", self.db])
        finally:
            sys.stdout = stdout
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("added: 1: c", text)
        self.assertIn("removed: 1: b", text)
        self.assertIn("kept removed by a person: 0", text)
        self.assertIn("states: Active 2, Disabled 0, Removed 1", text)
        self.assertIn("result: imported", text)

    def test_main_reports_a_changed_wine_as_an_error(self):
        self.create_db()
        self.run_import([wine("a")])
        path = self.write_csv([wine("a", **{"Цвет": "Золотой"})])
        err = io.StringIO()
        stderr, sys.stderr = sys.stderr, err
        try:
            code = IMP.main([path, "--db", self.db])
        finally:
            sys.stderr = stderr
        self.assertEqual(code, 1)
        self.assertIn("error: 1 wines of the CSV differ", err.getvalue())


if __name__ == "__main__":
    unittest.main()
