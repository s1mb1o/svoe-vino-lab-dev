-- 015: the change times of a wine, and the refusals of the website import.
--
-- `website_modified_at` is the `lastmod` of the wine in `wines-sitemap.xml` of
-- vino-svoe.ru, as the sitemap writes it. `pipeline/import_website.py` writes it. NULL:
-- no import saw the wine yet.
-- `modified_at` is the UTC time of the last change of the row, to the second, in ISO 8601
-- with `Z`. The two triggers set it, so no writer changes its code. A change of a field
-- or of the state counts. A write of `website_modified_at` or `modified_at` does not
-- count. An existing row keeps NULL, because its change time is not known.
--
-- A schema file that builds `wine_catalog` again (as 004 and 014) drops the triggers.
-- Such a file MUST create both triggers again. A new column of the table MUST get its
-- line in the trigger of the update.
--
-- `website_refusal` holds the choices of a person in the merge dialog of the website
-- import: a conflict that keeps the database value, or a plain change that is cleared.
-- A later import skips it while its situation stays. `website_value` is the website
-- value for `text`, the SHA-256 of the website file for `image` and `main`, and NULL for
-- `new`, `missing`, and `back`. The table has no foreign key, because a refused new wine
-- is not in `wine_catalog`.
-- The owner chose this on 2026-09-25. Read docs/plans/21_website-import-ui.md.

ALTER TABLE wine_catalog ADD COLUMN website_modified_at TEXT
    CHECK (website_modified_at <> '');

ALTER TABLE wine_catalog ADD COLUMN modified_at TEXT
    CHECK (modified_at GLOB
           '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z');

CREATE TRIGGER wine_catalog_insert_time AFTER INSERT ON wine_catalog
WHEN NEW.modified_at IS NULL
BEGIN
    UPDATE wine_catalog SET modified_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER wine_catalog_update_time AFTER UPDATE OF
    name, producer, category, color, region, grapes, description, csv_photo_name, state,
    removed_by ON wine_catalog
WHEN OLD.name IS NOT NEW.name OR OLD.producer IS NOT NEW.producer
     OR OLD.category IS NOT NEW.category OR OLD.color IS NOT NEW.color
     OR OLD.region IS NOT NEW.region OR OLD.grapes IS NOT NEW.grapes
     OR OLD.description IS NOT NEW.description
     OR OLD.csv_photo_name IS NOT NEW.csv_photo_name OR OLD.state IS NOT NEW.state
     OR OLD.removed_by IS NOT NEW.removed_by
BEGIN
    UPDATE wine_catalog SET modified_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE rowid = NEW.rowid;
END;

CREATE TABLE website_refusal (
    wine_slug     TEXT NOT NULL CHECK (wine_slug <> ''),
    kind          TEXT NOT NULL
                  CHECK (kind IN ('text', 'image', 'new', 'missing', 'back', 'main')),
    field         TEXT NOT NULL DEFAULT '',
    website_value TEXT,
    created_at    TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    PRIMARY KEY (wine_slug, kind, field),
    CHECK ((kind = 'text') = (field <> ''))
) STRICT;
