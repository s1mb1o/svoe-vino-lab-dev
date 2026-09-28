# Plan 34: the section `pipeline` of config.yaml

Date: 2026-09-26. Session: drink-atlas-workspace-6a [792d65].

Source: owner message of 2026-09-25T23:37:48+0300 and the answers of 23:55:27. Then the
owner messages of 2026-09-26T00:10:18 and 00:11:19 and the answers of 00:12:24 and
00:15:17, in the session drink-atlas-workspace-ab [539687]. The text is in
[../owner-messages.md](../owner-messages.md).

## 1. Goal

1. `config.yaml` gets a new key `pipeline`. A pipeline is a matcher that answers a test
   photo with a ranked list of wines.
2. The entries `vino-svoe-search-by-photo` (backend `svoe-vino-ru`) and `mock` (backend
   `mock`) move from `embeddings` to `pipeline`. Changed by decision 10: `mock` is gone.
3. The dialog `Run>` of `/testset` and the filter of `/runs` show the pipelines. They do
   not show the entries of `embeddings`.
4. The key `embeddings` keeps the embedding models alone: the backends `openai` and
   `local`. The Embeddings page and the Clusters page show these entries alone.

## 2. Decisions of the owner (23:55:27)

1. A new module `pipeline/pipelines.py` reads the key `pipeline` and checks each entry.
   The code of the remote matcher (plan 31) moves there from `pipeline/embeddings.py`.
2. `mock` moves fully. The random-vector build of `mock` (plan 23, change of Q1) goes
   away. The directory `data/embeddings/mock/` stays on disk. An agent deletes it only
   when the owner asks. Changed by decisions 10 and 11: `mock` is gone.
3. Labels only. The pages show the word "Pipeline". These names stay: the routes
   `/api/run-configurations` and `/api/run-jobs`, the JSON keys `configurations` and
   `configuration`, the key `configuration` of `run.json`, the URL parameter
   `/runs?configuration=`, and the job directories `work/run-jobs/<name>/`. So the 5 old
   runs of the two entries keep their filter value.
4. This session adds separate hunks to `pipeline/pages/testset.html` (stale section 5c),
   `ChangeLog.md`, `README.md`, and `SMOKE_TESTS.md`.
5. The embedding runs of plan 33 (`pipeline/embedding_run.py`) leave the dialog. They stay
   a command until a later change. Session ab removed its dialog hunks for this reason.
   Changed by decision 8.

## 2a. Decisions of the owner after the first change (2026-09-26)

6. 00:10:18: "Pipelines combo shall show only items in pipeline: section of config". The
   filter of `/runs` lists `every run`, the pipelines, and `no pipeline`. It lists no
   other name. A run whose key `configuration` names no pipeline counts as `no pipeline`.
   Note of 2026-09-26T01:19:00+0300: the item `every run` reads `All` (owner answer to
   session d3 [4920ce]).
7. 00:11:19: "embeddings: section is abou preparint and using embeddings, but pipeline:
   used for runs".
8. 00:12:24: a pipeline of the new backend `embedding` names one entry of `embeddings`
   with the key `embedding`. `embedding_run.py --name <pipeline>` and the dialog start
   it. Session 6a writes the backend in `pipelines.py`, `run_job.build`, and `run_jobs`;
   session ab changes `embedding_run.py` (`build_pipeline_backend`). The 2 embedding runs
   of 2026-09-25 move to the pipeline.
9. 00:15:17: `pipeline` gets one such pipeline, for the tested entry, with the same name:
   `gx10-siglip2-so400m-patch16-naflex-p256`. So the 2 runs keep their `run.json`.
   Changed at about 01:07: the owner removed this pipeline from `config.yaml`. Its 2 runs
   count as `no pipeline` (owner answer of 01:19:00 to session d3: "Leave as is").
10. About 00:25: the owner removed the entry `mock` from `config.yaml` by hand. 00:26:27:
   "remove from source also". So the backend `mock`, `pipeline/mock_run.py`,
   `tests/test_mock_run.py`, the mock branch of `run_job.build`, and the mock rows and
   commands of the docs go away. This changes decision 2.
11. 00:29:55 (in the session ab): `data/embeddings/mock/` (808 MB) is deleted; session ab
   deleted it. The 2 mock runs of 2026-09-25 stay in `runs/` as history. The filter of
   `/runs` shows them under `no pipeline`.

