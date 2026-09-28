"""Create the lab database, or bring its schema up to date.

The schema is in `pipeline/schema/NNN_<name>.sql`. `PRAGMA user_version` holds the
number of the last applied file. `connect` applies each newer file in number order,
one transaction per file. Read `docs/plans/07_sqlite-lab-database.md`.

Usage:
    python3 pipeline/labdb.py data/catalog/catalog.sqlite3
"""
import argparse
import os
import re
import sqlite3
import sys

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema")
SCHEMA_RE = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")
# The folder of each image type of `wine_image` in the image store. Read
# `pipeline/schema/005_wine_image.sql` and the schema files of the additional types
# (010 and later).
IMAGE_FOLDERS = {"main": "main", "main_patched": "patched", "full_front": "additional",
                 "label_front": "additional", "full_back": "additional",
                 "label_back": "additional"}
# The folder of the processed files. Read `pipeline/schema/007_image_table.sql`.
DERIVED_FOLDER = "cropped"
# The folder of the test photos.
TESTSET_FOLDER = "testset"
# The layout of the data directory (plan 75). The database file is in the catalogue
# directory `catalog/`. The parent of that directory is the data root. The data root
# holds `testsets/`, `cache/`, and `backups/`. A database file in a directory with
# another name is its own data root, so each file of a unit test stays in the temporary
# directory of the test.
CATALOG_DIR = "catalog"


class SchemaError(Exception):
    """The schema files and the database version do not agree."""


def schema_files(directory=SCHEMA_DIR):
    """Return the schema files as a list of (number, path), in number order."""
    files = []
    for name in os.listdir(directory):
        match = SCHEMA_RE.match(name)
        if match:
            files.append((int(match.group(1)), os.path.join(directory, name)))
    files.sort()
    numbers = [number for number, _ in files]
    if numbers != list(range(1, len(numbers) + 1)):
        raise SchemaError("the schema files must be numbered 001, 002, ... "
                          "with no gap; found %s" % numbers)
    return files


def migrate(conn, directory=SCHEMA_DIR):
    """Apply each schema file that is newer than the database. Return the version."""
    files = schema_files(directory)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version > len(files):
        raise SchemaError("the database has schema version %d; this code knows "
                          "version %d" % (version, len(files)))
    for number, path in files[version:]:
        with open(path, encoding="utf-8") as fh:
            sql = fh.read()
        # A schema file MAY build a parent table again, for example `wine_catalog`. The
        # DROP of the old table breaks the links of the child tables until the new table
        # takes the name. So the foreign keys are off during the file, and
        # `PRAGMA foreign_key_check` checks each link before the COMMIT. The pragma
        # `foreign_keys` has no effect inside a transaction, so it is set before BEGIN.
        foreign_keys = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            conn.executescript("BEGIN;\n%s\n" % sql)
            broken = conn.execute("PRAGMA foreign_key_check").fetchall()
            if broken:
                raise SchemaError("the schema file %s breaks %d foreign keys; the first: %r"
                                  % (os.path.basename(path), len(broken), broken[0]))
            conn.execute("PRAGMA user_version = %d" % number)
            conn.commit()
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.execute("PRAGMA foreign_keys = %s" % ("ON" if foreign_keys else "OFF"))
        version = number
    return version


def connect(path, create=False, directory=SCHEMA_DIR):
    """Open the database at `path`, turn on foreign keys, and migrate it.

    A missing file is an error unless `create` is true. The check stops a mistyped
    path from making a second, empty database.
    """
    if not create and not os.path.isfile(path):
        raise SchemaError("no database at %s; create it with "
                          "`python3 pipeline/labdb.py %s`" % (path, path))
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        migrate(conn, directory)
    except Exception:
        conn.close()
        raise
    return conn


def catalog_dir(db_path):
    """Return the catalogue directory: the directory of the database file."""
    return os.path.dirname(os.path.abspath(db_path))


def data_root(db_path):
    """Return the data root of the database at `db_path` (plan 75)."""
    directory = catalog_dir(db_path)
    if os.path.basename(directory) == CATALOG_DIR:
        return os.path.dirname(directory)
    return directory


def image_dir(db_path, folder):
    """Return the directory of the files of one folder of the table `image`.

    The catalogue images are in `<catalogue>/images/<folder>/`, the processed files in
    `<catalogue>/cuts/`, and the test photos in `<data root>/testsets/images/`.
    """
    if folder == TESTSET_FOLDER:
        return os.path.join(data_root(db_path), "testsets", "images")
    if folder == DERIVED_FOLDER:
        return os.path.join(catalog_dir(db_path), "cuts")
    return os.path.join(catalog_dir(db_path), "images", folder)


def backups_dir(db_path):
    """Return the directory of the database copies: `<data root>/backups/`."""
    return os.path.join(data_root(db_path), "backups")


def tables(conn):
    """Return the names of the tables, in name order."""
    return [row[0] for row in conn.execute(
        "SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name")]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Create the lab database, or bring its schema up to date.")
    parser.add_argument("db", help="path of the database file")
    args = parser.parse_args(argv)

    existed = os.path.isfile(args.db)
    parent = os.path.dirname(os.path.abspath(args.db))
    os.makedirs(parent, exist_ok=True)
    try:
        conn = connect(args.db, create=True)
    except (SchemaError, sqlite3.Error) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    names = tables(conn)
    conn.close()
    print("database: %s (%s)" % (args.db, "existing" if existed else "created"))
    print("schema version: %d" % version)
    print("tables: %s" % ", ".join(names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
