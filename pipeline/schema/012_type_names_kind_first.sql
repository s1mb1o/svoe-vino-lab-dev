-- 012: the names of the additional image types put the kind first, then the side.
--
-- The owner chose these names on 2026-09-25T11:27:30+0300:
--   full_front   a full package, front side      (was `front_full`)
--   label_front  a close-up of the front label   (was `front_label`)
--   full_back    a full package, back side       (was `back_full`)
--   label_back   a close-up of the back label    (was `back_label`)
-- Read docs/plans/16_alternative-images.md.
--
-- SQLite cannot change a CHECK constraint, so this file builds `wine_image` again, as
-- 010 did. It maps each name of 010 to the new name. It keeps each row and its rowid,
-- because the rowid is the order of the uploads. No table references `wine_image`.

CREATE TABLE wine_image_new (
    wine_slug    TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    image_type   TEXT NOT NULL
                 CHECK (image_type IN ('main', 'main_patched', 'full_front', 'label_front',
                                       'full_back', 'label_back')),
    sha256       TEXT NOT NULL REFERENCES image (sha256),
    source_name  TEXT NOT NULL CHECK (source_name <> ''),
    match_method TEXT NOT NULL CHECK (match_method <> ''),
    PRIMARY KEY (wine_slug, image_type, sha256)
) STRICT;

INSERT INTO wine_image_new (rowid, wine_slug, image_type, sha256, source_name,
                            match_method)
SELECT rowid, wine_slug,
       CASE image_type WHEN 'front_full' THEN 'full_front'
                       WHEN 'front_label' THEN 'label_front'
                       WHEN 'back_full' THEN 'full_back'
                       WHEN 'back_label' THEN 'label_back'
                       ELSE image_type END,
       sha256, source_name, match_method
FROM wine_image;

DROP TABLE wine_image;

ALTER TABLE wine_image_new RENAME TO wine_image;

-- A wine has at most one `main` image and at most one `main_patched` image.
CREATE UNIQUE INDEX wine_image_one_main ON wine_image (wine_slug, image_type)
    WHERE image_type IN ('main', 'main_patched');
