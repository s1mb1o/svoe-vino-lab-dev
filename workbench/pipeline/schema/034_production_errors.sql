-- Reviewed production images. Feedback and predictions are evidence, not labels.
CREATE TABLE production_error (
    source TEXT NOT NULL,
    request_id TEXT NOT NULL,
    image_sha256 TEXT NOT NULL CHECK (length(image_sha256) = 64),
    extension TEXT NOT NULL,
    candidates_json TEXT NOT NULL CHECK (json_valid(candidates_json)),
    feedback_json TEXT NOT NULL CHECK (json_valid(feedback_json)),
    imported_at TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','reviewed','rejected','published')),
    identity TEXT,
    purpose TEXT CHECK (purpose IN ('reference','benchmark')),
    reviewer TEXT,
    review_note TEXT,
    destination TEXT,
    PRIMARY KEY (source, request_id)
) STRICT;
CREATE INDEX production_error_image ON production_error(image_sha256);
CREATE TABLE production_error_review (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    request_id TEXT NOT NULL,
    at TEXT NOT NULL,
    review_json TEXT NOT NULL CHECK (json_valid(review_json)),
    FOREIGN KEY(source, request_id) REFERENCES production_error(source, request_id)
) STRICT;
