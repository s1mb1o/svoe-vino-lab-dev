# Plan 01 — Match runner for the annotated photo set

Date: 2026-09-17. Carried out on the same day. The result is
`scripts/match_run.py`, `scripts/match_backends.py`, `backends.yaml`, and the page
`/runs` of the review tool. Read `docs/match-runner.md` for the built form.

## Context

`svoe-vino-testset` holds 1,388 hand-labelled photos: 979 `positive`, 364 `negative`,
45 `variant`. Nothing measures a recognizer against them today. `scripts/07_api_check.py`
asks the official API about one photo set and writes the answer into the pipeline
database, which is not a benchmark: it keeps no history, no metrics, and no second
backend.

The matching itself moved out of this project. What stays here is the ground truth. So
this project needs a CLI that sends every annotated photo to a **match backend**, records
what came back, and writes the result into `runs/<id>/`, one directory per run, so two
runs can be compared.

Three results matter:

1. **R@1 and the distance to it.** When a backend returns a ranked list, the rank of the
   true slug states how far the answer was from correct. A miss at rank 2 and a miss at
   rank 50 are different defects.
2. **Negative matches.** A `negative` photo shows a *different* wine under that slug. The
   backend is wrong when that slug is its **Top-1** answer. The slug deeper in the
   candidate list is a diagnostic, not a failure: a negative photo is usually a visually
   similar bottle, so a ranked list MAY hold it without being wrong.
3. **A file the organizers accept.** `predictions.jsonl` in their exact format, so the
   same run serves as the jury submission.

## Decisions taken with the user

- Variant photos are **out of the query set by default**. `--variants strict|group|off`
  turns them on: `strict` accepts only the photo's own slug, `group` also accepts any
  slug of its variant group.
- Backends live in a **separate `backends.yaml`**. `config.yaml` names it.
- First two backends: the **organizers' contract** and the **official vino-svoe API**.

## Files

| File | Work |
|---|---|
| `config.yaml` | Add `backends_file` and `runs_dir`. |
| `backends.yaml` | New. The backend definitions. |
| `scripts/common.py` | Add `BACKENDS_FILE` and `RUNS_DIR` through the existing `config_path`, and add both to `CONFIG_PATHS`. |
| `scripts/match_backends.py` | New. Load `backends.yaml`, one HTTP backend class, response parsing. |
| `scripts/match_run.py` | New. The CLI: build the query set, run it, write the run directory, compute the metrics. |
| `docs/match-runner.md` | New. The run directory, the backend contract, the metric definitions. |
| `docs/plans/01_match-runner.md` | New. A copy of this plan, as the workspace rules ask. |
| `README.md`, `ChangeLog.md`, `SMOKE_TESTS.md` | The usual update. |

## The query set

Built from the files that `config.yaml` already names: `label_file`, `photo_dir`,
`excluded_slugs_file`, `variant_groups_file`.

A photo enters the set when it holds a label and its file exists. A photo is left out
when its slug is excluded, when the label is `unusable`, when the entry is an unlabelled
agent proposal, or when the entry is marked `delete`.

| Label | Count today | Truth | Correct answer |
|---|---|---|---|
| `positive` | 979 | `{slug}` | the prediction equals the slug |
| `negative` | 364 | unknown, "not this slug" | the Top-1 prediction is NOT the slug |
| `variant` | 45 | `{slug}` or the group | only with `--variants` |

A `negative` photo carries no positive truth. The reviewer stated that the photo is not
this wine; the reviewer did not state which wine it is. So only one outcome is a proven
error, and the other outcomes MUST NOT be counted as successes.

The order is `sorted(slug, file)`, so `query_id` is stable between runs of the same set.
`query_id` follows the organizers' form: `q-000001`.

`image_path` is `<slug>/<file>`, relative to `photo_dir`. This keeps the manifest usable
by the organizers' own harness:

```bash
./participant_test.sh --images-dir dataset/my/photo \
  --manifest runs/<id>/queries.tsv --endpoint <url> --output /tmp/p.jsonl
```

## `backends.yaml`

```yaml
backends:
  - id: organizers
    label: The contract of the jury harness
    url: http://127.0.0.1:8080/v1/eval/predict
    field: image            # the multipart field name
    response: auto
    timeout_s: 10
    top_k: 1                # the contract answers Top-1 only

  - id: official-api
    label: Official vino-svoe recognizer (the baseline to beat)
    url: https://api.vino-svoe.ru/v1/wines/search-by-photo
    field: image
    response: auto
    query: { limit: 10 }    # the query string that asks for a ranked list
    top_k: 10
    timeout_s: 40
    headers: {}             # a value "env:NAME" reads the environment variable NAME
```

One class, `HttpMultipartBackend`, serves both: POST `multipart/form-data` with the image
in `field`, then parse. `response: auto` accepts every shape seen so far and returns a
ranked list of `{slug, score}`:

| Shape | Source |
|---|---|
| `{"slug": "..."}` | the organizers' contract |
| `[{"slug": "..."}, …]` | the answer of the present API |
| `{"data": [...]}`, `{"items": [...]}` | `07_api_check.py` already handles both |
| `{"candidates": [{"slug": "...", "score": 0.93}]}` | a backend that states a confidence |

A score is kept when the answer holds one, and is `null` otherwise. `metrics.json` states
which backend gave scores, so a run without them is never read as a run with zero
confidence.

**No secret in the file.** A header value `env:TOKEN_NAME` is read from the environment at
start, and `run.json` records the header name with the value redacted.

## The run directory

