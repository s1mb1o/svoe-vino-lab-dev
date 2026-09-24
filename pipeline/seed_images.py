"""Find the main image of each wine in the Strapi uploads, and store it.

Usage:
    python3 pipeline/seed_images.py --db data/lab.sqlite3 \\
        ../svoe-wino-hackaton/dataset/official-2026-09-17/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads

The script reads the table `wine_catalog` and the flat `uploads` folder of one
delivery. It copies each found file to `images/main/<sha256>.<extension>` in the
directory of the database file. It writes one row of the type `main` for each found
wine to the table `wine_image`. It reads no network resource. Read
`docs/plans/08_seed-images.md`.

Rules of the match. They are stage 1 of `svoe-wino-hackaton/scripts/build_catalog.py`:
- The match key of a name: drop the extension, transliterate Cyrillic, keep `a-z0-9`
  alone, in lower case.
- An upload name loses its Strapi suffix `_<10 hex>` before the key is made. A resized
  variant (`thumbnail_`, `small_`, `medium_`, `large_`) is left out.
- The key of `csv_photo_name` is looked up without its extension first, then with it.
- One upload file fits: the method is `name-unique`.
- Several upload files fit, and their bytes are equal: the method is `name-identical`.
  `source_name` is the first of the file names in sort order.
- Several upload files fit, and their bytes differ: no match.
- No upload file fits: no match.
- A wine with no match gets a console message and no row. The run goes on.

Rules of the store:
- The extension is the extension of `source_name`, in lower case.
- A file that is in the store already is not written again. A stored file whose bytes
  do not agree with its name is an error. The script does not overwrite it.
- A wine that has a `main` row with the same sha256 keeps its row. The script writes
  the file again if the store does not hold it.
- A wine that has a `main` row with another sha256 keeps its row. The script reports a
  conflict and writes no file for the wine.
- The script writes the files first. It writes all new rows in one transaction.
- A wine of each state gets an image: `Active`, `Disabled`, and `Removed`.

Exit status: 0 also when wines have no match or a conflict. 1 when the run cannot
start, or when an upload file or a stored file gave an error.
"""
import argparse
import collections
import hashlib
import os
import re
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labdb  # noqa: E402

IMAGE_TYPE = "main"
# The store of the type `main`, relative to the directory of the database file.
STORE = os.path.join("images", "main")
# The extensions that the column `extension` accepts.
EXTENSION_RE = re.compile(r"^[0-9a-z]+$")

# The match rule of `svoe-wino-hackaton/scripts/build_catalog.py`, stage 1. This copy
# MUST stay equal to that rule.
RU = {'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e', 'ж': 'zh',
      'з': 'z', 'и': 'i', 'й': 'j', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
      'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'cz',
      'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu',
      'я': 'ya'}
HASH = re.compile(r'^(.*)_([0-9a-f]{10})$')
VARIANT = re.compile(r'^(thumbnail|small|medium|large)_')


class SeedError(Exception):
    """The run cannot start."""


class StoreError(Exception):
    """A stored file or an upload file does not agree with its sha256."""


class Report:
    """The counts of one run."""

    def __init__(self):
        self.indexed = 0                        # upload files in the match index
        self.wines = 0                          # wines of wine_catalog
        self.methods = collections.Counter()    # found wines by match_method
        self.no_match = collections.Counter()   # wines with no match, by reason
        self.conflicts = 0     # found wines that keep another main row
        self.errors = 0        # read errors and store errors
        self.unchanged = 0     # found wines that have the same main row
        self.added = 0         # rows written
        self.late = 0          # new rows that another writer added first
        self.written = 0       # files copied to the store
        self.present = 0       # files that the store held already


def norm(name, keep_ext=False):
    """Return the separator-insensitive match key of one file name."""
    stem, ext = os.path.splitext(name)
    s = ''.join(RU.get(c.lower(), c) for c in stem).lower()
    s = re.sub(r'[^a-z0-9]+', '', s)
    if keep_ext:
        s += re.sub(r'[^a-z0-9]+', '', ext.lower())
    return s


def index_uploads(updir):
    """Return match key -> [file name]. A resized variant is left out."""
    uploads = collections.defaultdict(list)
    for fn in sorted(os.listdir(updir)):
        if VARIANT.match(fn):
            continue
        m = HASH.match(os.path.splitext(fn)[0])
        if m:
            uploads[norm(m.group(1))].append(fn)
    return uploads


def candidates_of(photo, uploads):
    """Return the upload files that one CSV photo name can mean."""
    return uploads.get(norm(photo)) or uploads.get(norm(photo, keep_ext=True)) or []


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def store_file(source, target, digest):
    """Copy `source` to `target` unless the store holds it. Return True on a copy.

    Raise `StoreError` when the bytes do not agree with `digest`.
    """
    if os.path.exists(target):
        if sha256_of(target) != digest:
            raise StoreError("%s: the stored bytes do not agree with the name; the "
                             "file stays" % target)
        return False
    with open(source, "rb") as fh:
        data = fh.read()
    if hashlib.sha256(data).hexdigest() != digest:
        raise StoreError("%s: the file changed during the run" % source)
    fd, temp = tempfile.mkstemp(prefix=".", suffix=".tmp", dir=os.path.dirname(target))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.chmod(temp, 0o644)
        os.replace(temp, target)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise
    return True


