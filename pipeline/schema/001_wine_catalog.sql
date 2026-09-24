-- 001: the wine catalogue of one delivery.
--
-- Source: the Strapi CSV of the organizers, for example
-- svoe-wino-hackaton/dataset/official-2026-09-17/strapi_output0709.csv.
-- pipeline/seed_catalog.py fills both tables. Read docs/plans/07_sqlite-lab-database.md.

-- The CSV file of the catalogue. One database holds one delivery, so this table
-- holds at most one row.
CREATE TABLE catalog_source (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    source_path   TEXT    NOT NULL,
    source_sha256 TEXT    NOT NULL CHECK (length(source_sha256) = 64),
    source_rows   INTEGER NOT NULL CHECK (source_rows > 0),
    imported_at   TEXT    NOT NULL
) STRICT;

-- One row per catalogue card. The slug is the only candidate key of the CSV.
-- Each column holds the value of one CSV column without its outer white space.
CREATE TABLE wine_catalog (
    slug           TEXT PRIMARY KEY CHECK (slug <> ''),           -- Slug
    name           TEXT NOT NULL    CHECK (name <> ''),           -- Название вина
    producer       TEXT NOT NULL    CHECK (producer <> ''),       -- Винодельня
    category       TEXT NOT NULL    CHECK (category <> ''),       -- Категория
    color          TEXT NOT NULL    CHECK (color <> ''),          -- Цвет
    region         TEXT NOT NULL    CHECK (region <> ''),         -- Регион
    grapes         TEXT             CHECK (grapes <> ''),         -- Сорт винограда, verbatim list; NULL when the CSV value is empty
    description    TEXT NOT NULL    CHECK (description <> ''),    -- Описание
    csv_photo_name TEXT NOT NULL    CHECK (csv_photo_name <> '')  -- Название фото; not unique
) STRICT;
