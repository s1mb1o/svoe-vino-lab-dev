# 75 — Data layout: catalogue, test data, cache

Date: 2026-09-28.
Status: stage 1 is done and committed (`86face6`). Stage 2a is done, not committed.
Stages 2b, 2c, 3, and 4 are not started.

## Goal

`data/` mixes the catalogue, the test data, the embeddings, the caches, and the backups.
The new layout puts them in separate directories. A copy of the catalogue directory MUST
be enough for the matcher, so that the matcher needs no bundle build.

The findings are in the `ResearchLog.md` entry "The content of `data/`, and a split into
catalogue, test data, and cache" of 2026-09-28.

## Owner decisions

The owner answered on 2026-09-28T16:50:22+0300 (`согласен, давай перейдем на такую
схему`) to the proposal of the agent:

1. Approach B now: move the files and keep one database. The split of the database
   (approach A) comes later as stage 4.
2. The cut files go to `catalog/cuts/`.
3. `backups/` is a fourth directory.
4. `runs/` and `dataset/` are out of scope.
5. The matcher part starts after the sessions e9, 7c, and `codex-side-matcher-bundle`.

## Target layout

```text
data/
  catalog/                  the catalogue; a copy of this directory is enough for the matcher
    catalog.sqlite3         was data/lab.sqlite3 (the test tables stay in it until stage 4)
    images/main/            was data/images/main/ (in git)
    images/patched/         was data/images/patched/ (in git)
    images/additional/      was data/images/additional/ (in git)
    cuts/                   was data/images/cropped/
    embeddings/<name>/      was data/embeddings/<name>/
  testsets/
    images/                 was data/images/testset/
  cache/
    models/<model>/         was data/cache/<model>/
  backups/                  no change
```

Until stage 3, the prepared PNG files stay in `catalog/embeddings/<name>/images/`.

## Path rules

1. `database_file` in `config.yaml` is `svoe-vino-lab/workbench/data/catalog/catalog.sqlite3`.
2. The catalogue directory is the directory of the database file.
3. The data root is the parent of the catalogue directory when the name of the catalogue
   directory is `catalog`. Otherwise, the data root is the catalogue directory. This rule
   keeps each file of a unit test database in the temporary directory of the test.
4. The table `image` keeps its folder names. `labdb.image_dir(db_path, folder)` gives the
   directory of a folder:

   | Folder | Directory |
   | --- | --- |
   | `main`, `patched`, `additional` | `<catalogue>/images/<folder>/` |
   | `cropped` | `<catalogue>/cuts/` |
   | `testset` | `<data root>/testsets/images/` |

5. The embeddings stay next to the database file: `<catalogue>/embeddings/<name>/`.
6. `model_cache.ROOT` is `<workbench>/data/cache/models/`.
7. `labdb.backups_dir(db_path)` is `<data root>/backups/`.
8. The URLs `/images/<folder>/<file>` of the lab server do not change.
9. Stage 1 does not change the database schema.

## Stages

1. **Stage 1: the move.** The code uses the path rules. The data moves. The lab server
   restarts. The documents get the new paths.
2. **Stage 2: the matcher reads `catalog/`.** Fixed SQL views in `catalog.sqlite3` give
   the wines, the cards, and the image relations. The matcher reads the views,
   `index.json`, and the vector file. A copy script refuses a copy during a build,
   copies the database with the SQLite backup API, and copies the other files with
   `rsync`. The bundle builder is then not necessary. This stage needs its own design
   section before code.
3. **Stage 3: a shared store of prepared PNG files.** `cache/prepared/` holds one file
   per distinct PNG. The SHA-256 of the PNG bytes is the file name. The status of an item
   does not depend on its PNG file. The store uses about 1.4 GB instead of 17 GB.
4. **Stage 4: the split of the database.** `testsets/testsets.sqlite3` gets the test
   tables and the register of the test photos. The owner decides whether a flatten of
   the schema comes at the same time (rule 12 of `AGENTS.md`).

## Stage 1 procedure

1. Make the code change in a scratch copy of `pipeline/`, `scripts/`, and `tests/`. Run
   the unit tests there before and after the change.
2. Record the counts of `GET /api/embeddings` and `GET /api/dataset` of the running lab
   server.
3. Make sure that no build, no run job, and no seed script runs. Set the state of the
   section in `ACTIVE_WORK.md` before the stop.
4. Stop the lab server on port 8168 with SIGTERM. The watcher `describe_images.py --watch`
   stops with it.
5. Copy `data/lab.sqlite3` with the SQLite backup API to
   `data/backups/lab-before-075-data-layout-<UTC time>.sqlite3`.
