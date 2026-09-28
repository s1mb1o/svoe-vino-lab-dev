-- 026: the insert time of each row of `wine_code`.
--
-- `modified_at` is the UTC time of the insert of the row, to the second, in ISO 8601
-- with `Z`, as `wine_catalog.modified_at` of schema 015. The lab never updates a row of
-- `wine_code`: a change is a DELETE and an INSERT. So the insert time is the time of the
-- last change of the row. A DELETE leaves no row and no time.
-- The trigger sets the time, so no writer changes its code. An INSERT with a time keeps
-- that time, as in a restore of pipeline/db_export.py. An existing row keeps NULL,
-- because its insert time is not known.
--
-- A schema file that builds `wine_code` again drops the trigger. Such a file MUST create
-- the trigger again.
-- The owner chose this on 2026-09-27.

ALTER TABLE wine_code ADD COLUMN modified_at TEXT
    CHECK (modified_at GLOB
           '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z');

CREATE TRIGGER wine_code_insert_time AFTER INSERT ON wine_code
WHEN NEW.modified_at IS NULL
BEGIN
    UPDATE wine_code SET modified_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE rowid = NEW.rowid;
END;
