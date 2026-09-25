# Plan 39: the checkbox `Use caches` of the dialog `Run>`

Date: 2026-09-26. Session: drink-atlas-workspace-d3 [4920ce].
Status: approved by the owner on 2026-09-26T01:32:00+0300.

Source: owner message of 2026-09-26T01:20:30+0300 and the answers of 01:32:00. The text
is in [../owner-messages.md](../owner-messages.md). The message came with a screenshot of
the dialog `Run>` of `/testset`: `Run the set my`, three pipelines, `first N queries`,
`workers`, `Cancel`, and `Start`.

## 1. Goal

1. The dialog `Run>` of `/testset` gets a checkbox `Use caches`. It is on by default.
2. On: a model call that repeats an earlier call reads its answer from `data/cache/`
   (`pipeline/model_cache.py`, [plan 25](25_model-call-cache.md)). This is the behaviour
   before the change.
3. Off: the job reads no record of `data/cache/`. Each model call goes to its service,
   so the latency of the run is real time. The owner wrote "we need real time".

## 2. The facts before the change

- `model_cache` holds the answers of SAM3, GDINO, and the VLMs. On 2026-09-26 at 01:30,
  `data/cache/` held `sam3/` (42 MB), `qwen3.5-9b-nvfp4/` (17 MB), and
  `grounding-dino-base/` (8 KB).
- None of the three pipelines of `config.yaml` calls a VLM or an LLM.
  `siglip2-p256-crop` calls SAM3 through `derive.Sam3Client`, and that client reads
  `model_cache`. `siglip2-p256-as-is` sends no SAM3 request. `vino-svoe-search-by-photo`
  sends the photo to the API of vino-svoe.ru.
- The embedding request (`build_embeddings.OpenAIBackend`) and the request to the API of
  vino-svoe.ru have no cache in this project. They are real time in both modes.
- The latency of a photo of an embedding run (`EmbeddingBackend.ask`) includes the SAM3
  call. A cached SAM3 answer makes the latency shorter than the real-time latency.
- Not checked: whether the gx10 gateway or the SAM3 service keeps a cache of its own.

## 3. Decisions of the owner

| Question | Options | Answer |
|---|---|---|
| Which cached answers does the run skip when the box is off? | every record of `data/cache/` (SAM3, GDINO, VLM, LLM); the VLM and LLM records alone | every record |
| What happens to the fresh answers? | store them, as a normal cache miss does; leave the cache alone | store them |
| How do the runs show the state? | `run.json` and a tag `no cache` on `/runs`; `run.json` alone | `run.json` and a tag |
| Which approach does the code take? | one switch in `model_cache`; an environment variable; a switch in each client | one switch in `model_cache` |

Reasons for the recommended options:

- The owner wants real-time latency. A crop run that reads SAM3 from the cache does not
  give it. So the switch covers every record, not the VLM and LLM records alone.
- A skipped read is the least code. `store` does not change, and a real-time run keeps
  the cache up to date.
- The latency columns of `/runs` (`median ms`, `within SLA`) are real time only for a run
  with the box off. The tag shows this without a click on the run.
- One switch in `model_cache` covers each present and future client (SAM3, GDINO, VLM).
  A new step needs no code for the switch.

## 4. The design

1. `pipeline/model_cache.py` gets the module value `READ = True`. `lookup` answers None
   when `READ` is False. `store` does not change.
2. `pipeline/run_job.py` gets the flag `--no-cache`. The flag sets `model_cache.READ` to
   False before the backend is built. The event `start` holds `use_cache`. The call of
   `benchmark.run_benchmark` passes `use_cache`.
3. `POST /api/run-jobs` (`run_jobs.start`) takes the body key `use_cache`. A missing key
   or `null` means true. Another value that is not a boolean gives HTTP 400
   `use_cache MUST be true or false`. False adds `--no-cache` to the command.
