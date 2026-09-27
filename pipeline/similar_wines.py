"""The manual relation `similar` between two wines: the table `wine_similar` (schema 028).

One row is one pair. The relation has no direction: the pair (A, B) is the pair (B, A).
The smaller slug is always in `wine_slug_a`. `created_at` is the UTC time of the mark, in
the form of `comments.now_utc`.

The lab server and the cluster build use these functions. A function that writes runs in
the transaction of the caller. Read `docs/plans/62_similar-wines.md`.
"""
import comments


class SimilarError(ValueError):
    """The two slugs do not make a pair."""


class DuplicateError(ValueError):
    """The pair exists."""


def pair(slug, other):
    """Return the stored order (a, b) of the pair of `slug` and `other`."""
    if slug == other:
        raise SimilarError("a wine cannot be similar to itself")
    return (slug, other) if slug < other else (other, slug)


def partners(conn, slug=None):
    """Return wine slug -> the list of its partner slugs, in rowid order.

    With `slug`, the answer holds that wine alone. A wine with no pair has no key.
    """
    query = "SELECT wine_slug_a, wine_slug_b FROM wine_similar"
    rows = (conn.execute(query + " WHERE wine_slug_a = ? OR wine_slug_b = ? ORDER BY rowid",
                         (slug, slug))
            if slug is not None else conn.execute(query + " ORDER BY rowid"))
    out = {}
    for a, b in rows:
        if slug is None or a == slug:
            out.setdefault(a, []).append(b)
        if slug is None or b == slug:
            out.setdefault(b, []).append(a)
    return out


def pairs(conn):
    """Return the sorted list of the pairs (a, b)."""
    return [tuple(row) for row in conn.execute(
        "SELECT wine_slug_a, wine_slug_b FROM wine_similar ORDER BY wine_slug_a, wine_slug_b")]


def count(conn):
    """Return the number of pairs."""
    return conn.execute("SELECT count(*) FROM wine_similar").fetchone()[0]


def add(conn, slug, other, now=None):
    """Add the pair of `slug` and `other`, and return its stored order (a, b).

    A pair that exists raises `DuplicateError`. `now` is the stored time, or None for the
    present time.
    """
    a, b = pair(slug, other)
    if conn.execute("SELECT 1 FROM wine_similar WHERE wine_slug_a = ? AND wine_slug_b = ?",
                    (a, b)).fetchone():
        raise DuplicateError("the wines %s and %s are already similar" % (a, b))
    conn.execute("INSERT INTO wine_similar (wine_slug_a, wine_slug_b, created_at) "
                 "VALUES (?, ?, ?)", (a, b, now or comments.now_utc()))
    return a, b


def remove(conn, slug, other):
    """Remove the pair of `slug` and `other`. Return False for a pair that does not exist."""
    a, b = pair(slug, other)
    return conn.execute("DELETE FROM wine_similar WHERE wine_slug_a = ? AND wine_slug_b = ?",
                        (a, b)).rowcount > 0
