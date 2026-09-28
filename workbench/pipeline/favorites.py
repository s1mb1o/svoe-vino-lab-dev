"""The favorite wines: the table `wine_favorite`.

A wine is a favorite while it has a row. A favorite wine MAY have each state, also
`Removed`. `created_at` is the UTC time of the mark, in the form of `comments.now_utc`.

The lab server uses these functions. A function that writes runs in the transaction of
the caller. Read `docs/plans/19_favorites.md`.
"""
import comments


def favorites(conn):
    """Return wine slug -> `created_at` of each favorite wine."""
    return dict(conn.execute("SELECT wine_slug, created_at FROM wine_favorite"))


def count(conn):
    """Return the number of favorite wines."""
    return conn.execute("SELECT count(*) FROM wine_favorite").fetchone()[0]


def set_favorite(conn, slug, on, now=None):
    """Mark `slug` as a favorite when `on` is true, else remove the mark. Return `on`.

    A second mark keeps the first time. A remove of a missing mark changes nothing.
    `now` is the stored time, or None for the present time.
    """
    if on:
        conn.execute("INSERT INTO wine_favorite (wine_slug, created_at) VALUES (?, ?) "
                     "ON CONFLICT (wine_slug) DO NOTHING", (slug, now or comments.now_utc()))
    else:
        conn.execute("DELETE FROM wine_favorite WHERE wine_slug = ?", (slug,))
    return on
