# Plan 32: the button `Run>` of the Testset page

Date: 2026-09-25. Session: drink-atlas-workspace-5c [cbb143].

Source: owner message of 2026-09-25T22:41:00+0300 and the answers of 22:46:00. The text
is in [../owner-messages.md](../owner-messages.md).

Changed by [plan 39](39_use-caches-checkbox.md) on 2026-09-26: the dialog has the
checkbox `Use caches`, on by default. Off, the job gets `--no-cache` and reads no record
of `data/cache/`.

## 1. Goal

1. `/testset` gets a button `Run>`. A click opens a dialog.
2. The dialog lists the configurations of `config.yaml`. The owner selects one, and MAY
   set `first N queries` and `workers`. `Start` starts a run of the set of the page.
3. The header of `/testset` shows the progress of each run, as `/embedding` shows the
   progress of a build.

## 2. Decisions of the owner (22:46:00)

1. The dialog lists every configuration. A configuration with a runner can start:
   `backend: svoe-vino-ru` (`remote_run.py`, plan 31) and `backend: mock`
   (`mock_run.py`, plan 23). Another configuration is disabled with the note
   `no runner yet`. An entry with a configuration error is disabled with its error. The
   runner of the embedding configurations is a later plan.
2. The dialog also asks `first N queries` (empty: all) and `workers` (empty: the value
   of the entry).
3. The progress is a job row under the header of `/testset`: the configuration and the
   set, the state, a bar, done / total, the errors, the elapsed time, and a stop button
   `(x)`. When the run ends, the row shows a link to the run on `/runs` for 60 s. A
   reload of the page finds a running job again.

## 3. The job files

1. A job has the directory `work/run-jobs/<configuration>/`. `work/` is not in git.
2. `job.lock` holds the PID of the runner. `job.log` holds the output of the runner: one
   JSON event on each line.
3. One configuration runs one job at a time. A second `Start` of the same configuration
   answers HTTP 409. Two configurations MAY run at the same time.
4. The events: `start` (`pid`, `set`, `todo`), `progress` (`done`, `todo`, `errors`),
   `run_dir` (`run_id`), `stopping`, and one final event: `done`, `stopped`, or `failed`
   (`message`, `run_id`). Each event holds `t` (Unix seconds) and `time`.
5. The state of a job comes from `job.lock` and `job.log`, as the state of a build
   (`embeddings.job_state`). So a restart of the lab server does not lose a running job.
   A runner that ended with no final event is `failed`.

## 4. The runner

1. A new script `pipeline/run_job.py --name <configuration> --set <set> [--limit N]
   [--workers N] [--config PATH]` runs one job. The lab server starts it in a new
   session, with its output in `job.log`.
2. The script builds the backend of the configuration: `remote_run.build_backend` or
   `mock_run.build_backend` (top-k 10, a random seed). It calls
   `benchmark.run_benchmark` with `configuration` = the name. So the run files are the
   files of a CLI run.
3. A wrapper of the backend counts the answers and writes a `progress` event after each
   answer. `benchmark.py` does not change.
4. SIGTERM stops the job. The runner stops as Ctrl+C stops `remote_run.py`: the requests
   that run finish, `run_benchmark` writes the files of the answered photos, and the
   final event is `stopped`.

## 5. The routes

A new module `pipeline/run_jobs.py` holds the job state and the routes. `lab_server.py`
sends each route of `run_jobs.handles` to `run_jobs.respond`.

- `GET /api/run-configurations?set=<set>`: each configuration with `runnable`,
  `reason`, `backend`, the default `workers`, and its job; the count of the queries of
  the set.
- `GET /api/run-jobs`: the job of each configuration that has a job directory.
- `POST /api/run-jobs` with the body `{"configuration", "set", "limit", "workers"}`:
  HTTP 202, or 400 (not runnable, a wrong value), 404 (no such configuration or set),
  409 (a job of the configuration runs).
- `POST /api/run-jobs/<configuration>/stop`: SIGTERM, HTTP 202, or 409 (no job runs).

## 6. The page

1. The button `Run>` stands after the selector of the set in the title.
2. The dialog: the title `Run the set <set>`, the count of the queries, one radio row
   for each configuration (name, backend, note), the fields `first N queries` and
   `workers`, the buttons `Start` and `Cancel`, and an error line. `Esc` closes it.
3. The job rows stand at the bottom of the sticky header. The page polls
   `GET /api/run-jobs` every 2 s while a job runs or ended less than 60 s ago.
4. The page supports the light and the dark theme through `theme.css`.

## 7. Risks

1. A run of `vino-svoe-search-by-photo` on the set `my` sends 2,209 requests to an
   external API. The dialog shows the count of the queries before `Start`.
2. On 2026-09-25 the median latency of the official API was 9.2 s at 4 workers on
   `official-real-photos`; on 2026-09-17 it was 2.4 s at 1 worker on `my`. A full run of
   `my` can take about 1 h at 4 workers. The cause is not known.

## 8. Checks

1. `python3 -m unittest discover -s tests` passes.
2. The live server after a restart of 8168: the dialog lists the configurations, `mock`
   on the set `official-real-photos` runs to its end, and the row links to the run.
3. A run of `vino-svoe-search-by-photo` with `first N queries` = 5 shows the progress,
   and `(x)` stops a run.
