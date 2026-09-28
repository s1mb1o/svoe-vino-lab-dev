"""The timestamped comments of a wine: the table `wine_comment`.

One wine MAY have more than one comment. The lists are in time order, the oldest first.
`created_at` is the UTC time of the write, to the second, in ISO 8601 with `Z`. A remove
names the `id`, because two comments MAY hold the same text. `source` is `user` for a
person on the Dataset page and `script` for a script.

The lab server uses these functions. A function that writes runs in the transaction of
the caller. Read `docs/plans/17_wine-comments.md`.
"""
import datetime

TEXT_MAX = 4000
SOURCES = ("user", "script")
# The order of the comments of one wine: the time, then the order of the writes.
ORDER = " ORDER BY created_at, id"


class CommentError(ValueError):
    """A comment text or a source is not valid."""


def clean_text(value):
    """Check one comment text and return its stored form.

    The line breaks become `\\n`. The white space at the start and at the end goes away.
    A control character other than `\\n` and `\\t` is refused. A lone surrogate
    (U+D800 to U+DFFF, possible in JSON as `\\ud800`) is refused too: SQLite cannot
    store it as UTF-8.
    """
    if not isinstance(value, str):
        raise CommentError("the comment MUST be a string")
    text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise CommentError("the comment is empty")
    if len(text) > TEXT_MAX:
        raise CommentError("the comment is longer than %d characters" % TEXT_MAX)
    if any((ord(char) < 32 and char not in "\n\t") or ord(char) == 127 for char in text):
        raise CommentError("the comment contains a control character")
    if any(0xD800 <= ord(char) <= 0xDFFF for char in text):
        raise CommentError("the comment contains a lone surrogate character")
    return text


def check_source(source):
    """Raise `CommentError` for a source that is not in `SOURCES`."""
    if source not in SOURCES:
        raise CommentError("unknown source %r; use one of: %s"
                           % (source, ", ".join(SOURCES)))


def now_utc():
    """Return the present UTC time in the stored form."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row(row):
    comment_id, created_at, source, text = row
    return {"id": comment_id, "created_at": created_at, "source": source, "text": text}


def comments(conn, slug=None):
    """Return wine slug -> the comments of the wine, in time order.

    Each comment is `{"id", "created_at", "source", "text"}`. With `slug`, the answer
    holds that wine alone. A wine with no comment has no key.
    """
    query = "SELECT wine_slug, id, created_at, source, text FROM wine_comment"
    rows = (conn.execute(query + " WHERE wine_slug = ?" + ORDER, (slug,))
            if slug is not None else conn.execute(query + ORDER))
    out = {}
    for wine, *row in rows:
        out.setdefault(wine, []).append(_row(row))
    return out


def count(conn):
    """Return the number of comments."""
    return conn.execute("SELECT count(*) FROM wine_comment").fetchone()[0]


def add(conn, slug, text, source, now=None):
    """Add one comment of `source` to `slug`, and return it. `now` is the stored time,
    or None for the present time."""
    check_source(source)
    clean = clean_text(text)
    created_at = now or now_utc()
    cursor = conn.execute("INSERT INTO wine_comment (wine_slug, created_at, source, text) "
                          "VALUES (?, ?, ?, ?)", (slug, created_at, source, clean))
    return {"id": cursor.lastrowid, "created_at": created_at, "source": source,
            "text": clean}


def remove(conn, slug, comment_id):
    """Remove one comment of `slug`. Return it, or None when the wine has no comment
    with this id."""
    row = conn.execute("SELECT id, created_at, source, text FROM wine_comment "
                       "WHERE wine_slug = ? AND id = ?", (slug, comment_id)).fetchone()
    if row is None:
        return None
    conn.execute("DELETE FROM wine_comment WHERE id = ?", (comment_id,))
    return _row(row)
