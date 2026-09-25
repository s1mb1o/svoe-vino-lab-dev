# Active work of the sessions

This file shows the present work of each agent session of this project. The rules are in
[AGENTS.md](AGENTS.md), section "Work of the sessions". In short:

- Read this file before you change a file.
- Keep one section for your session. Change your own section alone.
- Do not change a file that another section lists. Send that session a message.
- Remove your section when your work is committed.

The form of a section:

```text
## <session name>

- Task: <one line>
- Source: <a plan, or the time of an owner message>
- Files: <the paths or globs that this session changes>
- State: active | waiting: <reason>
- Updated: <local time in ISO 8601>
- Agreements: <the agreements with other sessions, if any>
```

## drink-atlas-workspace-5c [cbb143]

- Task: (1) done: a run of `vino-svoe-search-by-photo` on `official-real-photos`
  (owner choice of 22:36:00). (2) the button `Run>` of `/testset`: a dialog selects a
  configuration and starts a runner; the header shows the progress.
- Source: owner messages of 2026-09-25T22:30:47+0300 to 22:41:00, the answers of
  22:46:00; `docs/plans/32_testset-run-button.md`.
- Files: `docs/owner-messages.md` (append), new `docs/plans/32_testset-run-button.md`, new
  `pipeline/run_jobs.py`, new `pipeline/run_job.py`, new `tests/test_run_jobs.py`, hunks
  in `pipeline/lab_server.py` (the docstring, `import run_jobs`, `_run_jobs`, one branch in
  `do_GET` and in `_write_route`), `pipeline/pages/testset.html` (the button, the dialog,
  the job rows, their script and style). `work/run-jobs/`. Entries in `README.md`,
  `SMOKE_TESTS.md`, `ChangeLog.md`. A restart of 8168.
- State: active. The code, the tests (648 `OK`), and the docs are done. 8168 restarted
  at 22:56:54 (pid 14874). The live routes and a live job work. A browser check waits
  for the restart of 15 [40dc83].
- Updated: 2026-09-25T23:06:30+0300
- Agreements: a9 [79efd8] and 3b [d30290] add their own hunks in `ChangeLog.md`,
  `SMOKE_TESTS.md`, and `README.md` (answers of about 22:45 and 22:48). 15 [40dc83] adds
  separate hunks in `pipeline/lab_server.py` and restarts 8168 after its tests (messages
  of about 22:55 and 23:04). a7 [bbd3b6] asked for `caffeinate` on the new watcher and
  the new pids in `GPU_TASKS.md`: done at 22:57.

## drink-atlas-workspace-a9 [79efd8]

- Task: show the bottle cards of `/clusters` on 8168 in the form of the cards of `/clusters` on 8154.
- Source: owner message of 2026-09-25T22:37:15+0300; owner answers of 22:41:15 (layout only; an "Image" select for the space "combined").
- Files: `docs/owner-messages.md` (append), `pipeline/pages/clusters.html`, `ChangeLog.md` (one bullet at the top of 2026-09-25), `SMOKE_TESTS.md` (row LC3).
- State: done, not committed. The section stays until the commit (rule 20).
- Updated: 2026-09-25T22:56:28+0300
- Agreements: drink-atlas-workspace-5c [cbb143] agreed to the `ChangeLog.md` bullet and the `SMOKE_TESTS.md` LC3 row (answer after 22:44:53). 5c adds its own entries later as separate hunks. drink-atlas-workspace-15 asked to add its own hunks to `ChangeLog.md` (one bullet) and `SMOKE_TESTS.md` (S11 and new `/dataset` rows); a9 agreed at 22:56:28.

## drink-atlas-workspace-3b [d30290]

- Task: (1) the patch `Remove` button of `/dataset`: red, the label `Clear`, and the lab server clears the patch at once with no `Apply`. (2) the GTIN input of `/dataset` accepts at most 14 digits.
- Source: owner messages of 2026-09-25T22:46:27+0300 and 22:47:19.
- Files: `docs/owner-messages.md` (append), hunks in `pipeline/pages/dataset.html` (the patch button style, `patchEditor`, the `data-patch-remove` branch of the click handler, the comment in `stagePatchFile`, the `.gtin-input` element). The patch editor paragraphs and the GTIN paragraph of `README.md`, rows PE3, PE5, PE6, PE19 and one GTIN row of `SMOKE_TESTS.md`, one bullet in `ChangeLog.md`.
- State: done, not committed. The section stays until the commit (rule 20).
- Updated: 2026-09-25T22:57:00+0300
- Agreements: drink-atlas-workspace-5c [cbb143] agreed to the separate hunks in `README.md`, `SMOKE_TESTS.md`, and `ChangeLog.md` (answer after 22:47). This session agreed that drink-atlas-workspace-15 adds separate hunks to `pipeline/pages/dataset.html`, `README.md`, `SMOKE_TESTS.md`, and `ChangeLog.md` (VLM details failures modal, hidden Validate; request after 22:54).

## drink-atlas-workspace-cb [395cc7]

- Earlier name: drink-atlas-workspace-15 [40dc83] (the same conversation after a reload).

- Task: (1) a click on `N details failed` of the VLM indicator of `/dataset` opens a
  dialog with the failed details and the watcher log. (2) hide `Validate` of `/dataset`
  on the lab server (8168); the review tool (8154) keeps it. (3) a click on the
  thumbnail of the dialog shows the file in the image preview. (4) a setting
  `max_tokens` of the `vlm` entries, 8192 by default.
- Source: owner messages of 2026-09-25T22:49:56+0300 and 22:51:31; owner answers of
  22:54:00 (rows + log lines; hide on 8168 only; details only); owner message of
  23:20:22 (the preview) and 23:21:25 (`max_tokens`).
- Files: `docs/owner-messages.md` (append), `pipeline/image_details.py` (a new function
  `failed`), `pipeline/image_descriptions.py` (new functions `detail_failures`,
  `log_entries`), hunks in `pipeline/lab_server.py` (a new function
  `image_detail_failures`, one `do_GET` branch after `/api/image-description-status`, one
  docstring sentence), hunks in `pipeline/pages/dataset.html` (the VLM indicator, the new
  dialog `#detail-failures-modal`, its style and script, one Escape line; the `Validate`
  button, `validationOn`, two lines in `init`), `tests/test_image_details.py`,
  `tests/test_image_descriptions.py`, `tests/test_lab_server.py` (one test), separate hunks in `README.md`, `SMOKE_TESTS.md`,
  `ChangeLog.md`. A restart of 8168. For (4): `pipeline/vlm_config.py`, hunks in
  `pipeline/describe_images.py` (`DEFAULTS`, `settings`, `describe_detail`) and
  `config.yaml` (the `image_description` block), `tests/test_vlm_config.py`,
  `tests/test_describe_images.py`, one row of `data/lab.sqlite3` `image_detail`
  (`vlm_attempts` of `e049e469…`), a second restart of 8168. One entry at the top of
  `ResearchLog.md`.
