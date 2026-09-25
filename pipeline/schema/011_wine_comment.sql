-- 011: the timestamped comments of a wine.
--
-- One row is one comment on one wine. One wine MAY have more than one
-- comment. Two comments MAY hold the same text, so a remove names the `id`.
--   created_at  the UTC time of the write, to the second, in ISO 8601 with `Z`. The
--               string order is the time order. Two comments of the same second keep
--               the `id` order.
--   source      the writer: `user` for a person on the Dataset page, `script` for a
--               script. The owner chose the two values on 2026-09-25.
--   text        the text of the comment, with its line breaks. pipeline/comments.py
--               checks the rest: the white space and the control characters.
-- A comment has no edit. The owner chose a separate table on 2026-09-25.
--
-- The foreign key blocks `DROP TABLE wine_catalog` while this table holds rows. A later
-- schema file that builds `wine_catalog` again MUST handle this table too.
-- Read docs/plans/17_wine-comments.md.

CREATE TABLE wine_comment (
    id         INTEGER PRIMARY KEY,
    wine_slug  TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    created_at TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    source     TEXT NOT NULL CHECK (source IN ('user', 'script')),
    text       TEXT NOT NULL CHECK (text <> '' AND length(text) <= 4000)
) STRICT;

-- The comments of one wine in time order.
CREATE INDEX wine_comment_wine ON wine_comment (wine_slug, created_at, id);
