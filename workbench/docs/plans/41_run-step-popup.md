# Plan 41: the step popup of a query photo on `/runs`

Date: 2026-09-26

Source: owner message of 2026-09-26T07:14:42+0300 and the answers of 07:22:00.

## 1. Goal

A click on the query photo of a row of `/runs` opens a popup. The popup shows the way of
that photo through the pipeline of the run, as a list of steps. For each step it shows:

- the step: its number, its name, the service, and the model;
- what the step made: images, boxes, candidate lists, the VLM answer;
- how long the step took.

The popup also shows the images that the run made from the photo, the embedding space of
each search (for example the space `full` and the space `label`), the VLM answer when
the pipeline used a VLM, and the candidates before the re-rank.

The look follows the step view of `drink-atlas-recognize` on port 8162.

## 2. Owner choices

1. Step data: record a trace at run time. `embedding_run.py` writes a small trace into
   each row of `results.jsonl`. The images are made again on demand from the SAM3 cache.
   The route checks each image against the sha256 of the trace. The run writes no image
   file. Only a new run has step times. An old run shows the same steps with "time not
   recorded".
2. Scope: embedding runs and matcher runs. Embedding runs get all steps. Matcher runs get
   the input photo, the model inputs of the matcher, the base order (the order before the
   re-rank), the difference step, the VLM rule step, and the final order. Remote runs and
   mock runs get the input photo and the answer.
3. Language: English, as the other lab pages.
4. Grouping: rounds by phase, as on 8162. Each round header shows the elapsed time and
   the sum of the step times of the round.

## 3. Facts

### 3.1 The runs

1. `runs/` holds 139 runs on 2026-09-26: 51 embedding runs (`backend.kind: embedding`),
   69 matcher runs of `svoe-vino-matcher` (`backend.url` `.../v1/pipelines/<name>/predict`),
   3 remote runs, 6 runs of the official API, 2 mock runs, and older runs.
2. A row of `results.jsonl` holds the candidates, `latency_ms`, `http_status`, and
   `error`. `latency_ms` is the time of the whole photo. No run records the time of a
   step.
3. An embedding run makes these steps for each photo, one after another
   (`EmbeddingBackend.ask`): open the photo; SAM3 cuts (`derive.derive_image` for the
   target `package`, `alternatives.label_cut_of` for the target `label`); the steps of
   each view (`embeddings.apply_steps`); one embedding request for all views; the cosine
   search in the catalogue vectors of each view; the score, which is the mean of the best
   cosine of each view.
4. An embedding run keeps no derived image. `/api/run-inputs` makes the model inputs
   again from the SAM3 answers of `data/cache/sam3/` (`embedding_run.model_inputs`).
5. A candidate of an embedding run holds its best cosine of each view, and (plan 38) the
   cosine of each catalogue item of the wine. The run keeps no top list of one view. So
   a search in the space `label` alone cannot be shown for an old run.
6. `derive.Sam3Client._post` reads `model_cache` first. So a SAM3 step of a run is a
   cache hit or a real request. The run does not record which.
7. The embedding requests do not use `model_cache`. Each run sends them again.
8. A matcher run with the query `explain: 1` holds an `explain` record in each candidate
   that the cluster rule step touched (`kind: cluster_rules`): the cluster, the mode, the
   window, the questions, the answers, the scores, `ms`, `cached`, `changed`, `base_rank`,
   and `base_score`. Its key `inner` holds the difference step (`kind: difference`):
   `producer`, `applied`, `evidence`, `seen`, `contradicted`, `base_rank`, and
   `base_score`. So the order before each re-rank step is known for the touched
   candidates. Four runs hold such records, for example
   `2026-09-24T080721Z-svm-label-gw-cluster-rules-label-only-rules`.
9. No lab pipeline of `config.yaml` has a VLM step or a re-rank step. Each pipeline of
   the backend `embedding` has the view `full` alone. Two old embedding runs have the
   views `full` and `label`:
   `2026-09-25T205239Z-lab-gx10-siglip2-so400m-patch16-naflex-p256-official-real-photos-smoke`
   and `2026-09-25T205359Z-lab-gx10-siglip2-so400m-patch16-naflex-p256-official-real-photos`.
10. A 1024 px PNG of a test photo has a median size of 510 KB. The same image as WebP has
    47 KB (25 photos, measured on 2026-09-26). This is why the run writes no image file.

### 3.2 The step view of 8162

