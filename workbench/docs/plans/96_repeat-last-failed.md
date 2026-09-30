# Plan 96: the option `Repeat last failed` of the dialog `Run>`

Date: 2026-09-30

Source: the owner message of 2026-09-30T22:45:00+0300 and the answers of about 22:52
(`docs/owner-messages.md`).

## Request

```text
add option "[ ] Repeat last failed" when start new run

this means - search for last run that was done with this dataset and pipeline. And repeat only for new candidate images and failed in last run
```

The owner selected these answers:

- A failed photo is a photo that is wrong at rank 1, or a request that failed.
- The new run is a merged full run: it covers the whole set.
- A new photo is a query that the last run does not hold as it is now.

## The last run

1. The last run is the newest run directory of `runs/` whose `run.json` names the same
   pipeline (`configuration`) and the same set (`options.set`), and holds the same value
   of `use_barcode`. The directory MUST hold `run.json` and `results.jsonl`.
2. A stopped run and a run with `--limit` MAY be the last run. Each query that such a run
   did not answer counts as new (rule 6).
3. An earlier repeat run MAY be the last run. So each repeat starts from the result of
   the repeat before it.
4. With no last run, the job makes a full run. Its log states this.

## The queries of the new run

5. The new run builds the queries of the set as a full run does (`build_queries`), with
   the same `--limit`.
6. A query is new when the last run has no row with its `image_path`, or when that row
   has another `image_sha256`, `label`, `slug`, or `truth`.
7. A query failed in the last run when its row has an `error`, or when:
   - its label is `positive` and its outcome is not `hit` (a `miss` or `no_answer`);
   - its outcome is `false_match_at_1` or `false_match_in_top_k` (a negative photo or a
     photo of `No Match` that got its wine at rank 1).
8. The job asks the backend again for each new query and each failed query.
9. Each other query is copied from the last run: its row of `results.jsonl` and of
   `predictions.jsonl` gets the new `query_id`, and it keeps its candidates, its
   judgement, its latency, and its trace. The row gets `copied_from`: the run that asked
   the backend for it. A row that the last run copied keeps its first `copied_from`.
10. When no query is new or failed, the job makes no run. It fails with the message
    `nothing to repeat: the last run <run id> has no failed and no new photo`.

## The files of the new run

11. The new run has the files of a full run. `queries.tsv`, `queries.jsonl`, and the
    metrics cover every query of the set.
12. `run.json` gets the key `repeat_of`: `run_id` (the last run), `copied`, `asked`,
    `failed`, and `new`. `based_on` stays null: `scripts/match_run.py` uses it for a
    subset run.
13. `wall_s` is the time of the new run alone. The latency metrics mix the copied rows
    of the older runs and the new answers.

## The dialog and the route

14. The dialog `Run>` of `/testset` gets the checkbox `Repeat last failed`, off by
    default. The page does not store it.
15. `POST /api/run-jobs` MAY hold `repeat_failed`: true or false. Another value gives
    HTTP 400. True gives `--repeat-failed` to `run_job.py`.
16. The job log states the plan: `repeat of <run id>: <copied> copied, <asked> asked
    (<failed> failed, <new> new)`. The progress counts the asked queries alone.
17. The self-test of an embedding (`--selftest`) does not take `--repeat-failed`.

## Limits

18. A copied row comes from the code and the configuration of the older run. A change of
    `config.yaml` since that run does not change a copied row.
19. `use_cache` and `workers` do not select the last run.

## Tests

20. `tests/test_benchmark.py`: the failure rule, the new rule, the choice of the last
    run, a repeat run on the fixture (the backend gets the failed and new photos alone;
    the copied rows; the metrics; `repeat_of`), a chain of two repeats, and "nothing to
    repeat".
21. `tests/test_run_jobs.py`: `repeat_failed` true gives `--repeat-failed`; a bad value
    gives HTTP 400.
22. A browser check of the dialog: the checkbox and the body of the POST.
