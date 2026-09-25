-- Plan 29: the detail of each image, the answer of the detail prompt of stage 2 of the
-- watcher `describe_images.py`. Read `docs/plans/29_image-details.md`.
--
-- One row describes one original. The three input columns hold the inputs of the last
-- call. When the wanted inputs of the image differ from them, the row is stale and the
-- watcher sends the image again.
CREATE TABLE image_detail (
    sha256        TEXT PRIMARY KEY REFERENCES image (sha256),  -- the original
    prompt_kind   TEXT NOT NULL CHECK (prompt_kind IN ('package', 'label')),
    package_type  TEXT NOT NULL,
    input_sha256  TEXT NOT NULL REFERENCES image (sha256),     -- the file that the VLM got
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    -- NULL: no valid answer for these inputs yet.
    vlm_at        TEXT,
    vlm_name      TEXT,     -- the name of the `vlm` entry
    vlm_model     TEXT,     -- the model name that the service reported
    answer        TEXT CHECK (answer IS NULL OR json_valid(answer)),
    vlm_error     TEXT,     -- the last failure, NULL after a success
    vlm_attempts  INTEGER NOT NULL DEFAULT 0 CHECK (vlm_attempts >= 0)
) STRICT;
