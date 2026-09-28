# Plan 35: more than one VLM request at the same time

Date: 2026-09-26. Session: drink-atlas-workspace-d3 [4920ce].
Status: approved by the owner on 2026-09-25T23:58:53+0300.

Source: owner message of 2026-09-25T23:44:31+0300 and the answers of 23:58:53. The text
is in [../owner-messages.md](../owner-messages.md). The message came with a screenshot of
the VLM indicator of `/dataset`: `VLM details 292 / 2,017 · 20.0 s · 1 details failed`.

## 1. Goal

1. The watcher `pipeline/describe_images.py` sends up to `workers` requests at the same
   time. Plans 26 and 29 sent one request at a time.
2. `image_description.workers` of `config.yaml` sets the number. The owner chose 8.

## 2. Decisions of the owner

| Question | Options | Answer |
|---|---|---|
| How does the watcher send the requests? | a rolling pool of threads in the one watcher; batches of N; N watcher processes with a claim in the database | the rolling pool |
| Where is the number? | `image_description.workers`; `image_description.requests`; a key of the `vlm` entry | `image_description.workers` |
| Which number? | 4, then a check of the live rate; a probe first; 8 | 8 |
| What does the speed of the pill show? | the wall time per image; the time of one request; both | the wall time per image |

Reasons for the recommended options:

- A detail request takes 7 s to 80 s. A batch waits for its slowest request, so the other
  workers of the batch wait with no work. A rolling pool starts the next image when one
  request ends.
- N watcher processes need a claim column (a schema change), a state file for each
  watcher, and a merge of the state files for the pill.
- `workers` is the term of `config.yaml` (`vino-svoe-search-by-photo`) and of
  `backends.yaml` for the number of requests at the same time. One term names one
  concept.
- The wall time per image is the rate of the backlog. With 1 worker it equals the old
  value. The time of one request rises with more workers, so the pill would look slower
  while the backlog goes faster.

## 3. The pool

- `run` holds a `concurrent.futures.ThreadPoolExecutor` with `workers` threads. A thread
  makes one call: `describe_one` (stage 1) or `detail_one` (stage 2), with the same
  writes as before.
- The main thread alone takes the images: `next_items(db_path, cfg, count, busy)`. It
  leaves out each image that a call holds. So two calls never send the same image.
- The images that wait for a class come first. When fewer wait than there are free
  workers and `details` is true, the images that wait for a detail fill the rest. The
  newest link comes first, as before.
- The main thread wakes when a call ends, and at least once each second. It checks the
  parent process, collects the results, and fills the free workers.
- The main thread alone writes the state file. `working` names the newest call that runs.
- `log` holds a lock, so that the lines of two threads do not mix.
- The default of `workers` is 1. A configuration with no key works as before.

## 4. Failures

- A failure of the service (HTTP 429 or 5xx, no connection, a timeout) is not counted, as
  in plan 26. No new call starts for the backoff time: 30 s, doubled up to 600 s. A
  success sets the backoff back to 30 s.
- The calls that run finish, and their results are stored.
- A failure during a running backoff does not double the backoff again. Without this
  rule, 8 calls that fail at the same time would give the maximum backoff at once.
- The state is `waiting` during the backoff, with the error.
- Without `watch` (`--once`), the first failure of the service is raised after the calls
  that run ended.
- A database error of a call (`WaitError`, `sqlite3.Error`) stops the new calls for
  `poll_seconds`. A call that got a valid answer stored it in `data/cache/` first, so the
  next attempt reads the cache and sends no request.

## 5. The speed

- `Status.step(sha256, described, seconds, wall)`: `seconds` is the time of the call of
  the image (`last.seconds`); `wall` is the wall time since the end of the image before
  it. When the pool was empty, `wall` counts from the start of the call. So an idle time
  does not enter the speed.
- `seconds_per_image` is the mean `wall` of the last 20 images. With 1 worker it is the
  time of the call, as before.
- `pipeline/pages/dataset.html` does not change. The tooltip line `Speed: ... s per image
  (last 20)` stays true.

## 6. Deployment

- The lab server calls `describe_images.settings` for the route
  `GET /api/image-description-reply`. The server that runs has the old code, which
  refuses the unknown key `workers`. So the key enters `config.yaml` in the same minute
  as the restart of 8168 (rules 22 to 24 of `AGENTS.md`). A restart of the watcher alone
  is not enough.
