"""Store the patched main images of the wines, and add or replace their `main_patched` rows.

Usage:
    python3 pipeline/seed_patched.py --db data/catalog/catalog.sqlite3 \\
        ../../svoe-wino-hackaton/dataset/patched-official-2026-09-17

The patch folder is an overlay on a delivery. Each file `<wine_slug>.<extension>`
replaces the main image of that wine. Read the `README.md` of the folder. The script
copies each patch to `images/patched/<sha256>.<extension>` in the directory of the
database file. It writes one row of `image` for each file, and one row of the type
`main_patched` for each wine to the table `wine_image`. Then it processes each patch
with `derive.py`, as `seed_images.py` does. Read
`docs/plans/07_sqlite-lab-database.md`, step 5, and `docs/plans/09_image-processing.md`.

Rules of the folder:
- A patch is a file at the top level of the folder. The name before the extension is
  the wine slug. The extension is one of `IMAGE_EXTENSIONS`, in any case.
- The script skips a hidden file, a folder such as `_originals/`, and a file with
  another extension, such as `README.md`.
- A slug that `wine_catalog` does not hold gets a console message and no row.
- Two patch files for one slug are an error. The row of that wine does not change.

Rules of the rows. The database is the truth for the patches, and the folder is one
source of them. The owner chose this on 2026-09-25; the patch editor of the Dataset page
is the other source. Read `docs/plans/14_patch-editor.md`.
- A patch of a wine with no `main_patched` row adds a row.
- A patch with the same sha256 as the row of its wine changes nothing.
- A patch with another sha256 replaces the row of its wine. The old file stays in the
  store, because another row can use it.
- A `main_patched` row whose wine has no patch file in the folder stays. The script
  names it in the report. Before 2026-09-25 the script deleted such a row.
- A wine with an error keeps its row.
- `match_method` is `slug-name`: the file name is the wine slug.
- A wine of each state gets its patch: `Active`, `Disabled`, and `Removed`.

Rules of the store, as in `pipeline/seed_images.py`:
- A file that is in the store already is not written again. A stored file whose bytes
  do not agree with its name is an error. The script does not overwrite it.
- The script writes the files first. Then it reads the rows again and writes all
  changes in one transaction.
- The script reads the pixel size of each patch from its header.

Exit status: 0 also when a slug is unknown, and when SAM3 does not answer. 1 when the
run cannot start, or when a patch file or a stored file gave an error.
"""
import argparse
import collections
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import derive  # noqa: E402
import imagestore  # noqa: E402
import labdb  # noqa: E402
import seed_images  # noqa: E402

IMAGE_TYPE = "main_patched"
MATCH_METHOD = "slug-name"
# The extensions of a patch file. The README of the folder names `.webp` and `.png`.
IMAGE_EXTENSIONS = frozenset({"webp", "png", "jpg", "jpeg"})


class SeedError(Exception):
    """The run cannot start."""


class Report:
    """The counts and the slugs of one run."""

    def __init__(self):
        self.files = 0           # patch files in the folder
        self.skipped = []        # names that are not a patch file
        self.unknown = []        # slugs that wine_catalog does not hold
        self.errors = 0          # read errors, store errors, and slugs with two files
        self.added = []          # slugs with a new row
        self.replaced = []       # slugs whose row points to another file now
        self.kept = []           # slugs with a row and no file in the folder
        self.unchanged = 0       # slugs with the same row
        self.written = 0         # files copied to the store
        self.present = 0         # files that the store held already
        self.derivatives = derive.Derivatives()   # the processing of the patches

    def changed(self):
        return bool(self.added or self.replaced or self.written
                    or self.derivatives.written or self.derivatives.processed())


def store_of(db_path):
    """Return the folder of the type `main_patched` in the image store of the database."""
    return imagestore.folder_of(db_path, labdb.IMAGE_FOLDERS[IMAGE_TYPE])


def scan_patches(folder, report, log):
    """Return slug -> [file name] of the patch files. Record the skipped names."""
    patches = collections.defaultdict(list)
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        stem, extension = os.path.splitext(name)
        extension = extension[1:].lower()
        if name.startswith(".") or not os.path.isfile(path):
            continue
        if extension not in IMAGE_EXTENSIONS or not stem:
            report.skipped.append(name)
            log("skipped: %s is not a patch file" % name)
            continue
        patches[stem].append(name)
    report.files = sum(len(names) for names in patches.values())
    return patches


