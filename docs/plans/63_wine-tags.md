# Plan 63: the tags of a wine

Date: 2026-09-27

Source: owner messages of 2026-09-27T17:04:20+0300 and 17:05:11+0300, and the owner
answers of 17:07:53 (`docs/owner-messages.md`).

## Goal

A person puts free-form text tags on a wine on `/dataset`. The first use is to mark the
variants of one wine that have more than one `wine_slug`:

- `shato-pino-shiraz-krasnoe-suhoe-135` gets the tag `generic`: the card of each vintage.
- `shato-pino-shiraz-krasnoe-suhoe-14` gets the tag `vintage:2017`: the card of 2017.

The catalogue rows of these two wines are equal. No catalogue column holds the year. A tag
records the decision of a person.

## Decisions of the owner

1. A tag is free-form text. One wine MAY have more than one tag. There is no closed list.
2. This plan stores the tags, shows and edits them on `/dataset`, and sends them in
   `GET /api/dataset`. The pipeline does not read the tags. The use of the tags in the
   match (a photo of 2017 goes to `-14`, other photos go to `-135`) is a later plan.

## Decisions of the agent

3. The normal form of a tag: the module removes the outer white space and makes the text
   lower case (Python `str.lower`). So `Generic` and `generic` are one tag.
4. A valid tag has 1 to 64 characters. Each character is a letter, a digit, `_`, `-`,
   `:`, or `.`. A tag has no white space. Cyrillic letters are allowed. The suggested
   forms are `generic` and `vintage:YYYY`, but the code does not require them.

## Data

Schema file `pipeline/schema/NNN_wine_tag.sql`. The number is fixed at the entry of the file
(rules 25 and 26 of `AGENTS.md`). The next free number on 2026-09-27T17:10 is 029.

```sql
CREATE TABLE wine_tag (
    wine_slug  TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    tag        TEXT NOT NULL CHECK (tag <> '' AND length(tag) <= 64),
    created_at TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    PRIMARY KEY (wine_slug, tag)
) STRICT;
```

- One row is one tag of one wine. The rowid order is the order of the adds.
- `created_at` is the UTC time of the add, as `wine_favorite.created_at`.
- A wine of each state MAY have tags.
- `pipeline/wine_tags.py` checks the form of item 4. The CHECK holds the length alone.

## Module `pipeline/wine_tags.py`

5. `normal(text)` returns the normal form of item 3. A tag that breaks item 4 raises
   `TagError`.
6. `tags(conn, slug=None)` returns wine slug -> the list of its tags, in rowid order. A
   wine with no tag has no key.
7. `count(conn)` returns the number of rows.
8. `add(conn, slug, text, now=None)` adds one tag and returns its normal form. A tag that
   the wine has raises `DuplicateError`.
9. `remove(conn, slug, text)` removes one tag. It returns False for a tag that the wine
   does not have.

## Routes of the lab server

10. `POST /api/dataset-tag` with the body `{"slug", "tag"}` adds one tag.
    `DELETE /api/dataset-tag?slug=&tag=` removes one tag.
    - The answer: `ok`, `slug`, `tags` (the tags of the wine after the write), `total`
      (the number of rows), and `added` or `removed` (the normal form of the tag).
    - HTTP 400: no slug, no tag, or a tag that breaks item 4.
    - HTTP 404: a wine that does not exist, or a DELETE of a tag that the wine does not
      have.
    - HTTP 409: a POST of a tag that the wine has.
11. `GET /api/dataset` sends `tag_editor: true` and `wine_tags` (the number of rows). Each
    record holds `_tags`: the list of its tags, in the order of the adds.

## The page `/dataset`

12. Each card has the editor `Tags` after the editor `Hard cases` of plan 62 (named
    `Similar wines` until 2026-09-27T23:15). It lists the tags:
    the tag text and a remove button `×`. The button `+` opens an input. The input
    suggests the tags that the page holds already. Enter or the save button adds the tag.
    Escape or the cancel button closes the input. A save or a remove draws the card again.
13. The page shows the editor only when `GET /api/dataset` sends `wine_tags`, so the review
    tool keeps its page.
14. The editor uses the classes of the other code editors. It has no new colour, so the
    light and the dark theme stay correct.

## Deploy

15. The entry of the schema file, the migration of `data/lab.sqlite3` with
    `pipeline/labdb.py`, and the restart of 8168 belong together (rule 27).
16. `pipeline/db_export.py` reads `sqlite_schema`. It exports the new table with no change.

## Tests

17. `tests/test_wine_tags.py`: the module functions and the table checks.
18. `tests/test_lab_server.py`: the routes and the key `_tags` (a new class at the end).
19. `tests/test_labdb.py`: VERSION and the table list.
20. Smoke tests WT1 and later in `SMOKE_TESTS.md`.

## Open for a later plan

21. The match reads `generic` and `vintage:YYYY`. The owner compared three ways on
    2026-09-27: the tags feed `label_rules.vintage_facts`, or the re-rank asks a fixed
    vintage question, or no pipeline change. The owner chose no pipeline change for now.

## Result

Done on 2026-09-27. Schema 029 was entered and migrated at 17:20:28. 8168 was restarted
at 17:21 (pid 46259). By 23:36 the owner had stored 12 tags through the editor, for
example `2023` and `2024` on the `usadba-mezyb-*-vione-*` variants, and `brut`,
`duplicate`, and `wrong_image`. So the tags serve more uses than the vintage.

- `test_wine_tags.py` 5, `test_lab_server.py` 69, `test_labdb.py` 17 tests OK. The full
  suite gives 1,262 tests OK (5 skipped).
- A browser check on 8168 with the tag writes mocked and each other write blocked, in
  the light and the dark theme, at 1,440 px and 390 px, passed 58 of 60 checks.
- The 2 failures are one defect that is older than this plan. At 390 px the page header
  (`.bar-actions`, `#vlm-status`, the navigation links) makes the page 529 px wide. The
  width is the same when the check removes each `Tags` editor.
