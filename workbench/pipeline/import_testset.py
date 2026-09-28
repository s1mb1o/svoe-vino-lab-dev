"""Import one test set of `dataset/<set>/` into the lab database.

Usage:
    python3 pipeline/import_testset.py --db data/catalog/catalog.sqlite3 --set my \
        ../../svoe-vino-testset/dataset/my
    python3 pipeline/import_testset.py --db data/catalog/catalog.sqlite3 --set my --force <dir>

`pipeline/import_testsets.py` imports the three sets of `svoe-vino-testset/dataset/`
with one command.

Each import makes the rows of the set equal to the files of the set directory. The owner
chose per-set labels on 2026-09-25. Read `docs/plans/12_testsets-benchmark.md`. Since
plan 24 the database is the source of the labels: the Testset page writes to the rows,
and `pipeline/export_testset.py` writes the JSON files. So the import refuses a set that
holds a page edit (`test_set.edited_at`), unless `--force`. `--force` replaces the page
edits with the files. Read `docs/plans/24_testset-page.md`.

Rules of the set directory:
- A photo is a file `photo/<place>/<file>` with an extension of `IMAGE_EXT`. A hidden
  file is skipped. A file directly in `photo/` has no place; it is left out and counted.
- `place` is a wine slug, or `__null__` for a photo that matches no card. A place that
  `wine_catalog` does not hold gets a console message; its photos are imported.
- The label entry of a photo is `labels[<place>][<file>]` in `review-labels.json`. Each
  field of the entry goes into a column of `test_photo` by the rule of `testsets.py`,
  and each other field into `extra`, so the export gives the same entry back. A photo
  with no entry gets no field. A label value that is not one of the four labels, and
  not null, stops the import. An entry that is not a JSON object stops it too.
- The field `comments` of an entry goes into `test_photo_comment`, and so does the old
  field `comment` of the old tool (`testsets.entry_comments`, plan 51).
- The field `tags` of an entry is a list of tags of the image of the photo (plan 66). The
  import adds each tag to `image_tag`. The import never removes an image tag, because an
  image tag belongs to no set. A tag that the image has already is not added again, so a
  second import adds no row. A `tags` value that is not a list of valid tags stops the
  import.
- The text `note` of `review-labels.json` goes into `test_set.label_note`.
- The old map `wines` of `review-labels.json` and the old file `excluded-slugs.json` go
  into `wine_comment` by the rules of plan 51. A text that the wine has already is not
  added again, so a second import adds no row. The import never removes a wine comment:
  the wine comments belong to no set. A slug that `wine_catalog` does not hold gets a
  console message, and its text is left out.
- A label entry whose file is not there is left out and counted.
- `variant-groups.json` holds the variant groups. A missing file gives none.
  `review-labels.json` MUST be there.

Rules of the store:
- Each photo file is stored as `images/testset/<sha256>.<extension>` with
  `pipeline/imagestore.py`, and gets a row of `image` with the folder `testset`. A file
  that the table `image` holds already is not stored again, and keeps its folder. The
  pixel size comes from the header; a file whose size Pillow cannot read gets NULL and a
  console message.
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
import comments  # noqa: E402
import image_tags  # noqa: E402
import imagestore  # noqa: E402
import labdb  # noqa: E402
import testsets  # noqa: E402
from match_scoring import NULL_SLUG  # noqa: E402

# The extensions of a photo, as `scripts/match_run.py` reads a photo directory.
IMAGE_EXT = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"})
# The label values of `review-labels.json`. NULL means no label.
LABELS = frozenset({"positive", "negative", "unusable", "variant"})
SET_NAME_RE = re.compile(r"^[0-9a-z_-]+$")
# The folder of the image store for a test photo. Read the schema file of the test sets.
FOLDER = "testset"
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
        self.excluded = 0                      # reasons of excluded-slugs.json
        self.variant_slugs = 0                 # slugs in a variant group
        self.written = 0                       # files copied to the store
        self.present = 0                       # files that the store held already
        self.unsized = 0                       # new files with no pixel size
        self.wine_notes = 0                    # notes of the old map `wines`
        self.photo_comments = 0                # rows of test_photo_comment
        self.wine_comments = 0                 # new rows of wine_comment
        self.wine_comments_present = 0         # texts that the wine had already
        self.wine_comments_left_out = 0        # texts of a slug not in wine_catalog
        self.boxes = 0                         # photos with a box of the main object
        self.image_tags = 0                    # new rows of image_tag
        self.image_tags_present = 0            # tags that the image had already
        self.extra = 0                         # entries with a field in `extra`


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


def photo_path(db_path, sha256, extension):
    """Return the path of a test photo in the image store of the database."""
    return os.path.join(imagestore.folder_of(db_path, FOLDER), "%s.%s" % (sha256, extension))


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


def entry_tags(place, name, entry):
    """Return the normal forms of the field `tags` of one label entry: a list, empty when
    the entry has no such field. A value that is not a list of valid tags raises
    `TestsetError`."""
    if "tags" not in entry:
        return []
    value = entry["tags"]
    if not isinstance(value, list):
        raise TestsetError("the field tags of the entry %s/%s is not a list" % (place, name))
    try:
        return [image_tags.normal(tag) for tag in value]
    except image_tags.TagError as exc:
        raise TestsetError("the field tags of the entry %s/%s: %s" % (place, name, exc))


def check_not_edited(conn, set_name, force):
    """Raise `TestsetError` when the Testset page edited the set and `force` is false."""
    row = conn.execute("SELECT edited_at FROM test_set WHERE set_name = ?",
                       (set_name,)).fetchone()
    if row and row[0] and not force:
        raise TestsetError("the set %s holds edits of the Testset page (the last at %s); "
                           "the database is the source of its labels. Export them with "
                           "`pipeline/export_testset.py`, or add --force to replace them "
                           "with the files" % (set_name, row[0]))


def import_testset(db_path, set_name, set_dir, log=print, schema_dir=labdb.SCHEMA_DIR,
                   force=False):
    """Import the set directory as the set `set_name`. Return a `Report`.

    Raise `TestsetError` for a set with page edits, unless `force`."""
    if not SET_NAME_RE.match(set_name or ""):
        raise TestsetError("the set name %r MUST hold 0-9, a-z, '_', and '-' alone" % set_name)
    set_dir = os.path.abspath(set_dir)
    photo_dir = os.path.join(set_dir, "photo")
    if not os.path.isdir(photo_dir):
        raise TestsetError("no photo directory at %s" % photo_dir)
    document = load_json(os.path.join(set_dir, "review-labels.json"), required=True) or {}
    labels = document.get("labels") or {}
    wines = document.get("wines") or {}
    label_note = document.get("note") if isinstance(document.get("note"), str) else None
    for place, files in labels.items():
        for name, entry in (files or {}).items():
            if entry is not None and not isinstance(entry, dict):
                raise TestsetError("the label entry %s/%s is not a JSON object" % (place, name))
            entry_tags(place, name, entry or {})
    for slug, note in wines.items():
        if not isinstance(note, dict):
            raise TestsetError("the note of the wine %s is not a JSON object" % slug)
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
                  and not ((entry or {}).get("label") in LABELS
                           and isinstance((entry or {}).get("label"), str))})
    if bad:
        raise TestsetError("unknown label values: %s" % ", ".join(bad[:SHOWN]))

    conn = labdb.connect(db_path, directory=schema_dir)
    conn.isolation_level = None
    try:
        check_not_edited(conn, set_name, force)
        catalog = {row[0] for row in conn.execute("SELECT wine_slug FROM wine_catalog")}
        known = {digest for (digest,) in conn.execute("SELECT sha256 FROM image")}
        now = comments.now_utc()
        new_images = {}   # sha256 -> the row of `image`
        rows, comment_rows = [], []
        tag_rows = {}     # (sha256, tag) -> None, in the order of the photos
        for place, name, path in photos:
            digest = imagestore.sha256_of(path)
            extension = os.path.splitext(name)[1][1:].lower()
            if digest in known or digest in new_images:
                report.present += 1
            else:
                target = photo_path(db_path, digest, extension)
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
                new_images[digest] = (digest, FOLDER, extension, width, height)
            entry = (labels.get(place) or {}).get(name) or {}
            entry, notes = testsets.entry_comments(entry, now)
            # `entry_comments` returns a copy, so the pop leaves `labels` as it is.
            for tag in entry_tags(place, name, entry):
                tag_rows[(digest, tag)] = None
            entry.pop("tags", None)
            size = None
            if "box" in entry:
                try:
                    size = testsets.oriented_size(path)
                except OSError as exc:
                    log("no pixel size for the box: %s/%s: %s" % (place, name, exc))
            columns = testsets.entry_columns(entry, size)
            report.labels[columns["label"]] += 1
            report.boxes += columns["box_left"] is not None
            report.extra += columns["extra"] is not None
            rows.append((set_name, place, name, digest)
                        + tuple(columns[c] for c in testsets.ENTRY_COLUMNS))
            comment_rows += [(set_name, place, name) + tuple(note[k] for k in testsets.COMMENT_KEYS)
                             for note in notes]
        report.photos, report.photo_comments = len(rows), len(comment_rows)
        report.unknown_places = sorted({place for place, _, _ in photos
                                        if place != NULL_SLUG and place not in catalog})
        for place in report.unknown_places:
            log("unknown place: %s: wine_catalog holds no wine with this slug" % place)
        # The old wine notes and the old exclusions become wine comments (plan 51).
        wine_notes = [(slug, testsets.wine_note_comment(note, now))
                      for slug, note in sorted(wines.items())]
        reasons = [(slug, testsets.exclusion_comment(rec, now))
                   for slug, rec in sorted(excluded.items())]
        report.wine_notes, report.excluded = len(wines), len(excluded)
        wine_rows = []
        for slug, note in wine_notes + reasons:
            if note is None:
                continue
            if slug not in catalog:
                report.wine_comments_left_out += 1
                log("left out: a wine comment of %s: wine_catalog holds no wine with this "
                    "slug" % slug)
                continue
            wine_rows.append((slug,) + tuple(note[k] for k in testsets.COMMENT_KEYS))
        # A slug in two groups keeps its last group, as `load_groups` of match_run.py does.
        variant = {}
        for number, group in enumerate(groups):
            for slug in (group or {}).get("slugs") or []:
                if isinstance(slug, str):
                    variant[slug] = number
        report.variant_slugs = len(variant)

        conn.execute("BEGIN IMMEDIATE")
        try:
            # A page write MAY come between the first check and the write lock.
            check_not_edited(conn, set_name, force)
            conn.executemany("INSERT INTO image (sha256, folder, extension, width, height) "
                             "VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                             new_images.values())
            for table in ("test_photo_comment", "test_photo", "test_variant"):
                conn.execute("DELETE FROM %s WHERE set_name = ?" % table, (set_name,))
            conn.execute("INSERT INTO test_set (set_name, source_dir, label_note) "
                         "VALUES (?, ?, ?) ON CONFLICT (set_name) DO UPDATE SET "
                         "source_dir = excluded.source_dir, label_note = excluded.label_note, "
                         "edited_at = NULL", (set_name, set_dir, label_note))
            conn.executemany("INSERT INTO test_photo (set_name, place, file_name, sha256, %s) "
                             "VALUES (%s)" % (", ".join(testsets.ENTRY_COLUMNS), ", ".join(
                                 "?" for _ in range(4 + len(testsets.ENTRY_COLUMNS)))), rows)
            conn.executemany("INSERT INTO test_photo_comment (set_name, place, file_name, "
                             "created_at, source, text) VALUES (?, ?, ?, ?, ?, ?)", comment_rows)
            for digest, tag in tag_rows:
                if conn.execute("INSERT INTO image_tag (sha256, tag, created_at) "
                                "VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
                                (digest, tag, now)).rowcount:
                    report.image_tags += 1
                else:
                    report.image_tags_present += 1
            for slug, created_at, source, text in wine_rows:
                if conn.execute("SELECT 1 FROM wine_comment WHERE wine_slug = ? AND text = ?",
                                (slug, text)).fetchone():
                    report.wine_comments_present += 1
                    continue
                comments.add(conn, slug, text, source, created_at)
                report.wine_comments += 1
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


def print_report(report, set_name, set_dir, db_path):
    """Print the counts of one import."""
    labels = ", ".join("%s %d" % (label or "no label", n)
                       for label, n in sorted(report.labels.items(), key=lambda x: str(x[0])))
    print("set: %s from %s" % (set_name, os.path.abspath(set_dir)))
    print("photos: %d (%s)" % (report.photos, labels))
    print("files directly in photo/, left out: %d" % report.loose)
    print("label entries with no file, left out: %d" % report.no_file)
    print("places that wine_catalog does not hold: %d" % len(report.unknown_places))
    print("slugs in a variant group: %d" % report.variant_slugs)
    print("comments of the photos: %d" % report.photo_comments)
    print("image tags: %d new, %d there already" % (report.image_tags,
                                                     report.image_tags_present))
    print("old notes of a whole wine: %d; old exclusions: %d" % (report.wine_notes,
                                                                 report.excluded))
    print("wine comments: %d new, %d there already, %d left out (no wine)"
          % (report.wine_comments, report.wine_comments_present,
             report.wine_comments_left_out))
    print("photos with a box: %d" % report.boxes)
    print("entries with a field in extra: %d" % report.extra)
    print("files written: %d" % report.written)
    print("files in the store already: %d" % report.present)
    print("database: %s" % db_path)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Import one test set of dataset/<set>/ into the lab database. "
                    "The database is the source of the labels after the import.")
    parser.add_argument("set_dir", help="the directory of the set, for example "
                        "../../svoe-vino-testset/dataset/my")
    parser.add_argument("--db", required=True, help="path of the lab database")
    parser.add_argument("--set", required=True, dest="set_name",
                        help="the name of the set in the database, for example my")
    parser.add_argument("--force", action="store_true",
                        help="replace the edits of the Testset page with the files")
    args = parser.parse_args(argv)

    def log(message):
        print(message, flush=True)

    try:
        report = import_testset(args.db, args.set_name, args.set_dir, log, force=args.force)
    except (TestsetError, imagestore.StoreError, labdb.SchemaError, sqlite3.Error,
            OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print_report(report, args.set_name, args.set_dir, args.db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
