import contextlib
import datetime
import io
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import seed_from_testset as SFT  # noqa: E402

NOW = datetime.datetime(2026, 9, 25, 15, 0, 0, tzinfo=datetime.timezone.utc)

# A step that writes the value of argv[2] into the table `t` of the database argv[1].
WRITE_VALUE = ("import sqlite3, sys\n"
               "conn = sqlite3.connect(sys.argv[1])\n"
               "conn.execute('CREATE TABLE IF NOT EXISTS t (x INTEGER)')\n"
               "conn.execute('INSERT INTO t VALUES (?)', (int(sys.argv[2]),))\n"
               "conn.execute('PRAGMA user_version = 7')\n"
               "conn.commit()\n")


def make_database(path, value):
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (?)", (value,))
        conn.commit()


def values(path):
    with closing(sqlite3.connect(path)) as conn:
        return [row[0] for row in conn.execute("SELECT x FROM t ORDER BY x")]


def user_version(path):
    with closing(sqlite3.connect(path)) as conn:
        return conn.execute("PRAGMA user_version").fetchone()[0]


class SeedFromTestsetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = str(self.root / "lab.sqlite3")
        self.work = self.db + SFT.WORK_SUFFIX
        self.steps = SFT.steps

    def tearDown(self):
        SFT.steps = self.steps
        self.tmp.cleanup()

    def use_steps(self, *commands):
        SFT.steps = lambda work: [("step %d" % number, [part.replace("{work}", work)
                                                         for part in command])
                                  for number, command in enumerate(commands, 1)]

    def run_main(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = SFT.main(["--db", self.db])
        return status, out.getvalue()

    def test_each_step_names_a_tool_of_pipeline(self):
        for name, command in self.steps("/tmp/x.seeding"):
            self.assertEqual(command[0], sys.executable, name)
            self.assertTrue(os.path.isfile(command[1]), command[1])
            self.assertIn("/tmp/x.seeding", command, name)

    def test_the_steps_run_in_order(self):
        names = [name for name, _ in self.steps("w")]
        self.assertEqual(names[0], "tables")
        self.assertEqual(names[-1], "label cuts")
        self.assertLess(names.index("catalogue"), names.index("main images"))
        self.assertLess(names.index("catalogue"), names.index("test sets"))

    def test_swap_backs_up_the_old_database(self):
        make_database(self.db, 1)
        make_database(self.work, 2)
        backup = SFT.swap(self.work, self.db, NOW)
        self.assertEqual(backup, str(self.root / "backups" / "lab-20260925T150000Z.sqlite3"))
        self.assertEqual(values(backup), [1])
        self.assertEqual(values(self.db), [2])
        self.assertFalse(os.path.exists(self.work))

    def test_swap_with_no_old_database_makes_no_backup(self):
        make_database(self.work, 2)
        self.assertIsNone(SFT.swap(self.work, self.db, NOW))
        self.assertEqual(values(self.db), [2])
        self.assertFalse((self.root / "backups").exists())

    def test_swap_refuses_an_existing_backup(self):
        make_database(self.db, 1)
        make_database(self.work, 2)
        backup = Path(SFT.backup_path(self.db, NOW))
        backup.parent.mkdir()
        backup.write_bytes(b"x")
        with self.assertRaises(FileExistsError):
            SFT.swap(self.work, self.db, NOW)
        self.assertEqual(values(self.db), [1])

    def test_swap_keeps_an_open_connection_working(self):
        make_database(self.db, 1)
        make_database(self.work, 2)
        with closing(sqlite3.connect(self.db)) as reader:
            self.assertEqual(reader.execute("SELECT x FROM t").fetchall(), [(1,)])
            SFT.swap(self.work, self.db, NOW)
            self.assertEqual(reader.execute("SELECT x FROM t").fetchall(), [(2,)])

    def test_main_swaps_the_new_database_in(self):
        make_database(self.db, 1)
        self.use_steps([sys.executable, "-c", WRITE_VALUE, "{work}", "5"],
                       [sys.executable, "-c", WRITE_VALUE, "{work}", "6"])
        status, out = self.run_main()
        self.assertEqual(status, 0, out)
        self.assertEqual(values(self.db), [5, 6])
        self.assertEqual(user_version(self.db), 7)
        self.assertEqual(len(list((self.root / "backups").iterdir())), 1)
        self.assertFalse(os.path.exists(self.work))
        self.assertRegex(out, r"t\s+1\s+2")
        self.assertIn("result:", out)

    def test_a_failed_step_keeps_the_old_database(self):
        make_database(self.db, 1)
        self.use_steps([sys.executable, "-c", WRITE_VALUE, "{work}", "5"],
                       [sys.executable, "-c", "raise SystemExit(1)"],
                       [sys.executable, "-c", WRITE_VALUE, "{work}", "6"])
        status, out = self.run_main()
        self.assertEqual(status, 1)
        self.assertIn("stopped: the step `step 2` failed", out)
        self.assertEqual(values(self.db), [1])
        self.assertEqual(values(self.work), [5])
        self.assertFalse((self.root / "backups").exists())

    def test_a_partial_database_of_an_earlier_run_is_deleted(self):
        make_database(self.work, 9)
        Path(self.work + "-journal").write_bytes(b"")
        self.use_steps([sys.executable, "-c", WRITE_VALUE, "{work}", "5"])
        status, out = self.run_main()
        self.assertEqual(status, 0, out)
        self.assertIn("delete the partial database", out)
        self.assertEqual(values(self.db), [5])
        self.assertFalse(os.path.exists(self.work + "-journal"))
        self.assertIn("backup: none", out)

    def test_row_counts(self):
        self.assertEqual(SFT.row_counts(self.db), {})
        make_database(self.db, 1)
        self.assertEqual(SFT.row_counts(self.db), {"t": 1})


if __name__ == "__main__":
    unittest.main()
