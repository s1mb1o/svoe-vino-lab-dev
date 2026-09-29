# Plan 88: Jobs of both kinds on /embedding and /testset

Date: 2026-09-29

Status: implemented, tested, and live. 8168 restarted on 2026-09-29 at 19:50.

Source: owner messages of 2026-09-29T19:11:00+0300 to 19:22:00+0300. The owner selected
option A at 19:35:06+0300.

## Problem

1. `/testset` shows the run jobs alone. `/embedding` shows the embedding builds alone.
2. A run job of a pipeline with an embedding waits in `rebuild_on_run.wait_for_build`
   while a build of that embedding runs. This wait comes before the event `start`.
3. During the wait, the job row on `/testset` shows `starting`. The server sets this
   text in `run_jobs.job`. The reason of the wait is a `log` event in `job.log`, but the
   API does not return it.
4. `wait_for_build` writes one `log` line, for the first build PID alone. When another
   build takes the lock, the line names a PID that ended.
5. After a restart of 8168, a job with a live runner PID and no event `start` has the
   state null. No page shows this job.

The observed case of 2026-09-29: the run `barcode-rerank-siglip2-512-rot5-seg` on
`official-real-photos` waited 33 min for the build of
`gx10-siglip2-so400m-patch16-512-rot5`. A Codex session started that build outside the
server. The owner stopped the build on `/embedding`. The `Build All` queue started a new
build of the same entry 4 s later (`_run_queue` waits for a build that runs, then starts
its own). The job row showed `starting` for the whole time.

## Changes

### Server

1. `pipeline/rebuild_on_run.py`, `wait_for_build`: write a `log` line each time the
   build PID changes. The text keeps the present form: `a build of <name> runs: PID <pid>;
   the run waits for its end`.
2. `pipeline/run_jobs.py`, `job_state`: a job with a live runner PID, no event `start`
   and no final event gets the state `running`. Its `message` is the message of the last
   `log` event, or `starting` when the log holds no `log` event. `todo` stays null.
3. The state stays `running`. This plan adds no new state `waiting`. Reason: the tuple
   `ACTIVE` decides the HTTP 409 of `start`, the rows of both pages, and the Selftest
   line. The Codex script `work/fixed512-rot5/finish_trial.py` also checks `running` and
   `stopping`. A new state needs a change in each of these places.

### Page `/testset`

4. `pollRunJobs` also reads `GET /api/embedding-jobs`.
5. The panel `#jobs` shows one row for each build in the state `running` or `stopping`,
   after the run rows.
6. The name cell of a build row is `build · <embedding>`.
7. The count cell is `done / todo`, with the phase text of `/embedding` (a model request
   of 3 s or more, or a retry).
8. When the `Build All` queue runs and its `current` is this build, the count cell adds
   ` · Build All <index + 1> / <count>`.
9. The last cell is the link `open` to `/embedding?name=<embedding>`.
10. The × of a build row sends `POST /api/embeddings/<name>/stop`.
11. A run row that waits shows the `message` of change 2 in its count cell. The present
    code does this already when `todo` is null.
12. The poll runs while the panel shows a run row or a build row.

### Page `/embedding`

13. `pollJobs` also reads `GET /api/run-jobs`.
14. The panel `#jobs` shows one row for each run job in the state `running` or
    `stopping`, after the build rows. A job whose name starts with `selftest-` gets no
    row, because the Selftest line shows it.
15. The name cell of a run row is `run · <pipeline> · <set>`.
16. The count cell is `done / todo`, or the `message` while the job waits.
17. The last cell is the link `open` to `/testset?set=<set>`.
18. The × of a run row sends `POST /api/run-jobs/<name>/stop`.
19. The grid of `.job` gets one more column for the link. A build row has an empty cell
    there.
20. The poll runs while the panel shows a build row or a run row, or the queue runs.

## Tests

21. `tests/test_run_jobs.py`, class `JobStateTest`: a live runner with no event `start`
    is `running` with the last `log` message; with no `log` event, the message is
    `starting`.
22. `tests/test_rebuild_on_run.py`: a change of the build PID writes a second line.
23. Headless Chromium on 8168: `/testset` shows the build row of the running rot5 build.
24. Headless Chromium on a scratch server with a test jobs directory: `/embedding` shows a
    run row that waits, with its message.
25. The full test suite with system `python3 -m unittest discover`.

## Deployment

26. `run_jobs.py` is loaded by the server. The change needs a restart of 8168 (rules 22
    to 24 of `CLAUDE.md`).
27. `rebuild_on_run.py` and the pages are read from disk. They need no restart.
28. Before the restart, check the pending server files of other sessions. A restart
    loads them too.
29. A restart ends the `Build All` queue. The running build continues.
30. The Codex trial `work/fixed512-rot5/finish_trial.py` calls the API of 8168 after the
    rot5 build ends. A restart during these calls makes the trial fail. Restart 8168 only
    while `work/fixed512-rot5/trial.json` shows the phase `wait_for_index`, or after the
    phase `done`.

## Documents

31. `docs/API.md` (the `message` of a job that waits), `SMOKE_TESTS.md` (new entries),
    `ChangeLog.md`, and this plan.

## Not in this plan

32. The server does not name the starter of a build (the queue, the page, or a process
    outside the server).
33. The behavior of `_run_queue` after a stop of a build that the queue did not start
    stays as it is.
