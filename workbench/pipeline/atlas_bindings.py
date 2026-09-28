"""The Drink Atlas Core products of a wine: the table `wine_atlas_binding` (schema 025).

A wine MAY have 2 or more products. One row links one wine and one product UUID. Each
row keeps its source as a label:
- `automatic`: a match of `svoe-wino-hackaton/scripts/match_atlas.py`.
- `manual`: a binding by a person.

The seed and the lab server use these functions. A function that writes runs in the
transaction of the caller. Read `docs/plans/15_atlas-binding.md` and
`docs/plans/54_atlas-binding-list.md`.
"""
import uuid

SOURCES = ("automatic", "manual")


class BindingError(ValueError):
    """A value is not a valid product UUID."""


class DuplicateError(ValueError):
    """The wine already has the product UUID."""


def clean_uuid(value):
    """Check one product UUID and return its stored form: lower case, with hyphens.

    The messages are those of the review tool.
    """
    if not isinstance(value, str):
        raise BindingError("product_uuid MUST be a string")
    text = value.strip()
    if not text:
        raise BindingError("product_uuid is empty")
    try:
        return str(uuid.UUID(text))
    except ValueError as exc:
        raise BindingError("product_uuid is not a valid UUID") from exc


def bindings(conn, slug=None):
    """Return wine slug -> a list of (product UUID, source), in rowid order.

    With `slug`, the answer holds that wine alone. A wine with no row has no key.
    """
    query = "SELECT wine_slug, product_uuid, source FROM wine_atlas_binding"
    rows = (conn.execute(query + " WHERE wine_slug = ? ORDER BY rowid", (slug,))
            if slug is not None else conn.execute(query + " ORDER BY rowid"))
    out = {}
    for wine, product, source in rows:
        out.setdefault(wine, []).append((product, source))
    return out


def counts(conn):
    """Return (the rows, the manual rows)."""
    return conn.execute("SELECT count(*), count(*) FILTER (WHERE source = 'manual') "
                        "FROM wine_atlas_binding").fetchone()


def add_manual(conn, slug, product_uuid):
    """Add one manual row to `slug`, and return the stored UUID.

    A UUID that the wine already has, of either source, raises `DuplicateError`.
    """
    clean = clean_uuid(product_uuid)
    if conn.execute("SELECT 1 FROM wine_atlas_binding WHERE wine_slug = ? "
                    "AND product_uuid = ?", (slug, clean)).fetchone():
        raise DuplicateError("the wine %s already has the Atlas product %s" % (slug, clean))
    conn.execute("INSERT INTO wine_atlas_binding (wine_slug, source, product_uuid) "
                 "VALUES (?, 'manual', ?)", (slug, clean))
    return clean


def approve(conn, slug, product_uuid):
    """Change the automatic row of `slug` and `product_uuid` to a manual row.

    A person confirmed the match. The row keeps its rowid, so its place in the list stays.
    Return the old source of the row, or None for a row that does not exist. A manual row
    does not change.
    """
    row = conn.execute("SELECT source FROM wine_atlas_binding WHERE wine_slug = ? "
                       "AND product_uuid = ?", (slug, product_uuid)).fetchone()
    if row is None:
        return None
    conn.execute("UPDATE wine_atlas_binding SET source = 'manual' WHERE wine_slug = ? "
                 "AND product_uuid = ?", (slug, product_uuid))
    return row[0]


def remove(conn, slug, product_uuid):
    """Remove the row of `slug` and `product_uuid`, of either source.

    Return the source of the removed row, or None for a row that does not exist. The
    seed does not add a removed automatic row back, because it refuses a table with rows.
    """
    row = conn.execute("SELECT source FROM wine_atlas_binding WHERE wine_slug = ? "
                       "AND product_uuid = ?", (slug, product_uuid)).fetchone()
    if row is None:
        return None
    conn.execute("DELETE FROM wine_atlas_binding WHERE wine_slug = ? AND product_uuid = ?",
                 (slug, product_uuid))
    return row[0]
