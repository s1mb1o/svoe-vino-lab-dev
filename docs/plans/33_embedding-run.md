# Plan 33: the runner of the embedding configurations

Date: 2026-09-25. Session: drink-atlas-workspace-ab [539687].

Source: owner message of 2026-09-25T23:19:28+0300 and the answers of 23:24:20. The text
is in [../owner-messages.md](../owner-messages.md).

## 1. Goal

1. A new runner makes a run of one embedding configuration of `config.yaml` on one test
   set. An embedding configuration is an entry of the key `embeddings` with the backend
   `openai` or `local`.
2. Each test photo gets the preparation of a catalogue image: the SAM3 cuts, then the
   steps of each view of the entry.
3. The endpoint of the entry gives the vector of each view. The vectors rank the wines
   with the catalogue vectors of `data/embeddings/<name>/`.
4. The run appears on `/runs` under its pipeline. The button `Run>` of `/testset`
   (plan 32) starts it through a pipeline of the backend `embedding` (section 9).

## 2. Facts of 2026-09-25

1. `config.yaml` holds 11 embedding entries: 10 entries of the backend `openai` (the
   gateway of gx10) and 1 entry of the backend `local`. Each index holds 4,039 items: 2,021
   of the view `full` and 2,018 of the view `label`. The builds ran from 18:14 to 18:37.
2. At 20:53 the label cuts were made again with the body-label rule (owner answers of
   19:16:44 and 20:24:14). 111 cuts changed. So 111 `label` items of each index are
   stale. The index `gx10-siglip2-so400m-patch16-naflex-p256` holds 3,926 current, 111
   stale, 4 failed, and 3 missing items. 1,928 of 2,045 wines have a current vector in
   both views. 117 wines have a current `full` vector alone.
3. The test photos have no cuts. 4 of the 1,841 distinct query images of `my` have a
   package cut. 0 of the 80 query images of `official-real-photos` have one.
4. The queries of `benchmark.build_queries`: `my` 2,209 (1,841 distinct images),
   `official-real-photos` 80, `vlmrerank-8b-failed` 171.
5. The label cut run of 20:30 took 0.70 s for each SAM3 call on gx10. `model_cache`
   keeps each SAM3 answer in `data/cache/sam3/` (plan 25).
6. A build took 0.17 s for each item on the gateway (`gx10-dinov3-vitb16`, while 10
   builds ran at the same time) and 0.34 s for each item with the backend `local`.
7. The label experiment of svoe-vino-matcher (2026-09-22, 1,600 positive photos): the
   whole photo gave R@1 0.759, the label cut 0.743, and the sum of the two 0.793.

## 3. Decisions of the owner (23:24:20)

1. The runner cuts each test photo at run time, in memory, with the rules of the
   catalogue. The runner writes nothing to the database.
2. The score of a wine is its best `full` cosine plus its best `label` cosine. A photo
   with no label cut uses the `full` score alone. One run has one ranking.
3. The dialog `Run>` starts these configurations. An entry with no index is disabled
   with the note `no index`.
4. This session adds separate hunks to `ChangeLog.md`, `README.md`, and `SMOKE_TESTS.md`.

## 4. The question Q1

**Q1. The score of a wine with no current vector in a view.** Decision 2 does not cover
a wine that has no current `label` vector. Today 117 wines have none.

| Option | Rule | Effect |
|---|---|---|
| A | The mean of the view scores of the wine. A wine with both views keeps the order of the sum. | A wine with no `label` vector competes with its `full` cosine alone. |
| B | The missing view adds 0. This is the sum as written. | Such a wine rarely enters the top 10 when the photo has a label cut. |

Answered on 2026-09-25T23:35:19+0300: option A, "Mean of its views". The owner also
allowed the live check of section 12 without a build: the 111 stale `label` items stay
out of the ranking.

## 5. The preparation of a test photo

1. The runner opens the photo with `derive.open_image`. The EXIF orientation applies.
2. A view whose first step is `segment` with the target `package` uses the package cut of
   `derive.derive_image`. This is the function, the SAM3 nouns, and the mask rules of a
   catalogue image (plan 09). When SAM3 finds no package, the white rule of the same
   function cuts the border.
3. A view with the target `label` uses the label cut of a new function
   `alternatives.label_cut_of`. It holds the rule of `label_derivatives`, with the
   body-label rule of 20:24:14. `label_derivatives` calls the new function, so the two
   rules stay equal. When SAM3 finds no label, the view has no input for this photo.
