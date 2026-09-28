"""The free-form text tags of a wine: the table `wine_tag` (schema 029).

One row is one tag of one wine. One wine MAY have more than one tag. The rowid order is
the order of the adds. `created_at` is the UTC time of the add, in the form of
`comments.now_utc`. The first use is to mark the variants of one wine, for example
`generic` and `vintage:2017`, but the code requires no form of a tag.

The lab server uses these functions. The pipeline does not read the tags. A function
that writes runs in the transaction of the caller. Read `docs/plans/63_wine-tags.md`.
"""
import re

import comments

MAX_LENGTH = 64
# A letter (also Cyrillic), a digit, `_`, `-`, `:`, or `.`. No white space.
TAG_RE = re.compile(r"^[\w:.-]+$")


class TagError(ValueError):
    """The text is not a valid tag."""


class DuplicateError(ValueError):
    """The wine has the tag."""


def normal(text):
    """Return the normal form of a tag: no outer white space, lower case.

    A tag that is empty, longer than `MAX_LENGTH`, or that holds another character than
    a letter, a digit, `_`, `-`, `:`, or `.` raises `TagError`.
    """
    if not isinstance(text, str) or not text.strip():
        raise TagError("the tag is empty")
    tag = text.strip().lower()
    if len(tag) > MAX_LENGTH:
        raise TagError("a tag has at most %d characters" % MAX_LENGTH)
    if not TAG_RE.match(tag):
        raise TagError("a tag holds only letters, digits, and the characters _ - : . "
                       "(no white space): %r" % tag)
    return tag


def tags(conn, slug=None):
    """Return wine slug -> the list of its tags, in rowid order.

    With `slug`, the answer holds that wine alone. A wine with no tag has no key.
    """
    query = "SELECT wine_slug, tag FROM wine_tag"
    rows = (conn.execute(query + " WHERE wine_slug = ? ORDER BY rowid", (slug,))
            if slug is not None else conn.execute(query + " ORDER BY rowid"))
    out = {}
    for wine, tag in rows:
        out.setdefault(wine, []).append(tag)
    return out


def count(conn):
    """Return the number of rows: each tag of each wine counts one time."""
    return conn.execute("SELECT count(*) FROM wine_tag").fetchone()[0]


def add(conn, slug, text, now=None):
    """Add one tag to the wine `slug`, and return the normal form of the tag.

    A tag that the wine has raises `DuplicateError`. `now` is the stored time, or None
    for the present time.
    """
    tag = normal(text)
    if conn.execute("SELECT 1 FROM wine_tag WHERE wine_slug = ? AND tag = ?",
                    (slug, tag)).fetchone():
        raise DuplicateError("the wine %s has the tag %s" % (slug, tag))
    conn.execute("INSERT INTO wine_tag (wine_slug, tag, created_at) VALUES (?, ?, ?)",
                 (slug, tag, now or comments.now_utc()))
    return tag


def remove(conn, slug, text):
    """Remove one tag of the wine `slug`. Return False for a tag that the wine does not
    have."""
    return conn.execute("DELETE FROM wine_tag WHERE wine_slug = ? AND tag = ?",
                        (slug, normal(text))).rowcount > 0
