# Plan 46: the Health page

Date: 2026-09-26

Source: owner message of 2026-09-26T10:35:48+0300, and the answers of 11:02:57
(session drink-atlas-workspace-cc [d62b09]).

## 1. Goal

Add the page `/health` to the lab server. The page shows the present state of the lab
server. The button `Check` checks each endpoint of `config.yaml`, one row for each
endpoint. A failure gets a clear text: what failed, which request, and what to do.

## 2. The decisions of the owner

| Question | Answer |
|---|---|
| How does `Check` test an endpoint? | Hybrid. Each entry: the lists of the gateway (`/v1/models`, `/running`), or `GET /models` of a cloud service. A real call goes only to a model that runs on gx10 now, and to a cloud entry. A model that does not run gets no call. |
| What does the status part show? | The server and the database, the image description watcher, the jobs, the models that run on gx10. |
| Which other endpoints? | SAM3 and the vino-svoe.ru API. |
| Where does the link go? | Last in the navigation, after `Runs`. |

## 3. Facts about the services

Probes of 2026-09-26 from this Mac. Read `ResearchLog.md`, entry of 2026-09-26 "Health
checks of the endpoints".

- The gateway `http://192.168.86.14:18081` of gx10 is llama-swap. `GET /v1/models` lists
  49 models. Each model has `status.value`: `loaded` or `unloaded`. `GET /running` lists
  the models that run, with `state` (`ready`) and `ttl`. Both answer in about 3 ms. Both
  load no model.
- A request to `/upstream/<model>/<path>` makes llama-swap load the model. At about 10:37
  a probe of `/upstream/sam3/health` loaded SAM3. No other model stopped. So the check
  never sends a request to a model that does not run.
- SAM3 answers `GET /upstream/sam3/health` in about 8 ms when it runs:
  `{"status": "ok", "model": "facebook/sam3", "device": "cuda", "dtype": "fp16", ...}`.
- QwenCloud and DashScope answer `GET <endpoint>/models` with HTTP 200 in about 1 s,
  with the key. The lists hold `qwen3.8-max` and `qwen3.8-flash` (QwenCloud), and
  `qwen3.7-flash` (DashScope). This call costs no tokens.
- The vino-svoe.ru API answers `GET /v1/info` with HTTP 404: that route is a route of
  svoe-vino-matcher. `GET /v1/wines?page=1&perPage=1` answers HTTP 200 in about 1.6 s. The
  body holds `totalItems` (2109).
- A byte-identical chat request to the llama.cpp model `qwen3.5-9b` stopped its server
  at 11:24:33 (the browser test sent the prompt of 11:10 again). The full hit of the
  prompt cache made llama.cpp roll back one token of the recurrent state of the hybrid
  model, and `ggml_abort` stopped the process. llama-swap answered HTTP 502 with an empty
  body. So each chat request of the check holds a new random token (section 5.3).

## 4. The endpoints

| Kind | Source | One row for |
|---|---|---|
| `vlm` | the key `vlm` | each entry |
| `embedding` | the key `embeddings` | each entry |
| `sam3` | `sam3.endpoint` (`derive.configured_endpoint`) | the service |
| `remote` | `import_website.API` | the API; the row names the pipelines of the backend `svoe-vino-ru` whose `url` starts with the API |

An entry that is not valid in `config.yaml` gets a row with the status `error` and the
text of the configuration error.

## 5. The check of one endpoint

### 5.1 The lists of the gateway

An endpoint with no key uses the lists: a `vlm` entry with no `key`, an `embeddings`
entry of the backend `openai`, and SAM3. The root of the endpoint is its scheme and its
host, for example `http://192.168.86.14:18081`. The check reads `GET <root>/running`.
When the answer is a JSON object with a list `running`, the root is a llama-swap
gateway. Then the check also reads `GET <root>/v1/models`.

The model of SAM3 is the part after `/upstream/` of `sam3.endpoint`.

| The model on the gateway | Status | Real call |
|---|---|---|
| not in `/v1/models` | `error`: the gateway has no such model; the close names | no |
| in `/running`, `state` `ready` | the result of the real call | yes |
| in `/running`, another `state` (for example `starting`) | `warn`: the state | no |
| not in `/running` | `idle`: the model does not run; the first call of a job starts it | no |

