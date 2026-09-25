# 12 — The test sets in the database, and the lab benchmark

Date: 2026-09-25.
Status: approved by the owner on 2026-09-25. In progress. Q1 is superseded (see Q1). Step
4 is done: schema 016 entered on 2026-09-25 before the flat image store, and the three
sets are imported (session TESTSET [0fe970]). Step 5 (the baseline run) is open. This plan
is steps 6 and 7 of [plan 07](07_sqlite-lab-database.md), in a smaller form.

## Goal

1. The database holds each test set: its photos, the wine slug of each photo, and the
   label of each photo in that set.
2. A new runner `pipeline/benchmark.py` sends the photos of one set to one match backend
   and writes the run files of `scripts/match_run.py`.
3. The first lab run gives the result of the last JSON-era run of the same backend on the
   same photos. This proves the runner.

## Decisions of the owner (2026-09-25)

| Question | Decision |
|---|---|
| Where does a label live? | Per test set. Each set keeps its own photos and labels. The bytes of a photo are stored one time. |
| The source of the labels | `dataset/<set>/review-labels.json` stays the source, in git. The lab imports it read-only, and imports it again after a change. The labels move into the database only when the Testset page moves to the lab. |
| The first backend | One baseline, `svm-siglip2-448`, checked against an old run. |
| The run results | Run files `runs/<run id>/`, in the format of `scripts/match_run.py`. |
| The source directory (2026-09-25T12:15:00+0300) | `svoe-vino-testset/dataset/<set>/` for the sets `my`, `official-real-photos`, and `vlmrerank-8b-failed`. `pipeline/import_testsets.py` imports all three. |
| The order of the schema file (2026-09-25T12:22:00+0300) | The file enters now, before the flat image store. It adds the folder `testset` to `image`. |

## The baseline run

The matcher on `127.0.0.1:8158` answers `siglip2-448` from the index
`siglip2-9fbef0a4a2.npz` (built 2026-09-23T14:55:00+03:00). The run
`runs/2026-09-24T131126Z-svm-siglip2-448-index-9fbef0a4a2` used the same index, the set
`default` (`dataset/my/`), and 2,183 queries: 1,600 positive and 583 negative. The label
files of `svoe-vino-lab/dataset/` and `svoe-vino-testset/dataset/` are byte-identical on
2026-09-25. So this run is the baseline.

## The tables

The schema file is `pipeline/schema/016_testset.sql`. The number was fixed at the entry
on 2026-09-25 (rules 25 to 28 of `AGENTS.md`). The file builds `image` again with the
folder `testset` in its CHECK, and it adds the four tables below.

| Table | Key | Content |
|---|---|---|
| `test_set` | `set_name` | One row per set: `my`, `official-real-photos`, `vlmrerank-8b-failed`. `source_dir` is the directory of the import. |
| `test_photo` | `set_name`, `place`, `file_name` | One photo file in one set. `place` is the name of its directory: a wine slug, or `__null__`. `sha256` names the stored file. `label` is `positive`, `negative`, `unusable`, `variant`, or NULL (no label yet). `marked_delete` is 0 or 1. |
| `test_excluded` | `set_name`, `wine_slug` | An excluded slug of one set, with `reason` and `ts`. |
| `test_variant` | `set_name`, `wine_slug` | The variant group of a slug in one set: `group_no`, the position of the group in `variant-groups.json`. |

Normal form: each column of `test_photo` depends on the whole key. `sha256` depends on
the file, and one file can be in several places and sets, so `sha256` is a column, not a
key. The pixel size and the extension of the file stay in the table of the file (see the
open question).

`place` has no foreign key to `wine_catalog`, because `__null__` is not a wine. The
import reports each place that `wine_catalog` does not hold.

A test photo is a row of `image` with the folder `testset`, and a file
`data/images/testset/<sha256>.<extension>`. A photo whose bytes `image` holds already
keeps the row and the folder of that file. The owner chose on 2026-09-25T12:22:00+0300
that the file enters before the flat image store of drink-atlas-workspace-9a [f028b4].
So the flat store MUST also move the files of `data/images/testset/`, and its
`DROP COLUMN folder` drops the value `testset` too.

The variant groups are in the set, because the metric `near_duplicate_confusion` reads
them also with `--variants off`. With the groups of `my`, the moved `metrics_of` gives
the `metrics.json` of the baseline run exactly: all blocks equal on 2026-09-25. Without
them, `near_duplicate_confusion` is 0 and not 35.

## The import: `pipeline/import_testset.py`

```bash
python3 pipeline/import_testsets.py --db data/lab.sqlite3     # the three sets
python3 pipeline/import_testset.py --db data/lab.sqlite3 --set my \
    ../svoe-vino-testset/dataset/my                           # one set
```