- State: done, not committed. The section stays until the commit (rule 20). 8168 was
  restarted at 23:05:37 and 23:28:25; the failed detail row was reset at 23:29, timed out
  twice, and was set back to 3 attempts at about 23:35. A second looping row
  (`24e28aea6a4d`) was set to 3 attempts at 2026-09-26T00:20:23, reset to 0 at 00:41:25,
  and got a valid answer at 00:41:39.
- Updated: 2026-09-26T01:37:49+0300
- Agreements: 3b [d30290] agreed to the separate hunks in `dataset.html`, `README.md`,
  `SMOKE_TESTS.md`, `ChangeLog.md` (answer after 22:55). 5c [cbb143] asked for a separate
  `do_GET` hunk in `lab_server.py`; 5c restarts 8168 near 22:58; 15 tells 5c before its
  own restart.
  39 [fb59ad] agreed to add a separate bullet under the bullets of 15 in `ChangeLog.md`
  and one row in `SMOKE_TESTS.md` (answer after 23:27). ab [539687] agreed to the entry in
  `ResearchLog.md` and to the change of the own bullet in `ChangeLog.md` (answer after 23:42).
  15 agreed that d3 [4920ce] adds separate hunks in `pipeline/describe_images.py`
  (`run`, `Status`, `DEFAULTS`, `settings`), `config.yaml`, `tests/test_describe_images.py`,
  and if needed `pipeline/vlm_config.py` and `tests/test_vlm_config.py` (parallel requests,
  owner message of 23:44:31); d3 keeps the `max_tokens` hunks of 15.
  cb (earlier 15) agreed that 6a [792d65] adds separate hunks in `config.yaml`: the two
  entries leave the end of `embeddings:`, and a new section `pipeline:` comes after
  `embeddings:`, before the comment of `vlm:` (owner message of 23:37:48).
  cb agreed that d3 [4920ce] adds separate hunks in `README.md` (the watcher paragraph,
  the `image_description` row), `SMOKE_TESTS.md` (one row), `ChangeLog.md` (one bullet),
  and `ResearchLog.md` (one entry at the top); d3 keeps the hunks of cb.
  cb agreed that 43 [c33611] adds a heading `## 2026-09-26` with one bullet at the top of
  `ChangeLog.md` and row IW17 in `SMOKE_TESTS.md`.
  cb agreed that 39 [fb59ad] adds a block `clusters:` in `config.yaml` after `embeddings:`
  and before the comment of `pipeline:` (owner message of 2026-09-26T00:20:00).
  cb agreed that 39 [fb59ad] adds separate hunks in `pipeline/pages/dataset.html`: a block
  of localStorage functions for the header controls and call lines in `init` (owner
  message of 2026-09-26T00:30:00).
  cb agreed that d3 [4920ce] adds separate hunks for plan 39 in `README.md`,
  `SMOKE_TESTS.md` (a new section), and `ChangeLog.md` (one bullet in 2026-09-26).

## drink-atlas-workspace-39 [fb59ad]

- Earlier name: drink-atlas-workspace-43 [58637c] (the same conversation after a reload).

- Task: (1) done: safeguard A of the cluster build (limits of links and of the largest
  cluster). (2) the thresholds and the limits come from a new block `clusters:` of
  `config.yaml`; the page `/clusters` has no threshold input.
- Task (4): the key `min_cluster_size` of the block `clusters:` of `config.yaml`: the build
  stores no smaller cluster; the input "Minimum size" of `/clusters` goes away. Owner
  message of 2026-09-26T01:04:00+0300, answer of 01:05:00. Files: `pipeline/clusters.py`,
  `pipeline/pages/clusters.html`, my block of `config.yaml`, `tests/test_clusters.py`,
  `tests/test_build_clusters.py`, `tests/test_cluster_routes.py`,
  `docs/plans/30_embedding-clusters.md`. A restart of 8168. State: done. 29 cluster tests
  OK; 8168 restarted by 39 at 01:06:21 (pid 89346); a live build from the config gave
  `min_cluster_size: 2` in `settings` and the same clusters; 15 browser checks pass.
- Task (3): each header control of `/dataset`, `/embedding`, `/clusters`, `/testset`,
  `/runs` (selects, number inputs, search boxes) is stored in `localStorage` on change and
  restored at page load. A URL value wins; a stored value that is no longer a choice is
  ignored. Code in each page; no server change, no restart. Owner message of
  2026-09-26T00:30:00+0300, answers of 00:33:00. Files: separate hunks (the header
  state code, one start-up call) in `pipeline/pages/dataset.html`,
  `pipeline/pages/embedding.html`, `pipeline/pages/clusters.html`,
  `pipeline/pages/testset.html`, `pipeline/pages/runs.html`. Agreed (about 00:33 to
  00:35): 6a (embedding, runs, testset), 28 and e2 (testset; e2 keeps `svl.testset.sidebar`,
  `setSide`, `initSide`), ab (runs; keep `evenCards`), cb (dataset; keep its `init` lines).
- Source: owner messages of 2026-09-25T23:00:00+0300, 23:10:30, the answer "A", the answer
  "2" of 2026-09-26T00:06:30, "define limits in config" of 00:16:00, the answers of
  00:19:00 (one global block; limits and thresholds), and 00:20:00 (no thresholds in the UI).
- Files: `docs/owner-messages.md` (append), `pipeline/clusters.py`,
  `pipeline/build_clusters.py`, `pipeline/cluster_routes.py`, `pipeline/pages/clusters.html`
  (the threshold inputs, the build request, the summary; the owner asked for this UI
  change, the section a9 is stale), `tests/test_clusters.py`, `tests/test_cluster_routes.py`,
  `tests/test_build_clusters.py`, `docs/plans/30_embedding-clusters.md`. After agreement:
  `config.yaml` (a new block `clusters:` after the `embeddings:` list), the cluster
  paragraph of `COMMANDS.md`, one bullet in `ChangeLog.md`, one row in `SMOKE_TESTS.md`.
  A restart of 8168. Done: the rebuild of the clusters of
  `gx10-siglip2-so400m-patch16-naflex-p256` at 0.95 / 0.95 (00:07:14, 1.0 MB).
