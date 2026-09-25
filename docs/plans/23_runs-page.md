# Plan 23: the Runs page on the lab server, and the Mock configuration

Date: 2026-09-25. State: implemented and deployed on 2026-09-25 (8168 started at
13:14:31); the owner commits. Approved by the owner at 2026-09-25T12:52:00+0300.
Session: drink-atlas-workspace-85.

Source: owner messages of 2026-09-25T12:36:00+0300, 12:38:00, 12:41:00 (three answers),
12:43:00, and 12:52:00 (the answers to Q1 to Q3 and the approval). The text is in [../owner-messages.md](../owner-messages.md).

## 1. Goal

1. The lab server on port 8168 serves the page `/runs`. The page is on, not disabled.
2. The page reads the runs from the directory `runs/` of this project. The runs stay
   files. The lab database does not hold them.
3. The page is a full port of the Runs page of `scripts/review_server.py`: the table of
   the runs, the metric cards, the histograms, the photo rows with the filter, the sort,
   and the text search, the candidate images, the cluster frames, the VLM rule box, the
   large view with the arrow keys, and the model inputs.
4. The page has a filter `Configuration`. Its values are the lab configurations.
5. A lab configuration is one entry of the key `embeddings` of `config.yaml`. The
   `/embedding` page selects it. The owner calls it "Configuration", because an entry
   holds more than the embedding model: the endpoint, the options, and the steps of
   each view.
6. The `/embedding` page shows the label `Configuration` in place of `Embedding` in
   front of its selector. The route and the page name stay.
7. A configuration `mock` makes a run with random top-k candidates for each photo of a
   test set. The owner uses it to test the UI pipeline.

## 2. Facts

1. `runs/` holds 83 run directories. 78 of them hold `run.json`.
2. Each run records a match backend of `backends.yaml` in `options.backend`, for example
   `svm-siglip2-448`. No run records a lab configuration.
3. So, today, each lab configuration of the filter has zero runs. The first run with a
   configuration is a run of `mock`.
4. `data/lab.sqlite3` is at schema version 17. It holds the test sets `my` (4,043
   photos), `official-real-photos` (100), and `vlmrerank-8b-failed` (180).
5. `pipeline/benchmark.py` `run_benchmark` accepts any backend object with `id`, `spec`,
   `top_k`, and `ask(path)`. It writes the run files of `scripts/match_run.py`.
6. `pipeline/embeddings.py` accepts the backends `openai` and `local` alone. An entry
   with another backend makes the configuration file invalid for the `/embedding` page.

## 3. The configuration of a run

1. `run.json` gets a new top-level key `configuration`: the name of one lab
   configuration, as a string.
2. A run with no key `configuration` has no configuration. All 78 present runs are such
   runs.
3. The filter `Configuration` offers these values:
   - `every run` (the default): no filter.
   - one value for each lab configuration, in the order of `config.yaml`, with the
     count of its runs;
   - `no configuration`: the runs with no key `configuration`.
4. A run whose `configuration` names no present entry stays visible under `every run`.
   The filter shows such a name as a value too, with the mark `(not in config.yaml)`.
5. The table of the runs gets a column `configuration`.
6. The filter state goes into the page address (`?configuration=<name>`), so a reload
   keeps it. The run id stays in the hash, as in the old page.

## 4. The server code

1. A new module `pipeline/run_files.py` reads the run files. It holds the functions of
   `scripts/review_server.py` that read a run: `run_dirs`, `run_path`, `run_head`,
   `ROW_SORTS`, `twin_index`, `first_rank`, `add_twin`, `run_rows`, `run_result`, and
   `_row_matches`. Each function takes the directory of the runs as an argument, not as
   a global.
2. `scripts/review_server.py` does not change. It keeps its own copy of these
   functions. The old tool is not part of this task.
3. A new module `pipeline/run_routes.py` answers the routes of the page, as
   `pipeline/embedding_routes.py` does for `/embedding`. `lab_server.py` asks
   `run_routes.handles(route)` in `do_GET` and delegates.
4. The routes. Each one is GET and reads alone:
   - `/runs`: the page `pipeline/pages/runs.html`.
   - `/api/runs`: the head of each run (with `configuration`), and the list of the lab
     configurations of `config.yaml`.
   - `/api/run?id=&filter=&sort=&q=&offset=&limit=`: the metrics and the rows of one
     run, as in the old tool. Each row gets `photo_url`. The answer gets `bottles`
     (slug -> the URL of the catalogue image) and `patched` (the slugs with a patch)
     for the slugs of the rows.
   - `/api/run-clusters`: the clusters of `dataset/catalog-clusters.json` and the card
     names from `wine_catalog`, for the cluster frames and the VLM box.
   - `/api/run-inputs?id=&query=`: the model inputs of one row, with
     `scripts/run_model_inputs.py`, as in the old tool.
