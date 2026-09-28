-- 014: the description of a wine is optional.
--
-- The owner chose this on 2026-09-25T12:09:52+0300 for the form `Add wine` of the
-- Dataset page. A wine with no description holds NULL. An empty text stays refused. The
-- imports still require a description in their source. Read docs/plans/20_add-wine.md.
--
-- SQLite cannot drop a NOT NULL constraint, so this file builds `wine_catalog` again. It
-- keeps each row and its rowid, so the import order stays. Five tables reference
-- `wine_catalog`: `wine_image`, `wine_code`, `wine_atlas_binding`, `wine_comment`, and
-- `wine_favorite`. They keep their rows. Their foreign keys name the table, so they
-- point to the new table after the rename. `labdb.migrate` runs this file with the
-- foreign keys off and checks each link before the COMMIT.

CREATE TABLE wine_catalog_new (
    wine_slug      TEXT PRIMARY KEY CHECK (wine_slug <> ''),           -- Slug
    name           TEXT NOT NULL    CHECK (name <> ''),                -- Название вина
    producer       TEXT NOT NULL    CHECK (producer <> ''),            -- Винодельня
    category       TEXT NOT NULL    CHECK (category <> ''),            -- Категория
    color          TEXT NOT NULL    CHECK (color <> ''),               -- Цвет
    region         TEXT NOT NULL    CHECK (region <> ''),              -- Регион
    grapes         TEXT             CHECK (grapes <> ''),              -- Сорт винограда
    description    TEXT             CHECK (description <> ''),         -- Описание
    csv_photo_name TEXT NOT NULL    CHECK (csv_photo_name <> ''),      -- Название фото
    state          TEXT NOT NULL DEFAULT 'Active'
                   CHECK (state IN ('Active', 'Disabled', 'Removed')),
    removed_by     TEXT CHECK (removed_by IN ('import', 'person')),
    CHECK ((state = 'Removed') = (removed_by IS NOT NULL))
) STRICT;

INSERT INTO wine_catalog_new (rowid, wine_slug, name, producer, category, color, region,
                              grapes, description, csv_photo_name, state, removed_by)
SELECT rowid, wine_slug, name, producer, category, color, region, grapes, description,
       csv_photo_name, state, removed_by
FROM wine_catalog;

DROP TABLE wine_catalog;

ALTER TABLE wine_catalog_new RENAME TO wine_catalog;
