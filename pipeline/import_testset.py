"""Import one test set of `dataset/<set>/` into the lab database, read-only.

Usage:
    python3 pipeline/import_testset.py --db data/lab.sqlite3 --set my dataset/my

The labels stay in the JSON files of the set, in git. The database holds a copy, and
each import makes the rows of the set equal to the files again. The owner chose per-set
labels on 2026-09-25. Read `docs/plans/12_testsets-benchmark.md`.

Rules of the set directory:
- A photo is a file `photo/<place>/<file>` with an extension of `IMAGE_EXT`. A hidden
  file is skipped. A file directly in `photo/` has no place; it is left out and counted.
- `place` is a wine slug, or `__null__` for a photo that matches no card. A place that
  `wine_catalog` does not hold gets a console message; its photos are imported.
- The label of a photo is the field `label` of `labels[<place>][<file>]` in
  `review-labels.json`. A photo with no entry, or with an entry with no label, gets NULL.
  `marked_delete` is the field `delete`. Another label value stops the import.
- A label entry whose file is not there is left out and counted.
- `excluded-slugs.json` holds the excluded slugs, and `variant-groups.json` the variant
  groups. A missing file gives none. `review-labels.json` MUST be there.

Rules of the store:
- Each photo file is stored in the image store with `pipeline/imagestore.py`. A file
  that the table `image` holds already is not stored again. The pixel size comes from the
  header; a file whose size Pillow cannot read gets NULL and a console message.
- The files are stored first. Then the rows of the set are deleted and written again in
  one transaction.
- The import never writes to the set directory.
"""
import argparse
import collections
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.join(os.path.dirname(HERE), "scripts"))
import imagestore  # noqa: E402
import labdb  # noqa: E402
from match_scoring import NULL_SLUG  # noqa: E402

# The extensions of a photo, as `scripts/match_run.py` reads a photo directory.
IMAGE_EXT = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"})
# The label values of `review-labels.json`. NULL means no label.
LABELS = frozenset({"positive", "negative", "unusable", "variant"})
SET_NAME_RE = re.compile(r"^[0-9a-z_-]+$")
# The number of problem names that an error message shows.
SHOWN = 10


class TestsetError(Exception):
    """The set directory or the database does not allow the import."""


class Report:
    """The counts of one import."""

    def __init__(self):
        self.photos = 0                        # photo files with a place
        self.labels = collections.Counter()    # photos by label; None is no label
        self.loose = 0                         # files directly in photo/
        self.no_file = 0                       # label entries whose file is not there
        self.unknown_places = []               # places that wine_catalog does not hold
        self.excluded = 0                      # excluded slugs
        self.variant_slugs = 0                 # slugs in a variant group
        self.written = 0                       # files copied to the store
        self.present = 0                       # files that the store held already
        self.unsized = 0                       # new files with no pixel size


def load_json(path, required=False):
    """Return the content of a JSON file, or None when it is not there."""
    if not os.path.exists(path):
        if required:
            raise TestsetError("no file %s" % path)
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        raise TestsetError("cannot read %s: %s" % (path, exc))


def scan_photos(photo_dir):
    """Return [(place, file name, path)] in name order, and the count of loose files."""
    photos, loose = [], 0
    for place in sorted(os.listdir(photo_dir)):
        path = os.path.join(photo_dir, place)
        if place.startswith("."):
            continue
        if not os.path.isdir(path):
            loose += 1
            continue
        for name in sorted(os.listdir(path)):
            file_path = os.path.join(path, name)
            if (name.startswith(".") or not os.path.isfile(file_path)
                    or os.path.splitext(name)[1].lower() not in IMAGE_EXT):
                continue
            photos.append((place, name, file_path))
    return photos, loose


