# Plan 59: the key `rebuild_embeddings_on_run` of `config.yaml`

Date: 2026-09-27. Session: drink-atlas-workspace-c7 [09419d].
Status: approved by the owner on 2026-09-27T08:53:00+0300. Done, not committed.

Source: owner messages of 2026-09-27T08:40:19+0300 and 08:40:26, and the answers of
08:53:00. The text is in [../owner-messages.md](../owner-messages.md).

## 1. Goal

1. `config.yaml` gets the top-level key `rebuild_embeddings_on_run`. The owner set it to
   true.
2. True: before each run of a pipeline of the backend `embedding`, the run updates the
   index of the embedding that the key `embedding` of the pipeline names.
3. The reason: a run ranks the current items of the index alone
   ([plan 33](33_embedding-run.md)). A wine, a patch, a cut, or an alternative photo that
   came after the last build is not in the ranking until a person presses `Build` on
   `/embedding`. On 2026-09-27, the last builds of 8 of the 12 embeddings planned 4,183
   items. The last builds of the other 4 embeddings, about 15 minutes later, planned 4,186
   items. At about 09:05 (`GET /api/embeddings`), the catalogue gave 4,192 items, and each
   of the 12 indexes missed 6 to 9 of them.

## 2. Decisions of the owner

| Question | Options | Answer |
|---|---|---|
| How does a run update the embedding? | update the changed items; also build a missing index; a full rebuild for each run | update the changed items |
| Which runs do the update? | `Run>` and the CLI; `Run>` alone | `Run>` and the CLI |
| What does a fatal build error or a stopped build do? | the run fails; the run uses the old index | the run fails |
| May this session add hunks to the files of the stale sections? | yes, separate hunks; no | yes, separate hunks |

## 3. The design

1. The key `rebuild_embeddings_on_run` is true or false. A missing key or null is false.
   Another value stops the run with `rebuild_embeddings_on_run MUST be true or false`.
2. The new module `pipeline/rebuild_on_run.py` holds the function
   `before_run(pipeline, config_path, log)`. It does nothing when the key is false, or
   when the pipeline has no key `embedding` (the backend `svoe-vino-ru`).
3. An embedding with no index (no `index.json` or no vector file, the check of
   `embedding_run.index_ready`) gets no build. The run then fails as before with
   `no index: build it on /embedding`. The first build stays an action on `/embedding`.
   The dialog `Run>` refuses such a pipeline before the run, as before.
4. The build is `<python> pipeline/build_embeddings.py --config <config> --name
   <embedding>`, as the button `Build` of `/embedding` starts it
   (`embedding_routes.start`). `<python>` is `embedding_python`, else the interpreter of
   the run. The working directory is the project root, and the build runs in a session
   of its own. The run waits for the end of the build.
5. The build does each item that is stale, missing, or failed. An item whose
   `embedding_hash` did not change and whose prepared image exists stays as it is. The
   hash covers the source file, the view, the role of the file, the settings of the model
   and of the steps, and the cut. So the vectors are equal to the vectors of a full
   rebuild. A build with no change took 0.7 to 2.4 s on 2026-09-27. It tried the 3 items
   again that fail in each build. A build of 129 changed items took 38 to 119 s.
6. The output of the build goes to the end of `data/embeddings/<name>/build.log`, so
   `/embedding` shows the progress as for a build of the button. The button `Build`
   truncates the file at its start. The run appends to the file, because a truncation
   can destroy the log of a build that started in the same second.
   `embeddings.job_state` reads the events after the last event `start`, so the page
   shows the right state.
7. A build of the same embedding that runs already, for example from the button `Build`
   or from the run of another pipeline of the same embedding: the run waits for its end.
   It checks every 2 s. Then the run starts its own build, which then has little to do.
   Exit code 3 of the build (another build took the lock first) makes the run wait again
   and start again.
8. The end of the build:
   - `done`: the run continues. One line gives the counts. A failed item does not stop
     the run. The run uses the current items, as before.
   - `stopped`, for example from the button `Stop` of `/embedding`: the run fails with
     `the build of <name> stopped before its end; the run did not start`.
   - `error`, another exit code, or no final line: the run fails with
     `the build of <name> failed: <message>`.
9. `run_job.py`: the call comes after the check of the set (`query_total`) and before
   `build`, so an unknown set fails before a build. The lines of the build phase are
   events `log` before the event `start`. `run_jobs.job_state` ignores them, so the
   dialog `Run>` shows the job as `starting` while the build runs.
10. A stop of the run during the build (the button `Stop` of the run, SIGTERM; Ctrl+C of
    the CLI): the run sends SIGTERM to the build and waits for its end. The build stops
    after the present batch and keeps the finished items. Then the run ends `stopped`
    with `stopped before the first answer`.
11. `embedding_run.py`: the call comes after `find_pipeline` and before
    `build_pipeline_backend`. The lines go to stdout.
12. `run.json` gets no new key. Its key `embeddings` holds `built_at`, the time of the
    last checkpoint of the build, and the item counts. After an update, `stale` and
    `missing` are 0.

## 4. Limits

- The re-rank of [plan 48](48_cluster-rerank.md) reads `clusters.json` and
  `cluster-rules.json` of the embedding `rerank.rules`. The run does not build them
  again.
- `/recognize` ([plan 55](55_recognize-page.md)) and the scripts `scripts/benchmark_*.py`
  call `build_pipeline_backend` directly. They do not update the index.
- Each build writes a checkpoint, also when no item changed. So `updated_at` of
  `index.json`, and `built_at` of `run.json`, give the time of the last build before the
  run.
- `scripts/run_internal_profile_queue.py` (the profile queue of the session
  codex-profile-latency) compares the SHA-256 of `index.json` before and after each run
  (`index_identity` of `scripts/benchmark_bulk_cache.py`). The checkpoint of the build
  changes `updated_at`, so with the key true each completed run of that queue gets the
  state `invalid_completion`. For a queue run, set the key to false, or change one of the
  two scripts. The owner decides.
- The dialog `Run>` shows `starting` during the build. The progress of the build is on
  `/embedding`. When the lab server restarts during the build, the dialog shows no job
  until the event `start`. This gap existed before for the load of the index. The build
  makes it longer.

## 5. The order of the deployment

1. `pipeline/rebuild_on_run.py` comes first, because `run_job.py` and
   `embedding_run.py` import it.
2. Then the calls in `run_job.py` and `embedding_run.py`, then the key in `config.yaml`.
3. The lab server starts `run_job.py` from disk for each job and reads `config.yaml` for
   each request. So the change needs no restart of 8168. An old runner ignores the key,
   and a new runner with no key does no build.

## 6. Tests

`tests/test_rebuild_on_run.py`:

- the key: missing or null is false, a boolean is its value, another value is an error;
- no build when the key is false, for a pipeline with no embedding, and for an embedding
  with no index;
- a stand-in of the build script: the command holds the configuration and the name of
  the embedding; the output goes to the end of `build.log`; a failed item does not stop
  the run; an error, an exit with no final line, and a stopped build raise an error;
  exit code 3 makes the run wait and start again; a running build is waited for; an
  `embedding_python` that is not a file is an error;
- `run_job.py` with the real `build_embeddings.py` on the test database: the build runs
  before the event `start`, and the run ends `done`; with the key false there is no build;
- `run_job.py` with the stand-in: a failed build fails the job before the event `start`;
  SIGTERM during the build stops the build and the job; an unknown set fails before a
  build;
- `embedding_run.py`: the update comes before `build_pipeline_backend`, and a failed
  update stops the CLI with exit code 1.
