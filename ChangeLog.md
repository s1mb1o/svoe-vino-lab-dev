# ChangeLog

## 2026-09-25

- The Embeddings page is on. `pipeline/lab_server.py` sends each route that
  `embedding_routes.handles` accepts to `embedding_routes.respond`, for GET, HEAD, and
  POST. `/embedding` is no longer in `DISABLED_PAGES`. `make_server` takes
  `config_path`; `main` passes `--config`. The old routes `/api/embedding` and
  `/img/embedding` stay HTTP 503. The navigation order is now `Dataset`, `Embeddings`,
  `Clusters`, `Testset`, `Runs`, in `NAV` and in the navigation of `dataset.html` and
  `embedding.html`. The owner asked for both on 2026-09-25. New tests in
  `tests/test_lab_server.py` (4): the page, the config path of the routes, the old
  routes, the navigation order. The lab server on 8168 was restarted.
- Plan 12 (`docs/plans/12_testsets-benchmark.md`), approved by the owner: the test sets
  in the database and a lab benchmark runner. New `pipeline/import_testset.py` imports
  `dataset/<set>/` read-only (photos, per-set labels, excluded slugs, variant groups). New
  `pipeline/benchmark.py` sends the photos of a set to a backend of `backends.yaml` and
  writes the run files of `scripts/match_run.py`. The tables are in
  `pipeline/schema_pending/NNN_testset.sql`; the file enters `pipeline/schema/` after the
  flat image store of drink-atlas-workspace-9a [f028b4]. No benchmark runs before that.
- `judge`, `f1`, `metrics_of`, `write_summary`, and their constants moved unchanged from
  `scripts/match_run.py` to the new `scripts/match_scoring.py`; `embeddings_of` moved to
  `scripts/match_backends.py`. Each moved item is byte-identical to commit `a8e113a`. With
  the variant groups of `my`, the moved `metrics_of` gives the `metrics.json` of the run
  `2026-09-24T131126Z-svm-siglip2-448-index-9fbef0a4a2` exactly.
- New rules 25 to 28 of `AGENTS.md`: a schema number is fixed only when the file enters
  `pipeline/schema/`. The sessions -a2, -9a, and -20 agreed; the owner approved.
- New tests: `tests/test_import_testset.py` (10), `tests/test_benchmark.py` (7).
- New file `ACTIVE_WORK.md` and rules 13 to 21 in `AGENTS.md`, section "Work of the
  sessions". Each agent session that works on this project keeps one section there: its
  task, its source, the files that it changes, its state, and the time of the last
  update. A session does not change a file that another section lists; it sends that
  session a message. The owner asked for the file.
- `COMMANDS.md`: the owner's command notes are fixed. The delete command names
  `data/lab.sqlite3`. The load section holds `import_catalog.py`, `seed_images.py`, and
  `seed_patched.py` in one block. The stale pasted replies and the fixed schema version
  are gone. The typo `Pапуск` is `Запуск`.
- `tests/test_seed_patched.py` names the columns of its `wine_image` insert. Schema file
  006 added `width` and `height`, and the insert by position failed.

### The embeddings of the lab: the build, the routes, the page (plan 10)

- New key `embeddings` in `config.yaml`: 11 entries, one for each image embedding model of
  gx10 on the screenshot of the owner, and `local-siglip2-so400m-patch16-naflex-p256`.
  Each entry has a name, an endpoint, options (`extra_body`), and the steps of the views
  `full` (variant C) and `label` (variant F). New key `embedding_python`: the venv
  `~/.venvs/svoe-vino-lab`.
- New module `pipeline/embeddings.py`: the configuration check, the inputs (Active
  wines; `main_patched` replaces `main`), the steps `segment`, `remove_background`,
  `white_background`, `resize`, the `embedding_hash`, the item status, the atomic files,
  the lock, and the job state.
- New CLI `pipeline/build_embeddings.py`: the backends `openai` (the gateway) and
  `local` (Hugging Face on `mps`). It writes `data/embeddings/<name>/index.json`,
  `vectors-<8 hex>.npy`, and `images/<sha256>_<view>.png`, and one JSON event line for
  each step to stdout. SIGTERM stops it after the present batch; the next run continues.
- New module `pipeline/embedding_routes.py` and page `pipeline/pages/embedding.html`:
  the combobox, `Build`, `Stop`, the job rows, and the wine matrix of the prepared
  images. The hook in `lab_server.py` waits for the commit of plan 09.
- The gateway drops the alpha channel (measured). So the configuration check rejects
  `remove_background` with no `white_background`, and a build fails each model input
  with a transparent pixel. The owner asked for an error on 2026-09-25.
- New `requirements-local.txt` and `QUESTIONS.md` (Q1, the label image: answered).
- New tests: `tests/test_embeddings.py`, `tests/test_build_embeddings.py`,
  `tests/test_embedding_routes.py`, with the fixture `tests/embedding_lab.py`: 44 tests.
- The first real build: `gx10-siglip2-so400m-patch16-naflex-p256`. A stop with SIGTERM
  after 416 items, and a second start that continued with the rest.

### An agent may restart the lab server on 8168

- New rules 22 to 24 in `AGENTS.md`, section "The lab server". The owner allows an agent
  to restart `pipeline/lab_server.py` on port 8168 when a change needs it: stop it with
  SIGINT, start it with `--no-browser` in the background with the log
  `work/lab_server.log`, check `/api/dataset`, and tell the owner.

### Each import processes its images: `crop` and `seg`

- New schema file `pipeline/schema/007_image_table.sql`: the table `image` with one row
  for each stored file, and the table `image_derivative` that links an original to its
  processed file. `wine_image` refers to `image`; `extension`, `width`, and `height`
  moved to `image`. The migration keeps each row. The owner chose option C.
- New module `pipeline/derive.py`. An image with transparent pixels loses its border
  (`crop`, the alpha rule of `build_cropped.py`). An image with no transparent pixels
  goes to SAM3 on gx10 with `wine bottle, can, packet` (`seg`); the largest instance
  wins, and its mask is smoothed, grown a little, and becomes the alpha channel. When
  SAM3 finds nothing, the white rule cuts the border. When SAM3 does not answer, the
  image stays unprocessed, and the next import asks again.
- New module `pipeline/imagestore.py`: the store functions of each writer.
- `pipeline/seed_images.py` and `pipeline/seed_patched.py` process each image that they
  store or keep, and take `--sam3 <URL>`. The processed files are PNG files in
  `data/images/cropped/`.
- The Dataset page shows the processed image with the badge `crop` or `seg`. The link
  `open raw image` opens the original. The size sort uses the processed file.
- Tests: `tests/test_derive.py` 14, `tests/test_seed_images.py` 25,
  `tests/test_seed_patched.py` 14, `tests/test_lab_server.py` 21, `tests/test_labdb.py`
  10. No test calls the real SAM3 service.
- The run on `data/lab.sqlite3` migrated it to schema 7 and processed the 2,018
  originals in 4 min 25 s: `crop` 1,876, `seg` 142. One `crop` comes from the white rule:
  SAM3 found no package on a bag-in-box image of three wines. The processed files take
  1.2 GB. A run of `seed_patched.py` on a copy of the database processed the 15 patches
  (`crop` 15). The real database holds no patch yet.
- A known weak result: on 3 bag-in-box images of Союз-Вино, SAM3 cuts out the bottle
  that is printed on the box, and not the box.

## 2026-09-24

### The Dataset page: sort by image size, and the slug links to the wine page

- New schema file `pipeline/schema/006_image_size.sql`: the columns `width` and
  `height` of `wine_image`. Both MAY be NULL.
- `pipeline/seed_images.py` reads the pixel size of each stored file with Pillow. A new
  row gets it; a kept row with no size gets it too. On `data/lab.sqlite3` the run filled
  2,046 sizes.
- `/api/dataset` sends `main_image_width` and `main_image_height`.
- The `Sort` control has `image size, smallest first` and `image size, largest first`.
  The key is the pixel count. A card with no known size stands at the end.
- The slug of a card is a link to `https://vino-svoe.ru/wines/<slug>`. It opens a new
  tab. The owner asked for it.
- `AGENTS.md` (`CLAUDE.md`) has the new rules 9 to 12: a schema change is allowed at any
  time during development, and the owner asks for a flatten later.
- Tests: `tests/test_seed_images.py` 22, `tests/test_lab_server.py` 20,
  `tests/test_labdb.py` expects schema version 6. New smoke cases I7a and S28 to S30.
  The tests of `seed_images.py` use real PNG pictures now.

### The patched main images: `pipeline/seed_patched.py`

- New CLI `pipeline/seed_patched.py`. It stores each file of
  `svoe-wino-hackaton/dataset/patched-official-2026-09-17/` as
  `images/patched/<sha256>.<extension>` and writes one `main_patched` row of
  `wine_image` for its wine. The file name before the extension is the wine slug.
- The patch folder is the truth for the patches, as the owner chose: a new file replaces
  the row of its wine, and a missing file deletes the row. The old file stays in the
  store. `match_method` is `slug-name`.
- The script skips hidden files, `_originals/`, and `README.md`. A slug that
  `wine_catalog` does not hold gets a message. Two files for one slug are an error.
- It reuses `sha256_of` and `store_file` of `pipeline/seed_images.py`, and
  `labdb.image_store` and `labdb.IMAGE_FOLDERS`.
- On a copy of the database: 15 rows added, 15 files written. The lab server shows the
  15 patches as card images.
- Plan 07 step 5, new tests `tests/test_seed_patched.py` (11 cases), smoke cases P1 to P7.

### The Dataset page shows the main images

- `GET /api/dataset` sends `main_image_url` in each record: the `main_patched` image of
  the wine, else its `main` image, else null.
- New route `GET /images/<folder>/<sha256>.<extension>` of the lab server. It sends one
  file of the image store `data/images/`, with a cache time of one year. It admits a
  name of 64 hex characters and an extension alone; another path gives 404.
- `pipeline/pages/dataset.html` loads `main_image_url` for the card image, the large
  view, and the filter `without a catalogue image`. A record of
  `scripts/review_server.py` still loads `/img/catalog`.
- `pipeline/labdb.py` holds `IMAGE_FOLDERS` and `image_store`. `seed_images.py` uses
  them.
- On `data/lab.sqlite3`: 2,046 cards show an image, 57 cards show `no catalogue image`.
  The owner selected option C; decision 9 of decision record 01 holds the options.
- The caption below the card image names the image type and the match, for example
  `main · name-unique`, instead of `catalog.jsonl`. `/api/dataset` sends
  `main_image_type` and `main_image_match_method` for it. A record of the review tool
  keeps `catalog.jsonl`.
- `.gitignore` holds `/data/` instead of `data/`. The first rule also ignored
  `tests/data/`.
- Tests: `tests/test_lab_server.py` 19 cases. New smoke cases S23 to S27.

### The Dataset page: no colour line, and the slug above the name

- A card no longer shows the line `Colour: …`. The owner asked for it. The colour stays
  in `full catalog.jsonl record` and in the search.
- The slug with its `copy` button is the first line of a card, above the name. The
  owner asked for it.

### The Dataset page: fast state changes, and `Ignore` is `Disable`

- A state click took 1.8 to 2.1 s. The server write took 2 to 4 ms. The time went to two
  full renders of the list: about 0.7 s each for 2,103 cards and 6.9 MB of HTML.
- A state change now renders its own card alone. A card that leaves the view of the
  `State` filter is taken out of the list. The busy mark goes on the buttons alone.
- Each card has `content-visibility: auto`. A full render takes about 0.14 s, and a
  state click about 0.1 s, in headless Chromium.
- A link `/dataset#<slug>` scrolls two times, so the card still lands below the header
  when the cards out of view have an estimated height.
- The owner renamed the button `Ignore` to `Disable`. The API action is `disable` now.
  The button, the action, and the state `Disabled` use one term.
- New smoke cases S21 and S22.

### The images of a wine: the table `wine_image` and `pipeline/seed_images.py`

- New schema file `pipeline/schema/005_wine_image.sql`: the table `wine_image`. One row
  links a wine, an image type, and a stored file by its SHA-256. The types: `main`,
  `main_patched`, `front`, `back`, `label_front`, `label_back`. A wine has at most one
  `main` and one `main_patched`. The columns `source_name` and `match_method` record the
  source file and the match.
- New script `pipeline/seed_images.py`. It finds the main image of each wine in the
  Strapi `uploads` folder by `csv_photo_name`, with stage 1 of `build_catalog.py`. It
  reads no network resource. It stores each file as
  `data/images/main/<sha256>.<extension>`. A wine with no match gets a console message.
- The run on `data/lab.sqlite3`: 2,046 of 2,103 wines matched (`name-unique` 2,023,
  `name-identical` 23), 57 no match, 2,018 files, 135 MB. A second run changes nothing.
- New folders `data/images/patched/`, `data/images/additional/`, and
  `data/images/testset/`. No tool fills them yet. The photos of the test sets get their
  own table later.
- New plan `docs/plans/08_seed-images.md` and decision 8 of decision record 01. Plan 07
  marks step 4 as done.
- Tests: `tests/test_seed_images.py` 19 cases. `tests/test_labdb.py` expects schema
  version 5 and the table `wine_image`. New smoke cases I1 to I9. The cases D2, D10,
  D10a, S1, and S3 expect schema version 5.

### Git ignores the whole `data/` directory

- `.gitignore` now holds `data/` instead of the two `*.sqlite3` rules. The directory
  holds the lab database and the image store `data/images/`. The owner asked for it.

### The Dataset page: state buttons and the state filter

- Each card holds buttons below the catalogue image. An `Active` wine: `Ignore` and
  `Remove`. A `Disabled` wine: `Enable` and `Remove`. A `Removed` wine: `Restore`. The
  card shows the tag `disabled`, `removed by import`, or `removed by person`.
- New filter `State`: `All (except Removed)`, the default, and `Removed`.
- New route `POST /api/wine-state` with the actions `ignore`, `enable`, `remove`, and
  `restore`. It allows the listed changes alone and answers 409 for another change. The
  lab server writes the columns `state` and `removed_by` alone; a GET stays read-only.
- New schema file `pipeline/schema/004_removed_by.sql`: the column `removed_by`
  (`import` or `person`) and a table check that ties it to `state`. It builds the table
  again and keeps each rowid. An earlier `Removed` wine gets `import`.
- `pipeline/import_catalog.py` restores only a wine that the import removed. A wine
  that a person removed stays `Removed`, and the report counts it under
  `kept removed by a person`.
- `Ignore` sets the state `Disabled`. No tool reads the state for embeddings and matches
  yet. Decision 7 of decision record 01 records the choices of the owner.
- Tests: `tests/test_labdb.py` 9, `tests/test_import_catalog.py` 20,
  `tests/test_lab_server.py` 15 cases. New smoke cases S13 to S20, D10a, and D10b.

### The Dataset page: no source panel

- The owner removed the source panel above the list: `catalog.jsonl`, `patch directory`,
  `alternative directory`, `barcode file`, and the two Atlas lines. The panel and its
  style are gone from `pipeline/pages/dataset.html`.
- An error of `/api/dataset` shows in the list now, with its reason.
- `/api/dataset` of the lab server no longer sends `catalog_file`. Only the panel read it.

### The catalogue import: add and remove wines

- New schema file `pipeline/schema/003_wine_state.sql`. It adds the column `state` to
  `wine_catalog`: `Active`, `Disabled`, or `Removed`, with the default `Active`. It drops
  the table `catalog_source`. The database keeps no record of the imported files.
- New CLI `pipeline/import_catalog.py`. It replaces `pipeline/seed_catalog.py`, which is
  removed. The first import into an empty database adds every wine. A later import adds
  the new wines as `Active`, and marks each missing `Active` or `Disabled` wine `Removed`.
  A `Removed` wine that comes back becomes `Active`. A `Disabled` wine in the CSV stays
  `Disabled`. A changed field of a wine stops the import, and the error names each field.
  The import writes all changes in one transaction under the write lock.
