CREATE TABLE wine_code (
    wine_slug TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    kind      TEXT NOT NULL CHECK (kind IN ('gtin', 'barcode', 'qr_url')),
    value     TEXT NOT NULL CHECK (value <> ''), modified_at TEXT
    CHECK (modified_at GLOB
           '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    PRIMARY KEY (wine_slug, kind, value),
    CHECK (kind <> 'gtin'
           OR (length(value) = 14 AND value NOT GLOB '*[^0-9]*')),
    CHECK (kind <> 'barcode' OR length(value) <= 128),
    CHECK (kind <> 'qr_url'
           OR (length(value) <= 4096
               AND (value GLOB 'http://?*' OR value GLOB 'https://?*')))
) STRICT;

CREATE TABLE wine_comment (
    id         INTEGER PRIMARY KEY,
    wine_slug  TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    created_at TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    source     TEXT NOT NULL CHECK (source IN ('user', 'script')),
    text       TEXT NOT NULL CHECK (text <> '' AND length(text) <= 4000)
) STRICT;

CREATE TABLE "wine_image" (
    wine_slug    TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    image_type   TEXT NOT NULL
                 CHECK (image_type IN ('main', 'main_patched', 'full_front', 'label_front',
                                       'full_back', 'label_back')),
    sha256       TEXT NOT NULL REFERENCES image (sha256),
    source_name  TEXT NOT NULL CHECK (source_name <> ''),
    match_method TEXT NOT NULL CHECK (match_method <> ''),
    PRIMARY KEY (wine_slug, image_type, sha256)
) STRICT;

CREATE TABLE wine_favorite (
    wine_slug  TEXT PRIMARY KEY REFERENCES wine_catalog (wine_slug),
    created_at TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z')
) STRICT;

CREATE TABLE "wine_catalog" (
    wine_slug      TEXT PRIMARY KEY CHECK (wine_slug <> ''),           -- Slug
    name           TEXT NOT NULL    CHECK (name <> ''),                -- Название вина
    producer       TEXT NOT NULL    CHECK (producer <> ''),            -- Винодельня
    category       TEXT NOT NULL    CHECK (category <> ''),            -- Категория
    color          TEXT NOT NULL    CHECK (color <> ''),               -- Цвет
    region         TEXT NOT NULL    CHECK (region <> ''),              -- Регион
    grapes         TEXT             CHECK (grapes <> ''),              -- Сорт винограда
    description    TEXT             CHECK (description <> ''),         -- Описание
    csv_photo_name TEXT NOT NULL    CHECK (csv_photo_name <> ''),      -- Название фото
    state          TEXT NOT NULL DEFAULT 'Active'
                   CHECK (state IN ('Active', 'Disabled', 'Removed')),
    removed_by     TEXT CHECK (removed_by IN ('import', 'person')), website_modified_at TEXT
    CHECK (website_modified_at <> ''), modified_at TEXT
    CHECK (modified_at GLOB
           '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'), name_patched TEXT CHECK (name_patched <> ''),
    CHECK ((state = 'Removed') = (removed_by IS NOT NULL))
) STRICT;

CREATE TABLE website_refusal (
    wine_slug     TEXT NOT NULL CHECK (wine_slug <> ''),
    kind          TEXT NOT NULL
                  CHECK (kind IN ('text', 'image', 'new', 'missing', 'back', 'main')),
    field         TEXT NOT NULL DEFAULT '',
    website_value TEXT,
    created_at    TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    PRIMARY KEY (wine_slug, kind, field),
    CHECK ((kind = 'text') = (field <> ''))
) STRICT;

CREATE TABLE "image" (
    sha256    TEXT PRIMARY KEY
              CHECK (length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'),
    folder    TEXT NOT NULL
              CHECK (folder IN ('main', 'patched', 'additional', 'cropped', 'testset')),
    extension TEXT NOT NULL CHECK (extension <> '' AND extension NOT GLOB '*[^0-9a-z]*'),
    width     INTEGER CHECK (width > 0),
    height    INTEGER CHECK (height > 0),
    CHECK ((width IS NULL) = (height IS NULL))
) STRICT;

CREATE TABLE test_set (
    set_name   TEXT PRIMARY KEY CHECK (set_name <> '' AND set_name NOT GLOB '*[^0-9a-z_-]*'),
    source_dir TEXT NOT NULL CHECK (source_dir <> '')
, edited_at TEXT CHECK (edited_at <> ''), label_note TEXT) STRICT;

CREATE TABLE test_variant (
    set_name  TEXT NOT NULL REFERENCES test_set (set_name),
    wine_slug TEXT NOT NULL CHECK (wine_slug <> ''),
    group_no  INTEGER NOT NULL CHECK (group_no >= 0),
    PRIMARY KEY (set_name, wine_slug)
) STRICT;

CREATE TABLE "image_derivative" (
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
    vlm_attempts  INTEGER NOT NULL DEFAULT 0 CHECK (vlm_attempts >= 0), presentation_mode TEXT
    CHECK (presentation_mode IN ('on_package', 'flat_surface', 'other', 'unknown')),
    CHECK ((vlm_at IS NULL) = (vlm_answer IS NULL))
) STRICT;

CREATE TABLE "test_photo" (
    set_name       TEXT NOT NULL REFERENCES test_set (set_name),
    place          TEXT NOT NULL CHECK (place <> ''),
    file_name      TEXT NOT NULL CHECK (file_name <> ''),
    sha256         TEXT NOT NULL REFERENCES image (sha256),
    label          TEXT CHECK (label IN ('positive', 'negative', 'unusable', 'variant')),
    marked_delete  INTEGER NOT NULL DEFAULT 0 CHECK (marked_delete IN (0, 1)),
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

CREATE TABLE image_derivative_absence (
    source_sha256 TEXT NOT NULL REFERENCES image (sha256),
    kind          TEXT NOT NULL CHECK (kind IN ('package', 'label')),
    settings      TEXT NOT NULL CHECK (settings <> ''),
    reason        TEXT NOT NULL CHECK (reason <> ''),
    PRIMARY KEY (source_sha256, kind)
) STRICT;

CREATE TABLE test_photo_comment (
    id         INTEGER PRIMARY KEY,
    set_name   TEXT NOT NULL,
    place      TEXT NOT NULL,
    file_name  TEXT NOT NULL,
    created_at TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    source     TEXT NOT NULL CHECK (source IN ('user', 'script')),
    text       TEXT NOT NULL CHECK (text <> '' AND length(text) <= 4000),
    FOREIGN KEY (set_name, place, file_name)
        REFERENCES test_photo (set_name, place, file_name)
        ON UPDATE CASCADE ON DELETE CASCADE
) STRICT;

CREATE TABLE wine_beverage_type (
    wine_slug          TEXT PRIMARY KEY REFERENCES wine_catalog (wine_slug),
    beverage_type_code TEXT NOT NULL CHECK (beverage_type_code IN ('4', '44')),
    updated_at         TEXT NOT NULL CHECK (updated_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z')
) STRICT;

CREATE TABLE "wine_atlas_binding" (
    wine_slug    TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    source       TEXT NOT NULL CHECK (source IN ('automatic', 'manual')),
    product_uuid TEXT NOT NULL CHECK (length(product_uuid) = 36
        AND product_uuid NOT GLOB '*[^0-9a-f-]*'
        AND product_uuid GLOB '????????-????-????-????-????????????'),
    PRIMARY KEY (wine_slug, product_uuid)
) STRICT;

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

CREATE TABLE image_label_description_failure (
    sha256     TEXT PRIMARY KEY REFERENCES image (sha256),
    attempts   INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    error      TEXT,
    updated_at TEXT NOT NULL CHECK (updated_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z')
) STRICT;

CREATE TABLE wine_similar (
    wine_slug_a TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    wine_slug_b TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    created_at  TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    PRIMARY KEY (wine_slug_a, wine_slug_b),
    CHECK (wine_slug_a < wine_slug_b)
) STRICT;

CREATE TABLE wine_tag (
    wine_slug  TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    tag        TEXT NOT NULL CHECK (tag <> '' AND length(tag) <= 64),
    created_at TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    PRIMARY KEY (wine_slug, tag)
) STRICT;

CREATE TABLE image_tag (
    sha256     TEXT NOT NULL REFERENCES image (sha256),
    tag        TEXT NOT NULL CHECK (tag <> '' AND length(tag) <= 64),
    created_at TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    PRIMARY KEY (sha256, tag)
) STRICT;