- State: done, not committed. The section stays until the commit (rule 20). Task 2 is
  live since the restart of 8168 by d3 at 00:36:23 (a build request with a threshold
  answers HTTP 400; the page has no threshold input). Task 3: the five pages pass a
  Playwright check (restore after reload, the URL wins, an unknown stored set gives the
  default set, no page error). An address with a view key restores no stored view
  control (a missing key is the default; proposal of 28, applied in `testset.html` and
  for the image of `clusters.html`); 14 checks pass. Open: the owner decides on the `ChangeLog.md` bullet and
  the `SMOKE_TESTS.md` rows (stale sections 5c, a9, 3b).
- Updated: 2026-09-26T01:37:40+0300
- Agreements: 15 [40dc83] (now drink-atlas-workspace-cb [395cc7]) agreed at about 23:28
  to one separate bullet under its bullet in `ChangeLog.md` and one new row in
  `SMOKE_TESTS.md`; its bullet and its rows S11 and DT9 to DT12 stay as they are. 15
  restarts 8168 near 23:29 for its own change. d3 [4920ce] adds its own separate bullet
  in `ChangeLog.md` and row in `SMOKE_TESTS.md`; 39 agreed (request after 23:44).
  drink-atlas-workspace-43 [c33611] (a new session, not the earlier name of 39) adds the
  heading `## 2026-09-26` with one bullet in `ChangeLog.md` and row IW17 in
  `SMOKE_TESTS.md`; 39 agreed (request after 00:00).
  ab [539687], 6a [792d65], d3 [4920ce], cb [395cc7] agreed (about 00:20 to 00:23) to the
  new block `clusters:` of `config.yaml` after the `embeddings:` list (6a, d3, cb) and to
  the cluster paragraph of `COMMANDS.md` (ab, 6a, d3). d3 restarts 8168 and deploys this
  code with it.
  28 [5ddfae] removes `, "#slugsel"` from the line `HEADER_IDS` of `testset.html` in the
  same edit as its removal of the select `Slugs` (owner message of 00:39:13); 39 agreed.
  28 [5ddfae] (plan 37, `#wine` becomes `#cluster`) reads the consts `HEADER` and
  `URL_VIEW` of the block of 39 in its own hunk of `load`; 39 does not rename them.
  d3 [4920ce] changes the label `every run` to `All` in `renderConfigs` of `runs.html`
  and the comment above it (owner answer of 01:19:00); 39 agreed.
  43 [c33611] changes the job rows of `embedding.html` (`.job`, `.job-stop`, `showJobs`;
  owner message of 01:24:00) and adds its own README.md, SMOKE_TESTS.md (EB41 to EB43),
  and ChangeLog.md hunks; 39 agreed.
  43 [c33611] changes the job rows of `testset.html` (`.job`, `.job-stop`, `showRunJobs`;
  owner message of 01:32:00) with its own README.md, SMOKE_TESTS.md, ChangeLog.md hunks;
  39 agreed.
  e2 [9e7fe4] adds plan 38 hunks to `runs.html` (candidate card, large view of the
  catalogue items; owner message of 01:23:11); 39 agreed.
  d3 [4920ce] adds plan 39 hunks ("Use caches": `#run-cache` in the Run dialog of
  `testset.html`, the tag `no cache` in `runs.html`; owner answers of 01:32:00); 39 agreed.

## drink-atlas-workspace-ab [539687]

- Task: plan 33, the runner of the embedding configurations of `config.yaml`: each photo
  of a test set gets the SAM3 cuts and the steps of the entry, the endpoint of the entry
  gives its vectors, and the vectors rank the catalogue vectors of
  `data/embeddings/<name>/`; the result is a run on `/runs`. A command alone (owner
  answer of 23:55:27 to session 6a).
- Source: owner message of 2026-09-25T23:19:28+0300 and the answers of 23:24:20 and
  23:35:19.
- Files: `docs/owner-messages.md` (append), new `docs/plans/33_embedding-run.md`, new
  `pipeline/embedding_run.py`, new `tests/test_embedding_run.py`, hunks in
  `pipeline/embeddings.py` (`apply_steps`), `pipeline/alternatives.py` (`label_cut_of`),
  `pipeline/run_routes.py` (`inputs_view` alone). Separate hunks in `README.md`,
  `SMOKE_TESTS.md` (section ER), `ChangeLog.md` (one bullet of 2026-09-26),
  `COMMANDS.md`, `ResearchLog.md` (entry of 2026-09-26), `docs/API.md`.
- New tasks of 2026-09-26: (1) an embedding run becomes a pipeline (owner answers
  of 00:12:24 and 00:15:17): one pipeline `gx10-siglip2-so400m-patch16-naflex-p256`,
  `backend: embedding`; 6a adds the kind to `pipelines.py`, this session adapts
  `embedding_run.py`. (2) /runs: the cards of one photo row get one height (owner
  message of 00:12:24).
- New files: `pipeline/embedding_run.py`, `tests/test_embedding_run.py`, plan 33
  (sections 1, 8, 9, 13); separate hunks in `pipeline/pages/runs.html` (the CSS rule
  after `.clgrp-link:hover` and the function `evenCards` before `loadRun`, agreed with
  6a); separate hunks in `README.md`, `SMOKE_TESTS.md` (ER1, ER6 to ER8, RN18),
  `ChangeLog.md` (two bullets of 2026-09-26), `COMMANDS.md`, `docs/API.md`.
- New task of 00:26:27: remove the pipeline `mock` from the source, the tests, and the
  docs (owner answer of 00:29:55: "Also free the 808 MB only"). Done: the delete of
  `data/embeddings/mock/` (808 MB) at about 00:31. The 2 mock runs in `runs/` stay.
  6a [792d65] removes `mock` from the source, the tests, and the docs (message of
  about 00:33; this session agreed, no handover). This session changed its own test
  (`tests/test_embedding_run.py`: a pipeline of the backend `svoe-vino-ru`).