`drink-atlas-recognize/src/main.tsx` and `src/style.css` render it. The facts below come
from these files.

1. A round is a block with an `h2`: "Round N", a note, and at the right a clock. The clock
   shows the elapsed time of the round and the sum of its step times. Elapsed is the last
   end minus the first start. The saving (sum minus elapsed) shows only when the sum is
   larger.
2. A step is a card. The head holds the two-digit number, the name, the meta line
   `host · model · group` in a monospace font, the time as `0.03 s`, and a state pill
   (done, running, waiting, failed, skipped).
3. The body holds the error, the artifacts (a figure with the image and a monospace
   caption, for example `00-input.jpg`), boxes drawn over the photo, candidate lists, and
   two closed sections: "Step settings" (the configuration as JSON) and "Result" (the
   output as JSON).
4. A card is closed at the start. A click on the head opens or closes it. A failed card is
   always open.
5. A click on an image opens a large view. A click or Escape closes it.
6. The left border of a card marks a lane. Steps that ran at the same time share a lane.
   The lanes alternate between purple and blue. A step that never started has no lane.
7. A critical step gets a pink inner stripe and the pill "critical path".
8. Light is the default. Dark follows `prefers-color-scheme`.

## 4. Design

### 4.1 The trace of an embedding run

`EmbeddingBackend.ask` measures each step with `time.perf_counter`. It returns a fifth
value: the trace. `benchmark.run_benchmark` writes it into the row as the key `trace`. A
backend that returns four values gets no key `trace`. So `benchmark.py` stays the writer
of every run.

```json
"trace": {
  "v": 1,
  "steps": [
    {"id": "input", "start_ms": 0.0, "ms": 11.8,
     "out": {"width": 3024, "height": 4032}},
    {"id": "sam3-package", "start_ms": 11.8, "ms": 402.3, "cached": false,
     "out": {"method": "seg", "box": [120, 40, 900, 2000]}},
    {"id": "sam3-label", "start_ms": 414.1, "ms": 3.1, "cached": true,
     "out": {"found": false}},
    {"id": "view", "view": "full", "start_ms": 417.2, "ms": 41.0,
     "out": {"width": 768, "height": 1024, "bytes": 523001, "sha256": "..."}},
    {"id": "embed", "start_ms": 458.2, "ms": 298.4,
     "out": {"views": ["full"], "dim": 1152}},
    {"id": "search", "view": "full", "start_ms": 756.6, "ms": 3.2,
     "out": {"rows": 4043, "wines": 2046,
             "top": [{"slug": "...", "cosine": 0.9419, "sha256": "...",
                      "type": "main_patched", "embedding_hash": "..."}]}},
    {"id": "score", "start_ms": 759.8, "ms": 0.9, "out": {"wines": 2046}}
  ]
}
```

Rules:

1. `start_ms` and `ms` count from the start of `ask`. Each value has one decimal.
2. A SAM3 step holds `cached`: true when `model_cache` gave the answer.
   `derive.Sam3Client._post` stores this in a thread-local value. `Sam3Once` reads it.
3. A SAM3 step exists only when a view needs its target.
4. A view with no input gets a step with `error`, for example "SAM3 found no label".
5. `search.top` holds the `top_k` wines of that view alone, by their best cosine in that
   view. Each wine names its best item. This is the result before the score step.
6. The score step holds no list. Its list is the candidates of the row.
7. A step that raises gets `error`. The trace ends at that step. `ask` returns the trace
   with the error.
8. `/api/run` removes `trace` from its rows, as it removes `items`.

### 4.2 The route

`GET /api/run-steps?id=<run>&query=<query id>` answers the steps of one photo. The new
module `pipeline/run_steps.py` builds the answer. `run_routes.py` calls it.

```json
{
  "run": "<run id>", "query": "q-000001", "kind": "embedding",
  "configuration": "local-siglip2-p256-crop",
  "photo": {"url": "/images/testset/<sha256>.jpg", "path": "<slug>/01.jpg",
            "width": 3024, "height": 4032},
  "row": {"label": "positive", "outcome": "hit", "rank_of_truth": 1,
          "truth": ["<slug>"], "slug": "<slug>", "latency_ms": 812, "error": null},
  "recorded": true,
  "rounds": [{"n": 0, "title": "Round 0", "note": "the photo", "steps": ["<step>"]}],
  "notes": []
}
```

A step:

