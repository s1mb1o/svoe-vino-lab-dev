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

## Decision 9 — the card image of the Dataset page

Date: 2026-09-24. Plan: section "The card image on the Dataset page" of
`docs/plans/08_seed-images.md`.

Context: the Dataset page showed no catalogue image. The lab server sent no image in
`/api/dataset`, and it answered `/img/catalog` with HTTP 503. `pipeline/pages/dataset.html`
is shared with `scripts/review_server.py`, which has its own `/img/catalog` route.

| Option | For | Against |
|---|---|---|
| A: the server alone. `/api/dataset` sends `local_path`; `/img/catalog?slug=` sends the file. | The smallest change. The page does not change, so the review tool and the open work of a parallel session on the page stay safe. | The caption stays `catalog.jsonl`. The URL holds the slug alone, so the browser must check each image again. |
| B: A, and the caption shows the image type and `match_method`. | A correct caption. | A change of the shared page while a parallel session changes it. A fallback for the review tool. |
| C: static URLs `/images/<folder>/<sha256>.<ext>` in each record. | The URL changes when the image changes, so the browser keeps each file for good. No database read for an image. | Changes of the server and of the page. Two ways to load a card image in the page. A file route that MUST refuse each other path. |

Decision of the owner: C.

Consequences:

- The page loads `main_image_url` when a record holds it, else `/img/catalog`.
- The route `/images/` admits a name of 64 hex characters and an extension alone.
- The owner asked for the caption part of option B later on 2026-09-24. The caption
  names the image type and `match_method`. The server sends both in each record.

## Decision 10 — the pixel size of an image

Date: 2026-09-24. Plan: section "The sort by image size" of
`docs/plans/08_seed-images.md`.

Context: the owner wants a sort of the Dataset page by the image size in pixels.

| Option | For | Against |
|---|---|---|
| A: `width` and `height` in `wine_image` | One read of each file. Other tools can use the size. `/api/dataset` stays fast. | A schema file and a fill of the old rows. Each tool that adds a row must write the size. |
| B: the server reads the size and keeps it in memory by SHA-256 | No schema change. | About 2 s more for the first page after a start. The database does not hold the size. |
| C: the browser measures the loaded images | The page alone changes. | The browser must load all 2,046 images, 135 MB. |

Decision of the owner: A. The owner also set the rules 9 to 12 of `AGENTS.md`: a schema
change is allowed at any time during development, and a flatten comes later.

Consequences:

- `width` and `height` MAY be NULL. A flatten MAY make them NOT NULL.
- `pipeline/seed_patched.py` does not write the size yet. A card with a patch then
  stands at the end of a size sort.

## Decision 11 — the processing of the images and the table `image`

Date: 2026-09-25. Plan: `docs/plans/09_image-processing.md`.

Context: the owner wants each import to process its images, and to keep the sha256 of
each original, so that no image is loaded two times.

| Question | Options | Decision of the owner |
|---|---|---|
| Keep the originals | A: keep them, and add the processed files; B: keep the processed files alone; C: process later, in a separate command | A |
| The processing | the crop alone; the crop and SAM3 label boxes; other steps | Cut white and transparent borders. SAM3 segments an image with no transparent background. |
| The storage of the link | A: a table of processed files keyed by the sha256 of the original; B: columns in `wine_image`; C: a table `image` for each file, and `wine_image` and `image_derivative` refer to it | C |
| The result of `seg` | the mask as the alpha channel; the box alone | The segmentation of the bottle, the can, or the packet, smoothed and grown a little |
| Several instances | the union; the largest | One package: the largest instance |
| The size of the size sort | the processed file; the original | The processed file |

Consequences:

- The link from a wine to its processed file is a chain of foreign keys:
  `wine_image.sha256` -> `image` <- `image_derivative.source_sha256`, and
  `image_derivative.sha256` -> `image`.
- `wine_image` is in BCNF: `extension`, `width`, and `height` are in `image` now.
- A file that several wines share is processed one time, and SAM3 gets one request for it.
- An import needs the SAM3 service of gx10 for an image with no transparent background.
  When the service does not answer, the image gets no processed file, and the next
  import asks again.

