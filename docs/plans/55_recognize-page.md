# Plan 55: the Recognize page

Date: 2026-09-26. Session: drink-atlas-workspace-41 [501d23].
Status: done on 2026-09-26, not committed. The owner selected the approach on
2026-09-26T22:37:00+0300.

Source: owner message of 2026-09-26T22:32:00+0300 and the answers of 22:37:00. The text
is in [../owner-messages.md](../owner-messages.md).

## 1. Goal

A new page `/recognize` recognizes one photo that the user gives.

1. The top of the page holds the pipeline select.
2. Below the select, a drop area takes one image: drag and drop, or a click that opens
   the file dialog.
3. Below the drop area, the page shows the steps of the photo, as the step popup of
   `/runs` shows them ([plan 41](41_run-step-popup.md)): the rounds, the step cards, the
   times, and the total of the photo.

## 2. Decisions of the owner

| Question | Options | Answer |
|---|---|---|
| Where does the pipeline run? | a subprocess for each photo; inside the server, with a cache; a warm worker process | a subprocess for each photo |
| Which pipelines does the select offer? | the pipelines of the backend `embedding`; also `vino-svoe-search-by-photo` | the pipelines of the backend `embedding` |
| Do the other pages link to the new page? | a link on every page; no link; a link on `/runs` alone | a link on every page |
| How does the page get the step renderer? | a copy in the page; shared files `steps.js` and `steps.css` | shared files |

## 3. Facts

1. `embedding_run.build_pipeline_backend` builds the backend of one pipeline:
   `EmbeddingBackend`, with `cluster_rerank.ClusterRerank` for the key `rerank` and
   `barcode.CodeFirst` for the key `barcode`. `ask(path)` returns five values. The fifth
   value is the step trace of plan 41.
2. `run_steps.embedding_rounds(ctx)` makes the rounds and the steps of one row from the
   trace. It makes the cuts and the model inputs again from the SAM3 answers of
   `data/cache/sam3/`. It needs `ctx.row`, `ctx.spec`, `ctx.photo`, `ctx.lists`,
   `ctx.notes`, and `ctx.db_path`.
3. The lab server runs on the Homebrew `python3` 3.14.7. That interpreter has numpy,
   Pillow, and torch. It has no zxing-cpp. `embedding_python`
   (`~/.venvs/svoe-vino-lab/bin/python`) has zxing-cpp and torch. So a pipeline with the
   key `barcode` runs only in `embedding_python`. `run_jobs.interpreter` gives that path.
4. A new process of `embedding_python` imports the modules in 0.45 s and builds the
   backend of `barcode-siglip2-512-crop` in 1.0 s (measured on 2026-09-26, 4,058 current
   items). A pipeline of the backend `local` also loads its model in each process.
5. The server is a `ThreadingHTTPServer`. A long request blocks only its own thread.
6. An upload of the lab is the raw bytes of the image in the body, with the fields in the
   query (`/api/testset-upload`). `testsets.UPLOAD_MAX` is 20 MB.
7. The step popup of `/runs` has its CSS (about 125 lines) and its JS (about 200 lines) in
   `runs.html`. The JS uses `esc` of the page. The candidate cards use the classes
   `.cand`, `.r`, `.sl`, and `.nobottle`, and the VLM box uses `.vlm`. `runs.html` defines
   these classes for the table too.
8. `lab_pages.page` puts `theme.css` in place of the mark `/* THEME_CSS */`. The server
   reads each page from disk for each request.
9. `config.yaml` has 57 pipelines: 56 of the backend `embedding` and 1 of the backend
   `svoe-vino-ru`.

## 4. Design

### 4.1 The runner script `pipeline/recognize.py`

```text
python pipeline/recognize.py --config <config.yaml> --name <pipeline> --photo <path>
    [--top-k N]
```

1. The server starts the script with `run_jobs.interpreter`, so the script runs in
   `embedding_python`.
2. The script builds the backend with `embedding_run.find_pipeline` and
   `embedding_run.build_pipeline_backend`. Then it calls `ask(photo)` one time.
3. The script writes one JSON object to stdout:
   `{"spec", "candidates", "latency_ms", "http_status", "error", "trace", "build_ms"}`.
   `spec` is `backend.spec`, the key `backend` of a `run.json`. `build_ms` is the time of
   the backend build. The key `items` of each candidate (plan 38) stays out, because the
   step view does not read it.
4. During the work, the script sends the output of the modules to stderr. So stdout holds
   the JSON alone.
5. A failure before `ask` (an unknown pipeline, no index, an import error) writes
   `{"error": "..."}` and exits with the status 1. A failure inside `ask` (SAM3, the
   embedding endpoint) is the answer of `ask`: the trace holds the failed step, and the
   status is 0.
