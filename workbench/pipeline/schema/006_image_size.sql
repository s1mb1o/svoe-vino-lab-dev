-- 006: the pixel size of an image.
--
-- `width` and `height` are the size of the stored file in pixels. NULL means that no
-- tool measured the file yet. pipeline/seed_images.py writes both for each `main` row,
-- and it fills them for an old row with NULL. The Dataset page sorts by
-- `width * height`.
--
-- The columns MAY be NULL, so a tool that does not know them yet can still add a row.
-- Like `extension`, both depend on the file alone. A flatten of the schema MAY make them
-- NOT NULL. Read docs/plans/08_seed-images.md.

ALTER TABLE wine_image ADD COLUMN width INTEGER CHECK (width > 0);

ALTER TABLE wine_image ADD COLUMN height INTEGER CHECK (height > 0);
