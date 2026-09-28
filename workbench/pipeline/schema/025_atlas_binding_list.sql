-- 025: a wine MAY have 2 or more Drink Atlas Core products.
--
-- The owner chose this on 2026-09-26: one list per wine, and each row keeps its source as
-- a label. The rule of 009 "the manual row replaces the automatic row" goes away. One
-- wine has at most one row for one product UUID. The rowid order is the order of the list
-- on the Dataset page.
--   automatic  a match of svoe-wino-hackaton/scripts/match_atlas.py (atlas-matches.jsonl).
--   manual     a binding by a person: the old file atlas-bindings.manual.jsonl or the
--              Dataset page.
--
-- SQLite cannot change a primary key, so this file builds `wine_atlas_binding` again.
-- It keeps the effective row of each wine: the manual row, else the automatic row. An
-- automatic row that a manual row hides is dropped. The owner chose this on 2026-09-26.
-- The rows keep their rowid. The column order and the checks of 009 stay.
-- Read docs/plans/54_atlas-binding-list.md.

CREATE TABLE wine_atlas_binding_new (
    wine_slug    TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    source       TEXT NOT NULL CHECK (source IN ('automatic', 'manual')),
    product_uuid TEXT NOT NULL CHECK (length(product_uuid) = 36
        AND product_uuid NOT GLOB '*[^0-9a-f-]*'
        AND product_uuid GLOB '????????-????-????-????-????????????'),
    PRIMARY KEY (wine_slug, product_uuid)
) STRICT;

INSERT INTO wine_atlas_binding_new (rowid, wine_slug, source, product_uuid)
SELECT rowid, wine_slug, source, product_uuid
FROM wine_atlas_binding AS row
WHERE source = 'manual'
   OR NOT EXISTS (SELECT 1 FROM wine_atlas_binding AS manual
                  WHERE manual.wine_slug = row.wine_slug AND manual.source = 'manual')
ORDER BY rowid;

DROP TABLE wine_atlas_binding;

ALTER TABLE wine_atlas_binding_new RENAME TO wine_atlas_binding;

-- The lookup of the wines of one product.
CREATE INDEX wine_atlas_binding_product ON wine_atlas_binding (product_uuid);
