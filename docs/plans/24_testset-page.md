# 24 — The Testset page on the lab database

Date: 2026-09-25.
Status: draft. It waits for the approval of the owner and for the answers to the open
questions. Session: TESTSET [0fe970].

## Goal

1. The page `/` of the lab server (port 8168) shows the test sets of the database.
2. A person labels the photos of a set on this page. Each click writes to
   `data/lab.sqlite3`.
3. The database is the source of the labels. The JSON files of `dataset/<set>/` are no
   longer the source.
4. A person MAY draw one box around the main object of a scene photo. The box is
   optional. The owner expects it on a few photos.

The test sets are in the database since schema 016 (plan 12, step 4).

## Decisions of the owner (2026-09-25)

| Question | Decision | Time |
|---|---|---|
| What does the page do? | It edits the labels in the database (not a read-only page, not the old page). | 12:22:00 |
| The scope of the first version | Labels and marks. The move and the copy of a photo, the upload, the fetch by URL, and the checks come in later plans. | 12:40:00 |
| The source of the labels | The database. `import_testsets.py` refuses a set that holds page edits, unless `--force`. A new export writes the JSON files from the database. The old review tool on port 8154 is no longer used for labels. | 12:40:00 |
| The fields of a label entry | All fields. Nothing of `review-labels.json` is lost. | 12:40:00 |
| The box of the main object | An optional box on a scene photo, for scenes with several items, and for a later test of how the matcher finds the main item. | 12:42:00 |

## The present state

- `test_photo` holds `label` and `marked_delete` of each entry alone.
- A label entry of `review-labels.json` holds more fields. The counts of 2026-09-25 for
  `my`: `ts` 3,615, `comment` 1,495, `by`, `proposed`, `confidence`, and `source_url`
  1,608 each, `moved_from` 29, `copied_from` 6. `official-real-photos` also holds
  `reassign_to` (7) and `prefilled_from` (93, an object).
- The top-level map `wines` holds a note of a whole wine (82 in `my`, 6 in
  `vlmrerank-8b-failed`).
- The old page is `PAGE` of `scripts/review_server.py`. Its write routes for this scope
  are `/api/label`, `/api/mark-delete`, `/api/comment`, `/api/wine-comment`, and
  `/api/exclude`.

## Scope of the first version

In the first version:

1. A set selector: `my`, `official-real-photos`, `vlmrerank-8b-failed`.
2. One row for each wine. The NULL row (`__null__`) stands first. A row holds the
   catalogue image of the wine (the card image of the Dataset page), the slug with a
   `copy` button, the name, the producer, the state, and the photos of the set.
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
10. The address of one photo: `/?set=<set>#<slug>/<file name>`.
11. The 13 sort orders of the old page.
12. These filters of the old page: `all wines`, `not fully labelled`, `no label yet`,
    `partly labelled`, `fully labelled`, `has a positive photo`, `has no positive
    photo`, `has a negative sample`, `has an unusable photo`, `has a different-design
    photo`, `has a similar wine (variant group)`, `no candidate photos`, `holds a
    comment`, `holds a photo proposed by an agent`, `excluded from the benchmark`, and
    `included in the benchmark`. Two new filters: `marked for deletion` and `holds a
    box`.
13. A text search in the slug, the name, the producer, the region, and the grapes. The
    words of the query match in any order. Case and accents are folded.
14. The counts of the set in the header.
15. The light and the dark theme after the system setting, with `theme.css`.

Not in the first version:

- The move and the copy of a photo, `apply`, the trash (`reassign_to` stays read-only).
- The upload, the fetch by URL, and the inbox.
- The checks (`validate`).
- The editor of the variant groups (`Group`).
- The CSV export of the table, the picture selector (`package`, `label`, `label box`),
  and the `catalogue photo:` filters.
- The fuzzy rules 3 and 4 of the old text search (one letter away; Cyrillic to Latin).
- The agent API `/api/v1/`.

## The schema file `NNN_testset_page.sql`

The number is fixed at the entry (rules 25 to 28 of `AGENTS.md`).

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

2. A new table `test_wine_note` (`set_name`, `wine_slug`, `comment`, `ts`). It holds the
   map `wines` of `review-labels.json`.
3. `test_set` gets two columns:
   - `edited_at`: the time of the last write of the page. NULL means no page edit.
   - `label_note`: the text `note` of `review-labels.json`, for the export.

## The box

1. One box for each row of `test_photo`: one photo in one place of one set. The same
   bytes in two places MAY hold two boxes, because a scene with two bottles has another
   main object for each slug.
2. The box is in the pixels of the stored file after its EXIF orientation, as the box of
   `image_derivative`. `0 <= box_left < box_right <= width` and
   `0 <= box_top < box_bottom <= height`. The four values are all NULL or all set.
3. The large view: the key `b` or the button `Box` starts the box mode. A drag on the
   photo draws the box. A new drag replaces it. `Clear box` removes it. `Esc` leaves the
   box mode. The large view shows the box as a frame. A card with a box gets the badge
   `box`.
