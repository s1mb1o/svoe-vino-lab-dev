-- A Telegram link code belongs to the first Telegram user who opens it (issue #51 review).
-- Only that user can confirm it. A repeated confirm by the same user answers the same result.
ALTER TABLE link_codes ADD COLUMN claimed_by TEXT;