5. The images use the present route `/images/<folder>/<sha256>.<ext>` of the lab
   server. The page gets no new image route.
   - The photo of a row: the `image` row of its `image_sha256`. A photo whose bytes are
     not in the image store gets `photo_url: null`, and the page shows `not in the lab
     store`.
   - The catalogue image of a slug: the processed patch when the wine has a
     `main_patched` image, else the processed `main` image. This is the rule of
     `card_images` of `lab_server.py`.
6. The model inputs need the file of the photo. The route takes the store file of
   `image_sha256`. The old tool took the file in `svoe-vino-testset/dataset/my/photo`.
7. The link `cluster details` of a frame points to `/clusters#<slug>`. The Clusters page
   is disabled, so the link shows its notice. The link stays, so that it works when the
   Clusters page comes back.
8. `DISABLED_PAGES` of `lab_server.py` loses `/runs`. The start report no longer lists
   `Runs` as disabled.

## 5. The page

1. `pipeline/pages/runs.html` is the page `PAGE_RUNS` of `scripts/review_server.py` with
   `PATCH_CSS` and `PATCH_JS`, and these changes:
   - the lab navigation (`Dataset`, `Embeddings`, `Clusters`, `Testset`, `Runs`) and the
     mark `/* THEME_CSS */`;
   - the filter `Configuration` above the table of the runs, and the column
     `configuration`;
   - `row.photo_url` in place of `/img/photo` and `/img/runphoto`;
   - `bottles[slug]` in place of `/img/bottle`;
   - `patched` of `/api/run` in place of `/api/patched`;
   - `/api/run-clusters` in place of `/api/clusters`.
2. The page supports the light and the dark theme through `theme.css`, as the other lab
   pages.

## 6. The Mock configuration

1. A new script `pipeline/mock_run.py` makes one run of the configuration `mock`:

   ```text
   python3 pipeline/mock_run.py --set my [--top-k 10] [--seed N] [--limit N]
   ```

2. The script builds a mock backend object and calls `benchmark.run_benchmark`. So the
   run has the same files and the same metrics code as a real run.
3. The mock backend sends no request. For each photo it answers `top_k` candidates with
   random descending scores between 0 and 1.
4. The candidates are distinct slugs of `wine_catalog` with the state `Active`.
5. The answer of one photo depends on the seed and on the `image_sha256` of the photo
   alone. So a run with the same seed gives the same answers, and two rows of the same
   bytes get the same answer.
6. The true slug goes to a random place (Q2 = A). For each place slug of the photo (its
   positive or its negative slug), the rank is uniform over 1 to `top_k` or absent. The
   other places hold random slugs. So the page shows every state: correct at rank 1,
   rank 2 to 5, absent, false match, and a negative above a positive.
7. The mock backend reports a random latency between 50 ms and 4,000 ms, so the latency
   cards, the SLA share, and the latency sort show values. The script does not wait.
8. `run.json` records `configuration: "mock"`, the seed, and the top-k in `backend`.
9. `run_benchmark` gets one new optional argument `configuration`. It writes the key
   `configuration` into `run.json`. A call without it writes no key, as today.
10. The run id is `<stamp>-lab-mock-<set>`, by the present rule of `run_benchmark`.

## 7. Decisions of the owner (12:52:00)

- Q1 = A. The configuration `mock` is an entry of `config.yaml` `embeddings`:

  ```yaml
  - name: mock
    backend: mock
  ```

  `pipeline/embeddings.py` accepts the backend `mock`. Such an entry takes the keys
  `name` and `backend` alone. It has no model, no endpoint, and no view, so it has zero
  items. The `/embedding` selector shows it. `POST /api/embeddings/mock/build` answers
  HTTP 400, and `pipeline/build_embeddings.py --name mock` refuses it: a mock has no
  vectors. The entry stands last in the list, so the default entry of `/embedding`
  stays the same.
- Q2 = A: the true slug at a random rank or absent (section 6, item 6).
- Q3 = A: the command line alone. The Runs page shows the new run after a reload.

