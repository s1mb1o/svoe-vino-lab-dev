# 65 — The button `Build all clusters` of the Clusters page

Date: 2026-09-27.
Source: owner message of 2026-09-27T21:44:04+0300 (`add "Build all clusters"` on
`/clusters`), and the owner answers of 22:05:44 ("Server queue"; "Yes, separate hunks")
and of 22:39:01 (separate hunks next to the uncommitted hunks of 4e).
Base: [30_embedding-clusters.md](30_embedding-clusters.md) and the queue of
[60_build-all-embeddings.md](60_build-all-embeddings.md).
Session: drink-atlas-workspace-1c [b72be3].

## Goal

A button `Build all clusters` on `/clusters` builds `clusters.json` of each embedding
entry of `config.yaml`. The builds run one at a time. A build of one entry is the build
of the button `Build clusters`: `clusters.build_to_directory`, with the thresholds of the
block `clusters` of `config.yaml`.

## Options that the owner did not choose

- Page loop: the page calls `POST /api/clusters/<name>/build` for each entry. No server
  change. A closed tab stops the loop.
- Chain after embeddings: the queue of plan 60 also builds the clusters of each entry.
  This needs `embedding_routes.py`, which holds uncommitted work of other sessions.

## The queue

1. The lab server holds one queue. A thread of the server runs it, so a closed tab does
   not stop it. A restart of the server ends the queue. An atomic write keeps
   `clusters.json` whole.
2. The queue holds each entry of `config.yaml` with no configuration error, in the order
   of `config.yaml`. This is the order of the combobox `Configuration`.
3. For each entry, the thread reads `config.yaml` again and calls
   `clusters.build_to_directory` in the thread. A build takes seconds; the thread does not
   start a process.
4. `clusters.Busy` (the embedding build of the entry runs, or another cluster build of the
   entry runs) makes the thread wait 1 s and try again. The key `waiting` of the queue
   holds the reason.
5. `clusters.ClusterError`, for example an entry with no index or no vector file, gives
   the result `skipped` with the error. `OSError` or `ValueError` gives `failed`. The next
   entry starts in both cases.
6. A new read of `config.yaml` that fails ends the queue with the state `failed`.
7. The queue has no stop. The server keeps the last queue after its end, until the next
   `Build all clusters`.
8. A cluster rebuild does not rebuild the label rules of plan 45.

## The routes

1. `POST /api/clusters/build-all` starts the queue. Answer HTTP 202 with
   `{"queue": <queue>}`. HTTP 409 when a queue runs. HTTP 400 when each entry of
   `config.yaml` has a configuration error.
2. Only `POST` goes to the queue. A `GET` of `/api/clusters/build-all` stays the detail of
   an entry with the name `build-all`, as in plan 60.
3. `GET /api/clusters` adds the key `queue`: null, or
   `{state, names, index, current, waiting, results, started_t, ended_t, message}`.
   - `state`: `running`, `done`, or `failed`.
   - `results`: one `{name, state, counts, message}` for each entry that ended. `state` is
     `done`, `skipped`, or `failed`. `counts` holds the counts of each space for `done`.
   - The route took 0.12 to 0.16 s on 2026-09-27 with 12 entries, so the page polls it.

## The page

1. The button `Build all clusters` follows `Build clusters`. Its title is `Build the
   clusters of each configuration, one at a time, in the order of config.yaml`. A span
   `#queue` after it shows the queue. The span is not `#message`, because each load of
   the detail clears `#message`.
2. `Build all clusters` is disabled while a queue runs.
3. The text of `#queue`:
   - while the queue runs: `Build all clusters <index + 1> / <count>: <name>`, and
     ` · waiting: <reason>` while the entry is busy;
   - after its end: `Build all clusters done: <n> built`, with ` · skipped <n>` and
     ` · failed <n>` when they are above zero; or `Build all clusters failed: <message>`.
   - A failed entry or a failed queue shows the text in the error colour.
   - The title lists each result as `<name>: <state>`, with ` — <message>`.
4. The page polls `/api/clusters` every 2 s while the queue runs, and fills the combobox
   again, so each built entry shows its new count. At the end the page loads the detail
   of the selected entry again.
5. A load of the page while a queue runs shows the queue and starts the poll.

## Tests

`tests/test_cluster_routes.py`, class `BuildAllTest`:

1. Two entries and one entry with a configuration error: the queue holds the two, in the
   order of `config.yaml`; the first is `done`, the second (no index) is `skipped`.
2. A second `POST` while the queue runs: HTTP 409. A `POST` after the end: HTTP 202.
3. A busy entry is tried again until its build runs.
4. A failed entry does not stop the queue.
5. A `GET` of `/api/clusters/build-all` is not the queue.

Browser check of the live page with the `POST` mocked and each other write blocked: the
light and dark themes, 1,440 px and 390 px. The new controls do not change the width of
the page or the row of the navigation.
