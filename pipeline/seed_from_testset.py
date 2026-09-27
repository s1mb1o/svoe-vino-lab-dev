"""Build the lab database again from svoe-vino-testset and its sources, then swap it in.

Usage:
    python3 pipeline/seed_from_testset.py --db data/lab.sqlite3

The script is the seed and the restore of the lab database. A first run fills an empty
lab. A later run brings the lab back to the state of the files of svoe-vino-testset after
a test. Read `docs/plans/28_seed-from-testset.md`.

The steps, in this order. Each step is one tool of `pipeline/`:
1. `labdb.py`: create the tables.
2. `import_catalog.py`: the wines of the Strapi CSV.
3. `seed_images.py`: the main image of each wine, from the Strapi uploads folder.
4. `seed_patched.py`: the patched main images.
5. `seed_codes.py`: the GTINs and the QR URLs of the code map of the matcher.
6. `seed_atlas_bindings.py`: the automatic and the manual Atlas Core bindings.
7. `import_testsets.py`: the test sets `my`, `official-real-photos`, and
   `vlmrerank-8b-failed`, with their labels, the comments of the photos, and the variant
   groups. The old wine notes and the reasons of the old excluded slugs of the files
   become wine comments (plan 51).
8. `seed_label_cuts.py`: the label cut of each full original. The owner chose on
   2026-09-25 that each run makes the label cuts.

Rules:
- The script builds a new database `<db>.seeding` next to `--db`. So the new database
  uses the same image store `images/` as `--db`, and a stored file is not copied again.
- Each step runs as a separate process. A step that exits with a status other than 0
  stops the script. `--db` then does not change. The partial database stays at
  `<db>.seeding` for a check. The next run deletes it.
- After the last step, the script copies `--db` to `backups/<name>-<UTC time>.sqlite3`
  next to it. Then it copies the new database into `--db`. The two copies use the SQLite
  backup API, so a running lab server does not need a restart.
- The script reads the sources. It never writes to them.
- The new database holds the data of the sources alone. The data that the lab alone
  holds are not in it, for example a wine state, a comment, a favorite, a wine added by
  hand, an alternative photo, and an image description. The backup keeps them.
- The script prints the row count of each table in the old and in the new database.
"""
import argparse
import datetime
import os
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.dirname(os.path.dirname(HERE))

# The sources. The paths are the paths of `COMMANDS.md`. The patch folder, the code map,
# and the two Atlas files are the keys `patch_dir`, `barcode_file`, `atlas_matches_file`,
# and `atlas_bindings_file` of `svoe-vino-testset/config.yaml`.
HACKATON = os.path.join(WORKSPACE, "svoe-wino-hackaton", "dataset")
DELIVERY = os.path.join(HACKATON, "official-2026-09-17")
DERIVED = os.path.join(HACKATON, "derived", "official-2026-09-17")
CATALOG_CSV = os.path.join(DELIVERY, "strapi_output0709.csv")
UPLOADS = os.path.join(DELIVERY, "prod-svoe-vino-strapi", "prod-svoe-vino", "strapi",
                       "uploads")
PATCH_DIR = os.path.join(HACKATON, "patched-official-2026-09-17")
CODE_MAP = os.path.join(WORKSPACE, "svoe-vino-matcher", "dataset", "code-map.json")
ATLAS_MATCHES = os.path.join(DERIVED, "atlas-matches.jsonl")
ATLAS_MANUAL = os.path.join(DERIVED, "atlas-bindings.manual.jsonl")
TESTSETS = os.path.join(WORKSPACE, "svoe-vino-testset", "dataset")

WORK_SUFFIX = ".seeding"


def tool(name, *args):
    """Return the command line of one tool of `pipeline/`."""
    return [sys.executable, os.path.join(HERE, name)] + list(args)


