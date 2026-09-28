-- 003: the state of a wine, and no table catalog_source.
--
-- `Active`: the last imported CSV holds the wine.
-- `Removed`: the last imported CSV does not hold the wine.
-- `Disabled`: a person took the wine out of use. The import never sets this state.
-- pipeline/import_catalog.py sets `Active` and `Removed`.
--
-- The owner removed the table catalog_source on 2026-09-24. The database keeps no
-- record of the imported CSV files.
-- Read docs/plans/07_sqlite-lab-database.md.

ALTER TABLE wine_catalog ADD COLUMN state TEXT NOT NULL DEFAULT 'Active'
    CHECK (state IN ('Active', 'Disabled', 'Removed'));

DROP TABLE catalog_source;
