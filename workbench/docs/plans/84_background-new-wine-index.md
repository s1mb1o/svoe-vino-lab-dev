# 84 — Index build of a new wine in the background

Date: 2026-09-29.
Status: implemented and verified. Approved by the owner at 2026-09-29T12:45:37+0300,
with a `Retry` button.

Source: the owner message of 2026-09-29T12:28:00+0300 and the owner answer of
2026-09-29T12:41:02+0300. The messages are in [owner-messages.md](../owner-messages.md).
The cause of the slow `Save` is in `ResearchLog.md`, entry "The slow `Save` of the
`Add wine` dialog is a cold start of SigLIP 2 @512".

This plan replaces items 4 to 7 of the section "Web interface" of
[plan 78](78_incremental-new-wine-index.md). The CLI of plan 78 does not change.

## Goal

1. `POST /api/wine` MUST answer when the wine is in the catalogue. It MUST NOT wait for
   the index build.
2. The server MUST start the index build and the index verification of plan 78 in the
   background.
3. The card of the new wine MUST show the tag `indexing…` until the result arrives.
4. The card MUST show the result: `indexed` or `not indexed`.
5. `not indexed` MUST show the error and a `Retry` button. `Retry` starts the background
   job again for that wine.

## Measured baseline

1. `Save` of `__vino-shardone-sovinon-blan-kyuve` took about 40 s.
2. The SAM3 call took 0.57 s. The gateway call `POST /v1/embeddings` took 37.3 s (a cold
   start of `siglip2-so400m-patch16-512`, `ttl: 1800`).
3. The expected `Save` time after this plan is the SAM3 time and the catalogue write,
   about 1 to 2 s.

## Workflow

`pipeline/new_wine_workflow.py`:

1. `create_wine` does the preflight and `manual_wines.add_wine`. It returns the create
   result and the selected embedding.
2. `update_index` runs `rebuild_on_run.build` and `verify`. It returns the index result
   of plan 78 (state `active` or `failed`).
3. `create` calls `create_wine` and then `update_index`. The CLI keeps `create`, so the
   CLI output does not change.

## Jobs

New module `pipeline/new_wine_jobs.py`:

1. One `IndexJobs` object belongs to the lab server process.
2. `start(slug, ...)` records the state `indexing` and starts one daemon thread. The
   thread calls `update_index` and records `active` or `failed`.
3. A job holds `name`, `state`, `error`, `started_at`, `finished_at`, and the index
   result of plan 78.
4. A second `start` for a slug with the state `indexing` starts no thread.
5. Two jobs of two wines do not build at the same time. `rebuild_on_run.build` waits for
   the lock of `build_embeddings.py`. So the second build starts after the first build.
6. The jobs stay in memory. A restart of 8168 removes them.
7. After a restart, a wine with an unfinished job has no tag. The `build_embeddings.py`
   process continues, because it has its own session. The key
   `rebuild_embeddings_on_run: true` also builds the missing items before the next run of
   the embedding.

## Server

`pipeline/lab_server.py`:

1. `add_wine` calls `create_wine` and `IndexJobs.start`. The answer holds
   `index: {name, state: "indexing"}`.
2. A preflight failure still creates no wine and answers the error code of plan 78.
3. New route `GET /api/wine-index?slug=<slug>`. The answer is the job of the slug:
   `{slug, name, state, error, ...}`. HTTP 404 means that this server process has no job
   for the slug.
4. New route `POST /api/wine-index` with the body `{slug}`. It starts a job for the slug
   and answers the job with the state `indexing`. HTTP 404 means that the catalogue has no
   Active wine with the slug. A job with the state `indexing` stays; the route answers
   that job. The preflight of plan 78 runs first; a preflight failure starts no job.
5. `GET /api/dataset` sends `new_wine_index`: a map from slug to `{state, error}` for
   each job of this server process. A reload of the page during a build keeps the tag.
6. The legacy test server with no `config_path` keeps the create-only behavior. It starts
   no job.

## Page

`pipeline/pages/dataset.html`:

1. The busy text of `Save` is `Creating…`.
2. The dialog closes when the answer arrives. The card appears with the tag `indexing…`.
3. The page reads `GET /api/wine-index` every 2 s for each card with the tag
   `indexing…`.
