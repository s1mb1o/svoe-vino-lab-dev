-- Application tokens for MCP clients (issue #65). A token reads only its owner's diary data.
-- The service keeps only the SHA-256 hash. A token never opens a web session.
CREATE TABLE app_tokens (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    last_used_at INTEGER,
    revoked_at INTEGER
);
CREATE INDEX app_tokens_user ON app_tokens (user_id);
