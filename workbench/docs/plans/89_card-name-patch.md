# Plan 89: Edit the name of a card (`name_patched`)

Date: 2026-09-29

Status: implemented, tested, and live. Schema 032 migrated on 2026-09-29 at 22:12. 8168
restarted with the code at 22:24:22 (PID 83275).

Source: owner message of 2026-09-29T22:00:54+0300 ("Добавь в workbench возможность
редактировать имена карточек. И больще ничего не делай"). Owner answers of 22:05:15
(storage "Separate column", place "Dataset card") and of 22:06:52 (column
`name_patched`).

## Goal

A person edits the name of a card on the Dataset page. The edit does not change the
value of the import. Each reader that shows the name, or sends it to a model, reads the
edit.

## Rules

1. `wine_catalog.name` holds the value of the import: vino-svoe.ru, the CSV, or the form
   `Add wine`.
2. The new column `wine_catalog.name_patched` holds the edit of a person, or NULL.
3. The name in use is `name_patched`, else `name`. This is the pattern of `main` and
   `main_patched`.
4. `pipeline/import_website.py` and `pipeline/import_catalog.py` compare and write `name`
   alone. They do not read or write `name_patched`. So an edit gives no conflict of the
   import, and an import keeps the edit.
5. An edit that equals `name` stores NULL. So the card has no edit.
6. The edit is allowed for a wine in each state.

## Schema 032

The number is fixed when the file enters `pipeline/schema/` (rules 25 and 26).

- `ALTER TABLE wine_catalog ADD COLUMN name_patched TEXT CHECK (name_patched <> '')`.
- The trigger `wine_catalog_update_time` gets the line of `name_patched` (the rule of
  schema 015). The file drops the trigger and creates it again.
- The view `matcher_wine` gets `COALESCE(w.name_patched, w.name) AS name`. The columns
  of the view stay the same (the rule of schema 031). So the matcher reads the edit with
  no change of its code.

## Route `POST /api/wine-name`

- Body: `{"slug": <text>, "name": <text>}`. At most `MAX_BODY` (4096) bytes.
- `name` loses its outer white space. An empty value gives HTTP 400. A value of more
  than 500 characters gives HTTP 400. A value that UTF-8 cannot encode gives HTTP 400.
- A slug that `wine_catalog` does not hold gives HTTP 404.
- One write transaction sets `name_patched`: NULL when the value equals `name`, else the
  value.
- Answer 200: `{"slug", "name", "catalog_name", "name_patched"}`. `name` is the name in
  use. `catalog_name` is the column `name`. `name_patched` is true or false.

## `GET /api/dataset`

- The key `name` of a record is the name in use.
- The new key `_catalog_name` is the column `name`.
- The new key `_name_patched` is true when `name_patched` is set.

## The Dataset page

- The name of the card gets a button `edit` after the button `copy`.
- The button opens a text field with the name in use, a button Save, and a button Cancel.
  Enter saves. Escape cancels.
- A card with an edit shows the tag `name patched`. The title of the tag holds the
  catalogue name. A button `reset` sends the catalogue name, so the edit goes away.
- After a save, the page updates the record and draws the card again.

## The readers of the name in use

Each query below reads `COALESCE(name_patched, name)` in place of `name`:

1. `pipeline/embeddings.py`, `read_inputs`: the Embeddings page, the log of an index
   build, the matcher bundle, the clusters.
2. `pipeline/clusters.py`, `_catalog`: the cards of `/clusters` and the card data of the
   label rules (`pipeline/label_rules.py`).
3. `pipeline/cluster_rerank.py`, `catalogue_names`: the verdict prompt of the re-rank.
4. `pipeline/run_routes.py`: the names of `/api/run-clusters`.
5. `pipeline/run_steps.py`: the names of the step popup of `/runs`.
6. `pipeline/testsets.py`: the cards of the Testset page.
7. `pipeline/lab_server.py`, `dataset_records`: the Dataset page.
8. `scripts/benchmark_bulk_cache.py`, `catalogue_identity`: the fingerprint of the
   catalogue.

## Effects

- The names do not enter the input hash of the clusters or of an index. An edit makes no
  index and no cluster file stale.
- The names enter `inputs_sha` of a label rule. The next run of
  `pipeline/build_label_rules.py` builds the rules of the clusters with an edited card
  again. This plan does not start that run.
- The matcher copies of `data/catalog/` get the edit at the next copy with
  `pipeline/catalog_copy.py`. This plan does not make a copy.

## Out of scope

- An edit on the Clusters page.
- A rebuild of rules, clusters, or indexes. A copy of the catalogue to the matcher.
- A change of the imports.

## Tests

- `tests/test_labdb.py`: the version 32.
- A new `tests/test_wine_name.py`: the route (save, reset by an equal value, trim, empty,
  too long, unknown slug, each state), the record keys of `GET /api/dataset`, the view
  `matcher_wine`, the trigger `modified_at`, and a website import that keeps the edit.
- `tests/test_lab_openapi.py`: the operation `POST /api/wine-name`.
- The focused tests of the changed readers. The fixtures of
  `tests/test_cluster_rerank.py` and `tests/test_prepare_rerun_label_inputs.py` build
  `wine_catalog` by hand; they get the column `name_patched`.
- A browser check on a scratch database and a scratch server: edit, Enter, the tag,
  reload, Esc, reset, the save button, light and dark theme. 12 of 12 checks pass in 3
  runs.

## Deployment

The entry of schema 032, the migration of `data/catalog/catalog.sqlite3` with
`pipeline/labdb.py`, and a restart of 8168 belong together (rule 27).
