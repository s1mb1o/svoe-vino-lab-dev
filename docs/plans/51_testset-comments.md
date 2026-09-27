# Plan 51: the comment tables of the test sets

Date: 2026-09-26

State: done. Schema 022 went live on 2026-09-26T18:50:37+0300. The owner allowed the
files of the stale sections and the restart at 18:17:31.

Source: owner message of 2026-09-26T17:55:00+0300, and the answers of 18:08:34 (session
drink-atlas-workspace-ab [539687]). The answers: one step; the wine notes go to
`wine_comment`; the exclusion goes away; this session also changes the wine rows of
`/testset`. The last answer covers the owner message of 17:37:45 ("show comments same as
on dataset page") for `/testset`.

## 1. The present state

The counts are of `data/lab.sqlite3` at 2026-09-26T18:00, schema 21.

| Source | Rows | What the rows are |
|---|---|---|
| `test_photo.comment` | 1,594: `my` 1,495, `official-real-photos` 80, `vlmrerank-8b-failed` 19 | One text for each photo. 1,460 of the photos have `proposed_by`. |
| `test_wine_note` | 88: `my` 82, `vlmrerank-8b-failed` 6 | One text for each wine and set. The texts are about the whole wine, not about one photo. Most texts start with the tag of a hunt agent, for example `irec-03:`, `hunter-09:`, or `cigar-r05 /`. Six texts are in both sets with the same text. |
| `test_excluded` | 15 rows over 10 wines | The benchmark skips the photos of these slugs. Each row has a reason. |
| `wine_comment` | 0 | The seed of 2026-09-26T07:42 made the table empty. |

Each `ts` of the three sources has the form `YYYY-MM-DDTHH:MM:SS+0300`.

The slug `chateau-tamagne-select-blanc-brut-svo-yo-vino` has a wine note, but
`wine_catalog` does not hold the slug. `wine_comment.wine_slug` refers to `wine_catalog`.
So a plain copy of this note stops the migration: `labdb.migrate` runs
`PRAGMA foreign_key_check` before the commit.

## 2. The decisions

1. A new table `test_photo_comment` holds the comments of the test photos. One photo MAY
   have more than one comment. The columns follow `wine_comment` (plan 17).
2. `test_photo.comment` moves to `test_photo_comment`, one row for each value. Then the
   column goes away.
3. `test_wine_note.comment` moves to `wine_comment`, one row for each wine and text. The
   set name goes away. The same text in two sets gives one row. Then the table goes
   away.
4. The note of `chateau-tamagne-select-blanc-brut-svo-yo-vino` goes to
   `chateau-tamagne-select-blanc-brut`, the slug that the note names. Its first line
   names the missing slug. The owner accepted this rule with the answer of 18:08:34.
5. `test_excluded.reason` moves to `wine_comment` with the text
   `Excluded from the benchmark: <reason>`. The same reason in two sets gives one row.
   Then the table goes away.
6. The exclusion goes away. The benchmark uses the photos of the 10 wines. The button
   `Exclude` goes away. The metrics of a new run are not equal to the metrics of an
   old run of the same set.
7. The time of a moved comment is the old `ts`, in UTC, in the form of `wine_comment`.
8. The source of a moved comment:
   - A photo comment gets `script` when the photo has `proposed_by`, else `user`.
   - A wine note gets `script` when its text starts with the tag of a hunt agent:
     `irec-<digit>`, `hunter-<digit>`, or `cigar-r<digit>`. Else it gets `user`. The dry
     run gives 76 `script` notes and 6 `user` notes.
   - An exclusion reason gets `user`.

The text of item 5 has no set name. The session proposed the set names at 18:05. The
plan drops them so that an import of the old files gives the same rows as the migration
(section 5). The session reports this change to the owner.

## 3. The schema file `NNN_testset_comments.sql`

The number is fixed when the file enters `pipeline/schema/` (rules 25 and 26 of
`CLAUDE.md`). The file does these steps in one transaction:

1. `CREATE TABLE test_photo_comment`:
   `id INTEGER PRIMARY KEY`, `set_name`, `place`, `file_name`, `created_at`, `source`,
   `text`. The checks of `created_at`, `source`, and `text` are the checks of
   `wine_comment`. The foreign key `(set_name, place, file_name)` refers to
   `test_photo` with `ON UPDATE CASCADE ON DELETE CASCADE`. So a move of a photo takes its
   comments with it, and a new import of a set removes the old comments of the set. An
   index covers `(set_name, place, file_name)`.
2. Insert the photo comments, the wine notes, the one note of item 4, and the exclusion
   reasons.
3. `DROP TABLE test_wine_note`, `DROP TABLE test_excluded`, and
   `ALTER TABLE test_photo DROP COLUMN comment`. SQLite 3.53 allows the `DROP COLUMN`:
   only the check of the column itself names the column.

A note whose slug is not in `wine_catalog` and is not the slug of item 4 is not copied.
On `data/lab.sqlite3` there is no such note. The dry run of section 7 checks it.

## 4. The code

| File | Change |
|---|---|
| `pipeline/testsets.py` | `comment` leaves `ENTRY_FIELDS`. New: the comments of a photo, `add_photo_comment`, `remove_photo_comment`, `utc_of`. `photo_view` gives `comments`. `set_view` gives the wine comments of each row (`comments`), and no `note`, `excluded`, or `exclude_reason`. `counts` counts `commented` from `test_photo_comment` and has no `wine_notes`. `set_comment`, `set_wine_note`, and `set_excluded` go away. |
| `pipeline/testset_routes.py` | New: `POST /api/testset-photo-comment` `{set, place, file, text, source?}` and `POST /api/testset-photo-comment-remove` `{set, place, file, id}`. Removed: `/api/testset-comment`, `/api/testset-wine-note`, and `/api/testset-exclude`. |
| `pipeline/benchmark.py` | No exclusion. The count `excluded slug` goes away. |
| `pipeline/import_testset.py` | Section 5. |
| `pipeline/export_testset.py` | Section 5. |
| `pipeline/testset_from_run.py` | The copy takes the comments of each copied photo. It copies no wine notes and no exclusions. The answer has `photo_comments`, and no `wine_notes` and `excluded`. |
| `pipeline/pages/testset.html` | Section 6. |
| `pipeline/pages/runs.html` | Two texts of the dialog `New testset…`. |

The wine comments of `/testset` use the route `POST` and `DELETE /api/dataset-comment`
of the Dataset page. A write of a wine comment changes no test set, so it does not set
`test_set.edited_at`. A write of a photo comment sets `test_set.edited_at`, as each other
write of the page. It does not change `test_photo.ts`: a comment has its own time.

## 5. The import and the export

The JSON field `comments` of a label entry holds the comments of the photo: a list of
`{"created_at", "source", "text"}`, the oldest first.

The export (`export_testset.py`):

- writes `comments` into each entry of a photo with comments. An entry that has only
  comments is written too.
- does not write the map `wines`. The wine comments are data of the catalogue, not of a
  set.
- does not write `excluded-slugs.json`. A file of that name in the set directory stays
  as it is. The old tools of `scripts/` still read it.
- drops `wine_notes` from `counts`.

The import (`import_testset.py`):

- reads `comments` of an entry into `test_photo_comment`. A list with an item that is not
  valid stays in `extra`, as each other field that no column keeps.
- reads the old field `comment` of an entry into one comment, by the rules 7 and 8 of
  section 2. The time comes from `ts` of the entry. With no valid `ts`, the time is the
  time of the import.
- reads the old map `wines` and the old `excluded-slugs.json` into `wine_comment`, by the
  rules of section 2. A comment that the wine has already with the same text is not
  added again. So a second import adds no row. A slug that `wine_catalog` does not hold
  gets a console message, and its text is not stored.
- does not remove a wine comment. The wine comments are not rows of one set.

## 6. The page `/testset`

The photo popup (the large view):

- The panel `Comments on this photo` shows the comments of the photo, the oldest first:
  the button `×` (remove, after a confirm), the local time, the source, and the text. The
  form follows the Dataset page.
- A text field and the button `Add` stand below the list. Cmd+Enter or Ctrl+Enter adds
  the text as a new comment. A step to another photo, a close of the view, a change of
  the set, a move of the photo, and a reload add a text that is not empty, so that no
  typed text is lost.
- The badge of a card shows the number of comments. Its popup shows the texts.

A wine row:

- The field `note about this wine` goes away. The row shows the editor of the wine
  comments of the Dataset page: the list, `+`, the text field, save, and cancel.
- A row whose slug is not in `wine_catalog`, the row `No Match`, and the Drawer show no
  wine comment editor.
- The button `Exclude`, the reason under it, and the red colour of an excluded row go
  away.

## 7. The steps

1. A copy of `data/lab.sqlite3` goes to `data/backups/` with the SQLite backup API.
2. A dry run applies the schema file to a second copy. It checks the counts of section 1
   against the new rows.
3. The schema file enters `pipeline/schema/` with the next free number. The migration of
   `data/lab.sqlite3` and the restart of 8168 follow in the same minutes (rule 27).
4. The tests of `tests/` run. A browser check covers the popup and the wine rows.

## 8. The consequences

- The Testset page has no exclusion. A slug with a wrong catalogue photo now counts in
  the metrics. The state `Removed` of a wine still takes its photos out of a run.
- The old tools of `scripts/` (`review_server.py`, `match_run.py`) read the JSON files.
  After an export, they see no `comment` and no `wines`. `match_run.py` still reads the
  old `excluded-slugs.json`.
- `test_set.label_note` holds the note text of the old tool. It still names the field
  `comment` and the map `wines`. The export writes it unchanged.
- A new seed from the JSON files gives the same wine comments as the migration, until an
  export writes `review-labels.json` again without `wines`.

## 9. The result

- The migration of `data/lab.sqlite3` at 18:50:37 gave 1,594 rows of
  `test_photo_comment` and 92 new rows of `wine_comment`: 81 notes, the note of item 4,
  and 10 exclusion reasons. `PRAGMA foreign_key_check` gave no row. The backup is
  `data/backups/lab-before-022-testset-comments-20260926T155037Z.sqlite3`.
- The dry run found a third agent tag, `cigar-r<digit>`. Rule 8 of section 2 names it.
- The tests of the change pass. The whole suite in a scratch tree ran 842 tests. Only
  `test_barcode` failed (23 != 22); it fails on HEAD too.
- 22 browser checks passed on a copy of the database: the wine comments of a row (add,
  remove, Esc), the panel of the large view (Add, Cmd+Enter, the add at a close and at a
  step, `×`), the badge of a card, the filter `Marks`, the dark theme, and a width of
  390 px.
- `docs/database-structure.html` shows schema 001-017 only. It needs a new layout for
  schema 018 and later, also for `wine_beverage_type` of plan 52. The owner decides.
