-- 018: the descriptions of the images.
--
-- One row describes one image file of `image`. The watcher `pipeline/describe_images.py`
-- fills the rows with a VLM; the owner sets values by hand on `/dataset`.
--   package_type, subject_scope, package_view   one value of the set, or NULL (not set)
--   content_roles  a JSON list of 1 to 2 values, or NULL (not set); `unknown` stands
--                  alone. `pipeline/image_descriptions.py` checks the list.
--   created_by     who made the row: 'vlm' (the watcher) or 'manual' (the owner, before
--                  the VLM)
--   vlm_at         NULL until the VLM filled the row. The VLM fills only the NULL values,
--                  so a value that is set is never overwritten.
--   vlm_name       the name of the `vlm` entry of the configuration
--   vlm_model      the model name that the service reported
--   vlm_answer     the full valid answer of the VLM, as JSON
--   vlm_error      the last failure; NULL after a success
--   vlm_attempts   the failed calls; the watcher stops at `image_description.max_attempts`
-- The times are UTC, to the second, in ISO 8601 with `Z`, as `wine_comment.created_at`.
--
-- The foreign key blocks `DROP TABLE image` while this table holds rows. A later schema
-- file that builds `image` again MUST handle this table too.
-- Read docs/plans/26_image-description.md.

CREATE TABLE image_description (
    sha256        TEXT PRIMARY KEY REFERENCES image (sha256),
    package_type  TEXT CHECK (package_type IN ('bottle', 'can', 'keg', 'bag', 'bag_in_box',
                      'tetra_pak', 'barrel', 'decanter', 'box', 'other', 'unknown')),
    subject_scope TEXT CHECK (subject_scope IN ('full_package', 'label_closeup',
                      'multiple_packages', 'unknown')),
    package_view  TEXT CHECK (package_view IN ('front', 'back', 'unknown')),
    content_roles TEXT CHECK (content_roles IS NULL OR (json_valid(content_roles)
                      AND json_type(content_roles) = 'array')),
    created_by    TEXT NOT NULL CHECK (created_by IN ('vlm', 'manual')),
    created_at    TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    updated_at    TEXT NOT NULL CHECK (updated_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    vlm_at        TEXT CHECK (vlm_at IS NULL OR vlm_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    vlm_name      TEXT,
    vlm_model     TEXT,
    vlm_answer    TEXT CHECK (vlm_answer IS NULL OR json_valid(vlm_answer)),
    vlm_error     TEXT,
    vlm_attempts  INTEGER NOT NULL DEFAULT 0 CHECK (vlm_attempts >= 0),
    CHECK ((vlm_at IS NULL) = (vlm_answer IS NULL))
) STRICT;