4. JSON: the field `box` of a label entry, `[left, top, right, bottom]`. The import reads
   it, and the export writes it.
5. The benchmark does not use the box in this plan. The matcher answer holds no box of
   the item that it matched (`svm/server.py`, `shape_answer`: `slug`, `score`, `rank`,
   and `explain` alone). Read the open question Q3.

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

## The routes

A new module `pipeline/testset_routes.py` answers the routes, as `embedding_routes.py`
does for the Embeddings page. `pipeline/testsets.py` holds the reads and the writes of
the database. `lab_server.py` gets small hunks: the import, the delegation in `do_GET`
and in the write routes, `/` out of `DISABLED_PAGES`, and the docstring. The folder
`testset` in `IMAGE_ROUTE` comes with plan 23 of drink-atlas-workspace-85 (agreed on
2026-09-25): the Runs page shows the test photos too. A photo URL uses the folder of its
row of `image`, because 4 test photos keep the folders `additional` and `patched`.

| Route | Body or query | Answer |
|---|---|---|
| `GET /` | | The page `pipeline/pages/testset.html`. |
| `GET /api/testset` | `set=<name>` | `sets` (each name and its counts), `set`, `rows`, `counts`. A row holds the wine data, the card image, `excluded`, `group`, `note`, and `photos`. A photo holds `file`, `url`, `sha256`, `width`, `height`, and every column of the table above. |
| `POST /api/testset-label` | `set`, `place`, `file`, `label` (a label or null) | `photo`, `counts`. HTTP 400 for another label or for `negative` and `variant` on `__null__`. HTTP 404 for an unknown photo. |
| `POST /api/testset-delete` | `set`, `place`, `file`, `delete` (boolean) | `photo`, `counts`. |
| `POST /api/testset-comment` | `set`, `place`, `file`, `text` | `photo`, `counts`. An empty text removes the comment. |
| `POST /api/testset-box` | `set`, `place`, `file`, `box` (`[l, t, r, b]` or null) | `photo`, `counts`. HTTP 400 for a box outside the image. |
| `POST /api/testset-wine-note` | `set`, `slug`, `text` | `note`, `counts`. |
| `POST /api/testset-exclude` | `set`, `slug`, `excluded` (boolean), `reason` | `excluded`, `counts`. |

Rules of each write:

1. One transaction. It changes the field, sets `ts` of the photo entry (or of the note,
   or of the exclusion), and sets `test_set.edited_at`. The other fields of the entry do
   not change, as in `_entry` of the old tool.
2. The page draws the card of the answer again, not the whole table.
3. The server refuses a text with a lone surrogate, as `comments.py` does.

## The page

`pipeline/pages/testset.html` uses the navigation and the theme of the other lab pages.
It loads the rows of one set. The photos load lazily (`loading="lazy"`), because `my`
holds 4,043 photos (795 MB in `svoe-vino-testset/dataset/my/photo/`).

## Steps

1. The owner approves this plan and answers the open questions.
2. The schema file, the import of all fields, the export, and their tests. The
   round-trip check on the three sets.
3. `pipeline/testsets.py`, `pipeline/testset_routes.py`, the `lab_server.py` hunks, and
   their tests.
4. The page. A check in headless Chromium, in the light and the dark theme, and at a
   width of 390 px.
5. The entry of the schema file, the migration, a new import of the three sets with the
   new import (before any page edit), and a restart of 8168 (rules 22 to 27 of
   `AGENTS.md`).
6. `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`, and plan 07.

## Risks

- A person who labels in the old tool on port 8154 after step 5 writes to the JSON
  files. The lab does not see these labels, and a new import is refused. The owner
  decided that the old tool is no longer used for labels.
- `lab_server.py`, `test_lab_server.py`, and the navigation are changed by several
  sessions. drink-atlas-workspace-85 enables `/runs` at the same time. The hunks MUST
  stay small, and the sessions agree the order.
- The flat image store of drink-atlas-workspace-9a [f028b4] MUST also move
  `data/images/testset/`.

## Open questions

- **Q1. The rows of a `Removed` wine.** Proposal: a row for each `Active` and `Disabled`
  wine, and a row for each place that holds a photo of the set, also when its wine is
  `Removed` or is not in `wine_catalog`.
- **Q2. The manual variant groups.** `my` and `vlmrerank-8b-failed` hold
  `manual-groups.json` (pairs that a person joined). The old page shows them together
  with `variant-groups.json`. `test_variant` holds `variant-groups.json` alone, and the
  benchmark reads it. Proposal: the first version does not import the manual pairs; a
  later plan with the `Group` editor imports them.
- **Q3. The test of the main item.** The matcher does not report the box of the item
  that it matched. A test of "how the matcher finds the main item" needs a change of
  `svoe-vino-matcher`, for example a query box in `explain`, and a metric in the
  benchmark, for example the IoU of the two boxes. Proposal: a later plan. This plan
  stores and exports the box.
- **Q4. One box or more.** Proposal: one box, the main object. A box of each item of a
  scene is a later change.
