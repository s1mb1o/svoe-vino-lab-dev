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

    def test_manual_row_wins(self):
        with self.conn:
            self.assertEqual(AB.set_manual(self.conn, "wine-b", UUID_2.upper()), UUID_2)
        self.assertEqual(AB.bindings(self.conn), {"wine-a": (UUID_1, "automatic"),
                                                  "wine-b": (UUID_2, "manual")})
        self.assertEqual(AB.bindings(self.conn, "wine-b"), {"wine-b": (UUID_2, "manual")})
        self.assertEqual(AB.bindings(self.conn, "wine-c"), {})
        self.assertEqual(AB.counts(self.conn), (2, 1))

    def test_set_replaces_the_manual_row(self):
        with self.conn:
            AB.set_manual(self.conn, "wine-c", UUID_1)
            AB.set_manual(self.conn, "wine-c", UUID_2)
        self.assertEqual(AB.bindings(self.conn, "wine-c"), {"wine-c": (UUID_2, "manual")})
        self.assertEqual(AB.counts(self.conn), (3, 1))

    def test_remove_keeps_the_automatic_row(self):
        with self.conn:
            AB.set_manual(self.conn, "wine-a", UUID_2)
            self.assertEqual(AB.remove_manual(self.conn, "wine-a"), UUID_2)
            self.assertIsNone(AB.remove_manual(self.conn, "wine-a"))
        self.assertEqual(AB.bindings(self.conn, "wine-a"), {"wine-a": (UUID_1, "automatic")})

    def test_schema_refuses_a_bad_row(self):
        for row in (("wine-c", "manual", UUID_1.upper()), ("wine-c", "manual", "x" * 36),
                    ("wine-c", "other", UUID_1), ("wine-x", "manual", UUID_1),
                    ("wine-a", "automatic", UUID_2)):  # the second automatic row of wine-a
            with self.subTest(row=row), self.assertRaises(sqlite3.IntegrityError):
                with self.conn:
                    self.conn.execute("INSERT INTO wine_atlas_binding VALUES (?, ?, ?)", row)


if __name__ == "__main__":
    unittest.main()