`runs/<UTC time>-<backend id>[-<label>]/`, for example
`runs/2026-09-17T154210Z-official-api/`.

| File | Content |
|---|---|
| `run.json` | What ran: backend (redacted), options, the resolved configuration, the query-set counts, the git commit of this repository, start and end, wall time. |
| `queries.tsv` | `query_id<TAB>image_path`. The organizers' manifest of this run. |
| `queries.jsonl` | The same rows with `sha256`, `slug`, `label`, and the expectation. |
| `predictions.jsonl` | **The organizers' format, exactly**: `query_id`, `image_path`, `image_sha256`, `predicted_slug`, `latency_ms`. `predicted_slug` is `null` when no valid slug came back. |
| `results.jsonl` | The full record per photo: every candidate with its score and rank, `rank_of_truth`, `hit@1/5/10`, `false_match` for a negative, `latency_ms`, `http_status`, `error`. |
| `metrics.json` | The aggregate, see below. |
| `summary.md` | The same numbers as a short table, so the directory is readable in GitLab. |

`predictions.jsonl` and `results.jsonl` are written line by line as the run goes, so an
interrupted run keeps what it already has. `--resume <run dir>` reads the finished
`query_id` values and asks only for the rest.

## `metrics.json`

```json
{
  "run_id": "2026-09-17T154210Z-official-api",
  "backend": "official-api",
  "has_scores": true,
  "queries": { "total": 1343, "positive": 979, "negative": 364, "variant": 0 },
  "positive": {
    "n": 979, "recall_at_1": 0.61, "recall_at_5": 0.74, "recall_at_10": 0.78,
    "mrr": 0.66, "no_answer": 12, "errors": 3,
    "rank_histogram": { "1": 597, "2": 61, "3": 34, "4-10": 42, ">10": 0, "absent": 245 }
  },
  "negative": {
    "n": 364,
    "false_match_at_1": 18,
    "other_slug_at_1": 339,
    "no_answer": 6,
    "errors": 1,
    "slug_rank_histogram": { "1": 18, "2": 57, "3": 31, "4-10": 44, "absent": 214 },
    "false_match_scores": { "median": 0.71, "max": 0.88 }
  },
  "latency_ms": { "median": 842, "p95": 1930, "max": 4100, "comparable": true },
  "wall_s": 1180
}
```

`rank_histogram` is the answer to "how far from R@1". `absent` counts the queries whose
true slug never appeared in the returned list; with a Top-1 backend every miss lands
there, which is the honest reading of a contract that returns one slug.

The `negative` block names four outcomes and mixes none of them:

- `false_match_at_1` — the slug is the Top-1 answer. **This is the error count.**
- `other_slug_at_1` — the answer is a third slug. The photo may genuinely be that wine,
  so this is unverifiable, not a success.
- `no_answer` — the backend abstained. A true rejection, for a backend that can abstain.
- `slug_rank_histogram` — where the slug sat in the list. A backend that places it at
  rank 2 for most negatives ranks fragilely even when its R@1 looks good.

`false_match_scores` holds the score of the false Top-1 answers, when the backend returns
scores. Compared with the scores of the true positives, it states whether a confidence
threshold would remove these errors without costing recall.

`--negative-strict` counts any appearance of the slug in the top-k as a failure, for the
pessimistic reading. It is off by default.

`latency_ms.comparable` is `false` when the run used more than one worker.

## The run loop

Serial by default, as the jury harness is: one request, wait for the whole answer, write
the row, then the next image. `latency_ms` is then comparable to the organizers' number.
`--workers N` runs N requests at once for a fast local backend and sets
`latency_ms.comparable: false`.

Other options: `--backend <id>` (required), `--limit N` (a short trial run),
`--only positive|negative|all`, `--variants strict|group|off`, `--negative-strict`,
`--label <text>` for the directory name, `--dry-run` (build the query set and the
manifests, call nothing), `--resume <run dir>`.

An HTTP error, a timeout, or an unparsable answer is recorded on the row and the run goes
on. `predictions.jsonl` keeps `predicted_slug: null` for that photo, which is what the
organizers' harness also writes.

## Verification

1. `--dry-run` against the present data. Expect 979 positives and 364 negatives, minus the
   photos of any excluded slug, and a `queries.tsv` whose header is exactly
   `query_id<TAB>image_path`.
2. A stub backend of about 30 lines in the scratchpad that always answers one known slug.
   Run the tool against it, then check by hand: the positives of that slug count as hits,
   every other positive counts as a miss, a negative under that slug counts as a false
   match at rank 1, and every other negative counts as `other_slug_at_1` and NOT as a
   success. This proves the metric arithmetic without the network.
   A second stub that answers a ranked list with the true slug at rank 3 proves the rank
   histogram and the `--negative-strict` switch.
3. The organizers' own harness against the same stub, with our `queries.tsv` and
   `--images-dir dataset/my/photo`. Their `predictions.jsonl` and ours MUST hold the same
   `query_id`, `image_path`, `image_sha256`, and `predicted_slug` for every row. This is
   the proof that the format is accepted.
4. `--backend official-api --limit 20` for a real ranked answer, real scores, and real
   latency. This uploads 20 photos to `api.vino-svoe.ru`; a full pass uploads 1,343.
5. New `SMOKE_TESTS.md` cases for the points above.

## Open point, decided unless you say otherwise

`runs/` is committed to git. The directories are text and small, about 1–2 MB per run, and
history is the reason the directory exists. If you would rather keep the repository clean,
one line in `.gitignore` reverses it.