- The restart also deploys the uncommitted code of the other sessions. Before the
  restart, this session sends a message to each active session with uncommitted hunks
  in the files of the server.
- After the restart: `caffeinate -ims -w <watcher pid>`, and the watcher row of
  `/Users/ashmelev/Admin/GPU_TASKS.md`.
- The live check: the log line `start: ... workers 8`, the rate on the pill against the
  serial rate, and the time of each call against `TIMEOUT_SECONDS` (300 s).

## 7. Risks

- 8 calls share the GPU of gx10, so each call is slower. At 21.8 tokens/s alone, the
  longest normal detail answer (1,678 tokens) takes about 77 s (the ResearchLog entry of
  drink-atlas-workspace-15 [40dc83]). If each call becomes more than about 4 times slower,
  good answers also reach the timeout of 300 s. A timeout is not counted, and it starts a
  backoff. The live check measures this. The remedy is a lower `workers`.
- A call that loops until the timeout holds one worker, and the image stays at the head
  of the queue. Before this plan such an image blocked the whole queue; now it blocks one
  worker of 8, plus a stop of the new calls for 30 s after each timeout. The fix of the
  loop is the proposal of drink-atlas-workspace-15 to the owner (a timeout tied to
  `max_tokens`, a counted timeout, or a loop guard). This plan does not choose one.
- The gateway 18081 is llama-swap. A request for another model can make it unload the
  VLM. Then 8 calls fail at the same time, and the rule of section 4 gives one backoff.
- Ctrl+C in a manual `--once` run waits for the calls that run, up to 300 s.

## 8. Tests

New tests at the end of `tests/test_describe_images.py`:

- `WorkersSettingsTest`: the default 1; 0, -1, `"8"`, `true`, 2.5, and null are refused;
  the project configuration has 8.
- `WorkersTest`: two calls run at the same time (a barrier); an image is in one call at a
  time, and no more than `workers` calls run (3 images, 2 workers, 9 failed answers); the
  calls that run end before a failure is raised; two calls that fail together give one
  backoff of 30 s; the speed is the mean wall time; two workers give about half the time
  of a call.
- A check on a scratch copy: each of four faults makes a test fail. The faults: no
  exclusion of the images that calls hold; each failure doubles the backoff; no wait for
  the calls that run; the speed is the time of the call.

## 9. Files

- `pipeline/describe_images.py`: the docstring, the imports, `DEFAULTS`, `settings`,
  `log`, `Status`, `next_items`, `run_item`, `run`, the `start:` line of `main`.
- `config.yaml`: `workers: 8` and the comment of `image_description`.
- `tests/test_describe_images.py`: the imports and the new tests.
- Docs: `README.md`, `COMMANDS.md`, `SMOKE_TESTS.md`, `ChangeLog.md`, `ResearchLog.md`,
  one note line in plan 26 and plan 29.

## 10. Result on 2026-09-26

- The key `workers: 8` entered `config.yaml` at 00:36:22. 8168 was restarted at 00:36:23
  with SIGTERM (old server pid 50020; new server pid 36577, `/opt/homebrew/bin/python3`).
  Sessions 6a [792d65], e2 [9e7fe4], 39 [fb59ad], and ab [539687] agreed that their
  uncommitted server code went live with the restart.
- The watcher pid 36603 logged `start: watch, vlm qwen3.5-9b-nvfp4 (qwen3.5-9b-nvfp4),
  workers 8, details on`. `caffeinate -ims -w 36603` is pid 36646. The plan 29 row of
  `GPU_TASKS.md` names both.
- `GET /api/dataset`, `GET /api/testset?set=official-real-photos`,
  `GET /api/image-description-status`, and `GET /api/image-description-reply` answered
  HTTP 200 after the restart. The full suite: 692 tests `OK`.
- The pill of `/dataset` (headless Chrome, dark theme) read `VLM details 494 / 2,018 · 2.1 s
  · 2 details failed`. Before the change the owner saw `VLM details 292 / 2,017 · 20.0 s`.
- The rate rose from 3.4 to 26.5 details per minute (7.8 times). The call time stayed:
  mean 16.0 s, maximum 32.5 s in 157 calls; about 22 tokens/s per call. The numbers are
  in the entry of 2026-09-26 of `ResearchLog.md`.
- One timeout in the first 6 minutes (`ac892b17a4bf`). The rule of section 4 worked: no
  new call for 30 s, the running calls finished, and the next call of the image gave a
  valid answer. The timeout was a stuck request, as two timeouts of the serial watcher.
