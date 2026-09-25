-- 017: one processed file for each original and kind of cut.
--
-- `kind` names the cut:
--   package  the cut of the whole package: derive.py (crop or SAM3 package)
--   label    the cut of the label: alternatives.py and seed_label_cuts.py (SAM3 label)
-- One file can be a `main`, a patch, or a full type (package cut) and a label type (label
-- cut) at the same time, and a full image can have both cuts for the Embeddings page. So
-- the key is (source_sha256, kind). The owner chose this on 2026-09-25T12:28:04+0300. Read
-- docs/plans/16_alternative-images.md and docs/reviews/2026-09-25_unfinished-work.md.
--
-- The rows of 007 are package cuts, except the label cuts of alternatives.py: their
-- settings name "the largest label that is not the package (build_labels.py)". The
-- default of `kind` is `package`, so an old writer that names no kind writes a package
-- cut. SQLite cannot change a primary key, so this file builds the table again. No table
-- references `image_derivative`.

CREATE TABLE image_derivative_new (
    source_sha256 TEXT NOT NULL REFERENCES image (sha256),
    method        TEXT NOT NULL CHECK (method IN ('crop', 'seg')),
    settings      TEXT NOT NULL CHECK (settings <> ''),
    sha256        TEXT NOT NULL REFERENCES image (sha256),
    box_left      INTEGER NOT NULL,
    box_top       INTEGER NOT NULL,
    box_right     INTEGER NOT NULL,
    box_bottom    INTEGER NOT NULL,
    kind          TEXT NOT NULL DEFAULT 'package' CHECK (kind IN ('package', 'label')),
    PRIMARY KEY (source_sha256, kind),
    CHECK (box_left >= 0 AND box_top >= 0 AND box_right > box_left
           AND box_bottom > box_top)
) STRICT;

INSERT INTO image_derivative_new (source_sha256, method, settings, sha256, box_left,
                                  box_top, box_right, box_bottom, kind)
SELECT source_sha256, method, settings, sha256, box_left, box_top, box_right, box_bottom,
       CASE WHEN settings LIKE '%the largest label that is not the package (build_labels.py)%'
            THEN 'label' ELSE 'package' END
FROM image_derivative;

DROP TABLE image_derivative;

ALTER TABLE image_derivative_new RENAME TO image_derivative;
