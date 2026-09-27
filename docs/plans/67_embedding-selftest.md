# Plan 67: the self-test of one embedding

Date: 2026-09-28. Session: drink-atlas-workspace-49 [549156].
Status: approved by the owner on 2026-09-28T00:07:00+0300. In work.

Source: owner messages of 2026-09-27T23:58:00+0300 and 2026-09-28T00:00:00+0300, and the
answers of 00:04:00. The text is in [../owner-messages.md](../owner-messages.md).

## 1. Goal

1. The self-test checks that each image of the dataset is in the index of one embedding.
   "In the index" means: the image, as a query, finds its own wine.
2. The owner selects one entry of the key `embeddings` of `config.yaml`.
3. Each image of an Active wine is one query: `main`, `main_patched`, `full_front`,
   `full_back`, `label_front`, and `label_back`.
4. Each query searches the `full` view of the index alone: the package space.
5. The output is a normal run on `/runs`. The truth of a query is the `wine_slug` of its
   image. The test set of the run is `dataset`.
6. The run has no barcode step.

## 2. Decisions of the owner

| Question | Options | Answer |
|---|---|---|
| Where does the query vector come from? | the real query path; the index vectors alone | the real query path |
| Where does the self-test start? | a button on `/embedding` and a script; a script alone | a button on `/embedding` and a script |
| What does a label close-up send into the package space? | the image as it is; the steps of the `full` view | the image as it is |
| Does the original `main` of a wine with `main_patched` enter? | both images; the card image alone | both images |

## 3. The queries

1. `selftest.build_queries(conn, db_path)` reads `wine_catalog`, `wine_image`, and
   `image`. It makes one row for each `wine_image` row of an Active wine whose
   `image_type` is a key of `embeddings.ROLES`.
2. The `main` of a wine with `main_patched` stays in the queries (owner answer). The index
   holds `main_patched` alone for such a wine, so this `main` checks the patch.
3. A file of two wines gives two rows, one for each wine. Each row has the truth of its
   own wine. So a shared file shows as a miss of one of the two wines. This is a finding
   of the self-test, not an error of the code.
4. A row holds the keys of `benchmark.build_queries`: `query_id`, `image_path`,
   `abs_path`, `image_sha256`, `slug`, `label`, and `truth`. The values:
   - `slug` is the `wine_slug`, and `truth` is `[wine_slug]`.
   - `label` is `positive`.
   - `image_path` is `<wine_slug>/<image_type>.<sha256>.<extension>`.
   - `image_type` is an extra key of the row.
5. The rows are in the order of `image_path`. The query ids follow this order.
6. The left-out counts: the images of the wines that are not Active, by state.

## 4. The query path

1. `selftest.SelfTestBackend` has `id`, `spec`, `top_k`, and `ask(path)`, as the backend
   of `benchmark.run_benchmark` needs.
2. It holds two `embedding_run.EmbeddingBackend` objects. Both use one `Catalogue`, one
   model, and one SAM3 client (`Sam3Once`).
   - A `full` image (`main`, `main_patched`, `full_front`, `full_back`) uses the view
     `{"full": <the steps of the view full of the entry>}`. This is the path of a test
     photo: the SAM3 package cut, then the steps.
   - A label close-up (`label_front`, `label_back`) uses the view `{"full": []}`: the
     image as it is, with no SAM3 request. This is the input of a catalogue close-up.
3. Both search the `full` vectors of the index alone. The view `label` of the index is
   not used.
4. `ask(path)` selects the object by the role of the file. A file that is a full image of
   one wine and a close-up of another wine is a full image, as in
   `embeddings.read_inputs`.
5. An entry with no view `full` gives `ConfigError`: "the embedding <name> has no view
   full".
6. With the key `rebuild_embeddings_on_run` true, the self-test first updates the index,
   as a run does (plan 59).
7. The default of `workers` is 4. The script option `--workers` changes it.

## 5. The run files

