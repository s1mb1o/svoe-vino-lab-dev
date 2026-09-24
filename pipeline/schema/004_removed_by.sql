-- 004: who removed a wine.
--
-- `removed_by` is `import` or `person` for a `Removed` wine, and NULL for another
-- state. The import restores a wine only when the import removed it. A removal by a
-- person lasts until a person restores the wine. The owner asked for this on
-- 2026-09-24. A wine that is `Removed` before this file was removed by the import.
--
-- SQLite cannot add a table constraint to an existing table. So this file builds the
-- table again. It keeps each rowid, so the import order stays.
-- Read docs/plans/07_sqlite-lab-database.md.

CREATE TABLE wine_catalog_004 (
    wine_slug      TEXT PRIMARY KEY CHECK (wine_slug <> ''),           -- Slug
    name           TEXT NOT NULL    CHECK (name <> ''),                -- Название вина
    producer       TEXT NOT NULL    CHECK (producer <> ''),            -- Винодельня
    category       TEXT NOT NULL    CHECK (category <> ''),            -- Категория
    color          TEXT NOT NULL    CHECK (color <> ''),               -- Цвет
    region         TEXT NOT NULL    CHECK (region <> ''),              -- Регион
    grapes         TEXT             CHECK (grapes <> ''),              -- Сорт винограда
    description    TEXT NOT NULL    CHECK (description <> ''),         -- Описание
    csv_photo_name TEXT NOT NULL    CHECK (csv_photo_name <> ''),      -- Название фото
    state          TEXT NOT NULL DEFAULT 'Active'
                   CHECK (state IN ('Active', 'Disabled', 'Removed')),
    removed_by     TEXT CHECK (removed_by IN ('import', 'person')),
    CHECK ((state = 'Removed') = (removed_by IS NOT NULL))
) STRICT;

INSERT INTO wine_catalog_004 (rowid, wine_slug, name, producer, category, color, region,
                              grapes, description, csv_photo_name, state, removed_by)
SELECT rowid, wine_slug, name, producer, category, color, region, grapes, description,
       csv_photo_name, state, CASE WHEN state = 'Removed' THEN 'import' END
FROM wine_catalog;

DROP TABLE wine_catalog;

ALTER TABLE wine_catalog_004 RENAME TO wine_catalog;
