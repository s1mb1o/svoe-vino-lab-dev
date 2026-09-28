-- 005: the images of a wine.
--
-- One row links one wine, one image type, and one stored file. The file is
-- `images/<folder>/<sha256>.<extension>` in the directory of the database file. The
-- folder follows from `image_type`:
--   main                                  -> main
--   main_patched                          -> patched
--   front, back, label_front, label_back  -> additional
-- `main` is the main image of the wine page on vino-svoe.ru. The source is the Strapi
-- `uploads` folder of a delivery. `main_patched` is the fix of a bad `main` image. A
-- reader MUST use `main_patched` instead of `main` when a wine has both. The other
-- types are extra views for training.
-- The photos of a test set are not in this table. They get their own table later.
--
-- `source_name` is the file name at the source. For `main` it is the upload file name,
-- the value of `upload_file` in `catalog.jsonl`.
-- `match_method` states how the file was found for the wine. pipeline/seed_images.py
-- writes `name-unique` and `name-identical`.
--
-- The owner chose one table on 2026-09-24. `extension` depends on the file alone, not
-- on the whole key, so this table is not in BCNF. A file that several wines share has
-- one row for each wine.
--
-- The foreign key blocks `DROP TABLE wine_catalog` while this table holds rows. A later
-- schema file that builds `wine_catalog` again MUST handle this table too.
-- pipeline/seed_images.py fills the type `main`. Read docs/plans/08_seed-images.md.

CREATE TABLE wine_image (
    wine_slug    TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    image_type   TEXT NOT NULL
                 CHECK (image_type IN ('main', 'main_patched', 'front', 'back',
                                       'label_front', 'label_back')),
    sha256       TEXT NOT NULL
                 CHECK (length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'),
    extension    TEXT NOT NULL
                 CHECK (extension <> '' AND extension NOT GLOB '*[^0-9a-z]*'),
    source_name  TEXT NOT NULL CHECK (source_name <> ''),
    match_method TEXT NOT NULL CHECK (match_method <> ''),
    PRIMARY KEY (wine_slug, image_type, sha256)
) STRICT;

-- A wine has at most one `main` image and at most one `main_patched` image.
CREATE UNIQUE INDEX wine_image_one_main ON wine_image (wine_slug, image_type)
    WHERE image_type IN ('main', 'main_patched');
