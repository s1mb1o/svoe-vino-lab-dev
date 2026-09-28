# 07 — The lab database

Date: 2026-09-24.
Status: steps 1 to 3 are implemented on 2026-09-24. Step 4 is implemented on 2026-09-24
by [plan 08](08_seed-images.md). The owner approves each later step before it starts.

## Goal

1. One SQLite database holds the state of the lab for one catalogue delivery.
2. The tables are in BCNF. A deviation from BCNF MUST be stated in this plan.
3. The database and the dataset are filled one step at a time. Each step fills its own
   tables. The owner reviews a step before the next step starts.

The decisions and their reasons are in `docs/decisions/01_sqlite-lab-database.md`.

## Rules

1. One database holds one catalogue. `pipeline/import_catalog.py` updates it from a new
   CSV by added and removed wines.
2. The database file is `data/lab.sqlite3`. The owner chose this flat layout on
   2026-09-24. A second delivery needs a second file name.
3. Do not use the prefix `official-` for a directory of this project. In this workspace,
   `official-<DATE>` names a read-only delivery of the organizers.
4. The database MUST be on a local disk. Do not put it on NFS, for example
   `/mnt/projects` of gx10. SQLite file locks are not reliable on NFS.
5. The schema is in `pipeline/schema/NNN_<name>.sql`. A schema change is a new file with
   the next number. Do not edit an applied file.
6. `PRAGMA user_version` holds the number of the last applied schema file.
   `pipeline/labdb.py` applies each newer file in one transaction. The foreign keys are
   off during the file, so a file MAY build a parent table again, and
   `PRAGMA foreign_key_check` MUST find no broken link before the COMMIT. SQLite ignores
   `PRAGMA foreign_keys` inside a transaction. This came with schema 014 on 2026-09-25.
7. Each table is `STRICT`.
8. The key column of a wine is `wine_slug`, as in `code-map.json` and `embedding-ignore.json`.
   Another column name follows the key of `catalog.jsonl` when that key exists.
9. A step writes all of its rows in one transaction, or no row.
10. A step never writes to `svoe-wino-hackaton/dataset/official-<DATE>/`.

## Step 1 — create the database and the table `wine_catalog`

Status: done.

Command:

```bash
python3 pipeline/labdb.py data/lab.sqlite3
```

Schema files:

| File | Change |
|---|---|
| `pipeline/schema/001_wine_catalog.sql` | The tables `catalog_source` and `wine_catalog`. |
| `pipeline/schema/002_wine_slug.sql` | Renames the column `slug` to `wine_slug`. The owner asked for the name on 2026-09-24. |
| `pipeline/schema/003_wine_state.sql` | Adds the column `state`. Drops the table `catalog_source`. The owner asked for both on 2026-09-24. |
| `pipeline/schema/004_removed_by.sql` | Adds the column `removed_by` and the table check that ties it to `state`. It builds the table again and keeps each rowid. A wine that was `Removed` before gets `import`. |

| Table | Key | Content |
|---|---|---|
| `wine_catalog` | `wine_slug` | One row per catalogue card, with its state. |

The database keeps no record of the imported CSV files. The owner removed the table
`catalog_source` on 2026-09-24.

The columns of `wine_catalog`:

| Column | CSV column | Rule |
|---|---|---|
| `wine_slug` | `Slug` | Primary key. Not empty. |
| `name` | `Название вина` | Not empty. |
| `producer` | `Винодельня` | Not empty. |
| `category` | `Категория` | Not empty. |
| `color` | `Цвет` | Not empty. |
| `region` | `Регион` | Not empty. |
| `grapes` | `Сорт винограда` | The verbatim list. NULL when the CSV value is empty. |
| `description` | `Описание` | Not empty. |
| `csv_photo_name` | `Название фото` | Not empty. Not unique. |
| `state` | none | `Active`, `Disabled`, or `Removed`. The default is `Active`. |
| `removed_by` | none | `import` or `person` for a `Removed` wine. NULL for another state. A table check enforces this. |

The states:

| State | Meaning | Set by |
|---|---|---|
| `Active` | The wine is in use. | `pipeline/import_catalog.py`; the buttons `Enable` and `Restore` |
| `Disabled` | A person took the wine out of use. The wine is not used for embeddings and matches. No tool reads the state for that yet. | the button `Disable` |
| `Removed` | The wine is out of the dataset. `removed_by` tells who removed it. | `pipeline/import_catalog.py` (`import`); the button `Remove` (`person`) |

Normal form:

- `Slug` is the only candidate key of the CSV. `Название фото` and `Описание` are not
  unique.
