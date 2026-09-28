-- 030: the free-form text tags of an image (plan 66).
--
-- One row is one tag of one image. The key is the SHA-256 of the bytes, so each copy of
-- the image shows the same tags: each test photo of each set and each place that holds
-- the bytes. The owner chose this on 2026-09-27T23:53:00+0300. One image MAY have more
-- than one tag. The rowid order is the order of the adds.
--   tag         the normal form of `wine_tags.normal` (plan 63): no outer white space,
--               lower case, only letters, digits, `_`, `-`, `:`, and `.`. The module
--               checks the form. The CHECK holds the length alone.
--   created_at  the UTC time of the add, to the second, in ISO 8601 with `Z`, as
--               `wine_tag.created_at`.
-- The Testset page writes the tags. The pipeline does not read them.
--
-- No code deletes a row of `image`. The foreign key blocks `DROP TABLE image` while this
-- table holds rows. A later schema file that builds `image` again MUST handle this table
-- too. Read docs/plans/66_testset-image-tags.md.

CREATE TABLE image_tag (
    sha256     TEXT NOT NULL REFERENCES image (sha256),
    tag        TEXT NOT NULL CHECK (tag <> '' AND length(tag) <= 64),
    created_at TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    PRIMARY KEY (sha256, tag)
) STRICT;
