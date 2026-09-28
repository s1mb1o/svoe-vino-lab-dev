"""Import a Strapi CSV of the catalogue into the table `wine_catalog`.

Usage:
    python3 pipeline/import_catalog.py --db data/catalog/catalog.sqlite3 \\
        ../../svoe-wino-hackaton/dataset/official-2026-09-17/strapi_output0709.csv

The import handles an added wine and a removed wine. It does not handle a changed
wine: a changed field stops the import. Read `docs/plans/07_sqlite-lab-database.md`.

Rules of the CSV:
- The CSV MUST hold exactly the nine columns of `COLUMNS`. The column order is free.
- Each value loses its outer white space, as in `catalog.jsonl`.
- An empty `Сорт винограда` becomes NULL. Another empty value stops the import.
- Rows that are equal after the trim are one wine. Two different rows with the same
  slug stop the import.

Rules of the import:
- The database MUST exist. `pipeline/labdb.py` creates it.
- A wine of the CSV that the database does not hold is added as `Active`.
- A wine of the database that the CSV does not hold becomes `Removed`, with
  `removed_by` = `import`. This applies to an `Active` wine and to a `Disabled` wine.
- A wine that the import removed becomes `Active` when the CSV holds it again.
- A wine that a person removed stays `Removed`, also when the CSV holds it. The
  import never changes `removed_by` = `person`.
- A `Disabled` wine that the CSV holds stays `Disabled`.
- A wine that a person added has a slug that starts with `__`
  (`manual_wines.is_manual`). The import never removes it. A CSV slug with this prefix
  stops the import. Read `docs/plans/20_add-wine.md`.
- A wine of the CSV with a field that differs from the database stops the import. The
  error names each changed field. This applies to a `Removed` wine too.
- The import writes all changes in one transaction, or no change.
"""
import argparse
import csv
import hashlib
import io
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labdb  # noqa: E402
import manual_wines  # noqa: E402

# Table column, CSV column. The order is the order of the table.
COLUMNS = (
    ("wine_slug", "Slug"),
    ("name", "Название вина"),
    ("producer", "Винодельня"),
    ("category", "Категория"),
    ("color", "Цвет"),
    ("region", "Регион"),
    ("grapes", "Сорт винограда"),
    ("description", "Описание"),
    ("csv_photo_name", "Название фото"),
)
FIELDS = tuple(column for column, _ in COLUMNS)
# The columns that MAY be empty. An empty value becomes NULL.
NULLABLE = frozenset({"grapes"})
# The states of a wine. The import sets `Active` and `Removed` alone.
STATES = ("Active", "Disabled", "Removed")
# The number of problem rows that an error message names.
SHOWN = 10
# The length of a field value in an error message.
VALUE_CHARS = 60


class CatalogError(Exception):
    """The CSV or the database does not allow the import."""


class Catalog:
    """The parsed CSV: the wines by slug and the counts of the report."""

    def __init__(self):
        self.wines = {}          # slug -> tuple of values in the order of COLUMNS
        self.rows = 0            # data rows in the file
        self.duplicates = 0      # rows equal to an earlier row after the trim
        self.trimmed = 0         # values of the kept wines that lost white space
        self.empty_grapes = 0    # kept wines with NULL grapes


class Changes:
    """The changes that one import makes, in CSV order or in table order."""

    def __init__(self, added, restored, removed, kept, unchanged):
        self.added = added          # rows of new wines
        self.restored = restored    # slugs: Removed by the import -> Active
        self.removed = removed      # slugs: Active or Disabled -> Removed by the import
        self.kept = kept            # slugs of the CSV that a person removed; no change
        self.unchanged = unchanged  # count of the other CSV wines with no change

    def empty(self):
        return not (self.added or self.restored or self.removed)


def parse_catalog(data):
    """Parse the CSV bytes. Return a `Catalog`, or raise `CatalogError`."""
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    expected = [header for _, header in COLUMNS]
    found = reader.fieldnames or []
    if sorted(found) != sorted(expected):
        missing = [h for h in expected if h not in found]
        unknown = [h for h in found if h not in expected]
        raise CatalogError("the CSV columns do not match; missing: %s; unknown: %s"
                           % (missing or "none", unknown or "none"))

    catalog = Catalog()
    empty = []
    conflicts = {}
    trimmed = {}
    for raw in reader:
        catalog.rows += 1
        values = []
        changed = 0
        for column, header in COLUMNS:
            value = raw[header] or ""
            clean = value.strip()
            if clean != value:
                changed += 1
            if not clean:
                if column not in NULLABLE:
                    empty.append("line %d: %s" % (reader.line_num, header))
                clean = None
            values.append(clean)
        row = tuple(values)
        slug = row[0]
        if slug is None:
            continue
        kept = catalog.wines.get(slug)
        if kept is None:
            catalog.wines[slug] = row
            trimmed[slug] = changed
        elif kept == row:
            catalog.duplicates += 1
        else:
            conflicts.setdefault(slug, reader.line_num)

    problems = []
    if empty:
        problems.append("%d empty required values: %s"
                        % (len(empty), "; ".join(empty[:SHOWN])))
    if conflicts:
        shown = ["%s (line %d)" % item for item in list(conflicts.items())[:SHOWN]]
        problems.append("%d slugs have different rows: %s"
                        % (len(conflicts), "; ".join(shown)))
    if problems:
        raise CatalogError(". ".join(problems))
    if not catalog.wines:
        raise CatalogError("the CSV holds no wine")

    grapes = FIELDS.index("grapes")
    catalog.trimmed = sum(trimmed.values())
    catalog.empty_grapes = sum(1 for row in catalog.wines.values() if row[grapes] is None)
    return catalog