def import_testset(db_path, set_name, set_dir, log=print, schema_dir=labdb.SCHEMA_DIR):
    """Import the set directory as the set `set_name`. Return a `Report`."""
    if not SET_NAME_RE.match(set_name or ""):
        raise TestsetError("the set name %r MUST hold 0-9, a-z, '_', and '-' alone" % set_name)
    set_dir = os.path.abspath(set_dir)
    photo_dir = os.path.join(set_dir, "photo")
    if not os.path.isdir(photo_dir):
        raise TestsetError("no photo directory at %s" % photo_dir)
    labels = (load_json(os.path.join(set_dir, "review-labels.json"), required=True)
              or {}).get("labels") or {}
    excluded = (load_json(os.path.join(set_dir, "excluded-slugs.json")) or {}).get("excluded") or {}
    groups = (load_json(os.path.join(set_dir, "variant-groups.json")) or {}).get("groups") or []

    report = Report()
    photos, report.loose = scan_photos(photo_dir)
    present = {(place, name) for place, name, _ in photos}
    report.no_file = sum(1 for place, files in labels.items() for name in files
                         if (place, name) not in present)
    bad = sorted({str((entry or {}).get("label")) for files in labels.values()
                  for entry in files.values()
                  if (entry or {}).get("label") is not None
                  and (entry or {}).get("label") not in LABELS})
    if bad:
        raise TestsetError("unknown label values: %s" % ", ".join(bad[:SHOWN]))

    conn = labdb.connect(db_path, directory=schema_dir)
    conn.isolation_level = None
    try:
        wines = {row[0] for row in conn.execute("SELECT wine_slug FROM wine_catalog")}
        known = {digest for (digest,) in conn.execute("SELECT sha256 FROM image")}
        new_images = {}   # sha256 -> the row of `image`
        rows = []
        for place, name, path in photos:
            digest = imagestore.sha256_of(path)
            extension = os.path.splitext(name)[1][1:].lower()
            if digest in known or digest in new_images:
                report.present += 1
            else:
                target = imagestore.path_of(db_path, digest, extension)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                if imagestore.store_file(path, target, digest):
                    report.written += 1
                else:
                    report.present += 1
                try:
                    width, height = imagestore.pixel_size(target)
                except OSError as exc:
                    width = height = None
                    report.unsized += 1
                    log("no pixel size: %s/%s: %s" % (place, name, exc))
                new_images[digest] = (digest, extension, width, height)
            entry = (labels.get(place) or {}).get(name) or {}
            label = entry.get("label")
            report.labels[label] += 1
            rows.append((set_name, place, name, digest, label, 1 if entry.get("delete") else 0))
        report.photos = len(rows)
        report.unknown_places = sorted({place for place, _, _ in photos
                                        if place != NULL_SLUG and place not in wines})
        for place in report.unknown_places:
            log("unknown place: %s: wine_catalog holds no wine with this slug" % place)
        excluded_rows = [(set_name, slug, (rec or {}).get("reason"), (rec or {}).get("ts"))
                         for slug, rec in sorted(excluded.items())]
        # A slug in two groups keeps its last group, as `load_groups` of match_run.py does.
        variant = {}
        for number, group in enumerate(groups):
            for slug in (group or {}).get("slugs") or []:
                if isinstance(slug, str):
                    variant[slug] = number
        report.excluded, report.variant_slugs = len(excluded_rows), len(variant)

        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.executemany("INSERT INTO image (sha256, extension, width, height) "
                             "VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING",
                             new_images.values())
            for table in ("test_photo", "test_excluded", "test_variant"):
                conn.execute("DELETE FROM %s WHERE set_name = ?" % table, (set_name,))
            conn.execute("INSERT INTO test_set (set_name, source_dir) VALUES (?, ?) "
                         "ON CONFLICT (set_name) DO UPDATE SET source_dir = excluded.source_dir",
                         (set_name, set_dir))
            conn.executemany("INSERT INTO test_photo (set_name, place, file_name, sha256, "
                             "label, marked_delete) VALUES (?, ?, ?, ?, ?, ?)", rows)
            conn.executemany("INSERT INTO test_excluded (set_name, wine_slug, reason, ts) "
                             "VALUES (?, ?, ?, ?)", excluded_rows)
            conn.executemany("INSERT INTO test_variant (set_name, wine_slug, group_no) "
                             "VALUES (?, ?, ?)",
                             [(set_name, slug, number) for slug, number in sorted(variant.items())])
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Import one test set of dataset/<set>/ into the lab database, "
                    "read-only. The JSON files stay the source of the labels.")
    parser.add_argument("set_dir", help="the directory of the set, for example dataset/my")
    parser.add_argument("--db", required=True, help="path of the lab database")
    parser.add_argument("--set", required=True, dest="set_name",
                        help="the name of the set in the database, for example my")
    args = parser.parse_args(argv)

    def log(message):
        print(message, flush=True)

    try:
        report = import_testset(args.db, args.set_name, args.set_dir, log)
    except (TestsetError, imagestore.StoreError, labdb.SchemaError, sqlite3.Error,
            OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    labels = ", ".join("%s %d" % (label or "no label", n)
                       for label, n in sorted(report.labels.items(), key=lambda x: str(x[0])))
    print("set: %s from %s" % (args.set_name, os.path.abspath(args.set_dir)))
    print("photos: %d (%s)" % (report.photos, labels))
    print("files directly in photo/, left out: %d" % report.loose)
    print("label entries with no file, left out: %d" % report.no_file)
    print("places that wine_catalog does not hold: %d" % len(report.unknown_places))
    print("excluded slugs: %d" % report.excluded)
    print("slugs in a variant group: %d" % report.variant_slugs)
    print("files written: %d" % report.written)
    print("files in the store already: %d" % report.present)
    print("database: %s" % args.db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