4. State `active`: the tag changes to `indexed`.
5. State `failed`: the tag changes to `not indexed`. Its `title` holds the error text.
   A `Retry` button stands next to the tag. `Retry` sends `POST /api/wine-index`, sets the
   tag to `indexing…`, and starts the reads again.
6. HTTP 404: the page removes the tag and stops the reads for that slug.
7. A network error: the page keeps the tag and reads again after 2 s.
8. A create warning (for example no processed file) still opens an `alert`. An index
   failure opens no `alert`. The card tag shows it.

## Tests

1. `create` gives the same result as `create_wine` followed by `update_index`. The
   present tests of `tests/test_new_wine_workflow.py` pass with no change of their
   assertions.
2. A job goes from `indexing` to `active` with a fake build.
3. A job goes from `indexing` to `failed` with a failed fake build. The error is in the
   job.
4. A second `start` for the same slug during `indexing` starts no second build.
5. `POST /api/wine` answers `indexing` while a fake build waits on an event.
   `GET /api/wine-index` answers `active` after the event.
6. `GET /api/wine-index` answers 404 for a slug with no job.
7. `POST /api/wine-index` starts a new job after a failed job. It answers 404 for an
   unknown slug.
8. `GET /api/dataset` sends `new_wine_index`.
9. `docs/lab-openapi.yaml` holds the new routes. `tests/test_lab_openapi.py` passes.
10. The inline script of `dataset.html` passes a syntax check.
11. A headless browser check on a scratch server with a fake build shows `indexing…` and
    then `indexed`, and `not indexed` with `Retry` for a failed build. `Retry` gives
    `indexing…` again.

## Live trial

1. A live trial on 8168 creates the wine `__web-bg-index-smoke-20260929`.
2. The trial measures the `Save` time and the time to the tag `indexed`.
3. The trial then sets the wine to `Disabled`, as plan 78 did.
4. The owner approved the trial at 2026-09-29T12:45:37+0300.

## Files

- `docs/plans/84_background-new-wine-index.md` (new)
- `pipeline/new_wine_jobs.py` (new)
- `tests/test_new_wine_jobs.py` (new)
- `pipeline/new_wine_workflow.py` (the split of `create`)
- `pipeline/lab_server.py` (`add_wine`, the two new routes, `new_wine_index`, the docstring)
- `pipeline/pages/dataset.html` (`saveWine`, the busy text, the card tag, `Retry`, the reads)
- `tests/test_new_wine_workflow.py` (the route tests)
- `docs/lab-openapi.yaml` (the answer of `createWine`, the new routes)
- `docs/plans/78_incremental-new-wine-index.md` (one pointer to this plan)
- `README.md`, `SMOKE_TESTS.md` (AW17, AW19), `ChangeLog.md`

A restart of 8168 follows the tests.

## Decisions

The owner answers of 2026-09-29T12:45:37+0300:

1. A failed card gets a `Retry` button. It replaces the link to `/embedding`.
2. This plan adds separate hunks to the files of the section `/root`. The lines of
   `/root` stay byte-identical.
3. The live trial runs.

## Result

1. `POST /api/wine` answers after the catalogue write. `pipeline/new_wine_jobs.py` runs
   `update_index` in a daemon thread.
2. Tests: `test_new_wine_jobs.py` 10, `test_new_wine_workflow.py` 8,
   `test_manual_wines.py` 17, `test_lab_openapi.py` 11, `test_lab_server.py` 69,
   `test_lab_pages.py` 4. All pass. The page script passes `node --check`.
3. Headless Chromium on a scratch server with a fake build passed 18 of 18 checks in the
   light and the dark theme.
4. Port 8168 restarted at 12:59 on PID 24435.
5. The live trial created `__web-bg-index-smoke-20260929` at 13:00. The gateway model was
   warm. The POST answered in 0.74 s. The card showed `indexing…` at 0.90 s and `indexed`
   at 2.84 s. The job built 2 items and activated `vectors-71603780.npy`. No page error.
6. The trial wine is `Disabled`. The next build prunes its items.
