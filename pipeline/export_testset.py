"""Export one test set of the lab database to the JSON files of a set directory.

Usage:
    python3 pipeline/export_testset.py --db data/lab.sqlite3 --set my --out <directory>

The database is the source of the labels since plan 24. The export writes two files into
`--out`, in the form of `scripts/review_server.py`: `review-labels.json` (version 2:
`version`, `updated`, `counts`, `note`, `wines`, `labels`) and `excluded-slugs.json`
(version 1). A file of the same name in `--out` is replaced; each write is atomic. The
export writes no photo file. Read `docs/plans/24_testset-page.md`.

A label entry comes from the columns of its row of `test_photo` and from `extra` by the
rule of `testsets.py`. A row with no field gives no entry, as the old tool removes an
entry with no field.
"""
import argparse
import json
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import labdb  # noqa: E402
import testsets  # noqa: E402

LABELS_FILE = "review-labels.json"
EXCLUDED_FILE = "excluded-slugs.json"
# The keys of `counts` in `review-labels.json`: the keys of `count_state` of the old tool.
COUNT_KEYS = ("commented", "copied", "deleting", "labelled", "negative", "no_match",
              "no_match_pending", "positive", "proposed", "reassigned", "unusable",
              "variant", "wine_notes")
# The text `note` of a set that the import gave no note. It is the text of the old tool.
LABELS_NOTE = (
    "Manual labels for the photos of svoe-vino-testset/my. "
    "The key of an entry is the slug, then the photo file name. "
    "label 'positive': the photo shows the wine of this slug. "
    "label 'negative': the photo shows a different wine, and the photo stays "
    "in the set as a negative sample of this slug. "
    "label 'unusable': the photo is not usable at all and does not belong in "
    "the set. label 'variant': the photo shows this wine in another bottle, "
    "such as another vintage or another package design. "
    "A photo with no entry is not reviewed yet. "
    "The slug '__null__' is the virtual NULL wine. A photo under that "
    "slug matches NO card of the catalogue. The place is the statement, "
    "so such a photo needs no label; 'positive' confirms it and "
    "'unusable' takes the photo out of the set. "
    "Field 'reassign_to' names the slug that the photo belongs to; "
    "scripts/09_apply_moves.py moves the file. "
    "Field 'copy_to' names a slug that the photo ALSO belongs to; the same "
    "script copies the file and leaves the source photo where it is. "
    "The copy carries no label and one comment that names the source slug. "
    "Field 'comment' holds a free text note of the reviewer about this "
    "photo and this slug. The map 'wines' holds one free text note about a "
    "whole wine, keyed by the slug."
)
EXCLUDED_NOTE = (
    "Excluded slugs of svoe-vino-testset. The key of an entry is the wine "
    "slug. Field 'reason' states why the slug is excluded. Field 'ts' holds "
    "the time of the exclusion. The photos of an excluded slug MUST NOT be "
    "used for benchmarking. A slug that is not in this file is included. "
    "Purpose: some slugs of the catalogue hold an error, most often a wrong "
    "bottle photo. A wrong bottle photo shifts the metrics, because the "
    "reference of the slug does not show the wine. Such a slug is excluded "
    "instead of corrected, so the benchmark stays comparable."
)


class ExportError(Exception):
    """The database or the set does not allow the export."""


def open_database(db_path, schema_dir=labdb.SCHEMA_DIR):
    """Open the database read-only. Its schema version MUST equal the schema files."""
    if not os.path.isfile(db_path):
        raise ExportError("no database at %s" % db_path)
    conn = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    expected = len(labdb.schema_files(schema_dir))
    if version != expected:
        conn.close()
        raise ExportError("the database has schema version %d and this code needs "
                          "version %d; run `python3 pipeline/labdb.py %s`"
                          % (version, expected, db_path))
    return conn


def labels_document(conn, set_name):
    """Return the content of `review-labels.json` of one set."""
    row = conn.execute("SELECT label_note FROM test_set WHERE set_name = ?",
                       (set_name,)).fetchone()
    if row is None:
        raise ExportError("the database holds no test set %r" % set_name)
    labels = {}
    for photo in testsets.photo_rows(conn, set_name):
        entry = testsets.entry_of(photo)
        if entry:
            labels.setdefault(photo["place"], {})[photo["file_name"]] = entry
    wines = {}
    for slug, comment, ts, extra in conn.execute(
            "SELECT wine_slug, comment, ts, extra FROM test_wine_note WHERE set_name = ?",
            (set_name,)):
        note = testsets.note_of(comment, ts, extra)
        if note:
            wines[slug] = note
    counts = testsets.counts(conn, set_name)
    return {"version": 2, "updated": testsets.now_local(),
            "note": row[0] if row[0] is not None else LABELS_NOTE,
            "counts": {key: counts[key] for key in COUNT_KEYS},
            "labels": labels, "wines": wines}


def excluded_document(conn, set_name):
    """Return the content of `excluded-slugs.json` of one set."""
    excluded = {}
    for slug, reason, ts in conn.execute(
            "SELECT wine_slug, reason, ts FROM test_excluded WHERE set_name = ?", (set_name,)):
        excluded[slug] = {key: value for key, value in (("reason", reason), ("ts", ts))
                          if value is not None}
    return {"version": 1, "updated": testsets.now_local(), "note": EXCLUDED_NOTE,
            "count": len(excluded), "excluded": excluded}


def write_json(path, payload):
    """Write `payload` as the old tool does: sorted keys, indent 2, a final line break.
    The write is atomic."""
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(temporary, path)


def export_testset(db_path, set_name, out_dir, schema_dir=labdb.SCHEMA_DIR):
    """Write the two JSON files of one set into `out_dir`. Return (the path of each file,
    the labels document)."""
    with closing(open_database(db_path, schema_dir)) as conn:
        labels = labels_document(conn, set_name)
        excluded = excluded_document(conn, set_name)
    os.makedirs(out_dir, exist_ok=True)
    labels_path = os.path.join(out_dir, LABELS_FILE)
    excluded_path = os.path.join(out_dir, EXCLUDED_FILE)
    write_json(labels_path, labels)
    write_json(excluded_path, excluded)
    return labels_path, excluded_path, labels


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Export one test set of the lab database to review-labels.json and "
                    "excluded-slugs.json.")
    parser.add_argument("--db", required=True, help="path of the lab database")
    parser.add_argument("--set", required=True, dest="set_name", help="the name of the set")
    parser.add_argument("--out", required=True,
                        help="the directory of the two files; a file there is replaced")
    args = parser.parse_args(argv)
    try:
        labels_path, excluded_path, labels = export_testset(args.db, args.set_name, args.out)
    except (ExportError, labdb.SchemaError, sqlite3.Error, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    entries = sum(len(files) for files in labels["labels"].values())
    print("set: %s" % args.set_name)
    print("label entries: %d in %d places" % (entries, len(labels["labels"])))
    print("notes of a whole wine: %d" % len(labels["wines"]))
    print("written: %s" % labels_path)
    print("written: %s" % excluded_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