- No non-key column determines another non-key column. `Винодельня → Регион` does not
  hold: 3 producers appear in two regions. `state` and `removed_by` depend on the wine
  alone. The table check `(state = 'Removed') = (removed_by IS NOT NULL)` keeps the two
  columns consistent.
- Deviation from 1NF: `grapes` holds a list as one string. The owner accepted this on
  2026-09-24. A child table `wine_grape (wine_slug, position, grape)` MAY follow when a
  query needs one grape.

## Step 2 — the import CLI

Status: done. `pipeline/import_catalog.py` replaced the seed CLI `pipeline/seed_catalog.py`
on 2026-09-24. The first import into an empty database adds every wine.

Command:

```bash
python3 pipeline/import_catalog.py --db data/lab.sqlite3 \
    ../../svoe-wino-hackaton/dataset/official-2026-09-17/strapi_output0709.csv
```

Rules of the CSV:

1. The CSV MUST hold exactly the nine known columns. The column order is free.
2. Each value loses its outer white space. `build_catalog.py` uses the same rule.
3. An empty `Сорт винограда` becomes NULL. Another empty value stops the import.
4. Rows that are equal after the trim are one wine. Two different rows with one slug
   stop the import.

Rules of the import. The import handles an added wine and a removed wine alone. The
owner set this scope on 2026-09-24.

1. The database MUST exist. The import does not create it. This stops a mistyped path
   from making a second database.
2. A wine of the CSV that the database does not hold is added as `Active`.
3. A wine of the database that the CSV does not hold becomes `Removed`, with
   `removed_by` = `import`. This applies to an `Active` wine and to a `Disabled` wine.
4. A wine that the import removed becomes `Active` when the CSV holds it again.
5. A wine that a person removed stays `Removed`, also when the CSV holds it. The import
   never changes `removed_by` = `person`. The report counts such wines under
   `kept removed by a person`. The owner chose this on 2026-09-24.
6. A `Disabled` wine that the CSV holds stays `Disabled`.
7. A wine of the CSV with a field that differs from the database stops the import. The
   error names the wine, its state, and each changed field with the old and the new
   value. This applies to a `Removed` wine too.
8. The import takes the write lock before it reads the database. It writes all changes
   in one transaction, or no change.
9. A second import of the same file changes nothing.
10. A wine that a person added has a slug that starts with `__`. The import never
    removes it. A CSV slug with this prefix stops the import. The owner chose this on
    2026-09-25. Read [plan 20](20_add-wine.md).

Result of the first import on 2026-09-24:

| Count | Value |
|---|---|
| Data rows read | 4,147 |
| Duplicate rows | 2,044 |
| Wines added | 2,103 |
| Values trimmed | 198 |
| Wines with NULL `grapes` | 2 |
| CSV SHA-256 | `12a1b0b620db7a2264b094446861e83940a927708d65a1b7ccffda7ec3aeffee` |
| Values that differ from `catalog.jsonl` | 0 of 2,103 × 8 |

`tests/data/` holds three fake variants of the official CSV and the expected import
results. Read `tests/data/README.md`.

Tests: `tests/test_labdb.py`, 14 cases on 2026-09-25 (9 at the end of step 2).
`tests/test_import_catalog.py`, 22 cases.

## Step 3 — the lab server with the Dataset page

Status: done on 2026-09-24.

The owner removed every JSON file and every directory from `config.yaml` on
2026-09-24. The database is the only source of the lab data. `config.yaml` holds two
keys: `rootdir` and `database_file`.

Command:

```bash
python3 pipeline/lab_server.py            # http://127.0.0.1:8168/dataset
```

Rules:

1. `database_file` is resolved against `rootdir`, as every relative path of
   `config.yaml`. The value for this project is `svoe-vino-lab/data/lab.sqlite3`.
   The owner kept this rule on 2026-09-24.
2. The server opens the database for each request. A GET opens it read-only.
   `POST /api/wine-state` opens it read-write and writes the columns `state` and
   `removed_by` of one wine alone.
3. The schema version of the database MUST equal the number of schema files. Another
   version stops the start, and `/api/dataset` answers HTTP 503.
4. `GET /dataset` serves `pipeline/pages/dataset.html`. `GET /api/dataset` answers the
   rows of `wine_catalog` in import order, with each state. The key `wine_slug` goes
   out as `slug`, because the page reads `slug`. A removed wine stays in the answer, and
   its key `state` tells it apart.
