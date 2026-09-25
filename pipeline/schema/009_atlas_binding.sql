-- 009: the Drink Atlas Core product of a wine.
--
-- One row links one wine, one source, and one product UUID of Drink Atlas Core. A wine
-- has at most one row of each source.
--   automatic  a match of svoe-wino-hackaton/scripts/match_atlas.py (atlas-matches.jsonl).
--   manual     a binding by a person: the old file atlas-bindings.manual.jsonl or the
--              Dataset page.
-- The effective binding of a wine is its manual row, else its automatic row. One product
-- MAY belong to more than one wine. The owner chose the database and the remove of a
-- manual row on 2026-09-25.
--
-- The stored UUID is the lower-case form with hyphens, as Python `str(uuid.UUID(text))`
-- gives. pipeline/atlas_bindings.py checks the rest.
--
-- The foreign key blocks `DROP TABLE wine_catalog` while this table holds rows. A later
-- schema file that builds `wine_catalog` again MUST handle this table too.
-- pipeline/seed_atlas_bindings.py fills the table from the two JSONL files. Read
-- docs/plans/15_atlas-binding.md.

CREATE TABLE wine_atlas_binding (
    wine_slug    TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    source       TEXT NOT NULL CHECK (source IN ('automatic', 'manual')),
    product_uuid TEXT NOT NULL CHECK (length(product_uuid) = 36
        AND product_uuid NOT GLOB '*[^0-9a-f-]*'
        AND product_uuid GLOB '????????-????-????-????-????????????'),
    PRIMARY KEY (wine_slug, source)
) STRICT;

-- The lookup of the wines of one product.
CREATE INDEX wine_atlas_binding_product ON wine_atlas_binding (product_uuid);
