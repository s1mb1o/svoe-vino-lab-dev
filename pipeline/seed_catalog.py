"""Seed the table `wine_catalog` from the Strapi CSV of one delivery.

Usage:
    python3 pipeline/seed_catalog.py --db data/catalog-2026-09-17/lab.sqlite3 \\
        ../svoe-wino-hackaton/dataset/official-2026-09-17/strapi_output0709.csv

Rules. Read `docs/plans/07_sqlite-lab-database.md` for the reasons.
- The database MUST exist. `pipeline/labdb.py` creates it.
- The CSV MUST hold exactly the nine columns of `COLUMNS`.
- Each value loses its outer white space, as in `catalog.jsonl`.
- An empty `Сорт винограда` becomes NULL. Another empty value stops the seed.
- Rows that are equal after the trim are one wine. Two different rows with the same
  slug stop the seed.
- One database holds one delivery. A second seed from the same file changes nothing.
  A seed from another file stops.
- The seed writes all rows in one transaction, or no row.
"""
import argparse
import csv
import hashlib
import io
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labdb  # noqa: E402

# Table column, CSV column. The order is the order of the table.
COLUMNS = (
    ("slug", "Slug"),
    ("name", "Название вина"),
    ("producer", "Винодельня"),
    ("category", "Категория"),
    ("color", "Цвет"),
    ("region", "Регион"),
    ("grapes", "Сорт винограда"),
    ("description", "Описание"),
    ("csv_photo_name", "Название фото"),
)
# The columns that MAY be empty. An empty value becomes NULL.
NULLABLE = frozenset({"grapes"})
# The number of problem rows that an error message names.
SHOWN = 10


class CatalogError(Exception):
    """The CSV or the database does not allow the seed."""


class Catalog:
    """The parsed CSV: the wines by slug and the counts of the report."""

    def __init__(self):
        self.wines = {}          # slug -> tuple of values in the order of COLUMNS
        self.rows = 0            # data rows in the file
        self.duplicates = 0      # rows equal to an earlier row after the trim
        self.trimmed = 0         # values of the stored wines that lost white space
        self.empty_grapes = 0    # stored wines with NULL grapes


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
        stored = catalog.wines.get(slug)
        if stored is None:
            catalog.wines[slug] = row
            trimmed[slug] = changed
        elif stored == row:
            catalog.duplicates += 1
        else:
            conflicts.setdefault(slug, reader.line_num)

    problems = []
    if empty:
        problems.append("%d empty required values: %s" % (len(empty), "; ".join(empty[:SHOWN])))
    if conflicts:
        shown = ["%s (line %d)" % item for item in list(conflicts.items())[:SHOWN]]
        problems.append("%d slugs have different rows: %s" % (len(conflicts), "; ".join(shown)))
    if problems:
        raise CatalogError(". ".join(problems))
    if not catalog.wines:
        raise CatalogError("the CSV holds no wine")

    grapes = [column for column, _ in COLUMNS].index("grapes")
    catalog.trimmed = sum(trimmed.values())
    catalog.empty_grapes = sum(1 for row in catalog.wines.values() if row[grapes] is None)
    return catalog


def seed(db_path, csv_path, now=None):
    """Seed the database from the CSV. Return (catalog, digest, stored).

    `stored` is False when the database already holds this file.
    """
    csv_path = os.path.abspath(csv_path)
    with open(csv_path, "rb") as fh:
        data = fh.read()
    digest = hashlib.sha256(data).hexdigest()
    catalog = parse_catalog(data)

    conn = labdb.connect(db_path)
    try:
        source = conn.execute(
            "SELECT source_path, source_sha256 FROM catalog_source").fetchone()
        if source:
            if source[1] == digest:
                return catalog, digest, False
            raise CatalogError("the database holds another delivery: %s (sha256 %s)"
                               % source)
        count = conn.execute("SELECT count(*) FROM wine_catalog").fetchone()[0]
        if count:
            raise CatalogError("wine_catalog holds %d rows with no catalog_source row"
                               % count)
        columns = ", ".join(column for column, _ in COLUMNS)
        marks = ", ".join("?" for _ in COLUMNS)
        with conn:
            conn.execute(
                "INSERT INTO catalog_source (id, source_path, source_sha256, "
                "source_rows, imported_at) VALUES (1, ?, ?, ?, ?)",
                (csv_path, digest, catalog.rows,
                 now or time.strftime("%Y-%m-%dT%H:%M:%S%z")))
            conn.executemany("INSERT INTO wine_catalog (%s) VALUES (%s)"
                             % (columns, marks), catalog.wines.values())
    finally:
        conn.close()
    return catalog, digest, True


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Seed the table wine_catalog from the Strapi CSV of one delivery.")
    parser.add_argument("csv", help="path of the Strapi CSV, for example "
                        "official-2026-09-17/strapi_output0709.csv")
    parser.add_argument("--db", required=True, help="path of the lab database")
    args = parser.parse_args(argv)

    try:
        catalog, digest, stored = seed(args.db, args.csv)
    except (CatalogError, labdb.SchemaError, sqlite3.Error, OSError,
            UnicodeDecodeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("source: %s" % os.path.abspath(args.csv))
    print("sha256: %s" % digest)
    print("rows read: %d" % catalog.rows)
    print("duplicate rows: %d" % catalog.duplicates)
    print("wines: %d" % len(catalog.wines))
    print("values trimmed: %d" % catalog.trimmed)
    print("empty grapes: %d" % catalog.empty_grapes)
    print("database: %s" % args.db)
    if stored:
        print("result: stored %d wines" % len(catalog.wines))
    else:
        print("result: unchanged; the database already holds this file")
    return 0


if __name__ == "__main__":
    sys.exit(main())