5. The data of the page editors is in the database. The GTINs and the QR URLs are in
   the table `wine_code` since schema 008: `POST` and `DELETE` of `/api/dataset-gtin` and
   `/api/dataset-qr-url` (plan 11). The Atlas bindings are in `wine_atlas_binding` since
   schema 009: `POST /api/dataset-atlas-binding` sets a manual binding, and `DELETE
   /api/dataset-atlas-binding?slug=…` removes it (plan 15). A patch is the `main_patched`
   row of `wine_image`: `POST` and `DELETE` of `/api/dataset-patch` (plan 14). The
   alternative photos are rows of `wine_image` of the types `full_front`, `label_front`,
   `full_back`, and `label_back` since schemas 010 and 012: `POST` and `DELETE` of
   `/api/dataset-alternative`, and `POST /api/dataset-alternative-type` (plan 16). Their
   processed files are in `image_derivative`, one for each original and kind of cut since
   schema 017. The comments of a wine are in `wine_comment` since schema 011 (plan 17).
   The favorites are in `wine_favorite` since schema 013 (plan 19). A wine added by hand
   has a slug that starts with `__`: `POST /api/wine` (plan 20).
5a. Each card holds state buttons below the catalogue image. `POST /api/wine-state`
   takes `{"slug": …, "action": …}` and allows these changes alone:

   | Action | Button | From | To |
   |---|---|---|---|
   | `disable` | `Disable` | `Active` | `Disabled` |
   | `enable` | `Enable` | `Disabled` | `Active` |
   | `remove` | `Remove` | `Active`, `Disabled` | `Removed`, `removed_by` = `person` |
   | `restore` | `Restore` | `Removed` | `Active`, `removed_by` = NULL |

   Another change answers HTTP 409. An unknown slug answers 404. A bad body or an unknown
   action answers 400. A card of a `Disabled` wine shows the tag `disabled`. A card of a
   `Removed` wine shows `removed by import` or `removed by person`.
5b. The filter `State` shows `All (except Removed)` or `Removed`. The default is
   `All (except Removed)`. The owner asked for the buttons and the filter on
   2026-09-24. The owner renamed the button `Ignore` to `Disable` on the same day.
5c. A state change renders its own card alone, not the list. A card that leaves the
   view of the `State` filter is taken out of the list. Each card has
   `content-visibility: auto`, so the browser skips the layout of a card out of view.
   A link `/dataset#<slug>` scrolls two times: the second scroll puts the card at its
   place after the cards near it get their true heights. Measured on 2026-09-24 in
   headless Chromium with 2,103 cards: a full render took 0.7 s before and 0.14 s after;
   a state click took 1.8 to 2.1 s before and about 0.1 s after. The server write takes
   2 to 4 ms.
6. The page Clusters and `/docs` are disabled for now. Each one answers a notice page
   with HTTP 503. The notice page keeps the navigation. The Embeddings page is on since
   plan 10, and the Runs page since plan 23: it reads `runs/`, not the database. The
   Testset page is on since plan 24, at `/testset`; `/` redirects to `/dataset`.
7. Each other `/api/` route answers HTTP 503 with a JSON error. An `/img/` route answers
   HTTP 503.
8. Do not remove a part of a page unless the owner asks for it. A disabled part comes
   back when its data is in the database. On 2026-09-24 the owner removed the source
   panel of the Dataset page: the lines `catalog.jsonl`, `patch directory`, and the
   other sources above the list. An error of `/api/dataset` now shows in the list.
   The owner also removed the line `Colour: …` of each card. The colour stays in the
   full record and in the search. The slug with its `copy` button stands above the
   name, as the first line of a card. The owner asked for both on 2026-09-24.

The shared page files are in `pipeline/pages/`: `dataset.html`, `theme.css`, and
`disabled.html`. `pipeline/lab_pages.py` reads them. `scripts/review_server.py` reads
`dataset.html` and `theme.css` from there too. At the move, each page string of
`review_server.py` was byte-identical to commit `ab54124`. After the move, one fix
changed `dataset.html`: `safeUrl` answers no link for an empty value. Before the fix, a
record with no `page_url` got a `site page` link to the Dataset page itself.

`scripts/review_server.py` and the other scripts of `scripts/` read the JSON files
through `scripts/common.py`. They do not start with the new `config.yaml`.

Tests: `tests/test_lab_server.py`, 15 cases.

## Step 5 — the patched main images

Status: done on 2026-09-24. Plan 08 made the table `wine_image` and the type
`main_patched`. This step fills that type.

Command:

```bash
python3 pipeline/seed_patched.py --db data/lab.sqlite3 \
    ../../svoe-wino-hackaton/dataset/patched-official-2026-09-17
```

The patch folder is an overlay on the delivery. Its `README.md` states the rule: the
name of a file before the extension is the wine slug, and the file replaces the main
image of that wine.

