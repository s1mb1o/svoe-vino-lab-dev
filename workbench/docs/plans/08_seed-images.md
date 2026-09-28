# 08 — The images of a wine, and the main images of the delivery

Date: 2026-09-24.
Status: implemented on 2026-09-24, with the card images of the Dataset page. This plan
is step 4 of
[plan 07](07_sqlite-lab-database.md). The owner messages of 2026-09-24 in
[owner-messages.md](../owner-messages.md) hold the request and the answers.

## Goal

1. A new table holds the images of a wine and the type of each image.
2. `pipeline/seed_images.py` finds the main image of each wine in the Strapi `uploads`
   folder of the delivery. It stores each file as `<sha256>.<extension>`.
3. The script reads no network resource. A wine with no match gets a console message,
   and the run goes on.

## Decisions of the owner

| Question | Options | Decision |
|---|---|---|
| The match of an unclear photo name | A: the name match alone, offline; B: A, and the live answers of `catalog.jsonl` as an extra input | A. The owner adds a load from the website later. |
| The table | one table `wine_image`; two tables `image` and `wine_image` | One table. |
| The column `match_method` | keep; drop | Keep. |
| Test photos | their own table later; the type `testset` in this table | Their own table later. There can be several test sets. Each test set holds its own photos, and the photos link to different wine slugs. |
| Git | ignore `data/images/`; ignore `data/` | Ignore the whole `data/` directory. |

The reasons for each option are in decision 8 of
[decision record 01](../decisions/01_sqlite-lab-database.md).

## The image types and the store

The store is `images/` in the directory of the database file. For
`data/lab.sqlite3` it is `data/images/`.

| `image_type` | Folder | Meaning |
|---|---|---|
| `main` | `main/` | The main image of the wine page on vino-svoe.ru. The source is the Strapi `uploads` folder of the delivery. |
| `main_patched` | `patched/` | The fix of a bad `main` image. A reader MUST use it instead of `main`. |
| `front`, `back`, `label_front`, `label_back` | `additional/` | Extra views for training. |

The folder `testset/` exists. The photos of a test set get their own table in a later
step. No tool fills `patched/`, `additional/`, or `testset/` yet.

## The table `wine_image`

Schema file: `pipeline/schema/005_wine_image.sql`.

| Column | Content |
|---|---|
| `wine_slug` | The wine. A foreign key to `wine_catalog`. |
| `image_type` | One of the six types above. |
| `sha256` | The SHA-256 of the file bytes, 64 lower-case hex characters. |
| `extension` | The file extension in lower case, with no dot. |
| `source_name` | The file name at the source. For `main` it is the upload file name, the value of `upload_file` in `catalog.jsonl`. |
| `match_method` | How the file was found for the wine. |
| `width`, `height` | The pixel size of the file. NULL means that no tool measured it yet. Schema file 006. |

- The key is `(wine_slug, image_type, sha256)`.
- A unique index allows at most one `main` and at most one `main_patched` for each wine.
- Both rows stay when a wine has `main` and `main_patched`. The reader applies the
  override.
- A deviation from BCNF: `extension` depends on the file alone. A file that several
  wines share has one row for each wine. The owner chose one table, so the plan states
  the deviation, as rule 2 of plan 07 requires.
- The column name `source_name` does not follow `catalog.jsonl` (rule 8 of plan 07). The
  column holds the source file of each image type, not only an upload file.

## The command

```bash
python3 pipeline/seed_images.py --db data/lab.sqlite3 \
    ../../svoe-wino-hackaton/dataset/official-2026-09-17/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads
```

The docstring of `pipeline/seed_images.py` holds the full rules. In short:

1. The match is stage 1 of `svoe-wino-hackaton/scripts/build_catalog.py`. The key of
   `csv_photo_name` is compared with the key of each upload name. The wine name is not
   part of the match. `tests/test_seed_images.py` checks that the copy of the rule is
   equal to the rule of `build_catalog.py`.
2. `match_method` = `name-unique`: one upload file fits.
3. `match_method` = `name-identical`: several upload files fit, and their bytes are
   equal. `source_name` is the first file name in sort order.
