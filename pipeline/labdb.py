"""Create the lab database, or bring its schema up to date.

The schema is in `pipeline/schema/NNN_<name>.sql`. `PRAGMA user_version` holds the
number of the last applied file. `connect` applies each newer file in number order,
one transaction per file. Read `docs/plans/07_sqlite-lab-database.md`.

Usage:
    python3 pipeline/labdb.py data/lab.sqlite3
"""
import argparse
import os
import re
import sqlite3
import sys

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema")
SCHEMA_RE = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")
# The folder of each image type of `wine_image` in the image store. Read
# `pipeline/schema/005_wine_image.sql`.
IMAGE_FOLDERS = {"main": "main", "main_patched": "patched", "front": "additional",
                 "back": "additional", "label_front": "additional",
                 "label_back": "additional"}


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
        try:
            conn.executescript("BEGIN;\n%s\nPRAGMA user_version = %d;\nCOMMIT;"
                               % (sql, number))
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise
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


def image_store(db_path):
    """Return the image store of the database at `db_path`: `images/` next to it."""
    return os.path.join(os.path.dirname(os.path.abspath(db_path)), "images")


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
