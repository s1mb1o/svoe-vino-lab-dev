CREATE INDEX wine_code_value ON wine_code (kind, value);

CREATE INDEX wine_atlas_binding_product ON wine_atlas_binding (product_uuid);

CREATE INDEX wine_comment_wine ON wine_comment (wine_slug, created_at, id);

CREATE UNIQUE INDEX wine_image_one_main ON wine_image (wine_slug, image_type)
    WHERE image_type IN ('main', 'main_patched');

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

PRAGMA user_version = 21;
