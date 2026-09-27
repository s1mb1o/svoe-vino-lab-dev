# Plan 53: the checkbox `Disable barcode fast path` of the dialog `Run>`

Date: 2026-09-26. Session: drink-atlas-workspace-b4 [aee81a].
Status: approved by the owner on 2026-09-26T19:47:40+0300. Done.

Source: owner message of 2026-09-26T19:43:40+0300 and the answers of 19:47:40. The text
is in [../owner-messages.md](../owner-messages.md).

## 1. Goal

1. The dialog `Run>` of `/testset` gets a checkbox `Disable barcode fast path`. It is off
   by default.
2. Off: a pipeline with the key `barcode` runs as before. The barcode step
   ([plan 42](42_barcode-step.md)) decodes the photo first, and a code of `wine_code`
   answers the photo.
3. On: the run skips the barcode step. The embedding answers each photo.

## 2. Decisions of the owner

| Question | Options | Answer |
|---|---|---|
| What does the checked box do? | skip the step (no decode, no lookup); decode, but ignore a hit | skip the step |
| How does a run show the state? | `run.json` and a tag on `/runs`; `run.json` alone; nothing extra | `run.json` and a tag |
| What does the box do for a pipeline with no key `barcode`? | disabled and greyed; always enabled, and the server ignores it | disabled and greyed |
| May this session add hunks to the files of the stale section f4? | yes, separate hunks; no | yes, separate hunks |

## 3. The design

1. `run_jobs.configurations_view` gives the key `barcode` for each pipeline: true when
   the pipeline has the key `barcode` (`run_jobs.has_barcode`).
2. `POST /api/run-jobs` (`run_jobs.start`) takes the body key `use_barcode`. A missing
   key or `null` means true. Another value that is not a boolean gives HTTP 400
   `use_barcode MUST be true or false`. False adds `--no-barcode` to the command of a
   pipeline with the key `barcode`. Another pipeline ignores the key.
3. `pipeline/run_job.py` gets the flag `--no-barcode`. For a pipeline with the key
   `barcode`, the flag sets `entry.barcode` to None before `build`. So
   `embedding_run.build_pipeline_backend` puts no `barcode.CodeFirst` around the backend.
   The run is the same as a run of the twin pipeline with no key `barcode`. The id of
   the backend stays the name of the pipeline.
4. `run_job.py` writes `use_barcode` into the event `start`: true or false for a pipeline
   with the key `barcode`, null for another pipeline. The call of
   `benchmark.run_benchmark` passes the same value.
5. `benchmark.run_benchmark` takes `use_barcode=None`. `run.json` holds the key
   `use_barcode` when the value is not None.
6. `run_files.run_head` gives `use_barcode`: the boolean of `run.json`, else None.
7. `pipeline/pages/testset.html`: the checkbox `#run-barcode` stands after `Use caches`.
   The markup leaves it unchecked and disabled. `runSyncFields` enables it when the
   chosen pipeline has `barcode: true`. A disabled box has a greyed label, and its title
   gives the reason. While the page is open, the box keeps its state. `startRun` sends
   `use_barcode` for a pipeline with `barcode: true` alone.
8. `pipeline/pages/runs.html`: a run with `use_barcode: false` has the tag `no barcode`
   after its id, in the style of the tag `no cache`.

## 4. The order of the deployment

Each change is compatible with the old code of the other files:

- An old server gives no key `barcode`, so the page keeps the box disabled.
- The page sends `use_barcode` alone; an old server ignores the key.
- `benchmark.py` received the keyword before `run_job.py` passed it.
- An old `run_files.py` gives no key `use_barcode`, so `/runs` shows no tag.

The lab server restarted at 19:50:15 (not by this session). The change of `run_jobs.py`
(19:49:19) and of `run_files.py` (19:49:33) was on disk before that restart, so the
running server serves both. `run_job.py`, `benchmark.py` (for the job), and the pages are
read from disk. No restart by this session.

## 5. Limits

- The command-line runner `embedding_run.py` gets no flag. The owner did not ask for it.
- The pipeline `vino-svoe-search-by-photo` has no barcode step in the lab. The API of
  vino-svoe.ru is not changed.

## 6. Tests

- `tests/test_run_jobs.py`, class `UseBarcodeTest`: the key `barcode` of each pipeline;
  `--no-barcode` for a pipeline with the key `barcode` alone; HTTP 400 for a value that
  is not a boolean; the runner with a fake embedding backend (`build` gets no barcode
  options, the event `start` and `run.json` hold `use_barcode`); a pipeline with no key
  `barcode` records nothing in `run.json`.
- `tests/test_run_files.py`: `run_head` gives `use_barcode` as a boolean alone.
- A browser check on the live 8168 (light and dark), with `POST /api/run-jobs`
  intercepted: 22 checks pass, no page error.
- A build of the real backend of `barcode-siglip2-p256-as-is` in `embedding_python`, with
  no request to a model: `CodeFirst` with the step, `EmbeddingBackend` with the step off.
