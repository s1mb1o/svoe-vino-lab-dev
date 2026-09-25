"""Seed the table `wine_code` from the structured code map of the matcher.

Usage:
    python3 pipeline/seed_codes.py --db data/lab.sqlite3 \\
        ../svoe-vino-matcher/dataset/code-map.json

The code map holds the list `wines`. Each record gives `wine_slug`, `barcode`, and
`qr_code`. `barcode` and `qr_code` are a string, a list of strings, or `null`.
Read `docs/plans/11_wine-codes.md`.

Rules:
- A `barcode` value MUST be a GTIN. It is stored in its GTIN-14 form. The lab keeps
  GTINs alone, so a value that is not a GTIN is a bad value. A `qr_code` value is a
  QR URL.
- The seed checks every value before the first write. A bad value, for example a wrong
  check digit or a letter in a `barcode` value, stops the seed. The seed then writes nothing
  and prints the record number, the field, and the value.
- A slug that is not in `wine_catalog` prints `no wine: <slug>`. The seed skips it.
- The seed adds the missing rows in one transaction. It never removes or changes a row.
- The seed refuses a table `wine_code` that already holds rows, because a second run adds
  back the values that a person removed on the page. `--force` adds the missing rows
  anyway. The owner chose this on 2026-09-25.
- The seed does not copy other fields of a record, for example `source_note`.
"""
import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codes  # noqa: E402
import labdb  # noqa: E402


class SeedError(Exception):
    """The code map does not allow the seed."""


def _values(record, field, number):
    value = record.get(field)
    values = value if isinstance(value, list) else ([] if value is None else [value])
    for item in values:
        if not isinstance(item, str):
            raise SeedError("record %d: `%s` MUST be a string, a list of strings, or null"
                            % (number, field))
    return values


def read_code_map(path):
    """Return the checked rows of the code map as a list of (slug, kind, value).

    The list keeps the file order and holds each row one time.
    """
    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)
    wines = document.get("wines") if isinstance(document, dict) else None
    if not isinstance(wines, list):
        raise SeedError("the code map MUST hold a `wines` list")
    rows = []
    for number, record in enumerate(wines, 1):
        if not isinstance(record, dict):
            raise SeedError("record %d MUST be an object" % number)
        slug = record.get("wine_slug")
        if not isinstance(slug, str) or not slug.strip():
            raise SeedError("record %d MUST name `wine_slug`" % number)
        slug = slug.strip()
        found = []
        for field, kind, clean in (("barcode", "gtin", codes.clean_gtin),
                                   ("qr_code", "qr_url", codes.clean_qr_url)):
            for value in _values(record, field, number):
                try:
                    found.append((kind, clean(value)))
                except codes.CodeError as exc:
                    raise SeedError("record %d (%s): `%s` %r: %s"
                                    % (number, slug, field, value, exc)) from exc
        for kind, value in found:
            if (slug, kind, value) not in rows:
                rows.append((slug, kind, value))
    return rows


def seed_codes(db_path, code_map_path, log=print, force=False):
    """Add the missing rows of the code map to `wine_code`.

    A table that holds rows raises `SeedError`, unless `force`.

    Return the counts by kind of the rows of the code map, the counts by kind of the
    added rows, and the slugs that are not in `wine_catalog`.
    """
    rows = read_code_map(code_map_path)
    conn = labdb.connect(db_path)
    try:
        held = conn.execute("SELECT count(*) FROM wine_code").fetchone()[0]
        if held and not force:
            raise SeedError("wine_code already holds %d rows; a second run adds back the "
                            "values that a person removed on the page; give --force to "
                            "add the missing rows anyway" % held)
        wines = {row[0] for row in conn.execute("SELECT wine_slug FROM wine_catalog")}
        stored = set(conn.execute("SELECT wine_slug, kind, value FROM wine_code"))
        missing = []
        for slug, _kind, _value in rows:
            if slug not in wines and slug not in missing:
                missing.append(slug)
                log("no wine: %s" % slug)
        added = [row for row in rows if row[0] in wines and row not in stored]
        with conn:
            conn.executemany("INSERT INTO wine_code (wine_slug, kind, value) VALUES (?, ?, ?)",
                             added)
    finally:
        conn.close()
    read = {kind: sum(1 for row in rows if row[1] == kind) for kind in codes.KINDS}
    new = {kind: sum(1 for row in added if row[1] == kind) for kind in codes.KINDS}
    return read, new, missing


def _counts(counts):
    return ", ".join("%s %d" % item for item in counts.items())


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Seed the GTINs and the QR URLs of wine_code from the code map of "
                    "the matcher. The seed adds rows alone.")
    parser.add_argument("code_map", help="path of the code map, for example "
                        "../svoe-vino-matcher/dataset/code-map.json")
    parser.add_argument("--db", required=True, help="path of the lab database")
    parser.add_argument("--force", action="store_true",
                        help="run also when wine_code already holds rows")
    args = parser.parse_args(argv)

    try:
        read, added, missing = seed_codes(args.db, args.code_map, force=args.force)
    except (SeedError, labdb.SchemaError, sqlite3.Error, OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("source: %s" % os.path.abspath(args.code_map))
    print("values: %s" % _counts(read))
    print("slugs with no wine: %d" % len(missing))
    print("added: %s" % _counts(added))
    print("database: %s" % args.db)
    print("result: %s" % ("seeded" if any(added.values()) else "no change"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
