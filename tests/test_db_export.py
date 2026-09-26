import filecmp
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import db_export  # noqa: E402
import labdb  # noqa: E402

# A small database with each feature that the export must keep: a text key whose rowid
# order differs from the key order, an INTEGER PRIMARY KEY, a WITHOUT ROWID table, an
# index, a view, a trigger that changes a new row, and the schema version.
SCHEMA = """
CREATE TABLE wine (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price REAL,
    modified_at TEXT
) STRICT;
CREATE TABLE note (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL REFERENCES wine (slug),
    text TEXT NOT NULL
) STRICT;
CREATE TABLE pair (a TEXT, b TEXT, PRIMARY KEY (a, b)) WITHOUT ROWID, STRICT;
INSERT INTO wine VALUES ('zeta', 'Зета «Резерв»', 12.5, NULL);
INSERT INTO wine VALUES ('alpha', 'Alpha "One"
two lines', 3.0, '2026-09-01T00:00:00Z');
INSERT INTO note VALUES (5, 'zeta', 'first');
INSERT INTO note VALUES (2, 'alpha', 'second');
INSERT INTO pair VALUES ('y', '1'), ('x', '2');
CREATE INDEX note_slug ON note (slug);
CREATE VIEW wine_name AS SELECT slug, name FROM wine;
CREATE TRIGGER wine_insert_time AFTER INSERT ON wine WHEN NEW.modified_at IS NULL
BEGIN
    UPDATE wine SET modified_at = 'set by the trigger' WHERE rowid = NEW.rowid;
END;
PRAGMA user_version = 7;
"""


class DbExportTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")
        self.out = str(self.root / "export")
        conn = sqlite3.connect(self.db)
        conn.executescript(SCHEMA)
        conn.close()

    def tearDown(self):
        self.directory.cleanup()

    def query(self, db, sql):
        conn = sqlite3.connect(db)
        try:
            return conn.execute(sql).fetchall()
        finally:
            conn.close()

    def read(self, name):
        return Path(self.out, name).read_text(encoding="utf-8")

    def assert_same_files(self, one, two):
        compare = filecmp.dircmp(one, two)
        self.assertEqual((compare.left_only, compare.right_only), ([], []))
        names = ["schema.sql", "after-rows.sql"] + [
            os.path.join("rows", n) for n in os.listdir(os.path.join(one, "rows"))]
        match, mismatch, errors = filecmp.cmpfiles(one, two, names, shallow=False)
        self.assertEqual((mismatch, errors), ([], []))

    def test_rows_follow_the_key_and_keep_the_rowid(self):
        version, counts = db_export.export(self.db, self.out)
        self.assertEqual(version, 7)
        self.assertEqual(counts, {"wine": 2, "note": 2, "pair": 2})
        self.assertEqual(self.read("rows/wine.jsonl"), (
            '{"rowid":2,"slug":"alpha","name":"Alpha \\"One\\"\\ntwo lines","price":3.0,'
            '"modified_at":"2026-09-01T00:00:00Z"}\n'
            '{"rowid":1,"slug":"zeta","name":"Зета «Резерв»","price":12.5,'
            '"modified_at":null}\n'))
        # The INTEGER PRIMARY KEY is the rowid, so the rows carry no second copy of it.
        self.assertEqual(self.read("rows/note.jsonl"),
                         '{"id":2,"slug":"alpha","text":"second"}\n'
                         '{"id":5,"slug":"zeta","text":"first"}\n')
        self.assertEqual(self.read("rows/pair.jsonl"),
                         '{"a":"x","b":"2"}\n{"a":"y","b":"1"}\n')
        self.assertTrue(self.read("schema.sql").startswith("CREATE TABLE wine ("))
        self.assertNotIn("TRIGGER", self.read("schema.sql"))
        after = self.read("after-rows.sql")
        self.assertIn("CREATE INDEX note_slug", after)
        self.assertIn("CREATE VIEW wine_name", after)
        self.assertIn("CREATE TRIGGER wine_insert_time", after)
        self.assertTrue(after.endswith("PRAGMA user_version = 7;\n"))

    def test_restore_gives_the_same_database(self):
        db_export.export(self.db, self.out)
        restored = str(self.root / "restored.sqlite3")
        version, counts = db_export.restore(self.out, restored)
        self.assertEqual((version, counts), (7, {"wine": 2, "note": 2, "pair": 2}))
        for sql in ("SELECT rowid, * FROM wine ORDER BY rowid",
                    "SELECT * FROM note ORDER BY rowid", "SELECT * FROM pair",
                    "SELECT * FROM wine_name ORDER BY slug", "PRAGMA user_version",
                    "SELECT type, name, sql FROM sqlite_schema ORDER BY name"):
            self.assertEqual(self.query(restored, sql), self.query(self.db, sql), sql)
        # The trigger came after the rows: the NULL of `zeta` stays NULL.
        self.assertEqual(self.query(restored, "SELECT modified_at FROM wine "
                                              "WHERE slug = 'zeta'"), [(None,)])
        again = str(self.root / "again")
        db_export.export(restored, again)
        self.assert_same_files(self.out, again)

    def test_restore_refuses_an_existing_file(self):
        db_export.export(self.db, self.out)
        with self.assertRaises(db_export.ExportError):
            db_export.restore(self.out, self.db)
        self.assertEqual(self.query(self.db, "SELECT count(*) FROM wine"), [(2,)])

    def test_restore_of_a_broken_export_leaves_no_file(self):
        db_export.export(self.db, self.out)
        Path(self.out, "rows", "note.jsonl").write_text(
            '{"id":9,"slug":"missing","text":"x"}\n', encoding="utf-8")
        restored = self.root / "restored.sqlite3"
        with self.assertRaises(db_export.ExportError):
            db_export.restore(self.out, str(restored))
        self.assertEqual(sorted(p.name for p in self.root.iterdir()
                                if p.name.startswith("restored")), [])

    def test_export_removes_the_file_of_a_dropped_table(self):
        db_export.export(self.db, self.out)
        conn = sqlite3.connect(self.db)
        conn.execute("DROP TABLE pair")
        conn.close()
        version, counts = db_export.export(self.db, self.out)
        self.assertEqual(sorted(os.listdir(os.path.join(self.out, "rows"))),
                         ["note.jsonl", "wine.jsonl"])

    def test_export_refuses_a_blob(self):
        conn = sqlite3.connect(self.db)
        conn.executescript("CREATE TABLE raw (k TEXT PRIMARY KEY, v ANY) STRICT;"
                           "INSERT INTO raw VALUES ('a', x'00ff');")
        conn.close()
        with self.assertRaises(db_export.ExportError):
            db_export.export(self.db, self.out)

    def test_export_of_a_missing_database_is_an_error(self):
        with self.assertRaises(db_export.ExportError):
            db_export.export(str(self.root / "none.sqlite3"), self.out)
        self.assertFalse((self.root / "none.sqlite3").exists())

    def test_lab_schema_restores_and_opens(self):
        lab = str(self.root / "lab-full.sqlite3")
        labdb.connect(lab, create=True).close()
        out = str(self.root / "lab-export")
        version, counts = db_export.export(lab, out)
        self.assertEqual(version, len(labdb.schema_files()))
        restored = str(self.root / "lab-restored.sqlite3")
        db_export.restore(out, restored)
        conn = labdb.connect(restored)
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone(), (version,))
        conn.close()
        again = str(self.root / "lab-again")
        db_export.export(restored, again)
        self.assert_same_files(out, again)


if __name__ == "__main__":
    unittest.main()