- New fake variants of the official CSV in `tests/data/`, from
  `tests/data/make_catalog_variants.py`: v2 and v3 add and remove wines, v4 changes one
  field. `tests/data/README.md` states the expected import results.
- The lab server sends `state` in each record of `/api/dataset`, and the start report
  counts the wines of each state.
- Tests: `tests/test_seed_catalog.py` is replaced by `tests/test_labdb.py` (7 cases) and
  `tests/test_import_catalog.py` (17 cases). `tests/test_lab_server.py` has 11 cases.
- Plan 07 steps 1 and 2 and decision 6 of decision record 01 describe the rules.

### The lab server: the Dataset page on the database

- `config.yaml` holds two keys now: `rootdir` and `database_file`. The owner removed each
  JSON file and each directory. The database is the only source of the lab data.
- New `pipeline/lab_server.py` on port 8168. It opens the database read-only for each
  request and checks the schema version. `GET /dataset` serves the Dataset page.
  `GET /api/dataset` answers the 2,103 rows of `wine_catalog`, with `wine_slug` under
  the key `slug` of the page.
- Clusters, Embeddings, Testset, Runs, and `/docs` are disabled for now. Each one answers
  the new notice page `pipeline/pages/disabled.html` with HTTP 503 and the full
  navigation. Each other `/api/` route answers HTTP 503 with a JSON error. No part of a
  page is removed.
- The Dataset page and the colour theme moved out of `scripts/review_server.py` into
  `pipeline/pages/dataset.html` and `pipeline/pages/theme.css`. New
  `pipeline/lab_pages.py` reads them for both servers. Each page string of
  `review_server.py` stayed byte-identical at the move.
- Fix on the Dataset page: `safeUrl` gives no link for an empty value. Before, a record
  with no `page_url` or `image_url` got `site page` and `source image` links to the
  Dataset page itself.
- Port 8168 is recorded in `PORTS_USED.md`. The review tool of `svoe-vino-testset` keeps
  8154.
- The database file is `data/lab.sqlite3` now, with no delivery directory. The owner
  chose the flat layout. `database_file` stays relative to `rootdir`, so its value is
  `svoe-vino-lab/data/lab.sqlite3`. `.gitignore` excludes `data/**/*.sqlite3` at any
  depth. The earlier rule `data/*/*.sqlite3` did not match the flat file.
- New tests `tests/test_lab_server.py`, 10 cases. New smoke cases S1 to S12.
- The tools of `scripts/` read JSON files through `scripts/common.py`. They do not start
  with the new `config.yaml`, and their 5 test modules stop at the import.

### Project rules and the log of the owner messages

- New `AGENTS.md` with the rules of this project. `CLAUDE.md` is a symbolic link to it.
  The file links to the workspace rules in `../CLAUDE.md`.
- New rule: an agent records each message of the project owner verbatim in
  `docs/owner-messages.md`, before the work on it starts. The log starts with the
  messages after 2026-09-24 21:37. Earlier messages are not recorded.

### The lab database: the key column is `wine_slug`

- New schema file `pipeline/schema/002_wine_slug.sql`. It renames the column `slug` of
  `wine_catalog` to `wine_slug`, the name of `code-map.json` and `embedding-ignore.json`.
  SQLite renames the column in the `CHECK` constraint too.
- `pipeline/labdb.py` applies the file to an existing database at version 1. The rows
  stay. A new database gets schema version 2.
- `pipeline/seed_catalog.py` writes the column `wine_slug`.
- New test: a version 1 database keeps its rows and its constraint after the rename.
- Plan 07, rule 8: the key column of a wine is `wine_slug`.

### The lab database: steps 1 and 2

- New plan `docs/plans/07_sqlite-lab-database.md` and decision record
  `docs/decisions/01_sqlite-lab-database.md`. One SQLite database holds the lab state of
  one catalogue delivery. The tables are in BCNF.
- New `pipeline/labdb.py`. It creates the database and applies the schema files of
  `pipeline/schema/` in number order. `PRAGMA user_version` holds the version.
- New schema file `pipeline/schema/001_wine_catalog.sql`: the tables `catalog_source` and
  `wine_catalog`. The columns of `wine_catalog` are the nine columns of
  `strapi_output0709.csv`, with the names of `catalog.jsonl`.
- New CLI `pipeline/seed_catalog.py`. It seeds `wine_catalog` from a Strapi CSV. It trims
  each value, drops exact duplicate rows, and stops on two different rows for one slug.
  It refuses a database that is not there and a second delivery.
- New database `data/catalog-2026-09-17/lab.sqlite3`: 2,103 wines from 4,147 CSV rows.
  All 2,103 × 8 values equal `catalog.jsonl`. `.gitignore` excludes the database file.
- New tests `tests/test_seed_catalog.py`, 13 cases.

### Manual cluster rule editor

- Each `Label rule` block on `/clusters` has an `Edit rule` button.
- The editor changes the rule text, the questions, and each card's expected answer.
- The editor can add or remove questions. A rule has at most three questions.
- New route `POST /api/cluster-rule-edit` stores the edit.
- The server applies the rule checks again. It recomputes the valid questions and the
  mode.
- A manual edit keeps the build identity. A later VLM rebuild replaces the edit.

### Model input previews on the Runs page

- A click on a matched photo now opens a lazy strip of the derived images that the
  matcher passed to an embedding model.
- The same strip shows the query images that the matcher passed to a VLM. Each such
  preview has a `VLM` badge.
- New route `GET /api/run-inputs` rebuilds the model-bound bytes from the run, the
  matcher configuration, and the content-addressed crop cache. It does not call a
  model or SAM3.
- The route checks the source SHA-256. It refuses an inexact reconstruction after the
  source image changes.
- A barcode or QR short-circuit states that no embedding model ran.

### External pictures in the Testset sideboard

- The Testset sideboard accepts image files from the desktop and images dragged from
  another browser page.
- A dropped picture goes directly into the durable `my/` inbox. It has no wine, label,
  score, or comment. The page shows it at once for future distribution.
- New routes `POST /api/inbox-upload` and `POST /api/inbox-fetch` store the two forms
  of external drop.
- The server reads the image type from the bytes. It removes path parts and unsafe
  characters from the source name. It does not replace a file with the same name.
- The empty sideboard and its help text now state that it accepts external images.

### Embedding input page

- Every page uses the navigation order `Dataset`, `Clusters`, `Embeddings`, `Testset`,
  `Runs`. The earlier `Review` label is now `Testset`.
- New page `/embedding`. It shows the cropped main image and segmented label in one
  column. Each additional view gets another column with its full image and label.
- Every image cell uses a checkerboard. A missing derived file stays visibly missing.
- The Show filter has `Patched image` for wines whose main image comes from a patch.
- Each prepared image has an `Ignore` or `Use` control. The page writes
  `svoe-vino-matcher/dataset/embedding-ignore.json`.
- An ignored image stays visible in grayscale. Its dashed border and `Use` button
  identify the state.
- The matcher filters the four image kinds independently. The ignore fingerprint
  changes every affected index file name.
- A label pipeline MAY name `source.alternative_dir` to index segmented labels of
  additional views.

### Checkerboard preview for Dataset images

- A click on a catalogue image or a patch image opens a checkerboard modal over the
  Dataset page. It does not open a new page.
- A border shows the displayed image boundary. The header shows the natural pixel
  dimensions and the file name.
- Arrow buttons and the Left and Right keys move through the current filtered and
  sorted list. Escape closes the modal without changing the page scroll position.
- The preview scales a tall image to fit the available height. It shows no scrollbar.
- The preview has an `open raw image` link.
- Image elements and API clients continue to get the original image bytes.

### All Dataset records on one page

- The Dataset page shows all records that pass the current filter.
- The `Rows`, `Previous`, and `Next` controls are removed.
- Search waits 180 ms after input before it rebuilds the full list.
- Catalogue and patch images keep native lazy loading.
- A row does not show the wine description. The description stays searchable and stays
  in `full catalog.jsonl record`.

### Label-only cluster rules

Plan: `docs/plans/06_label-only-cluster-rules.md`. The owner chose the label crops with
a label-only prompt, and the vintage policy in the same rebuild.

- Stage 2 of `scripts/cluster_rules.py` sends the label crop of each card from
  `bottle_label_dir` on white, scaled to a long side of 768 pixels, UP or down. A card
  with no label crop sends its catalogue picture with a caption that states it.
- The prompt of stage 2 allows only features that are printed on the label. It states
  that some catalogue pictures are drawings, and that a drawing shows only the label
  correctly. It asks for texts exactly as the label prints them, in their own alphabet.
  It allows a vintage question only when the catalogue names of two cards state two
  different years.
- A card that shares its catalogue picture with another card of its cluster gets a
  caption that names that card: 43 cards of 21 clusters.
- The label description goes into stage 2 without the key `bottle`. Stage 1 does not
  change.
- `check_rule` enforces two new kinds. A question of kind `bottle` (the glass, the
  liquid, the capsule, the cork, the shape of the bottle) is never valid, and a rule text
  about such a feature gives mode `none`. A question of kind `vintage` keeps a year only
  when the name or the slug of the card states it.
- `RULES_SHA` holds the picture setting and the captions, and `rule_inputs_sha` holds
  the paths of the label crops. Every rule of 2026-09-23 became stale, and all 255 rules
  are built again. The old rules file is kept as
  `work/catalog-cluster-rules.2026-09-24T082150.json`.
- The page `/clusters` names the reason for a struck question of kind `bottle` or
  `vintage`.
- `scripts/cluster_rules_report.py` has the option `--rules` for the post hoc score of
  an older run, and a section with the paired numbers for each half of the wines.
- The vintage variants, added by the owner during the rebuild: when cards differ only
  by the vintage year, and one card states no year, that card is the card of every
  vintage that no other card states. A year counts from the name, the slug, or the
  label description. Only the 43 mixed clusters get the note `VINTAGE_NOTE` in their
  prompt, so the other rules stay current. `check_rule` keeps the mark `other` only for
  a card with no year that differs from a card with a year only by the vintage.
- `README.md`, `SMOKE_TESTS.md` (L16 to L23), and `ResearchLog.md` describe the change.
- The benchmark: run `runs/2026-09-24T080721Z-svm-label-gw-cluster-rules-label-only-rules`.
  Against the base, R@1 0.8161 → 0.8355, 61 wins, 30 losses, p 0.002; negatives
  0.8262 → 0.8451. Against the run v2, +0.0038 R@1, p 0.47, not significant. The
  section «Result» of the plan holds the details.
- The plan holds six open questions for the owner, Q1 to Q6.

### Drink Atlas Core product binding on the Dataset page

- Each Dataset row shows its effective Drink Atlas Core product UUID.
- An `open` link after `copy` opens the matching product page on the local Drink Atlas
  Core service at `http://127.0.0.1:8157/products/<uuid>`.
- Automatic matches come from `atlas_matches_file`. The page marks them `automatic`.
- The `+` or `edit` button opens a UUID input with save checkmark and cancel cross
  icons. The checkmark writes a manual binding. The cross cancels and writes nothing.
- `POST /api/dataset-atlas-binding` writes the manual overlay in
  `atlas_bindings_file`. A manual value replaces the automatic value for that slug.
- The automatic match file does not change. Several Svoe Vino slugs MAY bind to one
  Atlas product UUID.

### Barcode and QR URL entry on the Dataset page

- Each Dataset row shows its product barcodes and a `+` button.
- The `+` button opens a text input with save checkmark and cancel cross icons. The
  checkmark writes the value. The cross cancels the new row and writes nothing.
- `POST /api/dataset-barcode` adds one value to `barcode_file`. One slug MAY have more
  than one value. A value cannot belong to two slugs.
- Each saved barcode has a small red `×` button. A confirmed click removes only that
  barcode. The server preserves the QR code and the other fields of the wine record.
- `DELETE /api/dataset-barcode?slug=<slug>&barcode=<value>` performs the removal. A
  wine with no barcode keeps its structured record with `barcode: null`.
- Each Dataset row has a `QR URLs` editor with the same `+`, save checkmark, cancel
  cross, red `×`, and `copy` controls. Each saved URL also has `open`.
- `POST` and `DELETE /api/dataset-qr-url` add and remove URL values in the `qr_code`
  field. The server normalizes the URL and prevents one normalized URL from belonging
  to two wines.
- The barcode matcher already reads `qr_code`. A matching scanned URL identifies the
  wine before visual matching.
- The page and `svoe-vino-matcher` share `svoe-vino-matcher/dataset/code-map.json`.

### Alternative photos on the Dataset page

- Each Dataset row has an `Alternative photos` area at the right. It accepts multiple
  images by drag and drop or by a file chooser.
- Additions appear as candidates. Active images can be marked for removal. `Apply`
  writes all pending changes of the row. `Cancel` writes nothing.
- `alternative_dir/<slug>/` holds the active files. A removal moves a file to
  `alternative_dir/.trash/<slug>/` for recovery.
- `POST` and `DELETE /api/dataset-alternative` apply the staged changes.
- `svoe-vino-matcher` reads the same directory and indexes every file as another view
  of the slug. An alternative does not replace the main catalogue picture or a patch.

### Patch changes on the Dataset page

- A `no patch` place accepts an image by drag and drop or by a file chooser. The page
  shows the image as a candidate. It writes the file only after `Apply`.
- An existing patch has a `Remove` button. Removal stays pending until `Apply`.
  `Cancel` discards a pending addition, replacement, or removal.
- `POST /api/dataset-patch` applies an image. `DELETE /api/dataset-patch` applies a
  removal. The server validates the slug, the size, and the image bytes.
- A replaced or removed patch moves to `patch_dir/.trash` for recovery.
- Existing package crops and label crops for the slug move to `.trash` in their
  directories. Another page cannot keep showing pixels from the old patch.

### The dataset `vlmrerank-8b-failed`

- New dataset `vlmrerank-8b-failed` in `config.yaml`. It holds the positive photos of
  `default` whose true slug was not at rank 1 in the run
  `2026-09-18T195710Z-svm-vlmrerank-8b-siglip2-448-bench`.
- The run holds 184 such photos. 180 photos of 108 wines are copied into
  `dataset/vlmrerank-8b-failed/photo/`. Each file keeps its path `<slug>/<file>` and the
  SHA-256 that the run recorded.
- 4 photos stay out, because their label in `default` is `negative` now:
  `abrau-dyurso-az-abrau-bayanshira-beloe-suhoe-12/02_manual.jpg`,
  `abrau-dyurso-russkoe-igristoe-koshernoe-bryut-shardone-beloe-13/04_conf095.jpg`,
  `abrau-dyurso-udelnoe-vedomstvo-imperatorskoe-beloe-bryut/01_conf095.jpg`, and
  `inkermanskiy-zmv-inkerman-muskat-polusladkoe-beloe-13/01_conf095.jpg`.
- The label entries of the 180 photos and the notes of their wines are copied without
  a change. `excluded-slugs.json`, `variant-groups.json`, and `manual-groups.json` are
  copies of the files of `default`. 9 photos lie on excluded slugs, so a run takes 171
  photos.
- `dataset/vlmrerank-8b-failed/selection.json` records the rule, the source run, and
  each of the 184 photos.
- The runs of the set go to `dataset/vlmrerank-8b-failed/runs/`. Port 8167 is assigned
  to the review tool of this set.
- `README.md`, `ResearchLog.md`, and `SMOKE_TESTS.md` (F1 to F5) describe the set.

## 2026-09-23

### Dataset validation

- The Dataset page has a `Validate` button. Its dialog explains and runs three
  read-only checks: the website slug set, exact source image bytes with SHA-256,
  and the source image file on each `wine_slug` page.
- The checks run in one background job. The dialog shows progress and keeps the
  last result when it is closed and opened again.
- New routes `GET /api/dataset-validation` and `POST /api/dataset-validation`.
  The POST route refuses a second job while one job runs.
- The slug check reads the public wine sitemap. The page check reads `og:image`.
  The image check states that a resize service can re-encode the same visible image.

### Dataset page

