# 28 — Seed and restore the lab from svoe-vino-testset

Date: 2026-09-25.
Status: the owner chose the design on 2026-09-25T17:52:00+0300. Implemented by
drink-atlas-workspace-c5 [7cabb3] as `pipeline/seed_from_testset.py`. The owner message
of 2026-09-25T17:46:51+0300 and the two answers are in
[owner-messages.md](../owner-messages.md).

## Goal

1. One command fills `data/lab.sqlite3` and `data/images/` from `svoe-vino-testset`:
   the catalogue, the three test sets, the QR URLs, the GTINs, and the annotations.
2. The same command restores this state after a test. The owner tests the lab, changes
   data, and then goes back to the annotations of `svoe-vino-testset`.
3. The command does not copy the configuration, the runs, or the clusters.

## Decisions of the owner

- Full rebuild and swap. The script builds a new database and swaps it in. The old
  database goes to a backup. The data of the lab alone are not kept in the new database.
- Each run makes the label cuts (`seed_label_cuts.py`). So each run needs SAM3 on gx10
  for each full original that the model cache does not hold.

## The sources

| Data | Source | Step |
|---|---|---|
| Tables | `pipeline/schema/` | `labdb.py` |
| Catalogue | `svoe-wino-hackaton/dataset/official-2026-09-17/strapi_output0709.csv` | `import_catalog.py` |
| Main images | the Strapi uploads folder of the same delivery | `seed_images.py` |
| Patches | `patch_dir` of `svoe-vino-testset/config.yaml` | `seed_patched.py` |
| GTINs, QR URLs | `barcode_file` (`svoe-vino-matcher/dataset/code-map.json`) | `seed_codes.py` |
| Atlas Core bindings | `atlas_matches_file`, `atlas_bindings_file` | `seed_atlas_bindings.py` |
| Test sets | `svoe-vino-testset/dataset/{my,official-real-photos,vlmrerank-8b-failed}` | `import_testsets.py` |
| Label cuts | SAM3 on gx10, through `data/cache/sam3/` | `seed_label_cuts.py` |

`catalog_file` of the testset (`catalog.jsonl`) is built from the same Strapi CSV. The
lab reads the CSV, because `import_catalog.py` reads the CSV.

The test sets bring the labels, the photo comments and the other fields of a label
entry, the wine notes, the excluded slugs, and the variant groups.

These sources give no data on 2026-09-25, so the script has no step for them:

- `alternative_dir` and `alternative_label_dir`: the folders hold a `README.md` alone.
- `embedding_ignore_file`: the list `ignored` is empty.
- `manual-groups.json`: plan 24 skips the manual groups (Q2).
- The `trash/` folders of the sets: a deleted photo is not in a set.

## Rules

1. The script builds the new database at `<db>.seeding`, next to `--db`. So the new
   database uses the same image store `images/`. A stored file is not copied again.
2. Each step is one tool of `pipeline/`, as a separate process. A step with an exit
   status other than 0 stops the script. `--db` then does not change. The partial
   database stays at `<db>.seeding`. The next run deletes it.
3. After the last step, the script copies `--db` to `backups/<name>-<UTC time>.sqlite3`
   next to it. Then it copies the new database into `--db`. Both copies use the SQLite
   backup API. The lab server opens the database for each request, so it needs no
   restart.
4. The script never writes to a source.
5. The script prints the row count of each table in the old and in the new database.

## What a restore removes

The new database holds the data of the sources alone. These data of the lab are only in
the backup after a run:

- the state `Disabled` or `Removed` that a person set, and each refusal of the website
  import;
- the comments and the favorites;
- a wine added by hand (slug prefix `__`) and a wine of the website import;
- the alternative photos (`full_front`, `label_front`, `full_back`, `label_back`);
- the edits of the Testset page;
- the image descriptions. The watcher of the lab server (`image_description.watch`)
  makes them again, mostly from `data/cache/`.

## The state on 2026-09-25

- The script and the 10 tests are done (`tests/test_seed_from_testset.py`, `OK`).
  drink-atlas-workspace-c5 [7cabb3] stopped before its test run ended. The test run
  reached step 8 (label cuts): `data/lab-test.sqlite3.seeding` holds steps 1 to 7
  (2,103 wines, 2,061 `wine_image` rows, 26 codes, 367 Atlas bindings, 4,323 test
  photos). No process of the run was left.
- A full run makes the label cut of each full original. `data/cache/sam3/` held 397
  records at 18:25, so a full run asks SAM3 on gx10 about 1,660 times (about 17 min).
  TESTSET [0fe970] did not start the full test run, because 8 embedding builds of the
  owner used gx10 at that time. The owner decides when it runs (`SMOKE_TESTS.md` SD2 to
  SD6).
- Docs: `README.md`, `COMMANDS.md`, `SMOKE_TESTS.md` (section SD), `ChangeLog.md`.

## Tests

`tests/test_seed_from_testset.py`: the step list, the order, the swap and its backup, an
open connection after the swap, a failed step, and the delete of a partial database.
