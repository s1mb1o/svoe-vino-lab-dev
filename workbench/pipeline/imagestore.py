"""The file store of the images.

A stored file is `<sha256>.<extension>` in the directory of its folder. The function
`labdb.image_dir` gives the directory of each folder (plan 75). The name is the
SHA-256 of the bytes, so a file never changes. Each
writer of the store uses these functions: `seed_images.py`, `seed_patched.py`, and
`derive.py`. Read `docs/plans/08_seed-images.md` and `docs/plans/09_image-processing.md`.
"""
import hashlib
import os
import tempfile

from PIL import Image

import labdb

# The tools read images of the own store and of the deliveries. The largest has
# 60 megapixels, so the limit of Pillow against a decompression bomb is off.
Image.MAX_IMAGE_PIXELS = None


class StoreError(Exception):
    """A stored file or a source file does not agree with its sha256."""


def folder_of(db_path, folder):
    """Return the path of one folder of the image store of the database."""
    return labdb.image_dir(db_path, folder)


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def pixel_size(path):
    """Return (width, height) of the image at `path` from its header. Raise `OSError`
    if Pillow cannot read it."""
    with Image.open(path) as image:
        return image.size


def _check_stored(target, digest):
    if sha256_of(target) != digest:
        raise StoreError("%s: the stored bytes do not agree with the name; the file "
                         "stays" % target)


def store_bytes(data, target, digest):
    """Write `data` to `target` unless the store holds it. Return True on a write.

    Raise `StoreError` when a stored file does not agree with `digest`.
    """
    if os.path.exists(target):
        _check_stored(target, digest)
        return False
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


def store_file(source, target, digest):
    """Copy `source` to `target` unless the store holds it. Return True on a copy.

    Raise `StoreError` when the bytes do not agree with `digest`.
    """
    if os.path.exists(target):
        _check_stored(target, digest)
        return False
    with open(source, "rb") as fh:
        data = fh.read()
    if hashlib.sha256(data).hexdigest() != digest:
        raise StoreError("%s: the file changed during the run" % source)
    return store_bytes(data, target, digest)
