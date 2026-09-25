"""The Drink Atlas Core product of a wine: the table `wine_atlas_binding` (schema 009).

A wine has at most one row of each source:
- `automatic`: a match of `svoe-wino-hackaton/scripts/match_atlas.py`.
- `manual`: a binding by a person.

The effective binding of a wine is its manual row, else its automatic row. The seed and
the lab server use these functions. A function that writes runs in the transaction of
the caller. Read `docs/plans/15_atlas-binding.md`.
"""
import uuid

SOURCES = ("automatic", "manual")


class BindingError(ValueError):
    """A value is not a valid product UUID."""


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
    """Return wine slug -> (product UUID, source) of the effective binding.

    With `slug`, the answer holds that wine alone. A wine with no row has no key.
    """
    query = "SELECT wine_slug, source, product_uuid FROM wine_atlas_binding"
    rows = (conn.execute(query + " WHERE wine_slug = ?", (slug,)) if slug is not None
            else conn.execute(query))
    out = {}
    for wine, source, product in rows:
        if source == "manual" or wine not in out:
            out[wine] = (product, source)
    return out


def counts(conn):
    """Return (the wines with an effective binding, the wines with a manual row)."""
    total = conn.execute(
        "SELECT count(DISTINCT wine_slug) FROM wine_atlas_binding").fetchone()[0]
    manual = conn.execute(
        "SELECT count(*) FROM wine_atlas_binding WHERE source = 'manual'").fetchone()[0]
    return total, manual


def set_manual(conn, slug, product_uuid):
    """Set the manual row of `slug`, and return the stored UUID."""
    clean = clean_uuid(product_uuid)
    conn.execute("INSERT INTO wine_atlas_binding (wine_slug, source, product_uuid) "
                 "VALUES (?, 'manual', ?) ON CONFLICT (wine_slug, source) "
                 "DO UPDATE SET product_uuid = excluded.product_uuid", (slug, clean))
    return clean


def remove_manual(conn, slug):
    """Remove the manual row of `slug`. Return its UUID, or None for a wine with none."""
    row = conn.execute("SELECT product_uuid FROM wine_atlas_binding "
                       "WHERE wine_slug = ? AND source = 'manual'", (slug,)).fetchone()
    if row is None:
        return None
    conn.execute("DELETE FROM wine_atlas_binding WHERE wine_slug = ? AND source = 'manual'",
                 (slug,))
    return row[0]