4. A new function `embeddings.apply_steps` holds the step code of `embeddings.prepare`.
   `prepare` calls it. So a test photo and a catalogue image get their pixels from the
   same code.
5. Each test photo counts as a full photo (the role `full`). The runner does not know
   whether a photo is a close-up.
6. SAM3 answers go to `data/cache/sam3/`. A second run of the same set sends no SAM3
   request, with any configuration.
7. When SAM3 does not answer, the photo gets an error, and the run asks SAM3 no more.
   This is the rule of `derive._Once`. So a run with no SAM3 service ends fast.

## 6. The vectors and the score

1. The runner sends one request for each photo. It holds the input of each view: one or
   two PNG data URIs. The code is `build_embeddings.OpenAIBackend` or
   `build_embeddings.LocalBackend`, the code of the build. `extra_body` of the entry goes
   into the request.
2. The runner divides each vector by its length. The cosine is the dot product.
3. The catalogue side is the current items of the index (`embeddings.item_status`). A
   stale, missing, or failed item is not used. `run.json` states the counts.
4. For each view, the runner takes the best cosine of each wine over its current items
   in that view. The wines and their images come from `embeddings.read_inputs`: the
   Active wines, and `main_patched` in place of `main`. A file of two wines counts for
   each wine.
5. The score of a wine is the mean of its view scores over the views of the photo (Q1,
   option A). For a wine with both views, the order is the order of the sum of
   decision 2. A wine with no current vector in any view of the photo is not a
   candidate.
6. The candidates are the `top_k` wines (10), the highest score first. A tie goes by the
   slug. Each candidate holds `slug`, `score`, `rank`, and the cosine of each view under
   the keys `full` and `label`.

## 7. The run files

1. `benchmark.run_benchmark` writes the run files, with `configuration` = the name of
   the entry. `benchmark.py` does not change.
2. The key `backend` of `run.json` holds `kind: embedding`, `url` (the endpoint; null for
   the backend `local`), `model`, `extra_body`, the steps of each view, `top_k`,
   `workers`, `score`, and the SAM3 settings.
3. The key `embeddings` of `run.json` holds `built_at` (`updated_at` of `index.json`),
   `index_file`, `dim`, and the count of each item state. The Runs page shows
   `built_at` and `index_file`.
4. The latency of a photo is the time of the SAM3 cuts, the steps, the request, and the
   ranking.

## 8. The command

```text
python3 pipeline/embedding_run.py --name <pipeline> --set <set>
    [--workers N] [--limit N] [--label TEXT] [--top-k N]
```

`--name` is a pipeline of the backend `embedding` (section 9). An entry of the backend
`local` needs `torch`: run it with `embedding_python`.

## 9. The dialog `Run>` (plan 32)

The owner message of 2026-09-25T23:37:48+0300 replaces the first design of this
section. `config.yaml` gets a section `pipeline:`, and the dialog `Run>` and the filter of
`/runs` show the pipelines, not the embedding entries. Session drink-atlas-workspace-6a
[792d65] owns that work and asks the owner how an embedding run enters the dialog. Its
proposal is a pipeline of the kind `embedding` that names an entry of `embeddings:`.

So this session removed its hunks from `run_jobs.py` and `run_job.py` at 23:44. The
owner answered session 6a at 23:55:27: "The embedding runs of plan 33 leave the dialog
and stay a command until a later change."

The later change came on 2026-09-26. The owner wrote at 00:11:19: "embeddings: section is
abou preparint and using embeddings, but pipeline: used for runs". The answers of 00:12:24
and 00:15:17:

1. A run of an embedding is a run of a pipeline of the backend `embedding` (plan 34 of
   session 6a). The key `embedding` of the pipeline names an entry of `embeddings:`.
   `config.yaml` holds one such pipeline: `gx10-siglip2-so400m-patch16-naflex-p256`, with
   the name of its embedding entry. The owner adds the others later.
2. The 2 runs of 2026-09-25 hold that name in `configuration` already, so their
   `run.json` did not change.

The split of the work (agreed with 6a at about 00:16):

1. 6a: the backend `embedding` in `pipelines.py` (`Pipeline.embedding`, and a check that
   the named entry is a valid entry of `embeddings:`), the entry of `config.yaml`, the
   branch of `run_job.build`, and the rules of `run_jobs`: the note
   `embedding_run.NO_INDEX` when `embedding_run.index_ready` is false, and
   `embedding_python` as the interpreter of the job, because the backend `local` needs
   `torch`.