- New task of about 00:55 (owner message of 00:45:33 and answers of 00:52:41, through
  6a): a pipeline of the backend `embedding` MAY hold `views`, the steps of the test
  photo. Files: hunks in `pipeline/embedding_run.py` (`query_inputs`, `EmbeddingBackend`,
  `build_backend`, `build_pipeline_backend`) and `tests/test_embedding_run.py`. 6a does
  `pipelines.py`, `config.yaml`, the docs, and the restart.
- State: finished at 01:47; waiting: e2 [9e7fe4] commits all pending changes (owner
  message of 01:43:59). This session does not commit, and removes this section after
  that commit (rule 20). Done, not committed. The key `views`: 24 tests `OK`; 6a added
  `siglip2-p256-as-is` and `siglip2-p256-crop` (with `white_background`, owner answer of
  00:57:59) and restarted 8168 at 01:01:42 (pid 81403); the dialog and the combo list 4
  pipelines, all runnable; the model inputs of both on 3 real photos are right (checked
  at 01:02 with the SAM3 cache alone). Earlier, also done: (1) `embedding_run.py --name` takes a pipeline name
  (`find_pipeline`, `build_pipeline_backend`); 6a's `run_job.build` calls it. (2) The
  card heights of `/runs` are live. d3 restarted 8168 at 00:36:23 (pid 36577): the
  dialog and the combo list the 2 pipelines alone, and `inputs_view` is live (checked
  at 00:37). 6a completed the removal of `mock`; the full suite gave 692 tests `OK`
  at 00:40. The section stays until the commit (rule 20).
- Updated: 2026-09-26T01:47:40+0300
- Agreements: the owner allowed separate hunks in `ChangeLog.md`, `README.md`,
  `SMOKE_TESTS.md` (answers of 23:24:20).
  15 [40dc83] (message from the session drink-atlas-workspace-cb, about 23:41) adds a
  separate new entry at the top of `ResearchLog.md` and changes its own bullet of
  `ChangeLog.md`; this session agreed.
  6a [792d65] (messages of about 23:44 and 00:00): this session removed its hunks from
  `pipeline/run_job.py` and `pipeline/run_jobs.py` and does not change them or
  `tests/test_run_jobs.py`. 6a keeps the hunks of this session in `pipeline/embeddings.py`
  and `pipeline/run_routes.py`, adds separate hunks to `tests/test_run_routes.py` and to
  the `mock_run.py` and `remote_run.py` paragraphs of `COMMANDS.md`, and includes the
  `inputs_view` hunk in its restart of 8168. This session changed its test of a wrong
  backend to an entry with a configuration error, which passes after the change of 6a.
  d3 [4920ce] (about 00:00) adds separate hunks to `README.md`, `SMOKE_TESTS.md`,
  `ChangeLog.md`, `COMMANDS.md`, `ResearchLog.md`; this session agreed. This session
  started `caffeinate -ims -w 50025` (pid 73010) for the VLM watcher, and asked d3 to
  hold the new watcher after its restart and to update the plan 29 row of
  `GPU_TASKS.md`.
  43 [c33611] (about 00:02) adds the heading `## 2026-09-26` of `ChangeLog.md` with its
  bullet and the row IW17 of `SMOKE_TESTS.md`; this session agreed and put its bullet
  under that heading.
  6a [792d65] (about 00:16 to 00:20): 6a writes the kind `embedding` of `pipelines.py`,
  the entry of `config.yaml`, `run_job.build`, and the rules of `run_jobs`; this session
  writes `embedding_run.py` against `Pipeline.embedding`; 6a allowed the two hunks of
  `runs.html`. 39 [fb59ad] (about 00:20) changes the clusters paragraph of `COMMANDS.md`;
  this session agreed.
  39 [fb59ad] (about 00:34) adds separate hunks to `pipeline/pages/runs.html` (the
  header values in localStorage; owner message of 00:30:00); this session agreed and
  asked 39 to keep the call `evenCards` of `loadRun` and to ask 6a too.
  d3 [4920ce] (about 01:21) changes the label `every run` of `renderConfigs` in
  `pipeline/pages/runs.html` to `All` (owner answer of 01:19:00); this session agreed and
  asked d3 to ask 6a too.
  6a [792d65] (about 01:25) told this session that the owner removed the pipeline
  `gx10-siglip2-so400m-patch16-naflex-p256` at about 01:07; this session changed its doc
  examples to `siglip2-p256-crop` (README, COMMANDS, ER rows, plan 33) at 01:28.
  e2 [9e7fe4] (about 01:35; plan 38, owner message of 01:23:11 and answers of 01:29:00)
  adds separate hunks to `pipeline/embedding_run.py` (`Catalogue`: the item key of each
  row, the key `items` of each candidate; a new function after `model_inputs`),
  `tests/test_embedding_run.py` (new tests, and `items` in the three key-set checks),
  `pipeline/run_routes.py` (a new route; not `inputs_view`), and `docs/API.md`; this
  session agreed.
  d3 [4920ce] (about 01:38; plan 39, owner answers of 01:32:00) adds a CSS line after
  `.tag.dry` and a tag `no cache` in `renderRuns` of `pipeline/pages/runs.html`; this
  session agreed, and asked d3 to ask 6a and to tell this session before any change of
  the SAM3 cache path of `embedding_run.py`.
  d3 restarts 8168 at about 01:50 (plan 39, with plan 38 of e2); this session answered
  "ready" at 01:44: 40 tests `OK` (`test_embedding_run`, `test_run_routes`); the switch
  `model_cache.READ` holds in the runner process alone, so `inputs_view` keeps the cache.
  e2 [9e7fe4] (about 01:47): plan 38 is done; 33 tests `OK` in
  `tests/test_embedding_run.py`; this session changed its row ER1 to 33.
## drink-atlas-workspace-6a [792d65]

- Task: a new section `pipeline:` in `config.yaml`. The entries `vino-svoe-search-by-photo`
  and `mock` move there from `embeddings:`. The dialog `Run>` of `/testset` and the filter
  of `/runs` show the pipelines, not the embeddings. Added: the pipeline backend
  `embedding` (a pipeline names one `embeddings` entry) and the pipeline
  `gx10-siglip2-so400m-patch16-naflex-p256`; the combo of `/runs` lists the pipelines
  alone. The owner removed `mock` from `config.yaml` and from the source (00:26:27):
  `pipeline/mock_run.py` and `tests/test_mock_run.py` are deleted.