- New page `/dataset`. It shows every record of the configured `catalog.jsonl`.
- Each row shows the unmodified catalogue image and the patch image next to it.
  A row with no patch shows an explicit `no patch` place.
- The page shows the main catalogue fields in the row. The control
  `full catalog.jsonl record` shows every field of the source record.
- Search reads every field. Filters select patched records, unpatched records, or
  records without a catalogue image. Pagination keeps the page responsive.
- New read-only routes `GET /api/dataset`, `GET /img/catalog`, and `GET /img/patch`.
- The navigation of every page includes `Dataset`.

### The benchmark of the cluster rule step

- Run `runs/2026-09-23T224548Z-svm-label-gw-cluster-rules-qwen38max-rules-v2`: R@1
  0.8156 -> 0.8313, 47 wins, 22 losses, exact McNemar p 0.004; without the `confusion`
  clusters 0.8244, p 0.038. `ResearchLog.md` and the section «Result» of
  `docs/plans/05_cluster-label-rules.md` hold the analysis. A first full run was stopped
  after about 600 photos for the verdict fault of `svoe-vino-matcher`.
- The rules of the 99 clusters that the test set cannot trigger are built after the
  benchmark, for the page `/clusters`.

### Stage 2 of the label rules runs on `qwen3.8-max`

- The owner's decision: stage 2 runs once, so it uses `qwen3.8-max` of the QwenCloud
  Token Plan, with thinking, 4 requests at a time. New keys `rules_url`,
  `rules_model`, `rules_api`, `rules_key_env`, `rules_thinking`, `rules_workers`, and
  `rules_timeout_s` in the block `cluster_rules` of `config.yaml`. The key is read from
  `QWENCLOUD_TOKEN_PLAN_API_KEY` at run time.
- Stage 1 and the re-rank keep the local `qwen3.5-9b`.
- The prompt of stage 2 keeps only major differences. Every rule is therefore stale
  and is built again.
- `scripts/11_cluster_rules.py` builds the rules of stage 2 in parallel.
- A mark that only some cards carry, such as a kosher mark, gets a yes/no question
  with "yes" or "no" for each card. Before this rule the check struck every kosher
  question, because only one card held a non-null answer.

### The letters of a rule on the page `/clusters`

- `GET /api/clusters` gives the map `letters` of each rule: the letter that stage 2
  used for a card, to the slug of that card.
- The badge of each card and the head of the sheet show the letter beside the number,
  and `the cards of the letters` under the rule text names the card and the slug of each
  letter. The prompts do not change.

### The answer of the VLM rule step on the page `/runs`

- A row whose candidates hold the `explain` record of the cluster rule step shows a box
  `VLM` under the frame of the top cluster: the mode, the cluster id, the time of the
  call or `from the cache`, each question with the answer, the score of each card of the
  window, and whether the answer moved a card to rank 1. A run that did not record the
  questions takes their text from the current rule, and the box states that.
- New filters `rule_acted` and `rule_changed` of `GET /api/run` and of the page.
- The strip of the candidates aligns its cards at the top, so a card next to the box
  keeps its height.
- `README.md`, `docs/API.md`, `docs/openapi.yaml`, and `SMOKE_TESTS.md` (R30 to R33)
  describe the change.

### Label rules for the catalogue clusters

Plan: `docs/plans/05_cluster-label-rules.md`.

- New stage `scripts/11_cluster_rules.py` with the module `scripts/cluster_rules.py`.
  Stage 1 asks the VLM `qwen3.5-9b` (thinking off) to describe the label of each card
  of each cluster. Stage 2 asks where the labels of one cluster differ, and writes the
  cluster rule: a difference sheet of questions with the expected answer of each card,
  and a rule text. The note of the reviewer goes into stage 2. The code drops a question
  about a bottle number, and a question about the alcohol value when another question
  separates the cards.
- New files `dataset/catalog-cluster-rules.json` (the descriptions and the rules) and
  `dataset/catalog-cluster-notes.json` (the notes of the reviewer).
- New block `cluster_rules` of `config.yaml`.
- `.gitignore` ignores the lock files `*.lock` next to the two new JSON files.
- `GET /api/clusters` adds `key`, `notes`, `rule` and `rule_status` to each cluster,
  the label description to each card, and the field `rules`.
- New routes `POST /api/cluster-note` and `POST /api/cluster-rule`.
- The page `/clusters` shows a `Label rule` block in each cluster, with the sheet, the
  rule text, the note editor, and the buttons `Save note` and `Rebuild rule`. Each card
  shows its `label description`. New filter `Rule`.
- The note of the «Фантом» cluster is stored: «pay attention to numbers in bottom left
  corner of bottle (30/70), (50/50), (70/30)».
- `match_backends.parse_answer` keeps the field `explain` of a candidate.
- New backend `svm-label-gw-cluster-rules` in `backends.yaml`: the pipeline
  `cluster-rules-difference-gateway` of `svoe-vino-matcher` on port 8164, with
  `explain=1`.
- New script `scripts/cluster_rules_report.py`: the report of one run against its base,
  with a replay over the clusters without the `confusion` signal.
- `config.yaml` names the indexes of 2026-09-23 for the clusters: `gateway-6e12e149fe`
  and `gateway-b57810da3d`. The new build of `dataset/catalog-clusters.json` holds the
  same 255 clusters and the same links as the build of 2026-09-22. The old file is
  kept as `work/catalog-clusters.2026-09-22T231210.json`.
- `docs/API.md`, `docs/openapi.yaml`, `README.md`, `SMOKE_TESTS.md` (L1 to L14) and
  `ResearchLog.md` describe the change.

### The cluster frame of the page `/runs`

- Two or more candidates that stand next to each other in the strip and belong to one
  catalogue cluster now share one frame in the accent colour. The tooltip of the frame
  names the cluster id, the kind, and the size. A cluster card that stands apart from
  the others gets no frame.
- The frame holds a link to the cluster details. The link opens `/clusters` and scrolls
  to that cluster.
- The page reads `GET /api/clusters` once at start. When the cluster file is missing
  or the request fails, the page shows no frame and works as before.

### Backend for the hard cases

- New backend `svm-label-gw-difference` in `backends.yaml`. It asks the pipeline
  `difference-ensemble-gateway-photo-label` of `svoe-vino-matcher` on port 8164: the
  gateway ensemble, re-ranked inside one producer by the label words that separate
  its cards. Plan: `svoe-vino-matcher/docs/plans/02_sibling-difference-rerank.md`.

### Cropped catalogue photos

- New key `bottle_cropped_dir` of `config.yaml`. It names the catalogue photos without
  their empty border, one PNG file per wine slug.
  `svoe-wino-hackaton/scripts/build_cropped.py` writes them. The project owner asked
  for these pictures for display and for training.
- `common.catalogue_picture` states the order of the catalogue picture: the crop, then
  the patch, then the photo of the catalogue record. `GET /img/bottle`, the field
  `bottle_path` of the agent API, `scripts/08_variants.py`, and `scripts/03_embed.py`
  use it. The mark `patched` does not change.
- A patch that changed after its crop wins over the crop, because such a crop was cut
  from the picture before the correction. The tool prints a warning at start for each
  such patch.
- The pixel checks `candidate_is_catalog_photo` and `catalog_photo_twin` still read the
  catalogue photo of the delivery, because they look for a copy of that photo.
- `scripts/03_embed.py` scores only the candidates that have no `sim` yet. The scores of
  earlier runs were made against the old reference and stay as they are.
- New backends `svm-siglip2-448-bordered` and `svm-siglip2-448-cropped`. Each one pins
  the index file of `siglip2-448`, so the two pictures of the catalogue are compared on
  one server with no restart.
- New backends `svm-crop-ab-bordered-<pipeline>` and `svm-crop-ab-cropped-<pipeline>` for
  seven pipelines. The `bordered` entries ask a temporary baseline server on 8165, which
  was stopped after the runs of 2026-09-23, so they answer nothing now. The runs are
  `runs/2026-09-23T0*-svm-crop-ab-*`. The result is in `svoe-vino-matcher/ResearchLog.md`,
  entry "The cropped catalogue pictures in seven more pipelines".

## 2026-09-22

### The large view of the page `/clusters`

- A click on a card picture or on a confused photo opens a large view. The caption
  names the card, or the photo and the card that the run answered, and states the
  place in the cluster and in the view.
- `Left` and `Right` move over the images of one cluster: the cards first, then the
  confused photos. `Up` and `Down` open the same place in the previous or the next
  cluster, hold at its last image when the place is after its end, and scroll the page
  to that cluster. The first and the last image hold. `Esc` or a click on the dark
  ground closes the view. The view holds four buttons for the same moves.
- This follows the large view of the runs page. A click with a modifier key still
  opens the picture in a new tab. A click on a confused photo no longer opens the
  review page; the link `review` of the caption does that, in a new tab.
- The old picture is hidden while the next one loads, so the caption never stands
  under the picture of the step before.

### Catalogue clusters, and the page `/clusters`

- Added `scripts/10_clusters.py`. It finds the clusters of catalogue cards that the
  matcher confuses, or can confuse, over the whole catalogue of 2,103 cards. It
  writes `dataset/catalog-clusters.json`. A later re-rank step reads the same file.
  The plan and the four decisions of the owner are in
  `docs/plans/04_catalog-clusters.md`.
- Four signals join two cards: `name` (same producer, name and category after
  normalisation, and grapes that agree), `photo` and `label` (the SigLIP 2 cosine of
  the catalogue photos and of the label crops, at or above 0.95), and `confusion` (at
  least 2 positive photos that a run answered as the other card). A link records every
  signal that passed, and the cosines also when they did not pass.
- The vectors come from the index files of `svoe-vino-matcher`, so the script calls no
  service and runs in under a second.
- `config.yaml` gained the block `clusters`. `scripts/common.py` reads it as
  `CLUSTERS` and `CLUSTERS_FILE`, and the start report of every script names
  `clusters_file`.
- The review tool serves the new page `GET /clusters` and the route
  `GET /api/clusters`. The page shows the photos of each cluster side by side, the card
  fields, the label counts, and the evidence of each link with the confused test
  photos. It writes nothing. `/clusters#<slug>` opens the cluster of a card. The route
  reads the file at each request, so a new build needs no restart.
- Every page gained the link `Clusters` in its navigation.
- `variant-groups.json`, `scripts/08_variants.py`, and the review table did not
  change.
- Measured with the defaults: 255 clusters over 630 cards, the largest of 10 cards;
  53 `same-wine`, 22 `mixed`, 180 `look-alike`. The three Abrau-Durso Pinot Noir cards
  stand in one cluster with the Cabernet Sauvignon `-125` of the same label line. Read
  `ResearchLog.md` for the choice of the defaults.

### Three backends for the label experiment

- `backends.yaml` gained `svm-label-gw-photo`, `svm-label-gw-label` and
  `svm-label-gw-ensemble`. They answer from `svoe-vino-matcher/config.label.yaml`
  on port 8164, not from the main config on 8158, so the label experiment is
  measured without a change to the recognizer that serves 8158.
- The three differ in ONE thing: which picture is embedded. `-photo` embeds the
  whole query photo against the whole-picture index, `-label` embeds the SAM3
  label crop of that photo against an index of catalogue label crops, and
  `-ensemble` sums the two. The comment in `backends.yaml` states how to start
  that server and how to fill the query crop cache before a run.
- The first measurement is in `runs/2026-09-22T18*-label-exp`. Over 1,600
  positive photos the whole picture holds R@1 0.7594, the label crop 0.7431
  (p = 0.194, not established), and the two together 0.7931 (+0.0337,
  p = 0.000449). Read `svoe-vino-matcher/ResearchLog.md`.

### The review table shows the package, the label, or the label box

- The tool bar holds the control `Image` with the three values `package`,
  `label`, and `label box`. `package` is the catalogue photo, or the patch of
  that photo, as before. `label` is the label cut out of that photo with SAM3.
  `label box` is the bounding box of the label alone.
  `svoe-wino-hackaton/scripts/build_labels.py` writes the two crop directories,
  and it cuts the label out of the patch when the wine has one.
- `config.yaml` gained the two generic keys `bottle_label_dir` and
  `bottle_label_box_dir`. `scripts/common.py` reads them and holds
  `load_bottle_labels()`. An absent key gives no crop of that kind. A configured
  directory that is not on disk gives a warning at the start, and the tool runs.
- A label crop does NOT replace the catalogue photo, unlike a patch. It is a
  second view of the same photo. This is why the tool holds a selector for the
  crops and no selector for the patches.
- `GET /img/bottle` gained the parameter `kind`. A wine with no crop of the asked
  kind answers with its package picture, so a view never holds a hole. An unknown
  kind answers with the package picture as well.
- Every row carries `has_label` and `has_label_box`; the wine record also carries
  `label_path` and `label_box_path`. The page draws the mark `no label` in the
  bottom right corner of a picture that fell back, so the mark stands beside the
  mark `patched` and not over it. The pickers draw a dot in place of the word.
- The control acts on the whole review page: the table, the large view, the move
  target list, and the group picker. The runs page is unchanged.
- The control travels in the query string as `img`, beside `filter`, `sort`, and
  `slugs`. `/?img=label` opens the table on the label crops.
- The control is hidden when no wine has a crop, because the choice would then
  say nothing.
- A label crop is RGBA and its alpha channel holds the mask. The page puts such a
  picture on white, so a white label edge stays visible in the dark theme.
- The tool reads both directories again at every `GET /api/reload`.
- `docs/openapi.yaml`, `README.md`, and `SMOKE_TESTS.md` state the selector. The
  first build of the crops covers 2,070 of the 2,103 catalogue cards.

### The `Show` list of the review table holds the benchmark scope

- The control `Show` gained two entries: `excluded from the benchmark` and
  `included in the benchmark`. The reviewer looks for the excluded wines in that
  list, so the scope now stands there as well.
- The control `Slugs` (`all` / `included` / `excluded`) is unchanged. The two
  controls state the same scope, and one of them is enough.
- Both new entries ask about the card, not about its photos, so they joined
  `CATALOG_SCOPE_FILTERS`. A catalogue card with no directory in `my/` can be
  excluded too, and it reaches the list.
- The two controls can contradict each other, for example `Show` on `excluded`
  with `Slugs` on `included`. The table is then empty. The count line names the
  reason, in the same way as it does for `failed a check`.
- Checked against the running dataset `my` with its 14 excluded slugs:
  `all` gives 2107 rows, `excluded` gives 14, `included` gives 2093 and keeps
  the 246 catalogue-only cards.

## 2026-09-21

### A backend MAY pin an index, and the run records which one answered

- New backend `svm-siglip2-448-prepatch` in `backends.yaml`. It is the SAME
  pipeline and the SAME server as `svm-siglip2-448`, with
  `query: { limit: 10, index: siglip2-12041b8834 }`. That is the index of
  2026-09-18, built before the 6 patched catalogue photos existed, so the pair
  measures what the patches are worth in one benchmark, with no restart and no
  second model in memory.
- No code was needed for that: `match_backends._url` already puts every key of
  `query` into the query string.
- **Defect found and fixed in the same change.** `embeddings_of` read the
  `embeddings` block of the pipeline, which is the index the pipeline OWNS. A
  backend that pins another index therefore recorded the wrong provenance: two
  runs that read different vectors stated the same age. The first paired run
  showed it — the server log proved 40 requests used
  `index=siglip2-12041b8834.npz` while `run.json` claimed
  `siglip2-d3a1b76f7e.npz`. `embeddings_of` now reads `index` from the backend
  URL, takes the build time from `available_indexes` of that pipeline, and
  marks the block `pinned_by_backend: true`. A pinned index the server does
  not offer, and a pinned index on a pipeline that owns none, each record a
  reason instead of a wrong age.


### The virtual NULL wine: a photo that matches no card of the catalogue

- The review table holds a new first row, the NULL wine. It is a virtual wine
  with the reserved slug `__null__`. A photo that lies under it matches NO card
  of the catalogue. Until now the reviewer could state "not this wine"
  (`negative`) and could not state "no card of the catalogue".
