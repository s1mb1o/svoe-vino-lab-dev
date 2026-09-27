-- 023: the wine type of a wine.
--
-- `beverage_type_code` has the name of the column of Drink Atlas Core. `4` is a wine that
-- is not sparkling. `44` is a sparkling wine. Both values are prefixes of the EGAIS
-- product type codes, not dictionary codes. The owner chose the two values on 2026-09-26.
-- A wine has a type while it has a row. A change to "not set" deletes the row. A wine
-- with a type MAY have each state, also `Removed`.
--   updated_at  the UTC time of the last change of the code, to the second, in ISO 8601
--               with `Z`, as `wine_comment.created_at`.
-- The owner chose a separate table on 2026-09-26, so the imports of the catalogue and
-- the change-time triggers of 015 do not change. A new code value needs a new schema
-- file, because SQLite cannot change a CHECK in place.
--
-- The foreign key blocks `DROP TABLE wine_catalog` while this table holds rows. A later
-- schema file that builds `wine_catalog` again MUST handle this table too.
-- Read docs/plans/52_wine-beverage-type.md.

CREATE TABLE wine_beverage_type (
    wine_slug          TEXT PRIMARY KEY REFERENCES wine_catalog (wine_slug),
    beverage_type_code TEXT NOT NULL CHECK (beverage_type_code IN ('4', '44')),
    updated_at         TEXT NOT NULL CHECK (updated_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z')
) STRICT;