def steps(work):
    """Return the steps as [(name, command line)]. Each step writes to `work`."""
    return [
        ("tables", tool("labdb.py", work)),
        ("catalogue", tool("import_catalog.py", "--db", work, CATALOG_CSV)),
        ("main images", tool("seed_images.py", "--db", work, UPLOADS)),
        ("patches", tool("seed_patched.py", "--db", work, PATCH_DIR)),
        ("GTINs and QR URLs", tool("seed_codes.py", "--db", work, CODE_MAP)),
        ("Atlas Core bindings", tool("seed_atlas_bindings.py", "--db", work,
                                     "--matches", ATLAS_MATCHES, "--manual", ATLAS_MANUAL)),
        ("test sets", tool("import_testsets.py", "--db", work, "--source", TESTSETS)),
        ("label cuts", tool("seed_label_cuts.py", "--db", work)),
    ]


def remove_database(path):
    """Delete the database file at `path` and its rollback journal, if they exist."""
    for name in (path, path + "-journal"):
        if os.path.exists(name):
            os.unlink(name)


def run_steps(work, log=print):
    """Run each step. Return the name of the failed step, or None."""
    todo = steps(work)
    for number, (name, command) in enumerate(todo, 1):
        log("== step %d of %d: %s" % (number, len(todo), name))
        started = time.monotonic()
        status = subprocess.run(command).returncode
        log("== step %d: exit status %d, %.0f s" % (number, status,
                                                    time.monotonic() - started))
        if status != 0:
            return name
    return None


def row_counts(path):
    """Return {table: row count} of the database at `path`, or {} with no file."""
    if not os.path.isfile(path):
        return {}
    with closing(sqlite3.connect(Path(path).as_uri() + "?mode=ro", uri=True)) as conn:
        names = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {name: conn.execute('SELECT count(*) FROM "%s"' % name).fetchone()[0]
                for name in names}


def copy_database(source, target):
    """Copy the database `source` into `target` with the SQLite backup API."""
    with closing(sqlite3.connect(Path(source).as_uri() + "?mode=ro", uri=True)) as src, \
            closing(sqlite3.connect(target)) as dst:
        src.backup(dst)


def backup_path(db_path, now):
    """Return the path of the backup of `db_path`: `backups/<name>-<UTC time>.sqlite3`."""
    stem = os.path.splitext(os.path.basename(db_path))[0]
    return os.path.join(os.path.dirname(db_path), "backups",
                        "%s-%s.sqlite3" % (stem, now.strftime("%Y%m%dT%H%M%SZ")))


def swap(work, db_path, now):
    """Back up `db_path`, copy `work` into it, and delete `work`. Return the backup path,
    or None when no database was at `db_path`."""
    backup = None
    if os.path.isfile(db_path):
        backup = backup_path(db_path, now)
        if os.path.exists(backup):
            raise FileExistsError("the backup %s exists already" % backup)
        os.makedirs(os.path.dirname(backup), exist_ok=True)
        copy_database(db_path, backup)
    copy_database(work, db_path)
    remove_database(work)
    return backup


def print_counts(old, new, log=print):
    names = sorted(set(old) | set(new))
    width = max([len("table")] + [len(name) for name in names])
    log("%-*s %8s %8s" % (width, "table", "old", "new"))
    for name in names:
        log("%-*s %8s %8s" % (width, name, old.get(name, "-"), new.get(name, "-")))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build the lab database again from svoe-vino-testset and its "
                    "sources. Back up the old database, then swap the new one in.")
    parser.add_argument("--db", required=True,
                        help="path of the lab database, for example data/lab.sqlite3")
    args = parser.parse_args(argv)

    db_path = os.path.abspath(args.db)
    work = db_path + WORK_SUFFIX
    if os.path.exists(work):
        print("delete the partial database of an earlier run: %s" % work, flush=True)
    remove_database(work)

    failed = run_steps(work, log=lambda message: print(message, flush=True))
    if failed:
        print("stopped: the step `%s` failed. %s did not change. The partial database "
              "stays at %s." % (failed, db_path, work))
        return 1

    old = row_counts(db_path)
    new = row_counts(work)
    backup = swap(work, db_path, datetime.datetime.now(datetime.timezone.utc))
    print_counts(old, new)
    print("backup: %s" % (backup or "none; no database was at %s" % db_path))
    print("result: %s holds the state of svoe-vino-testset" % db_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