- Source: owner message of 2026-09-25T23:37:48+0300; owner answers of 23:55:27 (a new
  module; `mock` moves fully; labels only; separate hunks); owner messages of
  2026-09-26T00:10:18 and 00:11:19 and the answers of 00:12:24 and 00:15:17 in the
  session ab; plan 34.
- Files: `docs/owner-messages.md` (append), new `docs/plans/34_pipeline-section.md`, new
  `pipeline/pipelines.py`, new `tests/test_pipelines.py`. Hunks: `config.yaml` (the two
  entries of `embeddings` and their comments; a new section `pipeline` after
  `embeddings`), `pipeline/embeddings.py` (the backends, the remote and mock code of the
  class `Embedding`, `remote_refusal`), `pipeline/build_embeddings.py` (`MockBackend`,
  the remote refusal), `pipeline/embedding_routes.py` (the remote refusal of `start`),
  `pipeline/pages/embedding.html` (the remote branch), `pipeline/run_jobs.py`,
  `pipeline/run_job.py`, `pipeline/run_routes.py` (`configurations`, the docstring),
  `pipeline/remote_run.py`, `pipeline/pages/runs.html` (the labels and the code of the
  filter), `pipeline/pages/testset.html` (the texts of the dialog),
  `tests/test_run_jobs.py`, `tests/test_remote_run.py`, `tests/test_run_routes.py` (the
  config of `setUp`, one test). Deleted: `pipeline/mock_run.py`,
  `tests/test_mock_run.py`. Separate hunks in `README.md`, `SMOKE_TESTS.md`,
  `ChangeLog.md`, `COMMANDS.md` (the mock and remote paragraphs). One note line in
  `docs/plans/23_runs-page.md` and `docs/plans/31_remote-configuration.md`. A restart of
  8168.
- Task 2: two basic pipelines of the backend `embedding` for
  `gx10-siglip2-so400m-patch16-naflex-p256`: `siglip2-p256-as-is` and
  `siglip2-p256-crop` (owner message of 2026-09-26T00:45:33+0300, answers of 00:52:41
  and 00:57:59; plan 34 section 7). Done, not committed. Files: `config.yaml` (the two
  entries), `pipeline/pipelines.py` (the key `views`), `pipeline/embeddings.py`
  (`check_steps`), `tests/test_pipelines.py`, separate hunks in `README.md`,
  `SMOKE_TESTS.md` (PL1 to PL4, PL8, PL15 to PL17), `ChangeLog.md`, plan 34. ab [539687]
  wrote the hunks of `pipeline/embedding_run.py` and `tests/test_embedding_run.py`
  (agreed after 00:53). 6a restarted 8168 at 01:01:42 (pid 81403); the watcher pid
  81420 got `caffeinate` (pid 81659); the row of `~/Admin/GPU_TASKS.md` names them.
- State: done, not committed. The section stays until the commit (rule 20). d3 restarted
  8168 at 00:36:23; the live check passed (the dialog and the filter list the 2
  pipelines; `/embedding` and `/clusters` list the 11 embedding models).
- Updated: 2026-09-26T01:38:20+0300
- Agreements: the owner allowed separate hunks in `pipeline/pages/testset.html` (stale
  5c), `ChangeLog.md`, `README.md`, `SMOKE_TESTS.md` (answer of 23:55:27). ab [539687]
  handed over `pipeline/run_jobs.py`, `pipeline/run_job.py`, `tests/test_run_jobs.py`
  (message after 23:44); the hunks of ab in `pipeline/embeddings.py` (`apply_steps`) and
  `pipeline/run_routes.py` (`inputs_view`) stay. ab agreed to separate hunks in
  `tests/test_run_routes.py` and in the mock and remote paragraphs of `COMMANDS.md`, and
  changes its own test `test_another_backend_is_refused`; the restart of 8168 of this
  session also deploys the `inputs_view` hunk of ab (answer after 00:00). cb [395cc7]
  (earlier 15) agreed to the `config.yaml` hunks; its `max_tokens` paragraph and the
  `image_description` block stay. d3 [4920ce] adds `workers` in `image_description`; no
  overlap. d3 adds its own separate hunks in `README.md`, `SMOKE_TESTS.md`,
  `ChangeLog.md`, and `COMMANDS.md` (6a agreed). ab and 6a agreed the split of the
  backend `embedding` (after 00:15): 6a writes `pipelines.py`, `run_job.build`,
  `run_jobs`, and the `config.yaml` entry; ab changes `pipeline/embedding_run.py`
  (`build_pipeline_backend`). ab adds two separate hunks to `pipeline/pages/runs.html`
  (the CSS near `.strip` and `.cand`, the JS `evenCards`). d3 restarts 8168 for both
  sessions after the message "ready" of 6a.
  6a finishes the removal of `mock` (ab agreed after 00:31); ab deleted
  `data/embeddings/mock/` (owner answer of 00:29:55). 39 [fb59ad] adds separate hunks to
  `config.yaml` (`clusters:`), `COMMANDS.md` (the cluster paragraph), and the pages
  `embedding.html`, `runs.html`, `testset.html` (the localStorage of the header); 28
  [5ddfae] and e2 [9e7fe4] add separate hunks to `testset.html` and the docs (6a agreed).
  After 01:19: d3 [4920ce] changed the item `every run` to `All` in
  `pipeline/pages/runs.html` (owner answer of 01:19:00) and added its own bullet in
  `ChangeLog.md`; 6a wrote the README, PL8, and plan 34 hunks of that change. The owner
  removed the pipeline `gx10-siglip2-so400m-patch16-naflex-p256` at about 01:07; 6a fixed
  `tests/test_pipelines.py`, the `config.yaml` comment of the two basic pipelines, PL2 to
  PL5 and PL14, and plan 34. 43 [c33611] adds separate hunks to
  `pipeline/pages/embedding.html` and the docs (6a agreed); d3 sends the hunks of the
  checkbox `Use caches` before it changes `run_jobs.py`, `run_job.py`,
  `tests/test_run_jobs.py`, or `testset.html`.
  After 01:30: 43 [c33611] adds separate hunks to the job rows of
  `pipeline/pages/testset.html` (`.job`, `.job-stop`, `showRunJobs`). e2 [9e7fe4] adds
  separate hunks for plan 38 to `pipeline/run_routes.py` (a route `/api/run-candidate`),
  `tests/test_run_routes.py`, and `pipeline/pages/runs.html`. d3 [4920ce] writes the
  checkbox `Use caches` (plan 39, owner answers of 01:32:00) in `pipeline/run_jobs.py`
  (`start`, the docstring), `pipeline/run_job.py` (`--no-cache`), `tests/test_run_jobs.py`,
  the Run dialog of `pipeline/pages/testset.html` (after the restart), the tag
  `no cache` of `pipeline/pages/runs.html`, and the docs. 6a agreed to each; no line of
  6a changes.

