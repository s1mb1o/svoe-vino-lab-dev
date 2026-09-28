# Plan 31: the remote configuration `vino-svoe-search-by-photo`

Date: 2026-09-25. Session: drink-atlas-workspace-5c [cbb143].

Changed by [plan 34](34_pipeline-section.md) on 2026-09-26: `vino-svoe-search-by-photo`
is an entry of the key `pipeline` of `config.yaml`, not of `embeddings`. It has no key
`views`. `pipeline/pipelines.py` holds its checks.

Source: owner message of 2026-09-25T20:36:26+0300 and the answers of 20:39:30. The text
is in [../owner-messages.md](../owner-messages.md).

## 1. Goal

1. A lab configuration sends each photo of a test set to the official recognizer of
   vino-svoe.ru, `https://api.vino-svoe.ru/v1/wines/search-by-photo`, and writes a run.
2. The Runs page shows the run under the filter `Configuration`.
3. The configuration is the entry `vino-svoe-search-by-photo` of the key `embeddings` of
   `config.yaml`, with `backend: svoe-vino-ru`. The owner wrote the entry stub.

## 2. Facts

1. `scripts/match_backends.py` `HttpMultipartBackend` sends one photo as
   `multipart/form-data` and parses a ranked list of slugs. `backends.yaml` entry
   `official-api` uses it for the same URL.
2. The full run `runs/2026-09-17T194306Z-official-api/` of `scripts/match_run.py` sent
   1,387 photos from this Mac with 8 workers. 1,385 answers were HTTP 201. One answer was
   HTTP 413 and one was HTTP 502.
3. `pipeline/benchmark.py` `run_benchmark` accepts any backend object with `id`, `spec`,
   `top_k`, and `ask(path)`. Its argument `configuration` writes the key
   `configuration` into `run.json` (plan 23).
4. Before this plan, `pipeline/embeddings.py` refused the stub: the backend
   `svoe-vino-ru` was unknown, `url` was an unknown key, and the view `full` held no
   steps.

## 3. Decisions of the owner (20:39:30)

1. A new CLI script `pipeline/remote_run.py` makes the run, as `pipeline/mock_run.py`
   does. `pipeline/benchmark.py` does not change.
2. The photo goes to the API as it is: the bytes of the image store, with no step. The
   entry has zero embedding items.
3. The `/embedding` page hides `Build`, `Stop`, and `Log` for the entry and shows a note
   with the command of a run. `POST /api/embeddings/<name>/build` answers HTTP 400.

## 4. The entry

```yaml
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
  views:
    full:
```

1. The request keys `url`, `field`, `response`, `query`, `top_k`, `timeout_s`,
   `workers`, and `headers` have the meaning of the same keys of `backends.yaml`. Read
   `docs/match-runner.md`. They are the keys of `official-api` in the owner message.
2. The defaults are the defaults of `HttpMultipartBackend`: `field: image`,
   `response: auto`, `query: {}`, `top_k: 1`, `timeout_s: 30`, `workers: 1`,
   `headers: {}`.
3. A header value `env:NAME` reads the environment variable NAME at the start of the
   run. A key value MUST NOT go into `config.yaml`.
4. `views` MAY be absent. When present, it MUST hold the view `full` with no value. The
   backend `svoe-vino-ru` takes no step.
5. The backend `svoe-vino-ru` takes no `base_url`, `model`, `extra_body`, or
   `batch_size`. Another backend takes no request key.

## 5. The code

1. `pipeline/embeddings.py`: the backend `svoe-vino-ru` (`REMOTE_BACKEND`), the request
   keys (`REMOTE_KEYS`), and their check. `Embedding.remote` holds the request keys with
   their defaults, or None. The entry has `views == {}`, so `plan_items` gives zero
   items. `summary()` gets the key `remote`.
2. `pipeline/remote_run.py`:

   ```text
   python3 pipeline/remote_run.py --name vino-svoe-search-by-photo --set my
       [--workers N] [--limit N] [--label TEXT]
   ```

   The script builds `HttpMultipartBackend` from `Embedding.remote`, with `id` = the
   name of the entry and `kind: remote`. It calls `benchmark.run_benchmark` with
   `configuration` = the name. `embeddings` of `run.json` states that a remote matcher
   holds no vectors, so the run sends no request to `/v1/info` of the API.
3. The run id is `<stamp>-lab-<name>-<set>[-<label>]`, by the present rule of
   `run_benchmark`.
4. `pipeline/embedding_routes.py` `start` and `pipeline/build_embeddings.py` `main`
   refuse the backend `svoe-vino-ru`. The text names the command of a run.
5. `pipeline/pages/embedding.html`: the option text `<name> — remote matcher`; the source
   panel shows the URL, the request keys, the view `full` as "the photo as it is", and
   the command of a run; `Build`, `Stop`, and `Log` are hidden; the list shows a note in
   place of the wines.
6. `pipeline/run_routes.py` `inputs_view`: a run whose `backend` in `run.json` holds
   `kind: remote` answers a note and no input. Before this plan, such a run got HTTP 422
   "more than one configuration matches", because the lookup of the local matcher
   configuration does not know the URL of the API.

## 6. Risks

1. A full run of the set `my` sends about 2,200 photos to an external API. The probe of
   2026-09-17 excluded no rate limit over a longer window and no daily quota. The owner
   starts a full run.
2. The multipart file name is now `<sha256>.<extension>` of the image store, not the file
   name of the test set. The API is not known to read the file name.

## 7. Checks

1. `python3 -m unittest discover -s tests` passes.
2. `GET /api/embeddings` lists `vino-svoe-search-by-photo` with no error and zero items.
3. `POST /api/embeddings/vino-svoe-search-by-photo/build` answers HTTP 400.
4. `python3 pipeline/remote_run.py --name vino-svoe-search-by-photo --set my --limit 3`
   writes a run with `configuration: vino-svoe-search-by-photo`, and `/runs` shows it.