def seed_images(db_path, updir, log=print):
    """Find and store the main image of each wine. Return a `Report`.

    `log` gets one message for each wine with no match, a conflict, or an error.
    """
    if not os.path.isdir(updir):
        raise SeedError("no uploads folder at %s" % updir)
    conn = labdb.connect(db_path)
    conn.isolation_level = None
    try:
        wines = conn.execute("SELECT wine_slug, csv_photo_name FROM wine_catalog "
                             "ORDER BY rowid").fetchall()
        stored = {slug: (digest, extension) for slug, digest, extension in conn.execute(
            "SELECT wine_slug, sha256, extension FROM wine_image WHERE image_type = ?",
            (IMAGE_TYPE,))}
        uploads = index_uploads(updir)
        store = os.path.join(os.path.dirname(os.path.abspath(db_path)), STORE)
        os.makedirs(store, exist_ok=True)

        report = Report()
        report.indexed = sum(len(names) for names in uploads.values())
        report.wines = len(wines)
        digests = {}     # upload file name -> sha256
        checked = set()  # store paths that this run wrote or checked
        rows = []
        for slug, photo in wines:
            names = candidates_of(photo, uploads)
            if not names:
                report.no_match["no candidate"] += 1
                log("no match: %s: no upload file fits the photo name %r" % (slug, photo))
                continue
            try:
                for name in names:
                    if name not in digests:
                        digests[name] = sha256_of(os.path.join(updir, name))
            except OSError as exc:
                report.errors += 1
                log("error: %s: cannot read an upload file: %s" % (slug, exc))
                continue
            found = [digests[name] for name in names]
            if len(set(found)) > 1:
                report.no_match["different bytes"] += 1
                log("no match: %s: %d upload files fit the photo name %r, and their "
                    "bytes differ: %s" % (slug, len(names), photo, ", ".join(names)))
                continue
            source, digest = names[0], found[0]
            extension = os.path.splitext(source)[1][1:].lower()
            if not EXTENSION_RE.match(extension):
                report.no_match["bad extension"] += 1
                log("no match: %s: the upload file %s has no usable extension"
                    % (slug, source))
                continue
            method = "name-unique" if len(names) == 1 else "name-identical"
            report.methods[method] += 1

            old = stored.get(slug)
            if old is not None and old[0] != digest:
                report.conflicts += 1
                log("conflict: %s: the database holds main %s.%s; the uploads give %s "
                    "(%s); the row stays" % (slug, old[0], old[1], digest, source))
                continue
            if old is not None:
                extension = old[1]
            target = os.path.join(store, "%s.%s" % (digest, extension))
            if target not in checked:
                try:
                    if store_file(os.path.join(updir, source), target, digest):
                        report.written += 1
                    else:
                        report.present += 1
                except (StoreError, OSError) as exc:
                    report.errors += 1
                    log("error: %s: %s" % (slug, exc))
                    continue
                checked.add(target)
            if old is None:
                rows.append((slug, IMAGE_TYPE, digest, extension, source, method))
            else:
                report.unchanged += 1

        # The write lock is taken after the files are copied, so the lab server can
        # write while the files are copied. ON CONFLICT covers a row that another
        # writer added after the read.
        conn.execute("BEGIN IMMEDIATE")
        try:
            cursor = conn.executemany(
                "INSERT INTO wine_image (wine_slug, image_type, sha256, extension, "
                "source_name, match_method) VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT DO NOTHING", rows)
            report.added = cursor.rowcount if rows else 0
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        report.late = len(rows) - report.added
    finally:
        conn.close()
    return report


def _counts(counter):
    return ", ".join("%s %d" % item for item in sorted(counter.items()))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Find the main image of each wine in the Strapi uploads folder "
                    "by the CSV photo name, and store it. No network access.")
    parser.add_argument("uploads", help="the flat Strapi uploads folder, for example "
                        "official-2026-09-17/prod-svoe-vino-strapi/prod-svoe-vino/"
                        "strapi/uploads")
    parser.add_argument("--db", required=True, help="path of the lab database")
    args = parser.parse_args(argv)

    def log(message):
        print(message, flush=True)

    try:
        report = seed_images(args.db, args.uploads, log)
    except (SeedError, labdb.SchemaError, sqlite3.Error, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    found = sum(report.methods.values())
    missed = sum(report.no_match.values())
    print("uploads: %s" % os.path.abspath(args.uploads))
    print("upload files indexed: %d" % report.indexed)
    print("wines: %d" % report.wines)
    print("matched: %d%s" % (found, " (%s)" % _counts(report.methods) if found else ""))
    print("no match: %d%s" % (missed, " (%s)" % _counts(report.no_match) if missed else ""))
    print("conflicts: %d" % report.conflicts)
    print("errors: %d" % report.errors)
    print("rows added: %d" % report.added)
    if report.late:
        print("rows that another writer added first: %d" % report.late)
    print("rows unchanged: %d" % report.unchanged)
    print("files written: %d" % report.written)
    print("files in the store already: %d" % report.present)
    print("store: %s" % os.path.join(os.path.dirname(os.path.abspath(args.db)), STORE))
    print("database: %s" % args.db)
    print("result: %s" % ("no change" if not (report.added or report.written)
                          else "stored"))
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
