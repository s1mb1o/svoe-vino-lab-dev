-- Versioned observations and jobs. Source metadata and prior descriptions stay intact.
CREATE TABLE image_attribute_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    active_version TEXT NOT NULL DEFAULT 'attributes-v1',
    heartbeat_at TEXT,
    paused INTEGER NOT NULL DEFAULT 0 CHECK (paused IN (0,1))
) STRICT;
INSERT INTO image_attribute_settings(id) VALUES (1);
-- Snapshot image identities. Link rowids can be reused and are not image identities.
CREATE TABLE image_attribute_baseline (
    sha256 TEXT NOT NULL REFERENCES image(sha256),
    input_sha256 TEXT NOT NULL,
    PRIMARY KEY(sha256,input_sha256)
) STRICT;
INSERT INTO image_attribute_baseline
SELECT DISTINCT w.sha256,coalesce(d.sha256,w.sha256) FROM wine_image w
LEFT JOIN image_derivative d ON d.source_sha256=w.sha256 AND d.kind='package'
WHERE w.image_type IN ('main','main_patched');
CREATE TABLE image_attribute_facts (
    id INTEGER PRIMARY KEY,
    sha256 TEXT NOT NULL REFERENCES image(sha256),
    input_sha256 TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    facts TEXT NOT NULL CHECK (json_valid(facts) AND json_type(facts) = 'object'),
    source TEXT NOT NULL CHECK (source IN ('description', 'vlm')),
    model TEXT,
    created_at TEXT NOT NULL
) STRICT;
CREATE INDEX image_attribute_observation ON image_attribute_facts(sha256,input_sha256,extractor_version,id);
CREATE TABLE image_attribute_job (
    sha256 TEXT NOT NULL REFERENCES image(sha256),
    input_sha256 TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('cached','image')),
    state TEXT NOT NULL CHECK (state IN ('pending','running','ready','failed')),
    generation INTEGER NOT NULL DEFAULT 1,
    attempts INTEGER NOT NULL DEFAULT 0,
    facts_id INTEGER REFERENCES image_attribute_facts(id),
    error TEXT,
    requested_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(sha256,input_sha256,extractor_version)
) STRICT;
CREATE INDEX image_attribute_job_pending ON image_attribute_job(extractor_version,state,requested_at);