- The row takes a photo in four ways: a drag onto the row, the key `0` in the
  large view, the entry `No match in the catalogue (NULL)` of the context menu,
  and the last entry of the move dialog. Each way records a move, and `apply`
  moves the file into `<photo_dir>/__null__/`, as for every other move.
- The row stands first, and no filter and no search take it away, so the drop
  target is always there. It is built whether the directory is present or not;
  the first `apply` makes the directory.
- The place is the statement: a photo there needs no label. The card takes
  `positive`, which confirms it, and `unusable`, which takes the photo out of
  the set. `POST /api/label` answers `400` for `negative` and for `variant`
  there, and `POST /api/copy` refuses `__null__`: both judge a photo against a
  wine, and NULL is not a wine.
- These photos are out of the labelling progress of the header. The header
  counts them apart as `no match`, with the pending moves in brackets.
- `scripts/match_run.py` reads them as rejection cases. Such a photo enters the
  query set with the label `no_match` and no truth. No answer is the only
  correct outcome, and every card at rank 1 is `false_match_at_1`.
  `metrics.json` gained the block `no_match` with `n`, `rejected`,
  `false_match_at_1`, `rejection_rate`, `errors`, and the score that a false
  match reached. `summary.md` gained the section "Photos with no match in the
  catalogue". `--only no_match` runs these photos alone.
- The page `/runs` gained the filters `no match: every photo that matches no
  card` and `no match: the backend answered a card anyway`.
- Open point: the pipeline stages read `photo_dir` and now can meet the
  directory `__null__`. They are not changed. The pipeline builds the dataset
  `default` alone, and the NULL directory is empty there until a reviewer uses
  it.
- Read `docs/plans/03_null-image.md` for the decisions and the two stages.

### A run records when its embeddings were built, and the page shows it

- `scripts/match_run.py` gained `embeddings_of()`. At run creation it asks the
  backend `GET /v1/info` and stores the answer in `run.json` under
  `embeddings`. Two runs of one backend id were until now indistinguishable
  although a rebuild of the index moved every vector between them.
- The probe resolves the pipeline that owns the vectors. It reads the name from
  `/v1/pipelines/<name>/predict` or from `?pipeline=`, falls back to
  `default_pipeline` for `/v1/eval/predict`, and then walks the `embed` and
  `base` keys until it reaches the `embed` pipeline. An `ensemble` reports one
  block per member instead of one age.
- An unknown age is always a stated reason, never a blank: no HTTP backend, the
  server did not answer, no such pipeline, or the pipeline owns no index. A
  `kind: remote` backend such as `official-api` owns no index, so an unknown
  age there is the ordinary case and not a fault.
- `scripts/review_server.py` carries the block through `run_head()` and prints
  one line in the run detail header. A run made before this change prints "not
  recorded" rather than an empty line.
- The probe needs the matcher of 2026-09-21 or later. An older server reports
  no `embeddings` block, and the run then records "pipeline `<name>` reports no
  index".

### Added
- Arrow keys in the large view of the runs page. `Left` and `Right` move through
  the images of one photo row: the matched photo first, then the candidate
  strip. The first image and the last image hold; the move does not turn around
  at an end. `Up` and `Down` move to the previous row or to the next row and keep
  the place in the row, and the table scrolls to that row. A bottle photo that
  failed to load is not a step of the move, because the page puts a text card in
  its place. `Escape` closes the view, as before.
- `patch_dir` in `config.yaml`. It names a directory of corrected catalogue photos,
  one file per wine slug: `<wine_slug>.<extension>`. The first directory is
  `svoe-wino-hackaton/dataset/patched-official-2026-09-17`, which held 7 files on
  2026-09-22. Its `README.md` names each one and states where it comes from. The
  key is generic: every dataset reads the same directory. `common.PATCH_DIR`
  holds the path and `common.load_patches()` reads the files. The extension of a
  patch does NOT have to be the extension of the photo it replaces:
  `czitronnyj-magaracha.png` replaces a `.webp`. The match is made on the slug
  alone, which is the name before the extension. A file whose extension is not an
  image type, such as that `README.md`, is not a patch.
- A patch REPLACES the catalogue photo of that slug. Some cards of «Свое вино» carry
  the photo of a different wine, so the photo it corrects MUST NOT stay in view.
  `GET /img/bottle` serves the patch, and never the photo of the catalogue record.
  The catalogue file is never rewritten.
- The mark `patched` in the top right corner of every catalogue bottle that comes
  from `patch_dir`: the review table, the pickers of `add to wine`, `move` and
  `group`, and the candidate strips of a run. The pickers show a 34 px thumbnail,
  where the mark is a dot of the same colour and the tooltip states the meaning. The
  colour is `--var` in both the light and the dark palette.
- The field `patched` in a row, in a wine record, in a variant sibling, and in a
  suggest target. `GET /api/patched` answers the slugs that take a patch; the runs
  page holds a slug alone and no record, so it reads that list.
- The tool reads `patch_dir` again at every `GET /api/reload`, so a new patch file
  needs no restart. The start report states how many slugs take a patch, and warns
  about a patch file whose name is not a slug of the catalogue.
- `scripts/08_variants.py` embeds the patch and not the photo of the record. A
  variant group is found by comparing the catalogue bottle photos, so a photo that
  the tool no longer shows MUST NOT decide a group.
- `svoe-vino-matcher/config.yaml` reads the same directory under the same key and
  indexes the patch in place of the catalogue photo.

### Fixed
- A new or an edited patch stayed invisible in the browser for 24 hours.
  `_file` answered every image with `Cache-Control: public, max-age=86400`, and the
  URL `/img/bottle?slug=<slug>` does not change when a patch replaces the file.
  The browser therefore answered from its own cache and never asked the server.
  The route `/img/bottle` now answers with an `ETag` and `Cache-Control: no-cache`.
  The browser asks with `If-None-Match` and gets `304` while the file is the same.
  It gets the new file in the first answer after a patch. The other image routes
  keep `max-age=86400`, because their file never changes behind a stable URL.
  A browser that cached a bottle image before this change keeps the old copy until
  the 24 hours pass. One reload with an empty cache clears it.

### Changed
- The table of the review page is built from the catalogue. The filter `all wines`
  holds one row per catalogue card now, and not only the wines that hold a directory
  in the photo set. A wine with no candidate photo is a row with no candidate photo,
  and a drop of a photo on such a row makes its directory. The header counts every
  row: `2103 wines` for `official-real-photos`, `2106` for `default`, which holds 3
  directories whose slug the catalogue does not hold. Every other filter keeps its
  list: a card with no photo holds no photo and no label, so it stays out of the work
  lists. An address that names a wine with no photo now opens the filter `all` and
  not `no candidate photos`.

### Fixed
- `load_state` of `scripts/review_server.py` answered `{"labels": {}}` with no key
  `wines` when the label file was missing or broken. `prune_state` reads that key, so
  the tool stopped with `KeyError: 'wines'`. Every new dataset met this fault at the
  first start, because a new dataset holds no label file. Both answers hold the two
  keys now.

### Changed
- `.gitignore` covers `dataset/*/photo/` and `dataset/*/trash/`, and not the paths of
  one dataset alone. The pictures of every dataset stay out of git.
- The trash stands at `dataset/my/trash` now, and not at `work/trash`. The 360 files
  that the directory held were moved with it. A dataset owns its trash, so the trash
  stands beside the photos, the labels, and the other files of that dataset.
  `.gitignore` holds the new path: the directory holds pictures and does not belong
  in git.
- `config.yaml` holds two parts now. `rootdir`, `catalog_file`, and `backends_file`
  stand at the top and are the same for every dataset. The key `dataset` holds one
  entry per photo set, and each entry holds `name`, `photo_dir`, `trash_dir`,
  `label_file`, `variant_groups_file`, `manual_groups_file`, `excluded_slugs_file`,
  and `runs_dir`. One entry MUST carry the name `default`.
- `scripts/review_server.py` and `scripts/match_run.py` take `--dataset NAME`. Without
  the option they use the dataset named `default`. An unknown name stops the script
  and names every dataset of the file. Every other script uses `default`, so a second
  dataset is reviewed and benchmarked, and it is not built by the pipeline.
  `run.json` of a run records the dataset in `options.dataset`, and the configuration
  report at start holds the line `dataset`.
- `scripts/common.py` holds `DATASETS`, `dataset_names()`, and `select_dataset(name)`.
  The call binds the paths of one dataset. A file with the paths at the top level is
  the old flat shape; it is refused, and the error names the keys that belong in a
  dataset entry now. `common.OUT` follows `photo_dir` of the chosen dataset.

### Added
- The dataset `official-real-photos`. It holds the 100 photos of the official test set,
  copied from `~/Downloads/Реальные фото`, which stays as it is. The photos carry no
  ground truth. Each one lies in the directory of the wine that the pipeline
  `svm-siglip2-448` answered at rank 1 in the run
  `2026-09-21T114905Z-svm-siglip2-448-dir-realphoto`; the 100 photos fall on 65 wines
  and the scores run from 0.653 to 0.852. A place is not a label: every photo holds a
  comment that names the run, the rank and the score, it holds no label, and the field
  `prefilled_from` records the placement. A reviewer MUST judge each photo. The
  dataset holds its own `review-labels.json` and `excluded-slugs.json`; the variant
  groups and the manual groups are written when they are needed.
- The review page holds an inbox. An image file that lies directly in `my/`, and not
  in the directory of a wine, belongs to no wine yet. `scan_inbox` lists these files,
  `GET /api/rows` carries them in the new field `inbox`, and the page shows them in
  the sideboard with a dashed frame. The reviewer drags such a card to a wine row;
  the card then states the target and the header counts one more pending move. The
  button `clear`, and a drop back on the sideboard, take the target away. `apply`
  moves every file that holds a wine into `my/<slug>/`. The file keeps its name, and
  a name that is taken in the target gets the suffix `_moved2`. The photo carries no
  label, because no reviewer has judged it against this wine, and its comment states
  that it comes from the inbox. The target lives in the browser tab, as the rest of
  the sideboard does, so a reload before `apply` forgets it and the file stays in the
  inbox.
- `POST /api/apply-moves` reads the field `inbox` of the body: a list of
  `{"file": ..., "to": ...}`. It answers `inbox_moved`, `inbox_failed`, and the
  `inbox` that is left. A pair is refused when the target is not a slug of the
  catalogue, when a name holds a path separator, when the file is not in the inbox,
  or when the same file is named twice.
- `GET /img/inbox?file=<name>` serves one file of the inbox. It refuses a name with a
  path separator, a name that is a directory, and a file that is not present.
- `scripts/match_run.py` takes `--photos-dir DIR`. The runner then matches the image
  files of that directory instead of the photo set of the project. The walk is
  recursive. A hidden file and a file that is not an image stay out. Such a directory
  holds no ground truth, so every photo carries the label `unlabelled`, the slug is
  empty, the truth is empty, and the outcome is `answered` or `no_answer`. The run
  states no correctness: every share of `metrics.json` is `null`, and the new block
  `unlabelled` holds `n`, `answered`, `no_answer`, `errors`, `top_score_median`, and
  `score_margin_median`. The latency numbers are unchanged. `summary.md` holds a
  shorter form for a person. The option MUST NOT be used with `--from-run`, `--only`,
  or `--variants`; the runner refuses the combination. The name of the run directory
  carries the mark `dir`, and `run.json` holds the directory in `options.photos_dir`.
- `scripts/review_server.py` answers `GET /img/runphoto?id=<run>&file=<path>`. It
  serves one photo of a run of `--photos-dir` from the directory that `run.json`
  names. `/img/photo` never leaves `my/`, so it cannot serve such a photo. The route
  refuses a run id with a path separator, a run that names no directory, and a path
  that leaves the directory.
- The page `/runs` shows a run with no ground truth. A note above the cards states the
  kind of the run and the counts that need no truth. A row of such a run shows the
  photo, the tag `unlabelled`, and the path of the file. No candidate carries a green
  or a red border, because no slug is expected and no slug is forbidden, and no answer
  is marked as wrong.

## 2026-09-19

### Added
- The review page has an `export CSV` button. It exports the exact current table view
  from the browser. The export keeps the active filter, slug scope, search text, sort
  order, variant-group scope, and row order. One record describes one candidate photo.
  A wine with no candidate photo gets one record with empty photo fields. The file uses
  UTF-8 with a byte-order mark. CSV quoting keeps commas, quotes, and line breaks in one
  cell. A text value that starts with a spreadsheet formula marker gets an apostrophe
  guard.
- A check of `validate`: `two wines carry the same catalogue bottle photo`
  (`catalog_photo_twin`). It compares the CATALOGUE bottle photo of every wine with the
  catalogue bottle photo of every other wine. It reads no candidate photo of `my/`, so a
  label and a candidate photo do not change its result. Two wines that carry one picture
  are a defect of the catalogue: the matcher cannot separate them by the image, and one
  of the two cards names the wrong bottle.
- The check reads the whole catalogue, including a card that has no directory in `my/`.
  On the catalogue of 2026-09-17 that is 2,093 cards with a bottle photo on disk, which
  is 2,189,278 pairs.
- The check runs in two stages, because the full compare of 2,093 pictures at full
  resolution is not possible in the time of a check. Stage one reads the grey 32 by 32
  signature of `photo_signature` for every picture and compares every pair with numpy;
  it takes about 3 seconds and it names the pairs under 3.0 of 255. Stage two reads a
  COLOUR 128 by 128 signature of the named pictures alone and measures again; it takes
  about 8 seconds. The whole run takes about 43 seconds, of which about 30 seconds is
  the first decode of the 2,093 files.
- Stage two is needed because the grey 32 by 32 signature is too coarse for this
  question. It holds no colour and no text of the label, so two DIFFERENT wines of one
  producer line measure as little as 0.09 of 255 under it, which is the same band as a
  true duplicate. The colour 128 by 128 signature separates the two: a true duplicate
  measures 0.00 and the nearest different picture measures 0.18. The measurement is in
  `ResearchLog.md`.
- A finding reports the whole cluster, not the pair. Three wines that carry one picture
  give one finding of three slugs and not three findings. The finding carries `slugs`,
  `bottle`, `same_picture`, `same_bytes`, `distance`, and `tag`.
- The finding carries one of two tags. `same pic` means the distance is under 0.05 and
  the two cards carry one picture; this is a defect. `twin` means the distance is from
  0.05 to 1.0 and the two pictures are different photographs of a bottle that looks
  nearly the same, as two wines of one producer line do; this is not a defect by itself,
  and the pair is a candidate for a variant group.
- A badge under the bottle photo of the row states the tag and the size of the cluster,
  for example `same pic ×2` or `twin ×8`. The tooltip states the measured distance and
  names the other wines of the cluster. `same pic` takes the colour of a defect and
  `twin` takes the colour of a variant. The check reports the CATALOGUE photo, so its
  finding carries `slugs` and no `photos` and it cannot use the pill of a card.
- On the catalogue of 2026-09-17 the check reports 70 findings over 162 wines: 27
  clusters with the tag `same pic` over 55 wines, and 43 clusters with the tag `twin`.
  The largest cluster holds 8 wines of one sparkling line of Fanagoria.

### Changed
- The filter `failed a check` now also shows a catalogue card that has no directory in
  `my/`. `catalog_photo_twin` reads the whole catalogue and can report such a card, and
  without this change the other half of a cluster stayed invisible. The four older
  checks read `my/` alone and never report such a card, so the change does not affect
  them.

## 2026-09-18

