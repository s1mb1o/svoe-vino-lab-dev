"""Import the three test sets of `svoe-vino-testset/dataset/` into the lab database.

Usage:
    python3 pipeline/import_testsets.py --db data/lab.sqlite3
    python3 pipeline/import_testsets.py --db data/lab.sqlite3 --source ../../svoe-vino-testset/dataset
    python3 pipeline/import_testsets.py --db data/lab.sqlite3 --force

The sets are `my`, `official-real-photos`, and `vlmrerank-8b-failed`. The set name in the
database is the name of the directory. Each set is imported with `import_testset.py`, in
its own transaction, and the rules of that file apply. The owner named the three
directories on 2026-09-25T12:15:00+0300.

The script checks first that each set directory holds `photo/`, and that no set holds an
edit of the Testset page, unless `--force` (plan 24). It stops at the first error. The
sets before the error stay imported.
"""
import argparse
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import imagestore  # noqa: E402
import import_testset  # noqa: E402
import labdb  # noqa: E402

# The directory of the sets: `svoe-vino-testset/dataset/` next to this project.
SOURCE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))),
                          "svoe-vino-testset", "dataset")
SETS = ("my", "official-real-photos", "vlmrerank-8b-failed")


def import_all(db_path, source_dir, log=print, schema_dir=labdb.SCHEMA_DIR, force=False):
    """Import each set of `SETS` from `source_dir`. Return [(set name, directory, report)]."""
    missing = [name for name in SETS
               if not os.path.isdir(os.path.join(source_dir, name, "photo"))]
    if missing:
        raise import_testset.TestsetError("no photo directory for the sets %s in %s"
                                          % (", ".join(missing), source_dir))
    conn = labdb.connect(db_path, directory=schema_dir)
    try:
        for name in SETS:
            import_testset.check_not_edited(conn, name, force)
    finally:
        conn.close()
    done = []
    for name in SETS:
        set_dir = os.path.join(source_dir, name)
        report = import_testset.import_testset(db_path, name, set_dir, log, schema_dir, force)
        done.append((name, set_dir, report))
    return done


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Import the test sets my, official-real-photos, and "
                    "vlmrerank-8b-failed into the lab database, read-only.")
    parser.add_argument("--db", required=True, help="path of the lab database")
    parser.add_argument("--source", default=SOURCE_DIR,
                        help="the directory of the sets (default: %(default)s)")
    parser.add_argument("--force", action="store_true",
                        help="replace the edits of the Testset page with the files")
    args = parser.parse_args(argv)

    def log(message):
        print(message, flush=True)

    try:
        done = import_all(args.db, args.source, log, force=args.force)
    except (import_testset.TestsetError, imagestore.StoreError, labdb.SchemaError,
            sqlite3.Error, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    for name, set_dir, report in done:
        import_testset.print_report(report, name, set_dir, args.db)
        print()
    print("sets imported: %d" % len(done))
    return 0


if __name__ == "__main__":
    sys.exit(main())
