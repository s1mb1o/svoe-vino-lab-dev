import contextlib
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import labdb  # noqa: E402
import seed_atlas_bindings as SA  # noqa: E402

UUID_1 = "6062ada1-1c2b-4f3e-9a8b-0123456789ab"
UUID_2 = "7a1b2c3d-0000-4000-8000-00000000000f"
UUID_3 = "00000000-1111-4222-8333-444444444444"
MATCHES = [{"wine_slug": "wine-a", "product_uuid": UUID_1},
           {"wine_slug": "wine-b", "product_uuid": UUID_1.upper()}]
MANUAL = [{"wine_slug": "wine-c", "product_uuid": UUID_2}]


class SeedAtlasBindingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = str(self.root / "lab.sqlite3")
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.executemany(
                "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                "region, description, csv_photo_name) "
                "VALUES (?, 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp')",
                [(slug,) for slug in ("wine-a", "wine-b", "wine-c")])
        conn.close()
        self.log = []

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, records):
        path = self.root / name
        path.write_text("".join(json.dumps(r) + "\n" if not isinstance(r, str) else r
                                for r in records), encoding="utf-8")
        return str(path)

    def seed(self, matches=MATCHES, manual=MANUAL, force=False):
        return SA.seed_bindings(self.db, self.write("m.jsonl", matches) if matches else None,
                                self.write("b.jsonl", manual) if manual else None,
                                log=self.log.append, force=force)

    def rows(self):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute("SELECT wine_slug, source, product_uuid FROM "
                                "wine_atlas_binding ORDER BY rowid").fetchall()
        finally:
            conn.close()

    def test_seed_adds_both_sources(self):
        read, added, differs, missing = self.seed()
        self.assertEqual(self.rows(), [("wine-a", "automatic", UUID_1),
                                       ("wine-b", "automatic", UUID_1),
                                       ("wine-c", "manual", UUID_2)])
        self.assertEqual(read, {"automatic": 2, "manual": 1})
        self.assertEqual(added, read)
        self.assertEqual((differs, missing), ([], []))

    def test_second_run_is_refused_unless_force(self):
        # The owner chose on 2026-09-25: a second run MUST NOT add back a removed value.
        self.seed()
        with self.assertRaisesRegex(SA.SeedError,
                                    "wine_atlas_binding already holds 3 rows.*--force"):
            self.seed()
        _read, added, _differs, _missing = self.seed(force=True)
        self.assertEqual(added, {"automatic": 0, "manual": 0})
        self.assertEqual(len(self.rows()), 3)

    def test_changed_row_is_counted_and_not_applied(self):
        self.seed()
        _read, added, differs, _missing = self.seed(
            matches=[{"wine_slug": "wine-a", "product_uuid": UUID_3}], manual=None, force=True)
        self.assertEqual(added, {"automatic": 0, "manual": 0})
        self.assertEqual(differs, [("wine-a", "automatic", UUID_3)])
        self.assertEqual(self.log, ["differs: wine-a automatic"])
        self.assertIn(("wine-a", "automatic", UUID_1), self.rows())

    def test_manual_and_automatic_rows_of_one_wine(self):
        self.seed(manual=[{"wine_slug": "wine-a", "product_uuid": UUID_2}])
        self.assertEqual(self.rows()[:1] + self.rows()[2:],
                         [("wine-a", "automatic", UUID_1), ("wine-a", "manual", UUID_2)])

    def test_slug_with_no_wine_is_skipped(self):
        _read, added, _differs, missing = self.seed(
            matches=[{"wine_slug": "wine-x", "product_uuid": UUID_1}], manual=None)
        self.assertEqual(missing, ["wine-x"])
        self.assertEqual(self.log, ["no wine: wine-x"])
        self.assertEqual(added, {"automatic": 0, "manual": 0})

    def test_bad_rows_stop_the_seed_with_no_write(self):
        for records, message in (
                ([{"wine_slug": "wine-a", "product_uuid": "x"}], r"line 1 \(wine-a\): .*not a valid UUID"),
                ([{"wine_slug": "wine-a", "product_uuid": UUID_1},
                  {"wine_slug": "wine-a", "product_uuid": UUID_2}], "line 2: the slug wine-a has two"),
                (["[1]\n"], "line 1 MUST be an object"),
                (["{\n"], "line 1: not JSON"),
                ([{"product_uuid": UUID_1}], "line 1 MUST name `wine_slug`")):
            with self.subTest(records=records), self.assertRaisesRegex(SA.SeedError, message):
                self.seed(matches=[{"wine_slug": "wine-b", "product_uuid": UUID_1}],
                          manual=records)
            self.assertEqual(self.rows(), [])

    def test_same_row_twice_in_one_file_is_one_row(self):
        self.seed(matches=MATCHES + MATCHES[:1], manual=None)
        self.assertEqual(len(self.rows()), 2)

    def test_main_refuses_a_second_run_unless_force(self):
        matches, manual = self.write("m.jsonl", MATCHES), self.write("b.jsonl", MANUAL)
        argv = ["--db", self.db, "--matches", matches, "--manual", manual]
        outputs = []
        for args, code in ((argv, 0), (argv, 1), (argv + ["--force"], 0)):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(SA.main(args), code)
            outputs.append(out.getvalue() + err.getvalue())
        self.assertIn("added: automatic 2, manual 1\n", outputs[0])
        self.assertIn("result: seeded\n", outputs[0])
        self.assertIn("error: wine_atlas_binding already holds 3 rows", outputs[1])
        self.assertIn("added: automatic 0, manual 0\n", outputs[2])
        self.assertIn("result: no change\n", outputs[2])

    def test_main_needs_a_file(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            SA.main(["--db", self.db])


if __name__ == "__main__":
    unittest.main()
