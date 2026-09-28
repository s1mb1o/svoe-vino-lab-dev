-- 027: the label descriptions of the images (plan 61).
--
-- One row is one label description of one linked image: the answer of
-- `label_rules.DESCRIBE_PROMPT` (stage 3 of the watcher `pipeline/describe_images.py`),
-- or a copy of a description that the owner edited on `/dataset`. One image can have many
-- rows. The latest row (the newest `created_at`, then the higher `id`) is the effective
-- description. The watcher sends no request for an image that has a row.
--   description      the JSON object, after the key repair of `label_descriptions.repair`
--   created_by       'vlm' (the watcher) or 'manual' (the owner)
--   vlm_name         the name of the `vlm` entry; NULL in a manual row, as each vlm_* column
--   vlm_endpoint     the chat URL of the request
--   vlm_model        the model name of the request
--   vlm_served_model the model name that the service reported
--   max_tokens       `max_tokens` of the request that gave the answer
--   thinking         1 when the request turned thinking on, else 0
--   input_sha256     the file that the VLM got: the `package` cut, else the original. It
--                    has no foreign key, because a new cut can replace the file.
--   vlm_request      the other settings of the request, as JSON
--   vlm_reply        `finish_reason`, `usage`, `ms`, `cached`, `loop_guard`, `repairs`, and
--                    `raw` (the answer text) of the call, as JSON
--
-- `image_label_description_failure` counts the failed calls of an image that has no row.
-- The watcher stops at `image_description.max_attempts` failures. The removal of the last
-- row of an image removes its failure row too, so the image waits again.
--
-- The times are UTC, to the second, in ISO 8601 with `Z`, as `wine_comment.created_at`.
-- The foreign keys block `DROP TABLE image` while these tables hold rows. A later schema
-- file that builds `image` again MUST handle these tables too.
-- Read docs/plans/61_label-descriptions.md.

CREATE TABLE image_label_description (
    id               INTEGER PRIMARY KEY,
    sha256           TEXT NOT NULL REFERENCES image (sha256),
    description      TEXT NOT NULL CHECK (json_valid(description)
                         AND json_type(description) = 'object'),
    created_by       TEXT NOT NULL CHECK (created_by IN ('vlm', 'manual')),
    created_at       TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    vlm_name         TEXT,
    vlm_endpoint     TEXT,
    vlm_model        TEXT,
    vlm_served_model TEXT,
    max_tokens       INTEGER CHECK (max_tokens IS NULL OR max_tokens > 0),
    thinking         INTEGER CHECK (thinking IS NULL OR thinking IN (0, 1)),
    input_sha256     TEXT,
    vlm_request      TEXT CHECK (vlm_request IS NULL OR json_valid(vlm_request)),
    vlm_reply        TEXT CHECK (vlm_reply IS NULL OR json_valid(vlm_reply)),
    CHECK ((created_by = 'vlm') = (vlm_name IS NOT NULL))
) STRICT;

CREATE INDEX image_label_description_image ON image_label_description (sha256, created_at);

CREATE TABLE image_label_description_failure (
    sha256     TEXT PRIMARY KEY REFERENCES image (sha256),
    attempts   INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    error      TEXT,
    updated_at TEXT NOT NULL CHECK (updated_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z')
) STRICT;