def _short(value):
    text = "NULL" if value is None else repr(value)
    return text if len(text) <= VALUE_CHARS else text[:VALUE_CHARS - 1] + "…"


def plan_changes(conn, catalog):
    """Compare the CSV with the database. Return `Changes`, or raise `CatalogError`."""
    manual = [slug for slug in catalog.wines if manual_wines.is_manual(slug)]
    if manual:
        raise CatalogError(
            "%d slugs of the CSV start with %s, the prefix of a wine that a person "
            "added: %s" % (len(manual), manual_wines.MANUAL_PREFIX, _names(manual)))
    stored = {row[0]: row for row in conn.execute(
        "SELECT %s, state, removed_by FROM wine_catalog ORDER BY rowid"
        % ", ".join(FIELDS))}
    state, removed_by = len(FIELDS), len(FIELDS) + 1
    changed = []
    for slug, values in catalog.wines.items():
        old = stored.get(slug)
        if old is None:
            continue
        fields = ["%s %s -> %s" % (FIELDS[i], _short(old[i]), _short(values[i]))
                  for i in range(1, len(FIELDS)) if old[i] != values[i]]
        if fields:
            changed.append("%s (%s): %s" % (slug, old[state], "; ".join(fields)))
    if changed:
        raise CatalogError(
            "%d wines of the CSV differ from the database, and the import does not "
            "change a wine: %s" % (len(changed), " | ".join(changed[:SHOWN])))

    added = [values for slug, values in catalog.wines.items() if slug not in stored]
    back = [slug for slug in catalog.wines
            if slug in stored and stored[slug][state] == "Removed"]
    restored = [slug for slug in back if stored[slug][removed_by] == "import"]
    kept = [slug for slug in back if stored[slug][removed_by] == "person"]
    removed = [slug for slug, row in stored.items()
               if slug not in catalog.wines and row[state] != "Removed"
               and not manual_wines.is_manual(slug)]
    unchanged = len(catalog.wines) - len(added) - len(back)
    return Changes(added, restored, removed, kept, unchanged)


def import_catalog(db_path, csv_path):
    """Import the CSV into the database. Return (catalog, digest, changes, states)."""
    with open(csv_path, "rb") as fh:
        data = fh.read()
    digest = hashlib.sha256(data).hexdigest()
    catalog = parse_catalog(data)

    conn = labdb.connect(db_path)
    conn.isolation_level = None
    try:
        # The write lock is taken before the read, so no other writer can change the
        # rows between the comparison and the write.
        conn.execute("BEGIN IMMEDIATE")
        try:
            changes = plan_changes(conn, catalog)
            conn.executemany(
                "INSERT INTO wine_catalog (%s, state) VALUES (%s, 'Active')"
                % (", ".join(FIELDS), ", ".join("?" for _ in FIELDS)), changes.added)
            conn.executemany("UPDATE wine_catalog SET state = 'Active', removed_by = NULL "
                             "WHERE wine_slug = ?", [(s,) for s in changes.restored])
            conn.executemany("UPDATE wine_catalog SET state = 'Removed', "
                             "removed_by = 'import' WHERE wine_slug = ?",
                             [(s,) for s in changes.removed])
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        states = dict(conn.execute(
            "SELECT state, count(*) FROM wine_catalog GROUP BY state"))
    finally:
        conn.close()
    return catalog, digest, changes, {state: states.get(state, 0) for state in STATES}


def _names(slugs):
    shown = ", ".join(slugs[:SHOWN])
    return shown + (", …" if len(slugs) > SHOWN else "")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Import a Strapi CSV of the catalogue into wine_catalog. The "
                    "import adds and removes wines. A changed wine stops it.")
    parser.add_argument("csv", help="path of the Strapi CSV, for example "
                        "official-2026-09-17/strapi_output0709.csv")
    parser.add_argument("--db", required=True, help="path of the lab database")
    args = parser.parse_args(argv)

    try:
        catalog, digest, changes, states = import_catalog(args.db, args.csv)
    except (CatalogError, labdb.SchemaError, sqlite3.Error, OSError,
            UnicodeDecodeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("source: %s" % os.path.abspath(args.csv))
    print("sha256: %s" % digest)
    print("rows read: %d" % catalog.rows)
    print("duplicate rows: %d" % catalog.duplicates)
    print("wines in the CSV: %d" % len(catalog.wines))
    print("values trimmed: %d" % catalog.trimmed)
    print("empty grapes: %d" % catalog.empty_grapes)
    print("added: %d%s" % (len(changes.added), ": " + _names(
        [row[0] for row in changes.added]) if changes.added else ""))
    print("restored: %d%s" % (len(changes.restored), ": " + _names(changes.restored)
                              if changes.restored else ""))
    print("removed: %d%s" % (len(changes.removed), ": " + _names(changes.removed)
                             if changes.removed else ""))
    print("kept removed by a person: %d%s" % (len(changes.kept), ": " + _names(changes.kept)
                                              if changes.kept else ""))
    print("unchanged: %d" % changes.unchanged)
    print("database: %s" % args.db)
    print("states: %s" % ", ".join("%s %d" % item for item in states.items()))
    print("result: %s" % ("no change" if changes.empty() else "imported"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
