-- Plan 75, stage 2: the fixed views that the matcher reads from a copy of `data/catalog/`.
-- The matcher reads these two views alone, not the base tables. A later schema file that
-- changes a base table MUST keep the columns of these views.

-- One row for each `Active` wine. `main_source_name` is the `source_name` of the image
-- type `main`, for the public image URL of the card. `qr_values` is a JSON array of the
-- values of the kind `qr_url`; the matcher normalizes them.
CREATE VIEW matcher_wine AS
SELECT w.wine_slug, w.name, w.producer, w.category, w.region, w.color, w.grapes,
       (SELECT i.source_name FROM wine_image i
        WHERE i.wine_slug = w.wine_slug AND i.image_type = 'main'
        ORDER BY i.rowid DESC LIMIT 1) AS main_source_name,
       (SELECT json_group_array(c.value) FROM wine_code c
        WHERE c.wine_slug = w.wine_slug AND c.kind = 'qr_url') AS qr_values
FROM wine_catalog w
WHERE w.state = 'Active';

-- One row for each image of an `Active` wine, with the rules of `embeddings.read_inputs`:
-- a `main_patched` image replaces the `main` image of the same wine; the types
-- `label_front` and `label_back` have the role `label`, the other types the role `full`.
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
