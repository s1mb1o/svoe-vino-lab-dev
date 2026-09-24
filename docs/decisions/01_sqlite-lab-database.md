# 01 — SQLite for the lab state

Date: 2026-09-24.
Status: accepted by the project owner.
Plan: `docs/plans/07_sqlite-lab-database.md`.

## Context

The lab state is in JSON files: `review-labels.json`, `variant-groups.json`,
`manual-groups.json`, `excluded-slugs.json`, and others. The owner wants more than one
test dataset and a switch between them. A derived dataset such as `vlmrerank-8b-failed`
is a byte copy of photos and labels of `my`: all 179 distinct images of that set are
also in `my`.

## Decision 1 — the store

| Option | For | Against |
|---|---|---|
| JSON files, as now | Git diff of each review. No code change. 1.2 MB of labels is small. | Two writers at the same time: the last write wins. A move changes four files with no transaction. |
| SQLite | Transactions over many tables. Keys and constraints. One store for many datasets. | No git diff of a binary file. Not safe on NFS. Each reader of the JSON files needs a change. |

Decision: SQLite. The owner selected it on 2026-09-24. The tables are in BCNF.

Consequences:

- The database stays on a local disk.
- The history of the data that cannot be rebuilt needs an answer before that data moves
  into the database. See open question 3 of plan 07.

## Decision 2 — the project home

Options: build in `svoe-vino-testset` and rename it later, or build in the new
`svoe-vino-lab`.
Decision: `svoe-vino-lab`. The new code is in `pipeline/`, apart from the stages of
`scripts/`.

## Decision 3 — deliveries per database

| Option | For | Against |
|---|---|---|
| Several deliveries in one database | Old labels keep their reference when a new delivery arrives. | Each catalogue key becomes (release, slug). |
| One delivery per database | The key of `wine_catalog` is `slug` alone. Simple queries. | A new delivery needs a new database, or a migration. |

Decision: one delivery per database.

## Decision 4 — the grape list

| Option | For | Against |
|---|---|---|
| Verbatim text | Equal to the CSV. | A list in one string. A query for one grape needs `LIKE`. Not 1NF. |
| Child table only | 1NF. | The CSV value is not stored. A split rule is needed: `,` and ` и `. |
| Both | Both forms. | The list is stored two times. |

Decision: verbatim text. A child table MAY follow later.

## Decision 5 — outer white space

Options: trim, or keep the bytes. 198 values of the CSV have outer white space.
Decision: trim. `build_catalog.py` uses the same rule, so the database and
`catalog.jsonl` agree. The CSV in `official-2026-09-17/` keeps the exact bytes.

## Decision 6 — catalogue updates by add and remove

Date: 2026-09-24.

Context: a new CSV of the catalogue can add wines and remove wines. The owner does not
want to handle a changed wine.

Decision, by the owner:

- `pipeline/import_catalog.py` replaces `pipeline/seed_catalog.py`. The first import
  into an empty database adds every wine.
- The column `state` of `wine_catalog` holds `Active`, `Disabled`, or `Removed`.
- A wine that the new CSV does not hold becomes `Removed`, also from `Disabled`.
- A `Removed` wine that comes back becomes `Active`. A `Disabled` wine that stays in the
  CSV stays `Disabled`.
- A changed field stops the import with an error. The import writes nothing.
- The table `catalog_source` is removed. The database keeps no record of the imported
  CSV files.

Options that the owner did not select: stop on a wine that comes back; never touch a
`Disabled` wine; keep `seed_catalog.py`; keep a history table of the imports; keep the
last imported file only.

Consequences:

- Decision 3 stays: the key of `wine_catalog` is `wine_slug` alone. This holds because a
  wine never changes. A delivery with a changed wine cannot be imported.
- The database cannot tell which CSV file gave its present state.

## Decision 7 — state changes by a person

Date: 2026-09-24.

Context: the owner wants the buttons `Ignore`, `Remove`, and `Restore` on the Dataset
page. The owner renamed `Ignore` to `Disable` later on 2026-09-24. An ignored wine is not used for embeddings and matches. By rule 4 of decision 6,
the next import would restore a wine that a person removed.

| Question | Options | Decision of the owner |
|---|---|---|
| The name of the ignored state | rename `Disabled` to `Ignored`; keep `Disabled` | Keep `Disabled`. The button reads `Ignore`. |
| The buttons of a `Disabled` wine | `Include` and `Remove`; `Restore` and `Remove` | `Enable` and `Remove`. |
| A wine that a person removed, and the CSV holds it | the import restores it; it stays `Removed` | It stays `Removed`. |

Consequences:

- New column `removed_by`: `import` or `person` for a `Removed` wine, NULL for another
  state. A table check ties it to `state`. Schema file 004 builds the table again,
  because SQLite cannot add a table constraint to an existing table.
- The import restores only a wine that the import removed.
- The lab server writes the columns `state` and `removed_by`. It is not read-only now.
- The button `Disable`, the action `disable`, and the state `Disabled` use one term. The
  first button name `Ignore` did not; the owner renamed it.
- No tool reads `Disabled` yet. The embedding and match tools MUST skip a `Disabled` and
  a `Removed` wine when they read the database.

## Decision 8 — the images of a wine

Date: 2026-09-24. Plan: `docs/plans/08_seed-images.md`.

Context: the owner wants a table for the images of a wine, with an image type, and a
script that stores the main image of each wine from the Strapi `uploads` folder. The
script MUST NOT use the network. `build_catalog.py` asks the live site when a photo name
fits several upload files.

| Question | Options | For | Against | Decision of the owner |
|---|---|---|---|---|
| The match of an unclear photo name | A: the name match alone | No input apart from the delivery. | 57 of 2,103 wines get no image. | A. A load from the website follows later. |
| | B: A, and the live answers of `catalog.jsonl` | 2,098 wines get an image. | A derived file comes back, after the owner removed `catalog.jsonl` from the lab. | |
| The table | one table `wine_image` | One insert for each row. No join. The folder follows from the image type. | The file facts repeat for each wine that shares a file. Each image needs a wine. | One table. |
| | two tables `image` and `wine_image` | One row for each file. An image can exist before it has a wine. | A join for each read. One file can need two folders, because the folder follows from the type of the link. | |
| `match_method` | keep; drop | Keep: the rows state which match is an assumption. The website load can check those rows. | Keep: one more column, with two values for now. | Keep. |
| Test photos | their own table later; the type `testset` in `wine_image` | Own table: a test photo can show a wine outside the catalogue, and it has a label and a set. | | Their own table. There can be several test sets, each with its own photos. |
| Git | ignore `data/images/`; ignore `data/` | | | Ignore `data/`. |

Consequences:

- `extension` depends on the file alone. The table is not in BCNF. Plan 08 states it.
- The foreign key to `wine_catalog` blocks a `DROP TABLE wine_catalog` while
  `wine_image` holds rows. A schema file that builds `wine_catalog` again MUST handle it.
- Git keeps no copy of the database and of the image store. Open question 3 of plan 07
  stays open.