## 3. The section in config.yaml

```yaml
pipeline:
  - name: vino-svoe-search-by-photo
    backend: svoe-vino-ru
    url: https://api.vino-svoe.ru/v1/wines/search-by-photo
    field: image
    response: auto
    query: { limit: 10 }
    top_k: 10
    timeout_s: 40
    workers: 8
    headers: {}

  - name: gx10-siglip2-so400m-patch16-naflex-p256
    backend: embedding
    embedding: gx10-siglip2-so400m-patch16-naflex-p256
```

The rules of an entry:

1. `name` matches `embeddings.NAME_PATTERN`. A name MUST NOT occur two times in
   `pipeline`.
2. `backend` is `svoe-vino-ru` or `embedding`.
3. The backend `svoe-vino-ru` takes the keys `url`, `field`, `response`, `query`, `top_k`,
   `timeout_s`, `workers`, and `headers`. The defaults and the checks are the ones of
   plan 31. `url` is required. The entry has no `views`: the photo goes to the matcher
   as it is.
4. Removed with decision 10. The backend `mock` took the keys `name` and `backend`
   alone.
4a. The backend `embedding` takes the key `embedding` in addition. Its value MUST be the
   name of a valid entry of `embeddings`; else the pipeline gets an error. The dialog
   disables the pipeline with the note `no index: build it on /embedding` when the entry
   has no index (`embedding_run.index_ready`). The job runs with `embedding_python`,
   because the backend `local` needs `torch`. The default of `workers` is 1.
5. Another key is an error of the entry. An entry with an error stays in the list with
   its error, as an entry of `embeddings` does. The dialog shows it disabled.
6. A file with no key `pipeline` has no pipeline. A value that is not a list makes the
   file not valid for the dialog and for the filter.
7. An entry of `embeddings` with another backend than `openai` or `local` is an error of
   that entry. The error text names the key `pipeline`.

## 4. The code

1. `pipeline/pipelines.py`: the class `Pipeline` (one checked entry: `name`, `backend`,
   `remote`, `embedding`) and `load(path)`. `load` answers `config_path`, `db_path`, and `entries`, a
   list of (name, Pipeline or None, the error or None). `find(name)` raises KeyError for
   an unknown name and `embeddings.ConfigError` for an entry with an error.
2. `embeddings.read_config(path)` reads the file and the database path. `load_settings`
   and `pipelines.load` use it, so the two keys read the same file in the same way.
3. `pipeline/embeddings.py` accepts the backends `openai` and `local` alone. The remote
   code, `MOCK_MODEL`, and `remote_refusal` go away.
4. `pipeline/build_embeddings.py`: `MockBackend`, `MOCK_DIM`, and the refusal of a remote
   entry go away. `pipeline/embedding_routes.py`: the refusal of a remote entry goes away.
   `pipeline/pages/embedding.html`: the branch of a remote matcher goes away.
5. `pipeline/run_jobs.py` and `pipeline/run_job.py` read the pipelines. Each backend of a
   pipeline has a runner, so the note `no runner yet` goes away. `run_jobs.runnable` checks
   the index of a pipeline of the backend `embedding`, and `run_jobs.interpreter` gives
   its job `embedding_python`. `run_job.build` calls
   `embedding_run.build_pipeline_backend(pipeline, config_path)` for it.
6. `pipeline/run_routes.py` `configurations` reads the pipelines. The hunk of session ab
   in `inputs_view` stays.
7. `pipeline/remote_run.py` finds its entry in `pipeline`. Its command line does not
   change. `pipeline/mock_run.py` is gone (decision 10).
8. `pipeline/pages/runs.html`: the label `Pipeline`, its title, the column `pipeline`,
   and the text `no pipeline`. The filter lists the pipelines alone (decision 6). A run of
   a name that is not a pipeline counts as `no pipeline`.
9. `pipeline/pages/testset.html`: the texts of the dialog say "pipeline".

## 5. Checks

1. `python3 -m unittest discover -s tests` passes.
2. `tests/test_pipelines.py` checks the loader and the project `config.yaml`: the two
   pipelines are in `pipeline`, and no entry of `embeddings` has another backend than
   `openai` or `local`.