### Added
- A check of `validate`: `the candidate photo is the catalogue bottle photo of the wine`
  (`candidate_is_catalog_photo`). The `my/` set holds real-world photos only, and the
  catalogue bottle photo of a wine is a studio render. A candidate photo that is that
  render makes the benchmark easier than reality: the matcher reads its own catalogue
  picture back. The check compares every candidate photo with the bottle photo of the
  SAME wine. It never compares across wines. Two pictures count as duplicates when the
  bytes are equal, and also when the content is equal and the size differs. The second
  case reduces each picture to a signature: composite on white, convert to grey, crop to
  the bounding box of the bottle, resize to 32 by 32. The measure is the mean absolute
  difference of the 1,024 values, and the threshold is 10.0 of 255. The crop is what
  finds a copy that carries another white margin; without it the same picture measures as
  much as 119. A photo marked `unusable` and a photo marked for deletion stay out, and a
  wine with no catalogue bottle photo is not checked. On the set of today 304 of the
  4,112 pairs are under the threshold, and 0 of them have equal bytes; the check itself
  reports 282 photos in 241 wines, because it leaves the photos out that are already
  marked `unusable` or marked for deletion. The check composites a
  transparent picture on white, so a render that was flattened on another colour is not
  found. The measurement and the choice of the threshold are in `ResearchLog.md`.
- A finding of `candidate_is_catalog_photo` carries `same_bytes`, `difference`, and the
  pill text `catalogue render`.
- A check function now takes the catalogue as its fourth argument:
  `check_<name>(rows, labels, groups, catalog)`. The three older checks take it and do
  not use it.
- `candidate_is_catalog_photo` reads the pixels of about 6,000 files and takes about 50
  seconds, against about 3 seconds for the older checks. It decodes in 8 threads, and a
  JPEG decodes at a reduced scale through `Image.draft`. The dialog of `validate` states
  the cost in the help text of the check.
- Two checks of `validate` read the size of a photo: `the photo is too small (long
  side under 256 px)` and `the photo is smaller than the input of the matcher (long side
  256 to 447 px)`. The matcher runs SigLIP2 with an input of 448 by 448 pixels, and the
  preprocessor stretches the whole picture into that square. A photo with a long side
  under 448 is stretched up and holds no more detail than it had. A photo with a long
  side under 256 holds less than the half of the input, and the text of the label is
  then too small for the text step and for the OCR step. The band under 256 belongs to
  the first check alone, so the two never report the same photo. A photo marked
  `unusable` or marked for deletion stays out. The downloader already refuses a picture
  with a side under 200 (`MIN_SIDE` in `scripts/02_download.py`); a smaller picture in
  the set came in before that rule or by hand.
- A finding MAY now name the text of its pill in the field `tag`. The size checks state
  the size of the photo, for example `225x300`. A finding without `tag` keeps the older
  text, which states the count of the wines.
- The left column of a row of a run states the size of the photo, after the latency, for
  example `01_conf090.jpg · rank 2 · 237 ms · 225 × 300`. The number comes from the
  picture that the browser already loaded, so the page makes no further request.
- The filter `positive: the true slug is at rank 2 to 5` (`rank_2_5`) on the page `/runs`.
  It holds the band that R@5 wins and R@1 loses. A photo whose true slug never came back
  is out, as in `near`. The counts of `hit`, `rank_2_5`, and `after_5` add up to the count
  of the positive photos of the run.
- Two filters on the page `/runs`: `positive: the true slug is not in the top 5`
  (`after_5`) and `positive: the true slug is not in the top 10` (`after_10`). A photo
  whose true slug never came back is in both, because it counts as a failure at every
  depth. That is the rule of `failed_before()`, which `--from-run` and `--rerun-depth`
  already use. The filter `near` keeps its older reading and leaves such a photo out.
- The page `/runs` reads the true wine of a negative photo. A negative photo states one
  wine that the photo does NOT show, so `outcome` alone cannot say whether the answer was
  good. One photo file often stands in the set two times: `positive` for the wine that it
  shows, and `negative` for a wine that it does not show. The two rows hold the same
  `image_sha256`. The server reads that pair and gives the negative row the slug of its
  positive twin.
- The true wine now carries a **dashed green** frame in the strip of the candidates, next
  to the red frame of the forbidden wine. The left column states the true wine, its rank,
  and the rank of the forbidden wine. When the true wine never came back, a dashed green
  card stands after the last candidate, set apart by a gap.
- The new filter `negative: the wrong wine stands above the true wine`
  (`negative_above_positive`) selects the rows where the forbidden wine stands above the
  true wine. That is an error that no earlier number showed: the run counted the row as
  `other_slug_at_1`, which is not an error by itself. On the run
  `2026-09-17T220525Z-svm-text-siglip2-448-bench` the filter finds 20 rows of 384 negative
  photos; 97 more rows stand the right way round.
- The new filter `set defect: one photo is positive for two wines` (`twin_conflict`)
  selects the rows of a photo that carries `positive` for two wines, or `positive` and
  `negative` for one wine. One photo can show one wine only, so this is a defect of the
  set and not a result of the run. The filter exists so the reviewer can repair the set by
  hand. Until then the page marks every true wine of the group. The same run holds 121
  such rows, most of them a pair of catalogue cards that differ only in the bottle volume.
- The index reads one run only, so the report of a run stays a report of that run. A photo
  whose twin was not in the run gets no twin. The label `variant` is left out: it groups
  the same wine in another bottle and states no truth about the photo. A slug that comes
  back two times counts at its first rank, which is the rule of `judge()`.
- The field `twin` is added when the server reads a run. It is not written to
  `results.jsonl`, so a run made before today gets the marks as well.
- The button `validate` in the header checks the photo set for defects. It opens a
  dialog with one line per check, the reviewer chooses the checks, and the table then
  shows only the wines that fail at least one check. That view holds until the filter
  is changed. A check only reads: it writes no file and no label.
- The first check is `shared_positive`. It reads every candidate photo, compares the
  bytes, and reports a picture that carries the label `positive` under two or more
  slugs. One picture cannot show two wines, so such a pair is a defect: either one
  label is wrong, or the two catalogue cards are one wine. A pair of wines that are in
  one variant group is reported too and carries `same_group`, because the group itself
  may be wrong. A re-encoded copy of the same picture has other bytes and is not found.
  On the set of today the check reports 52 pictures across 56 wines, 14 of them
  inside one variant group.
- Every reported photo carries a red outline and a pill at the top left. The pill
  states how many wines share the picture, and its tooltip names the other wine and
  the other file. The count line states the findings, the photos read, and the seconds.
- The checks live in one registry, `CHECKS` in `scripts/review_server.py`. To add a
  check, write `check_<name>(rows, labels, groups)` and name it in the registry. A
  finding MUST hold `check` and `why`, and it SHOULD hold `photos` or `slugs`. The
  route builds the failing wines from those two fields and the dialog reads
  `GET /api/checks`, so a new check needs no change of the page.
- `GET /api/checks` answers the checks that the server offers.
  `POST /api/validate` takes `{checks: [id]}` and answers
  `{ok, ran, wines, photos, seconds, findings, slugs}`. An absent `checks` runs every
  check. An empty list, a value that is not a list of strings, and an unknown id are
  each refused with `400`.
- One run reads the 2,543 candidate photos in about 2.5 seconds, so the result is
  not cached. The lock is held only long enough to take the rows and the labels, so a
  label of the reviewer is not blocked while a check runs.
- A photo can now be copied to a second wine slug. One picture sometimes shows two
  wines: the same label stands on two bottles of a variant group, and the photo is a
  true photo of both. A move is wrong there, because a move takes the photo away from
  the first wine. The card holds a `⧉ copy` button under the `→ move` button, and
  the key `c` in the large view opens the same dialog in copy mode.
- The copy is recorded, not performed, exactly as a move is. The target is written to
  `review-labels.json` as the field `copy_to`, the card gets a dotted outline, and the
  header states `N copies pending`. The button `apply` and
  `python3 scripts/09_apply_moves.py --apply` carry the copies out.
- The copies run before the moves, because a move takes the source file away. A photo
  can hold a copy and a move at the same time. A `delete` mark drops both.
- The source photo does not change. It keeps its slug, its label, and its comment.
  The copy is a new candidate photo of the target wine. It carries no label, because a
  label judges one photo against one wine. Its comment is one line,
  `копия фотографии из <source slug>`, and its entry holds `copied_from`.
  `copy_to` is dropped when the file is written, so a second run copies nothing.
- `POST /api/copy` takes `{slug, file, to}` and answers `{ok, counts}`. It refuses an
  unknown photo, an unknown target, and the slug of the photo itself, each with `400`.
  An empty `to` clears the record.
- `POST /api/apply-moves` answers `copied` and `copy_failed` beside `moved` and
  `failed`. The counter `copied` was added to the counts of the review set. The photo
  record of `GET /api/v1/wine/<slug>` holds `copy_to` and `copied_from`.
- `free_name` takes the tag of the action, so a name that is taken in the target
  directory gets `_copy2` for a copy and keeps `_moved2` for a move.
- `docs/API.md`, `docs/openapi.yaml`, `README.md`, and `SMOKE_TESTS.md` state the two
  new features, the four new routes, the new fields, and 33 new test cases
  (139 to 171).

- `docs/openapi.yaml` states the whole HTTP contract of `scripts/review_server.py` in
  OpenAPI 3.1. It covers all 32 routes, not only the 7 routes under `/api/v1/`: the
  routes of the review page, the routes of the runs page, the two picture routes, and
  the three document routes. It holds 33 schemas. The document is written by hand.
  It is not generated from the code, so a change of a route MUST change the document
  in the same commit.
- The server serves the document. `GET /openapi.yaml` answers the file as it is
  written. `GET /openapi.json` answers the same document converted to JSON.
  `GET /docs` shows
  the document in a browser with Swagger UI, pinned to version 5.33.0 from the CDN.
  The page follows the theme of the operating system. Swagger UI ships no dark theme,
  so the dark form turns the light theme around with a CSS filter.
- `docs/API.md` now states the contract of the routes of the page. Those 11 write
  routes and 6 read routes had no written contract before: the file named 6 of them in
  a table of one line each. The new text states the body, the answer, and the errors of
  each one, the shared rules of a stored picture, and the table of the status codes.

### Fixed
- `README.md` stated that the page has fourteen filters. It has twenty-two. The number
  was already wrong before the filter `failed a check` was added.
- `docs/API.md` stated that the error status `502` means that the embedding service
  failed and that `503` means that the index is absent. The server holds no embedding
  service and no index, and it never answers `502`. The file now states the five
  status codes that the server does answer: `400`, `404`, `409`, and `500`.
- `docs/API.md` named 6 values of the parameter `filter` of `GET /api/v1/wines`. The
  route accepts 12. The 6 that were missing are `no_candidate_photos`,
  `image_unresolved`, `image_assumed`, `image_confirmed`, `image_manual`, and
  `image_shared`.
- `docs/API.md` stated that `GET /api/v1/wine/<slug>` adds `description` to the record.
  The record of `GET /api/v1/wines` already holds `description`. The detail route adds
  `photos` alone.
- `docs/API.md` did not state that the field `photos` of the answer of
  `POST /api/v1/propose` holds the short form `{file, conf}` and no label state.

### Changed
- The two size checks of `validate` read the LONG side of a photo, not the short side.
  A photo of a bottle is tall and narrow, so its short side is small even when the photo
  is correct. A run of `validate` on the set of today reads 3,832 photos: the short side
  reported 65 photos and 732 photos, the long side reports 0 photos and 44 photos. Over
  all 3,973 files on disk the two rules give 70 and 749 against 2 and 47; 52 of the 70
  were tall product shots such as 142 by 600 pixels, which are correct photos. The
  finding now carries `long_side` in place of `short_side`, and its text names the long
  side.
- The comment of the size checks stated that the preprocessor of SigLIP2 fits the whole
  picture into the square of 448 by 448 pixels. That statement was wrong. The
  preprocessor stretches the picture: `SiglipImageProcessor` calls
  `resize(image, size=(448, 448))`, and `preprocessor_config.json` of
  `google/siglip2-so400m-patch14-384` holds `size` alone and no `crop_size`. Verified in
  the installed `transformers` on gx10 on 2026-09-18.
- The `copy` button of the name in `scripts/review_server.py` now copies the brand and
  the name in one string, for example `WINEMAFIA David, 2020` instead of `David, 2020`.
  A search needs both parts.
- Every `copy` button in `scripts/review_server.py` has `user-select: none`. The word
  `copy` no longer enters a text selection, so a selection that is pasted into a search
  field holds the name or the slug alone.
- `scripts/02_download.py` writes its results to the database in slices of 400 instead
  of once at the end. A stop, a timeout, or `Ctrl-C` now keeps the work that is done.
  A wine is marked `downloaded=1` only when every task of that wine is written, so a
  wine is never half recorded as complete.
- `scripts/02_download.py` takes `--skip N`, which drops the first N pending wines. It
  allows a second run to start where a first run is still working.
- `backends.yaml` holds four more backends of the svoe-vino-matcher service on port
  8158: the pipelines `barcode-siglip2-448`, `text-siglip2-448`, `rerank-siglip2-448`,
  and `ocr-siglip2-448`. Each asks for 10 results with a 60 second timeout.

### Known defects, now written down
- `GET /api/v1/wines` does not check that `limit` and `offset` are numbers.
  `?limit=abc` raises inside the handler and the server closes the connection with no
  answer. `GET /api/run` does check and answers `400`. The defect is recorded in
  `docs/API.md`. The code is not changed.
- `GET /api/v1/wine/<slug>` answers `404` for a catalogue card that holds no directory
  in `my/`, although `GET /api/v1/wines` lists that card under a catalogue filter.

### Verified
- The document validates against the OpenAPI 3.1 schema.
- Every documented read route was checked against the running server with a JSON
  Schema validator: `/api/rows` with all 2106 rows, `/api/state`, `/api/v1/stats`,
  `/api/runs`, `/api/run`, `/api/suggest`, `/api/v1/wines` under three filters, and
  `/api/v1/wine/<slug>` for all 85 wines that hold a proposal. No mismatch is left.
- The check found one mismatch, which is corrected: `image_match.file` is null for a
  wine whose catalogue photo is unresolved. The document stated a string.
- The photo copy and the checks were driven end to end against a server that runs on
  a temporary photo set, not against the working set: 43 cases on the routes and 42
  cases in a headless browser, all passing. They cover the refusals of `POST /api/copy`
  and `POST /api/validate`, the order copy-move-delete, the `_copy2` rename, a second
  `apply` that copies nothing, a `delete` that drops a copy, the dialog in both modes,
  the key `c`, the mark on a reported card, and the view that holds until the filter
  changes. The new routes were NOT put through the JSON Schema validator; that tool is
  not installed on this machine.
- `check_shared_positive` was run once against the working set. It reads the 2,543
  candidate photos in 2.5 seconds and reports 52 pictures across 56 wines, 14 of them
  inside one variant group.
- 13 refusal paths were checked: the 7 refusals of `POST /api/v1/propose`, and the
  refusals of `/api/label`, `/api/comment`, `/api/exclude`, `/api/group`,
  `/api/labels`, and an unknown route. Each answers the documented status and the
  documented shape.
- The write paths that store a picture were NOT called, because a test instance shares
  the directory `my/` with the running tool. Their contract comes from the code.

## 2026-09-17

### Added
- The progress line of `scripts/match_run.py` now states the time of the last chunk of 25
  photos, the elapsed time of the run, and the ETA. The ETA uses the rate of the whole run.
  The line reads `  25/1387  chunk 12.3s  elapsed 0:00:12  ETA 0:11:05`.
- The table can now show a catalogue card that has no directory in `my/`. Such a card has no
  candidate photo, so it is a gap of the photo set. 1,262 of the 2,103 catalogue cards are such
  a gap. These rows stay out of the default list, and a filter that asks about the catalogue
  brings them in: `no candidate photos`, and the five `catalogue photo:` filters. The same
  rule holds in the agent API, where the filter `no_candidate_photos` is new.
  A catalogue-only row carries the mark `catalogue only`, a muted background, and the text
  `no directory my/<slug>`. It holds no label state, and the counters of the review set do not
  count it. The add, move, and open paths keep to the rows that have a directory.
