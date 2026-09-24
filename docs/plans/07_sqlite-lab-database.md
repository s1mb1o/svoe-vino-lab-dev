# 07 — The lab database

Date: 2026-09-24.
Status: steps 1 and 2 are implemented on 2026-09-24. The owner approves each later step
before it starts.

## Goal

1. One SQLite database holds the state of the lab for one catalogue delivery.
2. The tables are in BCNF. A deviation from BCNF MUST be stated in this plan.
3. The database and the dataset are filled one step at a time. Each step fills its own
   tables. The owner reviews a step before the next step starts.

The decisions and their reasons are in `docs/decisions/01_sqlite-lab-database.md`.

## Rules

1. One database holds one delivery. A new delivery gets a new database file.
2. The database file is `data/<delivery directory>/lab.sqlite3`. The directory of the
   delivery `official-2026-09-17` is `data/catalog-2026-09-17/`.
3. Do not use the prefix `official-` for a directory of this project. In this workspace,
   `official-<DATE>` names a read-only delivery of the organizers.
4. The database MUST be on a local disk. Do not put it on NFS, for example
   `/mnt/projects` of gx10. SQLite file locks are not reliable on NFS.
5. The schema is in `pipeline/schema/NNN_<name>.sql`. A schema change is a new file with
   the next number. Do not edit an applied file.
6. `PRAGMA user_version` holds the number of the last applied schema file.
   `pipeline/labdb.py` applies each newer file in one transaction.
7. Each table is `STRICT`.
8. A column name follows the key of `catalog.jsonl` when that key exists.
9. A step writes all of its rows in one transaction, or no row.
10. A step never writes to `svoe-wino-hackaton/dataset/official-<DATE>/`.

## Step 1 — create the database and the table `wine_catalog`

Status: done.

Command:

```bash
python3 pipeline/labdb.py data/catalog-2026-09-17/lab.sqlite3
```

Schema file: `pipeline/schema/001_wine_catalog.sql`.

| Table | Key | Content |
|---|---|---|
| `catalog_source` | `id` = 1 | The CSV file of the delivery: absolute path, SHA-256, data row count, seed time. At most one row. |
| `wine_catalog` | `slug` | One row per catalogue card. |

The columns of `wine_catalog`:

| Column | CSV column | Rule |
|---|---|---|
| `slug` | `Slug` | Primary key. Not empty. |
| `name` | `Название вина` | Not empty. |
| `producer` | `Винодельня` | Not empty. |
| `category` | `Категория` | Not empty. |
| `color` | `Цвет` | Not empty. |
| `region` | `Регион` | Not empty. |
| `grapes` | `Сорт винограда` | The verbatim list. NULL when the CSV value is empty. |
| `description` | `Описание` | Not empty. |
| `csv_photo_name` | `Название фото` | Not empty. Not unique. |

Normal form:

- `slug` is the only candidate key of the CSV. `Название фото` and `Описание` are not
  unique.
- No non-key column determines another non-key column. `Винодельня → Регион` does not
  hold: 3 producers appear in two regions.
- Deviation from 1NF: `grapes` holds a list as one string. The owner accepted this on
  2026-09-24. A child table `wine_grape (slug, position, grape)` MAY follow when a query
  needs one grape.

## Step 2 — the seed CLI

Status: done.

Command:

```bash
python3 pipeline/seed_catalog.py --db data/catalog-2026-09-17/lab.sqlite3 \
    ../svoe-wino-hackaton/dataset/official-2026-09-17/strapi_output0709.csv
```

Rules:

1. The database MUST exist. The seed does not create it. This stops a mistyped path
   from making a second database.
2. The CSV MUST hold exactly the nine known columns. The column order is free.
3. Each value loses its outer white space. `build_catalog.py` uses the same rule.
4. An empty `Сорт винограда` becomes NULL. Another empty value stops the seed.
5. Rows that are equal after the trim are one wine. Two different rows with one slug
   stop the seed.
6. A second seed from the same file changes nothing. The SHA-256 identifies the file.
7. A seed from another file stops, because the database holds one delivery.

Result on 2026-09-24:

| Count | Value |
|---|---|
| Data rows read | 4,147 |
| Duplicate rows | 2,044 |
| Wines stored | 2,103 |
| Values trimmed | 198 |
| Wines with NULL `grapes` | 2 |
| CSV SHA-256 | `12a1b0b620db7a2264b094446861e83940a927708d65a1b7ccffda7ec3aeffee` |
| Values that differ from `catalog.jsonl` | 0 of 2,103 × 8 |

Tests: `tests/test_seed_catalog.py`, 13 cases.

## Candidate later steps

These steps are proposals. The owner selects the next step and its content.

| Step | Content | Source |
|---|---|---|
| 3 | Catalogue pictures. Find the upload file of each `csv_photo_name`. Store the bytes as `objects/<sha256>.<ext>`. Tables for the image and for the picture of a card. | `uploads/` of the delivery, the rename rule of `build_catalog.py` |
| 4 | Patched pictures and extra catalogue views. | `patched-official-<DATE>/`, `derived/additional/` |
| 5 | Test photos into the object store, with their source URLs. | `dataset/*/photo/`, `review-labels.json` field `source_url` |
| 6 | Datasets, photo placements, labels, comments, wine notes, excluded slugs. | `review-labels.json`, `excluded-slugs.json` |
| 7 | Variant groups and manual pairs. | `variant-groups.json`, `manual-groups.json` |
| 8 | Match runs, queries, and candidates. | `runs/*/` |
| 9 | Move the readers and the writers from the JSON files to the database. | `scripts/match_run.py`, `scripts/review_server.py` |

## Open questions

1. Does one label hold for a photo and a slug in every dataset, or does each dataset keep
   its own labels? This decides the key of the label table in step 6.
2. Does the reviewer switch the dataset in the web UI, or does a restart with
   `--dataset` stay enough?
3. How does git keep the history of the database when it holds data that cannot be
   rebuilt, such as labels? A text export in git is one option.
4. Does the database use WAL mode when the review server and a script write at the same
   time?
5. Is the object store of step 3 one store per delivery, or one store for all deliveries?
