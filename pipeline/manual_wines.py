"""Add a wine by hand: one row of `wine_catalog` and its `main` image.

The lab server calls `add_wine` for `POST /api/wine`, the form `Add wine` of the Dataset
page. The owner chose the design on 2026-09-25. Read `docs/plans/20_add-wine.md`.

Rules:
- The slug of a manual wine starts with `MANUAL_PREFIX`. No slug of the catalogue starts
  with `_`, so a manual slug cannot be equal to a slug of vino-svoe.ru. `is_manual`
  tells a manual slug. The imports never remove a manual wine, and a source slug with
  the prefix stops an import.
- The full slug MUST match `SLUG`. A slug of `RESERVED_SLUGS` is refused. A slug that
  `wine_catalog` holds already, in any state, is a conflict.
- Each text value, and `image_name`, MUST be a JSON string that UTF-8 can encode. JSON
  admits a lone surrogate such as `\\ud800`, and SQLite cannot store it.
- Each text value loses its outer white space, as in `import_catalog.py`. An empty
  `grapes` or `description` becomes NULL. Each other field is required. The owner made
  the description optional on 2026-09-25; the schema file `014_description_optional.sql`
  allows NULL.
- The main image is required. `patches.read_image` checks it. Its base name becomes
  `csv_photo_name` and the `source_name` of the `main` row.
- `derive.derive_all` processes the image before the write transaction, as in
  `patches.py`. SAM3 does not answer: the wine is stored with no processed file, and
  the answer holds a warning.
- One write transaction writes the wine as `Active`, the `image` row, the `main` row of
  `wine_image`, and the processed rows.

The store path and the `INSERT INTO image` are each in one function: `file_path` and
`insert_image`.
"""
import base64
import binascii
import hashlib
import os
import re

import derive
import imagestore
import labdb
import patches

MANUAL_PREFIX = "__"
SLUG = re.compile(r"^__[a-z0-9][a-z0-9_-]*$")
MAX_SLUG = 200
# `__null__` is the place of the photos that match no wine: `NULL_SLUG` of
# `scripts/match_scoring.py`.
RESERVED_SLUGS = frozenset({"__null__"})
IMAGE_TYPE = "main"
MATCH_METHOD = "manual"
FOLDER = labdb.IMAGE_FOLDERS[IMAGE_TYPE]
# The text fields of the form, in the order of `wine_catalog`. `grapes` and
# `description` MAY be empty.
TEXT_FIELDS = ("name", "producer", "category", "color", "region", "grapes",
               "description")
NULLABLE = frozenset({"grapes", "description"})
# The largest body of `POST /api/wine`: the base64 form of the largest image and 64 KiB
# for the text fields.
MAX_BODY = (patches.MAX_BYTES + 2) // 3 * 4 + 64 * 1024


class WineError(Exception):
    """A new wine is not allowed. `code` is the HTTP status of the answer."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def is_manual(slug):
    """Tell whether `slug` is the slug of a wine that a person added."""
    return slug.startswith(MANUAL_PREFIX)


def file_path(db_path, folder, digest, extension):
    """Return the path of one file of the image store."""
    return patches.file_path(db_path, folder, digest, extension)


def insert_image(conn, digest, extension, width, height):
    """Write the row of `image` of a main image, unless the table holds it."""
    conn.execute("INSERT INTO image (sha256, folder, extension, width, height) "
                 "VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                 (digest, FOLDER, extension, width, height))
    conn.execute("UPDATE image SET width = ?, height = ? WHERE sha256 = ? "
                 "AND width IS NULL", (width, height, digest))


def check_slug(slug):
    """Raise `WineError` 400 unless `slug` is a valid manual slug."""
    if not isinstance(slug, str) or not slug.strip():
        raise WineError(400, "the request holds no wine slug")
    slug = slug.strip()
    if len(slug) > MAX_SLUG:
        raise WineError(400, "the slug has more than %d characters" % MAX_SLUG)
    if not SLUG.match(slug):
        raise WineError(400, "the slug %r MUST start with %s and hold only a-z, 0-9, "
                             "- and _ after it" % (slug, MANUAL_PREFIX))
    if slug in RESERVED_SLUGS:
        raise WineError(400, "the slug %s is reserved" % slug)
    return slug


def _text(body, field):
    """Return the value of `field`: a string, or None. Raise `WineError` 400."""
    value = body.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise WineError(400, "the field `%s` MUST be text" % field)
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise WineError(400, "the field `%s` holds a character that is not valid text"
                        % field)
    return value


def read_fields(body):
    """Return the text values of the request in the order of `TEXT_FIELDS`."""
    values = []
    for field in TEXT_FIELDS:
        value = (_text(body, field) or "").strip()
        if not value and field not in NULLABLE:
            raise WineError(400, "the field `%s` is empty" % field)
        values.append(value or None)
    return values


def read_image(body):
    """Return the image bytes of the request. Raise `WineError` 400."""
    image = body.get("image")
    if not isinstance(image, str) or not image:
        raise WineError(400, "the request holds no main image")
    try:
        return base64.b64decode(image, validate=True)
    except (binascii.Error, ValueError):
        raise WineError(400, "the field `image` is not base64")


def _check_new(conn, slug):
    if conn.execute("SELECT 1 FROM wine_catalog WHERE wine_slug = ?",
                    (slug,)).fetchone() is not None:
        raise WineError(409, "the database holds a wine with the slug %s already" % slug)


def add_wine(conn, db_path, body, segmenter=None):
    """Add the wine of the request `body`. Return a dict: `slug` and `warnings`.

    `conn` is a write connection with `isolation_level` None. `segmenter` is the SAM3
    client; None means `derive.Sam3Client()`.
    """
    slug = check_slug(body.get("slug"))
    values = read_fields(body)
    data = read_image(body)
    try:
        extension, width, height = patches.read_image(data)
    except patches.PatchError as exc:
        raise WineError(exc.code, str(exc))
    name = patches.source_name(_text(body, "image_name"))
    _check_new(conn, slug)

    digest = hashlib.sha256(data).hexdigest()
    row = conn.execute("SELECT folder, extension FROM image WHERE sha256 = ?",
                       (digest,)).fetchone()
    folder, stored_extension = row or (FOLDER, extension)
    path = file_path(db_path, folder, digest, stored_extension)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        imagestore.store_bytes(data, path, digest)
    except (imagestore.StoreError, OSError) as exc:
        raise WineError(500, "cannot store the main image: %s" % exc)

    warnings = []
    derivatives = derive.derive_all(conn, db_path, {digest: path},
                                    segmenter or derive.Sam3Client(), warnings.append)
    if derivatives.unavailable or derivatives.unreadable or derivatives.errors:
        warnings.insert(0, "The wine is stored with no processed file. The card shows "
                           "the main image as it is.")

    conn.execute("BEGIN IMMEDIATE")
    try:
        _check_new(conn, slug)
        conn.execute("INSERT INTO wine_catalog (wine_slug, %s, csv_photo_name, state) "
                     "VALUES (?, %s, ?, 'Active')"
                     % (", ".join(TEXT_FIELDS), ", ".join("?" for _ in TEXT_FIELDS)),
                     [slug] + values + [name])
        insert_image(conn, digest, extension, width, height)
        conn.execute("INSERT INTO wine_image (wine_slug, image_type, sha256, "
                     "source_name, match_method) VALUES (?, ?, ?, ?, ?)",
                     (slug, IMAGE_TYPE, digest, name, MATCH_METHOD))
        derive.write_rows(conn, derivatives)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return {"slug": slug, "warnings": warnings}
