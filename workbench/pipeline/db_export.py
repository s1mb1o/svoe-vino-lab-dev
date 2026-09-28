"""Export the lab database to text files for git, or restore it from them.

git cannot show the history of `data/catalog/catalog.sqlite3`: the file is binary, and
the database file is out of git. The export writes text files with one row on each
line, so `git diff` shows each added, changed, and removed row. Read `docs/plans/50_lab-db-text-export.md`.

The export directory:
    schema.sql          the CREATE TABLE statements, in the order of `sqlite_schema`
    rows/<table>.jsonl  one JSON object for each row, in primary key order
    after-rows.sql      the indexes, the views, the triggers, and `PRAGMA user_version`

Each row keeps its `rowid`, because the lab code sorts by `rowid` to keep the import
order. A table whose `INTEGER PRIMARY KEY` is the `rowid` has no separate key `rowid`.
The restore creates the triggers after the rows, so that a trigger does not change a
restored row.

Usage:
    python3 pipeline/db_export.py export [--db data/catalog/catalog.sqlite3] [--out db-export]
    python3 pipeline/db_export.py restore --from db-export --db <new file>
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.request

DEFAULT_DB = "data/catalog/catalog.sqlite3"
DEFAULT_OUT = "db-export"
SCHEMA_FILE = "schema.sql"
AFTER_FILE = "after-rows.sql"
ROWS_DIR = "rows"
# A table name becomes a file name, so it must be safe as one.
TABLE_RE = re.compile(r"^[A-Za-z0-9_]+$")


class ExportError(Exception):
    """The database or the export directory holds something that the tool cannot keep."""


def quote(name):
    """Return `name` as an SQL identifier in double quotes."""
    return '"%s"' % name.replace('"', '""')


def snapshot(path):
    """Copy the database at `path` into memory with the backup API, and return the copy.

    The copy reads the file in one step, so the export sees one state of the database
    and a running lab server waits for the copy alone.
    """
    if not os.path.isfile(path):
        raise ExportError("no database at %s" % path)
    uri = "file:%s?mode=ro" % urllib.request.pathname2url(os.path.abspath(path))
    src = sqlite3.connect(uri, uri=True)
    try:
        copy = sqlite3.connect(":memory:")
        src.backup(copy)
    finally:
        src.close()
    return copy


def table_names(conn):
    """Return the names of the user tables, in the order of `sqlite_schema`."""
    names = [name for (name,) in conn.execute(
        "SELECT name FROM sqlite_schema WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite\\_%' ESCAPE '\\' ORDER BY rowid")]
    for name in names:
        if not TABLE_RE.match(name):
            raise ExportError("the table name %r cannot be a file name" % name)
    return names


def statements(conn, types):
    """Return the SQL of the schema objects of `types`, in the order of `sqlite_schema`.

    An automatic index has no SQL. SQLite makes it again with its table.
    """
    rows = conn.execute(
        "SELECT sql FROM sqlite_schema WHERE type IN (%s) AND sql IS NOT NULL "
        "AND name NOT LIKE 'sqlite\\_%%' ESCAPE '\\' ORDER BY rowid"
        % ", ".join("?" * len(types)), types).fetchall()
    return "".join(sql + ";\n\n" for (sql,) in rows)


def layout(conn, table):
    """Return the columns of `table`, its sort key, and whether a row needs a key `rowid`."""
    info = conn.execute("PRAGMA table_info(%s)" % quote(table)).fetchall()
    columns = [row[1] for row in info]
    primary = [row for row in sorted(info, key=lambda row: row[5]) if row[5] > 0]
    keys = [row[1] for row in primary]
    (without_rowid,) = conn.execute(
        "SELECT wr FROM pragma_table_list WHERE schema = 'main' AND name = ?",
        (table,)).fetchone()
    # Only a single key column of the declared type INTEGER is the rowid itself.
    alias = len(primary) == 1 and primary[0][2].upper() == "INTEGER"
    separate = not without_rowid and not alias
    if separate and any(c.lower() in ("rowid", "oid", "_rowid_") for c in columns):
        raise ExportError("table %s has a column that hides its rowid" % table)
    return columns, keys, separate


def rows_text(conn, table):
    """Return the JSON lines of the rows of `table`, and the number of rows."""
    columns, keys, separate = layout(conn, table)
    names = ["rowid"] * separate + columns
    select = ["rowid"] * separate + [quote(c) for c in columns]
    order = ", ".join(quote(k) for k in keys) if keys else "rowid"
    lines = []
    for values in conn.execute("SELECT %s FROM %s ORDER BY %s"
                               % (", ".join(select), quote(table), order)):
        for name, value in zip(names, values):
            if isinstance(value, bytes):
                raise ExportError("table %s, column %s holds a BLOB; the export keeps text "
                                  "and numbers alone" % (table, name))
        lines.append(json.dumps(dict(zip(names, values)), ensure_ascii=False,
                                separators=(",", ":")) + "\n")
    return "".join(lines), len(lines)


def write_file(path, text):
    """Write `text` to `path` through a temporary file, so a reader never sees half."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


