"""The free-form text tags of an image: the table `image_tag` (schema 030).

One row is one tag of one image. The key is the SHA-256 of the bytes, so each test photo
that holds the bytes shows the same tags, in each set and in each place. The owner chose
this on 2026-09-27T23:53:00+0300. One image MAY have more than one tag. The rowid order is
the order of the adds. `created_at` is the UTC time of the add, in the form of
`comments.now_utc`.

A tag has the form of a wine tag: `wine_tags.normal` makes it (plan 63). A change of the
rules there changes the rules of the image tags too.

The Testset page writes the tags through `testsets.py`, and the import of a set adds them.
The pipeline does not read the tags. A function that writes runs in the transaction of
the caller. Read `docs/plans/66_testset-image-tags.md`.
"""
import comments
import wine_tags

TagError = wine_tags.TagError
normal = wine_tags.normal


class DuplicateError(ValueError):
    """The image has the tag."""


def tags(conn, digests=None):
    """Return SHA-256 -> the list of its tags, in rowid order.

    With `digests`, the answer holds those images alone. An image with no tag has no key.
    """
    wanted = None if digests is None else set(digests)
    out = {}
    for digest, tag in conn.execute("SELECT sha256, tag FROM image_tag ORDER BY rowid"):
        if wanted is None or digest in wanted:
            out.setdefault(digest, []).append(tag)
    return out


def names(conn):
    """Return each tag of the table once, in text order, with the number of its images:
    a list of {tag, images}."""
    return [{"tag": tag, "images": n} for tag, n in conn.execute(
        "SELECT tag, count(*) FROM image_tag GROUP BY tag ORDER BY tag")]


def add(conn, digest, text, now=None):
    """Add one tag to the image `digest`, and return the normal form of the tag.

    A tag that the image has raises `DuplicateError`. `now` is the stored time, or None
    for the present time.
    """
    tag = normal(text)
    if conn.execute("SELECT 1 FROM image_tag WHERE sha256 = ? AND tag = ?",
                    (digest, tag)).fetchone():
        raise DuplicateError("the image %s has the tag %s" % (digest[:12], tag))
    conn.execute("INSERT INTO image_tag (sha256, tag, created_at) VALUES (?, ?, ?)",
                 (digest, tag, now or comments.now_utc()))
    return tag


def remove(conn, digest, text):
    """Remove one tag of the image `digest`. Return False for a tag that the image does
    not have."""
    return conn.execute("DELETE FROM image_tag WHERE sha256 = ? AND tag = ?",
                        (digest, normal(text))).rowcount > 0
