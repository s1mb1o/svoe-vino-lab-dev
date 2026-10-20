-- A personal note of a saved wine (owner request, 2026-10-20). NULL: no note.
-- At most 2,000 characters after normalization. The service never writes a note to the log.
ALTER TABLE saved_wines ADD COLUMN note TEXT;
