-- NNN: the test sets and the labels of their photos.
--
-- The number of this file is fixed when it enters pipeline/schema/ (rules 25 to 28 of
-- AGENTS.md). Read docs/plans/12_testsets-benchmark.md.
--
-- A test set is a photo set of dataset/<set>/. The labels stay in
-- dataset/<set>/review-labels.json, in git. pipeline/import_testset.py copies them here
-- read-only, and each import makes the rows of the set equal to the files again. The
-- owner chose per-set labels on 2026-09-25: the same photo can hold another label in
-- another set. The bytes of a photo are stored one time.
--
-- A test photo is a row of `image` and a file of the flat image store. The file enters
-- pipeline/schema/ after the file of the flat store of drink-atlas-workspace-9a [f028b4],
-- which drops the column `image.folder`. This file does not change `image`.

-- One row per test set. `source_dir` is the directory of the last import.
CREATE TABLE test_set (
    set_name   TEXT PRIMARY KEY CHECK (set_name <> '' AND set_name NOT GLOB '*[^0-9a-z_-]*'),
    source_dir TEXT NOT NULL CHECK (source_dir <> '')
) STRICT;

-- One photo file in one set. `place` is the name of its directory: a wine slug, or
-- `__null__` for a photo that matches no card of the catalogue. `label` is NULL when the
-- photo has no label yet. `marked_delete` is the field `delete` of the label entry.
CREATE TABLE test_photo (
    set_name      TEXT NOT NULL REFERENCES test_set (set_name),
    place         TEXT NOT NULL CHECK (place <> ''),
    file_name     TEXT NOT NULL CHECK (file_name <> ''),
    sha256        TEXT NOT NULL REFERENCES image (sha256),
    label         TEXT CHECK (label IN ('positive', 'negative', 'unusable', 'variant')),
    marked_delete INTEGER NOT NULL DEFAULT 0 CHECK (marked_delete IN (0, 1)),
    PRIMARY KEY (set_name, place, file_name)
) STRICT;

-- An excluded slug of one set. The photos of an excluded slug are out of the benchmark.
CREATE TABLE test_excluded (
    set_name  TEXT NOT NULL REFERENCES test_set (set_name),
    wine_slug TEXT NOT NULL CHECK (wine_slug <> ''),
    reason    TEXT,
    ts        TEXT,
    PRIMARY KEY (set_name, wine_slug)
) STRICT;

-- The variant group of a slug in one set. `group_no` is the position of the group in
-- variant-groups.json. The metric `near_duplicate_confusion` reads the groups.
CREATE TABLE test_variant (
    set_name  TEXT NOT NULL REFERENCES test_set (set_name),
    wine_slug TEXT NOT NULL CHECK (wine_slug <> ''),
    group_no  INTEGER NOT NULL CHECK (group_no >= 0),
    PRIMARY KEY (set_name, wine_slug)
) STRICT;