6. The script sends the SAM3 request and the embedding request of one photo, as a run
   does. SAM3 answers go to `data/cache/sam3/`. The script writes no other file.

### 4.2 The routes `pipeline/recognize_routes.py`

| Route | Answer |
|---|---|
| `GET /recognize` | the page |
| `GET /api/recognize` | `{"pipelines": [{"name", "embedding", "barcode", "rerank", "runnable", "reason"}]}`: each pipeline of the backend `embedding`, in the order of `config.yaml` |
| `POST /api/recognize?pipeline=<name>&name=<file name>` | the body is the image. The answer is the step view of the photo |
| `GET /recognize/photo/<sha256>.<ext>` | the uploaded photo |

`POST /api/recognize`:

1. The pipeline MUST be a valid pipeline of the backend `embedding`. `run_jobs.runnable`
   MUST allow it. Else: HTTP 400 with the reason.
2. The body MUST be 1 byte to `testsets.UPLOAD_MAX` bytes. Pillow MUST open it. Else:
   HTTP 400. The body reader of the server gives no body for a length above the limit, so
   the route cannot tell an empty body from a body that is too large.
3. The server writes the body to `work/recognize/<sha256>.<ext>`. The extension comes from
   the Pillow format: `jpg`, `png`, `webp`, `gif`, or the lower-case format name. A file
   with the same sha256 stays as it is. The server deletes no upload. `work/` is not in
   git.
4. The server starts `recognize.py` and waits 300 s at most. A timeout, or the status 1,
   gives HTTP 503 with the error of the script.
5. The server makes a row from the answer: `image_path` is the file name, `image_sha256`
   is the sha256, and `candidates`, `latency_ms`, `http_status`, `error`, and `trace` come
   from the script. The row has no label and no truth.
6. The server calls `run_steps.embedding_rounds` with a context whose photo is the upload
   (a subclass of `run_steps.Photo`). The candidate lists get the card image and the name
   of each slug, as on `/runs`.
7. The answer has the keys of `/api/run-steps` (`kind`, `configuration`, `photo`, `row`,
   `recorded`, `rounds`, `notes`), and in addition `sha256`, `build_ms`, and `process_ms`
   (the wall time of the script: the start of Python, the build, and `ask`).

The route module writes no file other than the upload and changes no row of the lab
database. `run_steps.py` does not change.

### 4.3 The shared step renderer

1. New file `pipeline/pages/steps.css`: the CSS of the step view of plan 41. It holds the
   lane and pill colours (light and dark), the rounds, the step cards, the artifacts, the
   lists, the data sections, the total line, and a copy of the candidate card rules and
   the VLM box rules under `.step`. The popup shell `#sp` stays in `runs.html`.
2. New file `pipeline/pages/steps.js`: one global object `Steps` with
   `Steps.html(data, open)` (the notes, the rounds, and the total line of an answer),
   `Steps.toggle(head, open)` (open or close one card), and `Steps.dur(ms)`. `open` is the
   set of the open step keys of the page. The file has its own escape function, so it
   does not depend on `esc` of a page.
3. `lab_pages.page` puts `steps.css` in place of the mark `/* STEPS_CSS */` and
   `steps.js` in place of the mark `/* STEPS_JS */`. Each mark is optional and MAY occur
   one time. A page with no mark does not change. So `scripts/review_server.py` does not
   change.
4. `runs.html` changes: the CSS block of plan 41 (the part that `steps.css` now holds)
   becomes the mark `/* STEPS_CSS */`. The JS functions `stepKey`, `dur`, `score4`,
   `stepLanes`, `roundClock`, `artifactHtml`, `stepItemHtml`, `stepListHtml`,
   `stepVlmHtml`, `stepDataHtml`, and `stepHtml` become the mark `/* STEPS_JS */`.
   `renderSteps` keeps its header part and calls `Steps.html`. `toggleStep` calls
   `Steps.toggle`. `slugLine`, `openSteps`, `closeSteps`, `stepSteps`, and the listeners
   stay as they are. The look and the behaviour of the popup do not change.

### 4.4 The page `pipeline/pages/recognize.html`

1. The header and the navigation of the other lab pages, with `Recognize` on.
2. A bar with the pipeline select and the button `Recognize`. The select shows each
   pipeline of `/api/recognize`. A pipeline that cannot run is disabled, and its title
   holds the reason. The selected pipeline is kept in `localStorage` and comes back at the
   next load. The query `?pipeline=<name>` wins over the stored value.
3. The drop area: "Drop a photo here, or click to open a file". It takes one image file.
   A drop or a file choice sends the photo at once. The area shows a small preview and
   the file name of the present photo.
4. The button `Recognize` sends the present photo again, for example after a change of
   the pipeline. A change of the pipeline alone sends nothing.