- The bottle column states how the catalogue established that photo. The badge under the
  photo reads `from site`, `by name`, `by hand`, or `no photo`, and its colour follows the
  confidence of the match. The tooltip states the method, the confidence, the number of
  candidates for the CSV photo name, the source page, the time of the check, and the note.
  An old catalogue without the field `image_match` gets the badge `method unknown`.
- A card whose photo is shared with another card carries the mark `shared ×N`. The tooltip
  names the other slugs and states that those cards cannot be separated by the image.
- A wine whose catalogue photo is unresolved shows `no photo / unresolved` in place of the
  picture. The tool does not show a placeholder that looks like a photo.
- Five filters of the bottle photo: `unresolved`, `by name only (assumed)`, `confirmed by the
  site`, `set by hand`, and `shared with another card`. The same five values work in the agent
  API as `image_unresolved`, `image_assumed`, `image_confirmed`, `image_manual`, and
  `image_shared`.
  The field comes from the catalogue build of `svoe-wino-hackaton`. Read
  `svoe-wino-hackaton/docs/plans/01_photo-join-repair.md`.

### Fixed
- The sideboard covered the right end of the header. The panel stands over the page at
  the right edge, and the header is sticky over the whole width, so the header now keeps
  the same room free. No control of the header is covered now.

### Added
- The tag `variant group of N` on a row is a button. A click lists that group alone,
  and a click on the tag of the group that is shown lists every wine again. While a
  group is shown, the chip `variant group <id> of N ×` stands in the header beside the
  other controls and takes the group away. The chip sits there, and not in the count
  line, because the header is where a reviewer looks for the filter that is on. The
  count line names the group as well. The click clears
  the search, `Show` and `Slugs`, so every member of the group reaches the screen; the
  sort is kept, because the rows of one group stand together in every sort order. The
  group travels in the address as `?group=g0NN`, so the view can be reloaded and sent.
  An unknown group id is dropped, as an unknown value of a select is.

### Changed
- The line under the bottle photo that states how the catalogue established that photo
  (`by name`, `from site`, `by hand`, `no photo`) carries no border and no background
  any more. It is a statement, not a control, and a box of the same width as `Exclude`
  and `Group` right below it made it read as a third button. The colour of the text
  alone now carries the confidence, and `assumed` moved from grey to amber, because
  grey is the colour of the two buttons below.

### Added
- The `Group` button under the bottle photo joins one wine to the variant group of
  another wine. The tool writes one pair to the new file `manual-groups.json`, which
  `config.yaml` names under `manual_groups_file`. `scripts/08_variants.py` never
  writes that file, so a new run of the script keeps every pair made by hand.
  `load_variants()` now builds a group as a connected component over the generated
  groups and these pairs. A component that holds a generated group keeps that id; a
  component of manual pairs alone gets an id `m<NNN>`. With no manual pairs the
  loader gives the same 28 groups over the same 63 wines as before.
- `POST /api/group` takes `{slug, target}`. Two wines that are in no group make a new
  group. A wine that is in no group joins the group of the other wine, in either
  direction. Two wines that are each already in a group are refused with HTTP 409 and
  both group ids, because one pair cannot undo a merge of two groups. Two wines of one
  group answer HTTP 200 with `changed: false`. The answer carries the rebuilt rows and
  groups, so the table redraws at once.
- The search and the three selects of the table stand in the address:
  `?q=`, `?filter=`, `?sort=` and `?slugs=`. A control at its default value is left
  out, so a plain view keeps a plain address. The address is read once at start. An
  unknown value of a select is dropped. The fragment keeps its own job, the open
  photo, so `/?q=shardone#<slug>/<file>` states both.

- The right-click menu of a photo holds `Copy Image`, `Copy Image URL` and `Download`
  above the delete entry. `Download` saves the picture through a `download` link. The
  address is same-origin, so no tab opens. The saved name is `<slug>__<file>`, because
  most wines hold a file named `01_conf095.jpg` and the plain name would collide in the
  download folder. The menu closes at the click, because the browser states the
  download itself. `Copy Image` puts the picture itself on the clipboard. A JPEG or a WEBP
  goes through a canvas first, because the clipboard accepts `image/png` in every browser.
  `ClipboardItem` receives the promise of the picture, not the picture, so Safari keeps
  the permission of the click while the fetch runs. `Copy Image URL` puts the full address
  on the clipboard. The entry states `copied` or `failed` for 700 ms, then the menu closes.
  Both entries work in the table and in the large view, because both already report the
  photo under the pointer.
- A `copy` button stands next to the name of a wine. It puts the name on the clipboard.
  A wine without a name carries no button.
- `copySlug` is now `copyFromButton`. The function always copied the `data-copy` value of
  the button, and the name states that now.

- The sideboard hides and shows: the button `sideboard` in the header, the key `s`, and
  the `×` in the head of the panel. The button states the number of the held photos while
  the panel is hidden. The choice is kept in the browser and holds over a reload. A drag
  of a photo card shows the panel again, because the photo needs a target on the screen.
  While the panel is hidden, the page uses the whole width.

### Added
- `scripts/match_run.py --from-run <run>`: the repeat of a run. It asks the backend only
  about the photos that failed in an earlier run. `--rerun-depth K` states how many
  candidates count as an answer: 1 repeats every photo that was not correct at rank 1,
  and 10 repeats every photo whose true slug was not in the first 10. A negative photo
  is repeated when its own slug DID come back inside K. A failed request is always
  repeated.
- A repeated photo keeps the `query_id` of the earlier run, and its row in
  `results.jsonl` carries `previous` with the earlier rank, outcome, and answer. The two
  files join on `query_id`.
- `metrics.json` of a repeat run carries a `subset` block with `recovered_at_1`,
  `recovered_at_depth`, and `still_failing`, and states that its shares cover the
  repeated photos only. `run.json` states the rule in `based_on`, and `summary.md`
  states it in the first paragraph.
- The page `/runs` marks a repeat run with the tag `repeat d<K>`, puts the warning above
  the cards, and states under each photo what the earlier run answered.

### Added
- The metrics that `svoe-wino-hackaton/docs/task-10-specification.pdf` asks for:
  `match_share` with its target of 90 to 100 percent (section 7.1), `f1_at_1` and
  `f1_at_5` with their precision and recall (section 2.3), `within_sla_share` against
  the 3000 ms of section 2, `near_duplicate_confusion` for the wrong answers inside the
  variant group of the true wine, which the specification names as the main source of
  the errors, and `score_margin`, the gap between the first and the second candidate,
  for the correct answers and for the wrong answers apart.
- The page `/runs` shows these five measures in the first row of the cards, with the
  match share and the SLA in green when they reach the target and in red when they do
  not.
- The page `/runs` sorts. A click on a column of the table of the runs sorts by it; a
  second click turns the order around. The control `Sort` orders the photo rows by the
  most wrong first, by the rank of the true slug, by the score, by the latency, or by
  the path. The order of the photos is made by the server before the paging, so it
  holds over the whole run.
- `GET /api/run` takes `sort`. An unknown value is refused.
- The table of the runs holds the new columns: the match share, F1@1, F1@5, and the
  share inside the SLA.

### Added
- `scripts/match_run.py`: the match runner. It sends every annotated photo to one
  backend and writes one directory per run under `runs_dir`. The directory holds
  `run.json`, `queries.tsv`, `queries.jsonl`, `predictions.jsonl`, `results.jsonl`,
  `metrics.json`, and `summary.md`.
- `predictions.jsonl` carries the exact fields of the organizers. `queries.tsv` carries
  their manifest columns, so `participant_test.sh` runs against the same set. Both were
  checked against the harness of the organizers: 299 rows, no difference.
- `scripts/match_backends.py`: the backends. One HTTP class sends the photo as
  `multipart/form-data` and reads every answer shape seen so far. A header value
  `env:NAME` comes from the environment, so no token stands in a file.
- `backends.yaml`: the definitions of the backends. The first two are the contract of
  the jury and the official vino-svoe recognizer.
- `config.yaml` keys `backends_file` and `runs_dir`.
- `scripts/review_server.py`: the page `/runs`. It holds the table of the runs, the
  metrics of the selected run with two rank histograms, and one row per photo with the
  candidates that came back. The expected wine carries a green border; the wine that a
  negative photo MUST NOT match carries a red border. New routes: `GET /runs`,
  `GET /api/runs`, and `GET /api/run`.
- `docs/match-runner.md`: the format of `runs/`, of `backends.yaml`, and of every metric.
- `docs/plans/01_match-runner.md`: the plan of this work.

### Changed
- `scripts/review_server.py`: the colour variables of the page stand in one constant,
  `THEME_CSS`. The page of the review and the page of the runs use it.
- `scripts/review_server.py`: both pages hold the same navigation at the top right of
  the header. `Review` opens `/`, and `Runs` opens `/runs`. The link of the current
  page carries the class `on`. On the page of the runs this navigation replaces the
  link `back to the photo review` that stood in the title.

### Added
- `scripts/review_server.py`: the text search of the review page reads a query that
  is not written exactly as the text. It folds the accents, so `cotes` finds
  `Côtes du Don`. It takes the query apart into words and asks for each word on its
  own, so `don cotes` and `cotes du don tsimlyanskiy` find the same wine. A word of
  four letters or more also meets a word that stands one letter away from it, so
  `chardonay` finds `Chardonnay`. A word in Cyrillic is looked for in its Latin form
  as well, and a canonical form puts the spellings of the slugs together, so
  `cimlyanskiy`, `tsimlyanskiy`, and `czimlyanskoe` find each other.
  The words of a row are built once and kept on the row. A query of three words over
  2106 rows needs about 7 ms.

### Changed
- `scripts/review_server.py`: a photo added by drag and drop no longer draws the
  table again. The page brought the whole table up to date with `render`, so a wine
  that no longer matched the filter left the table at once. Under the filter `no
  candidate photos (catalogue gap)` the row went away as soon as its first photo
  landed. The new function `refreshRow` draws the cards, the photo count, and the
  mark of that one row where it stands. A reload of the page filters again.
- `scripts/review_server.py`: the new function `cardsHtml` builds the card strip of
  one row. `render` uses it for every row, and `refreshRow` uses it for one row.

### Fixed
- `scripts/review_server.py`: a drop of a picture on the row of a wine with no
  candidate photo was refused with `unknown wine slug`. `_known_slug` asked for a
  directory in `my/`, and a catalogue card with no candidate photo holds none. The
  test now accepts a slug of the catalogue too, and `_store_image` makes the
  directory. The wine then leaves the catalogue-only rows and enters the review set:
  `_store_image` builds its row with the new function `build_row` and puts it in
  `_rows`, and the page drops the mark `catalog_only`.
  The same refusal hit `POST /api/fetch-image`, `POST /api/wine-comment` and
  `POST /api/exclude`, which use the same test. All four take a catalogue slug now.
- `scripts/review_server.py`: the new function `build_row` builds the row of one
  directory. `build_rows` uses it for every directory, so one shape serves both.
- `scripts/review_server.py`: a click on the catalogue bottle of a wine with no
  candidate photo did nothing. `showLightbox` left the function when the wine held
  no photo, so the filter `no candidate photos (catalogue gap)` had no large view at
  all. The large view now opens with the catalogue bottle alone. The candidate
  figure stays hidden and the badge states `no candidate photo for this wine`. The
  keys `1` to `4` and `m` do nothing, and the comment field is closed, because both
  belong to a photo. A wine with neither a photo nor a bottle does not open, and
  `Down` and `Up` step over it.
- `scripts/review_server.py`: the address `#<slug>` opens a wine that holds no
  candidate photo. `openFromHash` needed a `/` in the address, and it looked for the
  wine in the review rows alone. A catalogue-only wine is not a review row and the
  filter `all` leaves it out, so the function now reads every row and chooses the
  filter `nophotos` for such a wine.

### Added
- `backends.yaml` key `workers`: how many requests a backend takes at the same time.
  `official-api` holds `workers: 4` and `organizers` holds `workers: 1`. The command
  `python3 scripts/match_run.py --backend official-api` now sends 4 requests at once
  without an option. `--workers N` still wins over the key. `--workers` has no fixed
  default any more: the key of the backend decides, and 1 is the last default.
  The runner states the count and its source, for example
  `requests at the same time: 4`, and the source of the value after it.
  `run.json` records the value that ran, under `options.workers`.
  The value 4 comes from a measurement. Read `ResearchLog.md`.
- `scripts/review_server.py`: the sideboard, a panel at the right of the review page.
  A photo card is dragged to the panel and waits there. A drag from the panel to a
  wine row records the move with `POST /api/reassign`, the route that the button
  `move` already uses. A drop on the row of the source wine, and the button
  `put back`, return the photo to its wine. The move machinery does not change:
  `apply` moves the file and drops the label, as it does for every move.
  The sideboard holds its list in the browser tab alone. A reload empties it and the
  server never learns about it. `apply` states nothing about a photo that waits in
  the sideboard with no target.
- `docs/plans/02_sideboard.md`: the plan of this work and the decisions of the owner.

### Added
- `scripts/match_run.py` states two rules of the query set on the console. The line
  `variant photos:` states the effect of `--variants`: how many variant photos stay
  out with `off`, or how many enter the set and which slug counts as a true match
  with `strict` and with `group`. The line `excluded slugs:` states how many slugs
  `excluded-slugs.json` holds and how many photos stay out because of them. The
  runner prints the second line also when the count is 0.

### Fixed
- `scripts/review_server.py`: the review page showed an empty list. The constant `PAGE`
  was one raw string. The change that made `THEME_CSS` cut `PAGE` into two parts. The
  second part lost the prefix `r`, so Python read it as a normal string. Every `\n` in a
  JavaScript string literal became a true newline. A JavaScript string literal MUST NOT
  hold a true newline, so the browser refused the whole script and drew no row. The
  second part carries the prefix `r` again. This also repairs the CSS escape `\2014` and
  the escaped quotation marks of the exclude prompt, and it removes the `SyntaxWarning`
  for `\s` at import. `PAGE_RUNS` is a normal string by design and does not change.

### Added
- `excluded-slugs.json` names the wine slugs that are out of the benchmark. Each entry
  holds the slug, a `reason`, and a timestamp. Some cards of the catalogue hold an
  error, most often a wrong bottle photo. The bottle photo is the reference of the
  benchmark, so a wrong reference shifts the metrics. The photos of an excluded slug
  MUST NOT be used for benchmarking.
- `config.yaml` key `excluded_slugs_file` names the file.
- `docs/excluded-slugs.md` states the purpose, the format, the rules, and the duty of a
  consumer of the file.
- `scripts/review_server.py`: an `Exclude` button under the bottle photo of every row.
  The button asks for the reason and writes the file at once. An excluded row is red.
  The button of an excluded row reads `Excluded` and puts the slug back after a
  confirmation.
- `scripts/review_server.py`: the control `Slugs` in the header bar. The values are
  `all`, `included`, and `excluded`.
- `scripts/review_server.py`: the route `POST /api/exclude` with the body
  `{slug, excluded, reason}`. An exclusion without a reason is refused.
- The agent API states the exclusion: `GET /api/v1/wines` leaves an excluded wine out
  unless `include_excluded=1`, `GET /api/v1/wine/<slug>` holds `excluded` and
  `exclude_reason`, and `GET /api/v1/stats` holds `excluded_wines` and
  `excluded_photos`.
- `config.yaml` now holds the configuration of the project. It defines `rootdir`, the root
  directory of the workspace, and `catalog_file`, the path to `catalog.jsonl`. A relative
  value of the configuration is resolved against `rootdir`.
- `scripts/common.py` reads `config.yaml` at import. It exports `CONFIG`, `ROOTDIR`,
  `CATALOG_FILE`, `PHOTO_DIR`, `TRASH_DIR`, `LABEL_FILE`, `VARIANT_GROUPS_FILE`,
  `EXCLUDED_SLUGS_FILE`, and the helpers `rootpath(path)`, `config_path(key, default)`,
  and `print_config()`. An absent key gives the earlier default path.
- `scripts/review_server.py` prints the configuration and the work directory at start.
  A path that does not exist gets the mark `(absent)`.