### 5.2 An endpoint that is not on a llama-swap gateway

This applies to a cloud entry (with `key`) and to a server that has no route `/running`.
The check never reads `/running` of an entry with a key.

1. An entry with `key: {env:NAME}` and no variable `NAME` in the environment of the lab
   server gets `error`. The check sends no request.
2. `GET <endpoint>/models`, with the key. HTTP 401 or 403 gives `error` ("the service
   refused the key"), and no real call. A model that the list does not hold gives a
   note: some services do not list each model.
3. One real call.

### 5.3 The real calls

| Endpoint | Request | OK when |
|---|---|---|
| `vlm` | `POST <endpoint>/chat/completions`: the text `Health check <12 random hex digits>. Reply with OK.`, `max_tokens: 1`, `temperature: 0`, thinking off in the `thinking_field` of the entry | the body holds `choices[0].message` |
| `embedding`, backend `openai` | `POST <base_url>/embeddings`: the `extra_body` of the entry and one grey PNG of 64 x 64 px as a data URI | the body holds one vector of numbers; the row shows its dimension |
| `sam3` | `GET <endpoint>/health` | the body holds `status: ok` |
| `remote` | `GET <API>/wines?page=1&perPage=1` | the body holds `totalItems` |

The check sends no photo to `search-by-photo`. It does not read `model_cache`: a health
check MUST reach the service.

An `embeddings` entry of the backend `local` loads no model:

1. `embedding_python` MUST be a file.
2. `embedding_python -c "import torch, transformers"` MUST end with code 0 in 60 s. The
   row shows the versions and the device (`mps` or `cpu`).
3. The Hugging Face cache (`HF_HUB_CACHE`, else `HF_HOME/hub`, else
   `~/.cache/huggingface/hub`) SHOULD hold a snapshot of the model with a weight file.
   Without it the status is `warn`: the first build downloads the model.

The timeouts: connect 5 s; a list 10 s; a real call 30 s; the import of step 2 60 s.

### 5.4 The status of a row

| Status | Meaning |
|---|---|
| `ok` | the check passed |
| `idle` | the service knows the model; the model does not run; no call |
| `warn` | the check passed with a note, or the model is in a transition |
| `error` | the check failed; the details tell why |

Before the first check, each row shows `not checked`.

### 5.5 The error texts

| Failure | Text (short form) |
|---|---|
| connection refused | no process listens on `<host>:<port>` |
| connect timeout | no connection in 5 s: the host is down, or a firewall drops the packets |
| DNS failure | the host name `<host>` does not resolve |
| TLS failure | the TLS handshake failed: the error |
| read timeout of a real call | the model runs, but gave no answer in 30 s; it can be busy with other requests |
| HTTP 401, 403 | the service refused the key of the variable `NAME` |
| HTTP 404 | the service has no route or no model: the body |
| HTTP 429 | the service is busy, or the quota is used up: the body |
| HTTP 502 of a llama-swap gateway | the gateway got no answer from the model process: the process stopped or crashed during the request; its output is at `GET <root>/logs/stream/upstream` |
| HTTP 5xx | the service failed: the body |
| HTTP 200, wrong body | the answer is not a chat answer, or holds no vector: the body |

Each text also names the URL, the HTTP code, and the first 300 characters of the body
(`(empty body)` when the body is empty).
The details list each request with its HTTP code and its time. A key value never
appears in an answer: the check replaces it with `<redacted>`.

## 6. The status part

Each part has its own field `error`. A part that fails does not stop the other parts.

| Part | Content |
|---|---|
| Server | process id, start time, uptime, the Python version, the path of `config.yaml`, the address |
| Database | path, size, the schema version of the file and of the code, the wines of each state, the free disk space (`warn` below 5 GB) |
| Watcher | `image_descriptions.watcher_status`, and the failures of the last hour in `work/describe_images.log`: the count and the last 5 lines |
| Jobs | the embedding builds and the run jobs in the state `running` or `stopping` |
| Gateway | the models of `GET <root>/running` of each llama-swap root; the models that `config.yaml` names are marked |

The page loads the status at the start and again after each check.

## 7. The routes

| Route | Answer |
|---|---|
| `GET /health` | the page |
| `GET /api/health` | `status` (the parts of section 6) and `endpoints` (kind, name, model, endpoint, key variable, the configuration error) |
| `POST /api/health/check` | one row: the body `{"kind": "<kind>", "name": "<name>"}`; the answer holds `status`, `summary`, `details`, `ms` |

`pipeline/health.py` answers each route. One request for each endpoint: the page fills
each row when its answer comes, so the page shows the progress, and a slow endpoint does
not hold the other rows. The page sends at most 4 requests at the same time.

## 8. The page

- The header: the title `Health`, the navigation, the button `Check`, and one line with
  the progress and the counts of each status.
- The status part: one card for each part of section 6.
- The table of the endpoints: kind, name, model, endpoint, status, details, time. The
  details show the summary line. A `<details>` element holds the requests.
- The theme of `theme.css`: light and dark, after the system setting.

## 9. The files

| File | Change |
|---|---|
| `pipeline/health.py` | new: the status, the checks, `handles`, `respond` |
| `pipeline/pages/health.html` | new: the page |
| `pipeline/lab_server.py` | `NAV`, the dispatch of the routes, `server.started_t` |
| `pipeline/pages/{dataset,embedding,clusters,testset,runs}.html` | the link `Health` in the `<nav>` line |
| `tests/test_health.py` | new |
| `tests/test_lab_server.py` | the navigation test reads `health.html` too |
| `README.md`, `docs/API.md`, `ChangeLog.md`, `SMOKE_TESTS.md`, `ResearchLog.md` | the documentation |

No schema change. The new routes need a restart of 8168.

## 10. The tests

`tests/test_health.py` starts a fake llama-swap gateway and a fake cloud service on
`127.0.0.1`:

1. A `vlm` entry that runs gets a real call and `ok`.
2. A `vlm` entry that does not run gets `idle`, and the fake gateway gets no chat call.
3. A model that the gateway does not list gets `error` with the close names.
4. A closed port gives `error` with "no process listens".
5. A cloud entry with no variable gets `error`, and no request.
6. A cloud entry with a refused key gets `error` with the variable name; the key value
   is not in the answer.
7. A cloud entry with an accepted key gets a real call and `ok`.
8. An `embeddings` entry that runs gets `ok` with the dimension; one that does not run
   gets `idle`.
9. SAM3 that runs gets `ok`; SAM3 that does not run gets `idle`, and no `/health` call.
10. A real call with no answer in time gives `error` with the timeout text.
11. The `remote` row reads `totalItems`.
12. The `local` backend: a missing interpreter gives `error`; a missing cache gives
    `warn`.
13. The routes: `GET /health`, `GET /api/health`, `POST /api/health/check` with a wrong
    body (400) and an unknown name (404).
14. Two checks of the same entry send two different prompts.
15. An HTTP 502 with an empty body from the gateway gives the text about the model
    process and names `/logs/stream/upstream`.

## 11. Risks

- A real call to a model that runs adds one short request to its queue. The llama.cpp
  model `qwen3.5-9b` has 1 slot, so the call can wait behind a long answer. The row then
  shows the timeout text.
- A model can stop between the read of `/running` and the real call (its `ttl` ends).
  The call then makes the gateway load the model again. The window is a few
  milliseconds.
- Each check costs a few tokens on each cloud entry.
- A llama.cpp server with a hybrid (recurrent) model stops on a byte-identical repeat of
  a prompt. llama.cpp 45b455e keeps one token to evaluate on a full prompt match and
  removes the last position from the memory; the recurrent state cannot drop one
  position, so `common_context_seq_rm` calls `GGML_ABORT`. The random token of each chat
  request prevents the full match. This happened one time, at 11:24:33, before the fix.
  `cache_prompt: false` also prevents it, but it is a field of llama.cpp alone, and
  another service can refuse an unknown field.
