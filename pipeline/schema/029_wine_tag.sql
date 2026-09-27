-- 029: the free-form text tags of a wine (plan 63).
--
-- One row is one tag of one wine. One wine MAY have more than one tag. The rowid order is
-- the order of the adds.
--   tag         the normal form of `pipeline/wine_tags.py`: no outer white space, lower
--               case, only letters, digits, `_`, `-`, `:`, and `.`. The module checks the
--               form. The CHECK holds the length alone. Examples: `generic`,
--               `vintage:2017`. The owner chose free-form tags on 2026-09-27.
--   created_at  the UTC time of the add, to the second, in ISO 8601 with `Z`, as
--               `wine_favorite.created_at`.
-- A wine of each state MAY have tags. The pipeline does not read the tags.
--
-- The foreign key blocks `DROP TABLE wine_catalog` while this table holds rows. A later
-- schema file that builds `wine_catalog` again MUST handle this table too.
-- Read docs/plans/63_wine-tags.md.

CREATE TABLE wine_tag (
    wine_slug  TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    tag        TEXT NOT NULL CHECK (tag <> '' AND length(tag) <= 64),
    created_at TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    PRIMARY KEY (wine_slug, tag)
) STRICT;
