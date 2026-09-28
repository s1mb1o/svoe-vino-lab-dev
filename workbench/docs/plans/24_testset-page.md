# 24 — The Testset page on the lab database

Date: 2026-09-25.
Status: done on 2026-09-25, not committed. Approved on 2026-09-25 (owner answers of
17:01:44 to 17:26:22). Session: drink-atlas-workspace-ca [a2daf6]. TESTSET [0fe970]
wrote the draft and stopped; the owner gave the plan to this session at 17:17:45.

## Goal

1. The page `/testset` of the lab server (port 8168) shows the test sets of the
   database. `GET /` redirects to `/dataset`.
2. A person labels the photos of a set on this page. Each click writes to
   `data/lab.sqlite3`.
3. The database is the source of the labels. The JSON files of `dataset/<set>/` are no
   longer the source.
4. A person MAY draw one box around the main object of a scene photo. The box is
   optional. The owner expects it on a few photos.
5. A wine that is in a test set stays in the set when its state becomes `Removed`, so a
   restore finds it again.

The test sets are in the database since schema 016 (plan 12, step 4).

## Decisions of the owner (2026-09-25)

| Question | Decision | Time |
|---|---|---|
| What does the page do? | It edits the labels in the database (not a read-only page, not the old page). | 12:22:00 |
| The scope of the first version | Labels and marks. The move and the copy of a photo, the upload, the fetch by URL, and the checks come in later plans. | 12:40:00 |
| The source of the labels | The database. `import_testsets.py` refuses a set that holds page edits, unless `--force`. A new export writes the JSON files from the database. The old review tool on port 8154 is no longer used for labels. | 12:40:00 |
| The fields of a label entry | All fields. Nothing of `review-labels.json` is lost. | 12:40:00 |
| The box of the main object | An optional box on a scene photo, for scenes with several items, and for a later test of how the matcher finds the main item. | 12:42:00 |
| Who implements the plan | drink-atlas-workspace-ca [a2daf6], after TESTSET [0fe970] stopped. | 17:17:45 |
| The address of the page | `/testset` is the Testset page. `/` redirects to `/dataset`. | 17:01:44 |
| Q1. The rows | A row for each `Active` and `Disabled` wine, and a row for each place that holds a photo of the set, also when its wine is `Removed` or is not in `wine_catalog`. | 17:01:44 |
| Q2. The manual variant groups | Skip the manual groups functionality. | 17:01:44 |
| Q3. The test of the main item | A new plan 27, after this plan. A match on a photo with a true box passes when the slug is right and the two boxes overlap (IoU > 0). A configuration that returns no box gives IoU `n/a`, and the slug alone decides. This plan stores and exports the box. | 17:23:18 |
| Q4. One box or more | One box: the main object. | 17:01:44 |
| A wine that becomes `Removed` | Its rows of the set stay. The page shows it with a `Removed` badge. The benchmark leaves its photos out ("removed wine") until a restore. | 17:13:17 |
| Hunks in the files of other sessions | Allowed. The live sessions got a notice. | 17:26:22 |

## The present state

- `test_photo` holds `label` and `marked_delete` of each entry alone.
- A label entry of `review-labels.json` holds more fields. The counts of 2026-09-25 for
  `my`: `ts` 3,615, `comment` 1,495, `by`, `proposed`, `confidence`, and `source_url`
  1,608 each, `moved_from` 29, `copied_from` 6. `official-real-photos` also holds
  `reassign_to` (7) and `prefilled_from` (93, an object).
- The top-level map `wines` holds a note of a whole wine (82 in `my`, 6 in
  `vlmrerank-8b-failed`).
- No label entry of the three sets names a missing file. No entry is empty, and no
  entry holds `ts` alone. No entry holds `delete` or `copy_to`.
- The old page is `PAGE` of `scripts/review_server.py`. Its write routes for this scope
  are `/api/label`, `/api/mark-delete`, `/api/comment`, `/api/wine-comment`, and
  `/api/exclude`.
- `image.width` and `image.height` are the size of the file header, before the EXIF
  orientation. None of the 3,453 test photo files has an EXIF orientation other than 1.

## Scope of the first version

In the first version:

1. A set selector: `my`, `official-real-photos`, `vlmrerank-8b-failed`.
2. One row for each wine of rule Q1. The NULL row (`__null__`) stood first; since
   2026-09-25T18:05:36 the NULL place is the right sidebar (see "Changes after the
   approval"). A row holds
   the catalogue image of the wine (the card image of the Dataset page), the slug with a
   `copy` button, the name, the producer, the state, and the photos of the set. A wine
   that is `Removed` gets the badge `Removed`. A wine that is `Disabled` gets the badge
   `Disabled`. A place that `wine_catalog` does not hold gets the badge
   `not in catalogue`.
3. The four labels `positive`, `negative`, `unusable`, and `variant`, with the buttons
   `V`, `N`, `x`, and `D`. The same button again clears the label. A photo of
   `__null__` takes `positive` or `unusable` alone, as in the old tool.
4. The mark `delete` of a photo. The mark does not move a file.
5. The comment of a photo (at most 4,000 characters).
6. The note of a wine (at most 4,000 characters).
7. The exclusion of a slug, with a reason (at most 1,000 characters). An exclusion needs
   a reason.
8. The box of the main object of a photo (see the section "The box").
9. The large view: the catalogue image at the left, the photo at the right, the comment
   panel, and the keys `Left`, `Right`, `Up`, `Down`, `1` to `4`, `b`, and `Esc`.
10. The address of one photo: `/testset?set=<set>#<slug>/<file name>`.
11. The 13 sort orders of the old page.
12. These filters of the old page: `all wines`, `not fully labelled`, `no label yet`,
    `partly labelled`, `fully labelled`, `has a positive photo`, `has no positive
    photo`, `has a negative sample`, `has an unusable photo`, `has a different-design
    photo`, `has a similar wine (variant group)`, `no candidate photos`, `holds a
    comment`, `holds a photo proposed by an agent`, `excluded from the benchmark`, and
    `included in the benchmark`. New filters: `marked for deletion`, `holds a box`, and
    `removed from the catalogue`.
13. A text search in the slug, the name, the producer, the region, and the grapes. The
    words of the query match in any order. Case and accents are folded.
14. The counts of the set in the header.
15. The light and the dark theme after the system setting, with `theme.css`.

Not in the first version:

- The move and the copy of a photo, `apply`, the trash (`reassign_to` stays read-only).
- The upload, the fetch by URL, and the inbox.
- The checks (`validate`).
- The editor of the variant groups (`Group`), and the manual groups of
  `manual-groups.json` (Q2).
- The CSV export of the table, the picture selector (`package`, `label`, `label box`),
  and the `catalogue photo:` filters.
- The fuzzy rules 3 and 4 of the old text search (one letter away; Cyrillic to Latin).
- The agent API `/api/v1/`.
- The IoU of the box in the benchmark and on the Runs page (plan 27).

## The schema file `019_testset_page.sql`

The number 019 was fixed at the entry on 2026-09-25T17:37:35+0300 (rules 25 to 28 of
`AGENTS.md`).

1. `test_photo` is built again, because the new box needs a CHECK over four columns. No
   table references `test_photo`. The file keeps each row. New columns:

   | Column | JSON field | Content |
   |---|---|---|
   | `comment` | `comment` | The comment of the photo. Not empty, at most 4,000 characters. |
   | `ts` | `ts` | The time of the last change of the entry, `%Y-%m-%dT%H:%M:%S%z`. |
   | `proposed` | `proposed` | The label that an agent proposed. One of the four labels. |
   | `proposed_by` | `by` | The agent that proposed the label. `by` is an SQL keyword. |
   | `confidence` | `confidence` | The confidence of the proposal, a REAL. |
   | `source_url` | `source_url` | The page where the photo was found. |
   | `moved_from` | `moved_from` | The slug of the photo before a move. |
   | `copied_from` | `copied_from` | The slug of the photo before a copy. |
   | `reassign_to` | `reassign_to` | A move that waits for `apply`. Read-only in this plan. |
   | `prefilled_from` | `prefilled_from` | The object of a prefilled label, as JSON text. |
   | `extra` | any other field | The other fields of the entry, as a JSON object. So a field that this table does not know is not lost. |
   | `box_left`, `box_top`, `box_right`, `box_bottom` | `box` | The box of the main object. |

2. A new table `test_wine_note` (`set_name`, `wine_slug`, `comment`, `ts`, `extra`). It
   holds the map `wines` of `review-labels.json`.
3. `test_set` gets two columns:
   - `edited_at`: the time of the last write of the page. NULL means no page edit.
   - `label_note`: the text `note` of `review-labels.json`, for the export.

The rule of `extra`: the import puts a field into its column only when the column keeps
the value exactly: a text column takes a non-empty text, `confidence` takes a number,
`prefilled_from` takes an object, `delete` takes `true`, and `box` takes four integers
inside the image. A field with another value (for example `null`, or `"delete": false`)
goes into `extra` with its value. A field that the table does not know (for example
`copy_to`) goes into `extra` too. The export writes the columns and then the keys of
`extra`. A page write of a field removes that key from `extra`.

## The box

1. One box for each row of `test_photo`: one photo in one place of one set. The same
   bytes in two places MAY hold two boxes, because a scene with two bottles has another
   main object for each slug.
2. The box is in the pixels of the photo as the browser shows it: after its EXIF
   orientation, as the box of `image_derivative`. `0 <= box_left < box_right <= width`
   and `0 <= box_top < box_bottom <= height`, where width and height are the size after
   the orientation. The server reads the orientation from the stored file at each box
   write. The four values are all NULL or all set.
3. The large view: the key `b` or the button `Box` starts the box mode. A drag on the
   photo draws the box. A new drag replaces it. `Clear box` removes it. `Esc` leaves the
   box mode. The large view shows the box as a frame. A card with a box gets the badge
   `box`.
4. JSON: the field `box` of a label entry, `[left, top, right, bottom]`. The import reads
   it, and the export writes it.
5. The benchmark does not use the box in this plan. Plan 27 adds the IoU.

## The import and the export

1. `import_testset.py` reads each field of the table above, the map `wines`, and the
   text `note`. It refuses a set whose `edited_at` is not NULL, unless `--force`.
   `import_testsets.py` gets the same option.
2. New `pipeline/export_testset.py`:

   ```bash
   python3 pipeline/export_testset.py --db data/lab.sqlite3 --set my --out <directory>
   ```

   It writes `review-labels.json` (version 2: `version`, `updated`, `counts`, `note`,
   `wines`, `labels`) and `excluded-slugs.json` of the set into `--out`. `--out` is
   required. The export writes no photo file.
3. The round-trip check: the import of a set, then its export, gives the same `labels`,
   `wines`, and excluded slugs as the source files, field for field. The check runs on
   the three sets of `svoe-vino-testset/dataset/` before the page is enabled.

## The benchmark

`build_queries` of `pipeline/benchmark.py` leaves out a photo whose place is a wine with
the state `Removed`, and counts it as "removed wine". A restore of the wine puts its
photos back into the next run.

## The routes

A new module `pipeline/testset_routes.py` answers the routes, as `run_routes.py` does
for the Runs page. `pipeline/testsets.py` holds the reads and the writes of the
database. `lab_server.py` gets small hunks: the import, the delegation in `do_GET` and in
the write routes, `/` out of `DISABLED_PAGES`, the redirect of `/`, `NAV`, and the
docstring. The folder `testset` in `IMAGE_ROUTE` came with plan 23. A photo URL uses the
folder of its row of `image`, because 4 test photos keep the folders `additional` and
`patched`.

| Route | Body or query | Answer |
|---|---|---|
| `GET /` | | HTTP 302 to `/dataset`. |
| `GET /testset` | | The page `pipeline/pages/testset.html`. |
| `GET /api/testset` | `set=<name>` | `sets` (each name and its counts), `set`, `rows`, `counts`, `groups`. A row holds the wine data, the state, the card image, `excluded`, `group`, `note`, and `photos`. A photo holds `file`, `url`, `sha256`, `width`, `height`, and every column of the table above. |
| `POST /api/testset-label` | `set`, `place`, `file`, `label` (a label or null) | `photo`, `counts`. HTTP 400 for another label or for `negative` and `variant` on `__null__`. HTTP 404 for an unknown photo. |
| `POST /api/testset-delete` | `set`, `place`, `file`, `delete` (boolean) | `photo`, `counts`. |
| `POST /api/testset-comment` | `set`, `place`, `file`, `text` | `photo`, `counts`. An empty text removes the comment. |
| `POST /api/testset-box` | `set`, `place`, `file`, `box` (`[l, t, r, b]` or null) | `photo`, `counts`. HTTP 400 for a box outside the image. |
| `POST /api/testset-wine-note` | `set`, `slug`, `text` | `note`, `counts`. |
| `POST /api/testset-exclude` | `set`, `slug`, `excluded` (boolean), `reason` | `excluded`, `counts`. |

Note of 2026-09-25 (drink-atlas-workspace-cb [48de03]; owner message of 18:19:01 and
the answers of 18:25:10): a new route `POST /api/testset-upload?set=&place=&name=`. The
body is the bytes of one image. The page sends it for each file that the Finder drops
onto the sidebar (`place` `__null__`) or onto a wine row. `testsets.upload_photo` stores
the bytes in `images/testset/` unless `image` holds them, and adds a row of `test_photo`
with no field. The answer holds `photo` and `counts`. HTTP 409 for an image that the
place holds already; an image that another place holds keeps its file name of the set.
HTTP 400 for no image or another format than JPEG, PNG, WebP, GIF, and BMP; HTTP 413 for
more than 20 MB or 100 megapixels; HTTP 404 for an unknown set or slug.

Changes after the approval (drink-atlas-workspace-ca [a2daf6]; owner messages of
2026-09-25T18:04:02+0300 and 18:04:22, and the answers of 18:05:36):

1. The set combobox stands in the title: `Test set [my (4043 photos) ▾]`. The bar has no
   second set control. The line after the combobox counts the wines and each photo of
   the set, the sidebar too; the time of the last edit stands at the end of the stats
   line, so the title line stays short (fixes of TESTSET [0fe970], 2026-09-25).
2. The right sidebar is the NULL place. The NULL row leaves the table. A sidebar card has
   `V` (confirmed: no card shows this wine) and `×` (unusable) and opens the large view.
   The large view names the NULL place, not a wine number.
3. A move: a drag of a photo card onto the sidebar moves the photo to `__null__`; a drag
   of a sidebar card onto a wine row moves it to that wine; the key `0` of the large view
   moves the photo to `__null__`. New route:

   | Route | Body | Answer |
   |---|---|---|
   | `POST /api/testset-move` | `set`, `place`, `file`, `to` (a slug or `__null__`) | `from`, `to`, `file`, `photo`, `counts`. HTTP 400 when `to` is the place of the photo, empty, or no text; HTTP 404 for an unknown set, photo, or slug. |

   A move clears the label. The comment, the box, the delete mark, and the proposal stay.
   `moved_from` gets the old place. A file name that the target place holds gets the
   suffix `_moved<N>`. A move changes rows of `test_photo` alone; no file moves.
4. The benchmark uses a NULL photo only with the label `positive`
   (`pipeline/benchmark.py`, `build_queries`). A NULL photo with no label waits for a
   wine and stays out of the run.
5. Known points, not changed: after wine, sidebar, and wine again, `moved_from` holds
   `__null__`, not the first slug; the first move overwrites an imported `moved_from`;
   the suffix `_moved<N>` stays when a photo returns to its own wine; a move does not
   clear `reassign_to`.

Note of 2026-09-26 (plan 36, drink-atlas-workspace-e2 [9e7fe4]): the sidebar is now the
Drawer (`__drawer__`), and `__null__` is the first table row `No Match` again. Points 2
and 4 above no longer hold: a run uses each `__null__` photo that is not `unusable`, and
no Drawer photo. Read `docs/plans/36_no-match-row-and-drawer.md`.

Rules of each write:

1. One transaction. It changes the field, sets `ts` of the photo entry (or of the note,
   or of the exclusion), and sets `test_set.edited_at`. The other fields of the entry do
   not change, as in `_entry` of the old tool. When no field of the entry is left, `ts`
   becomes NULL, so the export writes no entry, as the old tool removes it.
2. The page draws the card of the answer again, not the whole table.
3. The server refuses a text with a lone surrogate, as `comments.py` does.
4. A write to a wine of each state is allowed, also `Removed`.

## The page

`pipeline/pages/testset.html` uses the navigation and the theme of the other lab pages.
It loads the rows of one set. The photos load lazily (`loading="lazy"`), because `my`
holds 4,043 photos (795 MB in `svoe-vino-testset/dataset/my/photo/`).

## Steps

1. The owner approves this plan and answers the open questions. Done at 17:26:22.
2. The schema file, the import of all fields, the export, and their tests. The
   round-trip check on the three sets. Done: the check on a copy of the database gave
   the same `labels`, `wines`, excluded slugs, `note`, and `counts` for each set.
3. `pipeline/testsets.py`, `pipeline/testset_routes.py`, the `lab_server.py` hunks, the
   benchmark rule, and their tests. Done.
4. The page. A check in headless Chromium, in the light and the dark theme, and at a
   width of 390 px. Done on a copy of the database on port 8174: 36 checks pass.
5. The entry of the schema file, the migration, a new import of the three sets with the
   new import (before any page edit), and a restart of 8168 (rules 22 to 27 of
   `AGENTS.md`). Done: 019 entered and migrated at 17:37:35, the sets imported again at
   about 17:38 with no restart (the running server reads `pipeline/schema/` on each
   request), and a restart with the new code at 17:55:56.
6. `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`, and plan 07. Done.

## Risks

- A person who labels in the old tool on port 8154 after step 5 writes to the JSON
  files. The lab does not see these labels, and a new import is refused. The owner
  decided that the old tool is no longer used for labels.
- `lab_server.py`, `test_lab_server.py`, and the navigation are changed by several
  sessions. The hunks MUST stay small.
- The flat image store of drink-atlas-workspace-9a [f028b4] MUST also move
  `data/images/testset/`.
- `scripts/review_server.py` of this project serves the shared `dataset.html`. Its
  Testset page stays at `/`, so the Testset link of that page leads to 404 there. The
  owner uses the copy in `svoe-vino-testset` on port 8154, which has its own page.
