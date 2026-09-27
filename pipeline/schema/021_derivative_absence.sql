-- 021: a deliberate absence of an image derivative.
--
-- A packet or a box can have its design printed on the package. Such a package has no
-- separate label. Its full-package vector is sufficient, so the label derivative and
-- the label vector are not applicable. This table distinguishes that state from a
-- failed label segmentation. Read docs/plans/22_label-cut.md.

CREATE TABLE image_derivative_absence (
    source_sha256 TEXT NOT NULL REFERENCES image (sha256),
    kind          TEXT NOT NULL CHECK (kind IN ('package', 'label')),
    settings      TEXT NOT NULL CHECK (settings <> ''),
    reason        TEXT NOT NULL CHECK (reason <> ''),
    PRIMARY KEY (source_sha256, kind)
) STRICT;