## drink-atlas-workspace-d3 [4920ce]

- Task: the VLM watcher `describe_images.py` sends up to `image_description.workers`
  requests at the same time (a rolling pool of threads); `config.yaml` gets `workers: 8`.
- Source: owner message of 2026-09-25T23:44:31+0300; owner answers of 23:58:53 (rolling
  pool; `image_description.workers`; 8; the pill shows the wall time per image) and of
  2026-09-26T00:15:59 (separate hunks in the files of the stale sections); plan 35.
- Task (2): the filter `Pipeline` of `/runs`. Source: owner message of
  2026-09-26T01:10:00+0300 (a link to the run
  `2026-09-25T205359Z-lab-gx10-siglip2-so400m-patch16-naflex-p256-official-real-photos`,
  the text "Pipeline: All | ...", a screenshot of the open filter); owner answers of
  01:19:00 (the item `every run` becomes `All`; the runs of a pipeline that is not in
  config.yaml stay under `no pipeline`). Files: `docs/owner-messages.md` (append),
  `pipeline/pages/runs.html` (`renderConfigs`: the label and its comment), one bullet in
  `ChangeLog.md`. State: done, not committed; live (a page change, no restart). 6a, 39,
  and ab agreed (after 01:20). 6a wrote the `README.md`, PL8, and plan 34 hunks itself
  (split of 6a, about 01:24).
