-- 010: the types of the additional images are front_full, front_label, back_full, and
-- back_label.
--
-- The owner chose these names on 2026-09-25:
--   front_full   a full package, front side      (was `front`)
--   front_label  a close-up of the front label   (was `label_front`)
--   back_full    a full package, back side       (was `back`)
--   back_label   a close-up of the back label    (was `label_back`)
-- The Dataset page adds these images and changes their type. Read
-- docs/plans/16_alternative-images.md.
--
-- SQLite cannot change a CHECK constraint, so this file builds `wine_image` again. It maps
-- each old name to the new name. It keeps each row and its rowid, because the rowid is
-- the order of the uploads. No table references `wine_image`.

CREATE TABLE wine_image_new (
    wine_slug    TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    image_type   TEXT NOT NULL
                 CHECK (image_type IN ('main', 'main_patched', 'front_full', 'front_label',
                                       'back_full', 'back_label')),
    sha256       TEXT NOT NULL REFERENCES image (sha256),
    source_name  TEXT NOT NULL CHECK (source_name <> ''),
    match_method TEXT NOT NULL CHECK (match_method <> ''),
    PRIMARY KEY (wine_slug, image_type, sha256)
) STRICT;

INSERT INTO wine_image_new (rowid, wine_slug, image_type, sha256, source_name,
                            match_method)
SELECT rowid, wine_slug,
       CASE image_type WHEN 'front' THEN 'front_full' WHEN 'label_front' THEN 'front_label'
                       WHEN 'back' THEN 'back_full' WHEN 'label_back' THEN 'back_label'
                       ELSE image_type END,
       sha256, source_name, match_method
FROM wine_image;

DROP TABLE wine_image;

ALTER TABLE wine_image_new RENAME TO wine_image;

-- A wine has at most one `main` image and at most one `main_patched` image.
CREATE UNIQUE INDEX wine_image_one_main ON wine_image (wine_slug, image_type)
    WHERE image_type IN ('main', 'main_patched');
