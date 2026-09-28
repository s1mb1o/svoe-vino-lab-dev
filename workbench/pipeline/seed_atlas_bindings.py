"""Seed the table `wine_atlas_binding` from the two Atlas binding files.

Usage:
    D=../../svoe-wino-hackaton/dataset/derived/official-2026-09-17
    python3 pipeline/seed_atlas_bindings.py --db data/lab.sqlite3 \\
        --matches $D/atlas-matches.jsonl --manual $D/atlas-bindings.manual.jsonl

Each line of a file is one JSON object with `wine_slug` and `product_uuid`. The rows of
`--matches` get the source `automatic`. The rows of `--manual` get the source `manual`.
Both options are optional, but one of them MUST be given. Read
`docs/plans/15_atlas-binding.md`.

Rules:
- The seed checks every row before the first write. A bad UUID or a line that is not an
  object stops the seed. The seed then writes nothing.
- A file MAY give one slug 2 or more UUIDs (plan 54). A pair of slug and UUID in both
  files gets the source `manual`.
- A slug that is not in `wine_catalog` prints `no wine: <slug>`. The seed skips it.
- The seed adds the missing rows in one transaction. It never changes or removes a row.
  A pair of slug and UUID that the table holds, of either source, is not added.
- The seed refuses a table `wine_atlas_binding` that already holds rows, because a
  second run adds back the values that a person removed on the page. `--force` adds the
  missing rows anyway. The owner chose this on 2026-09-25.
"""
import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_bindings  # noqa: E402
import labdb  # noqa: E402


class SeedError(Exception):
    """A binding file does not allow the seed."""


def read_bindings(path, source):
    """Return the checked rows of one file as a list of (slug, source, UUID).

    The list keeps the file order and holds each pair of slug and UUID one time.
    """
    rows = {}
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SeedError("%s line %d: not JSON: %s" % (path, number, exc)) from exc
            if not isinstance(record, dict):
                raise SeedError("%s line %d MUST be an object" % (path, number))
            slug = record.get("wine_slug")
            if not isinstance(slug, str) or not slug.strip():
                raise SeedError("%s line %d MUST name `wine_slug`" % (path, number))
            slug = slug.strip()
            try:
                product = atlas_bindings.clean_uuid(record.get("product_uuid"))
            except atlas_bindings.BindingError as exc:
                raise SeedError("%s line %d (%s): %s" % (path, number, slug, exc)) from exc
            rows[(slug, product)] = None
    return [(slug, source, product) for slug, product in rows]


def seed_bindings(db_path, matches_path=None, manual_path=None, log=print, force=False):
    """Add the missing rows of the files to `wine_atlas_binding`.

    A table that holds rows raises `SeedError`, unless `force`.

    Return the counts by source of the rows of the files, the counts by source of the
    added rows, and the slugs that are not in `wine_catalog`.
    """
    rows = []
    for path, source in ((matches_path, "automatic"), (manual_path, "manual")):
        if path:
            rows += read_bindings(path, source)
    # A pair in both files gets the source `manual`: the later row wins.
    rows = list({(slug, product): (slug, source, product)
                 for slug, source, product in rows}.values())
    conn = labdb.connect(db_path)
    try:
        held = conn.execute("SELECT count(*) FROM wine_atlas_binding").fetchone()[0]
        if held and not force:
            raise SeedError("wine_atlas_binding already holds %d rows; a second run adds "
                            "back the values that a person removed on the page; give "
                            "--force to add the missing rows anyway" % held)
        wines = {row[0] for row in conn.execute("SELECT wine_slug FROM wine_catalog")}
        stored = set(conn.execute("SELECT wine_slug, product_uuid FROM wine_atlas_binding"))
        missing, added = [], []
        for slug, source, product in rows:
            if slug not in wines:
                if slug not in missing:
                    missing.append(slug)
                    log("no wine: %s" % slug)
            elif (slug, product) not in stored:
                added.append((slug, source, product))
        with conn:
            conn.executemany("INSERT INTO wine_atlas_binding (wine_slug, source, product_uuid) "
                             "VALUES (?, ?, ?)", added)
    finally:
        conn.close()

    def by_source(items):
        return {source: sum(1 for row in items if row[1] == source)
                for source in atlas_bindings.SOURCES}

    return by_source(rows), by_source(added), missing


def _counts(counts):
    return ", ".join("%s %d" % item for item in counts.items())


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Seed the Atlas Core product bindings of wine_atlas_binding from the "
                    "automatic match file and the manual binding file. The seed adds rows "
                    "alone.")
    parser.add_argument("--db", required=True, help="path of the lab database")
    parser.add_argument("--matches", help="atlas-matches.jsonl of match_atlas.py")
    parser.add_argument("--manual", help="atlas-bindings.manual.jsonl")
    parser.add_argument("--force", action="store_true",
                        help="run also when wine_atlas_binding already holds rows")
    args = parser.parse_args(argv)
    if not args.matches and not args.manual:
        parser.error("give --matches, --manual, or both")

    try:
        read, added, missing = seed_bindings(args.db, args.matches, args.manual,
                                             force=args.force)
    except (SeedError, labdb.SchemaError, sqlite3.Error, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    for name, path in (("matches", args.matches), ("manual", args.manual)):
        if path:
            print("%s: %s" % (name, os.path.abspath(path)))
    print("rows: %s" % _counts(read))
    print("slugs with no wine: %d" % len(missing))
    print("added: %s" % _counts(added))
    print("database: %s" % args.db)
    print("result: %s" % ("seeded" if any(added.values()) else "no change"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
