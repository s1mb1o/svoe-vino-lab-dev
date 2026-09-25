-- 007: one row for each stored file, and the processed file of an original.
--
-- `image` holds each file of the image store: an original or a processed file. The file
-- is `images/<folder>/<sha256>.<extension>` in the directory of the database file. The
-- folder of an original is the folder of the image type that stored it first.
-- `wine_image` links a wine and an image type to an original. It loses the columns
-- `extension`, `width`, and `height`: they depend on the file, and `image` holds them now.
-- `image_derivative` links an original to its processed file. The box is in the pixels
-- of the original after its EXIF orientation.
--
-- The owner chose option C on 2026-09-25. Rules 9 to 12 of AGENTS.md allow the rebuild.
-- The file keeps each row of `wine_image`. pipeline/derive.py writes
-- `image_derivative`. Read docs/plans/09_image-processing.md.

CREATE TABLE image (
    sha256    TEXT PRIMARY KEY
              CHECK (length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'),
    folder    TEXT NOT NULL CHECK (folder IN ('main', 'patched', 'additional', 'cropped')),
    extension TEXT NOT NULL CHECK (extension <> '' AND extension NOT GLOB '*[^0-9a-z]*'),
    width     INTEGER CHECK (width > 0),
    height    INTEGER CHECK (height > 0),
    CHECK ((width IS NULL) = (height IS NULL))
) STRICT;

INSERT INTO image (sha256, folder, extension, width, height)
SELECT sha256,
       CASE min(CASE image_type WHEN 'main' THEN 1 WHEN 'main_patched' THEN 2 ELSE 3 END)
           WHEN 1 THEN 'main' WHEN 2 THEN 'patched' ELSE 'additional' END,
       min(extension), max(width), max(height)
FROM wine_image
GROUP BY sha256;

CREATE TABLE wine_image_007 (
    wine_slug    TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    image_type   TEXT NOT NULL
                 CHECK (image_type IN ('main', 'main_patched', 'front', 'back',
                                       'label_front', 'label_back')),
    sha256       TEXT NOT NULL REFERENCES image (sha256),
    source_name  TEXT NOT NULL CHECK (source_name <> ''),
    match_method TEXT NOT NULL CHECK (match_method <> ''),
    PRIMARY KEY (wine_slug, image_type, sha256)
) STRICT;

INSERT INTO wine_image_007 (wine_slug, image_type, sha256, source_name, match_method)
SELECT wine_slug, image_type, sha256, source_name, match_method FROM wine_image;

DROP TABLE wine_image;

ALTER TABLE wine_image_007 RENAME TO wine_image;

-- A wine has at most one `main` image and at most one `main_patched` image.
CREATE UNIQUE INDEX wine_image_one_main ON wine_image (wine_slug, image_type)
    WHERE image_type IN ('main', 'main_patched');

CREATE TABLE image_derivative (
    source_sha256 TEXT PRIMARY KEY REFERENCES image (sha256),
    method        TEXT NOT NULL CHECK (method IN ('crop', 'seg')),
    settings      TEXT NOT NULL CHECK (settings <> ''),
    sha256        TEXT NOT NULL REFERENCES image (sha256),
    box_left      INTEGER NOT NULL,
    box_top       INTEGER NOT NULL,
    box_right     INTEGER NOT NULL,
    box_bottom    INTEGER NOT NULL,
    CHECK (box_left >= 0 AND box_top >= 0 AND box_right > box_left
           AND box_bottom > box_top)
) STRICT;