3. After a restart of 8168: the dialog `Run>` lists the two pipelines alone. The filter
   of `/runs` lists the two pipelines, and the old runs keep their filter values; the 2
   mock runs count as `no pipeline`. `/embedding` and `/clusters` list the embedding
   models alone.
4. The rows PL1 to PL14 of `SMOKE_TESTS.md`.

## 6. Risks

1. A copy of `config.yaml` with the old layout, for example on another host, makes the
   two entries errors of `embeddings`. The error text names the key `pipeline`.
2. The restart of 8168 also deploys the pending code of the other sessions. Session ab
   asked that this restart deploys its `inputs_view` hunk.

## 7. Part 2: the steps of the test photo in a pipeline (2026-09-26)

Source: owner message of 2026-09-26T00:45:33+0300 ("create basic runner configs"), the
answers of 00:52:41 and 00:57:59.

### Decisions of the owner

12. A pipeline of the backend `embedding` MAY hold the key `views`: the steps of the test
    photo in each view, in the step language of `embeddings`. Without the key, the photo
    gets the steps of the embedding entry, as the pipeline
    `gx10-siglip2-so400m-patch16-naflex-p256` did until about 01:07. The catalogue side
    stays the index of the entry.
13. The photo is resized to a long side of 1024 px (`resize`, `aspect: keep`). The test
    photos are 4,000 to 4,624 px on the long side, about 12 MB each as PNG.
14. "segment and crop" keeps the background inside the box of the package: the step
    `segment` alone.
15. The short names `siglip2-p256-as-is` and `siglip2-p256-crop`.
16. Both pipelines get `white_background`. It does not change an opaque photo. 60 queries
    of `my` (58 photos) and 3 of `vlmrerank-8b-failed` have transparent pixels; without
    the step they fail with the transparency error.

### The entries

```yaml
  - name: siglip2-p256-as-is
    backend: embedding
    embedding: gx10-siglip2-so400m-patch16-naflex-p256
    views:
      full:
        steps:
          - step: white_background
          - step: resize
            max_size: 1024
            aspect: keep

  - name: siglip2-p256-crop
    backend: embedding
    embedding: gx10-siglip2-so400m-patch16-naflex-p256
    views:
      full:
        steps:
          - step: segment
            target: package
          - step: white_background
          - step: resize
            max_size: 1024
            aspect: keep
```

### The rules of the key `views`

1. The views are `full` and `label`. Each view MUST be a view of the named entry, because
   the photo view is compared with the vectors of the same view of the index.
2. `embeddings.check_steps(view, spec, segment_first=False)` checks the steps. The first
   step MAY be another step than `segment`. When `segment` is present, it MUST be the
   first step. `remove_background` MUST come directly after `segment`.
3. The runner asks SAM3 only for the views whose first step is `segment`. So a photo of
   `siglip2-p256-as-is` sends no SAM3 request.
4. `run.json` records the steps of the photo in `backend.views`. `/api/run-inputs` makes
   the model input again from them.

### The code

- 6a: `pipeline/pipelines.py` (`Pipeline.views`, `_views`, the view check of `load`),
  `pipeline/embeddings.py` (`check_steps`), `config.yaml`, `tests/test_pipelines.py`.
- ab: `pipeline/embedding_run.py` (`query_inputs`, `EmbeddingBackend(..., views=None)`,
  `build_backend(..., views=None)`, `build_pipeline_backend`), `tests/test_embedding_run.py`.

### Checks

1. The full suite: 708 tests `OK` (2026-09-26 01:00).
2. After the restart of 8168 at 01:01:42: the dialog and the filter list the four
   pipelines, each runnable. Session ab rebuilt the inputs of 3 photos of
   official-real-photos from the SAM3 cache: the whole photo (768 x 1024) and the box of
   the package with its background.
3. The owner started both pipelines on the set `my` at 01:07 from the dialog. The run
   `2026-09-25T220722Z-lab-siglip2-p256-as-is-my` ended at 01:12:58 in 336 s: 2,209
   answers, 0 errors, recall@1 0.6462, recall@5 0.8597. The run of `siglip2-p256-crop`
   stood at 875 of 2,209 at 01:24 (about 1.1 s per photo, most of it SAM3) with 0 errors;
   its job runs with `embedding_python`.
