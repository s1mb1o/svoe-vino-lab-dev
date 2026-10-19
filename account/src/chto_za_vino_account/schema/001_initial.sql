-- Accounts, login identities, sessions, and short-lived login state.
-- Times are UTC Unix seconds.

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL,
    consent_version TEXT NOT NULL,
    consent_at INTEGER NOT NULL,
    terms_version TEXT NOT NULL,
    terms_at INTEGER NOT NULL
);

-- One identity per provider and user. A subject belongs to one user at most.
-- email: the normalized address; yandex: the Yandex ID "id"; max and telegram: the user ID.
CREATE TABLE identities (
    provider TEXT NOT NULL CHECK (provider IN ('email', 'yandex', 'max', 'telegram')),
    subject TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    linked_at INTEGER NOT NULL,
    PRIMARY KEY (provider, subject),
    UNIQUE (user_id, provider)
);

CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    auth_method TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    auth_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    extended_at INTEGER NOT NULL
);
CREATE INDEX sessions_user ON sessions (user_id);

-- The challenge ID is a secret that only the requesting browser holds (httpOnly cookie).
CREATE TABLE email_challenges (
    id_hash TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    code_mac TEXT NOT NULL,
    purpose TEXT NOT NULL CHECK (purpose IN ('login', 'link')),
    user_id TEXT REFERENCES users (id) ON DELETE CASCADE,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    used_at INTEGER
);

CREATE TABLE oauth_flows (
    id_hash TEXT PRIMARY KEY,
    provider TEXT NOT NULL CHECK (provider IN ('yandex')),
    state TEXT NOT NULL,
    code_verifier TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    purpose TEXT NOT NULL CHECK (purpose IN ('login', 'link')),
    user_id TEXT REFERENCES users (id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    used_at INTEGER
);

-- A proven identity without an account. Sign-up completes it with a username and consents.
CREATE TABLE signup_tickets (
    token_hash TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    subject TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    used_at INTEGER
);

CREATE TABLE link_codes (
    code_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('telegram')),
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    used_at INTEGER
);

-- MAX launch IDs (query_id) that were already exchanged.
CREATE TABLE used_launches (
    query_id TEXT PRIMARY KEY,
    expires_at INTEGER NOT NULL
);