- Task (3): plan 39, a checkbox `Use caches` in the dialog `Run>` of `/testset`; on by
  default. Off: the job reads no record of `model_cache` (SAM3, GDINO, VLM, LLM), each
  model call goes to its service, the fresh answers are stored, `run.json` gets
  `use_cache: false`, and `/runs` shows the tag `no cache`. Source: owner message of
  2026-09-26T01:20:30+0300 and the answers of 01:32:00. Files: `docs/owner-messages.md`
  (append), new `docs/plans/39_use-caches-checkbox.md`, `pipeline/model_cache.py` (`READ`,
  `lookup`), `pipeline/run_files.py` (`run_head`), `tests/test_model_cache.py`,
  `tests/test_run_files.py`, `tests/test_derive.py` (one test in `Sam3ClientTest`), one
  note line in `docs/plans/25_model-call-cache.md` and
  `docs/plans/32_testset-run-button.md`. After the agreements: hunks in
  `pipeline/run_jobs.py`, `pipeline/run_job.py`, `tests/test_run_jobs.py` (6a),
  `pipeline/benchmark.py`, `tests/test_benchmark.py` (e2), `pipeline/pages/testset.html`
  (the checkbox after `#run-workers`, one CSS rule after `.run-fields input`, one key in
  `startRun`), `pipeline/pages/runs.html` (`.tag.nocache`, the tag in `renderRuns`),
  separate hunks in `README.md`, `SMOKE_TESTS.md` (a new section after "The cache of the
  model calls"), `ChangeLog.md`, one entry at the top of `ResearchLog.md`. A restart of
  8168 (`run_jobs.py`, `run_files.py`). The rows of `~/Admin/GPU_TASKS.md` (the watcher,
  the plan 39 check).
  State: done, not committed. 724 tests `OK`. 8168 restarted at 01:46:24 (server pid
  59921; watcher pid 59935, `caffeinate` pid 60808; e2's plan 38 route went live with
  it). Browser check 24 of 24; live check of 2 crop jobs of 3 queries (01:51). e2 commits
  all pending changes (owner message of 01:43:59); this session does not commit.
  Agreements: 6a (items 1 to 6; this session wrote items 1 to 3), e2 (`benchmark.py`,
  `tests/test_benchmark.py`), ab and 39 (`runs.html`, `testset.html`), cb (the docs),
  43 (no overlap with its job row hunks); 6a, ab, 39, cb, 43, and e2 answered "ready"
  for the restart. 28 [5ddfae] is not in `ListAgents` (stale); d1 [0feb34] is another
  conversation. The dialog hunks do not touch the lines of 28. Updated:
  2026-09-26T01:55:00+0300.
- Files: `docs/owner-messages.md` (append), new `docs/plans/35_vlm-workers.md`. Hunks in
  `pipeline/describe_images.py` (the docstring, the imports, `DEFAULTS`, `settings`,
  `log`, `Status`, `next_items`, `run_item`, `run`, the `start:` line of `main`),
  `config.yaml` (the key `workers` and the comment of the `image_description` block),
  `tests/test_describe_images.py` (the imports, new tests at the end). Separate hunks in
  `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`, `COMMANDS.md`, `ResearchLog.md`; one
  note line in `docs/plans/26_image-description.md` and `docs/plans/29_image-details.md`.
  A restart of 8168. The watcher row of `~/Admin/GPU_TASKS.md`.
- State: done, not committed. The section stays until the commit (rule 20). 8168 was
  restarted at 00:36:23 (server pid 36577; watcher pid 36603 with `workers 8`;
  `caffeinate` pid 36646). Live: 26.5 details per minute instead of 3.4, the same call
  time. 692 tests `OK`. The docs, the ResearchLog entry, and the result of plan 35 are in.
- Updated: 2026-09-26T00:44:26+0300
- Agreements: cb [395cc7] (earlier 15 [40dc83]) agreed at about 23:50 to separate hunks in
  `pipeline/describe_images.py`, `config.yaml`, `tests/test_describe_images.py` (and
  `pipeline/vlm_config.py`, `tests/test_vlm_config.py` if needed); the hunks of cb stay.
  cb sends a message before its own hunk near `TIMEOUT_SECONDS`, `post`, and `ask`. At
  about 00:05 cb, ab [539687], 6a [792d65], and 39 [fb59ad] agreed to separate hunks in
  `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md` (and cb, ab: `ResearchLog.md`; ab, 6a:
  `COMMANDS.md`). 6a: `config.yaml` hunks do not overlap (6a: `embeddings`, `pipeline`;
  d3: `image_description`). 6a asked at about 00:15: d3 restarts 8168 for both after the
  "ready" of 6a, and tells 6a the minute; no restart before. ab: its server code may go
  live (answer after 00:10).
  39 [fb59ad] asked at about 00:21 for separate hunks: a new block `clusters:` in
  `config.yaml` (after `embeddings`, before `pipeline`) and one clusters paragraph in
  `COMMANDS.md`; d3 agreed (no overlap).
  43 [c33611] agreed at about 00:25, after the fact, to the `ChangeLog.md` bullet (top of
  `## 2026-09-26`) and the `SMOKE_TESTS.md` section with VW1 after DT15.

## drink-atlas-workspace-43 [c33611]

- Task: the pixel size (width × height) under each image of a main image conflict of the
  dialog `Import from vino-svoe.ru` of `/dataset`.
- Source: owner message of 2026-09-25T23:58:00+0300 and the answers of 2026-09-26T00:00:30.
- Files: `docs/owner-messages.md` (append), `pipeline/pages/website_import.js`, one bullet in
  `ChangeLog.md`, one row in `SMOKE_TESTS.md`.
- State: done, not committed. The section stays until the commit (rule 20). The
  `ChangeLog.md` bullet and row IW17 are in. No restart of 8168.
- Updated: 2026-09-26T00:21:00+0300
- Agreements: cb [395cc7] agreed at about 00:09 to the new heading `## 2026-09-26` with
  one bullet at the top of `ChangeLog.md` and row IW17 after IW16 in `SMOKE_TESTS.md`;
  its bullets of `## 2026-09-25` and its rows S11 and DT9 to DT15 stay as they are.
  39 [fb59ad] agreed at about 00:10 to the same two hunks. ab [539687] agreed at about
  00:11 and adds its own bullet under the same heading.
  d3 [4920ce] asked at about 00:20, after the fact, for its bullet "Plan 35" at the top of
  `## 2026-09-26` in `ChangeLog.md` and a new section with row VW1 after DT15 in
  `SMOKE_TESTS.md`; this session agreed. The bullet and IW17 of this session are unchanged.
- Task 2: the stop button of each job row of `/embedding` shows an icon, not the red text
  `(x)`, and moves to the start of the row.
- Source: owner message of 2026-09-26T01:24:00+0300.
- Files: `docs/owner-messages.md` (append). After agreement with 6a [792d65] and 39
  [fb59ad]: separate hunks in `pipeline/pages/embedding.html` (the CSS `.job` and
  `.job-stop`, the stop button in `showJobs`, the comments near them). Separate hunks:
  the `/embedding` job paragraph of `README.md`, rows EB41 to EB43 of `SMOKE_TESTS.md`,
  one bullet in `ChangeLog.md`. No restart of 8168 (a page file).
- State 2: done, not committed. The section stays until the commit (rule 20). A
  Playwright check with mocked jobs passes (the button is the first cell, an SVG icon, no
  text, 1,440 px dark and light, 390 px; a click on the icon sends the stop request; no
  page error). The owner message of 01:26:00 (an embedding override in the dialog `Run>`)
  was cancelled by the owner at 01:27:00; no work on it.
- Updated 2: 2026-09-26T01:33:00+0300
- Agreements 2: 6a [792d65] agreed at about 01:27 (6a has no hunk left in
  `embedding.html`); 39 [fb59ad] agreed at about 01:27 (its header state block near the
  end of the script stays). Both agreed to the separate doc hunks.
- Task 3: the same change for the run job rows of `/testset`: the stop button shows the
  icon `×`, not the red text `(x)`, and is the first cell of the row. `open run` of an
  ended row stays at the end.
- Source: owner message of 2026-09-26T01:32:00+0300.
- Files: `docs/owner-messages.md` (append). After agreement: separate hunks in
  `pipeline/pages/testset.html` (the CSS `.job`, `.job-stop`, the `@media (max-width:
  860px)` line of `.job`; the button, the link, and the row template in `showRunJobs`).
  The owner asked for this change; 5c [cbb143] is stale. Separate hunks: the `/testset`
  job row lines of `README.md` and `SMOKE_TESTS.md`, one bullet in `ChangeLog.md`. No
  restart of 8168.
- State 3: done, not committed. The section stays until the commit (rule 20). A
  Playwright check with mocked jobs passes (running and stopping rows start with the SVG
  icon; the ended row has an empty first cell and `open run` last; the names align;
  1,440 px dark and light, 390 px; a click on the icon sends the stop request; no page
  error). Doc hunks: README job row sentence, RJ6, new RJ11, one ChangeLog bullet.
- Updated 3: 2026-09-26T01:43:00+0300
- Agreements 3: 39 [fb59ad], 6a [792d65], 28 [5ddfae], d3 [4920ce], and e2 [9e7fe4]
  agreed at about 01:37 to 01:39; no overlap with their hunks. 6a: the link
  `/runs?configuration=<name>` of `open run` stays. d3 adds its checkbox `Use caches` in
  the Run dialog later.

## drink-atlas-workspace-28 [5ddfae]

- Task: (1) split the select `Show` of `/testset` into several filter axes. (2) remove
  the select `Slugs` of `/testset`. (3) plan 37: the select `Clusters` of `/testset`
  takes the place of `Wine` and groups the wines by the clusters of an embedding. (4) the
  sort `cluster size` and the button `Additional settings` (Marks, Clusters) of `/testset`.
- Source: owner message of 2026-09-26T00:25:11+0300; owner message of 00:39:13 and the
  answer of 2026-09-26T00:39:51+0300 (remove entirely); owner message of 00:42:25 and the
  answers of 00:46:18 (plan 37); owner message of 01:06:36 and the answers of
  01:08:49 (task 4).
- Files: `docs/owner-messages.md` (append), new `docs/plans/37_testset-cluster-grouping.md`. After the owner choice: hunks in
  `pipeline/pages/testset.html` (the select `Show`, `matchFilter`, `render`,
  `VIEW_PARAMS`, `readViewFromUrl`, `openFromHash`, `showGroup`, the select `Slugs`, the
  `change` listener list, `matchAxis`, `load`, a new cluster block, the CSS of
  `tr.cl-head`); separate hunks in `README.md`,
  `SMOKE_TESTS.md`, `ChangeLog.md`.
- State: done, not committed. The section stays until the commit (rule 20). Tasks (1)
  to (4) are done. No restart of 8168 was necessary.
- Updated: 2026-09-26T01:33:44+0300
- Agreements: 6a [792d65] agreed to separate hunks in `pipeline/pages/testset.html`
  (message of about 00:30; its hunks are the `#run-open` title and the Run dialog). The
  owner asked for the change of this page (answers of 00:26:58); 5c is stale. e2 [9e7fe4]
  changes the NULL lines of `render` (`nullRow`, the row filter, `VIEW`, `#count`); this
  session agreed before 00:39 and handed over the new filter line. 39 [fb59ad] adds a
  localStorage block and start-up call lines (owner message of 00:30:00); this session
  agreed before 00:39. 39 agreed that this session removes `"#slugsel"` from its
  `HEADER_IDS` line (message after 00:40); done in the same edit as task (2).
  Plan 37: e2 agreed to the new hunks in `render` (message after 00:49); 39 agreed that
  `load` reads its consts `HEADER` and `URL_VIEW` (message after 00:49).
  43 [c33611] adds hunks for the run job rows (`.job`, `.job-stop`, `showRunJobs`; owner
  message of 01:32:00); this session agreed at 01:33 (no overlap).

## drink-atlas-workspace-e2 [9e7fe4]

- Task: plan 36: the row "No Match" (`__null__`, a run uses its photos) and the Drawer
  (the right sidebar, a new place `__drawer__`, a run does not use its photos) of `/testset`.
- Source: owner message of 2026-09-26T00:25:00+0300 and the answer of 00:29:00;
  `docs/plans/36_no-match-row-and-drawer.md`.
- Files: `docs/owner-messages.md` (append), new `docs/plans/36_no-match-row-and-drawer.md`.
  After the approval: `pipeline/testsets.py`, `pipeline/benchmark.py`,
  `pipeline/manual_wines.py`, `pipeline/testset_routes.py` (docstring),
  `tests/test_testsets.py`, `tests/test_testset_routes.py`, `tests/test_benchmark.py`,
  `tests/test_manual_wines.py`, one note line in `docs/plans/24_testset-page.md`. Separate
  hunks in `pipeline/pages/testset.html` (the sidebar HTML, `isNullRow`, `labelButtons`,
  `cardHtml`, `cardsHtml`, `rowHtml`, the NULL lines of `render`, `renderSide`, `stats`,
  the move menu, the drop handlers, the key `0`), `README.md`, `SMOKE_TESTS.md`,
  `ChangeLog.md`. Rows TP3, TP18, TP20, TP21, TP22 and a new group NM1 to NM8 of
  `SMOKE_TESTS.md`. Port 8175 in `~/Admin/mbp2023/PORTS_USED.md`.
- State: done, not committed. The section stays until the commit (rule 20). 692 tests
  `OK`; 23 browser checks pass on port 8175 (stopped). The server code went live with the
  restart of 8168 by d3 at 00:36:23; this session did not restart 8168.
- Updated: 2026-09-26T00:49:11+0300
- Agreements: 28 [5ddfae] agreed to the separate hunks in `testset.html` (its code hunks
  are in; `render` keeps `matchFilter(r, filts)`), `README.md`, `SMOKE_TESTS.md` (28 takes
  TP24 to TP28; this session takes other numbers), `ChangeLog.md`. 6a [792d65] agreed (no
  overlap); this session tells 6a and d3 [4920ce] the minute of its restart of 8168.
  28 [5ddfae] (plan 37, message after 00:45): new hunks in `render` (the grouping branch,
  the `cl-head` rows in the innerHTML map, one `#count` clause), a CSS rule `tr.cl-head`,
  and a function block before `render`. This session agreed: no overlap; the header
  rows stay out of `rows` and `VIEW`, and No Match stays the first row with no header.
  43 [c33611] (message of about 01:33): separate hunks in `testset.html` (`.job`,
  `.job-stop`, the `@media` line of `.job`, the `tail`/`link` consts and the row template
  of `showRunJobs`), `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`. This session agreed:
  no overlap.
- Task 2: plan 38: a click on a candidate card of an embedding run on `/runs` opens the
  large view; the rail shows each catalogue item of that wine (the PNG that went to the
  model) with the cosine that the run recorded. The runner records the items.
- Source: owner message of 2026-09-26T01:23:11+0300 and the answers of 01:29:00.
- Files (task 2): `docs/owner-messages.md` (append), new
  `docs/plans/38_candidate-inputs.md`. After the agreements: hunks in
  `pipeline/embedding_run.py` (`Catalogue`, `Catalogue.rank`, a new function after
  `model_inputs`), `tests/test_embedding_run.py` (new tests at the end),
  `pipeline/run_routes.py` (the docstring, `ROUTES`, one branch of `respond`, a new
  function at the end), `tests/test_run_routes.py` (new tests at the end),
  `pipeline/pages/runs.html` (CSS after `.model-input .input-label`, `candCard`,
  `bottleHtml`, the `<tr>` of `rowHtml`, one line in `loadRun`, `loadLbInputs`, a new
  render function after `renderLbInputs`), `docs/API.md` (the route and the key
  `items`). Separate hunks in `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`. A restart
  of 8168.
- State (task 2): done, not committed. 33 tests of `test_embedding_run.py` `OK`; 30
  browser checks pass on port 8175 (stopped at 01:45). The route went live with the
  restart of 8168 by d3 at 01:46:24 (checked). Agreements: ab, 6a, 39, d3 agreed to the
  separate hunks (messages of about 01:37 to 01:40); ab asked for `items` in the three
  key-set checks (done). This session agreed to d3's hunks in `pipeline/benchmark.py` and
  `tests/test_benchmark.py` (plan 39, `use_cache`).
- Task 3: the owner message of 2026-09-26T01:43:59+0300: wait for the present work of the
  sessions, commit all, then run the basic pipelines with each embedding entry, compare
  the results, and write a report. Plan 40. Files: `docs/owner-messages.md` (append), new
  `docs/plans/40_embedding-benchmark.md`, `QUESTIONS.md` (append Q2 to Q11), `config.yaml`
  (20 new entries of `pipeline:` after `siglip2-p256-crop`), `data/embeddings/*` (the
  builds of the missing items and of `gx10-siglip2-so400m-patch16-512`), new runs in
  `runs/`, new `docs/reports/2026-09-26_embedding-benchmark.md`, one entry at the top of
  `ResearchLog.md`, one bullet in `ChangeLog.md`, a row of `~/Admin/GPU_TASKS.md`. State:
  waiting: the work of the active sessions (all but d3 sent "finished" by 01:52).
- Updated (task 2, 3): 2026-09-26T01:49:00+0300