`import_testsets.py` checks first that each of the three set directories holds `photo/`.
Then it calls `import_testset` for each set, each in its own transaction. The set name is
the name of the directory. `--source` names another directory of the sets.

1. The import reads `photo/<place>/<file>`, `review-labels.json`, `excluded-slugs.json`,
   and `variant-groups.json` of the directory. A file directly in `photo/` has no place;
   the import leaves it out and counts it (12 files in `my`).
2. The JSON files are the source. So each import makes the rows of the set equal to the
   files: it deletes the rows of the set and writes them again, in one transaction.
3. It stores each photo file as `data/images/testset/<sha256>.<extension>` with the rules
   of `pipeline/imagestore.py`, and writes one row of `image` with the folder `testset`
   for each new file. It reads the pixel size from the header. A file that `image` holds
   already is not stored again, and keeps its folder.
4. A label entry with no file is left out and counted. A file with no label entry gets a
   NULL label (428 files in `my`). `match_run.py` never saw such a file, so the counts
   `left_out` of `run.json` can differ from the baseline. The queries, the results, and
   the metrics do not differ.
5. The import writes nothing to `dataset/`.

## The runner: `pipeline/benchmark.py`

```bash
python3 pipeline/benchmark.py --db data/lab.sqlite3 --set my --backend svm-siglip2-448
```

1. The query set follows `build_queries` of `scripts/match_run.py` with its defaults
   (`--variants off`, `--only all`):
   - a photo with the label `positive` or `negative` enters, with its place as the slug;
   - a photo is left out when its place is excluded, when its label is `unusable`,
     `variant`, or NULL, or when it is marked for deletion;
   - a photo of `__null__` enters with the label `no_match` and no truth, unless it is
     `unusable`, marked for deletion, or `__null__` is excluded;
   - the rows are in the order of `<place>/<file_name>`, and the query ids follow it.
2. The runner reads the backends from `backends.yaml` with `scripts/match_backends.py`,
   and sends each stored photo with `ask()`.
3. The judgement and the metrics come from one shared module. `judge`, `f1`,
   `metrics_of`, `write_summary`, and their constants move unchanged from
   `scripts/match_run.py` to `scripts/match_scoring.py`. `match_run.py` imports them
   from there. So both runners score with the same code.
4. The run files: `run.json`, `queries.jsonl`, `queries.tsv`, `predictions.jsonl`,
   `results.jsonl`, `metrics.json`, `summary.md`, in `runs/<UTC time>-lab-<backend>-<set>/`.
   `run.json` names the database, the set, and the tool `pipeline/benchmark.py`.

## The parity check

The first run is `svm-siglip2-448` on `my`. It passes when these three agree with the
baseline run:

1. `queries.jsonl`: the same rows, with the same `query_id`, `image_path`,
   `image_sha256`, `slug`, `label`, and `truth`.
2. `results.jsonl`: the same `predicted_slug`, `rank_of_truth`, and `outcome` for each
   query.
3. `metrics.json`: the same values, except `run_id`, `wall_s`, and `latency_ms`.

A difference in step 1 is a bug of the import or of the query set. A difference in step 2
alone means that the matcher answers differently from the baseline day; the report then
names the queries, and the owner decides.

## Open question

**Q1. The table of a test photo file.** Schema 007 of plan 09 holds each stored file in
`image`. Its column `folder` accepts `main`, `patched`, `additional`, and `cropped`, and
not `testset`. SQLite cannot change a CHECK in place.

| Option | For | Against |
|---|---|---|
| A: `NNN_testset.sql` builds `image` again with the folder `testset` | One table for each stored file, as 007 intends. | The rebuild keeps the rows of `wine_image` and `image_derivative`, which point to `image`; it runs with `PRAGMA defer_foreign_keys`. The table belongs to plan 09, so drink-atlas-workspace-8b agrees first. |
| B: a new table `test_file` (`sha256`, `extension`, `width`, `height`) | No change of `image`. | Two tables for stored files. A file that is both a catalogue image and a test photo gets a row in each. |

The owner chose A on 2026-09-25, and drink-atlas-workspace-8b agreed. Later on the same day
two facts superseded Q1:

1. The flat image store of drink-atlas-workspace-9a [f028b4] (the owner's option 1) drops
   the column `image.folder` with `ALTER TABLE image DROP COLUMN folder`. Then a test photo
   needs no folder, and `image` needs no rebuild for this plan.
2. A rebuild of `image` inside `pipeline/labdb.py` fails. On a copy of the database with
   2,046 `wine_image` rows and 2,018 `image_derivative` rows, the sequence CREATE, INSERT,
   DROP TABLE image, RENAME, with `PRAGMA defer_foreign_keys = ON`, ends in
   `FOREIGN KEY constraint failed` at COMMIT. The DROP counts a deferred violation for each
   child row, and the RENAME does not clear the count. `labdb.migrate` runs each file in one
   transaction with foreign keys on, and `PRAGMA foreign_keys` cannot change inside a
   transaction.

The owner chose on 2026-09-25 to wait for the flat store.

Later on the same day a third fact superseded the wait. `labdb.migrate` of
drink-atlas-workspace-fa now runs each schema file with the foreign keys off, and it runs
`PRAGMA foreign_key_check` before the COMMIT. So a rebuild of `image` works. The owner
chose at 12:22:00 to enter the schema now (option A in a new form). On a backup of the
live database at version 15, the rebuild kept the 4,054 rows of `image` and their rowids,
the 2,051 rows of `wine_image`, and the 2,023 rows of `image_derivative`. The foreign key
check found no problem.

## Steps

1. The owner approves this plan and answers Q1. Done on 2026-09-25.
2. Move the scoring code to `scripts/match_scoring.py`. The move changes no line of the
   logic. Done on 2026-09-25: the 11 moved items are byte-identical to commit `a8e113a`.
3. Write `NNN_testset.sql`, `pipeline/import_testset.py`, `pipeline/benchmark.py`, and
   their tests. Until the schema file enters `pipeline/schema/`, the tests use a schema
   directory of their own. Done on 2026-09-25:
   - `pipeline/schema_pending/NNN_testset.sql` holds the four tables.
   - `embeddings_of` and `EMBED_REF_KEYS` moved unchanged from `scripts/match_run.py` to
     `scripts/match_backends.py`, so the runner records the index of the backend.
   - `tests/testset_fixture.py` builds the schema: the files of `pipeline/schema/`, then
     `ALTER TABLE image DROP COLUMN folder` while the flat store is not there yet, then the
     pending file. It adds `imagestore.path_of` of the planned interface when it is absent.
   - `tests/test_import_testset.py` (10 cases) and `tests/test_benchmark.py` (7 cases)
     pass. The live matcher reports the index `siglip2-9fbef0a4a2.npz` through the moved
     `embeddings_of`, the index of the baseline run.
4. The schema file enters `pipeline/schema/` with the next free number (rules 25 to 28 of
   `AGENTS.md`); migrate `data/lab.sqlite3`; import the three sets. Done on 2026-09-25 by
   TESTSET [0fe970], before the flat store (owner choice 12:22:00):
   - `016_testset.sql` entered at 12:34. `data/lab.sqlite3` went from version 15 to 16.
     The lab server needed no restart: it checks the version on each request.
   - `pipeline/import_testsets.py` imported the three sets of `svoe-vino-testset/dataset/`:

     | Set | Photos | positive | negative | unusable | variant | no label | Excluded | Variant slugs |
     |---|---|---|---|---|---|---|---|---|
     | `my` | 4,043 | 1,644 | 584 | 251 | 77 | 1,487 | 6 | 63 |
     | `official-real-photos` | 100 | 60 | 21 | 15 | 4 | 0 | 4 | 0 |
     | `vlmrerank-8b-failed` | 180 | 180 | 0 | 0 | 0 | 0 | 5 | 63 |

   - `my` left out 12 files directly in `photo/`. One place is not in `wine_catalog`:
     `vinodelnya-uzunov-bunt-tsitronnyy-magaracha-beloe-suhoe-139`.
   - The 4,323 rows hold 3,453 distinct files. 3,449 files are new in
     `data/images/testset/` (760 MB). 4 files are catalogue images of the lab already:
     2 in `additional` and 2 in `patched`. `image` went from 4,054 to 7,503 rows.
   - `pipeline/benchmark.py` reads the folder of each photo from `image`.
5. Run the baseline and do the parity check. The owner chose on 2026-09-25 that no
   benchmark runs before the entry, also not on a copy.

## Risks

- The review tool on port 8154 runs in `svoe-vino-testset` and writes the labels of
  `svoe-vino-testset/dataset/`. The import reads that directory since 2026-09-25T12:15:00.
  On 2026-09-25 the label files of `svoe-vino-lab/dataset/` and
  `svoe-vino-testset/dataset/` were byte-identical. They can differ later.
- The owner chose on 2026-09-25T12:22:00 that the Testset page of the lab edits the labels
  in the database. Then the database is the source, and an import from JSON deletes the
  label edits of the set. The plan of the page MUST decide the role of the import.
- The matcher can get a new index before the check. The check then compares with the run
  of the new index, or the owner accepts the step 2 differences.