4. Several upload files with different bytes, or no upload file: no match.
5. A wine of each state gets an image.
6. A second run changes nothing. A wine with another `main` row keeps the row, and the
   script reports a conflict. A stored file with wrong bytes is an error; the script
   does not overwrite it, and it exits with status 1.
7. The script writes the files first, with no lock on the database. Then it writes all
   new rows in one transaction.

## Result on 2026-09-24

The database `data/lab.sqlite3` held 2,103 `Active` wines at schema version 4. The run
applied schema file 005.

| Count | Value |
|---|---|
| upload files indexed | 6,241 |
| matched, `name-unique` | 2,023 |
| matched, `name-identical` | 23 |
| no match, different bytes | 52 |
| no match, no candidate | 5 |
| rows added | 2,046 |
| files written | 2,018 (135 MB) |

- A second run gave `rows added: 0`, `rows unchanged: 2046`, `result: no change`.
- The name of each of the 2,018 files is the SHA-256 of its bytes.
- The run took 6 seconds.

The derived file `svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl`
holds the live answers of 2026-09-17. It names a file for 47 of the 52 wines with
different bytes and for the 5 wines with no candidate. For the 2,023 `name-unique` wines
it names the same file. The owner did not select this input (option B).

## The card image on the Dataset page

The owner asked on 2026-09-24 why the Dataset page showed no catalogue image. The lab
server did not read `wine_image`, and it answered each `/img/` route with HTTP 503. The
owner selected option C of three. Decision 9 of decision record 01 holds the options.

1. `GET /api/dataset` sends three keys in each record: `main_image_url`,
   `main_image_type`, and `main_image_match_method`. They describe the `main_patched`
   image of the wine, else its `main` image. Each is null for a wine with neither. The URL
   is `/images/<folder>/<sha256>.<extension>`.
2. `GET /images/<folder>/<sha256>.<extension>` sends that file from the image store.
   - The folder MUST be `main`, `patched`, or `additional`.
   - The name MUST be 64 lower-case hex characters, a dot, and an extension of
     `a-z0-9`. The route sends no other file, so a request cannot leave the store.
   - The answer has `Cache-Control: public, max-age=31536000, immutable`. The name is
     the SHA-256 of the bytes, so the file at a URL never changes.
   - A missing file or another path gives 404.
3. `pipeline/pages/dataset.html` uses `main_image_url` when a record holds it: for the
   card image, for the large view, and for the filter `without a catalogue image`. A
   record of `scripts/review_server.py` holds `local_path` instead. The page then uses
   `/img/catalog?slug=<slug>` as before.
4. The lab server still answers `/img/` with HTTP 503.
5. The caption below the image names the image type and the match, for example
   `main · name-unique`. A lab record with no image gets the caption `main`. A record of
   the review tool keeps the caption `catalog.jsonl`. The owner asked for this caption on
   2026-09-24 ("fix caption"). It is the caption part of option B.
6. `pipeline/labdb.py` holds the folder of each image type in `IMAGE_FOLDERS`, and the
   store path in `image_store`. `seed_images.py` and `lab_server.py` read both.

Check on 2026-09-24 in headless Chromium, on `data/lab.sqlite3`: 2,103 cards, 2,046
images from `/images/main/`, 57 cards with `no catalogue image`. The large view reads
`1 / 2046`. The filter `without a catalogue image` shows 57 cards. The captions:
`main · name-unique` 2,023, `main · name-identical` 23, `main` 57.

## The sort by image size

The owner asked on 2026-09-24 for a sort of the Dataset page by the image size in pixels.
The owner selected option A of three: store the size in the database. Decision 10 of
decision record 01 holds the options.

1. Schema file `pipeline/schema/006_image_size.sql` adds `width` and `height` to
   `wine_image`. Both MAY be NULL, so `pipeline/seed_patched.py` can still add a row.
2. `pipeline/seed_images.py` reads the size from the header of each stored file with
   Pillow. A new row gets the size. A kept row with a NULL size gets it too. The report
   holds `pixel sizes filled` and `no pixel size`.
