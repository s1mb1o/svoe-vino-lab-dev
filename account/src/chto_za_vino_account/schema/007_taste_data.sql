-- Stated preferences and tasting ratings are independent of history and saved wines.
ALTER TABLE users ADD COLUMN preferences TEXT;

CREATE TABLE wine_ratings (
    user_id TEXT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    wine_slug TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    note TEXT CHECK (note IS NULL OR length(note) <= 500),
    wine_snapshot TEXT,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, wine_slug)
);
CREATE INDEX wine_ratings_recent ON wine_ratings (user_id, updated_at);