- `../SVOE-VINO-ISSUES.md` in the workspace root. It is the consolidated register of every
  known defect of the «Своё Вино» catalogue and of this test set. It joins five earlier
  sources: `docs/catalogue-defects.md`, `ResearchLog.md`, `work/hunt/results/*.json`,
  `svoe-wino-hackaton/docs/research/`, and the `catalog-quality.md` / `catalog-twins.md` /
  `letters/02-platform-catalog-defects.md` documents of the hackathon repository.

### Removed
- The configuration key `embedding_cache_file` and the file
  `derived/bottle-embeddings.json`. The matching of a picture against the photo set is
  the work of an external application now.
- `scripts/review_server.py`: the route `POST /api/v1/search-by-image`, the helpers
  `load_embeddings`, `embed_one`, and `top_k_by_vector`, the constant `GX10`, and the
  field `embedding_index` of `GET /api/v1/stats`. The route needed the embedding cache
  and cannot answer without it.
- `scripts/08_variants.py`: the embedding cache and the option `--no-cache`. The image
  step embeds the bottle photos at every run now. `--no-image` skips the step.
- `scripts/common.py`: the constant `EMB_CACHE_FILE`.

### Changed
- `scripts/review_server.py` takes every path from `config.yaml`: the catalogue, the photo
  set, the trash directory, the label file, the embedding cache, and the variant groups.
  No path is hard-coded in the script now.
- `scripts/08_variants.py` takes the same four paths from `config.yaml`. The script writes
  the variant groups and the embedding cache that the review tool reads, so both scripts
  MUST use one value for each file.
- `common.OUT` is now `common.PHOTO_DIR`. The value does not change with the default
  configuration.
- `scripts/review_server.py` now needs `PyYAML`, because it imports `scripts/common.py`.

### Found
- New D4 metadata defects, found by a field cross-check of `catalog.jsonl` on 2026-09-17.
  **Every one of the 7 «Два Петра» cards carries `grapes = Саперави` and
  `category = Красное`**, although four of them name a white variety and describe a straw
  colour. `perovskih_aligote`, `uva-vallis-risling`,
  `vinodelnya-myshako-quintessence-reserve-risling-krasnoe-suhoe-131`,
  `vinodelnya-myshako-oranzhevoe-iz-belogo-gevyurtstraminer-krasnoe-suhoe-142`,
  `vinodelnya-zhakov-rkatsiteli-eskeyp-krasnoe-suhoe-119` and
  `agrolayn-heritage-dg-skin-contact-rkatsiteli-rkatsiteli-krasnoe-suhoe-12` also carry
  `category = Красное` against a white or an orange wine. 10 rosé cards carry a colour text
  that describes a red or a straw-yellow wine; those are candidates, not confirmed defects.
- Slug-namespace collisions. 10 slug families are only a grape name or a colour word, so the
  producer is not in the slug and a `-1` / `-2` counter is the only separator. `merlo`
  (Галицкий и Галицкий) and `merlo-1` (Mantra Estate) also share one photo file.
- The slug naming convention is not uniform. 36 slugs use underscores instead of hyphens,
  all from five producers: Усадьба Перовских, Denisov Winery, Два Петра, JD winery,
  Винодельня Орлова.
- Three test-set slugs are absent from the 2026-09-15 catalogue dump:
  `chateau-tamagne-select-blanc-brut-svo-yo-vino`,
  `vinodelnya-uzunov-bunt-tsitronnyy-magaracha-beloe-suhoe-139`,
  `vinodelnya-uzunov-roze-kaberne-sovinon-rozovoe-ekstra-bryut-127`.
- Re-measured on the 2026-09-15 dump: 34 shared-photo groups over 69 cards, and 70 groups
  over 154 cards that share one producer and one name. The earlier figures, 25 / 50 and
  64 / 141, came from an older snapshot and a different normalisation.

## 2026-09-16

### Added
- Agent photo hunt, batch 1. Six agents worked wines 1-48 of the `needs_positive`
  queue and wrote **87 proposals**, **29 wine notes**, and **102 photo comments**.
  Photos went from 2025 to 2112. No label was written: every result is a proposal
  for the reviewer.
- `work/hunt/` holds the state of the hunt. `queue.json` is the frozen 570-wine
  queue. `progress.json` records which slug went to which agent in which batch.
  `slices/` holds the per-agent input. `results/` holds the per-agent output.
  A later batch reads `progress.json` and does not repeat a wine.

### Added
- Agent photo hunt, batch 2. Six agents worked wines 49-96 of the `needs_positive`
  queue under `work/hunt/POLICY.md` and wrote **155 proposals**. Every one of the 48
  wines got at least one proposal, and 46 of 48 reached the target of 3.
- `work/hunt/POLICY.md`. The project owner set it on 2026-09-16. It OVERRIDES the
  matching rules of the `wine-hunt` skill. A photo of the right wine in an older
  label design is now proposed as `variant`. A clean studio shot on a white
  background is now acceptable. A lineup shot, a label-only crop, and brand lifestyle
  photography are now forbidden.
- `docs/catalogue-defects.md`. It collects every catalogue defect and wrong photo that
  the hunt found, grouped by the decision each one needs.
- Per-agent scratchpads at `work/hunt/scratch/<agent>/`. They fix the collision of
  batch 1.

### The cigarpro.ru run
- `cigarpro.ru` added as a photo source on the owner's instruction. Its Russian wines
  section holds **2042 products**, each with about five of its own photographs.
  `work/hunt/cigarpro/harvest_index.py` walked all 69 listing pages;
  `work/hunt/cigarpro/match.py` paired the products with the wines that need a
  positive. **483 of the 548** such wines have at least one cigarpro candidate.
- Batch 1 gave 12 agents a slice of 72 wines. Every one of the 72 held **no proposal at
  all**: they are the residue that the search-engine hunts and the irecommend run could
  not fill. **51 of the 72 now hold a proposal**; 21 stay empty.
- **146 cigarpro proposals** were written: 81 `positive` and 60 `variant` still pending,
  plus 5 that the reviewer has already confirmed as `positive`. 86 of them are back
  labels.
- Every cigarpro image carries a `CIGARPRO.RU` watermark over the label, on every size.
  The owner accepts it on the condition that each proposal is marked. An audit agent
  checked all 141 pending cigarpro proposals: **141 of 141** begin with the exact
  marker `WATERMARK cigarpro.ru | `, **141 of 141** name a cigarpro product page in
  `source_url`, and **141 of 141** carry a confidence from 0.80 to 0.95. No defect.
- A session rate limit killed the whole first cigarpro run part-way. 86 proposals had
  already reached the server; no agent had written its results file. The remaining work
  was recomputed from `review-labels.json` and finished by a resumable workflow.
  `work/hunt/cigarpro/HOWTO.md` now tells an agent to write its results file after the
  first wine.

### The irecommend run
- Five agents worked the 33 wines that batches 1 and 2 left short of 3 proposals.
  irecommend held a matching product for **2 of the 33**. The 521 wall was not hiding
  anything: irecommend indexes a producer's mass-market SKU, not the reserve, limited,
  kosher or single-vineyard bottle. 13 proposals came out of the run, and 10 of those
  came from other sites. Detail and the screening rule for a later run are in
  `ResearchLog.md`.

### Result of both batches
- **242 proposals over 78 wines**: 202 `positive` and 40 `variant`. 96 of the 570
  wines of the queue were worked; 474 remain. 55 wine notes and 257 photo comments.
  The agent totals reconcile exactly with `review-labels.json`.
- Batch 2 produced 155 proposals against 87 in batch 1, from the same number of
  agents and wines. Two causes: the `variant` rule recovered photos that batch 1
  discarded, and batch 2 started with the source list, the rate limits and the traps
  that batch 1 had to find for itself.

### Added
- Right-click Delete in the review page. A right-click on a candidate photo, in the
  table or on the large image, opens a menu with one item. The item MARKS the photo;
  it does not touch the file. The existing "apply" button now carries out the pending
  deletions together with the pending moves, behind one dialog that states each
  consequence apart. A deletion MOVES the file to `work/trash/<slug>/` and drops the
  whole entry. A photo that carries both a `delete` and a `reassign_to` is deleted and
  is not moved. New route `POST /api/mark-delete`; new field `delete` on a photo
  entry; new count `deleting`.
- `derived/bottles-fixed/` in `svoe-wino-hackaton`, with a README. It holds bottle
  photos fetched by hand for the wines that the official upload dump does not carry.
  The dated snapshot under `sources/` MUST stay as received, so a fetched file does
  not go into it.

### Fixed
- `fanagoriya-fanagoriya-hey-bey-shardone-beloe-suhoe-13` had no catalogue bottle
  (`local_path: null`, `match: "none"`). The bottle photo was fetched from the
  `og:image` of its `vino-svoe.ru` page, 406x1500 webp, and stored in
  `derived/bottles-fixed/`. `derived/catalog.jsonl` now points at it with
  `match: "manual"` and a `manual_bottle` record of the source. **A rebuild of
  `catalog.jsonl` drops this repair**, because `build_catalog.py` has no override step.
- The `del` pill hid the comment badge. Both sat at `top: 4px; right: 4px`, and the
  pill has the higher `z-index`, so a photo that carried a comment showed no comment
  badge exactly when the reviewer was about to delete the comment with the photo. The
  badge now moves aside, and the pill no longer takes the pointer. Found by an
  adversarial review of the diff; 22 agents raised findings and this one alone
  survived refutation.
- `docs/API.md` said the `url` of a proposal MUST be `http` or `https`. A `data:` URL
  has always worked and is the way every agent proposes a picture from a blocked host.
  The document now states it.
- `docs/catalogue-defects.md` section D was misread by an agent as "the renders look
  the same". The wording now separates the renders, which ARE separable, from the
  candidate photos, which usually are not.

### Changed
- Top-up pass run with `06_topup.py --need 3 --redownload`. It reopened **1632**
  wines that hold fewer than 3 accepted photos and freed 6120 retryable candidates.
  The driver runs again with `--per-wine 40 --top 16`, deeper than the first pass.
- The stalled first pipeline pass was resumed. It had stopped mid stage 2 on
  2026-09-15 at 02:39. `GPU_TASKS.md` said "running" and was wrong; the entry is
  corrected.

### Found
- `aligote-avtorskoe` and `aligote-avtorskoe-vino` share one `bottle_path`. They are
  one wine in two catalogue rows.
- `alma-valley-pino-nuar-beloe-ekstra-bryut-115` holds two unlabelled photos,
  `01_conf095.jpg` and `02_conf095.jpg`, that show the still red Pinot Noir 2020.
  They are a different wine and SHOULD be labelled negative.
- The render of `alma-valley-shardone-rezerv-beloe-suhoe-14` is a 2020 bottle whose
  label reads 13,0 %, not 14.
- The label of `abrau-dyurso-abrau-estates-beloe-shardone-suhoe-12` reads
  `CHARDONNAY / SAUVIGNON BLANC`; the slug names only `shardone`.
- `alma-valley-merlo-rezerv` `-14` and `-15` cannot be told apart in a photo unless
  the bottom label line is readable. Two agents reached this result on their own.
- One proposal is known to be wrong and cannot be withdrawn by its author:
  `aratti-muskat-belyj-polusuhoe` `02_agent.jpg`. Read the photo comment.
- `porusski.me` does not send its intermediate certificate, so `POST /api/v1/propose`
  cannot fetch it. A different CA bundle does not help. The `data:` URL path is the
  general answer. `review_server.py` needs no change. Details in `ResearchLog.md`.

### Added
- `scripts/bench_vlm_models.py`. It compares vision models on the stage 4 identity
  task with the production prompt of `04_verify.py` and the manual labels of
  `review-labels.json` as the ground truth. The sample is stratified and
  deterministic. The run is resumable: a finished call is not repeated.
- `scripts/bench_vlm_score.py`. It scores the benchmark output for two decision
  rules, `same_wine` and the production rule `accept`, and reports latency and
  token cost. The `unusable` stratum is scored apart from the main measure.
- `work/vlm_bench.jsonl` and `work/vlm_bench_report.md`. The raw answers and the
  scored report of the first run: 4 models, 300 pairs, 1200 calls, 0 errors.
- A ResearchLog entry with the result: `qwen3.7-flash`, `qwen3.8-flash`, and
  `qwen3.8-max` have the same accuracy on this task, but not the same error
  profile and not the same cost.

## 2026-09-15

### Added
- An HTTP API under `/api/v1/` for an agent: `GET stats`, `GET wines` with the
  filters `all`, `unlabelled`, `needs_positive`, `has_proposal`,
  `fully_labelled`, `in_variant_group`, `GET wine/<slug>`,
  `GET wine/<slug>/photos?label=...`, `POST propose`, and
  `POST search-by-image`. Every picture is named by an absolute path, so an
  agent reads the bytes with its own file tool.
- The status `proposed`. An agent writes a proposal, not a label: the photo lands
  as `NN_agent.<ext>` and the entry holds `proposed`, `by`, `confidence`, and
  `source_url`. A proposal is not counted in `labelled`. The card has a dashed
  border and a tag with the confidence, and the filter `holds a photo proposed by
  an agent` lists them. The reviewer answers with the keys `1` to `4`.
- `docs/API.md` with every route, every field, and the rule of the proposals.
- The skill `wine-hunt` in `.claude/skills/wine-hunt/` with the working
  instructions of the agent: the queries, the checks against the variant group,
  the confidence floor of 0.8, and what the agent MUST NOT do.
- `scripts/08_variants.py`. It finds the wine slugs that hold the same wine in
  another bottle and writes `derived/variant-groups.json`. Two steps: the same
  producer and the same name in `catalog.jsonl`, then the cosine similarity of
  SigLIP2 embeddings of the catalogue bottle photos. The metadata step gives 28
  groups over 63 wines of `my/`.
- `scripts/09_apply_moves.py`. It moves the photos that the review tool marked for
  another slug. A report run is the default; `--apply` moves the files. The script
  is safe to run twice, and a name that is taken gets a `_moved2` suffix.
- `scripts/review_server.py`. A manual review tool for the `my/` photo set.
  It starts a local HTTP server on port 8154 and opens a browser.
  The page shows one table row per wine. Column 1 holds the catalogue bottle photo
  of the wine from the strapi dump. The next column holds the candidate photos of
  `my/<slug>/`. Each candidate photo has a "V" button and an "X" button.
  "V" means the photo shows this bottle. "X" means it does not.
  A second click on the same button clears the verdict.
  Every click is written to `review-verdicts.json` at once. The file is read again
  at the next start. The tool has eleven sort orders, nine filters, and a text search.
  A click on a photo opens it at full size.
  The tool uses the Python standard library only. It needs no install step.
- `SMOKE_TESTS.md` with the manual test cases of the review tool.

- Five-stage pipeline that builds a real-world photo test set for all 2,018 wines
  in the `vino-svoe.ru` dump: `scripts/01_search.py` … `scripts/05_report.py`,
  driven by `scripts/run_pipeline.py`.
- `scripts/common.py` with the SQLite state schema, the studio-host deny list,
  the user-generated-content host list, and the gx10 request helpers.
- `README.md` that describes the set, the pipeline, and the reports.

### Notes
- The review tool reads the slug-to-bottle-photo map from
  `../svoe-wino-hackaton/derived/catalog.jsonl`. That file is written by
  `../svoe-wino-hackaton/scripts/build_catalog.py`.
- The tool does not test that a bottle photo file is present at start.
  The strapi `uploads` directory holds about 15,800 files on an external volume.
  One `stat` call there costs a large fraction of a second, so 811 calls block
  the start for minutes. The browser requests each bottle photo only when the row
  scrolls into view. `/img/bottle` answers 404 when the file is absent.
- Current size of the review job: 814 wines and 1,892 candidate photos.
  4 wines have no catalogue bottle photo. 3 of them are absent from
  `catalog.jsonl`. 1 has no `upload_file`.

