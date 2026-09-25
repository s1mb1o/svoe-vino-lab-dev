-- 013: the favorite wines.
--
-- A wine is a favorite while it has a row. A remove of the mark deletes the row. A
-- favorite wine MAY have each state, also `Removed`.
--   created_at  the UTC time of the mark, to the second, in ISO 8601 with `Z`, as
--               `wine_comment.created_at`.
-- The owner chose a separate table on 2026-09-25, so the imports of the catalogue do not
-- change.
--
-- The foreign key blocks `DROP TABLE wine_catalog` while this table holds rows. A later
-- schema file that builds `wine_catalog` again MUST handle this table too.
-- Read docs/plans/19_favorites.md.

CREATE TABLE wine_favorite (
    wine_slug  TEXT PRIMARY KEY REFERENCES wine_catalog (wine_slug),
    created_at TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z')
) STRICT;