```json
{"n": 1, "id": "sam3-package", "name": "Package cut",
 "service": "gateway", "model": "sam3", "group": "segment",
 "start_ms": 11.8, "ms": 402.3, "state": "done", "cached": false, "error": null,
 "artifacts": [{"src": "...", "caption": "01-package-box.jpg", "width": 3024,
                "height": 4032, "boxes": [[120, 40, 900, 2000]], "check": null}],
 "lists": [{"title": "...", "note": "...", "items": [
   {"slug": "...", "name": "...", "rank": 1, "score": 0.9419, "image": "...",
    "truth": true, "forbidden": false, "moved": null, "detail": "full 0.9419"}]}],
 "vlm": null,
 "settings": {}, "result": {}, "notes": []}
```

1. `state` is `done`, `failed`, or `skipped`. `ms` null means "time not recorded".
2. `check` of a derived image is `same` when the image made again has the sha256 of the
   trace, `changed` when it has another sha256, and null when the run recorded none.
3. A derived image comes as a PNG data URI, as in `/api/run-inputs`. A cut image gets a
   long side of 1024 px at most. The caption states the full size.
4. `service` is `local` for a step in the process. For an HTTP step it is `gateway` when
   the host is the gx10 gateway `192.168.86.14:18081`, `matcher` for a
   `svoe-vino-matcher` URL, and the host otherwise.
5. `image` of a list item is the catalogue item PNG of the index when the present index
   holds the item with the hash of the trace. Otherwise it is the card image of the slug.
6. A run or a query that does not exist answers HTTP 404.

### 4.3 The steps of each run kind

Embedding run:

| n | Round | id | Name | Meta | What the body shows |
|---|---|---|---|---|---|
| 00 | 0, the photo | `input` | Input photo | local | the photo |
| 01 | 1, the model inputs | `sam3-package` | Package cut | gateway · sam3 · segment | the photo with the box, the cut |
| 02 | 1 | `sam3-label` | Label cut | gateway · sam3 · instances | the photo with the box, the cut |
| 03.. | 1 | `view` | View `<name>` | local · the step names | the model input, its sha256 check |
| next | 2, the embedding and the search | `embed` | Embedding | gateway or local · the model | the views sent, the vector size |
| next | 2 | `search` | Search, space `<view>` | local · the entry · the view | the top list of that space |
| last | 2 | `score` | Score | local | the answer: the mean of the best cosine of each view |

A SAM3 step and a view step exist only when a view of the run needs them. A pipeline with
the key `barcode` (plan 42) adds the step `Decode codes, whole photo` (HTTP · qr-scanner)
after the input photo. When a code of `wine_code` answers the photo, no embedding model
ran, and the popup shows the photo and this step alone. An old
embedding run gets the same steps with no time. Its search step lists the candidates of
the row by the cosine of that view, with a note that the run kept no top list of the
space.

Matcher run:

| n | Round | Name | What the body shows |
|---|---|---|---|
| 00 | 0, the photo | Input photo | the photo |
| 01 | 1, the model inputs | Matcher inputs | the images of `/api/run-inputs`, made again with the matcher code |
| 02 | 2, the matcher request | Search | the base order: the order before the re-rank; time is `latency_ms`, the whole request |
| 03 | 3, the re-rank | Difference words | the producer, the evidence, the seen and the contradicted words, the order after the step |
| 04 | 3 | VLM cluster rule | the mode, the cluster, the questions and the answers, the scores, the time, the order after the step |

Round 3 exists only when the run holds `explain` records. A candidate with no `explain`
keeps its rank in the base order. The list of a re-rank step marks a move with ▲n or ▼n.

Remote run, mock run, and another run: 00 Input photo, then 01 with the answer of the
backend and `latency_ms`.

### 4.4 The page

1. A click on the query photo of a row opens the step popup. A click on a candidate image
   opens the large view, as before (plan 38).
2. The popup head shows the file name, the label and the outcome tags, the rank of the
   true wine, the pipeline, the run, the total time of the photo, and a button "close ✕".
3. The body shows the rounds and the step cards of section 3.2, in the colours of 8162.
   The page defines the lane and pill colours for light and dark. It uses the lab theme
   for the rest.
4. A lane marks steps that overlap in time, as on 8162. The runner makes the steps one
   after another, so the lanes alternate from step to step. A step with no time has no
   lane. The trace rounds each time to 0.1 ms, so a gap of less than 1 ms is no overlap.
5. The popup shows no "critical path" pill. Each step of the runner is on the critical
   path, so the pill tells nothing.