Rules:

1. A patch is a file at the top level of the folder with the extension `webp`, `png`,
   `jpg`, or `jpeg`, in any case. The script skips a hidden file, a folder such as
   `_originals/`, and another file such as `README.md`.
2. The script copies each patch to `images/patched/<sha256>.<extension>` next to the
   database file, with the store rules of `pipeline/seed_images.py`.
3. The patch folder is the truth for the patches. The owner chose this on 2026-09-24:
   - a patch of a wine with no `main_patched` row adds a row;
   - a patch with the same sha256 changes nothing;
   - a patch with another sha256 replaces the row; the old file stays in the store;
   - a row whose wine has no patch file in the folder is deleted, and the wine goes
     back to its `main` image.
4. `match_method` is `slug-name`. `source_name` is the file name in the folder.
5. A slug that `wine_catalog` does not hold gets a message and no row. Two patch files
   for one slug are an error, and the row of that wine stays.
6. The script writes the files first. It then reads the rows again under the write lock
   and writes all changes in one transaction.
7. `pipeline/lab_server.py` shows `main_patched` in place of `main` on the card.

Result on 2026-09-24, on a copy of the database: 15 patch files, 15 rows added,
15 files written, `README.md` skipped. A second run changed nothing. The folder holds 15
patches; its `README.md` table lists 7 of them.

Tests: `tests/test_seed_patched.py`, 11 cases.

Change of 2026-09-25 by plan 09 (`docs/plans/09_image-processing.md`): the script writes
one row of `image` for each patch file, with its pixel size, and a row of `wine_image`
with no `extension`. It processes each patch with `pipeline/derive.py` and takes the
option `--sam3 <URL>`. Tests: `tests/test_seed_patched.py`, 14 cases.

Change of 2026-09-25 by plan 14 (`docs/plans/14_patch-editor.md`): the database is the
truth for the patches. The owner chose this on 2026-09-25T09:53:00+0300. Rule 3 above no
longer deletes a row: a row whose wine has no patch file in the folder stays, and the
report names it (`rows kept with no file in the folder`). The patch editor of the
Dataset page writes rows too.

## Candidate later steps

These steps are proposals. The owner selects the next step and its content.

| Step | Content | Source |
|---|---|---|
| 4 | Done by [plan 08](08_seed-images.md): the table `wine_image` and `pipeline/seed_images.py`. The store is `data/images/<folder>/<sha256>.<ext>`, one folder for each image type. | `uploads/` of the delivery, the rename rule of `build_catalog.py` |
| 5 | Patched pictures (`main_patched`): done, see step 5 above. Extra catalogue views (`front`, `back`, `label_front`, `label_back`) into `wine_image`: open. | `patched-official-<DATE>/`, `derived/additional/` |
| 6 | Test photos into `data/images/testset/`, with their source URLs, in their own table. Several test sets, each with its own photos. Read the section "Input for the test set step" of plan 08. | `dataset/*/photo/`, `review-labels.json` field `source_url` |
| 7 | Done by plan 12 (schema 016) and [plan 24](24_testset-page.md) (schema 019): the test sets, the photo placements, each field of a label entry, the box of the main object, the wine notes, and the excluded slugs. The database is the source of the labels; `pipeline/export_testset.py` writes the JSON files. | `review-labels.json`, `excluded-slugs.json` |
| 8 | Variant groups: done by plan 12 (`test_variant`). Manual pairs: open; the owner skipped them for plan 24 (2026-09-25T17:01:44+0300). | `variant-groups.json`, `manual-groups.json` |
| 9 | Match runs, queries, and candidates. | `runs/*/` |
| 10 | Move each disabled page to the lab server when its data is in the database. | `scripts/review_server.py` |

## Open questions

1. Does one label hold for a photo and a slug in every dataset, or does each dataset keep
   its own labels? This decides the key of the label table in step 7.
2. Does the reviewer switch the dataset in the web UI, or does a restart with
   `--dataset` stay enough?
3. How does git keep the history of the database when it holds data that cannot be
   rebuilt, such as labels? A text export in git is one option.
   Answer of 2026-09-26: the text export `db-export/`, one JSON-lines file for each
   table, and the skill `backup-lab-db` commits it. Read
   [plan 50](50_lab-db-text-export.md).
4. Does the database use WAL mode when the review server and a script write at the same
   time?
5. Is the object store of step 4 one store per delivery, or one store for all deliveries?
   On 2026-09-24, plan 08 put the store in `images/` next to the database file. One
   database holds one delivery, so each delivery has its own store for now.
