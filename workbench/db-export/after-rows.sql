CREATE INDEX wine_code_value ON wine_code (kind, value);

CREATE INDEX wine_comment_wine ON wine_comment (wine_slug, created_at, id);

CREATE UNIQUE INDEX wine_image_one_main ON wine_image (wine_slug, image_type)
    WHERE image_type IN ('main', 'main_patched');

CREATE INDEX test_photo_comment_photo ON test_photo_comment (set_name, place, file_name);

CREATE INDEX wine_atlas_binding_product ON wine_atlas_binding (product_uuid);

CREATE INDEX image_label_description_image ON image_label_description (sha256, created_at);

CREATE INDEX wine_similar_b ON wine_similar (wine_slug_b);

CREATE TRIGGER wine_catalog_insert_time AFTER INSERT ON wine_catalog
WHEN NEW.modified_at IS NULL
BEGIN
    UPDATE wine_catalog SET modified_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER wine_code_insert_time AFTER INSERT ON wine_code
WHEN NEW.modified_at IS NULL
BEGIN
    UPDATE wine_code SET modified_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE rowid = NEW.rowid;
END;

CREATE VIEW matcher_wine_image AS
SELECT wi.wine_slug, wi.image_type, wi.sha256,
       CASE WHEN wi.image_type IN ('label_front', 'label_back') THEN 'label'
            ELSE 'full' END AS role
FROM wine_image wi
JOIN wine_catalog w ON w.wine_slug = wi.wine_slug
WHERE w.state = 'Active'
  AND wi.image_type IN ('main', 'main_patched', 'full_front', 'full_back', 'label_front',
                        'label_back')
  AND NOT (wi.image_type = 'main' AND EXISTS (
      SELECT 1 FROM wine_image p
      WHERE p.wine_slug = wi.wine_slug AND p.image_type = 'main_patched'));

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

PRAGMA user_version = 32;