3. `GET /api/dataset` sends `main_image_width` and `main_image_height` of the card image.
4. The `Sort` control has two new values: `image size, smallest first` and
   `image size, largest first`. The key is `width * height`. A card with no known size
   stands at the end. Cards of equal size keep the catalogue order.

The run on `data/lab.sqlite3` filled 2,046 sizes in 4 seconds. The smallest image has
55,200 pixels (120 x 460). The largest has 60,239,522 pixels (6337 x 9506).

## The link of the slug

The owner asked on 2026-09-24 that the slug of a card is a link to the page of the wine
on vino-svoe.ru. The page builds `https://vino-svoe.ru/wines/<slug>` from the slug. The
link opens a new tab. The URL is the value of `SITE` in `build_catalog.py`.

## Gotchas

1. The foreign key of `wine_image` blocks `DROP TABLE wine_catalog` while `wine_image`
   holds rows. Schema file 004 built `wine_catalog` again with `DROP TABLE`. A later
   file that does the same MUST handle `wine_image` too. `pipeline/labdb.py` runs each
   file in a transaction with `PRAGMA foreign_keys = ON`, and SQLite ignores a change
   of that pragma in a transaction.
2. The lab server compares the schema version with the number of schema files on each
   request. A new schema file makes the running server answer an error until a tool of
   `pipeline/` migrates the database, for example `pipeline/labdb.py`.
3. `name-unique` is an assumption. Nothing confirms that the website shows that file.
4. `pipeline/seed_images.py` needs Pillow. The lab server does not.
5. A test that adds a `wine_image` row MUST name the columns. A row with positional
   values breaks when a schema file adds a column.
6. The rule of `.gitignore` for the lab data MUST be `/data/`, with the leading slash.
   The first rule `data/` also matched `tests/data/`. So commit `f0c5649` left out the
   CSV variants of `tests/data/`.

## Later steps

These steps are proposals. The owner selects the next step.

1. The load from the website: read `og:image` of the wine page, as stage 2 of
   `build_catalog.py`. It gives a file for the 57 wines with no match, and it can
   confirm the 2,046 wines of `name-unique` and `name-identical`. A new value of
   `match_method` records it, for example `live-og-image`.
2. `main_patched` from `svoe-wino-hackaton/dataset/patched-official-2026-09-17/`. The
   name of each file there is the wine slug.
3. `front`, `back`, `label_front`, and `label_back`. `derived/additional/` of the
   delivery holds a README and no image yet.
4. The test sets. See the next section.

## Input for the test set step

A survey of `svoe-vino-testset` on 2026-09-24 found these facts. It did not design the
table.

1. `config.yaml` names three photo sets: `default` (`dataset/my/`, 4,055 photos under
   1,872 slug directories), `official-real-photos` (100 photos, 68 slugs), and
   `vlmrerank-8b-failed` (180 photos, 108 slugs).
2. Each set has its own `review-labels.json`. A record is
   `labels[<wine_slug>][<photo file name>]`. So one record links one photo to one slug.
3. The field `label` holds `positive`, `negative`, `unusable`, or `variant`
   (`scripts/review_server.py` `LABELS`). The counts: `my` positive 1,644, negative
   584, unusable 251, variant 77, no label 1,059; `official-real-photos` positive 60,
   negative 21, unusable 15, variant 4; `vlmrerank-8b-failed` positive 180.
4. The reserved slug `__null__` means "no wine of the catalogue". It allows `positive`
   and `unusable` alone (`NULL_LABELS`).
5. The same bytes occur under several slugs: in `my`, 419 groups of equal bytes stand
   under 2 to 11 slugs. The same bytes occur in several sets: 179 of the 180 photos of
   `vlmrerank-8b-failed` are also in `my`. A store by SHA-256 keeps one file for each
   group.
6. Other fields of a record: `ts`, `comment`, `by`, `confidence`, `source_url`,
   `reassign_to`, `moved_from`, `copy_to`, `copied_from`, `delete`, `proposed`, and
   `prefilled_from`. The wine note is `wines[<wine_slug>]`.
7. The sets also use `excluded-slugs.json`, `variant-groups.json`, and
   `manual-groups.json`. `vlmrerank-8b-failed/selection.json` records how that set was
   built.
