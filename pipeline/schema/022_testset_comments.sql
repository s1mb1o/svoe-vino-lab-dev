-- Plan 51: the comment tables of the test sets. Owner message of 2026-09-26T17:55:00+0300
-- and the answers of 18:08:34. Read `docs/plans/51_testset-comments.md`.
--
-- One photo of a test set MAY have more than one comment. `test_photo_comment` holds
-- them. The columns follow `wine_comment` (plan 17): `created_at` is the UTC time of the
-- write, to the second, with `Z`; `source` is `user` for a person on the Testset page and
-- `script` for a script. The foreign key follows the photo: a move of the photo takes its
-- comments with it, and a delete of the photo removes them.
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

CREATE INDEX test_photo_comment_photo ON test_photo_comment (set_name, place, file_name);

-- The time of a moved comment is its old `ts` in UTC. `ts` has the form
-- `YYYY-MM-DDTHH:MM:SS+HHMM`; SQLite reads the offset in the form `+HH:MM`. A `ts` that
-- SQLite cannot read gives the time of the migration.

-- 1. `test_photo.comment`: one comment for each value. A photo with `proposed_by` holds
--    the comment of an agent proposal, so its comment gets `script`.
INSERT INTO test_photo_comment (set_name, place, file_name, created_at, source, text)
SELECT set_name, place, file_name,
       coalesce(strftime('%Y-%m-%dT%H:%M:%SZ', substr(ts, 1, 22) || ':' || substr(ts, 23, 2)),
                strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
       CASE WHEN proposed_by IS NOT NULL THEN 'script' ELSE 'user' END,
       comment
FROM test_photo
WHERE comment IS NOT NULL
ORDER BY set_name, place, file_name;

-- 2. `test_wine_note`: one wine comment for each wine and text. The set name goes away.
--    A text that starts with an agent tag of the photo hunt (`irec-<digit>`,
--    `hunter-<digit>`, `cigar-r<digit>`) gets `script`. A text that the wine has
--    already is not added again.
INSERT INTO wine_comment (wine_slug, created_at, source, text)
SELECT n.wine_slug,
       min(coalesce(strftime('%Y-%m-%dT%H:%M:%SZ',
                             substr(n.ts, 1, 22) || ':' || substr(n.ts, 23, 2)),
                    strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))),
       CASE WHEN n.comment GLOB 'irec-[0-9]*' OR n.comment GLOB 'hunter-[0-9]*'
                 OR n.comment GLOB 'cigar-r[0-9]*' THEN 'script' ELSE 'user' END,
       n.comment
FROM test_wine_note n
WHERE n.comment IS NOT NULL
  AND n.wine_slug IN (SELECT wine_slug FROM wine_catalog)
  AND NOT EXISTS (SELECT 1 FROM wine_comment c
                  WHERE c.wine_slug = n.wine_slug AND c.text = n.comment)
GROUP BY n.wine_slug, n.comment
ORDER BY 2, 1;

-- 3. The note of `chateau-tamagne-select-blanc-brut-svo-yo-vino`. `wine_catalog` does not
--    hold this slug, so the note goes to the slug that the note names. The first line
--    names the missing slug. The owner accepted this rule on 2026-09-26T18:08:34+0300.
INSERT INTO wine_comment (wine_slug, created_at, source, text)
SELECT 'chateau-tamagne-select-blanc-brut',
       min(coalesce(strftime('%Y-%m-%dT%H:%M:%SZ',
                             substr(n.ts, 1, 22) || ':' || substr(n.ts, 23, 2)),
                    strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))),
       CASE WHEN n.comment GLOB 'irec-[0-9]*' OR n.comment GLOB 'hunter-[0-9]*'
                 OR n.comment GLOB 'cigar-r[0-9]*' THEN 'script' ELSE 'user' END,
       'The note of the slug chateau-tamagne-select-blanc-brut-svo-yo-vino, which '
       || 'wine_catalog does not hold:' || char(10) || n.comment
FROM test_wine_note n
WHERE n.wine_slug = 'chateau-tamagne-select-blanc-brut-svo-yo-vino'
  AND n.comment IS NOT NULL
  AND n.wine_slug NOT IN (SELECT wine_slug FROM wine_catalog)
  AND EXISTS (SELECT 1 FROM wine_catalog
              WHERE wine_slug = 'chateau-tamagne-select-blanc-brut')
GROUP BY n.comment;

-- 4. `test_excluded.reason`: one wine comment for each wine and reason. The exclusion
--    itself goes away (owner answer of 2026-09-26T18:08:34+0300).
INSERT INTO wine_comment (wine_slug, created_at, source, text)
SELECT e.wine_slug,
       min(coalesce(strftime('%Y-%m-%dT%H:%M:%SZ',
                             substr(e.ts, 1, 22) || ':' || substr(e.ts, 23, 2)),
                    strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))),
       'user',
       'Excluded from the benchmark: ' || trim(e.reason)
FROM test_excluded e
WHERE e.reason IS NOT NULL AND trim(e.reason) <> ''
  AND e.wine_slug IN (SELECT wine_slug FROM wine_catalog)
  AND NOT EXISTS (SELECT 1 FROM wine_comment c
                  WHERE c.wine_slug = e.wine_slug
                    AND c.text = 'Excluded from the benchmark: ' || trim(e.reason))
GROUP BY e.wine_slug, trim(e.reason)
ORDER BY 2, 1;

DROP TABLE test_wine_note;
DROP TABLE test_excluded;
ALTER TABLE test_photo DROP COLUMN comment;