6. The card of the input photo is open at the start, as in the screenshot of the owner.
   The other cards are closed. A failed card is always open. The page keeps the open step
   ids while the popup is open, also when the popup moves to another photo.
7. A SAM3 step draws its box over the photo with SVG.
8. A list shows candidate cards: the image, `#rank`, the score, and the slug. The true
   wine has a green frame, and the slug of a negative photo has a red frame, as in the
   rows.
9. The VLM box shows each question with its answer, the score of each wine, the time, and
   `cached`. The question text comes from the `explain` record of the run alone. The page
   does not read `dataset/catalog-cluster*.json` (owner message of
   2026-09-26T07:32:51+0300, plan 43).
10. A click on an artifact image opens the large view above the popup.
11. Escape closes the large view first, then the popup. The arrow keys up and down move
    the popup to the photo of the row above or below.
12. The bottom line shows the total time of the photo, the sum of the step times, and the
    time outside the steps.

## 5. Tests

1. `tests/test_embedding_run.py`: the trace of a run with the views `full` and `label`,
   and of a run with the view `full` alone: the step ids and order, `cached`, the sha256
   of a view equals the sha256 of the PNG that went to the model, the top list of a view
   follows the cosine of that view, a view with no label cut, and a failed request.
   `/api/run` sends no `trace`.
2. `tests/test_benchmark.py`: a backend that returns four values writes no `trace`; a
   backend that returns five values writes it.
3. `tests/test_run_steps.py`: the route for an embedding run with a trace (the rounds, the
   times, the check `same`, the check `changed`), an old embedding run (no time, the
   note), a matcher run with `explain` (the base order, the two re-rank steps, the moves),
   a remote run, a mock run, an unknown run, and an unknown query.
4. A Playwright check of the popup in the light and the dark theme: open, a card opens and
   closes, an artifact opens the large view, Escape, the arrow keys, no page error, and no
   sideways scroll at 390 px.

## 6. After the code

1. A restart of 8168 for the route (rules 22 to 24 of `AGENTS.md`).
2. A probe run of 30 photos of the set `my`, so that one run has a trace:
   `~/.venvs/svoe-vino-lab/bin/python pipeline/embedding_run.py --name local-siglip2-p256-crop --set my --limit 30 --label trace-probe`.
   The backend `local` runs on this Mac and sends no request to gx10.
3. The owner decides when to start full runs with a trace.
4. No pipeline has the view `label`. The owner decides whether to add a pipeline with the
   views `full` and `label`, so that the popup shows two search spaces.

## 7. Open points

None at the start of the code.

## 8. Result

Done on 2026-09-26.

1. `embedding_run.py`: `Trace`, `cut_targets`, `view_input`, `Catalogue.view_top`; `ask`
   returns the trace as a fifth value; `cuts_of` and `Catalogue.rank` record their
   steps. `derive.Sam3Client.cached` tells whether the last call of the thread read
   `model_cache`. `benchmark.py` `one` writes the fifth value as `trace` (in the commit
   5952bca of plan 42, with the agreement of this session).
2. `pipeline/run_steps.py` and the route `/api/run-steps` in `run_routes.py`;
   `run_view` removes `trace`.
3. `runs.html`: the popup `#sp`, its CSS (the lane and pill colours of 8162, light and
   dark), and the JS block of plan 41. The click on the query photo and the keys
   Escape, up, and down.
4. Tests: `tests/test_run_steps.py` (10, new), `tests/test_embedding_run.py` (5 new, 38
   in all), `tests/test_benchmark.py` (1 new, 14 in all). The full suite: 768 OK.
5. The live server answers the route for all kinds of runs. The two-view run
   `2026-09-25T205359Z-...-official-real-photos` gives an answer of about 4 MB in 1.5 s,
   because the cuts come at a long side of 1024 px.
6. The probe run `2026-09-26T044622Z-lab-local-siglip2-p256-crop-my-trace-probe` (30
   photos of the set `my`) recorded the trace. Median step times: input 4 ms, package cut
   61 ms (each a cache hit), view 29 ms, embedding 54 ms (1.9 s for the first photo, which
   loads the model), search 2 ms, score 1 ms. The trace adds about 3.4 KB to a row.
7. Playwright: 27 checks on the two-view run and a matcher run, and 12 checks on the probe
   run, in the light and the dark theme, with no page error. The popup has no sideways
   scroll at 390 px. The page behind it scrolls sideways at 390 px; that is older than
   this plan (plan 38).
