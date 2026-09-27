# 60 — The button `Build All` of the Embeddings page

Date: 2026-09-27.
Source: owner message of 2026-09-27T14:33:25+0300 and the owner answers of about 14:40
("One at a time, server"; "Yes, separate hunks").
Base: [10_embeddings-page.md](10_embeddings-page.md).

## Goal

A button `Build All` on `/embedding` starts the build of each embedding entry of
`config.yaml`. The builds run one at a time. 11 of the 12 entries use the gx10 gateway.
Each SigLIP 2 model takes about 7 GB. A build with no change ends in a few seconds.

## The queue

1. The lab server holds one queue. A thread of the server runs it. The page does not run
   the queue, so a closed tab does not stop it.
2. The queue holds each entry of `config.yaml` with no configuration error, in the order
   of `config.yaml`. This is the order of the combobox `Configuration`.
3. For each entry, the thread calls `start` of `embedding_routes.py`, as the button
   `Build` does. Then it reads the job of the entry every second until the job is not
   `running` and not `stopping`.
4. A build of the entry that runs already (a `Build`, or a build of
   `rebuild_embeddings_on_run`) gives HTTP 409. The thread waits for its end. Then it
   starts its own build of the entry.
5. A build that ends as `failed` does not stop the queue. The next entry starts.
6. A build that ends as `stopped` stops the queue. `Stop` and the `×` of the job row stop
   the build, so they also stop the queue. The queue gets the state `stopped`.
7. An entry that `start` refuses (HTTP 400 or 404) gets the result `skipped` with the
   error. The next entry starts.
8. A new read of `config.yaml` that fails ends the queue with the state `failed`.
9. A restart of the lab server ends the queue. The build that runs goes on, because it is
   a separate process. The page shows it as a job row.
10. The server keeps the last queue after its end, until the next `Build All`.

## The routes

1. `POST /api/embeddings/build-all` starts the queue. Answer HTTP 202 with
   `{"queue": <queue>}`. HTTP 409 when a queue runs. HTTP 400 when `embedding_python` is
   not a file. HTTP 400 when each entry of `config.yaml` has a configuration error.
2. Only `POST` goes to the queue. A `GET` of `/api/embeddings/build-all` stays the entry
   view of an entry with the name `build-all`. So no entry name is reserved.
3. `GET /api/embedding-jobs` and `GET /api/embeddings` add the key `queue`: null, or
   `{state, names, index, current, results, started_t, ended_t, message}`.
   - `state`: `running`, `done`, `stopped`, or `failed`.
   - `index`: the 0-based position of `current` in `names`.
   - `results`: one `{name, state, built, failed, message}` for each entry that ended.
     `state` is `done`, `stopped`, `failed`, or `skipped`.

## The page

1. The button `Build All` follows the message of the last build of the selected entry.
   Its title is `Build each configuration, one at a time, in the order of config.yaml`.
2. `Build All` is disabled while a queue runs.
3. The message after `Build All`:
   - while the queue runs: `Build All <index + 1> / <count>`. The job row names the
     configuration that builds, so the message does not repeat it;
   - after its end: `Build All done: <n> builds`, with `failed <n>` and `skipped <n>` when
     they are above zero; `Build All stopped: <index + 1> / <count>`; or
     `Build All failed: <message>`.
   - The title of the message lists each result as `<name>: <state>`.
4. The button and the message make the first header row wider. Measured on 2026-09-27 with
   the present texts: the navigation stays in the first row from 1,590 px without the
   button, from 1,680 px with it, and from 1,760 px while a queue runs.
5. The page polls `/api/embedding-jobs` every 2 s while a build or a queue runs. Between
   two builds of the queue no build runs for up to 1 s, so the queue alone keeps the poll.

## Tests

1. A queue of two entries with a fast fake build: both entries end as `done`, in the
   order of `config.yaml`.
2. A second `POST` while the queue runs: HTTP 409.
3. A `Stop` of the first build: the queue ends as `stopped`, and the second entry does
   not start.
4. An entry with a configuration error is not in `names`.
