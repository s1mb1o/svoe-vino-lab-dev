# 83 — Lab pipelines that call the matcher API

Date: 2026-09-29.
Status: implemented and verified in the lab. The matcher part waits for a prod redeploy by
the owner.

The owner sent the request on 2026-09-29T11:57:03+0300. The owner selected the answers at
12:00:47 and at 12:10:02. The messages are in [owner-messages.md](../owner-messages.md).

## Goal

1. The lab MUST have three pipelines that call the matcher API.
2. These pipelines MUST NOT use a local embedding. The matcher selects its own pipeline
   and its own bundle.
3. Pipeline 1 calls `POST /v1/eval/predict`. The answer is `{"slug": "..."}`, the
   contract of the hackathon hosts.
4. Pipeline 2 calls `POST /v1/match?k=20`. The answer holds up to 20 ranked candidates.
5. Pipeline 3 calls `POST /v1/group/match`. `/runs` shows the result of each photo as the
   original photo with numbered bottles, and a table to the right. Each table row is one
   found bottle, in the order of the matcher answer. The columns are the candidates of
   the bottle.

## Owner decisions

1. The three pipelines call the prod matcher `http://192.168.86.14:28000`
   ([deploy/gx10/matcher-prod.md](../../../../deploy/gx10/matcher-prod.md)). Prod has no
   token on the LAN.
2. `POST /v1/group/match` gets an optional query parameter `k`. Pipeline 3 asks `k=5`.
3. The metrics of pipeline 3 use this ranked list: the first candidate of each bottle,
   the highest score first, with one entry for each slug.
4. The group view replaces the candidate strip of the result row on `/runs`.

## Matcher change

1. `POST /v1/group/match` accepts the query parameter `k`. The range is 1 to 20. The
   default is 1.
2. Each bottle of the answer gets the new field `candidates`. The field holds up to `k`
   ranked candidates, the best first. Each candidate has the form of `MatchCandidate`.
3. The field `match` stays. It equals the first candidate, or null when `candidates` is
   empty.
4. With no `k`, the answer holds the same data as before, and one more field
   `candidates` with at most one entry.
5. `openapi.yaml`, `README.md`, and `docs/group-match.md` state the parameter and the
   field.
6. The portal validator `webui/shared/shelf.ts` ignores unknown bottle fields. The new
   field does not change the portal.
7. The prod matcher gets the change only after a redeploy by the owner. Before the
   redeploy, prod ignores `k` and sends no `candidates`. The lab then uses `match` as
   the only candidate of the bottle.

## Lab configuration

The three entries use the backend `svoe-vino-ru` (`pipeline/pipelines.py`), the remote
matcher backend of plan 31. They stand in `config.yaml` after
`vino-svoe-search-by-photo`.

| Name | URL | `response` | `query` | `top_k` |
|---|---|---|---|---|
| `matcher-eval-predict` | `/v1/eval/predict` | `slug-object` | none | 1 |
| `matcher-match-k20` | `/v1/match` | `candidates` | `k: 20` | 20 |
| `matcher-group-match` | `/v1/group/match` | `group` | `k: 5` | 20 |

1. Pipelines 1 and 2 use the answer shapes that exist. They need no new code.
2. Pipeline 3 uses the new answer shape `group`.
3. The run of each pipeline is a run of `pipeline/remote_run.py`, or a job of the dialog
   `Run>` of `/testset`.

## Answer shape `group`

`scripts/match_backends.py` parses the answer of `/v1/group/match`.

1. The answer MUST be an object with the list `bottles`.
2. The candidates of a bottle are its list `candidates`. A bottle with no list
   `candidates` uses `[match]`, or no candidate when `match` is null.
3. The ranked list of the run row is the first candidate of each bottle, the highest
   score first. Bottles with the same score keep the order of the answer. A slug that
   comes again is dropped. The ranks are 1, 2, and so on.
4. An answer with no bottle, or with no candidate, gives an empty ranked list and the
   error `the answer holds no bottle with a match`.
5. `HttpMultipartBackend.ask` returns a sixth value: the group record of the photo.
6. `pipeline/benchmark.py` writes the sixth value into the row of `results.jsonl` as the
   key `group`.

The group record:

```json
{
  "image": {"width": 1200, "height": 1600},
  "detected_count": 3,
  "truncated": false,
  "bottles": [
    {"n": 1, "id": "b1", "segmentation_score": 0.93,
     "box": [0.10, 0.05, 0.32, 0.95],
     "candidates": [{"rank": 1, "slug": "…", "score": 0.91}]}
  ]
}
```

1. `n` is the number of the bottle on the photo. It starts at 1 and follows the order of
   the answer.
2. `box` is `[left, top, right, bottom]` in the range 0 to 1.
3. The record keeps no mask, no preview, and no wine card. The run files stay small. The
   page takes the catalogue image of a slug from the lab database.

## Page `/runs`

1. `run_routes._row_slugs` adds the candidate slugs of the group record. The page then
   gets their catalogue images in `bottles`.
2. A row with the key `group` shows the group view in place of the candidate strip.
3. The group view shows the photo of the row with one frame and one number for each
   bottle. The box coordinates are fractions of the photo. The matcher applies the EXIF
   orientation before it computes the boxes. The browser applies the same orientation
   when it shows the photo.
4. The frame of a bottle whose first candidate is an expected wine has the colour of
   the expected wine.
5. To the right of the photo, a table has one row for each bottle. The first column
   holds the number and the SAM3 score. The next columns hold the candidates: the
   catalogue image, the score, and the slug. An expected wine has the frame of the
   expected wine.
6. A photo with no bottle shows the error text of the row.

## Tests

1. `../matcher/tests/test_group.py`: `k` gives up to `k` candidates for each bottle; the
   first candidate equals `match`; no `k` gives at most one candidate; `k=0` and `k=21`
   give HTTP 422.
2. `tests/test_matcher_api_pipelines.py`: the shape `group` with and without
   `candidates`; the score order and the slug deduplication; the empty answer; the
   sixth value of `ask`; the row key `group` of `run_benchmark`; the slugs of
   `_row_slugs`; the three entries of `config.yaml` load with no error.

## Risks

1. Each photo of a run lands in the request archive of prod and in the Inspector
   journals.
2. Prod serves the Telegram bot and the portal. The entries use 2 workers for
   pipelines 1 and 2, and 1 worker for pipeline 3, so a run does not fill the prod
   queue (8 in flight, 16 queued).
3. `/v1/eval/predict` answers `{"slug": ""}` when no wine matches. The present parser
   records this answer as the error `the answer holds no slug` and an empty list.

## Verification

1. `tests/test_matcher_api_pipelines.py`: 10 tests pass.
2. `../matcher/tests`: 125 tests pass, with the new test of `k` in `test_group.py`.
3. A probe of 3 photos of the set `my` for each pipeline on prod gave R@1 1.0. Runs
   `runs/2026-09-29T092035Z-lab-matcher-group-match-my-smoke83`,
   `runs/2026-09-29T092037Z-lab-matcher-match-k20-my-smoke83`, and
   `runs/2026-09-29T092037Z-lab-matcher-eval-predict-my-smoke83`.
4. Prod ignores `k` before the redeploy. Each bottle of the group probe has one candidate.
5. Headless Chromium on 8168, light and dark theme: the rows of the group run show 6, 1,
   and 2 bottles. The frames stand at the box fractions of the photo. A click on a card or
   on the photo opens the large view. The page has no error. A run of `matcher-match-k20`
   keeps the candidate strip (20 cards in each row).
