"""Store or remove the patch of one wine: its image of the type `main_patched`.

The lab server calls these functions for `POST` and `DELETE` of `/api/dataset-patch`.
The database is the truth for the patches. The owner chose this on 2026-09-25. Read
`docs/plans/14_patch-editor.md`.

Rules:
- A patch is a JPEG, PNG, or WebP image of at most `MAX_BYTES` bytes. Pillow reads the
  type from the bytes.
- The file goes to the image store under its SHA-256. A SHA-256 that `image` holds
  already reuses the stored file.
- `store_patch` creates the package cut and the label cut before its write transaction,
  so a slow SAM3 does not hold the write lock. SAM3 does not answer: the patch stays
  stored, and the answer holds a warning for each missing cut.
- `remove_patch` deletes the row alone. The file stays in the store, because another row
  can use it.
- A wine of each state MAY get a patch, as in `seed_patched.py`.

The store path and the `INSERT INTO image` are each in one function: `file_path` and
`insert_image`. `lab_server.card_images` builds the URL of a patch.
"""
import hashlib
import io
import os

from PIL import Image

import derive
import imagestore
import labdb

IMAGE_TYPE = "main_patched"
MATCH_METHOD = "manual"
# The source name of an upload whose request holds no file name.
DEFAULT_NAME = "upload"
MAX_NAME = 255
MAX_BYTES = 20 * 1024 * 1024
# The largest pixel count of an upload. The largest catalogue image has about 60 MP; a
# small file of a huge image would take gigabytes of memory in the processing.
MAX_PIXELS = 100_000_000
# The Pillow format of an accepted patch -> the extension of the stored file. These are
# the types of the patch folder: `seed_patched.IMAGE_EXTENSIONS`.
FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
NO_LABEL_CUT = ("The patch is stored with no label cut. A label-view embedding cannot "
                "be generated.")


class PatchError(Exception):
    """A patch change is not allowed. `code` is the HTTP status of the answer."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def file_path(db_path, folder, digest, extension):
    """Return the path of one file of the image store."""
    return os.path.join(labdb.image_dir(db_path, folder), "%s.%s" % (digest, extension))


def insert_image(conn, digest, extension, width, height, folder=None):
    """Write the row of `image` of an uploaded file, unless the table holds it. `folder`
    None means the folder of the patches. `alternatives.py` uses this function too."""
    conn.execute("INSERT INTO image (sha256, folder, extension, width, height) "
                 "VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                 (digest, folder or labdb.IMAGE_FOLDERS[IMAGE_TYPE], extension, width,
                  height))
    conn.execute("UPDATE image SET width = ?, height = ? WHERE sha256 = ? "
                 "AND width IS NULL", (width, height, digest))


def read_image(data):
    """Return (extension, width, height) of the patch bytes. Raise `PatchError`."""
    if not data:
        raise PatchError(400, "the body holds no image")
    if len(data) > MAX_BYTES:
        raise PatchError(413, "the image is larger than %d bytes" % MAX_BYTES)
    try:
        with Image.open(io.BytesIO(data)) as image:
            image_format, size = image.format, image.size
            if size[0] * size[1] > MAX_PIXELS:
                raise PatchError(413, "the image has %d × %d pixels; the limit is %d pixels"
                                 % (size[0], size[1], MAX_PIXELS))
            image.load()
    except (OSError, ValueError, SyntaxError) as exc:
        raise PatchError(400, "Pillow cannot read the image: %s" % exc)
    if image_format not in FORMATS:
        raise PatchError(400, "the image is %s; a patch MUST be JPEG, PNG, or WebP"
                         % image_format)
    return (FORMATS[image_format],) + size


def source_name(name):
    """Return the `source_name` of an upload: the base name of its file name."""
    name = os.path.basename((name or "").replace("\\", "/")).strip()
    return name[:MAX_NAME] or DEFAULT_NAME


def _check_slug(slug):
    if not isinstance(slug, str) or not slug:
        raise PatchError(400, "the request holds no wine slug")


def _check_wine(conn, slug):
    if conn.execute("SELECT 1 FROM wine_catalog WHERE wine_slug = ?",
                    (slug,)).fetchone() is None:
        raise PatchError(404, "no wine with the slug %s" % slug)


def store_patch(conn, db_path, slug, data, name=None, segmenter=None):
    """Store `data` as the patch of the wine `slug`. Return a dict: `sha256`, `changed`
    (False when the wine has this patch already), and `warnings`.

    `conn` is a write connection with `isolation_level` None. `segmenter` is the SAM3
    client; None means `derive.Sam3Client()`.
    """
    _check_slug(slug)
    extension, width, height = read_image(data)
    _check_wine(conn, slug)
    digest = hashlib.sha256(data).hexdigest()
    row = conn.execute("SELECT folder, extension FROM image WHERE sha256 = ?",
                       (digest,)).fetchone()
    folder, stored_extension = row or (labdb.IMAGE_FOLDERS[IMAGE_TYPE], extension)
    path = file_path(db_path, folder, digest, stored_extension)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        imagestore.store_bytes(data, path, digest)
    except (imagestore.StoreError, OSError) as exc:
        raise PatchError(500, "cannot store the patch: %s" % exc)

    client = segmenter or derive.Sam3Client()
    warnings = []
    package = derive.derive_all(conn, db_path, {digest: path}, client, warnings.append)
    if package.unavailable or package.unreadable or package.errors:
        warnings.insert(0, "The patch is stored with no processed file. The card shows "
                           "the patch as it is.")
    # Import here because `alternatives` uses the patch validation and store functions.
    import alternatives
    label_warnings = []
    label = alternatives.process_image(conn, db_path, digest, path, "label", client,
                                       label_warnings)
    if (label.unavailable or label.unreadable or label.errors
            or not (label.links or label.present
                    or getattr(label, "not_applicable", None))):
        warnings.append(NO_LABEL_CUT)
    warnings.extend(label_warnings)

    conn.execute("BEGIN IMMEDIATE")
    try:
        _check_wine(conn, slug)
        insert_image(conn, digest, extension, width, height)
        old = conn.execute("SELECT sha256 FROM wine_image WHERE wine_slug = ? AND "
                           "image_type = ?", (slug, IMAGE_TYPE)).fetchone()
        changed = old is None or old[0] != digest
        if changed:
            conn.execute("DELETE FROM wine_image WHERE wine_slug = ? AND image_type = ?",
                         (slug, IMAGE_TYPE))
            conn.execute("INSERT INTO wine_image (wine_slug, image_type, sha256, "
                         "source_name, match_method) VALUES (?, ?, ?, ?, ?)",
                         (slug, IMAGE_TYPE, digest, source_name(name), MATCH_METHOD))
        derive.write_rows(conn, package)
        alternatives.write_processed_rows(conn, label)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return {"sha256": digest, "changed": changed, "warnings": warnings}


def remove_patch(conn, slug):
    """Delete the `main_patched` row of the wine `slug`. Return a dict: `sha256` of the
    removed patch. The file stays in the store.

    `conn` is a write connection with `isolation_level` None.
    """
    _check_slug(slug)
    conn.execute("BEGIN IMMEDIATE")
    try:
        _check_wine(conn, slug)
        row = conn.execute("SELECT sha256 FROM wine_image WHERE wine_slug = ? AND "
                           "image_type = ?", (slug, IMAGE_TYPE)).fetchone()
        if row is None:
            raise PatchError(404, "the wine %s has no patch" % slug)
        conn.execute("DELETE FROM wine_image WHERE wine_slug = ? AND image_type = ?",
                     (slug, IMAGE_TYPE))
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return {"sha256": row[0]}