6. Copy the changed code files into the workbench.
7. Move the data. Each move is a rename on the same volume:
   - `data/lab.sqlite3` to `data/catalog/catalog.sqlite3`;
   - `data/images/main`, `patched`, and `additional` to `data/catalog/images/`;
   - `data/images/cropped` to `data/catalog/cuts`;
   - `data/images/testset` to `data/testsets/images`;
   - `data/embeddings` to `data/catalog/embeddings`;
   - each entry of `data/cache/` to `data/cache/models/`.
8. Set `database_file` in `config.yaml`. Update `.gitignore`.
9. Start the lab server (rule 23 of `AGENTS.md`).
10. Do the checks of "Stage 1 verification".
11. Update the documents, `ChangeLog.md`, and `SMOKE_TESTS.md`.

## Stage 1 verification

1. The unit tests pass. The failures are the same as before the change.
2. `GET /api/dataset` answers HTTP 200.
3. The counts of `GET /api/embeddings` are the same as before the move.
4. One file of each folder answers HTTP 200 through `/images/<folder>/<file>`.
5. One prepared PNG answers HTTP 200 through `/embeddings/<name>/images/<file>`.
6. `data/images/` and `data/embeddings/` do not exist after the move.

## Risks

1. The lab server starts scripts from disk for each job. So the new code and the moved
   data MUST go live at the same time, while the lab server is stopped.
2. git shows the moved files of `images/main`, `images/patched`, and `images/additional`
   as removed and added until a commit. The owner decides the commit.
3. Old run records hold absolute paths of data files. These paths are stale since plan
   73. The move does not add a new kind of stale path.
4. Other copies of the lab data keep the old layout: the scratch copies of other
   sessions and `/mnt/projects/svoe-vino-lab/data/embeddings/` on the NAS.

## Stage 1 result

1. The move ran at 17:38. It made the safety copy
   `data/backups/lab-before-075-data-layout-20260928T143801Z.sqlite3` and 12 renames.
   `data/images/` is gone.
2. The lab server was down from about 17:18. This change did not stop it. The session
   66 started it at 17:43 (pid 8280). `GET /api/dataset` answered HTTP 200.
3. The same check before and after the move gave the same result: 10,544 rows of `image`,
   each with its file; 2,376 sources and 4,642 cuts, each with its file; 4,645 items of each
   of the 12 embeddings, 4,642 `current` and 3 `failed`.
4. The lab server served one file of each of the five folders, one prepared PNG, the
   1,243 cut URLs of the cluster detail of `gx10-siglip2-so400m-patch16-naflex-p512`, and
   the 4,044 photo URLs of the set `my`. `GET /api/embeddings` gave the counts of item 3.
5. The unit tests of a scratch copy gave 1,331 tests with the same 5 errors before and
   after the change. The 5 errors need `docs/` or the module `svm`, which the scratch copy
   does not have. In the workbench after the move, the 1,331 tests gave 2 errors: the
   module `svm` is missing.
6. The change found one path rule in the code: `clusters._cut_url` took the folder of a
   cut from the directory name. It now uses `labdb.DERIVED_FOLDER`.
7. `deploy/test/check.sh` and `deploy/gx10/matcher-prod.md` named the test image
   `workbench/data/images/main/89b5a94a….webp`. The new path is
   `workbench/data/catalog/images/main/`. Session 7c changed `check.sh` before 17:48;
   `deploy/test/check.sh prod` exits 0. `matcher-prod.md` belongs to the session
   `codex-deployment-advice` and waits for the owner.
8. The first git commit after the move MUST record
   the removal of the old paths of `images/main`, `images/patched`, and
   `images/additional`, and the addition of the new paths.

## Stage 2 design

The owner answered `do 1 and 3` on 2026-09-28T18:57:07+0300: start stage 2.

### Goal

The matcher reads a copy of `data/catalog/`. The matcher needs no bundle build. The
matcher imports no workbench code and does not read the base tables of the lab.

### Parts

1. **2a (this step).** The SQL views, the reader of the matcher, the config keys, the copy
   script, the tests, and the documents. The bundle support stays. The default pipeline
   of `matcher/config.yaml` stays the bundle pipeline. No prod change.
2. **2b (owner approval).** The prod matcher on gx10 reads a copy of the catalogue. The
   default config, `SETUP.md`, and the deploy documents change.
3. **2c (owner approval).** The bundle builder, the bundle validator, and the bundle reader
   are removed.

### The catalogue directory for the matcher

```text
<catalog>/
  catalog.sqlite3                      the matcher reads the two views below alone
  embeddings/<name>/index.json         the items and the name of the vector file
  embeddings/<name>/vectors-<hash>.npy the vector file that index.json names
  images/, cuts/                       not necessary for the matcher
```

### SQL views (schema file `031_matcher_views.sql`)

1. `matcher_wine`: one row for each `Active` wine. The columns: `wine_slug`, `name`,
   `producer`, `category`, `region`, `color`, `grapes`, `main_source_name` (the
   `source_name` of the image type `main`, or NULL), and `qr_values` (a JSON array of the
   values of `wine_code` with the kind `qr_url`).
