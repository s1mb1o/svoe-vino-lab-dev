-- The diary lists of plan 07 (issues #71 and #64): the history of found wines and the saved wines.
-- A wine is a vino-svoe.ru slug. wine_snapshot is a JSON object (name, producer, color, sugar,
-- region, grapes), so a list renders when the catalog is not available.
-- The service checks the source values. The schema does not, so a new source needs no migration.

-- The switch «Записывать найденные вина». On by default. It applies to the site and the chats.
ALTER TABLE users ADD COLUMN save_history INTEGER NOT NULL DEFAULT 1;

-- first_met_at and last_met_at are the earliest and the latest first_at of the dates of the wine.
CREATE TABLE history_wines (
    user_id TEXT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    wine_slug TEXT NOT NULL,
    wine_snapshot TEXT,
    first_met_at INTEGER NOT NULL,
    last_met_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, wine_slug)
);
CREATE INDEX history_wines_recent ON history_wines (user_id, last_met_at);

-- One date for each wine and calendar day. met_on: YYYY-MM-DD in Europe/Moscow.
-- source: photo, shelf, telegram, or max. The first source of the day stays.
-- A wine without dates is removed.
CREATE TABLE history_days (
    user_id TEXT NOT NULL,
    wine_slug TEXT NOT NULL,
    met_on TEXT NOT NULL,
    source TEXT NOT NULL,
    first_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, wine_slug, met_on),
    FOREIGN KEY (user_id, wine_slug) REFERENCES history_wines (user_id, wine_slug) ON DELETE CASCADE
);

-- «Сохранённые»: independent of the history. A wine stays here when it leaves the history.
-- source: photo, shelf, lineup, dinner_lens, or history (where the person saved the wine).
CREATE TABLE saved_wines (
    user_id TEXT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    wine_slug TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('not_tasted', 'want', 'liked', 'disliked')),
    source TEXT NOT NULL,
    wine_snapshot TEXT,
    added_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, wine_slug)
);
CREATE INDEX saved_wines_recent ON saved_wines (user_id, updated_at);
