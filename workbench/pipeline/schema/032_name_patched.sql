-- Plan 89: the name that a person gives a card on the Dataset page.
--
-- `name` keeps the value of the import: vino-svoe.ru, the CSV, or the form `Add wine`.
-- The imports compare and write `name` alone. `name_patched` is the edit of a person, or
-- NULL. The name in use is `name_patched`, else `name`, as `main_patched` and `main`.
-- The owner chose this on 2026-09-29. Read docs/plans/89_card-name-patch.md.

ALTER TABLE wine_catalog ADD COLUMN name_patched TEXT CHECK (name_patched <> '');

-- The rule of schema 015: a new column of the table gets its line in the trigger of the
-- update.
DROP TRIGGER wine_catalog_update_time;

CREATE TRIGGER wine_catalog_update_time AFTER UPDATE OF
    name, producer, category, color, region, grapes, description, csv_photo_name, state,
    removed_by, name_patched ON wine_catalog
WHEN OLD.name IS NOT NEW.name OR OLD.producer IS NOT NEW.producer
     OR OLD.category IS NOT NEW.category OR OLD.color IS NOT NEW.color
     OR OLD.region IS NOT NEW.region OR OLD.grapes IS NOT NEW.grapes
     OR OLD.description IS NOT NEW.description
     OR OLD.csv_photo_name IS NOT NEW.csv_photo_name OR OLD.state IS NOT NEW.state
     OR OLD.removed_by IS NOT NEW.removed_by
     OR OLD.name_patched IS NOT NEW.name_patched
BEGIN
    UPDATE wine_catalog SET modified_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE rowid = NEW.rowid;
END;

-- The rule of schema 031: the columns of the view stay the same. The column `name` is the
-- name in use, so the matcher reads the edit.
DROP VIEW matcher_wine;

CREATE VIEW matcher_wine AS
SELECT w.wine_slug, COALESCE(w.name_patched, w.name) AS name, w.producer, w.category,
       w.region, w.color, w.grapes,
       (SELECT i.source_name FROM wine_image i
        WHERE i.wine_slug = w.wine_slug AND i.image_type = 'main'
        ORDER BY i.rowid DESC LIMIT 1) AS main_source_name,
       (SELECT json_group_array(c.value) FROM wine_code c
        WHERE c.wine_slug = w.wine_slug AND c.kind = 'qr_url') AS qr_values
FROM wine_catalog w
WHERE w.state = 'Active';