5. During the request, the page shows "Recognizing with <pipeline>…" and the seconds
   that went by. The answer of an older request is dropped when a newer request exists.
6. The result: a head line with the file name, the pipeline, the first candidate (slug
   and name), the total of the photo, and the time of the process. Below it, the rounds
   and the steps of `Steps.html`. The card of the input photo is open at the start, as in
   the popup.
7. A click on an image opens a large view. A click or Escape closes it.
8. Light and dark follow the system setting, through `theme.css`. The page has no
   sideways scroll at 390 px.

### 4.5 The navigation

1. Each page gets the link `Recognize` between `Runs` and `Health`: `dataset.html`,
   `embedding.html`, `clusters.html`, `testset.html`, `runs.html`, and `health.html`.
2. `NAV` of `lab_server.py` gets the same entry, for the notice page of a disabled route.

### 4.6 `lab_server.py`

Separate hunks: the import of `recognize_routes`, the entry of `NAV`, one paragraph of the
docstring, the method `_recognize`, one branch in `do_GET`, and one branch in
`_write_route`.

## 5. Order of the deploy

1. The new files and the hunks of `lab_server.py` and `lab_pages.py` land first.
2. A restart of 8168 (rules 22 to 24 of `AGENTS.md`). Before the restart, the session
   checks the pending files of other sessions, because a restart deploys them too.
3. After the restart, `runs.html` gets the marks. The old `lab_pages.py` does not know
   the marks, so this step MUST come after the restart.
4. The navigation hunks of the pages come last. The server reads the pages from disk.

## 6. Tests

1. `tests/test_recognize.py` (new): the script with a fake backend: the JSON keys, no key
   `items`, stdout holds the JSON alone, a failure before `ask` gives the status 1.
2. `tests/test_recognize_routes.py` (new): the pipeline list (the backend `svoe-vino-ru`
   stays out, a pipeline with no index is not runnable), the checks of the upload (no
   body, not an image, too large, an unknown pipeline), the upload file name, the photo
   route (a bad name gives 404), and the step view from a fake script answer.
3. `tests/test_lab_pages.py` (new): the two marks, and a page with no mark.
4. A Playwright check of `/recognize` in the light and the dark theme: the select, a file
   through the file input, the rounds and the cards, a card opens and closes, the large
   view, no page error, no sideways scroll at 390 px. The same check of the popup of
   `/runs`, so that the move of the renderer changes nothing.
5. A live check with one photo of the test set `my` on `barcode-siglip2-512-crop` and on
   one pipeline with no key `barcode`.

## 7. Open points

1. The stale section f4 [b39b7b] lists the popup code of `runs.html`. The owner allowed
   the move at 2026-09-26T22:43:00+0300.

## 8. Result

Done on 2026-09-26.

1. New files: `pipeline/recognize.py`, `pipeline/recognize_routes.py`,
   `pipeline/pages/recognize.html`, `pipeline/pages/steps.css`, `pipeline/pages/steps.js`,
   and the tests `test_recognize.py` (4), `test_recognize_routes.py` (12), and
   `test_lab_pages.py` (4). `lab_pages.py` fills the 2 optional marks. `lab_server.py` got
   6 hunks, `runs.html` 6 hunks, and each other page one nav hunk.
2. The server imports `recognize_routes` in alphabetical order, between `patches` and
   `run_jobs`, 2 lines above the place that the messages to d3, f2, 6c, and bc named.
3. One restart of 8168 at 23:07:24 deployed plan 55 and plan 56 of session 96 together
   (new pid 94543, watcher pid 94574). The same step wrote the new `runs.html` and the nav
   hunks. No other pending code was deployed: the files changed since the start of
   22:25:15 were the files of the two plans alone.
4. The step popup of `/runs` before and after the move: the computed styles of 21 parts,
   the title, and the scroll width are equal for 4 photos in light, dark, and 390 px. The
   HTML differs in the white space between tags alone (the functions of `steps.js` are
   indented 2 more spaces), which the browser does not show.
5. Live runs of `recognize.py`: `local-siglip2-p256-crop` gave all 6 steps and the true
   wine at rank 1 (0.8446); the backend build took 19.5 s (the local model loads in each
   process). `barcode-local-siglip2-p256-crop` answered by the code lookup in 107 ms; the
   build took 25.7 s. No gx10 embedding pipeline was tried: its model
   `siglip2-so400m-patch16-512` was not loaded, and the enrichment run used the gateway.
6. Browser checks: 41 on `/recognize` (light 1280 px, dark 390 px), RN27 and NT5 on
   `/runs`, `/testset` with the new nav, and 22 checks of the script of b4. No page error.
   The full suite: 949 tests, 1 failure of another session (`test_barcode.py` counts the
   pipelines of the uncommitted `config.yaml`).
