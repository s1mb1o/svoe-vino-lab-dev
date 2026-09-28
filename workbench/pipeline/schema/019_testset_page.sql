-- 019: the fields of the Testset page.
--
-- The number 019 was fixed at the entry on 2026-09-25 (rules 25 to 28 of AGENTS.md). Read
-- docs/plans/24_testset-page.md.
--
-- The database is the source of the labels of a test set now. The owner chose this on
-- 2026-09-25T12:40:00+0300. So `test_photo` keeps each field of a label entry of
-- review-labels.json, and pipeline/export_testset.py writes the JSON files again from
-- the rows.
--
-- `test_photo` is built again, because the box of the main object needs a CHECK over
-- four columns, and SQLite cannot add such a CHECK to a table. No table references
-- `test_photo`, so the rebuild changes no link. The file keeps each row. The new columns
-- stay NULL until the next import of the set.
--
-- The columns of a label entry (column: the JSON field):
--   comment         comment         the comment of the photo, 1 to 4,000 characters
--   ts              ts              the time of the last change of the entry
--   proposed        proposed        the label that an agent proposed
--   proposed_by     by              the agent that proposed it; `by` is an SQL keyword
--   confidence      confidence      the confidence of the proposal
--   source_url      source_url      the page where the photo was found
--   moved_from      moved_from      the place of the photo before a move
--   copied_from     copied_from     the place of the photo before a copy
--   reassign_to     reassign_to     a move that waits for `apply`; read-only on the page
--   prefilled_from  prefilled_from  the object of a prefilled label, as JSON text
--   extra           each other field, as a JSON object. A field whose value its column
--                   cannot keep exactly goes here too, for example `null`.
--   box_left, box_top, box_right, box_bottom   box, the box of the main object
-- The box is in the pixels of the photo after its EXIF orientation. The four values are
-- all NULL or all set. pipeline/testsets.py checks that the box is inside the photo.

CREATE TABLE test_photo_new (
    set_name       TEXT NOT NULL REFERENCES test_set (set_name),
    place          TEXT NOT NULL CHECK (place <> ''),
    file_name      TEXT NOT NULL CHECK (file_name <> ''),
    sha256         TEXT NOT NULL REFERENCES image (sha256),
    label          TEXT CHECK (label IN ('positive', 'negative', 'unusable', 'variant')),
    marked_delete  INTEGER NOT NULL DEFAULT 0 CHECK (marked_delete IN (0, 1)),
    comment        TEXT CHECK (comment <> '' AND length(comment) <= 4000),
    ts             TEXT CHECK (ts <> ''),
    proposed       TEXT CHECK (proposed IN ('positive', 'negative', 'unusable', 'variant')),
    proposed_by    TEXT CHECK (proposed_by <> ''),
    confidence     REAL,
    source_url     TEXT CHECK (source_url <> ''),
    moved_from     TEXT CHECK (moved_from <> ''),
    copied_from    TEXT CHECK (copied_from <> ''),
    reassign_to    TEXT CHECK (reassign_to <> ''),
    prefilled_from TEXT CHECK (json_valid(prefilled_from)
                               AND json_type(prefilled_from) = 'object'),
    extra          TEXT CHECK (json_valid(extra) AND json_type(extra) = 'object'),
    box_left       INTEGER,
    box_top        INTEGER,
    box_right      INTEGER,
    box_bottom     INTEGER,
    CHECK ((box_left IS NULL) = (box_top IS NULL) AND (box_left IS NULL) = (box_right IS NULL)
           AND (box_left IS NULL) = (box_bottom IS NULL)),
    CHECK (box_left IS NULL OR (box_left >= 0 AND box_top >= 0 AND box_right > box_left
                                AND box_bottom > box_top)),
    PRIMARY KEY (set_name, place, file_name)
) STRICT;

INSERT INTO test_photo_new (set_name, place, file_name, sha256, label, marked_delete)
SELECT set_name, place, file_name, sha256, label, marked_delete FROM test_photo;

DROP TABLE test_photo;

ALTER TABLE test_photo_new RENAME TO test_photo;

-- The note of a whole wine in one set: the map `wines` of review-labels.json. The key of
-- the map is the wine slug. `extra` holds each other field of the note, as for
-- `test_photo`.
CREATE TABLE test_wine_note (
    set_name  TEXT NOT NULL REFERENCES test_set (set_name),
    wine_slug TEXT NOT NULL CHECK (wine_slug <> ''),
    comment   TEXT CHECK (comment <> '' AND length(comment) <= 4000),
    ts        TEXT CHECK (ts <> ''),
    extra     TEXT CHECK (json_valid(extra) AND json_type(extra) = 'object'),
    PRIMARY KEY (set_name, wine_slug)
) STRICT;

-- `edited_at`: the time of the last write of the Testset page to the set. NULL means no
-- page edit, so a new import of the set changes no work of a person.
-- `label_note`: the text `note` of review-labels.json. The export writes it again.
ALTER TABLE test_set ADD COLUMN edited_at TEXT CHECK (edited_at <> '');
ALTER TABLE test_set ADD COLUMN label_note TEXT;