1. `benchmark.run_benchmark` gets the keyword `queries`: `(rows, left-out counts)`. When
   it is set, the runner uses these rows. It reads no test set and no variant group of
   the database. When it is None, nothing changes.
2. The run id: `<stamp>-lab-selftest-<embedding>-dataset`.
3. `run.json`:
   - `configuration`: `selftest-<embedding>`.
   - `options.set`: `dataset`.
   - `use_barcode`: false.
   - `backend`: the spec of `EmbeddingBackend` of the `full` view, with `kind:
     embedding`, and the key `selftest`: the steps of each role.
4. On `/runs`, the filter `Testset` gets the value `dataset`. The filter `Configuration`
   counts the run as "no pipeline", because `selftest-<embedding>` is not a pipeline. No
   change of `runs.html`.

## 6. The job and the button

1. `pipeline/run_job.py` gets the flag `--selftest`. With it, `--name` names an entry of
   `embeddings`, and `--set` is not allowed. The job directory is
   `work/run-jobs/selftest-<embedding>/`. The events stay the same.
2. `POST /api/run-jobs` (`run_jobs.start`) takes the body `{"selftest": "<embedding>",
   "limit", "workers", "use_cache"}`. It checks the entry, its index
   (`embedding_run.index_ready`), and `embedding_python`. It starts `run_job.py
   --selftest`. The body keys `configuration` and `set` are not allowed with `selftest`.
3. `GET /api/run-jobs` lists the job as `selftest-<embedding>`. `POST
   /api/run-jobs/selftest-<embedding>/stop` stops it.
4. `/embedding` gets the button `Selftest` after the button `Log`. It starts the
   self-test of the selected configuration. It is disabled when the configuration has no
   index, when its build runs, or when its self-test runs.
5. A line after the button shows the job: the state, `done / todo`, the errors, a stop
   button while it runs, and the link `open run` after its end. The page polls `GET
   /api/run-jobs` every 2 s while the job runs.
6. `/testset` shows the job in its job list while it runs, as it shows each job of `GET
   /api/run-jobs`.

## 7. Limits

1. The input popup of `/runs` (`/api/run-inputs`) makes the model input again from the
   key `views` of `run.json`. For a label close-up, it shows the input of the `full`
   steps, not the image as it is. The step popup (plan 41) shows the real steps.
2. The button `New testset…` of `/runs` does not work for a self-test run, because no
   test set `dataset` exists. It shows its error.

## 8. Files

- `pipeline/selftest.py` (new): the queries, the backend, and the script.
- `pipeline/benchmark.py`: the keyword `queries` of `run_benchmark`.
- `pipeline/run_job.py`: the flag `--selftest`.
- `pipeline/run_jobs.py`: the body key `selftest` of `POST /api/run-jobs`.
- `pipeline/pages/embedding.html`: the button `Selftest` and its job line.
- `tests/test_selftest.py` (new), `tests/test_run_jobs.py`.
- `docs/API.md`, `README.md`, `ChangeLog.md`, `SMOKE_TESTS.md`, `COMMANDS.md`.
- A restart of 8168 for `run_jobs.py`. The page, `run_job.py`, and `selftest.py` are
  read from disk.

## 9. Tests

1. `build_queries`: each image type enters; `main` and `main_patched` of one wine both
   enter; a Removed wine stays out; the truth is the wine slug; a shared file gives one
   row for each wine.
2. `SelfTestBackend.ask`: a full image uses the steps of the view `full`; a close-up uses
   no step and sends no SAM3 request; both search the view `full` alone.
3. `run_benchmark` with `queries`: `options.set` is `dataset`, `configuration` is
   `selftest-<embedding>`, and `use_barcode` is false.
4. `run_jobs.start` with `selftest`: the command holds `--selftest --name <embedding>`;
   an unknown entry gives 404; an entry with no index gives 400; `selftest` with
   `configuration` gives 400.
5. A real self-test with `--limit 20` on one embedding, then a full run.
