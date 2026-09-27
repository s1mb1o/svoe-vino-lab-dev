import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import atlas_bindings as AB  # noqa: E402
import labdb  # noqa: E402
from atlas_bindings import BindingError  # noqa: E402

UUID_1 = "6062ada1-1c2b-4f3e-9a8b-0123456789ab"
UUID_2 = "7a1b2c3d-0000-4000-8000-00000000000f"


class CleanUuidTest(unittest.TestCase):
    def test_stored_form(self):
        for value in (UUID_1, UUID_1.upper(), " %s " % UUID_1, UUID_1.replace("-", ""),
                      "{%s}" % UUID_1, "urn:uuid:" + UUID_1):
            with self.subTest(value=value):
                self.assertEqual(AB.clean_uuid(value), UUID_1)

    def test_refused_values(self):
        for value, message in ((None, "MUST be a string"), (5, "MUST be a string"),
                               ("", "empty"), ("  ", "empty"),
                               ("not-a-uuid", "not a valid UUID"),
                               (UUID_1 + "0", "not a valid UUID")):
            with self.subTest(value=value), self.assertRaisesRegex(BindingError, message):
                AB.clean_uuid(value)


class TableTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = labdb.connect(str(Path(self.tmp.name) / "lab.sqlite3"), create=True)
        with self.conn:
            self.conn.executemany(
                "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                "region, description, csv_photo_name) "
                "VALUES (?, 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp')",
                [(slug,) for slug in ("wine-a", "wine-b", "wine-c")])
            self.conn.executemany("INSERT INTO wine_atlas_binding VALUES (?, 'automatic', ?)",
                                  [("wine-a", UUID_1), ("wine-b", UUID_1)])

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_a_wine_has_a_list_of_products(self):
        # Plan 54: a manual row adds to the automatic row. It does not replace it.
        with self.conn:
            self.assertEqual(AB.add_manual(self.conn, "wine-b", UUID_2.upper()), UUID_2)
        self.assertEqual(AB.bindings(self.conn), {
            "wine-a": [(UUID_1, "automatic")],
            "wine-b": [(UUID_1, "automatic"), (UUID_2, "manual")]})
        self.assertEqual(AB.bindings(self.conn, "wine-b"),
                         {"wine-b": [(UUID_1, "automatic"), (UUID_2, "manual")]})
        self.assertEqual(AB.bindings(self.conn, "wine-c"), {})
        self.assertEqual(AB.counts(self.conn), (3, 1))

    def test_two_manual_products_in_add_order(self):
        with self.conn:
            AB.add_manual(self.conn, "wine-c", UUID_2)
            AB.add_manual(self.conn, "wine-c", UUID_1)
        self.assertEqual(AB.bindings(self.conn, "wine-c"),
                         {"wine-c": [(UUID_2, "manual"), (UUID_1, "manual")]})
        self.assertEqual(AB.counts(self.conn), (4, 2))

    def test_a_product_of_the_wine_is_refused(self):
        for product in (UUID_1, UUID_1.upper()):  # the automatic row of wine-a
            with self.subTest(product=product), self.assertRaisesRegex(
                    AB.DuplicateError, "wine-a already has the Atlas product " + UUID_1):
                AB.add_manual(self.conn, "wine-a", product)
        self.assertEqual(AB.counts(self.conn), (2, 0))

    def test_remove_takes_one_row_of_either_source(self):
        with self.conn:
            AB.add_manual(self.conn, "wine-a", UUID_2)
            self.assertEqual(AB.remove(self.conn, "wine-a", UUID_1), "automatic")
        self.assertEqual(AB.bindings(self.conn, "wine-a"), {"wine-a": [(UUID_2, "manual")]})
        with self.conn:
            self.assertEqual(AB.remove(self.conn, "wine-a", UUID_2), "manual")
            self.assertIsNone(AB.remove(self.conn, "wine-a", UUID_2))
        self.assertEqual(AB.bindings(self.conn, "wine-a"), {})
        self.assertEqual(AB.bindings(self.conn, "wine-b"), {"wine-b": [(UUID_1, "automatic")]})

    def test_approve_makes_the_automatic_row_manual_in_place(self):
        with self.conn:
            AB.add_manual(self.conn, "wine-a", UUID_2)
            self.assertEqual(AB.approve(self.conn, "wine-a", UUID_1), "automatic")
        # The approved row keeps its place before the manual row.
        self.assertEqual(AB.bindings(self.conn, "wine-a"),
                         {"wine-a": [(UUID_1, "manual"), (UUID_2, "manual")]})
        self.assertEqual(AB.bindings(self.conn, "wine-b"), {"wine-b": [(UUID_1, "automatic")]})
        with self.conn:
            self.assertEqual(AB.approve(self.conn, "wine-a", UUID_1), "manual")
            self.assertIsNone(AB.approve(self.conn, "wine-c", UUID_1))
        self.assertEqual(AB.counts(self.conn), (3, 2))

    def test_schema_refuses_a_bad_row(self):
        for row in (("wine-c", "manual", UUID_1.upper()), ("wine-c", "manual", "x" * 36),
                    ("wine-c", "other", UUID_1), ("wine-x", "manual", UUID_1),
                    ("wine-a", "manual", UUID_1)):  # the second row of wine-a and UUID_1
            with self.subTest(row=row), self.assertRaises(sqlite3.IntegrityError):
                with self.conn:
                    self.conn.execute("INSERT INTO wine_atlas_binding VALUES (?, ?, ?)", row)


class MigrationTest(unittest.TestCase):
    """Schema 025 keeps the effective row of each wine of schema 009 (plan 54)."""

    def test_the_migration_keeps_the_effective_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "schema"
            old.mkdir()
            for number, path in labdb.schema_files():
                if number < 25:
                    shutil.copy(path, old)
            db = str(Path(tmp) / "lab.sqlite3")
            conn = labdb.connect(db, create=True, directory=str(old))
            with conn:
                conn.executemany(
                    "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                    "region, description, csv_photo_name) "
                    "VALUES (?, 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp')",
                    [(slug,) for slug in ("wine-a", "wine-b", "wine-c", "wine-d")])
                conn.executemany("INSERT INTO wine_atlas_binding VALUES (?, ?, ?)", [
                    ("wine-a", "automatic", UUID_1), ("wine-b", "automatic", UUID_1),
                    ("wine-b", "manual", UUID_2), ("wine-c", "manual", UUID_2),
                    ("wine-d", "automatic", UUID_2), ("wine-d", "manual", UUID_2)])
            conn.close()
            conn = labdb.connect(db)
            try:
                self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0],
                                 len(labdb.schema_files()))
                self.assertEqual(conn.execute(
                    "SELECT wine_slug, source, product_uuid FROM wine_atlas_binding "
                    "ORDER BY rowid").fetchall(),
                    [("wine-a", "automatic", UUID_1), ("wine-b", "manual", UUID_2),
                     ("wine-c", "manual", UUID_2), ("wine-d", "manual", UUID_2)])
                self.assertEqual(conn.execute(
                    "SELECT name FROM sqlite_master WHERE tbl_name = 'wine_atlas_binding' "
                    "AND type = 'index' AND sql IS NOT NULL").fetchall(),
                    [("wine_atlas_binding_product",)])
                with conn:
                    AB.add_manual(conn, "wine-b", UUID_1)
                self.assertEqual(AB.bindings(conn, "wine-b"),
                                 {"wine-b": [(UUID_2, "manual"), (UUID_1, "manual")]})
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