### Changed
- The wine column holds a text field for a note about the whole wine. It is one
  line high until it holds a text, and opens while it is used. The text is saved
  after a pause of 700 ms and when the cursor leaves the field, through
  `POST /api/wine-comment`. The table is not drawn again while the note is saved,
  so the cursor stays in the field.
- A note about a wine is stored in the new top level map `wines` of
  `review-labels.json`, keyed by the slug. It is apart from the labels, because
  it states something about the wine and not about one photo. The count
  `wine_notes` is new, and `prune_state` drops the note of a wine that `my/` no
  longer holds.
- A picture dragged from another browser tab is accepted, on a row of a wine or
  beside the table. Such a drag carries an address, not a file, so the page reads
  `text/uri-list`, the `src` of an `<img>` in `text/html`, or plain text, and the
  server fetches the address through `POST /api/fetch-image`. A `data:` address is
  decoded without a request.
- The media type of an added picture comes from the first bytes of the file, not
  from the `Content-Type` of the host. A real case: `api.vino-svoe.ru` answers a
  WebP picture with no `Content-Type`, and the first version refused it.
  The same test now also repairs a wrong type from the file manager.
- The fetch refuses an address that is not `http` or `https`, and an address whose
  host resolves to a loopback, private, link-local, reserved, or multicast
  address, so a dragged link cannot reach a service of this machine or of the
  local network. The request carries a browser user agent string.
- A file dropped beside the table opens a dialog that asks for the wine, so a photo
  can be added to a named slug without a search for its row. The dialog offers
  five wines with their bottle photo for what is typed, over the slug, the name,
  and the producer. It names only the wines that already have a directory in
  `my/`. A hint at the bottom of the window states both ways to drop.
- Fixed: the edit that added the move dialog cut too wide a slice of the page
  script and removed `applyMoves` and every drag and drop handler. The build
  between 21:05 and 21:20 had no drag and drop. The handlers are back, and the
  check after each edit now counts all 23 handlers of the page.
- A photo with a comment carries a round badge in the top right corner of its
  card. The pointer over the badge opens a panel with the whole text. The panel
  keeps the line breaks and scrolls when the text is long, so a comment that
  states a move is readable. Before this, the comment was the `title` of the
  card: the browser tooltip was slow, cut the text, and dropped the line breaks.
- The header states `N moves pending` with an `apply` button whenever a move is
  recorded and the file is not moved yet. The button asks for a confirmation,
  moves the files through `POST /api/apply-moves`, and rebuilds the table from
  the answer. Before this, a recorded move was visible only through a filter or
  through a run of the script, so it was easy to forget.
- A moved photo loses its label, because the label judged the photo against the
  old wine. The comment is kept, and one line is put in front of it:
  `до переноса в <new> был в <old> с таким комментарием:`. The entry gets
  `moved_from` and loses `reassign_to`, so a second run moves nothing.
  The entry travels to the key of the target slug and of the new file name.
- The move logic lives in `review_server.py` as `plan_moves`, `perform_moves`,
  and `move_note`. `scripts/09_apply_moves.py` imports the module and calls the
  same functions, so the button and the script act the same way.
- The move question is a dialog, not a `prompt`. The dialog offers the five wines
  that the photo most likely belongs to, each with its catalogue bottle photo,
  name, and producer. `GET /api/suggest` ranks them: a member of the variant
  group first, then the same producer, then a shared word of the name, then the
  same grape and the same category. A field below still takes any slug.
- An image file dropped on the row of a wine is added to `my/<slug>/` through
  `POST /api/upload`. The name is `<next number>_manual.<extension>`, so a photo
  added by hand is easy to tell apart and sorts after the photos that the
  pipeline found. A file is at most 20 MB and MUST be JPEG, PNG, WebP, GIF, or
  BMP. The row is outlined while a file is over it.
- The rank of a photo is read with `RANK_RE` (`^(\\d+)_`) instead of the full
  `NAME_RE`, so a `_manual` photo sorts by its number and not at the end.
- The large view holds a comment panel at the right. The panel takes a free text
  comment about one photo and one wine slug. The text is saved as it is typed,
  after a pause of 600 ms, and a move to another photo or a close of the view
  flushes the pending text first. `POST /api/comment` is the route, the field is
  `comment`, and `count_state` answers a `commented` count. A comment is at most
  4000 characters.
- A photo with a comment carries a coloured bar at the left of its card, and the
  comment is the tooltip of the card. The row states `N noted`. The filter
  `holds a comment` is new.
- The keys of the large view do not act while the cursor is in a field. `Esc`
  leaves the field, and a second `Esc` closes the view. Without this rule a `1`
  inside a comment would label the photo.
- A click in the comment panel no longer closes the large view. Only a click on
  the background closes it.
- The review tool holds a fourth label, `variant`, on the key `4`: this wine in
  another bottle, such as another vintage or another package design. The reason:
  the catalogue holds one slug per bottle, not one slug per wine, so a photo of
  the right wine in the wrong bottle fits neither `positive` nor `negative`.
- The rows of one variant group stand next to each other, whatever the sort, and
  share one background colour. Two colours are used in turn, so two groups next
  to each other stay apart. The filter `has a similar wine (variant group)` shows
  only the wines of a group.
- A `copy` button next to the slug puts the slug on the clipboard. It falls back
  to a hidden text field when the clipboard API is not available, because the
  tool runs over plain HTTP on the loopback address.
- A photo can be moved to another wine slug. The `move` button under the photo and
  the `m` key in the large view ask for the target slug, and the field completes
  from the 2,103 catalogue slugs. The tool writes `reassign_to` into the label
  file and does NOT move the file. `scripts/09_apply_moves.py` moves the files
  later, on one command. A moved card carries a dashed outline.
- A photo entry can hold a `label`, a `reassign_to`, or both. Clearing one field
  no longer drops the other. The entry is removed only when no field is left.
- `POST /api/reassign` is new. `count_state` answers a `reassigned` count.
  `GET /api/rows` answers the variant groups and the list of catalogue slugs.
- The review tool labels a photo with one of three labels instead of two verdicts:
  `positive`, `negative`, and `unusable`. The reason: a `negative` photo is a
  wanted result, not waste. The set needs negative samples, so a photo that shows
  a different wine stays in the set as a negative sample of its slug. The earlier
  `no` verdict read as a rejection, and the card was dimmed like waste.
  `unusable` is now the only label that takes a photo out of the set: no bottle,
  unreadable, or a duplicate. A `negative` card has its own blue colour and is not
  dimmed. Only an `unusable` card is dimmed.
  The keys are `1` positive, `2` negative, `3` unusable.
- The label file is `review-labels.json`. It was `review-verdicts.json`. The top
  key is `labels`, the entry field is `label`, and the value is one of the three
  label names. `version` is 2. The counts are `positive`, `negative`, `unusable`,
  and `labelled`. The old name and the old values held no data, so no migration
  was needed.
- The API routes are `POST /api/label` and `POST /api/labels`. The body field is
  `label`. `GET /api/rows` and `GET /api/state` answer with the key `labels`.
- The sort orders and the filters follow the three labels: `unlabelled first`,
  `positive count`, `negative count`, `unusable count`, `has a negative sample`,
  `has an unusable photo`, and so on.
- The large view writes its place into the address of the page as
  `#<slug>/<photo file name>`. Such an address can be sent to another person. The
  tool opens the large view at that photo when the address is opened, and clears
  the filter and the search when the wine is not in the current view. The address
  is written with `replaceState`, so the arrow keys do not fill the history.
- The large view of the review tool holds the keyboard. `Right` and `Left` go to the
  next and the previous photo of the wine on screen. `Down` and `Up` go to the next
  and the previous wine, at its first photo. `1` confirms the photo and `2` rejects
  it; the same key again clears the verdict. `Esc` closes the view.
  The keys follow the order that the table shows, so the sort and the filter also
  control the keyboard pass. The table scrolls to the wine on screen, so the place
  is held when the view closes.
- The large view states the verdict of the photo on screen in a badge at the top:
  `confirmed V`, `rejected X`, or `not reviewed`. The caption under the candidate
  photo states the place in the wine and the review progress of the wine.
- A click on the catalogue bottle in the table opens the large view at the first
  photo of that wine. The first version showed the bottle alone, and the arrow keys
  had nothing to move through.
- `setVerdict` takes a slug and a file name. It took a card element before. The
  large view has no card, so both the button of the table and the key of the large
  view now call the same function.
- The two images of the large view stay next to each other in the middle of the
  screen. The first version gave each image half of the width, so a wide monitor
  pushed the catalogue bottle and the candidate photo to opposite edges and the
  two labels were far apart. Each figure now shrinks to the width of its own
  image. The caption is held out of the width of the figure, so a long wine name
  wraps instead of moving the images apart.
- The large view of the review tool shows two images side by side: the catalogue
  bottle at the left, the candidate photo at the right. The first version showed the
  candidate photo alone, so the operator had to hold the label in memory while the
  large view covered the table. Each image has a caption. A click on a large image
  keeps the view open. A click on the background closes it, and so does `Esc`.
  A click on the catalogue bottle in the table shows that bottle alone.
- Stage 4 uses a stricter prompt. The first prompt accepted a photo that showed only the
  producer brand. A back-label close-up of a different Agora wine passed as a match.
  The new prompt requires the front label of that exact wine and rejects a back label,
  a cork, a box, a glass, or another wine of the same producer.
  It adds the field `front_label`. Acceptance now needs
  `same_wine=true`, `studio=false`, and `front_label=true`.
  On a 6-case probe the new prompt kept every true match and removed the false match.
- Stage 2 downloads through one flat task queue over many wines. The first version ran one
  wine at a time, so one slow host stalled a whole wine and throughput fell to 0.8 images/s.
  The flat queue reaches 5 to 8 images/s.
- Stage 2 rewrites `irecommend.ru` image URLs to the CDN mirror `cdn-irec.r-99.com`.
  Direct requests answered HTTP 521 for 1,585 of 1,585 tries. The mirror answered every try.
  A per-host limit of 12 requests in flight keeps the mirror stable.
- The driver takes `--stages`. Stages 2 and 3 run in one process, stage 4 in another.
  llama-swap on gx10 holds `siglip2` and `qwen3-vl-32b` at the same time, so the two
  processes do not make the host swap models.

### Measurements
- Stage 1 search: about 960 wines/h at one Yandex query per 1.3 s.
- Stage 2 download: 3,287 of 3,677 candidates fetched for 200 wines in 9.8 min.
- Stage 3 embed: 19 images/s including the border-whiteness measure.
- Stage 4 verify: 1.32 s per pair at 12 concurrent requests, about 340 wines/h.
  12 workers gave almost no gain over 6 workers, so the GPU is the limit.
- A smaller VLM input (320 px instead of 448 px) gave no speed gain and lower agreement.
- One call carrying 5 candidates cost 35 s and agreed with the pairwise verdicts
  on only 90% of cases. Pairwise verification with concurrency is both faster and more exact.
- Acceptance does not fall with the similarity rank: rank 1 accepted 59%, rank 8 accepted 42%.
  Verifying only the top 4 candidates would lose wines that reach 3 photos at ranks 5 to 8.

### Findings
- The official Svoe Vino API exposes `POST /v1/wines/search-by-photo`.
  The Swagger document is at `https://api.vino-svoe.ru/docs`
  and the specification at `https://api.vino-svoe.ru/docs/swagger-ui-init.js`.
  The endpoint needs no token. It is the baseline recognizer, not ground truth.
- DuckDuckGo image search rate-limits this host after a few dozen queries and answers 403.
  Yandex Images answers about 30 results per query and stayed available at one query per 1.3 s.
- SigLIP2 similarity alone is not a decision rule. A supermarket shelf photo of unrelated
  Spanish wines scored 0.55 against the reference bottle. The vision model rejected it at 0.95.
- SigLIP2 batching on gx10: one image per request costs 7.9 s with model load,
  a batch of 32 costs 30 ms per image.
- `qwen3-vl-32b` pairwise verification costs about 8 s per pair when it writes a reason,
  and about 0.6 s per pair with `max_tokens=120` and 4 concurrent requests.

### Incidents
- The volume `/Volumes/T7_2TB` reached 100% with 254 MB free during stage 2.
  The cause is not this project: the volume held 1.8 TB before the run and this project
  used 1.5 GB. `work/raw` and `work/thumbs` now live on `/Volumes/Storage`
  and are reached through symbolic links, so the project keeps its paths.
  The database stores absolute paths and the links keep them valid.
- Moving `work/raw` while stage 4 was running closed 333 wines with no check.
  Stage 4 read `os.path.exists()` on files that were in transit, found none, and marked
  each wine verified with zero verdicts. 314 of them had usable candidates.
  Stage 4 now separates the two cases: a wine with no candidate is closed, a wine whose
  candidate files are missing is skipped and stays open. The 314 wines were reopened.

### Result on the first 102 fully checked wines
- 55 wines (54%) have at least 1 real-world photo.
- 32 wines (31%) have at least 3.
- 215 photos accepted out of 854 checked, so the vision model rejects about 75%
  of what the search engines return. The search noise is the reason, not the filter.

### Cross-check against the official recognizer
- `scripts/07_api_check.py` sends every accepted photo to
  `POST https://api.vino-svoe.ru/v1/wines/search-by-photo` and records the rank of the
  expected slug in `candidates.api_rank`. 0 means the slug was not in the answer.
- On 200 accepted photos the official recognizer returned the expected slug
  at rank 1 for 28% and inside the top 5 for 66%.
- A visual check of 12 photos that the recognizer missed found that most are correct
  photos of the right wine that are simply hard: a steep angle, a close-up of part of the
  label, or several bottles in one scene. One of them reads "MUSCAT BLACK AGORA",
  which is the target wine.
- The acceptance rule was therefore left as it is. `api_rank` is reported per photo as a
  difficulty label: a photo the baseline already handles, or a photo that it misses.
- A minority of accepted photos show only the producer brand on a neck label or a cork.
  These stay in the set and are visible in the report for manual removal.

## 2026-09-15 — final result

### The set
- 2,018 wines searched. 128,483 candidate images found, 117,660 of them on
  user-generated-content hosts. 33,068 images downloaded.
- 25,172 pairwise vision checks made. 2,163 photos accepted. Acceptance rate 8.6%.
- 844 wines (42%) have at least 1 real-world photo. 386 wines (19%) have 3 or more.
  1,174 wines (58%) have none.
- `my/` holds 844 directories and 2,016 photos, at most 4 per wine, 308 MB.

### Why 3 photos per wine was not reached
- The limit is the corpus, not the filter. A search for a small Russian producer returns
  images of other wines of the same grape, other wines of the same producer, or shop
  stock photos. The vision model rejects them correctly.
- The deep pass proves the point. It made about 15,000 extra checks at depth 20 and added
  only 73 wines to the group with 3 photos.

### Cross-check with the official recognizer
- 1,974 accepted photos were sent to `POST /v1/wines/search-by-photo`.
- The expected slug came back at rank 1 for 888 photos (45%) and inside the top 5
  for 1,455 photos (74%).
- The 26% that the recognizer misses are mostly correct photos that are hard:
  a steep angle, a close-up of part of the label, or several bottles in one scene.

### Verification backends
- Three vision backends ran in parallel with work-stealing:
  `qwen3-vl-32b` on gx10 (6,497 calls), `qwen3.8-flash` on the qwencloud token-plan
  endpoint (9,075 calls), and `qwen3.7-flash` on dashscope-intl (2,538 calls).
- Both cloud models were checked against 24 pairs already judged by `qwen3-vl-32b`.
  Agreement was 24/24 for each, and every answer parsed as JSON.
- The `candidates.vlm_model` column records the backend for each verdict.
- The qwencloud endpoint throttles above 8 concurrent requests. At 16 workers the cost
  per call tripled. 8 workers is the setting.
- Adding the cloud backends raised the rate from 320 to about 800 wines/h.

### Remaining material
- 86,071 candidate images were found by search and never downloaded. Working through
  them would take about a day. The yield curve of the deep pass suggests it would add
  roughly 50 to 100 wines to the group with 3 photos.