4. `benchmark.run_benchmark` takes `use_cache=None`. `run.json` holds the key
   `use_cache` when the value is not None.
5. `run_files.run_head` gives `use_cache`: the boolean of `run.json`, else None.
6. `pipeline/pages/testset.html`: the checkbox `#run-cache` stands in the row of
   `first N queries` and `workers`. The markup checks it, so each page load starts with
   the box on. While the page is open, the box keeps its state, as the two number fields
   do. `startRun` sends `use_cache`.
7. `pipeline/pages/runs.html`: a run with `use_cache: false` has the tag `no cache` after
   its id, in the style of the tag `dry run`.

Limits:

- The command-line runners `remote_run.py` and `embedding_run.py` get no flag. The owner
  did not ask for it. Their runs have no key `use_cache`, as the runs before this change.
- The lab server does not change `READ`. The VLM watcher `describe_images.py` is a
  separate process and keeps its cache.

## 5. The order of the deploy

1. `model_cache.py`, `run_job.py`, and `benchmark.py`. The lab server starts `run_job.py`
   from the disk for each job, so the flag is live for the next job.
2. `run_jobs.py` and `run_files.py` are code of the lab server: a restart of 8168. A
   running job continues, because it runs in its own session, and `job.lock` and
   `job.log` hold its state.
3. `testset.html` after the restart. Before the restart, the old server ignores
   `use_cache`, and a job of an unchecked box would read the cache.
4. `runs.html` at any time. A run with no key gets no tag.

## 6. Tests

- `tests/test_model_cache.py`: with `READ` off, a stored record is a miss, and `store`
  still writes the record.
- `tests/test_run_files.py`: `run_head` gives `use_cache`.
- `tests/test_benchmark.py`: `run.json` holds `use_cache` only when the value is given.
- `tests/test_run_jobs.py`: a start with a `use_cache` that is not a boolean is HTTP 400;
  `--no-cache` goes into the event `start`, into `run.json`, and into `model_cache.READ`;
  a start with `use_cache: false` puts `--no-cache` into the command.
- `SMOKE_TESTS.md`: the section "The checkbox `Use caches`", rows UC1 to UC6.

## 7. Result (2026-09-26)

- Done on 2026-09-26 by session drink-atlas-workspace-d3 [4920ce]. 6a, e2, ab, 39, cb,
  and 43 agreed to the hunks in their files. Session 28 was no longer in the `ListAgents`
  answer, and d1 is another conversation. The dialog hunks of `testset.html` do not touch
  the lines of the section of 28. The owner asked for the change of this dialog.
- The full suite gave 724 tests `OK` before the restart. 8168 was restarted at 01:46:24
  (server pid 59921; watcher pid 59935 with `caffeinate` pid 60808).
- A browser check on 8168 passed 24 of 24 checks, in the light and the dark theme. The
  check answered the POST of `/api/run-jobs` itself, so no job started. The checkbox is
  checked at each page load. It sends `use_cache: false` or `true`. The tag `no cache`
  shows for a run with `use_cache: false`.
- A live check on gx10 used `siglip2-p256-crop` on the first 3 queries of `my`. With the
  box off (`2026-09-25T225101Z-lab-siglip2-p256-crop-my`), the 3 photos sent 3 SAM3
  requests, 3 records of `data/cache/sam3/` were written again, and the median latency
  was 1,300 ms. With the box on (`2026-09-25T225128Z-lab-siglip2-p256-crop-my`), the job
  sent no SAM3 request, and the median latency was 116 ms.
- Finding: a cached SAM3 answer hides about 1.2 s per photo. In the full run
  `2026-09-25T220729Z-lab-siglip2-p256-crop-my` (made before this change, with the
  cache), 406 of 2,209 queries (18 %) took less than 400 ms. The as-is run of the same set
  has a median of 137 ms. So these 406 queries very likely read SAM3 from the cache. The
  median of that run (1,302 ms) is near the real time, but its fast tail is not.
