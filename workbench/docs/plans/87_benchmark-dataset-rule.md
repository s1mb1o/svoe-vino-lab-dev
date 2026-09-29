# Plan 87: Benchmark dataset rule

Date: 2026-09-29

Status: implemented and verified.

Source: owner messages of 2026-09-29T19:04:22+0300, 19:10:09+0300, 19:16:27+0300,
19:22:30+0300, and 19:42:59+0300, and the owner answers of 19:25:36+0300 and 19:38:55+0300.

## Purpose

The task states that each wine of the jury test set is in the dataset. A test photo of a
wine outside the dataset MUST NOT change F1@1, F1@5, or the other metrics of a run.

The dataset is the `Active` wines of `wine_catalog`. An `Active` manual wine (plan 20) is
in the dataset, as any other `Active` wine (owner message of 2026-09-29T19:42:59+0300).

## Rule

`pipeline/benchmark.py` leaves out each photo of a wine outside the dataset, whatever its
label. `benchmark.outside_dataset` states the rule. The reason goes to `left_out` of
`run.json`.

| Wine of the place | Reason in `left_out` |
|---|---|
| `Removed` | `removed wine` (plan 24, unchanged) |
| `Disabled` | `disabled wine` |
| A place that `wine_catalog` does not hold | `wine not in the catalogue` |
| `Active`, from the CSV or manual | none: the photo enters |

The rule does not change these cases:

- A photo of `__null__` stays a `no_match` query. `no_match` queries are not in F1.
- A photo of `__drawer__` stays out.
- A self-test of `pipeline/selftest.py` gives its own rows to `run_benchmark`. The rule
  does not apply to it.
- The photos stay in the test set. `enable` or `restore` gives them back to the next run.

Open point 2 of plan 20 stays true: the benchmark sees an `Active` manual wine as any
other `Active` wine.

## Options considered

| Option | Decision |
|---|---|
| Keep the photos of a `Disabled` wine as positives | rejected: the index holds `Active` wines alone, so each such photo is a certain miss |
| Leave out the photos of a `Removed` or `Disabled` wine, or of an unknown place | selected |
| A photo of a `Removed` or `Disabled` wine becomes a `no_match` query | rejected: a removed card can have an active successor, and a correct answer then counts as a false match |
| Also leave out the photos of an `Active` manual wine | implemented first, then rejected by the owner at 2026-09-29T19:42:59+0300 |

## Saved runs

`scripts/rescore_runs.py` applies the rule to the saved runs of `pipeline/benchmark.py`.
It reads `results.jsonl`, drops the rows of the wines outside the dataset, and writes
`metrics.json` and `summary.md` again. The old files stay as
`metrics.before-dataset-rule.json` and `summary.before-dataset-rule.md`. The new
`metrics.json` holds the key `dataset_rule` with the counts. `results.jsonl` and
`queries.jsonl` do not change. A re-scored run with no dropped row gets its old files back.

Before a write, the tool scores all rows of the run and compares the result with the old
metrics. No run differed.

After the owner message of 19:42:59, the tool re-scored 158 runs, gave the old files back
to 7 runs of `test-1`, left 112 runs unchanged, and skipped 93 runs (runs of
`scripts/match_run.py`, self-tests, and runs with no results).

## Consequences and risks

- The wine states are the states of the database at the moment of the re-score. A run of
  2026-09-27 on `my` loses 10 photos of wines that were removed later.
- F1@1 of the re-scored runs of `my` moved by -0.0008 to +0.0024. The runs of `test-1`
  and `official-real-photos` did not change.
- The photo list of `/runs` reads `results.jsonl`, so it still shows the left-out photos.
  The metrics do not count them.
- A new run of `my` has 2,231 queries instead of 2,232: the negative photo of the disabled
  wine `esse-demi-sec-muscat-nectar-muskat-belyy-beloe-ekstra-bryut-115` leaves the set.
  The query ids after that photo move by one. A tool that pairs an old run and a new run
  by `query_id` or by the bytes of `queries.jsonl` MUST pair them by `image_path`.
  `work/fixed512-rot5/compare.py` pairs by `image_path` (owner answer of 19:38:55).
- `scripts/match_run.py` does not apply the rule. It still reads `excluded-slugs.json`.