2. This session: `embedding_run.py --name` takes a pipeline name (`find_pipeline`). The
   new `build_pipeline_backend(pipeline, config_path)` finds the embedding entry and gives
   the backend the id of the pipeline; `spec["embedding"]` names the entry. `run.json`
   holds `configuration: <pipeline>`. `run_job.build` calls the same function.

The owner message of 2026-09-26T00:45:33 and the answers of 00:52:41 (through session 6a)
add the key `views` to a pipeline of the backend `embedding`: the steps of the test photo
in place of the steps of the entry. The catalogue side stays the index, and a view of the
photo ranks the catalogue vectors of the same view. Two pipelines use it:
`siglip2-p256-as-is` (the step `resize` alone) and `siglip2-p256-crop` (`segment` with the
target `package`, then `resize`; the background inside the box stays). In
`embedding_run.py`, `query_inputs` asks SAM3 only for a view whose first step is
`segment`, and `EmbeddingBackend` takes `views` (also into `spec["views"]`, so that
`/api/run-inputs` makes the right input again). 6a checks the key in `pipelines.py`.

At about 01:07 the owner removed the first pipeline, `gx10-siglip2-so400m-patch16-naflex-p256`,
from `config.yaml`, and chose "Leave as is" at 01:19:00 (a question of session d3): its 2
runs of 2026-09-25 count as `no pipeline`. So the embedding pipelines of `config.yaml` are
`siglip2-p256-as-is` and `siglip2-p256-crop`, and the examples of the docs use
`siglip2-p256-crop`.

## 10. The Runs page

`GET /api/run-inputs` answers a run of `kind: embedding` with the model inputs of the
query photo. The route prepares the photo again with the steps that `run.json` records
and with the SAM3 answers of the cache. It sends no SAM3 request and no embedding
request. A photo with no answer in the cache gets a note.

## 11. Risks

1. A wrong SAM3 cut gives a wrong query. An example is a shelf with more than one
   bottle: the largest package wins. The model inputs on `/runs` show the cut.
2. The first run of `my` sends about 3,700 SAM3 requests (two for each distinct photo) to
   the shared service of gx10. The estimate is about 45 min.
3. The stale `label` items stay out of the ranking until a build of the entry on
   `/embedding`.

## 12. Checks

1. `python3 -m unittest discover -s tests` passes.
2. `python3 pipeline/embedding_run.py --name gx10-siglip2-so400m-patch16-naflex-p256
   --set official-real-photos --limit 3`, then the whole set. On 2026-09-25 `--name` took
   an embeddings entry. Since 2026-09-26 it takes a pipeline, for example
   `siglip2-p256-crop` (section 9).
3. After a restart of 8168, `/runs` shows the run of check 2 with its model inputs.

## 13. The result of the checks (2026-09-26)

1. Check 1: 16 new tests in `tests/test_embedding_run.py`; 673 tests `OK` at
   2026-09-25 23:50. Three mutations of `embedding_run.py` (the sum with 0 for a missing
   view, no stop of the SAM3 requests, a cut with no alpha channel) each failed a test.
2. Check 2: the run of 3 photos and the run of all 80 photos of `official-real-photos`
   ended with 0 errors. The full run: recall@1 0.525, recall@5 0.712 of 59 positive
   photos. 15 of the 16 misses are photos of 10 wines with no row in `wine_image`. On the
   44 photos whose wine has an image, recall@1 was 31 of 44; the official recognizer had
   26. The details are in `ResearchLog.md` of 2026-09-26.
3. Check 3: a direct call of `run_routes.inputs_view` on the live data answered the two
   model inputs of a query (HTTP 200). This session did not restart 8168, because the
   work of sessions 6a and d3 on the lab server was in progress. Session d3 restarted
   8168 at 2026-09-26 00:36:23 (pid 36577). Then `GET /api/run-inputs` of the run of check
   2 answered HTTP 200 with the inputs `full` and `label`, and the dialog `Run>` and the
   filter of `/runs` listed the 2 pipelines of `config.yaml` alone.
4. 2026-09-26, the pipeline change of section 9: 19 tests `OK` in
   `tests/test_embedding_run.py`. Against the live `config.yaml`, `find_pipeline` and
   `build_pipeline_backend` built the backend of `gx10-siglip2-so400m-patch16-naflex-p256`
   with no request, and refused `vino-svoe-search-by-photo` (the backend `svoe-vino-ru`).
5. 2026-09-26, the key `views`: 24 tests `OK` in `tests/test_embedding_run.py`. An as-is
   view sends no SAM3 request and gives the resized photo. A crop view gives
   `resize(photo.crop(box))` with the background kept, and one SAM3 call.