def export(db_path, out):
    """Export the database at `db_path` into the directory `out`.

    Return the schema version and the number of rows of each table. A file of a table
    that the database no longer holds is removed.
    """
    conn = snapshot(db_path)
    try:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        names = table_names(conn)
        rows_dir = os.path.join(out, ROWS_DIR)
        os.makedirs(rows_dir, exist_ok=True)
        write_file(os.path.join(out, SCHEMA_FILE), statements(conn, ("table",)))
        counts = {}
        for name in names:
            text, counts[name] = rows_text(conn, name)
            write_file(os.path.join(rows_dir, name + ".jsonl"), text)
        write_file(os.path.join(out, AFTER_FILE),
                   statements(conn, ("index", "view", "trigger"))
                   + "PRAGMA user_version = %d;\n" % version)
    finally:
        conn.close()
    for entry in os.listdir(rows_dir):
        if entry.endswith(".jsonl") and entry[:-len(".jsonl")] not in counts:
            os.remove(os.path.join(rows_dir, entry))
    return version, counts


def read_file(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def load_rows(conn, table, path):
    """Insert the JSON lines of `path` into `table`. Return the number of rows."""
    with open(path, encoding="utf-8", newline="\n") as fh:
        rows = [json.loads(line) for line in fh]
    if rows:
        names = list(rows[0])
        for row in rows:
            if list(row) != names:
                raise ExportError("%s: a row with other keys than the first row" % path)
        conn.executemany("INSERT INTO %s (%s) VALUES (%s)" % (
            quote(table), ", ".join(quote(n) for n in names), ", ".join("?" * len(names))),
            [tuple(row.values()) for row in rows])
    return len(rows)


def restore(source, db_path):
    """Build the new database `db_path` from the export directory `source`.

    Return the schema version and the number of rows of each table. The restore never
    replaces a file: `db_path` must not exist.
    """
    if os.path.exists(db_path):
        raise ExportError("%s exists already; the restore writes a new file alone" % db_path)
    schema = read_file(os.path.join(source, SCHEMA_FILE))
    after = read_file(os.path.join(source, AFTER_FILE))
    rows_dir = os.path.join(source, ROWS_DIR)
    work = db_path + ".restoring"
    if os.path.exists(work):
        os.remove(work)
    conn = sqlite3.connect(work)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.executescript(schema)
        names = table_names(conn)
        files = {e[:-len(".jsonl")] for e in os.listdir(rows_dir) if e.endswith(".jsonl")}
        if files != set(names):
            raise ExportError("the files of %s do not match the tables of %s: %s"
                              % (rows_dir, SCHEMA_FILE, ", ".join(sorted(files ^ set(names)))))
        counts = {}
        with conn:
            for name in names:
                counts[name] = load_rows(conn, name, os.path.join(rows_dir, name + ".jsonl"))
        broken = conn.execute("PRAGMA foreign_key_check").fetchall()
        if broken:
            raise ExportError("%d rows break a foreign key, the first: %r"
                              % (len(broken), broken[0]))
        conn.executescript(after)
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        conn.close()
    except BaseException:
        conn.close()
        if os.path.exists(work):
            os.remove(work)
        raise
    os.replace(work, db_path)
    return version, counts


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Export the lab database to text files for git, or restore it.")
    commands = parser.add_subparsers(dest="command", required=True)
    one = commands.add_parser("export", help="write the text files")
    one.add_argument("--db", default=DEFAULT_DB, help="the database (default: %(default)s)")
    one.add_argument("--out", default=DEFAULT_OUT,
                     help="the export directory (default: %(default)s)")
    two = commands.add_parser("restore", help="build a new database from the text files")
    two.add_argument("--from", dest="source", default=DEFAULT_OUT,
                     help="the export directory (default: %(default)s)")
    two.add_argument("--db", required=True, help="the new database file; it must not exist")
    args = parser.parse_args(argv)

    try:
        if args.command == "export":
            version, counts = export(args.db, args.out)
            target = args.out
        else:
            version, counts = restore(args.source, args.db)
            target = args.db
    except (ExportError, OSError, sqlite3.Error, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("%s: %s (schema %d, %d tables, %d rows)"
          % (args.command, target, version, len(counts), sum(counts.values())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