def seed_patched(db_path, folder, log=print, segmenter=None, force=False):
    """Store and process the patches, and add or replace the `main_patched` rows. Return
    a `Report`. `segmenter` is the SAM3 client; None means `derive.SAM3_ENDPOINT`.

    With rows of the type `main_patched` in the table and no `force`, raise `SeedError`:
    a second run would add back the patches that a person removed on the page. The owner
    chose this on 2026-09-25.
    """
    if not os.path.isdir(folder):
        raise SeedError("no patch folder at %s" % folder)
    conn = labdb.connect(db_path)
    conn.isolation_level = None
    try:
        present = conn.execute("SELECT count(*) FROM wine_image WHERE image_type = ?",
                               (IMAGE_TYPE,)).fetchone()[0]
        if present and not force:
            raise SeedError("wine_image already holds %d rows of the type %s; a second run "
                            "adds back the patches that a person removed on the page; give "
                            "--force to add the missing rows anyway" % (present, IMAGE_TYPE))
        wines = {row[0] for row in conn.execute("SELECT wine_slug FROM wine_catalog")}
        report = Report()
        patches = scan_patches(folder, report, log)
        store = store_of(db_path)
        os.makedirs(store, exist_ok=True)

        found = {}       # slug -> (sha256, extension, file name) of a stored patch
        keep = set()     # slugs with a file in the folder, also with an error
        files = {}       # sha256 -> row of image for each stored patch
        originals = {}   # sha256 -> store path of each patch to process
        for slug, names in patches.items():
            keep.add(slug)
            if slug not in wines:
                report.unknown.append(slug)
                log("unknown: %s: wine_catalog holds no wine with this slug" % slug)
                continue
            if len(names) > 1:
                report.errors += 1
                log("error: %s: %d patch files for one wine: %s; the row stays"
                    % (slug, len(names), ", ".join(names)))
                continue
            name = names[0]
            extension = os.path.splitext(name)[1][1:].lower()
            try:
                digest = imagestore.sha256_of(os.path.join(folder, name))
                target = os.path.join(store, "%s.%s" % (digest, extension))
                if imagestore.store_file(os.path.join(folder, name), target, digest):
                    report.written += 1
                else:
                    report.present += 1
            except (imagestore.StoreError, OSError) as exc:
                report.errors += 1
                log("error: %s: %s; the row stays" % (slug, exc))
                continue
            try:
                size = imagestore.pixel_size(target)
            except OSError as exc:
                size = (None, None)
                log("no pixel size: %s: %s: %s" % (slug, target, exc))
            found[slug] = (digest, extension, name)
            files[digest] = (digest, labdb.IMAGE_FOLDERS[IMAGE_TYPE], extension) + size
            originals[digest] = target

        report.derivatives = derive.derive_all(
            conn, db_path, originals, segmenter or derive.Sam3Client(), log)

        # The rows are read again under the write lock, so the changes fit the rows of
        # this moment and not the rows of the start of the run.
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.executemany(
                "INSERT INTO image (sha256, folder, extension, width, height) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING", list(files.values()))
            conn.executemany(
                "UPDATE image SET width = ?, height = ? WHERE sha256 = ? AND width IS NULL",
                [(w, h, d) for d, _, _, w, h in files.values() if w is not None])
            stored = {slug: digest for slug, digest in conn.execute(
                "SELECT wine_slug, sha256 FROM wine_image WHERE image_type = ?",
                (IMAGE_TYPE,))}
            for slug, (digest, extension, name) in found.items():
                old = stored.get(slug)
                if old == digest:
                    report.unchanged += 1
                    continue
                if old is not None:
                    conn.execute("DELETE FROM wine_image WHERE wine_slug = ? AND "
                                 "image_type = ?", (slug, IMAGE_TYPE))
                    report.replaced.append(slug)
                    log("replaced: %s: %s -> %s (%s)" % (slug, old, digest, name))
                else:
                    report.added.append(slug)
                conn.execute(
                    "INSERT INTO wine_image (wine_slug, image_type, sha256, source_name, "
                    "match_method) VALUES (?, ?, ?, ?, ?)",
                    (slug, IMAGE_TYPE, digest, name, MATCH_METHOD))
            report.kept = sorted(set(stored) - keep)
            derive.write_rows(conn, report.derivatives)
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return report


def _names(slugs):
    return ": " + ", ".join(slugs) if slugs else ""


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Store the patched main images of the wines, and add or replace "
                    "the rows of the type main_patched from the patch folder.")
    parser.add_argument("folder", help="the patch folder, for example "
                        "svoe-wino-hackaton/dataset/patched-official-2026-09-17")
    parser.add_argument("--db", required=True, help="path of the lab database")
    parser.add_argument("--sam3", default=derive.SAM3_ENDPOINT,
                        help="the SAM3 service (default: %(default)s)")
    parser.add_argument("--force", action="store_true",
                        help="run also when wine_image already holds main_patched rows")
    args = parser.parse_args(argv)

    def log(message):
        print(message, flush=True)

    try:
        report = seed_patched(args.db, args.folder, log, derive.Sam3Client(args.sam3),
                              args.force)
    except (SeedError, labdb.SchemaError, sqlite3.Error, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("patch folder: %s" % os.path.abspath(args.folder))
    print("patch files: %d" % report.files)
    print("skipped names: %d%s" % (len(report.skipped), _names(report.skipped)))
    print("unknown slugs: %d%s" % (len(report.unknown), _names(report.unknown)))
    print("errors: %d" % (report.errors + report.derivatives.errors))
    print("rows added: %d" % len(report.added))
    print("rows replaced: %d%s" % (len(report.replaced), _names(report.replaced)))
    print("rows kept with no file in the folder: %d%s"
          % (len(report.kept), _names(report.kept)))
    print("rows unchanged: %d" % report.unchanged)
    print("files written: %d" % report.written)
    print("files in the store already: %d" % report.present)
    seed_images.print_derivatives(report.derivatives)
    print("store: %s" % store_of(args.db))
    print("database: %s" % args.db)
    print("result: %s" % ("stored" if report.changed() else "no change"))
    return 1 if report.errors or report.derivatives.errors else 0


if __name__ == "__main__":
    sys.exit(main())