2. `matcher_wine_image`: one row for each image of an `Active` wine. The columns:
   `wine_slug`, `image_type`, `sha256`, and `role` (`full` or `label`). A `main` image is
   not in the view when the wine has a `main_patched` image. These are the rules of
   `embeddings.read_inputs`.
3. A later schema file that changes the base tables MUST keep the columns of the two
   views.

### Reader of the matcher (`matcher/catalog.py`)

1. `load_catalog(directory, embedding)` returns the same `Bundle` object as `load_bundle`.
   The rest of the matcher does not change.
2. The reader opens `catalog.sqlite3` read-only and checks the columns of the two views.
3. The reader reads `index.json` and the vector file that it names. It checks the name of
   the file, the type `float32`, the shape, and each row number.
4. An item `(source_sha256, view)` belongs to each wine with a row of
   `matcher_wine_image` for this `sha256`. The view `label` takes each role. The view
   `full` takes the role `full` alone. These are the rules of the bundle builder.
5. The card of a wine: `page_url` is `https://vino-svoe.ru/wines/` plus the slug;
   `image_url` is the image prefix of the bundle builder plus the URL-encoded
   `main_source_name`; `qr_urls` are the normalized, unique, sorted HTTP and HTTPS values;
   `sugar` comes from the rules of the bot. A wine gets a card only when it owns an item.
6. `Bundle.embedding` is `config` of `index.json`.
7. The reader uses each item of `index.json`. It does not check the freshness. The copy
   script checks it.

### Config of the matcher

A pipeline entry names either `bundle`, or `catalog` together with `embedding`. A
relative path resolves against the working directory of the process.

### Copy script (`scripts/copy_catalog.py`)

1. `python3 scripts/copy_catalog.py --out <new directory> [--embedding <name>]...
   [--no-images]`. Without `--embedding`, the script copies each embedding of
   `config.yaml` that has an index.
2. The script refuses an `--out` that exists, a running build of a selected embedding,
   and a selected embedding with a `stale` item. A stale item would reach the matcher with
   an old vector.
3. The script reports the `missing` and the `failed` items of each selected embedding.
4. The script copies `catalog.sqlite3` with the SQLite backup API.
5. The script copies `index.json`, the vector file, and the cluster files of each
   selected embedding. It does not copy the prepared PNG files, the logs, and the locks.
6. The script links the files of `images/` and `cuts/` (a copy on another volume), unless
   `--no-images`. The image files never change, so a hard link is safe.
7. The script writes into a temporary sibling directory, loads each embedding with the
   reader of the matcher, and then renames the directory.
8. `rsync -a --delete <out>/ <host>:<path>/` sends the copy. rsync sends the changed
   files alone.

### Stage 2a verification

1. The matcher tests read a fixture catalogue. The workbench tests check the two views
   and the copy script.
2. A new bundle and a new catalogue copy of the same data give the same slugs, the same
   cards, the same vectors of each view and wine, and the same `top1` and `ranked` answers
   for 300 query vectors.

## Stage 2a result

1. `pipeline/schema/031_matcher_views.sql` adds the two views. The session 66 took the
   number 031 at 19:14:08. No other section named schema work. The migration of
   `data/catalog/catalog.sqlite3` ran at 19:14, after the safety copy
   `data/backups/lab-before-031-matcher-views-20260928T161408Z.sqlite3`. The lab server was
   down from about 18:48, not by this session. The session 66 started it at 19:14 (pid
   10583).
2. On the live data, the views give the rows of `embeddings.read_inputs` (2,392 image
   rows) and the card fields of the bundle builder (2,099 wines, no difference).
3. `matcher/catalog.py`, the config keys `catalog` and `embedding`, and
   `matcher/tests/test_catalog.py` (11 tests) are new. The matcher suite gives 80 tests
   `OK`.
4. `pipeline/catalog_copy.py`, `scripts/copy_catalog.py`, `tests/test_catalog_copy.py`
   (6 tests), and `tests/test_matcher_views.py` (3 tests) are new. The workbench suite
   gives 1,348 tests with 2 errors: the module `svm` is missing, as before the change.
5. A new bundle and a copy of the same data gave the same slugs (2,094), cards, embedding
   config, vectors of each view and wine (2,287 `full` and 2,387 `label` rows), and the
   same `top1` and `ranked` answers for 600 query vectors in each view.
6. With the live SigLIP2 endpoint of gx10, a matcher of the bundle and a matcher of the
   copy gave the same `predict` and `match(k=4)` answers for the 3 photos of
   `matcher/tests/data`.
7. A copy of one embedding without images takes about 1.3 s (55 MB). A copy of the 12
   embeddings with 7,210 linked image files takes about 31 s on the T7.
8. `matcher/config.yaml`, the prod matcher, `SETUP.md`, and the deploy documents did not
   change. They belong to stage 2b.

