"""Store direct links between entries for the same wine across vintages.

A link has no direction. A wine without a year MAY have more than one link.
Keep this relation separate from visual similarity. The caller owns the transaction.
"""
import comments


class VintageError(ValueError):
    """The two slugs do not make a pair."""


class DuplicateError(ValueError):
    """The pair exists."""


def pair(slug, other):
    """Return the stored order (a, b) of the pair of `slug` and `other`."""
    if slug == other:
        raise VintageError("a wine cannot link a vintage to itself")
    return (slug, other) if slug < other else (other, slug)


def partners(conn, slug=None):
    """Return wine slug -> the list of its partner slugs, in rowid order.

    With `slug`, the answer holds that wine alone. A wine with no pair has no key.
    """
    query = "SELECT wine_slug_a, wine_slug_b FROM wine_vintage"
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
        "SELECT wine_slug_a, wine_slug_b FROM wine_vintage ORDER BY wine_slug_a, wine_slug_b")]


def count(conn):
    """Return the number of pairs."""
    return conn.execute("SELECT count(*) FROM wine_vintage").fetchone()[0]


def add(conn, slug, other, now=None):
    """Add the pair of `slug` and `other`, and return its stored order (a, b).

    A pair that exists raises `DuplicateError`. `now` is the stored time, or None for the
    present time.
    """
    a, b = pair(slug, other)
    if conn.execute("SELECT 1 FROM wine_vintage WHERE wine_slug_a = ? AND wine_slug_b = ?",
                    (a, b)).fetchone():
        raise DuplicateError("the wines %s and %s are already linked as vintages" % (a, b))
    conn.execute("INSERT INTO wine_vintage (wine_slug_a, wine_slug_b, created_at) "
                 "VALUES (?, ?, ?)", (a, b, now or comments.now_utc()))
    return a, b


def remove(conn, slug, other):
    """Remove the pair of `slug` and `other`. Return False for a pair that does not exist."""
    a, b = pair(slug, other)
    return conn.execute("DELETE FROM wine_vintage WHERE wine_slug_a = ? AND wine_slug_b = ?",
                        (a, b)).rowcount > 0


def reassign(conn, source, target):
    """Move links when a duplicate catalogue entry is merged. Drop self-links."""
    rows = conn.execute("SELECT wine_slug_a, wine_slug_b, created_at FROM wine_vintage "
                        "WHERE wine_slug_a = ? OR wine_slug_b = ?", (source, source)).fetchall()
    conn.execute("DELETE FROM wine_vintage WHERE wine_slug_a = ? OR wine_slug_b = ?",
                 (source, source))
    for a, b, stamp in rows:
        a, b = (target if a == source else a), (target if b == source else b)
        if a != b:
            conn.execute("INSERT INTO wine_vintage VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
                         (*sorted((a, b)), stamp))


def cluster_pairs(links, known):
    """Connect known family members, including a family with an unindexed hub."""
    parent = {}

    def find(slug):
        parent.setdefault(slug, slug)
        if parent[slug] != slug:
            parent[slug] = find(parent[slug])
        return parent[slug]

    for a, b in links:
        parent[find(b)] = find(a)
    groups = {}
    for slug in sorted(known):
        if slug in parent:
            groups.setdefault(find(slug), []).append(slug)
    return sorted((members[0], other) for members in groups.values() for other in members[1:])