### Change of Q1 (2026-09-25T13:37:14+0300 and 13:41:00)

The owner saw the refusal of `Build` for `mock` and wrote: "mock should run as any other
config". The answer of 13:41:00 chose random vectors:

1. The entry `mock` has the views and the steps of the other entries
   (`views: *views_c_f`). It takes no `base_url`, `model`, or `extra_body`. Its model
   name is `embeddings.MOCK_MODEL` (`random-unit-vectors`).
2. `Build` prepares the images as for any entry. `build_embeddings.MockBackend` gives
   each prepared image a random unit vector of `MOCK_DIM` (256) values. It sends no
   request. The seed is the SHA-256 of the PNG bytes.
3. The refusals of `embedding_routes.start` and `build_embeddings.main` go away.
4. The random top-k run stays `pipeline/mock_run.py`. It does not read the vectors.

## 8. Files

- New: `docs/plans/23_runs-page.md`, `pipeline/run_files.py`, `pipeline/run_routes.py`,
  `pipeline/pages/runs.html`, `pipeline/mock_run.py`, `tests/test_run_files.py`,
  `tests/test_run_routes.py`, `tests/test_mock_run.py`.
- Hunks: `pipeline/lab_server.py` (the docstring, `import run_routes`, the delegation in
  `do_GET`, `DISABLED_PAGES`), `tests/test_lab_server.py` (the disabled-page tests of
  `/runs` and `/api/runs`), `pipeline/pages/embedding.html` (the label of `#emb`),
  `pipeline/benchmark.py` (the argument `configuration`), `tests/test_benchmark.py` (one
  test).
- For Q1 = A: `config.yaml` (the entry `mock` at the end of `embeddings`),
  `pipeline/embeddings.py` (`BACKENDS` and the mock branch of `Embedding.__init__`),
  `pipeline/embedding_routes.py` (`start` refuses the backend `mock`),
  `pipeline/build_embeddings.py` (`main` refuses the backend `mock`). Their tests go into
  the new `tests/test_mock_run.py`, so the test files of other sessions do not change.
- Docs: `README.md`, `COMMANDS.md`, `SMOKE_TESTS.md` (S8, S8a, S9, a new section RN),
  `ChangeLog.md`, `docs/plans/07_sqlite-lab-database.md` (rule 6),
  `docs/plans/10_embeddings-page.md` (the term).
- A restart of 8168 after the code is in place.

## 9. Coordination

1. `pipeline/lab_server.py`, `tests/test_lab_server.py`, and `pipeline/pages/embedding.html`
   hold uncommitted hunks of other sessions. This session adds small separate hunks on
   top, as the owner allowed the other sessions.
2. Before the first change, this session sends a message to:
   - ff: its delegation in `do_GET` stands in the same region.
   - TESTSET: it enables `/` and changes `DISABLED_PAGES` and the disabled-page test;
     it also lists `pipeline/benchmark.py` and `tests/test_benchmark.py`.
   - 7b and e3: `embedding.html`.
3. The owner commits.

## 10. Checks

1. `python3 -m unittest discover -s tests` passes, except the known loader errors.
2. `GET /runs` answers HTTP 200. `GET /api/runs` answers the 78 runs.
3. A mock run on the set `my` appears in the table, and the filter `mock` shows it alone.
4. The photo rows of the mock run show the photos and the candidate images.

## 11. Result (2026-09-25)

1. The full suite: 425 tests `OK`. New: `tests/test_run_files.py` (6),
   `tests/test_run_routes.py` (7), `tests/test_mock_run.py` (14), and one
   test in `tests/test_benchmark.py`.
2. The mock run `runs/2026-09-25T101320Z-lab-mock-my/` (seed 20260925) holds 2,209
   queries. Recall@1 is 0.085 and recall@5 is 0.456. The design expects 1/11 = 0.091 and
   5/11 = 0.455 for `top_k` 10.
3. The live server: `/runs` 200; `/api/runs` 84 runs (83 with no configuration, 1
   `mock`); the photos and the catalogue images of the rows answer 200; 255 clusters
   with a rule.
4. Headless Chromium, light and dark: no console error, no broken image, the filter and
   the page address work, the large view shows the note of a run with no model input.
5. The lab server was down from about 13:03:30, with no stop line in the log and no
   section that names a stop. This session started it at 13:14:31 (rules 22 and 23).
6. A defect of the old page stays in the port: the count label of the highest bar of a
   histogram overlaps the note line above the histogram.
