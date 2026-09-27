"""The wine type of a wine: the table `wine_beverage_type`.

`beverage_type_code` has the name of the column of Drink Atlas Core. `4` is a wine that is
not sparkling. `44` is a sparkling wine. Both values are prefixes of the EGAIS product type
codes, not dictionary codes. A wine has a type while it has a row. A wine with a type MAY
have each state, also `Removed`. `updated_at` is the UTC time of the last change of the
code, in the form of `comments.now_utc`.

The lab server uses these functions. A function that writes runs in the transaction of
the caller. Read `docs/plans/52_wine-beverage-type.md`.
"""
import comments

# The codes in the order of the page: a wine, a sparkling wine.
CODES = ("4", "44")


def types(conn):
    """Return wine slug -> `beverage_type_code` of each wine with a type."""
    return dict(conn.execute("SELECT wine_slug, beverage_type_code FROM wine_beverage_type"))


def counts(conn):
    """Return code -> the number of wines with the code, for each code of `CODES`."""
    found = dict(conn.execute("SELECT beverage_type_code, count(*) FROM wine_beverage_type "
                              "GROUP BY beverage_type_code"))
    return {code: found.get(code, 0) for code in CODES}


def set_type(conn, slug, code, now=None):
    """Set the type of `slug` to `code`, or remove the type when `code` is None. Return
    `code`.

    The same code again keeps the stored time. A remove of a missing type changes
    nothing. `now` is the stored time, or None for the present time. The CHECK of the
    table refuses a code that is not in `CODES`.
    """
    if code is None:
        conn.execute("DELETE FROM wine_beverage_type WHERE wine_slug = ?", (slug,))
    else:
        conn.execute(
            "INSERT INTO wine_beverage_type (wine_slug, beverage_type_code, updated_at) "
            "VALUES (?, ?, ?) ON CONFLICT (wine_slug) DO UPDATE SET "
            "beverage_type_code = excluded.beverage_type_code, "
            "updated_at = excluded.updated_at "
            "WHERE wine_beverage_type.beverage_type_code IS NOT excluded.beverage_type_code",
            (slug, code, now or comments.now_utc()))
    return code
