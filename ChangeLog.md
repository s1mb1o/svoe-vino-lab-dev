# ChangeLog

## 2026-09-26

- Plan 50, section 8, item 7: `data/images/additional/` is in git too (owner message of
  2026-09-26T18:53:37+0300; session drink-atlas-workspace-96). `.gitignore` takes the
  folder back, and the skill `backup-lab-db` commits it with the other two image folders.
- Plan 50, section 8: the main photos and the patches in git (owner message of
  2026-09-26T17:51:32+0300, answers of 17:54:00; session drink-atlas-workspace-96).
  `.gitignore` ignores the content of `data/` and of `data/images/` and takes back
  `data/images/main/` (2,019 files, 135 MB) and `data/images/patched/` (18 files, 7 MB);
  `data/cache/` and the rest of `data/` stay out. Step 3 of the skill `backup-lab-db`
  commits the two folders with `db-export/` in one commit, in plain git, and counts the
  added and the removed files in the message.
- Plan 50, a text export of the lab database for the git history (owner message of
  2026-09-26T17:26:06+0300, answers of 17:28:00; session drink-atlas-workspace-96). New
  `pipeline/db_export.py`: `export` writes `db-export/schema.sql`,
  `db-export/rows/<table>.jsonl` (one JSON object for each row, in primary key order,
  with the `rowid`), and `db-export/after-rows.sql` (the indexes, the views, the
  triggers, and `PRAGMA user_version`); `restore` builds a new file only, and creates the
  triggers after the rows. New skill `.claude/skills/backup-lab-db/`: the export, a round
  trip check, and a commit of `db-export/` alone through a private git index. On schema
  21: 17 tables, 26,792 rows, 12 MB; the export took 0.4 s and the restore 0.5 s; the
  second export of the restored file was byte for byte equal. 8 tests in
  `tests/test_db_export.py`. Plan 07 open question 3 has its answer; the comment of
  `/data/` in `.gitignore` names `db-export/`.
- The label rules again with `qwencloud-qwen3.8-max`, and the benchmark of plan 48 again
  (owner message of 2026-09-26T16:01:00+0300; session drink-atlas-workspace-39). The
  block `label_rules:` of `config.yaml` names `qwencloud-qwen3.8-max` for stage 2, with
  thinking, 4 calls at the same time; stage 1 stays on `qwen3.5-9b-nvfp4`. 163 rules in
  61 min, 0 errors (131 `sheet`, 32 `verdict`); the 9B rules are kept as
  `cluster-rules.qwen3.5-9b-nvfp4.2026-09-26T1116.json`. The benchmark (label `bench49`):
  `rerank-siglip2-512-crop` 83.82 % R@1 (9B rules 83.26 %, no re-rank 81.29 %), and
  `barcode-rerank-siglip2-512-crop` 85.17 %, the best of the lab; against no re-rank 52
  wins and 11 losses, p 1.7e-07; against the 9B rules +0.55 points, p 0.21, not
  significant. Negatives rejected 84.42 % (9B rules 85.10 %). Plan 48, section «Result
  with the rules of `qwen3.8-max`»; plan 45, change 8.
- Plan 49, a probe after a VLM timeout and the dialog of the watcher (owner message of
  2026-09-26T10:33:00+0300, answers of 15:18:00 and 15:35:00; session
  drink-atlas-workspace-0d). Cause of the pill `VLM waiting: no answer from
  http://192.168.86.14:1808`: one detail request
  (`a902e43a5f77`, Fanagoria «100 оттенков красного» Pinot Noir) ran for the full 300 s
  timeout 45 times, while the service served other requests; each timeout counted as a
  failure of the service, so the image never reached `max_attempts` and each timeout
  started the backoff. The watcher stored a valid answer at 07:39:21Z in another batch; a
  one-off run of this session at 12:18:31Z read the same answer from `model_cache` and
  moved `vlm_at` of the row to 12:18:31Z. Code: `describe_images.post` marks a read
  timeout (`timed_out`); `ask` then sends `probe` (1 token, no image, 30 s); when the
  probe answers, the timeout counts against the image and starts no backoff. The state
  file adds `endpoint`, `timeout_seconds`, `workers`, `running`, and in `waiting`
  `waiting_since`, `backoff_seconds`, `retry_at`, `error_sha256`, `error_stage`.
  `image_descriptions.watcher_status` adds `call_view` of each call and of the failed
  image, `retry_in_seconds`, and `max_attempts`; `log_tail` reads the end of the log.
  `GET /api/image-description-status?log=<1..200>` adds the log tail. `/dataset`: the
  pill shows the full error (the cut at 40 characters showed the port `18081` as `1808`);
  a click on the pill opens the dialog `VLM watcher`. New tests: 7 in
  `test_describe_images.py`, 3 in `test_image_descriptions.py`, 1 in
  `test_lab_server.py`; smoke tests VP1 to VP10; a Playwright check 88 of 88.
- Plan 48, the benchmark of the cluster re-rank on `my` (label `bench48`; session
  drink-atlas-workspace-39): `rerank-siglip2-512-crop` R@1 81.29 % → 83.26 %, and
  `barcode-rerank-siglip2-512-crop` 82.58 % → 84.55 %, each +1.97 points with 48 wins and
  16 losses (exact McNemar p 7.7e-05); the negatives rejected 82.88 % → 85.10 % (16 wins,
  3 losses, p 0.0044). The step acted on 574 of 2,209 photos, with 0 VLM errors; a photo
  with the step took a median of 5.1 s. The section «Result» of
  `docs/plans/48_cluster-rerank.md` holds the losses and the candidate changes.
- Plan 48, the cluster re-rank at query time (owner messages of 2026-09-26T13:04:00+0300
  and 13:10:00 «implement», answer of 14:56:00; session drink-atlas-workspace-39). A
  pipeline of the backend `embedding` takes the key `rerank` (`pipeline/cluster_rerank.py`,
  a port of the kind `cluster_rules` of `svoe-vino-matcher` with its prompts verbatim).
  When the rank-1 card and another card of its cluster stand in the top 5, the VLM
  (`qwen3.5-9b-nvfp4`, thinking off) reads the SAM3 label cut of the photo with the rule of
  that cluster (the rules of plan 45, from the embedding directory of `rerank.rules`), and
  only the cards of that cluster change their order. A failure keeps the base order. The
  re-rank runs inside the barcode step. Each touched card holds `explain` with `kind:
  cluster_rules` for the VLM box of `/runs`; the trace gets the step `cluster_rules`.
  `pipelines.py` checks the key; `embedding_run.build_pipeline_backend` wraps the backend
  (one hunk; the owner allowed it at 14:56:00); `label_rules.ask` takes a JSON schema. New
  pipelines `rerank-siglip2-512-crop` and `barcode-rerank-siglip2-512-crop`. New tests
  `tests/test_cluster_rerank.py` (19); smoke tests RR1 to RR6. A smoke run of 8 real
  photos: 4 misses at rank 2 moved to rank 1, 4 hits stayed. 8168 restarted by 39 at
  15:09:04 with the new entries of `config.yaml` (pid 7442).
- The full benchmark on the test set `my` (owner message of 2026-09-26T11:30:00+0300,
  answer «All 45 pipelines» of 11:34:00; session drink-atlas-workspace-39): the 45
  pipelines of `config.yaml`, label `bench45`, 2,209 photos (1,625 positive, 584 negative).
  Best `barcode-siglip2-512-crop`: R@1 82.6 %, R@5 96.7 %, MRR 0.890; without the barcode
  step 81.3 %. The official recognizer: 67.6 %. The barcode step adds 1.2 to 1.3 points to
  each pipeline and loses no photo. Report:
  `docs/reports/2026-09-26_full-benchmark-my.md`. The queue scripts and the logs are in
  `work/bench45/`; the 20 barcode pipelines of the gx10 entries needed a second pass with
  `embedding_python`.

- Plan 46, the Health page `/health` (owner message of 2026-09-26T10:35:48+0300, answers
  of 11:02:57; session drink-atlas-workspace-cc). New module `pipeline/health.py` and page
  `pipeline/pages/health.html`; the link `Health` is last in the navigation of each page.
  The status part shows the server, the database (the schema version, the wines, the free
  disk), the image description watcher with the failures of the last hour of its log, the
  jobs that run, and the models that run on the llama-swap gateway. The button `Check`
  checks each endpoint of `config.yaml` (the `vlm` and `embeddings` entries, SAM3, the
  vino-svoe.ru API), 4 at the same time, with one row and a clear failure text for each.
  The check "Hybrid" of the owner: a model that does not run on its llama-swap gateway
  gets no call; a model that runs and a cloud entry get a real call of 1 token; the local
  embedding entry loads no model. New routes `GET /api/health` and
  `POST /api/health/check`. At 11:24:33 a byte-identical repeat of the check prompt
  stopped the llama.cpp model `qwen3.5-9b` on gx10 (`ggml_abort` on a full hit of the
  prompt cache of the hybrid model); each chat request now holds a random token. New
  tests `tests/test_health.py` (28); smoke tests HL1 to HL9. 8168 restarted by cc at
  11:23:30 (pid 95458) and 11:29:51 (pid 8285).
- Plan 45, the label rules of the embedding clusters (owner message of
  2026-09-26T09:07:24+0300, answers of 09:27:00 and 10:19:00; session
  drink-atlas-workspace-39). New command `pipeline/build_label_rules.py` with the module
  `pipeline/label_rules.py`, a port of stages 1 and 2 of
  `svoe-vino-testset/scripts/cluster_rules.py` (verbatim prompts; a test compares them
  with `scripts/cluster_rules.py`). Stage 1 describes the label of each card from the
  package cut, enlarged to 2048 pixels, with no card data. Stage 2 sends one label cut for
  each card (768 pixels), the card data, the descriptions, and the note, and writes the
  difference sheet and the rule text. The check strikes a bottle number, a feature
  outside the label, a year that the card name does not state, and the alcohol value
  when another question is valid; the mode is `sheet`, `verdict`, or `none`. The rules
  go to `data/embeddings/<name>/cluster-rules.json` (`spaces.label`, for the view
  `combined`). New block `label_rules:` of `config.yaml`, with a comment for each key:
  `qwen3.5-9b-nvfp4`, thinking off in both stages (switch: `rules_thinking`), at most 20
  images in one prompt (`rules_max_images`; the owner set `--limit-mm-per-prompt` to 20).
  A cluster over the limit gets an error record and no call; a refusal of the service
  stops the run with a message that names the limit. `/clusters` shows the `label` rules
  in the views `combined` and `label` (`clusters.RULE_SPACE_OF`); a rule is stale also
  after a note change. The cluster build of 10:33:43 made the stale artifact current (163
  clusters). The run of 10:35 to 11:16: 382 descriptions, 163 rules (139 `sheet`, 24
  `verdict`), 0 errors. New tests `tests/test_label_rules.py` (19) and
  `tests/test_build_label_rules.py` (14); smoke tests LR1 to LR9. 8168 restarted by 39
  at 10:33:31 (pid 2858).
- `/clusters`: "Save note" starts the rebuild of the label rule of that cluster as a
  separate process (`build_label_rules.py --cluster <slug> --wait`; log
  `data/embeddings/<name>/label-rules.log`), and the page swaps in the new rule when it is
  current (owner message of 2026-09-26T11:08:00+0300, answer of 11:11:00). The rebuild
  waits for a running rule build. Tests in `tests/test_cluster_routes.py`. 8168
  restarted by 39 at 11:15:39 (pid 80384). The check on the page: the «Фантом» rule was
  rebuilt with the new note and now asks for the ratio and for the colour of the small
  box; the colour of card B («dark blue») is wrong (the box is dark burgundy).
- `/clusters` draws the segmented cut of each card image with its transparent
  background on a checkerboard, as `/embedding` does (owner message of
  2026-09-26T09:51:00+0300; session drink-atlas-workspace-39). Before, a card showed the
  prepared image, which the step `white_background` had put on white. `clusters.detail`
  gives each image the new field `cut_url`: the `package` cut in `full`, the `label` cut
  in `label`, from `image_derivative`. An image with no `segment` step keeps its prepared
  image. The preview shows the same cut. The edge links still open the prepared images.
  New test `test_detail_gives_the_segmented_cut_of_each_image`; smoke test LC21, LC3
  changed. 8168 restarted by 39 at 09:56:09 (pid 35773). A browser check in the light and
  the dark theme passes: 393 of 393 card images are cuts, with no page error.
- `/embedding`, build log: each `item_failed` line names the wine of the failed file:
  `wine` (the slug), `name`, `image_type` of the first wine in import order, and
  `other_wines` when more wines use the same file (owner messages of
  2026-09-26T07:50:00+0300 and 07:51:00; session drink-atlas-workspace-4f [9a1cce]). The
  checkbox of the dialog is `Show progress and request`. It is on at the start. When it
  is off, it hides the `progress` and `request` lines. An `item_failed` line always
  shows. No restart: 8168 starts `build_embeddings.py` from disk for each build and
  reads the page from disk. Tests: `test_build_embeddings.py`,
  `test_embedding_routes.py`, `test_embeddings.py` 54 OK. Smoke rows EB19 and EB20.
- The lab uses the clusters of `data/embeddings/<name>/` alone (plan 43, owner message of
  2026-09-26T07:32:51+0300 and the answers after it; session drink-atlas-workspace-2a
  [693b64]). `GET /api/run-clusters?id=<run id>` answers the view `combined` of
  `clusters.json` of the embedding of that run (`backend.embedding` of `run.json`, or
  `backend.id` for an older embedding run), the `label` rule of each cluster from
  `cluster-rules.json`, and `stale`. `/runs` reads it for each opened run; the frame link
  opens `/clusters?name=<embedding>&space=combined#<slug>`. A run of another backend shows
  no frame. `dataset/catalog-clusters.json`, `dataset/catalog-cluster-rules.json`,
  `dataset/catalog-cluster-notes.json`, `scripts/10_clusters.py`,
  `scripts/11_cluster_rules.py`, and `scripts/cluster_rules_report.py` moved to
  `../.attick/svoe-vino-lab/`, with the former README text of the catalogue clusters and
  their label rules. `scripts/review_server.py` lost its page `/clusters`, the routes
  `/api/clusters`, `/api/cluster-note`, `/api/cluster-rule-edit`, `/api/cluster-rule`,
  and its cluster frames; `docs/API.md` and `docs/openapi.yaml` lost their contracts.
  `scripts/cluster_rules.py` stays (owner answer): only tests import it now. The one
  reviewer note (the Fantom blend ratios) is in `cluster-notes.json` of
  `gx10-siglip2-so400m-patch16-naflex-p256` under the key `a29e59138ed4`. Tests:
  `test_run_routes.py` 7; the full suite 768 OK. Smoke rows R53 to R58 and CR1 to CR3.
- `/dataset`: the row `Advanced Filters:` has a second filter `Identifier` with `All`,
  `has GTIN`, `has QR URL`, and `has Drink Atlas` (owner message of
  2026-09-26T07:48:00+0300; session drink-atlas-workspace-74 [1c1b2b]). It reads
  `_gtins`, `_qr_urls`, and `_atlas_product_uuid` of `GET /api/dataset`. The header
  state in `localStorage` keeps its value. A page change alone; no restart. On the new
  database: 22, 3, and 367 of 2,103 records. 14 Playwright checks pass (smoke rows ID23
  to ID25).
- `/dataset`: the path is `/dataset/website-import` while the dialog `Import from
  vino-svoe.ru` is open (owner message of 2026-09-26T08:00:00+0300, answer of 08:07:00;
  session drink-atlas-workspace-74 [1c1b2b]). A link to it or a reload of it opens the
  dialog with the newest run. A close and Back give `/dataset`; Forward opens the dialog
  again. `imagePreviewOfPath` of `dataset.html` does not read `website-import` as a wine
  slug. `Reload the page` in the result loads `/dataset`. Page code alone
  (`website_import.js`, `dataset.html`); no restart. 17 Playwright checks pass; 6 website
  import tests and 60 lab server tests OK (smoke rows IW18 to IW20).
- The pipelines have a barcode step: the optional key `barcode:` of a pipeline of the
  backend `embedding` (plan 42; owner message of 2026-09-26T07:22:10+0300 and the answers
  of 07:27:08; session drink-atlas-workspace-1c [800d92]). The new `pipeline/barcode.py`
  is a copy of the zxing-cpp decoder of `svoe-vino-matcher/svm/pipelines/barcode.py`,
  which svoe-vino-testset uses through `svm-barcode-siglip2-448`. The lookup reads
  `wine_code` of the Active wines (GTIN-14 and QR URL, `codes.py`). A hit answers the photo
  with each wine of the code at score 1.0, and the embedding does not run. A miss asks the
  embedding. `config.yaml` has 22 twins `barcode-<pipeline>`, with the options of
  `barcode-siglip2-448`. `embedding_run.build_pipeline_backend` puts `barcode.CodeFirst`
  around the backend. `/api/run-inputs` and `/api/run-candidate` give a note for a code
  answer. The trace of plan 41 gets the step `barcode` first (agreed with f4 [b39b7b]).
  zxing-cpp 2.3.0 is in `~/.venvs/svoe-vino-lab` (a source build: no wheel for Python
  3.14) and in `requirements-local.txt`. `tests/test_barcode.py`: 28 tests OK with
  `embedding_python`; 5 decoder tests are skipped in system `python3`. A check on 169 real
  photos of the 22 wines of `code-map.json`: 40 hits, 0 wrong wines, 129 photos with no
  code; median 230 ms, maximum 619 ms for each photo.
- The header controls of `/dataset`, `/embedding`, `/clusters`, `/testset`, and `/runs`
  are kept in `localStorage` (the key `svl.<page>.header`; `/embedding` keeps its old key
  for the configuration) and come back at the next page load (owner message of
  2026-09-26T00:30:00+0300 and the answers of 00:33:00; session
  drink-atlas-workspace-39 [fb59ad]). Code in each page; no server change. A value in the
  URL wins. On `/testset`, an address with a view key restores no stored view control,
  because the address leaves out a control at its default (proposal of
  drink-atlas-workspace-28 [5ddfae]); on `/clusters`, an address with `space` holds the
  image. A stored value that is no longer an option is ignored, and an unknown stored test
  set gives the default set. The variant group filter of `/testset` is not stored. A
  Playwright check of the five pages passes (15 checks, no page error).
- The cluster build of `/clusters` has limits, and its settings are in `config.yaml` (owner
  messages of 2026-09-25T23:00:00+0300 to 2026-09-26T01:05:00+0300; session
  drink-atlas-workspace-39 [fb59ad], earlier name drink-atlas-workspace-43 [58637c]). A
  build with full threshold 0.5 gave 2,055,813 links, one cluster of 2,045 wines, and a
  5 GB `clusters.json`, and the page did not load. Now a build stops, answers HTTP 400,
  and keeps the old file when one space has more than `max_links` (20,000) links or one
  cluster has more than `max_cluster_size` (50) wines. The link search checks the count
  after each row, so it stops in less than one second. The new block `clusters:` of
  `config.yaml` holds `full_threshold`, `label_threshold`, `min_cluster_size`,
  `max_links`, and `max_cluster_size` for every embedding (`clusters.config_values`); a
  missing key takes its default, and an unknown key or a value that is not valid stops the
  build. `min_cluster_size` (2) drops the smaller clusters at the build. The page has no
  threshold input and no input "Minimum size"; its summary shows the build settings.
  `POST /api/clusters/<name>/build` refuses a body with a threshold.
  `build_clusters.py --full-threshold --label-threshold` replace the thresholds for one
  build. `settings` of `clusters.json` holds `min_cluster_size`. The clusters of
  `gx10-siglip2-so400m-patch16-naflex-p256` were built again at 0.95 / 0.95 (1.0 MB:
  full 147, label 108, combined 168 clusters). Measured limits: 0.9 passes (largest
  cluster 24), 0.85 stops (a chain of 184 wines). Decisions D6, D6a, and D7 of plan 30;
  the cluster paragraph of `COMMANDS.md`. 29 cluster tests `OK`.
- Plan 40, the benchmark of the 11 embedding entries with the two basic pipelines (owner
  message of 2026-09-26T01:43:59+0300; session drink-atlas-workspace-e2 [9e7fe4]). First,
  the commit 1dd3006 of all pending changes. Then 20 new pipelines in `config.yaml`
  (`<short>-as-is`, `<short>-crop` for each other entry), the builds of the missing index
  items and of `gx10-siglip2-so400m-patch16-512`, and 44 runs on `my` and
  `official-real-photos` (label `bench40`, 0 errors). Best: `siglip2-512-crop`, R@1
  79.8 % on `my`. The report is `docs/reports/2026-09-26_embedding-benchmark.md`. The
  session answered its own questions in `QUESTIONS.md` (Q2 to Q13) and removed the stale
  sections 5c, a9, 3b, 28 of `ACTIVE_WORK.md` after the commit (Q12).
- Plan 38, the catalogue inputs of a candidate of an embedding run on `/runs` (owner
  message of 2026-09-26T01:23:11+0300 and the answers of 01:29:00; session
  drink-atlas-workspace-e2 [9e7fe4]). `embedding_run.Catalogue.rank` records the key
  `items` in each candidate: each current item of the wine in the index, with its image
  type, its `embedding_hash`, and its cosine to the query (null for a view that the query
  does not have). The new route `GET /api/run-candidate` answers the items with the PNG of
  the index that went to the model, the best item of each view, and the state of the item
  in the present index. `/api/run` removes `items` from its rows. On `/runs`, a click on a
  candidate image of an embedding run fills the strip of the large view with these items.
  A run from before plan 38 shows the items of the present index with no cosine. 33 tests
  of `test_embedding_run.py` `OK`; 30 browser checks pass on a test copy on port 8175 in
  both themes. Found on the way: the photo `q-000001` of the set `my` (a
  `a-gordienko-m-nikolaev-pino-nuar-…` photo) is the `main_patched` image of
  `fanagoriya-100-ottenkov-krasnogo-kaberne-…`, so that wine takes rank 1 (0.8141).
- Plan 39, the checkbox `Use caches` of the dialog `Run>` of `/testset` (owner message of
  2026-09-26T01:20:30+0300 and the answers of 01:32:00; session
  drink-atlas-workspace-d3 [4920ce]). The box is on at each page load. Off, the job reads
  no record of `data/cache/` (SAM3, GDINO, VLM, LLM): each model call goes to its service,
  so the latency is real time, and the fresh answers are still stored. `model_cache.READ`
  (True by default) is the one switch; `run_job.py --no-cache` sets it before the backend
  is built, so each present and future client follows it. `POST /api/run-jobs` takes
  `use_cache` (a missing key is true; a value that is not a boolean is HTTP 400). The
  event `start` and `run.json` hold `use_cache`; `/runs` shows the tag `no cache` for
  `use_cache: false`. Today only `siglip2-p256-crop` reads a cache (the SAM3 cut); the
  embedding request and the vino-svoe API have no cache. New tests in
  `test_model_cache.py`, `test_derive.py`, `test_run_files.py`, `test_benchmark.py`, and
  `test_run_jobs.py`.
- `/testset`: the run job rows get the same stop button as `/embedding`: an icon `×` in
  the muted text color, not the red text `(x)`, in the first cell of the row (owner
  message of 2026-09-26T01:32:00+0300; session drink-atlas-workspace-43 [c33611]). An
  ended row has an empty first cell and keeps `open run` in the last cell. A window of
  860 px or less puts the first cell in a narrow column at the left of the row. The
  request `POST /api/run-jobs/<name>/stop` does not change. A page change alone; no
  restart of 8168.
- `/embedding`: the stop button of each running job row shows an icon `×` in the muted
  text color, not the red text `(x)`, and is the first cell of the row (owner message of
  2026-09-26T01:24:00+0300; session drink-atlas-workspace-43 [c33611]). A window of
  780 px or less puts the button in a narrow column at the left of the row. The request
  `POST /api/embeddings/<name>/stop` does not change. A page change alone; no restart
  of 8168.
- `/runs`: the first item of the filter `Pipeline` reads `All — N`, not `every run — N`
  (owner message of 2026-09-26T01:10:00+0300 and the answers of 01:19:00; session
  drink-atlas-workspace-d3 [4920ce]). The value stays "", so the address key
  `configuration` and the stored header value do not change. The runs of a pipeline that
  is not in `config.yaml` stay under `no pipeline` (owner answer). A page change alone;
  no restart of 8168.
- `/testset`: the sort `cluster size, largest first` and the button `Additional
  settings` (owner message of 2026-09-26T01:06:36+0300 and the answers of 01:08:49;
  session drink-atlas-workspace-28 [5ddfae]; plan 37, section "Changes"). The sort
  needs an embedding in `Clusters`: the largest cluster first, a tie by the cluster id,
  and the rows of a cluster by slug; with `Clusters` on `No` it is disabled and falls
  back to `slug A-Z`. `Marks` and `Clusters` moved into a second row that the button
  shows or hides; the button shows `· N` for N of the two away from their default, and
  `svl.testset.more` in localStorage keeps the open state. The ids of the selects and
  the address keys did not change. A browser check on 8168: 14 of 14 checks pass (the
  order of all 168 headers, the count, the fallback, the reload, 390 px with no
  horizontal scroll), and the check of plan 37 gives the same result as before.
- Two basic pipelines of `gx10-siglip2-so400m-patch16-naflex-p256` (owner message of
  2026-09-26T00:45:33+0300 and the answers of 00:52:41 and 00:57:59; session
  drink-atlas-workspace-6a [792d65], with session ab [539687] for
  `pipeline/embedding_run.py`). A pipeline of the backend `embedding` MAY hold the key
  `views`: the steps of the test photo; the catalogue side stays the index of the entry.
  `siglip2-p256-as-is` sends the photo as it is (`white_background`, `resize` 1024) and
  asks SAM3 nothing; `siglip2-p256-crop` cuts the photo to the SAM3 box of the package,
  with the background of the box (`segment`, `white_background`, `resize` 1024).
  `white_background` does not change an opaque photo; it keeps the 60 queries of `my`
  with transparent pixels from the transparency error. `embeddings.check_steps` (earlier
  `_steps`) takes `segment_first=False` for a test photo; `segment` stays the first step
  when present, and `remove_background` stays directly after it. `pipelines.load` refuses
  a view that the named entry does not have. 29 tests `OK` in `test_pipelines.py`, 24 in
  `test_embedding_run.py`; the full suite 708 `OK`. 6a restarted 8168 at 01:01:42 (pid
  81403; the watcher pid 81420 with `caffeinate`, pid 81659): the dialog and the filter
  list the four pipelines, each runnable. At about 01:07 the owner removed the pipeline
  `gx10-siglip2-so400m-patch16-naflex-p256` from `config.yaml`; its 2 runs count as `no
  pipeline` (owner answer of 01:19:00 to session d3), and the project test of
  `test_pipelines.py`, the rows PL2 to PL5, PL8, and PL14, and plan 34 follow.
- Plan 37, the select `Clusters` of `/testset` (owner message of 2026-09-26T00:42:25+0300
  and the answers of 00:46:18; session drink-atlas-workspace-28 [5ddfae]). It takes the
  place of the select `Wine`; the values `in a variant group` and `removed from the
  catalogue` are gone. `No`, or each embedding with a `clusters.json`: the table then
  lists only the wines in a cluster of the view `combined` that pass the other filters,
  one cluster after the other, each under a header row `<id> · <shown> of <size> wines
  shown · <signals>` with a link `open on /clusters`. The page reads `GET /api/clusters`
  at the first load and `GET /api/clusters/<name>` at the first use of an embedding; no
  server change. The address key `cluster` replaces `wine`. The stored value of the
  localStorage block of session 39 is applied after the options arrive. A browser check
  on 8168 (set `my`): 393 wines in 168 clusters, each row under the header of its
  cluster; with `Verdict` `positive` 145 wines, 44 clusters in part; the large view
  reads `wine 1 of 145`; a reload restores the choice; the link marks the same cluster
  on `/clusters`; no page error.
- Plan 36: `/testset` has two special places (owner message of 2026-09-26T00:25:00+0300
  and the answers of 00:29:00 and 00:33:55; session drink-atlas-workspace-e2 [9e7fe4]).
  The row `No Match` (`__null__`) stands first in the table again, and no filter takes it
  away. A run uses each of its photos as a `no_match` query, also with no label, as
  `scripts/match_run.py` does; `×`, the delete mark, or an exclusion takes a photo out.
  The right sidebar is now the Drawer, a new reserved place `__drawer__`: its photos wait
  for a wine, take no label (HTTP 400), and no run uses them (`build_queries` counts them
  as `drawer`). A drop onto the sidebar, a Finder drop onto the sidebar, and the key `0`
  go to the Drawer. The menu holds `Move to the Drawer` and `Move to No Match`.
  `manual_wines.RESERVED_SLUGS` holds `__drawer__`. No schema change and no data change:
  no set held a `__null__` photo. 692 tests `OK`; 23 browser checks on a copy of the
  database on the temporary port 8175 (light, dark, 390 px) pass. The server code went
  live with the restart of 8168 by drink-atlas-workspace-d3 at 00:36:23.
- The select `Slugs` of `/testset` is gone (owner message of 2026-09-26T00:39:13+0300
  and the answer of 00:39:51: remove entirely; session drink-atlas-workspace-28
  [5ddfae]). The page has no filter of the benchmark scope. An excluded row stays red,
  and `Exclude` stays. An old address with `slugs=…`, `filter=excluded`, or
  `filter=included` opens the full list and drops the key. The key `#slugsel` left
  `HEADER_IDS` of the localStorage block of session 39 in the same edit (agreed by 39).
  A browser check on 8168 gave no page error, 2105 of 2105 wines for each old address,
  and a working restore of `#marks` after a reload.
- The select `Show` of `/testset` is four filter axes now (owner message of
  2026-09-26T00:25:11+0300 and the answers of 00:26:58; session
  drink-atlas-workspace-28 [5ddfae]). `Progress` (`#filter`) holds the labelling states
  and `no candidate photos`; `Verdict` (`#verdict`) the labels; `Marks` (`#marks`) the
  comment, the agent proposal, the deletion mark, and the box; `Wine` (`#wine`) the
  variant group and `Removed`. The options `excluded from the benchmark` and `included in
  the benchmark` left the list, because `Slugs` holds the same scope; the count line
  lost its message about a contradiction of the two controls. A wine passes when it
  passes every axis. A wine with no photo in the set shows only when `Verdict`, `Marks`,
  and `Wine` stand on `any`, as before. The address keys `verdict`, `marks`, and `wine`
  are new; an old address `?filter=<value>` puts the value into its axis. A browser check
  on 8168 (set `my`) gave the same count for each of the 19 old options under the old
  and the new code. Only `pipeline/pages/testset.html` changed; the review tool (8154)
  keeps its select.
- Plan 34, the key `pipeline` of `config.yaml` (owner message of 2026-09-25T23:37:48+0300
  and the answers of 23:55:27; the messages of 2026-09-26T00:10:18 and 00:11:19 and the
  answers of 00:12:24 and 00:15:17 in the session ab; session drink-atlas-workspace-6a
  [792d65]). A pipeline is a matcher that answers a test photo with a ranked list; the
  key `embeddings` keeps the embedding models (`openai`, `local`) alone. The entry
  `vino-svoe-search-by-photo` (backend `svoe-vino-ru`) moved to `pipeline`, and a new
  pipeline `gx10-siglip2-so400m-patch16-naflex-p256` of the new backend `embedding`
  names the embedding entry of the same name. The new module
  `pipeline/pipelines.py` reads the key; the remote matcher code left
  `pipeline/embeddings.py`, and `embeddings.read_config` and `check_entries` serve both
  keys. The dialog `Run>` of `/testset` and the filter `Pipeline` of `/runs` show the
  pipelines alone; the filter shows no entry of `embeddings` and no item `(not a
  pipeline)`, and a run of another name counts as `no pipeline`. A pipeline of the
  backend `embedding` with no index is disabled with `no index: build it on /embedding`,
  and its job runs with `embedding_python`. `/embedding` and `/clusters` show the
  embedding models alone; the remote branch of `embedding.html` is gone. The owner
  removed `mock` from `config.yaml` at 00:25 and asked at 00:26:27 to remove it from the
  source: the backend `mock`, `pipeline/mock_run.py`, `tests/test_mock_run.py`, and
  `build_embeddings.MockBackend` are gone. Its 2 runs stay in `runs/` under `no pipeline`;
  session ab deleted `data/embeddings/mock/` (owner answer of 00:29:55). The routes, the
  JSON keys, and the key `configuration` of `run.json` keep their names, so the old runs
  keep their filter value. New `tests/test_pipelines.py`; 18, 14, 13, and 7 tests `OK` in
  `test_pipelines.py`, `test_run_jobs.py`, `test_remote_run.py`, and
  `test_run_routes.py`. At 00:08 a run of the dialog failed with
  `config.yaml has no pipeline vino-svoe-search-by-photo`: the old server started the new
  `run_job.py` 13 s before `config.yaml` got the key `pipeline`.
- An embedding run is a run of a pipeline (owner messages of 2026-09-26T00:10:18 and
  00:11:19, answers of 00:12:24 and 00:15:17; session drink-atlas-workspace-ab [539687],
  with plan 34 of session drink-atlas-workspace-6a [792d65]). `pipeline/embedding_run.py
  --name` takes a pipeline of the backend `embedding`: its key `embedding` names an entry
  of `embeddings:`. The new `build_pipeline_backend(pipeline, config_path)` gives the
  backend the pipeline name and `spec["embedding"]`; `run_job.build` of 6a calls it, so the
  dialog `Run>` starts the pipeline. `config.yaml` holds one such pipeline,
  `gx10-siglip2-so400m-patch16-naflex-p256`, with the name of its embedding entry, so the
  2 runs of 2026-09-25 keep their `run.json`. 19 tests `OK` in
  `tests/test_embedding_run.py`. After the restart of 8168 at 00:36:23 (session d3),
  the dialog and the filter of `/runs` list the 2 pipelines alone, and
  `GET /api/run-inputs` answers the model inputs of an embedding run.
- `/runs`: the candidate cards of one photo row have one height, the height of the
  tallest card of the row (owner message of 2026-09-26T00:12:24+0300). In a row with a
  cluster frame, a card outside a frame starts where the cards of the frame start
  (`margin-top: 19px`). `evenCards` of `pipeline/pages/runs.html` sets the heights after
  each batch of rows; a long slug is not cut. The server reads the page on each request,
  so no restart was necessary. A headless screenshot showed level rows.
- Plan 35, more than one VLM request at the same time (owner message of
  2026-09-25T23:44:31+0300 and the answers of 23:58:53; session drink-atlas-workspace-d3
  [4920ce]). `pipeline/describe_images.py` runs up to `image_description.workers` calls at
  the same time in a thread pool (1 when absent; `config.yaml` sets 8). The main thread
  alone takes the images, and it never takes an image that a call holds. A failure of the
  service stops the new calls for the backoff time; the calls that run finish and are
  stored; a failure during the backoff does not double it. The speed on the pill of
  `/dataset` is now the wall time per image of the last 20 images (the rate of the
  backlog), not the time of one call. The start line of the log names `workers`. 8 new
  tests (`WorkersSettingsTest`, `WorkersTest`); 692 tests `OK`. The key entered
  `config.yaml` with the restart of 8168 at 00:36:23, because the old server refused an
  unknown key of `image_description`. Live: 26.5 details per minute instead of 3.4, with
  the same call time (mean 16.0 s, maximum 32.5 s); the pill read `VLM details 494 /
  2,018 · 2.1 s`. The one timeout of the first 6 minutes was a stuck request; the next
  call of the image gave a valid answer.
- Plan 33, the runner of the embedding configurations (owner message of
  2026-09-25T23:19:28+0300 and the answers of 23:24:20 and 23:35:19; session
  drink-atlas-workspace-ab [539687]). New `pipeline/embedding_run.py --name <name> --set
  <set>` for an entry of the backend `openai` or `local` with an index. Each photo gets
  the package cut of `derive.derive_image` and the label cut of the new
  `alternatives.label_cut_of` in memory, then the steps of each view with the new
  `embeddings.apply_steps` (the step loop of `prepare`), so a test photo gets the pixels
  of a catalogue image. One request to the endpoint of the entry gives the vectors. The
  score of a wine is the mean of its best cosine in each view, over the current items of
  the index. `benchmark.run_benchmark` writes the run; `run.json` holds `kind:
  embedding`. `GET /api/run-inputs` makes the model inputs of such a run again from the
  steps of `run.json` and the SAM3 cache; it takes effect with the next restart of 8168.
  The dialog `Run>` does not start these runs (owner answer of 23:55:27 to session 6a).
  16 new tests; 673 tests `OK` at 2026-09-25 23:50. The live check on `official-real-photos` with
  `gx10-siglip2-so400m-patch16-naflex-p256`: recall@1 0.525 and recall@5 0.712 of 59
  positive photos; 15 of the 16 misses are photos of 10 wines with no catalogue image.
  Read `ResearchLog.md` of 2026-09-26.
- The dialog `Import from vino-svoe.ru` of `/dataset` shows the pixel size (width ×
  height) under each image of a main image conflict, on the `database` side and on the
  `website` side (owner message of 2026-09-25T23:58:00+0300 and the answers of
  2026-09-26T00:00:30; session drink-atlas-workspace-43 [c33611]). The browser reads
  the size from the loaded original file, so the diff and the server do not change.
  The other rows of the dialog show no size. Only `pipeline/pages/website_import.js`
  changed; the server reads it on each request, so no restart was necessary. A
  headless check on 8168 showed 6 sizes for the 6 images of the 3 image conflicts,
  and each size equals the pixel size of its file.

## 2026-09-25

- Each entry of `vlm` in `config.yaml` MAY hold `max_tokens`, 8192 when absent (owner
  message of 2026-09-25T23:21:25+0300 and answers after it; session
  drink-atlas-workspace-15 [40dc83]). It is the `max_tokens` of a detail request of
  `pipeline/describe_images.py` and replaces `image_description.detail_max_tokens`
  (4096), which `config.yaml` no longer holds; a configuration that still holds it gets
  an error that names the replacement. A class request keeps 300, so the saved class
  answers and `Raw VLM reply` stay valid. `scripts/cluster_rules.py` and
  `scripts/04_verify.py` keep their own limits. 657 tests `OK`. 8168 was restarted at
  23:28:25. The one failed detail (`e049e469…`) was sent again at 8192: it ended in the
  timeout of 300 s two times, and a timeout is not counted, so the image blocked the
  detail queue. Its `vlm_attempts` was set back to 3 at about 23:35, and the queue went on at
  23:41:09. Read the ResearchLog entry of the same date.
- A click on `N details failed` in the VLM pill of `/dataset` opens the dialog `Failed
  details`, and the lab server hides `Validate` (owner messages of
  2026-09-25T22:49:56+0300 and 22:51:31, answers of 22:54:00; session
  drink-atlas-workspace-15 [40dc83]). The new route `GET /api/image-detail-failures`
  (`image_descriptions.detail_failures`, `image_details.failed`) sends each image whose
  detail failed `max_attempts` times with its present inputs: the slug, the file that the
  VLM got, the prompt kind, the type, the attempts, the time, `vlm_error`, and the last 20
  entries of `work/describe_images.log` that name the image, each with the lines that
  follow it (the text of a cut answer). The pill writes a new HTML only when its HTML
  changes, so the button keeps the focus during the 5 s poll. `Validate` shows only when
  `GET /api/dataset` has no `database_file`, so the review tool (8154) keeps it; the website
  import covers its checks on 8168. 652 tests `OK`. A headless check in the light and the
  dark theme found no script error: 1 failure with 4 log entries, `Escape` closes the
  dialog, the button kept the focus for 11 s, and `Validate` shows without
  `database_file`. 8168 was restarted at 23:05:37. A click on the thumbnail shows the
  file alone in the image preview, above the dialog (owner message of 23:20:22); the page
  path stays, and a Cmd-click still opens the file in a new tab.
- `/testset` has the button `Run>` (plan 32). Its dialog lists every configuration of
  `config.yaml` with the count of the queries of the set; `vino-svoe-search-by-photo`
  and `mock` can start, and the embedding configurations are disabled with
  `no runner yet`. The fields `first N queries` and `workers` are optional. `Start`
  runs the new `pipeline/run_job.py` as a separate process (one JSON event on each line
  in `work/run-jobs/<configuration>/job.log`), and a job row under the header shows the
  state, a bar, done / total, the errors, the elapsed time, `(x)` to stop, and
  `open run` for 60 s after the end. New `pipeline/run_jobs.py` answers
  `/api/run-configurations` and `/api/run-jobs`. Owner message of
  2026-09-25T22:41:00+0300 and answers of 22:46:00; session drink-atlas-workspace-5c
  [cbb143]. 14 new tests in `tests/test_run_jobs.py`; 648 tests `OK`. 8168 restarted at
  22:56:54 (pid 14874); `caffeinate -ims -w 14904` (pid 15258) holds the new watcher of
  plan 29, and its row in `GPU_TASKS.md` names the new pids. A live job of 5 photos of
  `official-real-photos` ended `done`. `README.md`, `SMOKE_TESTS.md` RJ1 to RJ10.
- The first full run of `vino-svoe-search-by-photo`: the set `official-real-photos` (the
  owner chose it as the provided test set, answer of 22:36:00), 80 queries, 4 workers,
  `runs/2026-09-25T193223Z-lab-vino-svoe-search-by-photo-official-real-photos/`. All 80
  answers HTTP 201. Positive (59): recall@1 0.576, recall@5 0.932, recall@10 0.966, MRR
  0.746. Negative (21): 4 false matches at rank 1. The median latency was 9.2 s (the
  maximum 15.7 s); on 2026-09-17 it was 2.4 s at 1 worker on the set `my`. The cause is
  not known.
- The patch button of `/dataset` is the red `Clear`, and the GTIN input accepts at most
  14 characters (owner messages of 2026-09-25T22:46:27+0300 and 22:47:19; session
  drink-atlas-workspace-3b [d30290]). Only `pipeline/pages/dataset.html` changed. The
  former `Remove` button has the label `Clear` and the colour `--exc` in both themes. On
  the lab server one press sends the `DELETE` at once, with no `Apply`; the editor shows
  `Clearing…` until the answer. The review tool on 8154 keeps the staged removal with
  `Apply` and `Cancel`. The GTIN input had `maxlength="32"`; now it has 14. A browser check
  in the light and the dark theme with a mocked `DELETE` found no script error, and the
  button keeps its size of 77 × 24 px. The server reads the page for each request, so
  8168 was not restarted.
- The bottle cards of `/clusters` have the form of the cards of `/clusters` on 8154
  (owner message of 2026-09-25T22:37:15+0300, answers of 22:41:15; session
  drink-atlas-workspace-a9 [79efd8]). Only `pipeline/pages/clusters.html` changed. A card
  is 176 px wide, and the cards wrap in a row. The card shows a badge `#N` on one
  162×200 image, the name, `producer · category`, the grapes, and the slug. The colour,
  the region, and the view tag on the image are not on the card. The search still finds
  the colour and the region. A new select `Image` (`full`, `label`) chooses the image in
  the space `combined`. The address keeps a `label` choice as `image=label`. In the
  spaces `full` and `label`, the select is disabled and shows the view of the space.
  The owner chose the layout alone: the photo counts, the links `review` and
  `vino-svoe.ru`, and `label description` of 8154 are not on the card. The lab rules
  have no card letters, so the badge has no letter. The server reads the page for each
  request, so 8168 was not restarted. The 21 cluster tests and the 59 lab server tests
  pass. A browser check in the dark and the light theme and at 390 px found no script
  error.
- The owner stopped the work of all sessions in `ACTIVE_WORK.md` (owner message of
  2026-09-25T22:03:25+0300, answer "Stop everything now" of 22:05:09; session
  drink-atlas-workspace-27 [fa998d]). All 25 sections were removed. 22 sessions were stale
  (not in `ListAgents`). The live sessions drink-atlas-workspace-cb [48de03],
  drink-atlas-workspace-a7 [bbd3b6], and drink-atlas-workspace-5c [cbb143] got a stop
  message at 22:05. The uncommitted files of the sessions stay in the tree. A copy of the
  file before the change is `work/ACTIVE_WORK-stopped-2026-09-25T2206.md`.
- Image details, stage 2 of the watcher `describe_images.py` (plan 29, owner message of
  2026-09-25T19:14:31+0300, answers of 20:24:17, approval of 20:28:51, answer of
  21:45:41; session drink-atlas-workspace-a7 [bbd3b6]). When no image waits for a class
  and `image_description.details` is true, the watcher sends the detail prompt of the
  owner with the cut of the next eligible image and stores the valid answer in the new
  table `image_detail` (schema `020_image_detail.sql`, new `pipeline/image_details.py`).
  A `full_package` image gets the package prompt with its `package` cut; the word
  `bottle` becomes the name of the `package_type`, also in the last key. A
  `label_closeup` image gets the label prompt with its `label` cut. `multiple_packages`,
  `unknown` scopes, and the types `other` and `unknown` get no detail. The request sends
  the JSON Schema of the answer (`response_format: json_schema`, strict), a long side of
  1,536, and `max_tokens` 4,096; the code checks the same schema, and `finish_reason:
  length` is a failure. A row stores its inputs (`prompt_kind`, `package_type`,
  `input_sha256`); a change makes it stale. New option `--detail-sha`; `--retry-failed`
  also resets the details. `watcher_status` adds `stage` and the `details_*` counts; the
  pill of `/dataset` shows `VLM details <done> / <eligible>`. `config.yaml`: `details`,
  `detail_max_side`, `detail_max_tokens`. `data/lab.sqlite3` at version 20 since 22:00
  (backup `data/backups/lab-before-020-20260925T220038.sqlite3`). 8168 was down at 21:56
  (not stopped by this session); started at 22:00:54 with `/opt/homebrew/bin/python3`
  (5c and cb agreed). The backlog of 2,015 images runs since 22:00:53 (watcher pid
  59886, `caffeinate` pid 60168). 634 tests `OK`. Live checks and the key drift of the
  package prompt with `json_object` (3 of 4) are in `ResearchLog.md`. Docs: `README.md`
  (section "The image details"), `COMMANDS.md`, `SMOKE_TESTS.md` DT1 to DT8, plan 26
  (note), plan 29.
- The lab configuration `vino-svoe-search-by-photo` of `config.yaml` (`backend:
  svoe-vino-ru`) is the official recognizer of vino-svoe.ru,
  `https://api.vino-svoe.ru/v1/wines/search-by-photo`. The new script
  `pipeline/remote_run.py --name <name> --set <set>` sends each photo of the test set to
  the API as it is and writes a run with `configuration: <name>`; `/runs` shows it under
  the filter `Configuration`. The request keys of the entry have the meaning of the keys
  of `backends.yaml`. `pipeline/embeddings.py` accepts the backend with zero items;
  `Build` refuses it (HTTP 400), and `/embedding` hides `Build`, `Stop`, and `Log` and
  shows the command of a run. The large view of `/runs` states that a remote run has no
  model input, in place of the HTTP 422 "more than one configuration matches". Owner
  message of 2026-09-25T20:36:26+0300 and answers of 20:39:30; session
  drink-atlas-workspace-5c [cbb143]. A smoke run of 3 photos (`--label smoke`) answered
  HTTP 201 with 10 candidates for each photo. 15 new tests in `tests/test_remote_run.py`.
  Live on 8168 since the restart of a7 [bbd3b6] at 22:00:54. Plan 31, `README.md`,
  `COMMANDS.md`, `SMOKE_TESTS.md` RM1 to RM10.
- The owner dropped two waiting tasks (owner message of 2026-09-25T21:52:00+0300); their
  sections left `ACTIVE_WORK.md`:
  - drink-atlas-workspace-7e: the review of `docs/database-structure.pdf`. The page and
    its source `docs/database-structure.html` stay in the repository. They show schema
    version 17, not 19: `image_description` (018), `test_wine_note`, and the new columns
    of `test_photo` and `test_set` (019) are not in them.
  - drink-atlas-workspace-30: the restart of the review tool on 8154. The change is
    committed in `svoe-vino-testset`, but the running tool still shows the sort option
    `catalog.jsonl order` on its dataset page until its next start.
- The label cut (`alternatives.label_derivatives`, `image_derivative` kind `label`): a
  photo with a second body label gets the crop to the box around the labels, with no
  mask, not the segment of the largest label. A second label counts when its centre is on
  the largest bottle, less than 80 % of it lies inside the main label, and it has at
  least 25 % of the area and 60 % of the width of the main label (`body_labels`). Neck
  labels, capsules, and parts of the main label do not count. Owner messages of
  2026-09-25T19:10:14+0300 and 19:10:30, answers of 19:16:44 and 20:24:14; session
  drink-atlas-workspace-cb [48de03]. `seed_label_cuts.py` made each label cut again
  (20:30:00 to 20:53:39): 111 `crop`, 1,910 `seg` with the same file, 4 with no label.
  No embedding rebuild (owner choice): the `label` items of these 111 cuts are stale
  until the next `Build`. Backup of the database before the run in the scratchpad of the
  session. 591 tests `OK`. Plan 22 (note), `SMOKE_TESTS.md` EB44 to EB47, `ResearchLog.md`.
- `/clusters` is enabled for the lab database. Each configured embedding keeps its own
  `clusters.json` and `cluster-notes.json` in `data/embeddings/<name>/`. The builder
  uses the effective main image and every applicable additional image. It keeps `full`
  and `label` vectors in separate spaces and gives a `combined` union view. Each edge
  records the image pair with the highest cosine. The page builds the artifact, shows
  exact edge evidence and stale status, filters the three views, previews prepared
  images, and writes reviewer notes. The initial thresholds are `0.95` and `0.95`.
  Plan 30. Owner selected option 1 on 2026-09-25. The current NaFlex build gives 147
  full clusters over 334 wines, 108 label clusters over 244 wines, and 168 combined
  clusters over 397 wines. The final 21 cluster tests and two build-command tests pass.
  All 59 lab-server tests and the then-current 591-test project suite passed before the
  concurrent plan 29 edits. The page passed a live browser check in `combined` and
  `label`; the browser reported no warning or error. Port 8168 was restarted with
  SIGTERM and answered HTTP 200 for `/api/dataset` and `/clusters`.
- `/dataset`: the select `Package` of `Advanced Filters:` lists only the `package_type`
  values that at least one wine has (the patched image, else the main image), and `not
  described` only when a wine has no value. A save in the description dialog builds the
  list again; the chosen value stays. Owner message of 2026-09-25T19:07:49+0300 and the
  answers of 19:09:07; session drink-atlas-workspace-cb [48de03]. Checked on 8168 in
  headless Chromium: `bottle`, `can`, `tetra_pak`, `box`, `not described`, no page error.
  No restart: the page is read from disk. `SMOKE_TESTS.md` ID21, ID22.
- `/testset` and `/runs`: the plan 24 follow-ups of drink-atlas-workspace-ca [a2daf6]
  (owner messages of 2026-09-25T18:04:02+0300, 18:04:22, 18:05:36, 18:05:49, and the
  answers of 18:05:36), which stopped before its tests ended and before its docs:
  - `/testset`: the set combobox in the title; the right sidebar is the NULL place and
    the NULL row leaves the table; a drag moves a photo to the sidebar or back to a wine
    (new route `POST /api/testset-move`, `testsets.move_photo`); a move clears the label,
    keeps the comment, the box, the delete mark, and the proposal, sets `moved_from`, and
    gives a clashing name the suffix `_moved<N>`; no file moves.
  - `pipeline/benchmark.py`: a NULL photo is a `no match` query only with the label
    `positive`. The docstring now states this rule.
  - `/runs`: the filter `Configuration` in the header after `Match runs`; pages of the
    runs table (25, 50, 100, or all; the browser keeps the size).
  - Checked by TESTSET [0fe970] (owner message of 18:13:00) in headless Chromium, with
    each write answered by the real route code on a copy of the database; the live
    database did not change. The move was also checked on a copy with SQL.
  - Four page fixes of TESTSET [0fe970] in `pipeline/pages/testset.html`: the line after
    the combobox and the combobox count each photo of the set (the sidebar too) and are
    drawn again after each write (new `headSub`); the time of the last edit moved from the
    title to the stats line and follows each write (new `localStamp`; `post`, the end of
    `uploadFiles`, and `saveWineNote`), so the navigation stays in the title row; the
    large view of a NULL photo reads `the NULL place (sidebar)` and `confirmed: no card of
    the catalogue shows this wine`; the wine position no longer counts the NULL place.
  - `tests/test_mock_run.py`: the fixture NULL photo gets `positive`, as the new rule
    asks; all 559 tests pass.
  - Docs: `README.md`, `SMOKE_TESTS.md` TP3, TP4, TP18 to TP23, RN14 to RN17, plan 24
    ("Changes after the approval"), plan 23 (one item).
- `/testset`: a drop of image files from the macOS Finder onto the sidebar (the NULL
  place) or onto a wine row stores each file in that place with no label. New route
  `POST /api/testset-upload` and `testsets.upload_photo`. A new image keeps its Finder
  name (`_upload<N>` on a clash); an image that the set holds already keeps its file name
  of the set, the same place refuses it (HTTP 409), and another place takes it. JPEG,
  PNG, WebP, GIF, and BMP of at most 20 MB; HEIC is refused. A file dropped outside a
  target no longer opens in the tab. Owner message of 2026-09-25T18:19:01+0300 and the
  answers of 18:25:10; session drink-atlas-workspace-cb [48de03]. 565 tests `OK`; the
  drops checked in headless Chromium on a fixture database. 8168 restarted with SIGTERM
  at 18:34:39 (new watcher pid 21744 with `caffeinate`). `README.md`, `SMOKE_TESTS.md`
  TP13 to TP17, plan 24.
- `/dataset`, plan 26 additions of drink-atlas-workspace-99 (owner messages of about
  17:58 and 18:00): the block `Raw VLM reply` in the dialog `Image description` (new
  route `GET /api/image-description-reply?sha256=`, new `describe_images.cached_reply`),
  and the button `Advanced Filters:` with the filter `Package` (the patched image
  decides, else the main image). 99 stopped before its docs; TESTSET [0fe970] checked
  both features read-only on 8168 (owner message of 18:13:00): 1,683 of 1,683
  VLM-filled images answer `found: true`, the error codes are 400 and 404, the counts of
  `Package` agree with SQL for all 2,104 wines, and at 390 px no feature adds a
  horizontal scroll. `test_describe_images.py` 24 and `test_lab_server.py` 58 tests pass.
  A save in the dialog does not apply the `Package` filter again (as for `Show`).
  `README.md`, `SMOKE_TESTS.md` ID14 to ID20, plan 26.
- Plan 28, `pipeline/seed_from_testset.py`: one command builds the lab database again
  from `svoe-vino-testset` and its sources (tables, catalogue, main images, patches,
  GTINs and QR URLs, Atlas Core bindings, the three test sets, label cuts), backs up the
  old database to `data/backups/`, and swaps the new one in. Owner message of
  2026-09-25T17:46:51+0300 and the answers of 17:52:00 (full rebuild and swap; label
  cuts always). Written by drink-atlas-workspace-c5 [7cabb3], which stopped before its
  test run ended; the docs by TESTSET [0fe970] (owner message of 18:13:00). The 10 tests
  pass. The test run of c5 reached step 8: `data/lab-test.sqlite3.seeding` holds steps
  1 to 7. The full test run is not done: it asks SAM3 on gx10 about 1,660 times, and 8
  embedding builds used gx10. `README.md`, `COMMANDS.md`, `SMOKE_TESTS.md` (section SD),
  plan 28 (section "The state on 2026-09-25").
- `/embedding`: each running job row ends with a button `(x)` that stops the build of
  that row with `POST /api/embeddings/<name>/stop` (the route of the `Stop` button), also
  when the `Configuration` combobox selects another entry. A `stopping` row keeps a
  disabled `(x)`. Owner message of 2026-09-25T18:16:00+0300; session TESTSET [0fe970].
  `pipeline/pages/embedding.html`: the `.job` grid gets one column, new `.job-stop` CSS,
  the button in `showJobs`, new `stopJob`, one click listener on `#jobs`. Checked in
  headless Chromium on 8168 with a fake job list and every POST answered in the browser,
  so no real build stopped: dark and light theme at 1,440 px, light at 390 px; one click
  sent one stop request for the row. The page needs no restart. `SMOKE_TESTS.md` EB41 to
  EB43, `README.md`.
- The indicator of the image description watcher on `/dataset` (owner message of
  17:32:17, answers of 17:33:57): the pill left of `Add wine` shows working (described of
  linked, the speed), idle, waiting (the error), or stopped, and the failed count. The
  watcher writes `work/describe_images.status.json` at each step (`describe_images.Status`);
  the new route `GET /api/image-description-status` reads it, checks the pid, and adds the
  counts (`image_descriptions.watcher_status`). The page asks every 5 s while its tab is
  visible. 15 new tests; all 512 tests pass. Checked in headless Chromium in both themes
  and at 390 px, with the live state and three faked states. 8168 restarted at 17:38:45
  (watcher pid 66779, `caffeinate` on it).

- The header of `/embedding` has two rows instead of three (owner message of 17:30). The
  summary line `N of M wines · … items · current … · stale … · missing … · failed …`
  after the title `Embeddings` is gone; the row `Items` of the source panel still shows
  the counts, with the failed count in red. The bar `Configuration`, `Build`, `Stop`,
  `Log`, and the message of the last build moved into the first row, between the title
  and the navigation. `pipeline/pages/embedding.html` alone (the `.head` CSS, the header
  markup, `render`). Tested in headless Chromium on 8168: two rows at 1,440 px, no page
  error, the `Show` filter and `Search` work. A window narrower than about 1,410 px puts
  the navigation in its own row. No restart was necessary.
- The dialog `Import from vino-svoe.ru` on `/dataset` (owner message of 17:19): each row
  of `Missing on the website` shows a red prohibition sign (a circle with a diagonal bar)
  on top of the wine image, or on top of the empty box when the wine has no image. The
  sign is an inline SVG in `pipeline/pages/website_import.js` (`MISSING_SIGN`,
  `changeHtml`). It has `pointer-events: none`, so a click on it opens the large view of
  the image and does not change the checkbox. Tested in headless Chromium on 8168 in light
  and dark mode: 71 of 71 rows have the sign, and the 27 checks of the dialog still pass.
  No restart was necessary.
- Plan 24, the Testset page on the lab database (owner messages of 16:57:18 and 17:10:55,
  answers of 17:01:44 to 17:26:22; taken over from TESTSET [0fe970]). The page is
  `/testset`; `GET /` redirects to `/dataset`. The database is the source of the labels.
  - Schema `019_testset_page.sql` (entered and migrated at 17:37:35; a backup of version
    18 is in the scratchpad of the session): `test_photo` built again with each field of a
    label entry (`comment`, `ts`, `proposed`, `proposed_by`, `confidence`, `source_url`,
    `moved_from`, `copied_from`, `reassign_to`, `prefilled_from`, `extra`) and the box of
    the main object (`box_left` to `box_bottom`); new table `test_wine_note`;
    `test_set.edited_at` and `test_set.label_note`.
  - `pipeline/import_testset.py` and `import_testsets.py` keep each field, the notes of a
    whole wine, and the text `note`. A value that its column cannot keep exactly goes into
    `extra`. The import refuses a set with a page edit, unless `--force`. The three sets
    were imported again at about 17:38.
  - New `pipeline/export_testset.py`: `review-labels.json` and `excluded-slugs.json` of one
    set from the database. The round trip (import, then export) on the three sets gave the
    same `labels`, `wines`, excluded slugs, `note`, and `counts` as the source files.
  - New `pipeline/testsets.py` (the reads and the writes) and `pipeline/testset_routes.py`
    (`GET /api/testset`, `POST /api/testset-label`, `-delete`, `-comment`, `-box`,
    `-wine-note`, `-exclude`). New page `pipeline/pages/testset.html`: a port of the old
    Testset page with the labels, the delete mark, the comments, the wine notes, the
    exclusions, the 13 sorts, the filters, the large view, a set selector, the badges
    `Removed`, `Disabled`, and `not in catalogue`, and the box drawing (`b`). The move,
    the copy, the upload, the sideboard, the checks, and the group editor are not there.
  - `pipeline/lab_server.py`: `testset_routes` delegation, `/` redirect, `NAV` link
    `/testset`, `/` out of `DISABLED_PAGES`. The Testset link of `dataset.html`,
    `embedding.html`, and `runs.html` leads to `/testset`.
  - `pipeline/benchmark.py`: `build_queries` leaves out the photos of a `Removed` wine
    ("removed wine") until a restore (owner answer of 17:13:17).
  - Tests: new `tests/test_testsets.py` (13), `tests/test_testset_routes.py` (5),
    `tests/test_export_testset.py` (6); 4 new tests in `tests/test_import_testset.py`, 1 in
    `tests/test_benchmark.py`, 2 in `tests/test_lab_server.py`; `tests/test_labdb.py` at
    version 19. All 539 tests pass. Checked in headless Chromium on a copy of the database
    on port 8174: 36 checks pass, in the light and the dark theme and at 390 px.
  - 8168 was restarted at 17:55:56 (SIGTERM; server pid 16219, watcher pid 16234, and a
    new `caffeinate -ims -w 16234`). Port 8174 is recorded in `PORTS_USED.md` as a
    temporary test copy; it is stopped.
  - New draft `docs/plans/27_main-item-iou.md`: the IoU of the box in the run validator
    (owner answers of 17:23:18).
- New `tests/test_testset_retention.py` (owner message of 17:10:55, answer of 17:13:17):
  a wine that is in a test set keeps its rows of `test_set`, `test_photo`,
  `test_excluded`, `test_variant`, and `image` when a person removes it
  (`lab_server.change_state`) and when the catalogue import removes it, and has them again
  after a restore. The rule already held; the 4 tests guard it. No production code changed.
  The rules for the Testset page and the benchmark (a `Removed` wine with photos shows with
  a `Removed` badge; the benchmark skips its photos as "removed wine" until a restore) are
  part of plan 24 (the entry above).
- Plan 26, the image descriptions (owner messages of 16:31 to 16:48, approved at
  16:48:07). New table `image_description` (schema `018_image_description.sql`; the
  database is at version 18 since 17:00:57): `package_type`, `subject_scope` (with
  `multiple_packages`), `package_view`, `content_roles`, and `created_by` (`manual` or
  `vlm`) with `vlm_at`, `vlm_name`, `vlm_model`, `vlm_answer`, `vlm_error`, `vlm_attempts`.
  - New `pipeline/image_descriptions.py` (the table) and `pipeline/describe_images.py`
    (the watcher). The watcher sends each linked image with no VLM fill to
    `qwen3.5-9b-nvfp4`, with the values that are set as fixed facts in the prompt. It checks
    the answer against the JSON Schema `ANSWER_SCHEMA` with `jsonschema`, and fills only
    the values that are not set (`COALESCE`). A valid answer goes into `model_cache`; an
    answer that fails the schema writes nothing.
  - `pipeline/lab_server.py`: `POST /api/image-description`, the keys
    `image_descriptions` and `image_description_values` of `/api/dataset`, and the start
    and stop of the watcher in `main` when `image_description.watch` is true. A SIGTERM now
    ends the server through its `finally` block, so the watcher stops too.
  - `/dataset`: a button `✎` in the bottom right corner of the main image, the patch
    image, and each alternative photo opens the editor of that image.
  - The check of the owner: `package_type` set by hand to `tetra_pak` and `can` for the
    main images of `soyuz-vino-soyuz-vino-evropak-shiraz-krasnoe-polusladkoe-11` and
    `abrau-dyurso-fizz-beloe-bryut`; after the VLM run both values stayed, and the other
    three values were filled. On a scratch copy of the database, a wrong preset `keg` stayed
    while the VLM answered `bottle`.
  - 33 new tests; all 497 tests pass. 8168 was restarted at 17:01:08 (schema 18, no
    watcher) and at 17:07:33 (with the watcher). The backlog of about 2,020 images runs
    since 17:07.
- `pipeline/vlm_config.py`: the key `key` of a `vlm` entry is optional now; absent means
  no key. The three gx10 entries of `config.yaml` lost their `key: null` between 16:23
  and 16:54 (not by this session); `config.old.yaml` follows, so the two sections stay equal.
  The owner confirmed the rule at 2026-09-25T17:11:35+0300: a missing `key` is not set, and it is null.

- Owner messages of about 16:00 and 16:11 and the answers of about 16:05 and 16:09: the key
  `vlm` in `config.yaml` and in `config.old.yaml` holds the named VLM inferences. An
  entry holds `name`, `protocol` (`openai`), `thinking_field` (`chat_template_kwargs` or
  `top_level`), `endpoint`, `model`, and `key` (`null` or `{env:NAME}`; a key value is
  refused). The new `pipeline/vlm_config.py` reads it.
  - Six entries: `qwen3.5-9b-nvfp4` (the owner request), `qwen3.5-9b`, and `qwen3-vl-32b`
    of gx10; `qwencloud-qwen3.8-max` (the owner request) and `qwencloud-qwen3.8-flash` of
    the QwenCloud Token Plan with `{env:QWENCLOUD_TOKEN_PLAN_API_KEY}`;
    `dashscope-qwen3.7-flash` with `{env:QWENCLOUD_PAYGO_API_KEY}`.
  - `scripts/04_verify.py`: the built-in backends `local`, `tokenplan`, and `dashscope`
    are gone. `--backends` names `vlm` entries; the default is `qwen3-vl-32b:12`, the
    model of the old `local`. The column `candidates.vlm_model` now gets the entry
    name. The two cloud entries read the variables of `CREDENTIALS.md`, not the old
    `QWEN_API_KEY` and `DASHSCOPE_API_KEY`.
  - `scripts/cluster_rules.py`: `cluster_rules.vlm` (default `qwen3.5-9b`) and
    `cluster_rules.rules_vlm` (default: the entry of stage 1) replace `url`, `model`,
    `rules_url`, `rules_model`, `rules_api`, and `rules_key_env`, and the old keys are
    refused. `config.old.yaml` names `qwen3.5-9b` and `qwencloud-qwen3.8-max`, the same
    models as before. The chat URLs and the payloads stay the same, so the keys of
    `model_cache` do not change.
  - New `tests/test_vlm_config.py` (19 tests). All 464 tests pass. One live request to
    `qwen3.5-9b-nvfp4` gave HTTP 200 with the right JSON and no reasoning text.

- Owner messages of about 15:40 and 15:45 and the answers of 15:55: the dialog
  `Import from vino-svoe.ru` on `/dataset` (`pipeline/pages/website_import.js`, taken over
  from the stale session drink-atlas-workspace-ff with the permission of the owner).
  - One card holds all conflicts of one wine. The heading states the conflicts and the
    wines, for example `12 · 9 wines`. A card stays marked until each of its conflicts
    has a choice.
  - Each wine slug links to `https://vino-svoe.ru/wines/<slug>` in a new tab. A row of
    `Missing on the website` keeps the slug as plain text: the website has no page.
  - A click on an image shows a large view with the file name. Esc or a click closes
    it. The click changes neither the checkbox nor the radio button.
  - New section titles: `New wines on website`, and `Missing main images, taken from
    website` with the hint "The database has no main image for these wines. Apply
    stores the website image as the main image."
  - A long section hint wraps next to its title, or below it on a narrow screen.
  - Checked in headless Chromium on 8168 (run `20260925T125132`), both themes and
    390 px. Nothing was applied. The lab server reads the file on each request: no
    restart. New smoke tests IW13 to IW15.
- Owner message of 15:43:34 and the answer "Both pages": the `Sort` control of
  `/dataset` has no option `catalog.jsonl order` now. The default sort is
  `wine name A–Z`. `pipeline/pages/dataset.html` lost the option and its line in the
  sort code. The size and change-time sorts still use the catalogue order as the tie
  break. The same change is in the dataset page of the `svoe-vino-testset` review tool.
- Owner messages of 13:45:11, 13:47:30, and 13:51:48: the cache of the model calls
  (plan 25, `docs/plans/25_model-call-cache.md`). A call to SAM3, Grounding DINO, or a
  VLM that repeats an earlier successful call reads its answer from `data/cache/` and
  sends no request.
  - New `pipeline/model_cache.py`. The key is the sha256 of the request fields: the full
    endpoint URL, the served model name, the parameters, the prompt, and the sha256 of each
    sent image (the copy after the resize). One JSON file for each call:
    `data/cache/<model>/<key[0:2]>/<key>.json`. It holds the request fields, the time, the
    duration, and the answer; no image, no key. A success alone is stored. A write goes
    through a temporary file and `os.replace`. A record has the mode
    0644 (`mkstemp` made it 0600 before the fix of about 15:24).
  - `pipeline/derive.py`: `Sam3Client._post` does the lookup and the store; the retry loop
    moved unchanged into `_send`. So each SAM3 caller of `pipeline/` uses the cache.
    Agreed with drink-atlas-workspace-8b and drink-atlas-workspace-7b.
  - New `pipeline/gdino.py`: `GdinoClient` for `grounding-dino-base`, `mm-gdino-base`, and
    `mm-gdino-base-all` of the gx10 gateway, with a command line that states `hit` or
    `miss`.
  - The VLM calls of `scripts/cluster_rules.py` (`Vlm.ask`, new counter `hits`),
    `scripts/04_verify.py` (`Backend.ask`), and `scripts/bench_vlm_models.py` (`call`, a
    cached line holds `"cached": true`) use the cache. A VLM answer is stored when it holds
    a choice. A cached `Vlm.ask` needs no API key.
  - Tests: new `tests/test_model_cache.py` (12), new `tests/test_gdino.py` (4), one new
    test and a `setUpModule` in `tests/test_derive.py` (17). All 445 tests pass. No test
    writes into `data/cache/`. 12 live cases against gx10 pass: SAM3 miss then hit (494 ms,
    then 14 ms), other nouns, a hit with no network, a failure that is not stored, two
    processes on one key, GDINO miss then hit (9,667 ms cold, then 18 ms), another GDINO
    model and threshold, and VLM miss then hit for `cluster_rules` and `04_verify`.
  - Entries in `README.md` (section "The cache of the model calls"), `COMMANDS.md`,
    `SMOKE_TESTS.md` (section MC), and `ResearchLog.md`.
- Owner messages of 13:14:45 and 13:26:43: new `docs/database-structure.pdf`, a one-page
  A4 landscape ER diagram of `data/lab.sqlite3` at schema version 17. It shows the 13 tables
  with all 65 columns, the keys, the checks, the indexes, the triggers, and the 12 foreign
  keys as lines. Notes explain the migrations, the table rebuilds, the image store, the
  value rules, and the test-set import.
  - The source is new `docs/database-structure.html`, written by hand. Update it and print
    it again when a new file enters `pipeline/schema/`. Its head comment holds the print
    command. A small script draws the foreign-key lines and sets `data-fit` on `<html>`
    (`ok` or `overflow`).
  - Headless Chrome 153 with `--user-data-dir` and a new directory wrote the PDF but did
    not exit. Without `--user-data-dir`, the print takes about 2 s.
- The Embeddings page, the phase of a running build (owner message of 13:37:14 "make it
  show progress", answer "Phase text"). The bar moved only after each batch of 16 images
  had its vectors, so a cold start of a gateway model on gx10 (up to about 48 s) showed
  `0 / 2023` with no change. `pipeline/build_embeddings.py` writes the line `request`
  before each model request and the line `retry` before each wait of
  `OpenAIBackend.embed`. `embeddings.job_state` gives `phase`, `phase_event`, and
  `phase_t`. The job row shows `waiting for the model · <time>` when a request takes 3 s
  or more, and `retry <n> in <s> s: <error>`. The log dialog hides the `request` lines
  with the checkbox. Tests: `tests/test_build_embeddings.py` (2 new),
  `tests/test_embedding_routes.py` (1 new); 53 embedding tests pass. Checked in headless
  Chromium with a mocked job. The lab server on 8168 was restarted at 13:44:04 (SIGTERM
  on the process of the owner's terminal); the restart also deployed the mock backend of
  drink-atlas-workspace-85. It was restarted again at 13:46:33 with `start_new_session`
  (PID 25039 leads its own process group), so the end of the tool shell of a session
  does not stop it (finding of 85 in `ResearchLog.md`).
- The label view of the Embeddings page, plan 22 (owner message of 12:11:50, answers of
  12:27:47). Cause of the failures: `embeddings.read_inputs` set the label cut to `None`,
  because no full photo had a label cut. New `pipeline/seed_label_cuts.py`: SAM3 and the
  label rule of plan 16 (`alternatives.label_derivatives`) for each full original; the cut
  is a row of the kind `label` of `image_derivative` (schema 017 of
  drink-atlas-workspace-7b, owner answer of 12:28:04). `read_inputs` reads the kinds
  `package` and `label`. The run on `data/lab.sqlite3` (12:46:36 to 13:36:59, 3,022 s):
  2,019 of 2,023 full originals have a label cut, 4 have no label, no error; a backup of
  version 17 is in the scratchpad of the session. A `Build` of
  `gx10-siglip2-so400m-patch16-naflex-p256` made the label items: 4,039 of 4,043 items
  are `current`, 4 failed (`no label cut yet`). Each other entry needs a `Build`.
  The badge `vector`: `embedding_routes.entry_view` maps the vectors file and sets
  `vector` on a cell whose current or stale record has a row in it; the page shows it at
  the bottom left of the cell and in the preview. Tests: `tests/test_seed_label_cuts.py`
  (7), `tests/test_embedding_routes.py` (1 new). `README.md`, `SMOKE_TESTS.md` (EB31 to
  EB36), `COMMANDS.md`, `ResearchLog.md`, plans 10 and 22 follow.

- Plan 23, change of Q1 (owner message of 13:37:14, answer of 13:41:00: "mock should run
  as any other config"): the configuration `mock` builds as any entry. It has the views
  of the other entries in `config.yaml`. New `MockBackend` of `pipeline/build_embeddings.py`
  gives each prepared image a random unit vector of 256 values, with no request.
  `pipeline/embeddings.py` gives a mock entry the model `random-unit-vectors` and
  refuses `base_url`, `model`, and `extra_body`. The refusals of `embedding_routes.start`
  and `build_embeddings.main` are gone. Tests: `tests/test_mock_run.py` (14, with a full
  build on the fixture of `tests/embedding_lab.py`), `tests/test_run_routes.py` (7).
  Live since the restart of 8168 by e3 at 13:44:04.
- Plan 23 (`docs/plans/23_runs-page.md`), owner messages of 12:36:00, 12:38:00, 12:41:00,
  12:43:00, and 12:52:00: the Runs page on the lab server, the filter `Configuration`,
  and the configuration `mock`.
  - `/runs` is on. It reads the run directories of `runs/`; the database does not hold
    the runs. New `pipeline/run_files.py` (the run functions of the review tool, with
    the runs directory as an argument), new `pipeline/run_routes.py` (`/runs`,
    `/api/runs`, `/api/run`, `/api/run-clusters`, `/api/run-inputs`), new
    `pipeline/pages/runs.html` (the Runs page of the review tool, with the lab
    navigation, the filter `Configuration`, the column `configuration`, and the images of
    the lab image store).
  - `run.json` gets the key `configuration`: the name of an entry of `embeddings` in
    `config.yaml`. `pipeline/benchmark.py` `run_benchmark` writes it with the new
    argument `configuration`.
  - New `pipeline/mock_run.py` and the entry `mock` (`backend: mock`) at the end of
    `embeddings` in `config.yaml`: a run with random top-k candidates for each photo of
    a test set. `pipeline/embeddings.py` accepts the backend `mock` (zero items);
    `embedding_routes.start` and `build_embeddings.py` refuse to build it.
  - `/embedding`: the selector label is `Configuration`, not `Embedding`.
  - `pipeline/lab_server.py`: `/runs` leaves `DISABLED_PAGES`; `do_GET` sends the routes
    to `run_routes.py`; `IMAGE_ROUTE` admits the folder `testset` of the test photos.
  - The mock run `runs/2026-09-25T101320Z-lab-mock-my/` (seed 20260925).
  - Tests: 6 + 7 + 14 new tests and one in `tests/test_benchmark.py`; the disabled-page
    tests of `tests/test_lab_server.py` no longer name `/runs`. The full suite: 425 tests
    `OK`. 8168 was down since about 13:03:30; started at 13:14:31, and restarted at
    13:20:00 with SIGTERM in its own session (`ResearchLog.md`).
- Plan 21 (`docs/plans/21_website-import-ui.md`), owner messages of about 12:00 ("can we
  make 2 modes", "also introduce last_modified time") and the answers after them: the
  website import in the UI.
  - `pipeline/import_website.py`: the modes `--prepare DIR` (the compare writes
    `diff.json` and the website images; no write to the database) and `--apply DIR`
    (the choices of `choices.json`). The CLI with no mode flag still stops on a conflict.
    One reused HTTPS connection: a full run takes about 10 minutes, not 22. The sitemap
    gives `website_modified_at`. A refusal skips a conflict or a plain change while the
    website keeps the refused value; a write deletes a refusal that no longer matches.
    Each choice writes a short `script` comment.
  - Schema 015 (`pipeline/schema/015_website_import.sql`): `wine_catalog.website_modified_at`,
    `wine_catalog.modified_at` with two triggers, and the table `website_refusal`.
    `data/lab.sqlite3` migrated at 12:33.
  - New `pipeline/website_import_routes.py`: start, state, diff, images, apply, and stop
    of the job; `job.json` and `work/website-import/<run>/`. Hunks in
    `pipeline/lab_server.py` (the delegation, the two times in `dataset_records`).
  - New `pipeline/pages/website_import.js`: the button `Import from website` and the merge
    dialog. Hunks in `pipeline/pages/dataset.html` (the button, the script tag, two sort
    options and their code).
  - Also: `import_website.py` uses `manual_wines.is_manual` (plan 20 rule 4, review of
    7b). The fixture insert of `tests/test_lab_server.py` names its columns.
  - Tests: 31 + 6 new or changed tests; `test_lab_server.py` 50; the full suite 397, all
    `OK`. 8168 restarted at 12:50:39 with SIGTERM.
- The review of the unfinished work (owner messages of 12:01:18; answers of 12:28:04):
  `docs/reviews/2026-09-25_unfinished-work.md` lists the findings of each session. Each
  running session fixed its own; 7b fixed these:
  - Schema file `pipeline/schema/017_derivative_kind.sql`: `image_derivative` holds one cut
    for each original and kind (`package`, `label`), key (`source_sha256`, `kind`). The
    2,023 rows of `data/lab.sqlite3` are `package` cuts (migrated at 12:35:13; a backup of
    version 16 is in the scratchpad of the session). `derive.Derivatives` has a `kind`;
    `derive.write_rows` writes it; `derive_all` looks at the `package` rows alone
    (agreed with drink-atlas-workspace-8b). `lab_server.card_images` joins the `package`
    cut; `alternative_images` joins the cut of the kind of each row.
  - `pipeline/alternatives.py`: the row of `image` holds the size of the file, not of the
    SAM3 copy; a photo with no current cut of its kind is processed on the next request
    (the same file again, or a type change), and a change back to a kind reuses its cut;
    `label_derivatives` is public (EMBEDDINGS calls it); `insert_image` calls
    `patches.insert_image`.
  - `pipeline/patches.py`: an upload of more than 100,000,000 pixels answers 413.
  - `pipeline/lab_server.py`: an unexpected error of the patch and alternative routes
    answers 500 with a JSON error; `_json_body` answers 400 for a lone surrogate on every
    JSON route (finding of drink-atlas-workspace-98); the module docstring.
  - `pipeline/pages/dataset.html`: a patch dropped while the last one of the wine is
    processing gets a message; `Cancel` takes back the marked removals alone and the
    uploads go on; `×` is disabled while a type change runs.
  - `pipeline/seed_patched.py`: refuses a table with `main_patched` rows unless `--force`,
    in the form that `seed_codes.py` and `seed_atlas_bindings.py` of f1 use.
  - The 5 review-tool test modules load again: `scripts/common.py` reads the config path
    from `SVOE_VINO_REVIEW_CONFIG`, and the modules set it to `config.old.yaml` (25 tests).
  - Tests: `tests/test_alternatives.py` (33: the size, both cuts of one file, a type change
    with no SAM3, the same photo again, a version 9 database through 010, 012, and 017,
    the neck cases), `tests/test_patches.py` (the pixel limit, 503), `tests/test_seed_patched.py`
    (`--force`), `tests/test_lab_server.py` (`add_derivative` names its columns),
    `tests/test_labdb.py` (version 17). Full suite: 369 tests, no error except the 5 load
    errors, which are fixed now.
  - Docs: README steps 3 and 4, plan 07 rule 5 of step 3 (the whole sentence, with the
    facts of f1), plans 10, 14, and 16, SMOKE_TESTS P5, P8, AL22 to AL27, PE20 to PE22.
  - The lab server on 8168 was restarted at 12:45:39 (SIGTERM, rule 23), with the code of
    the other sessions as of that minute.

- The review fixes of drink-atlas-workspace-f1 (review
  `docs/reviews/2026-09-25_unfinished-work.md`, sections f1 and a2; owner answers of
  2026-09-25T12:28:04+0300):
  - `seed_codes.py` and `seed_atlas_bindings.py` refuse a table that already holds rows,
    because a second run added back each value that a person removed on the page.
    `--force` adds the missing rows as before. `seed_patched.py` of drink-atlas-workspace-7b
    uses the same form.
  - The error of `seed_codes.py` names the record, the field, and the value, for example
    ``record 2 (wine-b): `barcode` '4631168664970': wrong check digit 0; expected 9``.
  - `codes.clean_qr_url` keeps the brackets of an IPv6 host: `http://[::1]:8080/x`
    stayed `http://::1:8080/x` before.
  - The shared Dataset page on the review tool works as before plan 11 again: the
    Barcodes editor accepts an EAN-13, the GTIN editor and its count show only when the
    answer holds `gtins` (the lab), and the `+` of `Barcodes` and `QR URLs` needs a
    non-empty `barcode_file` when the answer holds no `gtins`. Checked in headless
    Chromium with the answer of `/api/dataset` changed in the browser to the form of the
    review tool. The review tool itself does not start now (the known `config.yaml`
    error of `scripts/common.py`).
  - Tests: `tests/test_codes.py` (13), `tests/test_seed_codes.py` (11),
    `tests/test_seed_atlas_bindings.py` (9), and a check that the lab answer holds no
    `barcode_file` in `tests/test_lab_server.py`. `COMMANDS.md`, `README.md` (steps 6 and
    7), plans 11 (decision O3, O2 point 5) and 15, and `SMOKE_TESTS.md` (the header of
    the lab server section, S1, S3, S12, WC2, WC3, AB2) follow. No restart: the page is
    read from disk. 8168 runs the IPv6 fix of `codes.py` since the restart by
    drink-atlas-workspace-7b at 12:45:39.

- The test sets in the lab database (plan 12 step 4), by TESTSET [0fe970]. Owner messages
  of 2026-09-25T12:13:10+0300 and 12:15:00, and the answers of 12:22:00 ("Enter schema
  now", "Editing on the DB"):
  - `pipeline/schema/016_testset.sql` (was `pipeline/schema_pending/NNN_testset.sql` of
    drink-atlas-workspace-20): it builds `image` again with the folder `testset`, and it
    adds `test_set`, `test_photo`, `test_excluded`, and `test_variant`. It enters before
    the flat image store of 9a [f028b4]; the flat store MUST also move
    `data/images/testset/`.
  - `pipeline/import_testset.py`: a test photo goes to `data/images/testset/` and gets the
    folder `testset` (new `photo_path`, `FOLDER`); new `print_report`. A file that `image`
    holds already keeps its folder.
  - New `pipeline/import_testsets.py`: imports `my`, `official-real-photos`, and
    `vlmrerank-8b-failed` of `svoe-vino-testset/dataset/` with one command. New
    `tests/test_import_testsets.py` (3 tests).
  - `pipeline/benchmark.py`: the path of a photo comes from its folder in `image`. One new
    test in `tests/test_benchmark.py`. `tests/testset_fixture.py` no longer emulates the
    flat store. `tests/test_import_testset.py` uses `photo_path`.
  - `tests/test_labdb.py`: version 16 and the four new tables.
  - `data/lab.sqlite3` migrated from 15 to 16 at 12:34 (a backup first). The lab server
    needed no restart. The import wrote 4,323 photo rows (`my` 4,043,
    `official-real-photos` 100, `vlmrerank-8b-failed` 180) and 3,449 new files (760 MB).
  - Docs: plan 12 (status, decisions, step 4, Q1, risks), `README.md`, `COMMANDS.md`,
    `SMOKE_TESTS.md` (new section TS), `ResearchLog.md`.
- The review findings of drink-atlas-workspace-0b (`docs/reviews/2026-09-25_unfinished-work.md`,
  owner answers of 2026-09-25T12:28:04+0300), `pipeline/pages/dataset.html`:
  - A click on a thumbnail of another kind, or of another alternative photo, switches the
    preview fully (owner decision "Switch fully"): the title, the page path, the
    position, and the arrows follow. The new `setPreviewItem` does this part of
    `showImagePreview`, so the thumbnails keep their place. Each thumbnail holds its
    `kind` and `sha256`; the mark goes on the thumbnail of the item in view.
  - Bug (7b finding 11): `open raw image` in the patch preview opened the processed
    patch. It now opens the patch original (`_patch_url`).
  - At a width of at most 860 px the text column takes the full width
    (`.info { align-self: stretch; }`), so the favorites star stands at the right edge.
  - Docs: `SMOKE_TESTS.md` AL12 stands before the barcode rows AL13 and AL14 of 7b again;
    the preview rows are now AL15 to AL20, and AL21 is new (the full switch). PE14 names
    the raw link, PE18 names `main · processed`. Plan 14 item 4 names the new thumbnails
    (one line; 7b agreed). `README.md`: the full switch and the raw link.
  - Checked in headless Chromium on the live lab server, read-only: the thumbnail clicks
    of each kind, the arrows after a switch, the raw link of `/patch`, and the star at
    800 px. No server change and no restart.
- Review fixes of section "98" of `docs/reviews/2026-09-25_unfinished-work.md` (owner
  answer of 12:28:04: each session fixes its own), by drink-atlas-workspace-98:
  1. `pipeline/comments.py`: `clean_text` refuses a lone surrogate (U+D800 to U+DFFF)
     with HTTP 400. Before, the INSERT raised `UnicodeEncodeError` and the request got
     no answer. New cases in `tests/test_comments.py` and `tests/test_lab_server.py`.
     The lab server gets it at its next restart; this session did not restart 8168,
     because other sessions have review fixes in progress.
  2. `pipeline/pages/dataset.html`: in the view `with comments`, the removal of the last
     comment of a wine takes its card out of the list, as the `State` views do.
  3. `pipeline/pages/dataset.html`: an empty or blank comment draft no longer triggers
     the leave-page prompt.
  4. Docs: `SMOKE_TESTS.md` D2, D10, D10a (the schema version and the tables; the text
     now names the last schema file, so it does not go stale), `docs/plans/07_*.md`
     (14 cases of `test_labdb.py`), `docs/plans/11_wine-codes.md` (SIGTERM), `README.md`
     step 3 (the value `Favorites` of `State`).
  Fixes 2 and 3 were checked in headless Chromium on a copy of the database.
- Plan 20, the fixes of review section fa (owner answer of 12:28:04). A text field or
  `image_name` that is not a JSON string, or that holds a lone surrogate, now gets HTTP
  400; before, the server sent no answer. The slug `__null__` is reserved (the no-match
  place of `scripts/match_scoring.py`). A new test: the slug of a `Removed` manual wine is
  a conflict. `pipeline/manual_wines.py`, `tests/test_manual_wines.py` (12). Live since
  the restart of 8168 by drink-atlas-workspace-7b at 12:45:39; checked with two refused
  requests. After schema 015 of drink-atlas-workspace-ff, the
  test fixture names the columns of `wine_catalog`; the route tests expect the message of
  the lone surrogate check of `_json_body`, and a unit test covers the check of
  `manual_wines.py`. Plan 20 (rules 16 and 16a) and `SMOKE_TESTS.md`
  (AW1, AW16) follow.

- Plan 20, `Add wine`: the slug follows the name until a person types a slug (owner
  message of 12:05:54). `slugOfName` of `pipeline/pages/dataset.html` spells each
  Cyrillic letter as the slugs of vino-svoe.ru mostly do (`х` -> `h`, `ц` -> `ts`, `й` and
  `ы` -> `y`). The description is optional (owner message and answer of 12:09:52). New
  schema file `pipeline/schema/014_description_optional.sql` builds `wine_catalog` again
  with a nullable `description`; it keeps each row, each rowid, and the rows of the 5
  child tables. `pipeline/labdb.py` `migrate` now runs a schema file with the foreign keys
  off and a `PRAGMA foreign_key_check` before the COMMIT: SQLite ignores the pragma inside
  a transaction, and `PRAGMA defer_foreign_keys` does not save the DROP of a parent table
  (tested on a copy). `pipeline/manual_wines.py` stores an empty description as NULL.
  The imports still require a description. `data/lab.sqlite3` migrated to version 14 at
  12:13:19 (backup in the scratchpad of drink-atlas-workspace-fa); the lab server on 8168
  was restarted at 12:13:40 (SIGTERM). Tests: `tests/test_labdb.py` (3 new, 14),
  `tests/test_manual_wines.py` (10), `tests/test_import_catalog.py` (22). Checked in
  headless Chromium. `README.md`, `SMOKE_TESTS.md` (D12, AW12 to AW15), plan 07 (rule 6),
  and plan 20 follow.

- The Embeddings page: a click on a prepared image opens the image preview of `/dataset`
  (owner message of 11:59:27, answers of 12:02:31: with thumbnails; a URL query key).
  `pipeline/pages/embedding.html` alone; no server change and no restart. The CSS and the
  markup are copies of the preview of `pipeline/pages/dataset.html`. The arrows and the
  arrow keys step through the images of the same view of the filtered list (2,048 `full`
  images of `gx10-siglip2-so400m-patch16-naflex-p256`). The thumbnails show each column
  of the wine: `original` and each view, with the status badge. `open raw image` names
  the original. The URL key `preview=<sha256>_<view>` names the open preview; Back
  closes it, and a link opens it again. A click with a modifier key opens the image in a
  new tab. At a width of at most 440 px the modal has no padding, so the dialog fills the
  screen (the preview of `/dataset` keeps a 24 px gap there). Tests:
  `tests/test_embedding_routes.py` (1 new; 49 embedding tests pass). Checked in headless
  Chromium on the live server: open, keys, thumbnails, Back and Forward, a copied link,
  light and dark mode, 1400 px and 390 px. `README.md`, `SMOKE_TESTS.md` (EB1, EB23 to
  EB30), and plan 10 (items 7 and 10) follow.

- Owner message of 2026-09-25T11:57:30+0300: the `main` image of a `Disabled` wine is
  gray on the card of `/dataset`. `pipeline/pages/dataset.html`: `imageFigure` gives the
  figure the class `state-disabled`, and the CSS `filter: grayscale(1)` draws the image
  gray in the browser. The file, the badge, the patch, and the alternative photos do not
  change. Checked in headless Chromium on the live lab server, in light and dark mode, on
  the one `Disabled` wine (`aligote-barrel-2024`). No server change and no restart.
- Owner message of 2026-09-25T11:58:25+0300: the favorites star of plan 19 moves from
  before the name to the top right of the text column of a card, next to the
  alternative photos. `pipeline/pages/dataset.html`: the star is its own line of
  `recordHtml` after the slug; `.info` is `position: relative`, and the star is
  absolute at its top right. The slug and the name keep 34 px of free space at the right
  (class `with-star`), so no text runs under the star. At a width of at most 860 px the
  alternative photos stand below the text, and the star stays at the top right of the
  text. No server change and no restart.
- Plan 19 (`docs/plans/19_favorites.md`), owner message of 11:37:46 and the two answers
  of 11:39:42: favorite wines on the lab database.
  - Schema file `pipeline/schema/013_wine_favorite.sql`: the table `wine_favorite` (`wine_slug`,
    `created_at` in UTC). `data/lab.sqlite3` is at version 13.
  - New `pipeline/favorites.py`: `favorites`, `count`, and `set_favorite` (a repeated
    request changes nothing).
  - `pipeline/lab_server.py`: `POST /api/dataset-favorite` with `"favorite": true|false`,
    `_favorite` of each record, and `favorites` of `/api/dataset`.
  - `pipeline/pages/dataset.html`: the star before the name (`☆`, or an amber `★`), the
    value `Favorites` of the filter `State` (each favorite in each state, also a removed
    one), and `N favorites` in the header. The review tool shows none of these.
  - Tests: new `tests/test_favorites.py` (4), 2 new tests in `tests/test_lab_server.py`,
    `tests/test_labdb.py` (version 13, table `wine_favorite`). Checked in headless
    Chromium on a copy of the database, in light and dark mode.
  - The lab server on 8168 was restarted at 11:55 with SIGTERM.
- Plan 20: the button `Add wine` of the Dataset page adds a wine by hand (owner messages
  of 11:30:05 and 11:41:15, answers of 11:40:48 and 11:42:50, approval at 11:46:09). A
  dialog asks each catalogue field and a required main image. The slug gets the fixed
  prefix `__`, so it cannot collide with a slug of vino-svoe.ru; the prefix alone marks a
  manual wine, with no schema file. New `pipeline/manual_wines.py` and the route
  `POST /api/wine` (JSON, the image in base64) of `pipeline/lab_server.py`: the wine is
  `Active`, the image is `main` with `match_method` = `manual` and its file name as
  `csv_photo_name`, and `derive.derive_all` processes it. A known slug gets HTTP 409.
  The card of a manual wine has no link to vino-svoe.ru. `pipeline/import_catalog.py`
  never removes a manual wine and stops on a CSV slug with `__`; drink-atlas-workspace-ff
  added the same rules to `import_website.py`. Tests: new `tests/test_manual_wines.py`
  (10), `tests/test_import_catalog.py` (2 new, 22). Checked in headless Chromium on a
  scratch database, in light and dark mode. The lab server on 8168 was restarted at
  11:52:40 (SIGTERM). `README.md`, `SMOKE_TESTS.md` (D12, new section AW), and plan 07
  (step 2, rule 10) follow. The image zone of the dialog is a portrait column at the left
  of the fields (owner message of 11:55:02); at 640 px or less it stands above them.

- Plan 18 (`docs/plans/18_import-website.md`), owner message of 2026-09-25T11:06:56+0300
  and the answers after it: a new tool `pipeline/import_website.py --db data/lab.sqlite3`
  imports the live catalogue of vino-svoe.ru from its JSON API.
  - A new website wine is added as `Active` with its image as `main`. A missing `Active`
    or `Disabled` wine becomes `Removed`. A `Removed` wine on the website becomes
    `Active`, also when a person removed it. A wine with no `main` row gets the website
    image. Each change gets a short comment of the source `script` (plan 17).
  - A changed `name`, `producer`, `category`, `color`, or `region`, or a changed main
    image (SHA-256 of the original), stops the import. The error lists all problems,
    and nothing changes. The same bytes under another upload name are no change.
  - A manual wine (slug prefix `__`, rules 24 to 26 of plan 20) is never removed. A
    website slug with this prefix stops the import.
  - Tests: `tests/test_import_website.py`, 20 tests, `OK`, with a fake HTTP client.
  - The first real run (11:31 to 11:54, 22.5 minutes) stopped on 10 problems, as
    expected: 7 wines with a changed text, 3 changed images. `data/lab.sqlite3` did not
    change.
  - Entries in `COMMANDS.md`, `README.md`, `SMOKE_TESTS.md` (section IW), and
    `ResearchLog.md` (the API, the response headers, the sitemap `lastmod`).
- The Embeddings page: a `Log` button after `Stop` opens a dialog with `build.log` of
  the selected entry (owner message of 11:42:50, answer of 11:45:00: readable lines and
  a filter). The new route `GET /api/embeddings/<name>/log` of
  `pipeline/embedding_routes.py` sends the text of the file (404 when no build wrote it
  yet). The page shows each JSON line as `time · event · fields`, and a line that is not
  JSON, for example a traceback, as it is, in red. The checkbox `hide item_failed and
  progress` is on at the start; for `gx10-siglip2-so400m-patch16-naflex-p256` it
  leaves 2 of 2,150 lines. `Refresh` reads the file again. `Log` is disabled for an entry
  with no build. Tests: `tests/test_embedding_routes.py` (2 new; 48 embedding tests
  pass). Checked in headless Chromium on the live server, in light and dark mode, at
  1400 px and 390 px. The lab server on 8168 was restarted at 11:48:14 (SIGTERM).
  `README.md`, `SMOKE_TESTS.md` (EB1, EB19 to EB22), and plan 10 follow.
  Owner message of 11:56:36: an `item_failed` line shows the full `source_sha256`, not
  the first 12 characters.

- Plan 16: the detection of an alternative photo sends SAM3 the nouns `barcode, bottle,
  label, bottle neck, can` (owner message of 11:45:49, answer of 11:47:17). `wine bottle
  label` is gone; the label cut uses `label` alone. 7 test images: 4.4 s instead of
  5.2 s, the same types. `pipeline/alternatives.py` alone; `tests/test_alternatives.py`
  (27) passes. Live since the restart of 8168 by drink-atlas-workspace-e3 at 11:48:14.

- Plan 16, last section (owner messages of 11:26:11 and 11:27:30, answer of 11:28:52):
  - A barcode makes an alternative photo a back view: `full_back` or `label_back`.
    `alternatives.side` counts a barcode of score 0.7 or more, at least 10 % of the width
    of the largest bottle or can, with its centre on that package. SAM3 gets the noun
    `barcode` too. Probe: 13 or 14 of 16 random FRAP photos got the right side; 15 lab
    photos with no back view got no back type (`ResearchLog.md`).
  - Schema file `pipeline/schema/012_type_names_kind_first.sql` renames the additional
    types to `full_front`, `label_front`, `full_back`, `label_back` and keeps each row.
    `data/lab.sqlite3` is at version 12 since 11:30:03 (the 3 owner photos kept their
    types); a backup of version 11 is in the scratchpad of the session. The buttons read
    `FF`, `LF`, `FB`, `LB`. `labdb.IMAGE_FOLDERS` and `embeddings.ROLES` and
    `TYPE_ORDER` hold the six names of the schema alone. The fixtures of the tests use the
    new names; `tests/test_labdb.py` expects version 12.
  - Tests: `tests/test_alternatives.py` (27). The lab server on 8168 was restarted at
    11:32:35 and again at 11:35:26 for the barcode limits (SIGTERM, rule 23).
  - `README.md`, `SMOKE_TESTS.md` (AL1 to AL14), `ResearchLog.md`, and plans 10 and 16
    follow.

- Owner messages of 2026-09-25T11:19:38+0300, the four answers of 11:22:10, and 11:22:21:
  the image preview of `/dataset` for the alternative photos of the lab server.
  - `pipeline/pages/dataset.html`: a click on an alternative photo opens the image
    preview, in place of a new tab. The arrows and the keys step through every
    alternative photo of the list, one photo for each step. The page path is
    `/dataset/<slug>/alternative/<sha256>`. The preview shows the processed file;
    `open raw image` opens the original.
  - The thumbnails are the same in each preview of a wine: `main`, `main · processed`,
    `patched`, `patched · processed`, then two for each alternative photo, for example
    `alternative 2 FF` and `alternative 2 FF · processed`. The labels `original` and
    `processed` are now `main` and `main · processed`.
  - The thumbnails stand in one row. A row that is wider than the preview scrolls
    sideways, and the marked thumbnail is scrolled into view. Before, a second row was
    cut off at the bottom of the preview.
  - `pipeline/lab_pages.py`: `DATASET_PREVIEW_ROUTE` accepts the alternative path. The
    review tool serves the path too, but it has no preview of an alternative photo.
  - Tests: the route test of `tests/test_lab_server.py` holds the new path and two wrong
    forms. `test_lab_server.py`: 47 tests, `OK`. Checked in headless Chromium on the live
    lab server, read-only: the deep link, the four keys, the card click, Back, an unknown
    photo, and widths of 1400 px and 800 px.
  - The lab server on 8168 was restarted at 11:26 with SIGTERM, for the new route.
- Rule 23 of `AGENTS.md` (owner message of 11:29:27): an agent stops the lab server on
  8168 with SIGTERM, not SIGINT. A server that was started in the background ignores
  SIGINT. `ResearchLog.md` records the finding and the decision.
- Plan 17 (`docs/plans/17_wine-comments.md`), owner messages of 11:04:34, 11:07:00,
  11:07:59, and 11:09:30: timestamped comments of a wine on the lab database.
  - Schema file `pipeline/schema/011_wine_comment.sql`: the table `wine_comment` (`id`,
    `wine_slug`, `created_at` in UTC ISO 8601 with `Z`, `source` `user` or `script`,
    `text` of at most 4,000 characters). `data/lab.sqlite3` is at version 11.
  - New `pipeline/comments.py`: `clean_text`, `check_source`, `comments` (time order, the
    oldest first), `count`, `add`, and `remove` by `id`.
  - `pipeline/lab_server.py`: `POST` and `DELETE /api/dataset-comment`; the POST body MAY
    hold `"source": "script"`, else the source is `user`. `_comments` of each record and
    `comments` of `/api/dataset`.
  - `pipeline/pages/dataset.html`: the editor `Comments` after `Atlas Core product`: a
    multi-line field (Enter adds a line break, Cmd+Enter or Ctrl+Enter saves, Esc
    cancels), the local time and the source of each comment, and `×` with a
    confirmation. The value `with comments` of the filter `Show`, `N comments` in the
    header, and the comment text in the search. The review tool shows none of these.
  - Tests: new `tests/test_comments.py` (9), 6 new tests in `tests/test_lab_server.py`,
    `tests/test_labdb.py` (version 11, table `wine_comment`). Full suite: 283 tests, only
    the 5 old loader errors of the `scripts/review_server.py` tests. Checked in headless
    Chromium on a copy of the database, in light and dark mode.
  - The lab server on 8168 was restarted at about 11:23 with SIGTERM. SIGINT does not
    stop a server that was started in the background.
- Plan 16 (`docs/plans/16_alternative-images.md`), approved by the owner at 11:02:26:
  alternative photos of a wine on the lab database.
  - Schema file `pipeline/schema/010_additional_types.sql` builds `wine_image` again with
    the types `front_full`, `front_label`, `back_full`, `back_label` in place of `front`,
    `label_front`, `back`, `label_back`. It keeps each row and its rowid. `data/lab.sqlite3`
    is at version 10 since 11:11:16; a backup of version 9 is in the scratchpad of the
    session. `labdb.IMAGE_FOLDERS` has the new names.
  - New `pipeline/alternatives.py`: upload, SAM3 detection of a full package or a label
    close-up (`detect`), the label cut (`label_instance`, the rule of `build_labels.py`
    with a fall-back to the largest label), the type change (a change between full and
    label cuts the photo again), and the removal (the file stays).
  - `pipeline/derive.py`: `Sam3Client` takes the SAM3 texts and the mask switch
    (`_post`), and answers all instances (`instances`, new `_sent_copy`). `segment` gives
    the same mask as before. Agreed with drink-atlas-workspace-8b.
  - `pipeline/lab_server.py`: `POST`/`DELETE /api/dataset-alternative`, `POST
    /api/dataset-alternative-type`, `alternative_images` (the `cut_nothing` rule applies),
    `_alternatives` of each record, `alternative_editor` and `alternatives` of
    `/api/dataset`. A shared `Handler._image_body` reads the body of a patch and of a photo.
  - `pipeline/pages/dataset.html`: a photo goes to the server at once and shows
    `processing`; the buttons `FF`, `FL`, `BF`, `BL` below each photo save the type at
    once; `×` and `Apply` remove a photo. The review tool keeps its old editor.
  - Tests: new `tests/test_alternatives.py` (20), `tests/test_derive.py` (2 new),
    `tests/test_labdb.py` (version 10), and the type names in the fixtures of
    `tests/embedding_lab.py`, `tests/test_seed_images.py`, `tests/test_embeddings.py`,
    `tests/test_embedding_routes.py`, `tests/test_lab_server.py`. Checked in headless
    Chromium with the live SAM3 on a copy of the database, in light and dark mode. The
    lab server on 8168 was restarted at 11:16:21 (SIGINT did not stop it; SIGTERM did).
  - `README.md`, `SMOKE_TESTS.md` (section AL), `ResearchLog.md`, and plan 10 follow.

- Plan 15 (`docs/plans/15_atlas-binding.md`): the Atlas Core product of a wine in the
  database (owner message of 2026-09-25T10:23:51+0300; answers of 10:30:50: the
  database, and a remove of a manual binding). New schema file `009_atlas_binding.sql`:
  the table `wine_atlas_binding`, one `automatic` and one `manual` row at most per wine;
  the manual row wins. `data/lab.sqlite3` is at version 9 (backup before the migration:
  `work/lab.sqlite3.before-009-f1`).
- New `pipeline/atlas_bindings.py` (the UUID check, the effective bindings, the set and
  the remove of a manual row) and `pipeline/seed_atlas_bindings.py`. The seed read
  `atlas-matches.jsonl` and `atlas-bindings.manual.jsonl` of
  `svoe-wino-hackaton/dataset/derived/official-2026-09-17/` and added 364 automatic rows
  and 3 manual rows. It adds rows alone; a changed file row prints `differs`.
- `pipeline/lab_server.py`: `GET /api/dataset` sends the bindings, the counts, and
  `atlas_binding_editor: true`. `POST /api/dataset-atlas-binding` sets a manual binding,
  and the new `DELETE` removes it; the wine then shows its automatic binding, or none.
- `pipeline/pages/dataset.html`: the editor `Atlas Core product` is on for the lab. A
  manual binding gets a red `×`. A save and a remove redraw their own card alone.
- The lab does not write the JSONL files. The review tool does not see a lab binding.
- Tests: new `tests/test_atlas_bindings.py` (6) and `tests/test_seed_atlas_bindings.py`
  (9); `tests/test_lab_server.py` (41); `tests/test_labdb.py` (version 9). Checked in
  headless Chromium on the live page with the writes answered in the browser, and with
  one set and remove on the live server. `README.md` (step 7), `COMMANDS.md`,
  `SMOKE_TESTS.md` (S4, section AB), and plan 07 follow. The lab server on 8168 was
  restarted with SIGTERM at 10:37:59.

- The Dataset page of the lab server (owner messages of 2026-09-25T10:20:28 to
  10:26:37, answers of 10:23:52; plan 14, last section):
  - A dropped or chosen patch file goes to the server at once, with no `Apply` step. The
    editor shows `Processing…` until the answer. `Remove` keeps `Apply` and `Cancel`.
  - The card shows the `main` image at the left and the processed patch in the patch
    slot, side by side. `card_images` of `pipeline/lab_server.py` sends the `main` image
    in `main_image_*` and the patch in `_patch_url`, `_patch_image_url`, and
    `_patch_derivation`. The key `catalog_main_url` is gone; `main_image_original_url`
    holds the same URL now. `patches.patch_urls` and `patches.image_url` are gone.
  - A `crop` whose box is the whole image cut nothing (`cut_nothing`): the slot shows the
    original with no badge. On the live database 568 cards lose the badge `crop`; 1,332
    keep it; 146 keep `seg`.
  - The preview shows four thumbnails for a patched wine: `original`, `processed`,
    `patched`, `patched · processed`. They are 120 px high (72 px at a width of at most
    440 px, in one row that scrolls sideways) and stand at the bottom of the preview, so
    a new image does not move them. Up and Down step to the previous and the next wine.
  - The patch `Remove` button has the size of the `Remove` button of the main image and
    stands at the right. The buttons of `.state-actions` get one width each
    (`flex: 1 1 0`).
  - The filter `State` has the new value `Disabled`: the disabled wines alone
    (`inStateView`).
- The Embeddings page (owner message of 10:29:30): the failed count is red when it is
  above zero, in the source panel and in the summary line. The row `Directory` has an
  `open` button. The new route `POST /api/embeddings/<name>/open` of
  `pipeline/embedding_routes.py` runs `open` on the directory of the entry (404 when the
  directory is not on disk, 500 when the command fails). The row `Directory` no longer
  repeats the endpoint.
- Tests: `tests/test_lab_server.py` (the two card image tests follow the side-by-side
  card; new `test_a_crop_that_cut_nothing_gets_no_badge` and
  `test_cut_nothing_knows_a_turned_image`), `tests/test_patches.py` (12),
  `tests/test_embedding_routes.py` (2 new). Checked in headless Chromium on a copy of the
  database, in light and dark mode, at 1400 px and 390 px. The lab server on 8168 was
  restarted at 10:32:52 (SIGINT did not stop it; SIGTERM did).
- `README.md` (steps 3 and 5, "The Dataset page", the lab embeddings), `SMOKE_TESTS.md`
  (PE2 to PE19, S17a, EB17, EB18), and plan 14 follow.

- The lab keeps GTINs alone (owner message of 2026-09-25T10:13:54+0300 and the answers
  of 10:16:07; plan 11, decision O2). `pipeline/codes.py` has the kinds `gtin` and
  `qr_url` alone. The lab server has no route `/api/dataset-barcode` (HTTP 503), and
  `GET /api/dataset` sends no `barcodes` and no `_barcodes`. `seed_codes.py` stores each
  `barcode` value of the code map as a GTIN; another value stops the seed. No schema
  file: schema 008 keeps `barcode` in its CHECK until the flatten. The one `barcode` row
  of `data/lab.sqlite3` (`golubitskoe-estate-chardonnay`, `343343234233123`) is deleted.
  The Dataset page shows the editor `Barcodes` on the review tool alone, which sends
  `barcode_file`. `scripts/review_server.py` is not changed. (Correction: the shared
  page did change for the review tool; the fix is in the entry "The review fixes of
  drink-atlas-workspace-f1" above.)
- The save delay of the code editors (owner message of 2026-09-25T09:51:46+0300): a save
  of a GTIN or a QR URL took a couple of seconds, because the page drew all 2,103 cards
  two times. The server write takes 1 to 4 ms. Each editor of a code now redraws its own
  card and the head line (`renderCodeCard`). In headless Chromium a GTIN save takes
  about 60 ms instead of about 540 ms. Read `ResearchLog.md`.
- Tests: `tests/test_codes.py` (12), `tests/test_seed_codes.py` (10),
  `tests/test_lab_server.py` (35). `README.md` (step 6), `SMOKE_TESTS.md` (S4, S5, WC1
  to WC3, WC10, WC11, WC15), and plans 07 and 11 follow. The lab server on 8168 was
  restarted with SIGTERM at about 10:27.

- The image preview of `/dataset/<slug>` (owner messages of 2026-09-25T10:08:37+0300 and
  10:10:04, answers of 10:13:53): the image stands in the vertical center of the stage.
  Thumbnails below it show `original` (the `main` image), `patched` with the badge `PATCH`
  when the wine has a patch, and `processed` with the badge `crop` or `seg`. A click on a
  thumbnail shows that image; `open raw image` of the processed file opens its original.
  A record of the review tool gets no thumbnail. The image keeps 104 px of the height for
  the thumbnails.
- `pipeline/lab_server.py`: `card_images` sends the new key `catalog_main_url`, the
  original of the `main` image, also when a `main_patched` image replaces it on the card.
- Tests: a new case in `tests/test_patches.py` (11). Checked in headless Chromium on a
  copy of the database, in light and dark mode, at 1400 px and 390 px.
- `README.md` (section "The Dataset page") and `SMOKE_TESTS.md` (PE12 to PE16) follow.

- Plan 14 (`docs/plans/14_patch-editor.md`): the patch editor of `/dataset` works on the
  lab server. Before, the page read `patch_dir is not configured`, because the lab server
  sent an empty `patch_dir`. The owner chose on 2026-09-25T09:53:00+0300: the database is
  the truth for the patches; `Apply` processes the file in the request; the change goes
  on top of the uncommitted work of the other sessions.
- New `pipeline/patches.py`: `store_patch` and `remove_patch`. A patch is a JPEG, PNG, or
  WebP file of at most 20 MiB; Pillow reads the type from the bytes. The file goes to
  `images/patched/<sha256>.<extension>`, or reuses the stored file with the same SHA-256.
  `derive.derive_all` processes it before the write transaction. When SAM3 does not
  answer, the patch is stored with no processed file and a warning. `match_method` is
  `manual`, and `source_name` is the file name of the upload. `remove_patch` deletes the
  row alone; the file stays in the store.
- `pipeline/lab_server.py`: `POST` and `DELETE` of `/api/dataset-patch`. The answer holds
  `patched`, `patches`, and `record`, the new record of the wine. `/api/dataset` sends
  `_patched` and `_patch_url` for each wine, the count `patches`, and `patch_editor: true`
  instead of `patch_dir`. `make_server` takes `segmenter`.
- `pipeline/pages/dataset.html`: the editor turns on with `patch_dir` (the review tool) or
  `patch_editor` (the lab server). It shows `_patch_url` when a record holds it. `Apply`
  sends the file name, takes `record` from the answer so the card image changes at once,
  and shows the warning of the answer. The page keeps its work on
  `scripts/review_server.py`.
- `pipeline/seed_patched.py`: a `main_patched` row whose wine has no file in the patch
  folder stays. The report line `rows deleted` is now `rows kept with no file in the
  folder`. So a seed run no longer deletes a patch of the editor.
- Tests: new `tests/test_patches.py` (10). `tests/test_seed_patched.py`: the delete test is
  now `test_missing_patch_file_keeps_the_row`. `tests/test_lab_server.py`: the list of
  disabled routes names `/api/dataset-alternative` instead of `/api/dataset-patch`. The
  editor was checked in headless Chromium, in light and dark mode, on a copy of the
  database: stage, `Apply`, reload, preview at `/dataset/<slug>/patch`, `Remove`.
- `README.md` (steps 3 and 5), `SMOKE_TESTS.md` (P4, new section PE), and plan 07 (step
  5) follow the change.

- The image preview of the Dataset page is addressable (owner message of
  2026-09-25T09:46:41+0300). The open preview puts the wine slug in the page path:
  `/dataset/<slug>` for the catalogue image, `/dataset/<slug>/patch` for the patch image.
  The open adds a history entry, so Back closes the preview; the arrow keys change the
  path and add no entry; the close gives `/dataset` again. A link to such a path opens
  the preview over the card of the wine. A slug that the list does not show gives the
  plain page at `/dataset`. A wine with the state `Removed` is not in the default list,
  so its link opens no preview.
- `pipeline/lab_pages.py`: the new pattern `DATASET_PREVIEW_ROUTE`. `pipeline/lab_server.py`
  and `scripts/review_server.py` serve `dataset.html` at the paths of that pattern too.
  Other paths under `/dataset/` answer 404.
- New test in `tests/test_lab_server.py`: `test_dataset_preview_paths_send_the_page`. The
  page was checked in headless Chromium on 8168 (open, arrows, close, Back, Forward, a
  direct link, an unknown slug, the scroll position). The patch path was not checked in
  a browser, because the lab server sends no patch images yet. New smoke tests D9f to
  D9h. The lab server on 8168 was restarted with SIGINT at 09:52:55.
- Plan 11 (`docs/plans/11_wine-codes.md`), approved by the owner: the GTINs, the
  barcodes, and the QR URLs of a wine are in the database. New schema file
  `pipeline/schema/008_wine_code.sql`: the table `wine_code` (`wine_slug`, `kind`,
  `value`). One wine MAY have more than one value of each kind; one value MAY belong to
  more than one wine. A GTIN is stored in its GTIN-14 form. New `pipeline/codes.py`
  checks each value: the GS1 check digit of a GTIN, the rules of a barcode, and the
  normal form of a QR URL of the old editor. New `pipeline/seed_codes.py` seeds the table
  from `svoe-vino-matcher/dataset/code-map.json`.
- `pipeline/lab_server.py`: `/api/dataset` sends `_gtins`, `_barcodes`, and `_qr_urls` of
  each wine and the counts `gtins`, `barcodes`, and `qr_urls`. `POST` and `DELETE` of
  `/api/dataset-gtin`, `/api/dataset-barcode`, and `/api/dataset-qr-url` write one row of
  `wine_code` (400 a bad value, 404 an unknown wine or value, 409 a value that the wine
  has). The key `barcode_file` is gone from `/api/dataset`. The JSON body check of
  `/api/wine-state` is now the method `_json_body`, shared with the new routes.
- `pipeline/pages/dataset.html`: a new editor `GTINs` above `Barcodes`. The GTIN input and
  the barcode input check the check digit while the person types; a bad value shows a
  red line below the input and disables the checkmark icon. The `+` buttons no longer
  depend on `barcode_file`. The header counts the GTINs. The text search finds a GTIN.
- Deploy: `data/lab.sqlite3` is at schema version 8. The seed added 23 GTINs and 3 QR
  URLs. The lab server on 8168 was restarted with SIGTERM, because SIGINT did not stop it
  (`ResearchLog.md`).
- New tests: `tests/test_codes.py` (16), `tests/test_seed_codes.py` (9), 8 in
  `tests/test_lab_server.py`, 1 in `tests/test_labdb.py`. `tests/test_labdb.py` expects
  version 8 and the table `wine_code`. The Dataset editors were checked in headless
  Chromium in light and dark mode on a copy of the database.
- `README.md` step 6, `COMMANDS.md`, plan 07 rule 5, and `SMOKE_TESTS.md` (S1, S3, S4,
  S12, and section WC) follow the change.

- The Embeddings page is on. `pipeline/lab_server.py` sends each route that
  `embedding_routes.handles` accepts to `embedding_routes.respond`, for GET, HEAD, and
  POST. `/embedding` is no longer in `DISABLED_PAGES`. `make_server` takes
  `config_path`; `main` passes `--config`. The old routes `/api/embedding` and
  `/img/embedding` stay HTTP 503. The navigation order is now `Dataset`, `Embeddings`,
  `Clusters`, `Testset`, `Runs`, in `NAV` and in the navigation of `dataset.html` and
  `embedding.html`. The owner asked for both on 2026-09-25. New tests in
  `tests/test_lab_server.py` (4): the page, the config path of the routes, the old
  routes, the navigation order. The lab server on 8168 was restarted.
- Plan 12 (`docs/plans/12_testsets-benchmark.md`), approved by the owner: the test sets
  in the database and a lab benchmark runner. New `pipeline/import_testset.py` imports
  `dataset/<set>/` read-only (photos, per-set labels, excluded slugs, variant groups). New
  `pipeline/benchmark.py` sends the photos of a set to a backend of `backends.yaml` and
  writes the run files of `scripts/match_run.py`. The tables are in
  `pipeline/schema_pending/NNN_testset.sql`; the file enters `pipeline/schema/` after the
  flat image store of drink-atlas-workspace-9a [f028b4]. No benchmark runs before that.
- `judge`, `f1`, `metrics_of`, `write_summary`, and their constants moved unchanged from
  `scripts/match_run.py` to the new `scripts/match_scoring.py`; `embeddings_of` moved to
  `scripts/match_backends.py`. Each moved item is byte-identical to commit `a8e113a`. With
  the variant groups of `my`, the moved `metrics_of` gives the `metrics.json` of the run
  `2026-09-24T131126Z-svm-siglip2-448-index-9fbef0a4a2` exactly.
- New rules 25 to 28 of `AGENTS.md`: a schema number is fixed only when the file enters
  `pipeline/schema/`. The sessions -a2, -9a, and -20 agreed; the owner approved.
- New tests: `tests/test_import_testset.py` (10), `tests/test_benchmark.py` (7).
- New file `ACTIVE_WORK.md` and rules 13 to 21 in `AGENTS.md`, section "Work of the
  sessions". Each agent session that works on this project keeps one section there: its
  task, its source, the files that it changes, its state, and the time of the last
  update. A session does not change a file that another section lists; it sends that
  session a message. The owner asked for the file.
- `COMMANDS.md`: the owner's command notes are fixed. The delete command names
  `data/lab.sqlite3`. The load section holds `import_catalog.py`, `seed_images.py`, and
  `seed_patched.py` in one block. The stale pasted replies and the fixed schema version
  are gone. The typo `Pапуск` is `Запуск`.
- `tests/test_seed_patched.py` names the columns of its `wine_image` insert. Schema file
  006 added `width` and `height`, and the insert by position failed.

### The embeddings of the lab: the build, the routes, the page (plan 10)

- New key `embeddings` in `config.yaml`: 11 entries, one for each image embedding model of
  gx10 on the screenshot of the owner, and `local-siglip2-so400m-patch16-naflex-p256`.
  Each entry has a name, an endpoint, options (`extra_body`), and the steps of the views
  `full` (variant C) and `label` (variant F). New key `embedding_python`: the venv
  `~/.venvs/svoe-vino-lab`.
- New module `pipeline/embeddings.py`: the configuration check, the inputs (Active
  wines; `main_patched` replaces `main`), the steps `segment`, `remove_background`,
  `white_background`, `resize`, the `embedding_hash`, the item status, the atomic files,
  the lock, and the job state.
- New CLI `pipeline/build_embeddings.py`: the backends `openai` (the gateway) and
  `local` (Hugging Face on `mps`). It writes `data/embeddings/<name>/index.json`,
  `vectors-<8 hex>.npy`, and `images/<sha256>_<view>.png`, and one JSON event line for
  each step to stdout. SIGTERM stops it after the present batch; the next run continues.
- New module `pipeline/embedding_routes.py` and page `pipeline/pages/embedding.html`:
  the combobox, `Build`, `Stop`, the job rows, and the wine matrix of the prepared
  images. The hook in `lab_server.py` waits for the commit of plan 09.
- The gateway drops the alpha channel (measured). So the configuration check rejects
  `remove_background` with no `white_background`, and a build fails each model input
  with a transparent pixel. The owner asked for an error on 2026-09-25.
- New `requirements-local.txt` and `QUESTIONS.md` (Q1, the label image: answered).
- New tests: `tests/test_embeddings.py`, `tests/test_build_embeddings.py`,
  `tests/test_embedding_routes.py`, with the fixture `tests/embedding_lab.py`: 44 tests.
- The first real build: `gx10-siglip2-so400m-patch16-naflex-p256`. A stop with SIGTERM
  after 416 items, and a second start that continued with the rest.

### An agent may restart the lab server on 8168

- New rules 22 to 24 in `AGENTS.md`, section "The lab server". The owner allows an agent
  to restart `pipeline/lab_server.py` on port 8168 when a change needs it: stop it with
  SIGINT, start it with `--no-browser` in the background with the log
  `work/lab_server.log`, check `/api/dataset`, and tell the owner.

### Each import processes its images: `crop` and `seg`

- New schema file `pipeline/schema/007_image_table.sql`: the table `image` with one row
  for each stored file, and the table `image_derivative` that links an original to its
  processed file. `wine_image` refers to `image`; `extension`, `width`, and `height`
  moved to `image`. The migration keeps each row. The owner chose option C.
- New module `pipeline/derive.py`. An image with transparent pixels loses its border
  (`crop`, the alpha rule of `build_cropped.py`). An image with no transparent pixels
  goes to SAM3 on gx10 with `wine bottle, can, packet` (`seg`); the largest instance
  wins, and its mask is smoothed, grown a little, and becomes the alpha channel. When
  SAM3 finds nothing, the white rule cuts the border. When SAM3 does not answer, the
  image stays unprocessed, and the next import asks again.
- New module `pipeline/imagestore.py`: the store functions of each writer.
- `pipeline/seed_images.py` and `pipeline/seed_patched.py` process each image that they
  store or keep, and take `--sam3 <URL>`. The processed files are PNG files in
  `data/images/cropped/`.
- The Dataset page shows the processed image with the badge `crop` or `seg`. The link
  `open raw image` opens the original. The size sort uses the processed file.
- Tests: `tests/test_derive.py` 14, `tests/test_seed_images.py` 25,
  `tests/test_seed_patched.py` 14, `tests/test_lab_server.py` 21, `tests/test_labdb.py`
  10. No test calls the real SAM3 service.
- The run on `data/lab.sqlite3` migrated it to schema 7 and processed the 2,018
  originals in 4 min 25 s: `crop` 1,876, `seg` 142. One `crop` comes from the white rule:
  SAM3 found no package on a bag-in-box image of three wines. The processed files take
  1.2 GB. A run of `seed_patched.py` on a copy of the database processed the 15 patches
  (`crop` 15). The real database holds no patch yet.
- A known weak result: on 3 bag-in-box images of Союз-Вино, SAM3 cuts out the bottle
  that is printed on the box, and not the box.

## 2026-09-24

### The Dataset page: sort by image size, and the slug links to the wine page

- New schema file `pipeline/schema/006_image_size.sql`: the columns `width` and
  `height` of `wine_image`. Both MAY be NULL.
- `pipeline/seed_images.py` reads the pixel size of each stored file with Pillow. A new
  row gets it; a kept row with no size gets it too. On `data/lab.sqlite3` the run filled
  2,046 sizes.
- `/api/dataset` sends `main_image_width` and `main_image_height`.
- The `Sort` control has `image size, smallest first` and `image size, largest first`.
  The key is the pixel count. A card with no known size stands at the end.
- The slug of a card is a link to `https://vino-svoe.ru/wines/<slug>`. It opens a new
  tab. The owner asked for it.
- `AGENTS.md` (`CLAUDE.md`) has the new rules 9 to 12: a schema change is allowed at any
  time during development, and the owner asks for a flatten later.
- Tests: `tests/test_seed_images.py` 22, `tests/test_lab_server.py` 20,
  `tests/test_labdb.py` expects schema version 6. New smoke cases I7a and S28 to S30.
  The tests of `seed_images.py` use real PNG pictures now.

### The patched main images: `pipeline/seed_patched.py`

- New CLI `pipeline/seed_patched.py`. It stores each file of
  `svoe-wino-hackaton/dataset/patched-official-2026-09-17/` as
  `images/patched/<sha256>.<extension>` and writes one `main_patched` row of
  `wine_image` for its wine. The file name before the extension is the wine slug.
- The patch folder is the truth for the patches, as the owner chose: a new file replaces
  the row of its wine, and a missing file deletes the row. The old file stays in the
  store. `match_method` is `slug-name`.
- The script skips hidden files, `_originals/`, and `README.md`. A slug that
  `wine_catalog` does not hold gets a message. Two files for one slug are an error.
- It reuses `sha256_of` and `store_file` of `pipeline/seed_images.py`, and
  `labdb.image_store` and `labdb.IMAGE_FOLDERS`.
- On a copy of the database: 15 rows added, 15 files written. The lab server shows the
  15 patches as card images.
- Plan 07 step 5, new tests `tests/test_seed_patched.py` (11 cases), smoke cases P1 to P7.

### The Dataset page shows the main images

- `GET /api/dataset` sends `main_image_url` in each record: the `main_patched` image of
  the wine, else its `main` image, else null.
- New route `GET /images/<folder>/<sha256>.<extension>` of the lab server. It sends one
  file of the image store `data/images/`, with a cache time of one year. It admits a
  name of 64 hex characters and an extension alone; another path gives 404.
- `pipeline/pages/dataset.html` loads `main_image_url` for the card image, the large
  view, and the filter `without a catalogue image`. A record of
  `scripts/review_server.py` still loads `/img/catalog`.
- `pipeline/labdb.py` holds `IMAGE_FOLDERS` and `image_store`. `seed_images.py` uses
  them.
- On `data/lab.sqlite3`: 2,046 cards show an image, 57 cards show `no catalogue image`.
  The owner selected option C; decision 9 of decision record 01 holds the options.
- The caption below the card image names the image type and the match, for example
  `main · name-unique`, instead of `catalog.jsonl`. `/api/dataset` sends
  `main_image_type` and `main_image_match_method` for it. A record of the review tool
  keeps `catalog.jsonl`.
- `.gitignore` holds `/data/` instead of `data/`. The first rule also ignored
  `tests/data/`.
- Tests: `tests/test_lab_server.py` 19 cases. New smoke cases S23 to S27.

### The Dataset page: no colour line, and the slug above the name

- A card no longer shows the line `Colour: …`. The owner asked for it. The colour stays
  in `full catalog.jsonl record` and in the search.
- The slug with its `copy` button is the first line of a card, above the name. The
  owner asked for it.

### The Dataset page: fast state changes, and `Ignore` is `Disable`

- A state click took 1.8 to 2.1 s. The server write took 2 to 4 ms. The time went to two
  full renders of the list: about 0.7 s each for 2,103 cards and 6.9 MB of HTML.
- A state change now renders its own card alone. A card that leaves the view of the
  `State` filter is taken out of the list. The busy mark goes on the buttons alone.
- Each card has `content-visibility: auto`. A full render takes about 0.14 s, and a
  state click about 0.1 s, in headless Chromium.
- A link `/dataset#<slug>` scrolls two times, so the card still lands below the header
  when the cards out of view have an estimated height.
- The owner renamed the button `Ignore` to `Disable`. The API action is `disable` now.
  The button, the action, and the state `Disabled` use one term.
- New smoke cases S21 and S22.

### The images of a wine: the table `wine_image` and `pipeline/seed_images.py`

- New schema file `pipeline/schema/005_wine_image.sql`: the table `wine_image`. One row
  links a wine, an image type, and a stored file by its SHA-256. The types: `main`,
  `main_patched`, `front`, `back`, `label_front`, `label_back`. A wine has at most one
  `main` and one `main_patched`. The columns `source_name` and `match_method` record the
  source file and the match.
- New script `pipeline/seed_images.py`. It finds the main image of each wine in the
  Strapi `uploads` folder by `csv_photo_name`, with stage 1 of `build_catalog.py`. It
  reads no network resource. It stores each file as
  `data/images/main/<sha256>.<extension>`. A wine with no match gets a console message.
- The run on `data/lab.sqlite3`: 2,046 of 2,103 wines matched (`name-unique` 2,023,
  `name-identical` 23), 57 no match, 2,018 files, 135 MB. A second run changes nothing.
- New folders `data/images/patched/`, `data/images/additional/`, and
  `data/images/testset/`. No tool fills them yet. The photos of the test sets get their
  own table later.
- New plan `docs/plans/08_seed-images.md` and decision 8 of decision record 01. Plan 07
  marks step 4 as done.
- Tests: `tests/test_seed_images.py` 19 cases. `tests/test_labdb.py` expects schema
  version 5 and the table `wine_image`. New smoke cases I1 to I9. The cases D2, D10,
  D10a, S1, and S3 expect schema version 5.

### Git ignores the whole `data/` directory

- `.gitignore` now holds `data/` instead of the two `*.sqlite3` rules. The directory
  holds the lab database and the image store `data/images/`. The owner asked for it.

### The Dataset page: state buttons and the state filter

- Each card holds buttons below the catalogue image. An `Active` wine: `Ignore` and
  `Remove`. A `Disabled` wine: `Enable` and `Remove`. A `Removed` wine: `Restore`. The
  card shows the tag `disabled`, `removed by import`, or `removed by person`.
- New filter `State`: `All (except Removed)`, the default, and `Removed`.
- New route `POST /api/wine-state` with the actions `ignore`, `enable`, `remove`, and
  `restore`. It allows the listed changes alone and answers 409 for another change. The
  lab server writes the columns `state` and `removed_by` alone; a GET stays read-only.
- New schema file `pipeline/schema/004_removed_by.sql`: the column `removed_by`
  (`import` or `person`) and a table check that ties it to `state`. It builds the table
  again and keeps each rowid. An earlier `Removed` wine gets `import`.
- `pipeline/import_catalog.py` restores only a wine that the import removed. A wine
  that a person removed stays `Removed`, and the report counts it under
  `kept removed by a person`.
- `Ignore` sets the state `Disabled`. No tool reads the state for embeddings and matches
  yet. Decision 7 of decision record 01 records the choices of the owner.
- Tests: `tests/test_labdb.py` 9, `tests/test_import_catalog.py` 20,
  `tests/test_lab_server.py` 15 cases. New smoke cases S13 to S20, D10a, and D10b.

### The Dataset page: no source panel

- The owner removed the source panel above the list: `catalog.jsonl`, `patch directory`,
  `alternative directory`, `barcode file`, and the two Atlas lines. The panel and its
  style are gone from `pipeline/pages/dataset.html`.
- An error of `/api/dataset` shows in the list now, with its reason.
- `/api/dataset` of the lab server no longer sends `catalog_file`. Only the panel read it.

### The catalogue import: add and remove wines

- New schema file `pipeline/schema/003_wine_state.sql`. It adds the column `state` to
  `wine_catalog`: `Active`, `Disabled`, or `Removed`, with the default `Active`. It drops
  the table `catalog_source`. The database keeps no record of the imported files.
- New CLI `pipeline/import_catalog.py`. It replaces `pipeline/seed_catalog.py`, which is
  removed. The first import into an empty database adds every wine. A later import adds
  the new wines as `Active`, and marks each missing `Active` or `Disabled` wine `Removed`.
  A `Removed` wine that comes back becomes `Active`. A `Disabled` wine in the CSV stays
  `Disabled`. A changed field of a wine stops the import, and the error names each field.
  The import writes all changes in one transaction under the write lock.
- New fake variants of the official CSV in `tests/data/`, from
  `tests/data/make_catalog_variants.py`: v2 and v3 add and remove wines, v4 changes one
  field. `tests/data/README.md` states the expected import results.
- The lab server sends `state` in each record of `/api/dataset`, and the start report
  counts the wines of each state.
- Tests: `tests/test_seed_catalog.py` is replaced by `tests/test_labdb.py` (7 cases) and
  `tests/test_import_catalog.py` (17 cases). `tests/test_lab_server.py` has 11 cases.
- Plan 07 steps 1 and 2 and decision 6 of decision record 01 describe the rules.

### The lab server: the Dataset page on the database

- `config.yaml` holds two keys now: `rootdir` and `database_file`. The owner removed each
  JSON file and each directory. The database is the only source of the lab data.
- New `pipeline/lab_server.py` on port 8168. It opens the database read-only for each
  request and checks the schema version. `GET /dataset` serves the Dataset page.
  `GET /api/dataset` answers the 2,103 rows of `wine_catalog`, with `wine_slug` under
  the key `slug` of the page.
- Clusters, Embeddings, Testset, Runs, and `/docs` are disabled for now. Each one answers
  the new notice page `pipeline/pages/disabled.html` with HTTP 503 and the full
  navigation. Each other `/api/` route answers HTTP 503 with a JSON error. No part of a
  page is removed.
- The Dataset page and the colour theme moved out of `scripts/review_server.py` into
  `pipeline/pages/dataset.html` and `pipeline/pages/theme.css`. New
  `pipeline/lab_pages.py` reads them for both servers. Each page string of
  `review_server.py` stayed byte-identical at the move.
- Fix on the Dataset page: `safeUrl` gives no link for an empty value. Before, a record
  with no `page_url` or `image_url` got `site page` and `source image` links to the
  Dataset page itself.
- Port 8168 is recorded in `PORTS_USED.md`. The review tool of `svoe-vino-testset` keeps
  8154.
- The database file is `data/lab.sqlite3` now, with no delivery directory. The owner
  chose the flat layout. `database_file` stays relative to `rootdir`, so its value is
  `svoe-vino-lab/data/lab.sqlite3`. `.gitignore` excludes `data/**/*.sqlite3` at any
  depth. The earlier rule `data/*/*.sqlite3` did not match the flat file.
- New tests `tests/test_lab_server.py`, 10 cases. New smoke cases S1 to S12.
- The tools of `scripts/` read JSON files through `scripts/common.py`. They do not start
  with the new `config.yaml`, and their 5 test modules stop at the import.

### Project rules and the log of the owner messages

- New `AGENTS.md` with the rules of this project. `CLAUDE.md` is a symbolic link to it.
  The file links to the workspace rules in `../CLAUDE.md`.
- New rule: an agent records each message of the project owner verbatim in
  `docs/owner-messages.md`, before the work on it starts. The log starts with the
  messages after 2026-09-24 21:37. Earlier messages are not recorded.

### The lab database: the key column is `wine_slug`

- New schema file `pipeline/schema/002_wine_slug.sql`. It renames the column `slug` of
  `wine_catalog` to `wine_slug`, the name of `code-map.json` and `embedding-ignore.json`.
  SQLite renames the column in the `CHECK` constraint too.
- `pipeline/labdb.py` applies the file to an existing database at version 1. The rows
  stay. A new database gets schema version 2.
- `pipeline/seed_catalog.py` writes the column `wine_slug`.
- New test: a version 1 database keeps its rows and its constraint after the rename.
- Plan 07, rule 8: the key column of a wine is `wine_slug`.

### The lab database: steps 1 and 2

- New plan `docs/plans/07_sqlite-lab-database.md` and decision record
  `docs/decisions/01_sqlite-lab-database.md`. One SQLite database holds the lab state of
  one catalogue delivery. The tables are in BCNF.
- New `pipeline/labdb.py`. It creates the database and applies the schema files of
  `pipeline/schema/` in number order. `PRAGMA user_version` holds the version.
- New schema file `pipeline/schema/001_wine_catalog.sql`: the tables `catalog_source` and
  `wine_catalog`. The columns of `wine_catalog` are the nine columns of
  `strapi_output0709.csv`, with the names of `catalog.jsonl`.
- New CLI `pipeline/seed_catalog.py`. It seeds `wine_catalog` from a Strapi CSV. It trims
  each value, drops exact duplicate rows, and stops on two different rows for one slug.
  It refuses a database that is not there and a second delivery.
- New database `data/catalog-2026-09-17/lab.sqlite3`: 2,103 wines from 4,147 CSV rows.
  All 2,103 × 8 values equal `catalog.jsonl`. `.gitignore` excludes the database file.
- New tests `tests/test_seed_catalog.py`, 13 cases.

### Manual cluster rule editor

- Each `Label rule` block on `/clusters` has an `Edit rule` button.
- The editor changes the rule text, the questions, and each card's expected answer.
- The editor can add or remove questions. A rule has at most three questions.
- New route `POST /api/cluster-rule-edit` stores the edit.
- The server applies the rule checks again. It recomputes the valid questions and the
  mode.
- A manual edit keeps the build identity. A later VLM rebuild replaces the edit.

### Model input previews on the Runs page

- A click on a matched photo now opens a lazy strip of the derived images that the
  matcher passed to an embedding model.
- The same strip shows the query images that the matcher passed to a VLM. Each such
  preview has a `VLM` badge.
- New route `GET /api/run-inputs` rebuilds the model-bound bytes from the run, the
  matcher configuration, and the content-addressed crop cache. It does not call a
  model or SAM3.
- The route checks the source SHA-256. It refuses an inexact reconstruction after the
  source image changes.
- A barcode or QR short-circuit states that no embedding model ran.

### External pictures in the Testset sideboard

- The Testset sideboard accepts image files from the desktop and images dragged from
  another browser page.
- A dropped picture goes directly into the durable `my/` inbox. It has no wine, label,
  score, or comment. The page shows it at once for future distribution.
- New routes `POST /api/inbox-upload` and `POST /api/inbox-fetch` store the two forms
  of external drop.
- The server reads the image type from the bytes. It removes path parts and unsafe
  characters from the source name. It does not replace a file with the same name.
- The empty sideboard and its help text now state that it accepts external images.

### Embedding input page

- Every page uses the navigation order `Dataset`, `Clusters`, `Embeddings`, `Testset`,
  `Runs`. The earlier `Review` label is now `Testset`.
- New page `/embedding`. It shows the cropped main image and segmented label in one
  column. Each additional view gets another column with its full image and label.
- Every image cell uses a checkerboard. A missing derived file stays visibly missing.
- The Show filter has `Patched image` for wines whose main image comes from a patch.
- Each prepared image has an `Ignore` or `Use` control. The page writes
  `svoe-vino-matcher/dataset/embedding-ignore.json`.
- An ignored image stays visible in grayscale. Its dashed border and `Use` button
  identify the state.
- The matcher filters the four image kinds independently. The ignore fingerprint
  changes every affected index file name.
- A label pipeline MAY name `source.alternative_dir` to index segmented labels of
  additional views.

### Checkerboard preview for Dataset images

- A click on a catalogue image or a patch image opens a checkerboard modal over the
  Dataset page. It does not open a new page.
- A border shows the displayed image boundary. The header shows the natural pixel
  dimensions and the file name.
- Arrow buttons and the Left and Right keys move through the current filtered and
  sorted list. Escape closes the modal without changing the page scroll position.
- The preview scales a tall image to fit the available height. It shows no scrollbar.
- The preview has an `open raw image` link.
- Image elements and API clients continue to get the original image bytes.

### All Dataset records on one page

- The Dataset page shows all records that pass the current filter.
- The `Rows`, `Previous`, and `Next` controls are removed.
- Search waits 180 ms after input before it rebuilds the full list.
- Catalogue and patch images keep native lazy loading.
- A row does not show the wine description. The description stays searchable and stays
  in `full catalog.jsonl record`.

### Label-only cluster rules

Plan: `docs/plans/06_label-only-cluster-rules.md`. The owner chose the label crops with
a label-only prompt, and the vintage policy in the same rebuild.

- Stage 2 of `scripts/cluster_rules.py` sends the label crop of each card from
  `bottle_label_dir` on white, scaled to a long side of 768 pixels, UP or down. A card
  with no label crop sends its catalogue picture with a caption that states it.
- The prompt of stage 2 allows only features that are printed on the label. It states
  that some catalogue pictures are drawings, and that a drawing shows only the label
  correctly. It asks for texts exactly as the label prints them, in their own alphabet.
  It allows a vintage question only when the catalogue names of two cards state two
  different years.
- A card that shares its catalogue picture with another card of its cluster gets a
  caption that names that card: 43 cards of 21 clusters.
- The label description goes into stage 2 without the key `bottle`. Stage 1 does not
  change.
- `check_rule` enforces two new kinds. A question of kind `bottle` (the glass, the
  liquid, the capsule, the cork, the shape of the bottle) is never valid, and a rule text
  about such a feature gives mode `none`. A question of kind `vintage` keeps a year only
  when the name or the slug of the card states it.
- `RULES_SHA` holds the picture setting and the captions, and `rule_inputs_sha` holds
  the paths of the label crops. Every rule of 2026-09-23 became stale, and all 255 rules
  are built again. The old rules file is kept as
  `work/catalog-cluster-rules.2026-09-24T082150.json`.
- The page `/clusters` names the reason for a struck question of kind `bottle` or
  `vintage`.
- `scripts/cluster_rules_report.py` has the option `--rules` for the post hoc score of
  an older run, and a section with the paired numbers for each half of the wines.
- The vintage variants, added by the owner during the rebuild: when cards differ only
  by the vintage year, and one card states no year, that card is the card of every
  vintage that no other card states. A year counts from the name, the slug, or the
  label description. Only the 43 mixed clusters get the note `VINTAGE_NOTE` in their
  prompt, so the other rules stay current. `check_rule` keeps the mark `other` only for
  a card with no year that differs from a card with a year only by the vintage.
- `README.md`, `SMOKE_TESTS.md` (L16 to L23), and `ResearchLog.md` describe the change.
- The benchmark: run `runs/2026-09-24T080721Z-svm-label-gw-cluster-rules-label-only-rules`.
  Against the base, R@1 0.8161 → 0.8355, 61 wins, 30 losses, p 0.002; negatives
  0.8262 → 0.8451. Against the run v2, +0.0038 R@1, p 0.47, not significant. The
  section «Result» of the plan holds the details.
- The plan holds six open questions for the owner, Q1 to Q6.

### Drink Atlas Core product binding on the Dataset page

- Each Dataset row shows its effective Drink Atlas Core product UUID.
- An `open` link after `copy` opens the matching product page on the local Drink Atlas
  Core service at `http://127.0.0.1:8157/products/<uuid>`.
- Automatic matches come from `atlas_matches_file`. The page marks them `automatic`.
- The `+` or `edit` button opens a UUID input with save checkmark and cancel cross
  icons. The checkmark writes a manual binding. The cross cancels and writes nothing.
- `POST /api/dataset-atlas-binding` writes the manual overlay in
  `atlas_bindings_file`. A manual value replaces the automatic value for that slug.
- The automatic match file does not change. Several Svoe Vino slugs MAY bind to one
  Atlas product UUID.

### Barcode and QR URL entry on the Dataset page

- Each Dataset row shows its product barcodes and a `+` button.
- The `+` button opens a text input with save checkmark and cancel cross icons. The
  checkmark writes the value. The cross cancels the new row and writes nothing.
- `POST /api/dataset-barcode` adds one value to `barcode_file`. One slug MAY have more
  than one value. A value cannot belong to two slugs.
- Each saved barcode has a small red `×` button. A confirmed click removes only that
  barcode. The server preserves the QR code and the other fields of the wine record.
- `DELETE /api/dataset-barcode?slug=<slug>&barcode=<value>` performs the removal. A
  wine with no barcode keeps its structured record with `barcode: null`.
- Each Dataset row has a `QR URLs` editor with the same `+`, save checkmark, cancel
  cross, red `×`, and `copy` controls. Each saved URL also has `open`.
- `POST` and `DELETE /api/dataset-qr-url` add and remove URL values in the `qr_code`
  field. The server normalizes the URL and prevents one normalized URL from belonging
  to two wines.
- The barcode matcher already reads `qr_code`. A matching scanned URL identifies the
  wine before visual matching.
- The page and `svoe-vino-matcher` share `svoe-vino-matcher/dataset/code-map.json`.

### Alternative photos on the Dataset page

- Each Dataset row has an `Alternative photos` area at the right. It accepts multiple
  images by drag and drop or by a file chooser.
- Additions appear as candidates. Active images can be marked for removal. `Apply`
  writes all pending changes of the row. `Cancel` writes nothing.
- `alternative_dir/<slug>/` holds the active files. A removal moves a file to
  `alternative_dir/.trash/<slug>/` for recovery.
- `POST` and `DELETE /api/dataset-alternative` apply the staged changes.
- `svoe-vino-matcher` reads the same directory and indexes every file as another view
  of the slug. An alternative does not replace the main catalogue picture or a patch.

### Patch changes on the Dataset page

- A `no patch` place accepts an image by drag and drop or by a file chooser. The page
  shows the image as a candidate. It writes the file only after `Apply`.
- An existing patch has a `Remove` button. Removal stays pending until `Apply`.
  `Cancel` discards a pending addition, replacement, or removal.
- `POST /api/dataset-patch` applies an image. `DELETE /api/dataset-patch` applies a
  removal. The server validates the slug, the size, and the image bytes.
- A replaced or removed patch moves to `patch_dir/.trash` for recovery.
- Existing package crops and label crops for the slug move to `.trash` in their
  directories. Another page cannot keep showing pixels from the old patch.

### The dataset `vlmrerank-8b-failed`

- New dataset `vlmrerank-8b-failed` in `config.yaml`. It holds the positive photos of
  `default` whose true slug was not at rank 1 in the run
  `2026-09-18T195710Z-svm-vlmrerank-8b-siglip2-448-bench`.
- The run holds 184 such photos. 180 photos of 108 wines are copied into
  `dataset/vlmrerank-8b-failed/photo/`. Each file keeps its path `<slug>/<file>` and the
  SHA-256 that the run recorded.
- 4 photos stay out, because their label in `default` is `negative` now:
  `abrau-dyurso-az-abrau-bayanshira-beloe-suhoe-12/02_manual.jpg`,
  `abrau-dyurso-russkoe-igristoe-koshernoe-bryut-shardone-beloe-13/04_conf095.jpg`,
  `abrau-dyurso-udelnoe-vedomstvo-imperatorskoe-beloe-bryut/01_conf095.jpg`, and
  `inkermanskiy-zmv-inkerman-muskat-polusladkoe-beloe-13/01_conf095.jpg`.
- The label entries of the 180 photos and the notes of their wines are copied without
  a change. `excluded-slugs.json`, `variant-groups.json`, and `manual-groups.json` are
  copies of the files of `default`. 9 photos lie on excluded slugs, so a run takes 171
  photos.
- `dataset/vlmrerank-8b-failed/selection.json` records the rule, the source run, and
  each of the 184 photos.
- The runs of the set go to `dataset/vlmrerank-8b-failed/runs/`. Port 8167 is assigned
  to the review tool of this set.
- `README.md`, `ResearchLog.md`, and `SMOKE_TESTS.md` (F1 to F5) describe the set.

## 2026-09-23

### Dataset validation

- The Dataset page has a `Validate` button. Its dialog explains and runs three
  read-only checks: the website slug set, exact source image bytes with SHA-256,
  and the source image file on each `wine_slug` page.
- The checks run in one background job. The dialog shows progress and keeps the
  last result when it is closed and opened again.
- New routes `GET /api/dataset-validation` and `POST /api/dataset-validation`.
  The POST route refuses a second job while one job runs.
- The slug check reads the public wine sitemap. The page check reads `og:image`.
  The image check states that a resize service can re-encode the same visible image.

### Dataset page

- New page `/dataset`. It shows every record of the configured `catalog.jsonl`.
- Each row shows the unmodified catalogue image and the patch image next to it.
  A row with no patch shows an explicit `no patch` place.
- The page shows the main catalogue fields in the row. The control
  `full catalog.jsonl record` shows every field of the source record.
- Search reads every field. Filters select patched records, unpatched records, or
  records without a catalogue image. Pagination keeps the page responsive.
- New read-only routes `GET /api/dataset`, `GET /img/catalog`, and `GET /img/patch`.
- The navigation of every page includes `Dataset`.

### The benchmark of the cluster rule step

- Run `runs/2026-09-23T224548Z-svm-label-gw-cluster-rules-qwen38max-rules-v2`: R@1
  0.8156 -> 0.8313, 47 wins, 22 losses, exact McNemar p 0.004; without the `confusion`
  clusters 0.8244, p 0.038. `ResearchLog.md` and the section «Result» of
  `docs/plans/05_cluster-label-rules.md` hold the analysis. A first full run was stopped
  after about 600 photos for the verdict fault of `svoe-vino-matcher`.
- The rules of the 99 clusters that the test set cannot trigger are built after the
  benchmark, for the page `/clusters`.

### Stage 2 of the label rules runs on `qwen3.8-max`

- The owner's decision: stage 2 runs once, so it uses `qwen3.8-max` of the QwenCloud
  Token Plan, with thinking, 4 requests at a time. New keys `rules_url`,
  `rules_model`, `rules_api`, `rules_key_env`, `rules_thinking`, `rules_workers`, and
  `rules_timeout_s` in the block `cluster_rules` of `config.yaml`. The key is read from
  `QWENCLOUD_TOKEN_PLAN_API_KEY` at run time.
- Stage 1 and the re-rank keep the local `qwen3.5-9b`.
- The prompt of stage 2 keeps only major differences. Every rule is therefore stale
  and is built again.
- `scripts/11_cluster_rules.py` builds the rules of stage 2 in parallel.
- A mark that only some cards carry, such as a kosher mark, gets a yes/no question
  with "yes" or "no" for each card. Before this rule the check struck every kosher
  question, because only one card held a non-null answer.

### The letters of a rule on the page `/clusters`

- `GET /api/clusters` gives the map `letters` of each rule: the letter that stage 2
  used for a card, to the slug of that card.
- The badge of each card and the head of the sheet show the letter beside the number,
  and `the cards of the letters` under the rule text names the card and the slug of each
  letter. The prompts do not change.

### The answer of the VLM rule step on the page `/runs`

- A row whose candidates hold the `explain` record of the cluster rule step shows a box
  `VLM` under the frame of the top cluster: the mode, the cluster id, the time of the
  call or `from the cache`, each question with the answer, the score of each card of the
  window, and whether the answer moved a card to rank 1. A run that did not record the
  questions takes their text from the current rule, and the box states that.
- New filters `rule_acted` and `rule_changed` of `GET /api/run` and of the page.
- The strip of the candidates aligns its cards at the top, so a card next to the box
  keeps its height.
- `README.md`, `docs/API.md`, `docs/openapi.yaml`, and `SMOKE_TESTS.md` (R30 to R33)
  describe the change.

### Label rules for the catalogue clusters

Plan: `docs/plans/05_cluster-label-rules.md`.

- New stage `scripts/11_cluster_rules.py` with the module `scripts/cluster_rules.py`.
  Stage 1 asks the VLM `qwen3.5-9b` (thinking off) to describe the label of each card
  of each cluster. Stage 2 asks where the labels of one cluster differ, and writes the
  cluster rule: a difference sheet of questions with the expected answer of each card,
  and a rule text. The note of the reviewer goes into stage 2. The code drops a question
  about a bottle number, and a question about the alcohol value when another question
  separates the cards.
- New files `dataset/catalog-cluster-rules.json` (the descriptions and the rules) and
  `dataset/catalog-cluster-notes.json` (the notes of the reviewer).
- New block `cluster_rules` of `config.yaml`.
- `.gitignore` ignores the lock files `*.lock` next to the two new JSON files.
- `GET /api/clusters` adds `key`, `notes`, `rule` and `rule_status` to each cluster,
  the label description to each card, and the field `rules`.
- New routes `POST /api/cluster-note` and `POST /api/cluster-rule`.
- The page `/clusters` shows a `Label rule` block in each cluster, with the sheet, the
  rule text, the note editor, and the buttons `Save note` and `Rebuild rule`. Each card
  shows its `label description`. New filter `Rule`.
- The note of the «Фантом» cluster is stored: «pay attention to numbers in bottom left
  corner of bottle (30/70), (50/50), (70/30)».
- `match_backends.parse_answer` keeps the field `explain` of a candidate.
- New backend `svm-label-gw-cluster-rules` in `backends.yaml`: the pipeline
  `cluster-rules-difference-gateway` of `svoe-vino-matcher` on port 8164, with
  `explain=1`.
- New script `scripts/cluster_rules_report.py`: the report of one run against its base,
  with a replay over the clusters without the `confusion` signal.
- `config.yaml` names the indexes of 2026-09-23 for the clusters: `gateway-6e12e149fe`
  and `gateway-b57810da3d`. The new build of `dataset/catalog-clusters.json` holds the
  same 255 clusters and the same links as the build of 2026-09-22. The old file is
  kept as `work/catalog-clusters.2026-09-22T231210.json`.
- `docs/API.md`, `docs/openapi.yaml`, `README.md`, `SMOKE_TESTS.md` (L1 to L14) and
  `ResearchLog.md` describe the change.

### The cluster frame of the page `/runs`

- Two or more candidates that stand next to each other in the strip and belong to one
  catalogue cluster now share one frame in the accent colour. The tooltip of the frame
  names the cluster id, the kind, and the size. A cluster card that stands apart from
  the others gets no frame.
- The frame holds a link to the cluster details. The link opens `/clusters` and scrolls
  to that cluster.
- The page reads `GET /api/clusters` once at start. When the cluster file is missing
  or the request fails, the page shows no frame and works as before.

### Backend for the hard cases

- New backend `svm-label-gw-difference` in `backends.yaml`. It asks the pipeline
  `difference-ensemble-gateway-photo-label` of `svoe-vino-matcher` on port 8164: the
  gateway ensemble, re-ranked inside one producer by the label words that separate
  its cards. Plan: `svoe-vino-matcher/docs/plans/02_sibling-difference-rerank.md`.

### Cropped catalogue photos

- New key `bottle_cropped_dir` of `config.yaml`. It names the catalogue photos without
  their empty border, one PNG file per wine slug.
  `svoe-wino-hackaton/scripts/build_cropped.py` writes them. The project owner asked
  for these pictures for display and for training.
- `common.catalogue_picture` states the order of the catalogue picture: the crop, then
  the patch, then the photo of the catalogue record. `GET /img/bottle`, the field
  `bottle_path` of the agent API, `scripts/08_variants.py`, and `scripts/03_embed.py`
  use it. The mark `patched` does not change.
- A patch that changed after its crop wins over the crop, because such a crop was cut
  from the picture before the correction. The tool prints a warning at start for each
  such patch.
- The pixel checks `candidate_is_catalog_photo` and `catalog_photo_twin` still read the
  catalogue photo of the delivery, because they look for a copy of that photo.
- `scripts/03_embed.py` scores only the candidates that have no `sim` yet. The scores of
  earlier runs were made against the old reference and stay as they are.
- New backends `svm-siglip2-448-bordered` and `svm-siglip2-448-cropped`. Each one pins
  the index file of `siglip2-448`, so the two pictures of the catalogue are compared on
  one server with no restart.
- New backends `svm-crop-ab-bordered-<pipeline>` and `svm-crop-ab-cropped-<pipeline>` for
  seven pipelines. The `bordered` entries ask a temporary baseline server on 8165, which
  was stopped after the runs of 2026-09-23, so they answer nothing now. The runs are
  `runs/2026-09-23T0*-svm-crop-ab-*`. The result is in `svoe-vino-matcher/ResearchLog.md`,
  entry "The cropped catalogue pictures in seven more pipelines".

## 2026-09-22

### The large view of the page `/clusters`

- A click on a card picture or on a confused photo opens a large view. The caption
  names the card, or the photo and the card that the run answered, and states the
  place in the cluster and in the view.
- `Left` and `Right` move over the images of one cluster: the cards first, then the
  confused photos. `Up` and `Down` open the same place in the previous or the next
  cluster, hold at its last image when the place is after its end, and scroll the page
  to that cluster. The first and the last image hold. `Esc` or a click on the dark
  ground closes the view. The view holds four buttons for the same moves.
- This follows the large view of the runs page. A click with a modifier key still
  opens the picture in a new tab. A click on a confused photo no longer opens the
  review page; the link `review` of the caption does that, in a new tab.
- The old picture is hidden while the next one loads, so the caption never stands
  under the picture of the step before.

### Catalogue clusters, and the page `/clusters`

- Added `scripts/10_clusters.py`. It finds the clusters of catalogue cards that the
  matcher confuses, or can confuse, over the whole catalogue of 2,103 cards. It
  writes `dataset/catalog-clusters.json`. A later re-rank step reads the same file.
  The plan and the four decisions of the owner are in
  `docs/plans/04_catalog-clusters.md`.
- Four signals join two cards: `name` (same producer, name and category after
  normalisation, and grapes that agree), `photo` and `label` (the SigLIP 2 cosine of
  the catalogue photos and of the label crops, at or above 0.95), and `confusion` (at
  least 2 positive photos that a run answered as the other card). A link records every
  signal that passed, and the cosines also when they did not pass.
- The vectors come from the index files of `svoe-vino-matcher`, so the script calls no
  service and runs in under a second.
- `config.yaml` gained the block `clusters`. `scripts/common.py` reads it as
  `CLUSTERS` and `CLUSTERS_FILE`, and the start report of every script names
  `clusters_file`.
- The review tool serves the new page `GET /clusters` and the route
  `GET /api/clusters`. The page shows the photos of each cluster side by side, the card
  fields, the label counts, and the evidence of each link with the confused test
  photos. It writes nothing. `/clusters#<slug>` opens the cluster of a card. The route
  reads the file at each request, so a new build needs no restart.
- Every page gained the link `Clusters` in its navigation.
- `variant-groups.json`, `scripts/08_variants.py`, and the review table did not
  change.
- Measured with the defaults: 255 clusters over 630 cards, the largest of 10 cards;
  53 `same-wine`, 22 `mixed`, 180 `look-alike`. The three Abrau-Durso Pinot Noir cards
  stand in one cluster with the Cabernet Sauvignon `-125` of the same label line. Read
  `ResearchLog.md` for the choice of the defaults.

### Three backends for the label experiment

- `backends.yaml` gained `svm-label-gw-photo`, `svm-label-gw-label` and
  `svm-label-gw-ensemble`. They answer from `svoe-vino-matcher/config.label.yaml`
  on port 8164, not from the main config on 8158, so the label experiment is
  measured without a change to the recognizer that serves 8158.
- The three differ in ONE thing: which picture is embedded. `-photo` embeds the
  whole query photo against the whole-picture index, `-label` embeds the SAM3
  label crop of that photo against an index of catalogue label crops, and
  `-ensemble` sums the two. The comment in `backends.yaml` states how to start
  that server and how to fill the query crop cache before a run.
- The first measurement is in `runs/2026-09-22T18*-label-exp`. Over 1,600
  positive photos the whole picture holds R@1 0.7594, the label crop 0.7431
  (p = 0.194, not established), and the two together 0.7931 (+0.0337,
  p = 0.000449). Read `svoe-vino-matcher/ResearchLog.md`.

### The review table shows the package, the label, or the label box

- The tool bar holds the control `Image` with the three values `package`,
  `label`, and `label box`. `package` is the catalogue photo, or the patch of
  that photo, as before. `label` is the label cut out of that photo with SAM3.
  `label box` is the bounding box of the label alone.
  `svoe-wino-hackaton/scripts/build_labels.py` writes the two crop directories,
  and it cuts the label out of the patch when the wine has one.
- `config.yaml` gained the two generic keys `bottle_label_dir` and
  `bottle_label_box_dir`. `scripts/common.py` reads them and holds
  `load_bottle_labels()`. An absent key gives no crop of that kind. A configured
  directory that is not on disk gives a warning at the start, and the tool runs.
- A label crop does NOT replace the catalogue photo, unlike a patch. It is a
  second view of the same photo. This is why the tool holds a selector for the
  crops and no selector for the patches.
- `GET /img/bottle` gained the parameter `kind`. A wine with no crop of the asked
  kind answers with its package picture, so a view never holds a hole. An unknown
  kind answers with the package picture as well.
- Every row carries `has_label` and `has_label_box`; the wine record also carries
  `label_path` and `label_box_path`. The page draws the mark `no label` in the
  bottom right corner of a picture that fell back, so the mark stands beside the
  mark `patched` and not over it. The pickers draw a dot in place of the word.
- The control acts on the whole review page: the table, the large view, the move
  target list, and the group picker. The runs page is unchanged.
- The control travels in the query string as `img`, beside `filter`, `sort`, and
  `slugs`. `/?img=label` opens the table on the label crops.
- The control is hidden when no wine has a crop, because the choice would then
  say nothing.
- A label crop is RGBA and its alpha channel holds the mask. The page puts such a
  picture on white, so a white label edge stays visible in the dark theme.
- The tool reads both directories again at every `GET /api/reload`.
- `docs/openapi.yaml`, `README.md`, and `SMOKE_TESTS.md` state the selector. The
  first build of the crops covers 2,070 of the 2,103 catalogue cards.

### The `Show` list of the review table holds the benchmark scope

- The control `Show` gained two entries: `excluded from the benchmark` and
  `included in the benchmark`. The reviewer looks for the excluded wines in that
  list, so the scope now stands there as well.
- The control `Slugs` (`all` / `included` / `excluded`) is unchanged. The two
  controls state the same scope, and one of them is enough.
- Both new entries ask about the card, not about its photos, so they joined
  `CATALOG_SCOPE_FILTERS`. A catalogue card with no directory in `my/` can be
  excluded too, and it reaches the list.
- The two controls can contradict each other, for example `Show` on `excluded`
  with `Slugs` on `included`. The table is then empty. The count line names the
  reason, in the same way as it does for `failed a check`.
- Checked against the running dataset `my` with its 14 excluded slugs:
  `all` gives 2107 rows, `excluded` gives 14, `included` gives 2093 and keeps
  the 246 catalogue-only cards.

## 2026-09-21

### A backend MAY pin an index, and the run records which one answered

- New backend `svm-siglip2-448-prepatch` in `backends.yaml`. It is the SAME
  pipeline and the SAME server as `svm-siglip2-448`, with
  `query: { limit: 10, index: siglip2-12041b8834 }`. That is the index of
  2026-09-18, built before the 6 patched catalogue photos existed, so the pair
  measures what the patches are worth in one benchmark, with no restart and no
  second model in memory.
- No code was needed for that: `match_backends._url` already puts every key of
  `query` into the query string.
- **Defect found and fixed in the same change.** `embeddings_of` read the
  `embeddings` block of the pipeline, which is the index the pipeline OWNS. A
  backend that pins another index therefore recorded the wrong provenance: two
  runs that read different vectors stated the same age. The first paired run
  showed it — the server log proved 40 requests used
  `index=siglip2-12041b8834.npz` while `run.json` claimed
  `siglip2-d3a1b76f7e.npz`. `embeddings_of` now reads `index` from the backend
  URL, takes the build time from `available_indexes` of that pipeline, and
  marks the block `pinned_by_backend: true`. A pinned index the server does
  not offer, and a pinned index on a pipeline that owns none, each record a
  reason instead of a wrong age.


### The virtual NULL wine: a photo that matches no card of the catalogue

- The review table holds a new first row, the NULL wine. It is a virtual wine
  with the reserved slug `__null__`. A photo that lies under it matches NO card
  of the catalogue. Until now the reviewer could state "not this wine"
  (`negative`) and could not state "no card of the catalogue".
- The row takes a photo in four ways: a drag onto the row, the key `0` in the
  large view, the entry `No match in the catalogue (NULL)` of the context menu,
  and the last entry of the move dialog. Each way records a move, and `apply`
  moves the file into `<photo_dir>/__null__/`, as for every other move.
- The row stands first, and no filter and no search take it away, so the drop
  target is always there. It is built whether the directory is present or not;
  the first `apply` makes the directory.
- The place is the statement: a photo there needs no label. The card takes
  `positive`, which confirms it, and `unusable`, which takes the photo out of
  the set. `POST /api/label` answers `400` for `negative` and for `variant`
  there, and `POST /api/copy` refuses `__null__`: both judge a photo against a
  wine, and NULL is not a wine.
- These photos are out of the labelling progress of the header. The header
  counts them apart as `no match`, with the pending moves in brackets.
- `scripts/match_run.py` reads them as rejection cases. Such a photo enters the
  query set with the label `no_match` and no truth. No answer is the only
  correct outcome, and every card at rank 1 is `false_match_at_1`.
  `metrics.json` gained the block `no_match` with `n`, `rejected`,
  `false_match_at_1`, `rejection_rate`, `errors`, and the score that a false
  match reached. `summary.md` gained the section "Photos with no match in the
  catalogue". `--only no_match` runs these photos alone.
- The page `/runs` gained the filters `no match: every photo that matches no
  card` and `no match: the backend answered a card anyway`.
- Open point: the pipeline stages read `photo_dir` and now can meet the
  directory `__null__`. They are not changed. The pipeline builds the dataset
  `default` alone, and the NULL directory is empty there until a reviewer uses
  it.
- Read `docs/plans/03_null-image.md` for the decisions and the two stages.

### A run records when its embeddings were built, and the page shows it

- `scripts/match_run.py` gained `embeddings_of()`. At run creation it asks the
  backend `GET /v1/info` and stores the answer in `run.json` under
  `embeddings`. Two runs of one backend id were until now indistinguishable
  although a rebuild of the index moved every vector between them.
- The probe resolves the pipeline that owns the vectors. It reads the name from
  `/v1/pipelines/<name>/predict` or from `?pipeline=`, falls back to
  `default_pipeline` for `/v1/eval/predict`, and then walks the `embed` and
  `base` keys until it reaches the `embed` pipeline. An `ensemble` reports one
  block per member instead of one age.
- An unknown age is always a stated reason, never a blank: no HTTP backend, the
  server did not answer, no such pipeline, or the pipeline owns no index. A
  `kind: remote` backend such as `official-api` owns no index, so an unknown
  age there is the ordinary case and not a fault.
- `scripts/review_server.py` carries the block through `run_head()` and prints
  one line in the run detail header. A run made before this change prints "not
  recorded" rather than an empty line.
- The probe needs the matcher of 2026-09-21 or later. An older server reports
  no `embeddings` block, and the run then records "pipeline `<name>` reports no
  index".

### Added
- Arrow keys in the large view of the runs page. `Left` and `Right` move through
  the images of one photo row: the matched photo first, then the candidate
  strip. The first image and the last image hold; the move does not turn around
  at an end. `Up` and `Down` move to the previous row or to the next row and keep
  the place in the row, and the table scrolls to that row. A bottle photo that
  failed to load is not a step of the move, because the page puts a text card in
  its place. `Escape` closes the view, as before.
- `patch_dir` in `config.yaml`. It names a directory of corrected catalogue photos,
  one file per wine slug: `<wine_slug>.<extension>`. The first directory is
  `svoe-wino-hackaton/dataset/patched-official-2026-09-17`, which held 7 files on
  2026-09-22. Its `README.md` names each one and states where it comes from. The
  key is generic: every dataset reads the same directory. `common.PATCH_DIR`
  holds the path and `common.load_patches()` reads the files. The extension of a
  patch does NOT have to be the extension of the photo it replaces:
  `czitronnyj-magaracha.png` replaces a `.webp`. The match is made on the slug
  alone, which is the name before the extension. A file whose extension is not an
  image type, such as that `README.md`, is not a patch.
- A patch REPLACES the catalogue photo of that slug. Some cards of «Свое вино» carry
  the photo of a different wine, so the photo it corrects MUST NOT stay in view.
  `GET /img/bottle` serves the patch, and never the photo of the catalogue record.
  The catalogue file is never rewritten.
- The mark `patched` in the top right corner of every catalogue bottle that comes
  from `patch_dir`: the review table, the pickers of `add to wine`, `move` and
  `group`, and the candidate strips of a run. The pickers show a 34 px thumbnail,
  where the mark is a dot of the same colour and the tooltip states the meaning. The
  colour is `--var` in both the light and the dark palette.
- The field `patched` in a row, in a wine record, in a variant sibling, and in a
  suggest target. `GET /api/patched` answers the slugs that take a patch; the runs
  page holds a slug alone and no record, so it reads that list.
- The tool reads `patch_dir` again at every `GET /api/reload`, so a new patch file
  needs no restart. The start report states how many slugs take a patch, and warns
  about a patch file whose name is not a slug of the catalogue.
- `scripts/08_variants.py` embeds the patch and not the photo of the record. A
  variant group is found by comparing the catalogue bottle photos, so a photo that
  the tool no longer shows MUST NOT decide a group.
- `svoe-vino-matcher/config.yaml` reads the same directory under the same key and
  indexes the patch in place of the catalogue photo.

### Fixed
- A new or an edited patch stayed invisible in the browser for 24 hours.
  `_file` answered every image with `Cache-Control: public, max-age=86400`, and the
  URL `/img/bottle?slug=<slug>` does not change when a patch replaces the file.
  The browser therefore answered from its own cache and never asked the server.
  The route `/img/bottle` now answers with an `ETag` and `Cache-Control: no-cache`.
  The browser asks with `If-None-Match` and gets `304` while the file is the same.
  It gets the new file in the first answer after a patch. The other image routes
  keep `max-age=86400`, because their file never changes behind a stable URL.
  A browser that cached a bottle image before this change keeps the old copy until
  the 24 hours pass. One reload with an empty cache clears it.

### Changed
- The table of the review page is built from the catalogue. The filter `all wines`
  holds one row per catalogue card now, and not only the wines that hold a directory
  in the photo set. A wine with no candidate photo is a row with no candidate photo,
  and a drop of a photo on such a row makes its directory. The header counts every
  row: `2103 wines` for `official-real-photos`, `2106` for `default`, which holds 3
  directories whose slug the catalogue does not hold. Every other filter keeps its
  list: a card with no photo holds no photo and no label, so it stays out of the work
  lists. An address that names a wine with no photo now opens the filter `all` and
  not `no candidate photos`.

### Fixed
- `load_state` of `scripts/review_server.py` answered `{"labels": {}}` with no key
  `wines` when the label file was missing or broken. `prune_state` reads that key, so
  the tool stopped with `KeyError: 'wines'`. Every new dataset met this fault at the
  first start, because a new dataset holds no label file. Both answers hold the two
  keys now.

### Changed
- `.gitignore` covers `dataset/*/photo/` and `dataset/*/trash/`, and not the paths of
  one dataset alone. The pictures of every dataset stay out of git.
- The trash stands at `dataset/my/trash` now, and not at `work/trash`. The 360 files
  that the directory held were moved with it. A dataset owns its trash, so the trash
  stands beside the photos, the labels, and the other files of that dataset.
  `.gitignore` holds the new path: the directory holds pictures and does not belong
  in git.
- `config.yaml` holds two parts now. `rootdir`, `catalog_file`, and `backends_file`
  stand at the top and are the same for every dataset. The key `dataset` holds one
  entry per photo set, and each entry holds `name`, `photo_dir`, `trash_dir`,
  `label_file`, `variant_groups_file`, `manual_groups_file`, `excluded_slugs_file`,
  and `runs_dir`. One entry MUST carry the name `default`.
- `scripts/review_server.py` and `scripts/match_run.py` take `--dataset NAME`. Without
  the option they use the dataset named `default`. An unknown name stops the script
  and names every dataset of the file. Every other script uses `default`, so a second
  dataset is reviewed and benchmarked, and it is not built by the pipeline.
  `run.json` of a run records the dataset in `options.dataset`, and the configuration
  report at start holds the line `dataset`.
- `scripts/common.py` holds `DATASETS`, `dataset_names()`, and `select_dataset(name)`.
  The call binds the paths of one dataset. A file with the paths at the top level is
  the old flat shape; it is refused, and the error names the keys that belong in a
  dataset entry now. `common.OUT` follows `photo_dir` of the chosen dataset.

### Added
- The dataset `official-real-photos`. It holds the 100 photos of the official test set,
  copied from `~/Downloads/Реальные фото`, which stays as it is. The photos carry no
  ground truth. Each one lies in the directory of the wine that the pipeline
  `svm-siglip2-448` answered at rank 1 in the run
  `2026-09-21T114905Z-svm-siglip2-448-dir-realphoto`; the 100 photos fall on 65 wines
  and the scores run from 0.653 to 0.852. A place is not a label: every photo holds a
  comment that names the run, the rank and the score, it holds no label, and the field
  `prefilled_from` records the placement. A reviewer MUST judge each photo. The
  dataset holds its own `review-labels.json` and `excluded-slugs.json`; the variant
  groups and the manual groups are written when they are needed.
- The review page holds an inbox. An image file that lies directly in `my/`, and not
  in the directory of a wine, belongs to no wine yet. `scan_inbox` lists these files,
  `GET /api/rows` carries them in the new field `inbox`, and the page shows them in
  the sideboard with a dashed frame. The reviewer drags such a card to a wine row;
  the card then states the target and the header counts one more pending move. The
  button `clear`, and a drop back on the sideboard, take the target away. `apply`
  moves every file that holds a wine into `my/<slug>/`. The file keeps its name, and
  a name that is taken in the target gets the suffix `_moved2`. The photo carries no
  label, because no reviewer has judged it against this wine, and its comment states
  that it comes from the inbox. The target lives in the browser tab, as the rest of
  the sideboard does, so a reload before `apply` forgets it and the file stays in the
  inbox.
- `POST /api/apply-moves` reads the field `inbox` of the body: a list of
  `{"file": ..., "to": ...}`. It answers `inbox_moved`, `inbox_failed`, and the
  `inbox` that is left. A pair is refused when the target is not a slug of the
  catalogue, when a name holds a path separator, when the file is not in the inbox,
  or when the same file is named twice.
- `GET /img/inbox?file=<name>` serves one file of the inbox. It refuses a name with a
  path separator, a name that is a directory, and a file that is not present.
- `scripts/match_run.py` takes `--photos-dir DIR`. The runner then matches the image
  files of that directory instead of the photo set of the project. The walk is
  recursive. A hidden file and a file that is not an image stay out. Such a directory
  holds no ground truth, so every photo carries the label `unlabelled`, the slug is
  empty, the truth is empty, and the outcome is `answered` or `no_answer`. The run
  states no correctness: every share of `metrics.json` is `null`, and the new block
  `unlabelled` holds `n`, `answered`, `no_answer`, `errors`, `top_score_median`, and
  `score_margin_median`. The latency numbers are unchanged. `summary.md` holds a
  shorter form for a person. The option MUST NOT be used with `--from-run`, `--only`,
  or `--variants`; the runner refuses the combination. The name of the run directory
  carries the mark `dir`, and `run.json` holds the directory in `options.photos_dir`.
- `scripts/review_server.py` answers `GET /img/runphoto?id=<run>&file=<path>`. It
  serves one photo of a run of `--photos-dir` from the directory that `run.json`
  names. `/img/photo` never leaves `my/`, so it cannot serve such a photo. The route
  refuses a run id with a path separator, a run that names no directory, and a path
  that leaves the directory.
- The page `/runs` shows a run with no ground truth. A note above the cards states the
  kind of the run and the counts that need no truth. A row of such a run shows the
  photo, the tag `unlabelled`, and the path of the file. No candidate carries a green
  or a red border, because no slug is expected and no slug is forbidden, and no answer
  is marked as wrong.

## 2026-09-19

### Added
- The review page has an `export CSV` button. It exports the exact current table view
  from the browser. The export keeps the active filter, slug scope, search text, sort
  order, variant-group scope, and row order. One record describes one candidate photo.
  A wine with no candidate photo gets one record with empty photo fields. The file uses
  UTF-8 with a byte-order mark. CSV quoting keeps commas, quotes, and line breaks in one
  cell. A text value that starts with a spreadsheet formula marker gets an apostrophe
  guard.
- A check of `validate`: `two wines carry the same catalogue bottle photo`
  (`catalog_photo_twin`). It compares the CATALOGUE bottle photo of every wine with the
  catalogue bottle photo of every other wine. It reads no candidate photo of `my/`, so a
  label and a candidate photo do not change its result. Two wines that carry one picture
  are a defect of the catalogue: the matcher cannot separate them by the image, and one
  of the two cards names the wrong bottle.
- The check reads the whole catalogue, including a card that has no directory in `my/`.
  On the catalogue of 2026-09-17 that is 2,093 cards with a bottle photo on disk, which
  is 2,189,278 pairs.
- The check runs in two stages, because the full compare of 2,093 pictures at full
  resolution is not possible in the time of a check. Stage one reads the grey 32 by 32
  signature of `photo_signature` for every picture and compares every pair with numpy;
  it takes about 3 seconds and it names the pairs under 3.0 of 255. Stage two reads a
  COLOUR 128 by 128 signature of the named pictures alone and measures again; it takes
  about 8 seconds. The whole run takes about 43 seconds, of which about 30 seconds is
  the first decode of the 2,093 files.
- Stage two is needed because the grey 32 by 32 signature is too coarse for this
  question. It holds no colour and no text of the label, so two DIFFERENT wines of one
  producer line measure as little as 0.09 of 255 under it, which is the same band as a
  true duplicate. The colour 128 by 128 signature separates the two: a true duplicate
  measures 0.00 and the nearest different picture measures 0.18. The measurement is in
  `ResearchLog.md`.
- A finding reports the whole cluster, not the pair. Three wines that carry one picture
  give one finding of three slugs and not three findings. The finding carries `slugs`,
  `bottle`, `same_picture`, `same_bytes`, `distance`, and `tag`.
- The finding carries one of two tags. `same pic` means the distance is under 0.05 and
  the two cards carry one picture; this is a defect. `twin` means the distance is from
  0.05 to 1.0 and the two pictures are different photographs of a bottle that looks
  nearly the same, as two wines of one producer line do; this is not a defect by itself,
  and the pair is a candidate for a variant group.
- A badge under the bottle photo of the row states the tag and the size of the cluster,
  for example `same pic ×2` or `twin ×8`. The tooltip states the measured distance and
  names the other wines of the cluster. `same pic` takes the colour of a defect and
  `twin` takes the colour of a variant. The check reports the CATALOGUE photo, so its
  finding carries `slugs` and no `photos` and it cannot use the pill of a card.
- On the catalogue of 2026-09-17 the check reports 70 findings over 162 wines: 27
  clusters with the tag `same pic` over 55 wines, and 43 clusters with the tag `twin`.
  The largest cluster holds 8 wines of one sparkling line of Fanagoria.

### Changed
- The filter `failed a check` now also shows a catalogue card that has no directory in
  `my/`. `catalog_photo_twin` reads the whole catalogue and can report such a card, and
  without this change the other half of a cluster stayed invisible. The four older
  checks read `my/` alone and never report such a card, so the change does not affect
  them.

## 2026-09-18

### Added
- A check of `validate`: `the candidate photo is the catalogue bottle photo of the wine`
  (`candidate_is_catalog_photo`). The `my/` set holds real-world photos only, and the
  catalogue bottle photo of a wine is a studio render. A candidate photo that is that
  render makes the benchmark easier than reality: the matcher reads its own catalogue
  picture back. The check compares every candidate photo with the bottle photo of the
  SAME wine. It never compares across wines. Two pictures count as duplicates when the
  bytes are equal, and also when the content is equal and the size differs. The second
  case reduces each picture to a signature: composite on white, convert to grey, crop to
  the bounding box of the bottle, resize to 32 by 32. The measure is the mean absolute
  difference of the 1,024 values, and the threshold is 10.0 of 255. The crop is what
  finds a copy that carries another white margin; without it the same picture measures as
  much as 119. A photo marked `unusable` and a photo marked for deletion stay out, and a
  wine with no catalogue bottle photo is not checked. On the set of today 304 of the
  4,112 pairs are under the threshold, and 0 of them have equal bytes; the check itself
  reports 282 photos in 241 wines, because it leaves the photos out that are already
  marked `unusable` or marked for deletion. The check composites a
  transparent picture on white, so a render that was flattened on another colour is not
  found. The measurement and the choice of the threshold are in `ResearchLog.md`.
- A finding of `candidate_is_catalog_photo` carries `same_bytes`, `difference`, and the
  pill text `catalogue render`.
- A check function now takes the catalogue as its fourth argument:
  `check_<name>(rows, labels, groups, catalog)`. The three older checks take it and do
  not use it.
- `candidate_is_catalog_photo` reads the pixels of about 6,000 files and takes about 50
  seconds, against about 3 seconds for the older checks. It decodes in 8 threads, and a
  JPEG decodes at a reduced scale through `Image.draft`. The dialog of `validate` states
  the cost in the help text of the check.
- Two checks of `validate` read the size of a photo: `the photo is too small (long
  side under 256 px)` and `the photo is smaller than the input of the matcher (long side
  256 to 447 px)`. The matcher runs SigLIP2 with an input of 448 by 448 pixels, and the
  preprocessor stretches the whole picture into that square. A photo with a long side
  under 448 is stretched up and holds no more detail than it had. A photo with a long
  side under 256 holds less than the half of the input, and the text of the label is
  then too small for the text step and for the OCR step. The band under 256 belongs to
  the first check alone, so the two never report the same photo. A photo marked
  `unusable` or marked for deletion stays out. The downloader already refuses a picture
  with a side under 200 (`MIN_SIDE` in `scripts/02_download.py`); a smaller picture in
  the set came in before that rule or by hand.
- A finding MAY now name the text of its pill in the field `tag`. The size checks state
  the size of the photo, for example `225x300`. A finding without `tag` keeps the older
  text, which states the count of the wines.
- The left column of a row of a run states the size of the photo, after the latency, for
  example `01_conf090.jpg · rank 2 · 237 ms · 225 × 300`. The number comes from the
  picture that the browser already loaded, so the page makes no further request.
- The filter `positive: the true slug is at rank 2 to 5` (`rank_2_5`) on the page `/runs`.
  It holds the band that R@5 wins and R@1 loses. A photo whose true slug never came back
  is out, as in `near`. The counts of `hit`, `rank_2_5`, and `after_5` add up to the count
  of the positive photos of the run.
- Two filters on the page `/runs`: `positive: the true slug is not in the top 5`
  (`after_5`) and `positive: the true slug is not in the top 10` (`after_10`). A photo
  whose true slug never came back is in both, because it counts as a failure at every
  depth. That is the rule of `failed_before()`, which `--from-run` and `--rerun-depth`
  already use. The filter `near` keeps its older reading and leaves such a photo out.
- The page `/runs` reads the true wine of a negative photo. A negative photo states one
  wine that the photo does NOT show, so `outcome` alone cannot say whether the answer was
  good. One photo file often stands in the set two times: `positive` for the wine that it
  shows, and `negative` for a wine that it does not show. The two rows hold the same
  `image_sha256`. The server reads that pair and gives the negative row the slug of its
  positive twin.
- The true wine now carries a **dashed green** frame in the strip of the candidates, next
  to the red frame of the forbidden wine. The left column states the true wine, its rank,
  and the rank of the forbidden wine. When the true wine never came back, a dashed green
  card stands after the last candidate, set apart by a gap.
- The new filter `negative: the wrong wine stands above the true wine`
  (`negative_above_positive`) selects the rows where the forbidden wine stands above the
  true wine. That is an error that no earlier number showed: the run counted the row as
  `other_slug_at_1`, which is not an error by itself. On the run
  `2026-09-17T220525Z-svm-text-siglip2-448-bench` the filter finds 20 rows of 384 negative
  photos; 97 more rows stand the right way round.
- The new filter `set defect: one photo is positive for two wines` (`twin_conflict`)
  selects the rows of a photo that carries `positive` for two wines, or `positive` and
  `negative` for one wine. One photo can show one wine only, so this is a defect of the
  set and not a result of the run. The filter exists so the reviewer can repair the set by
  hand. Until then the page marks every true wine of the group. The same run holds 121
  such rows, most of them a pair of catalogue cards that differ only in the bottle volume.
- The index reads one run only, so the report of a run stays a report of that run. A photo
  whose twin was not in the run gets no twin. The label `variant` is left out: it groups
  the same wine in another bottle and states no truth about the photo. A slug that comes
  back two times counts at its first rank, which is the rule of `judge()`.
- The field `twin` is added when the server reads a run. It is not written to
  `results.jsonl`, so a run made before today gets the marks as well.
- The button `validate` in the header checks the photo set for defects. It opens a
  dialog with one line per check, the reviewer chooses the checks, and the table then
  shows only the wines that fail at least one check. That view holds until the filter
  is changed. A check only reads: it writes no file and no label.
- The first check is `shared_positive`. It reads every candidate photo, compares the
  bytes, and reports a picture that carries the label `positive` under two or more
  slugs. One picture cannot show two wines, so such a pair is a defect: either one
  label is wrong, or the two catalogue cards are one wine. A pair of wines that are in
  one variant group is reported too and carries `same_group`, because the group itself
  may be wrong. A re-encoded copy of the same picture has other bytes and is not found.
  On the set of today the check reports 52 pictures across 56 wines, 14 of them
  inside one variant group.
- Every reported photo carries a red outline and a pill at the top left. The pill
  states how many wines share the picture, and its tooltip names the other wine and
  the other file. The count line states the findings, the photos read, and the seconds.
- The checks live in one registry, `CHECKS` in `scripts/review_server.py`. To add a
  check, write `check_<name>(rows, labels, groups)` and name it in the registry. A
  finding MUST hold `check` and `why`, and it SHOULD hold `photos` or `slugs`. The
  route builds the failing wines from those two fields and the dialog reads
  `GET /api/checks`, so a new check needs no change of the page.
- `GET /api/checks` answers the checks that the server offers.
  `POST /api/validate` takes `{checks: [id]}` and answers
  `{ok, ran, wines, photos, seconds, findings, slugs}`. An absent `checks` runs every
  check. An empty list, a value that is not a list of strings, and an unknown id are
  each refused with `400`.
- One run reads the 2,543 candidate photos in about 2.5 seconds, so the result is
  not cached. The lock is held only long enough to take the rows and the labels, so a
  label of the reviewer is not blocked while a check runs.
- A photo can now be copied to a second wine slug. One picture sometimes shows two
  wines: the same label stands on two bottles of a variant group, and the photo is a
  true photo of both. A move is wrong there, because a move takes the photo away from
  the first wine. The card holds a `⧉ copy` button under the `→ move` button, and
  the key `c` in the large view opens the same dialog in copy mode.
- The copy is recorded, not performed, exactly as a move is. The target is written to
  `review-labels.json` as the field `copy_to`, the card gets a dotted outline, and the
  header states `N copies pending`. The button `apply` and
  `python3 scripts/09_apply_moves.py --apply` carry the copies out.
- The copies run before the moves, because a move takes the source file away. A photo
  can hold a copy and a move at the same time. A `delete` mark drops both.
- The source photo does not change. It keeps its slug, its label, and its comment.
  The copy is a new candidate photo of the target wine. It carries no label, because a
  label judges one photo against one wine. Its comment is one line,
  `копия фотографии из <source slug>`, and its entry holds `copied_from`.
  `copy_to` is dropped when the file is written, so a second run copies nothing.
- `POST /api/copy` takes `{slug, file, to}` and answers `{ok, counts}`. It refuses an
  unknown photo, an unknown target, and the slug of the photo itself, each with `400`.
  An empty `to` clears the record.
- `POST /api/apply-moves` answers `copied` and `copy_failed` beside `moved` and
  `failed`. The counter `copied` was added to the counts of the review set. The photo
  record of `GET /api/v1/wine/<slug>` holds `copy_to` and `copied_from`.
- `free_name` takes the tag of the action, so a name that is taken in the target
  directory gets `_copy2` for a copy and keeps `_moved2` for a move.
- `docs/API.md`, `docs/openapi.yaml`, `README.md`, and `SMOKE_TESTS.md` state the two
  new features, the four new routes, the new fields, and 33 new test cases
  (139 to 171).

- `docs/openapi.yaml` states the whole HTTP contract of `scripts/review_server.py` in
  OpenAPI 3.1. It covers all 32 routes, not only the 7 routes under `/api/v1/`: the
  routes of the review page, the routes of the runs page, the two picture routes, and
  the three document routes. It holds 33 schemas. The document is written by hand.
  It is not generated from the code, so a change of a route MUST change the document
  in the same commit.
- The server serves the document. `GET /openapi.yaml` answers the file as it is
  written. `GET /openapi.json` answers the same document converted to JSON.
  `GET /docs` shows
  the document in a browser with Swagger UI, pinned to version 5.33.0 from the CDN.
  The page follows the theme of the operating system. Swagger UI ships no dark theme,
  so the dark form turns the light theme around with a CSS filter.
- `docs/API.md` now states the contract of the routes of the page. Those 11 write
  routes and 6 read routes had no written contract before: the file named 6 of them in
  a table of one line each. The new text states the body, the answer, and the errors of
  each one, the shared rules of a stored picture, and the table of the status codes.

### Fixed
- `README.md` stated that the page has fourteen filters. It has twenty-two. The number
  was already wrong before the filter `failed a check` was added.
- `docs/API.md` stated that the error status `502` means that the embedding service
  failed and that `503` means that the index is absent. The server holds no embedding
  service and no index, and it never answers `502`. The file now states the five
  status codes that the server does answer: `400`, `404`, `409`, and `500`.
- `docs/API.md` named 6 values of the parameter `filter` of `GET /api/v1/wines`. The
  route accepts 12. The 6 that were missing are `no_candidate_photos`,
  `image_unresolved`, `image_assumed`, `image_confirmed`, `image_manual`, and
  `image_shared`.
- `docs/API.md` stated that `GET /api/v1/wine/<slug>` adds `description` to the record.
  The record of `GET /api/v1/wines` already holds `description`. The detail route adds
  `photos` alone.
- `docs/API.md` did not state that the field `photos` of the answer of
  `POST /api/v1/propose` holds the short form `{file, conf}` and no label state.

### Changed
- The two size checks of `validate` read the LONG side of a photo, not the short side.
  A photo of a bottle is tall and narrow, so its short side is small even when the photo
  is correct. A run of `validate` on the set of today reads 3,832 photos: the short side
  reported 65 photos and 732 photos, the long side reports 0 photos and 44 photos. Over
  all 3,973 files on disk the two rules give 70 and 749 against 2 and 47; 52 of the 70
  were tall product shots such as 142 by 600 pixels, which are correct photos. The
  finding now carries `long_side` in place of `short_side`, and its text names the long
  side.
- The comment of the size checks stated that the preprocessor of SigLIP2 fits the whole
  picture into the square of 448 by 448 pixels. That statement was wrong. The
  preprocessor stretches the picture: `SiglipImageProcessor` calls
  `resize(image, size=(448, 448))`, and `preprocessor_config.json` of
  `google/siglip2-so400m-patch14-384` holds `size` alone and no `crop_size`. Verified in
  the installed `transformers` on gx10 on 2026-09-18.
- The `copy` button of the name in `scripts/review_server.py` now copies the brand and
  the name in one string, for example `WINEMAFIA David, 2020` instead of `David, 2020`.
  A search needs both parts.
- Every `copy` button in `scripts/review_server.py` has `user-select: none`. The word
  `copy` no longer enters a text selection, so a selection that is pasted into a search
  field holds the name or the slug alone.
- `scripts/02_download.py` writes its results to the database in slices of 400 instead
  of once at the end. A stop, a timeout, or `Ctrl-C` now keeps the work that is done.
  A wine is marked `downloaded=1` only when every task of that wine is written, so a
  wine is never half recorded as complete.
- `scripts/02_download.py` takes `--skip N`, which drops the first N pending wines. It
  allows a second run to start where a first run is still working.
- `backends.yaml` holds four more backends of the svoe-vino-matcher service on port
  8158: the pipelines `barcode-siglip2-448`, `text-siglip2-448`, `rerank-siglip2-448`,
  and `ocr-siglip2-448`. Each asks for 10 results with a 60 second timeout.

### Known defects, now written down
- `GET /api/v1/wines` does not check that `limit` and `offset` are numbers.
  `?limit=abc` raises inside the handler and the server closes the connection with no
  answer. `GET /api/run` does check and answers `400`. The defect is recorded in
  `docs/API.md`. The code is not changed.
- `GET /api/v1/wine/<slug>` answers `404` for a catalogue card that holds no directory
  in `my/`, although `GET /api/v1/wines` lists that card under a catalogue filter.

### Verified
- The document validates against the OpenAPI 3.1 schema.
- Every documented read route was checked against the running server with a JSON
  Schema validator: `/api/rows` with all 2106 rows, `/api/state`, `/api/v1/stats`,
  `/api/runs`, `/api/run`, `/api/suggest`, `/api/v1/wines` under three filters, and
  `/api/v1/wine/<slug>` for all 85 wines that hold a proposal. No mismatch is left.
- The check found one mismatch, which is corrected: `image_match.file` is null for a
  wine whose catalogue photo is unresolved. The document stated a string.
- The photo copy and the checks were driven end to end against a server that runs on
  a temporary photo set, not against the working set: 43 cases on the routes and 42
  cases in a headless browser, all passing. They cover the refusals of `POST /api/copy`
  and `POST /api/validate`, the order copy-move-delete, the `_copy2` rename, a second
  `apply` that copies nothing, a `delete` that drops a copy, the dialog in both modes,
  the key `c`, the mark on a reported card, and the view that holds until the filter
  changes. The new routes were NOT put through the JSON Schema validator; that tool is
  not installed on this machine.
- `check_shared_positive` was run once against the working set. It reads the 2,543
  candidate photos in 2.5 seconds and reports 52 pictures across 56 wines, 14 of them
  inside one variant group.
- 13 refusal paths were checked: the 7 refusals of `POST /api/v1/propose`, and the
  refusals of `/api/label`, `/api/comment`, `/api/exclude`, `/api/group`,
  `/api/labels`, and an unknown route. Each answers the documented status and the
  documented shape.
- The write paths that store a picture were NOT called, because a test instance shares
  the directory `my/` with the running tool. Their contract comes from the code.

## 2026-09-17

### Added
- The progress line of `scripts/match_run.py` now states the time of the last chunk of 25
  photos, the elapsed time of the run, and the ETA. The ETA uses the rate of the whole run.
  The line reads `  25/1387  chunk 12.3s  elapsed 0:00:12  ETA 0:11:05`.
- The table can now show a catalogue card that has no directory in `my/`. Such a card has no
  candidate photo, so it is a gap of the photo set. 1,262 of the 2,103 catalogue cards are such
  a gap. These rows stay out of the default list, and a filter that asks about the catalogue
  brings them in: `no candidate photos`, and the five `catalogue photo:` filters. The same
  rule holds in the agent API, where the filter `no_candidate_photos` is new.
  A catalogue-only row carries the mark `catalogue only`, a muted background, and the text
  `no directory my/<slug>`. It holds no label state, and the counters of the review set do not
  count it. The add, move, and open paths keep to the rows that have a directory.
- The bottle column states how the catalogue established that photo. The badge under the
  photo reads `from site`, `by name`, `by hand`, or `no photo`, and its colour follows the
  confidence of the match. The tooltip states the method, the confidence, the number of
  candidates for the CSV photo name, the source page, the time of the check, and the note.
  An old catalogue without the field `image_match` gets the badge `method unknown`.
- A card whose photo is shared with another card carries the mark `shared ×N`. The tooltip
  names the other slugs and states that those cards cannot be separated by the image.
- A wine whose catalogue photo is unresolved shows `no photo / unresolved` in place of the
  picture. The tool does not show a placeholder that looks like a photo.
- Five filters of the bottle photo: `unresolved`, `by name only (assumed)`, `confirmed by the
  site`, `set by hand`, and `shared with another card`. The same five values work in the agent
  API as `image_unresolved`, `image_assumed`, `image_confirmed`, `image_manual`, and
  `image_shared`.
  The field comes from the catalogue build of `svoe-wino-hackaton`. Read
  `svoe-wino-hackaton/docs/plans/01_photo-join-repair.md`.

### Fixed
- The sideboard covered the right end of the header. The panel stands over the page at
  the right edge, and the header is sticky over the whole width, so the header now keeps
  the same room free. No control of the header is covered now.

### Added
- The tag `variant group of N` on a row is a button. A click lists that group alone,
  and a click on the tag of the group that is shown lists every wine again. While a
  group is shown, the chip `variant group <id> of N ×` stands in the header beside the
  other controls and takes the group away. The chip sits there, and not in the count
  line, because the header is where a reviewer looks for the filter that is on. The
  count line names the group as well. The click clears
  the search, `Show` and `Slugs`, so every member of the group reaches the screen; the
  sort is kept, because the rows of one group stand together in every sort order. The
  group travels in the address as `?group=g0NN`, so the view can be reloaded and sent.
  An unknown group id is dropped, as an unknown value of a select is.

### Changed
- The line under the bottle photo that states how the catalogue established that photo
  (`by name`, `from site`, `by hand`, `no photo`) carries no border and no background
  any more. It is a statement, not a control, and a box of the same width as `Exclude`
  and `Group` right below it made it read as a third button. The colour of the text
  alone now carries the confidence, and `assumed` moved from grey to amber, because
  grey is the colour of the two buttons below.

### Added
- The `Group` button under the bottle photo joins one wine to the variant group of
  another wine. The tool writes one pair to the new file `manual-groups.json`, which
  `config.yaml` names under `manual_groups_file`. `scripts/08_variants.py` never
  writes that file, so a new run of the script keeps every pair made by hand.
  `load_variants()` now builds a group as a connected component over the generated
  groups and these pairs. A component that holds a generated group keeps that id; a
  component of manual pairs alone gets an id `m<NNN>`. With no manual pairs the
  loader gives the same 28 groups over the same 63 wines as before.
- `POST /api/group` takes `{slug, target}`. Two wines that are in no group make a new
  group. A wine that is in no group joins the group of the other wine, in either
  direction. Two wines that are each already in a group are refused with HTTP 409 and
  both group ids, because one pair cannot undo a merge of two groups. Two wines of one
  group answer HTTP 200 with `changed: false`. The answer carries the rebuilt rows and
  groups, so the table redraws at once.
- The search and the three selects of the table stand in the address:
  `?q=`, `?filter=`, `?sort=` and `?slugs=`. A control at its default value is left
  out, so a plain view keeps a plain address. The address is read once at start. An
  unknown value of a select is dropped. The fragment keeps its own job, the open
  photo, so `/?q=shardone#<slug>/<file>` states both.

- The right-click menu of a photo holds `Copy Image`, `Copy Image URL` and `Download`
  above the delete entry. `Download` saves the picture through a `download` link. The
  address is same-origin, so no tab opens. The saved name is `<slug>__<file>`, because
  most wines hold a file named `01_conf095.jpg` and the plain name would collide in the
  download folder. The menu closes at the click, because the browser states the
  download itself. `Copy Image` puts the picture itself on the clipboard. A JPEG or a WEBP
  goes through a canvas first, because the clipboard accepts `image/png` in every browser.
  `ClipboardItem` receives the promise of the picture, not the picture, so Safari keeps
  the permission of the click while the fetch runs. `Copy Image URL` puts the full address
  on the clipboard. The entry states `copied` or `failed` for 700 ms, then the menu closes.
  Both entries work in the table and in the large view, because both already report the
  photo under the pointer.
- A `copy` button stands next to the name of a wine. It puts the name on the clipboard.
  A wine without a name carries no button.
- `copySlug` is now `copyFromButton`. The function always copied the `data-copy` value of
  the button, and the name states that now.

- The sideboard hides and shows: the button `sideboard` in the header, the key `s`, and
  the `×` in the head of the panel. The button states the number of the held photos while
  the panel is hidden. The choice is kept in the browser and holds over a reload. A drag
  of a photo card shows the panel again, because the photo needs a target on the screen.
  While the panel is hidden, the page uses the whole width.

### Added
- `scripts/match_run.py --from-run <run>`: the repeat of a run. It asks the backend only
  about the photos that failed in an earlier run. `--rerun-depth K` states how many
  candidates count as an answer: 1 repeats every photo that was not correct at rank 1,
  and 10 repeats every photo whose true slug was not in the first 10. A negative photo
  is repeated when its own slug DID come back inside K. A failed request is always
  repeated.
- A repeated photo keeps the `query_id` of the earlier run, and its row in
  `results.jsonl` carries `previous` with the earlier rank, outcome, and answer. The two
  files join on `query_id`.
- `metrics.json` of a repeat run carries a `subset` block with `recovered_at_1`,
  `recovered_at_depth`, and `still_failing`, and states that its shares cover the
  repeated photos only. `run.json` states the rule in `based_on`, and `summary.md`
  states it in the first paragraph.
- The page `/runs` marks a repeat run with the tag `repeat d<K>`, puts the warning above
  the cards, and states under each photo what the earlier run answered.

### Added
- The metrics that `svoe-wino-hackaton/docs/task-10-specification.pdf` asks for:
  `match_share` with its target of 90 to 100 percent (section 7.1), `f1_at_1` and
  `f1_at_5` with their precision and recall (section 2.3), `within_sla_share` against
  the 3000 ms of section 2, `near_duplicate_confusion` for the wrong answers inside the
  variant group of the true wine, which the specification names as the main source of
  the errors, and `score_margin`, the gap between the first and the second candidate,
  for the correct answers and for the wrong answers apart.
- The page `/runs` shows these five measures in the first row of the cards, with the
  match share and the SLA in green when they reach the target and in red when they do
  not.
- The page `/runs` sorts. A click on a column of the table of the runs sorts by it; a
  second click turns the order around. The control `Sort` orders the photo rows by the
  most wrong first, by the rank of the true slug, by the score, by the latency, or by
  the path. The order of the photos is made by the server before the paging, so it
  holds over the whole run.
- `GET /api/run` takes `sort`. An unknown value is refused.
- The table of the runs holds the new columns: the match share, F1@1, F1@5, and the
  share inside the SLA.

### Added
- `scripts/match_run.py`: the match runner. It sends every annotated photo to one
  backend and writes one directory per run under `runs_dir`. The directory holds
  `run.json`, `queries.tsv`, `queries.jsonl`, `predictions.jsonl`, `results.jsonl`,
  `metrics.json`, and `summary.md`.
- `predictions.jsonl` carries the exact fields of the organizers. `queries.tsv` carries
  their manifest columns, so `participant_test.sh` runs against the same set. Both were
  checked against the harness of the organizers: 299 rows, no difference.
- `scripts/match_backends.py`: the backends. One HTTP class sends the photo as
  `multipart/form-data` and reads every answer shape seen so far. A header value
  `env:NAME` comes from the environment, so no token stands in a file.
- `backends.yaml`: the definitions of the backends. The first two are the contract of
  the jury and the official vino-svoe recognizer.
- `config.yaml` keys `backends_file` and `runs_dir`.
- `scripts/review_server.py`: the page `/runs`. It holds the table of the runs, the
  metrics of the selected run with two rank histograms, and one row per photo with the
  candidates that came back. The expected wine carries a green border; the wine that a
  negative photo MUST NOT match carries a red border. New routes: `GET /runs`,
  `GET /api/runs`, and `GET /api/run`.
- `docs/match-runner.md`: the format of `runs/`, of `backends.yaml`, and of every metric.
- `docs/plans/01_match-runner.md`: the plan of this work.

### Changed
- `scripts/review_server.py`: the colour variables of the page stand in one constant,
  `THEME_CSS`. The page of the review and the page of the runs use it.
- `scripts/review_server.py`: both pages hold the same navigation at the top right of
  the header. `Review` opens `/`, and `Runs` opens `/runs`. The link of the current
  page carries the class `on`. On the page of the runs this navigation replaces the
  link `back to the photo review` that stood in the title.

### Added
- `scripts/review_server.py`: the text search of the review page reads a query that
  is not written exactly as the text. It folds the accents, so `cotes` finds
  `Côtes du Don`. It takes the query apart into words and asks for each word on its
  own, so `don cotes` and `cotes du don tsimlyanskiy` find the same wine. A word of
  four letters or more also meets a word that stands one letter away from it, so
  `chardonay` finds `Chardonnay`. A word in Cyrillic is looked for in its Latin form
  as well, and a canonical form puts the spellings of the slugs together, so
  `cimlyanskiy`, `tsimlyanskiy`, and `czimlyanskoe` find each other.
  The words of a row are built once and kept on the row. A query of three words over
  2106 rows needs about 7 ms.

### Changed
- `scripts/review_server.py`: a photo added by drag and drop no longer draws the
  table again. The page brought the whole table up to date with `render`, so a wine
  that no longer matched the filter left the table at once. Under the filter `no
  candidate photos (catalogue gap)` the row went away as soon as its first photo
  landed. The new function `refreshRow` draws the cards, the photo count, and the
  mark of that one row where it stands. A reload of the page filters again.
- `scripts/review_server.py`: the new function `cardsHtml` builds the card strip of
  one row. `render` uses it for every row, and `refreshRow` uses it for one row.

### Fixed
- `scripts/review_server.py`: a drop of a picture on the row of a wine with no
  candidate photo was refused with `unknown wine slug`. `_known_slug` asked for a
  directory in `my/`, and a catalogue card with no candidate photo holds none. The
  test now accepts a slug of the catalogue too, and `_store_image` makes the
  directory. The wine then leaves the catalogue-only rows and enters the review set:
  `_store_image` builds its row with the new function `build_row` and puts it in
  `_rows`, and the page drops the mark `catalog_only`.
  The same refusal hit `POST /api/fetch-image`, `POST /api/wine-comment` and
  `POST /api/exclude`, which use the same test. All four take a catalogue slug now.
- `scripts/review_server.py`: the new function `build_row` builds the row of one
  directory. `build_rows` uses it for every directory, so one shape serves both.
- `scripts/review_server.py`: a click on the catalogue bottle of a wine with no
  candidate photo did nothing. `showLightbox` left the function when the wine held
  no photo, so the filter `no candidate photos (catalogue gap)` had no large view at
  all. The large view now opens with the catalogue bottle alone. The candidate
  figure stays hidden and the badge states `no candidate photo for this wine`. The
  keys `1` to `4` and `m` do nothing, and the comment field is closed, because both
  belong to a photo. A wine with neither a photo nor a bottle does not open, and
  `Down` and `Up` step over it.
- `scripts/review_server.py`: the address `#<slug>` opens a wine that holds no
  candidate photo. `openFromHash` needed a `/` in the address, and it looked for the
  wine in the review rows alone. A catalogue-only wine is not a review row and the
  filter `all` leaves it out, so the function now reads every row and chooses the
  filter `nophotos` for such a wine.

### Added
- `backends.yaml` key `workers`: how many requests a backend takes at the same time.
  `official-api` holds `workers: 4` and `organizers` holds `workers: 1`. The command
  `python3 scripts/match_run.py --backend official-api` now sends 4 requests at once
  without an option. `--workers N` still wins over the key. `--workers` has no fixed
  default any more: the key of the backend decides, and 1 is the last default.
  The runner states the count and its source, for example
  `requests at the same time: 4`, and the source of the value after it.
  `run.json` records the value that ran, under `options.workers`.
  The value 4 comes from a measurement. Read `ResearchLog.md`.
- `scripts/review_server.py`: the sideboard, a panel at the right of the review page.
  A photo card is dragged to the panel and waits there. A drag from the panel to a
  wine row records the move with `POST /api/reassign`, the route that the button
  `move` already uses. A drop on the row of the source wine, and the button
  `put back`, return the photo to its wine. The move machinery does not change:
  `apply` moves the file and drops the label, as it does for every move.
  The sideboard holds its list in the browser tab alone. A reload empties it and the
  server never learns about it. `apply` states nothing about a photo that waits in
  the sideboard with no target.
- `docs/plans/02_sideboard.md`: the plan of this work and the decisions of the owner.

### Added
- `scripts/match_run.py` states two rules of the query set on the console. The line
  `variant photos:` states the effect of `--variants`: how many variant photos stay
  out with `off`, or how many enter the set and which slug counts as a true match
  with `strict` and with `group`. The line `excluded slugs:` states how many slugs
  `excluded-slugs.json` holds and how many photos stay out because of them. The
  runner prints the second line also when the count is 0.

### Fixed
- `scripts/review_server.py`: the review page showed an empty list. The constant `PAGE`
  was one raw string. The change that made `THEME_CSS` cut `PAGE` into two parts. The
  second part lost the prefix `r`, so Python read it as a normal string. Every `\n` in a
  JavaScript string literal became a true newline. A JavaScript string literal MUST NOT
  hold a true newline, so the browser refused the whole script and drew no row. The
  second part carries the prefix `r` again. This also repairs the CSS escape `\2014` and
  the escaped quotation marks of the exclude prompt, and it removes the `SyntaxWarning`
  for `\s` at import. `PAGE_RUNS` is a normal string by design and does not change.

### Added
- `excluded-slugs.json` names the wine slugs that are out of the benchmark. Each entry
  holds the slug, a `reason`, and a timestamp. Some cards of the catalogue hold an
  error, most often a wrong bottle photo. The bottle photo is the reference of the
  benchmark, so a wrong reference shifts the metrics. The photos of an excluded slug
  MUST NOT be used for benchmarking.
- `config.yaml` key `excluded_slugs_file` names the file.
- `docs/excluded-slugs.md` states the purpose, the format, the rules, and the duty of a
  consumer of the file.
- `scripts/review_server.py`: an `Exclude` button under the bottle photo of every row.
  The button asks for the reason and writes the file at once. An excluded row is red.
  The button of an excluded row reads `Excluded` and puts the slug back after a
  confirmation.
- `scripts/review_server.py`: the control `Slugs` in the header bar. The values are
  `all`, `included`, and `excluded`.
- `scripts/review_server.py`: the route `POST /api/exclude` with the body
  `{slug, excluded, reason}`. An exclusion without a reason is refused.
- The agent API states the exclusion: `GET /api/v1/wines` leaves an excluded wine out
  unless `include_excluded=1`, `GET /api/v1/wine/<slug>` holds `excluded` and
  `exclude_reason`, and `GET /api/v1/stats` holds `excluded_wines` and
  `excluded_photos`.
- `config.yaml` now holds the configuration of the project. It defines `rootdir`, the root
  directory of the workspace, and `catalog_file`, the path to `catalog.jsonl`. A relative
  value of the configuration is resolved against `rootdir`.
- `scripts/common.py` reads `config.yaml` at import. It exports `CONFIG`, `ROOTDIR`,
  `CATALOG_FILE`, `PHOTO_DIR`, `TRASH_DIR`, `LABEL_FILE`, `VARIANT_GROUPS_FILE`,
  `EXCLUDED_SLUGS_FILE`, and the helpers `rootpath(path)`, `config_path(key, default)`,
  and `print_config()`. An absent key gives the earlier default path.
- `scripts/review_server.py` prints the configuration and the work directory at start.
  A path that does not exist gets the mark `(absent)`.

- `../SVOE-VINO-ISSUES.md` in the workspace root. It is the consolidated register of every
  known defect of the «Своё Вино» catalogue and of this test set. It joins five earlier
  sources: `docs/catalogue-defects.md`, `ResearchLog.md`, `work/hunt/results/*.json`,
  `svoe-wino-hackaton/docs/research/`, and the `catalog-quality.md` / `catalog-twins.md` /
  `letters/02-platform-catalog-defects.md` documents of the hackathon repository.

### Removed
- The configuration key `embedding_cache_file` and the file
  `derived/bottle-embeddings.json`. The matching of a picture against the photo set is
  the work of an external application now.
- `scripts/review_server.py`: the route `POST /api/v1/search-by-image`, the helpers
  `load_embeddings`, `embed_one`, and `top_k_by_vector`, the constant `GX10`, and the
  field `embedding_index` of `GET /api/v1/stats`. The route needed the embedding cache
  and cannot answer without it.
- `scripts/08_variants.py`: the embedding cache and the option `--no-cache`. The image
  step embeds the bottle photos at every run now. `--no-image` skips the step.
- `scripts/common.py`: the constant `EMB_CACHE_FILE`.

### Changed
- `scripts/review_server.py` takes every path from `config.yaml`: the catalogue, the photo
  set, the trash directory, the label file, the embedding cache, and the variant groups.
  No path is hard-coded in the script now.
- `scripts/08_variants.py` takes the same four paths from `config.yaml`. The script writes
  the variant groups and the embedding cache that the review tool reads, so both scripts
  MUST use one value for each file.
- `common.OUT` is now `common.PHOTO_DIR`. The value does not change with the default
  configuration.
- `scripts/review_server.py` now needs `PyYAML`, because it imports `scripts/common.py`.

### Found
- New D4 metadata defects, found by a field cross-check of `catalog.jsonl` on 2026-09-17.
  **Every one of the 7 «Два Петра» cards carries `grapes = Саперави` and
  `category = Красное`**, although four of them name a white variety and describe a straw
  colour. `perovskih_aligote`, `uva-vallis-risling`,
  `vinodelnya-myshako-quintessence-reserve-risling-krasnoe-suhoe-131`,
  `vinodelnya-myshako-oranzhevoe-iz-belogo-gevyurtstraminer-krasnoe-suhoe-142`,
  `vinodelnya-zhakov-rkatsiteli-eskeyp-krasnoe-suhoe-119` and
  `agrolayn-heritage-dg-skin-contact-rkatsiteli-rkatsiteli-krasnoe-suhoe-12` also carry
  `category = Красное` against a white or an orange wine. 10 rosé cards carry a colour text
  that describes a red or a straw-yellow wine; those are candidates, not confirmed defects.
- Slug-namespace collisions. 10 slug families are only a grape name or a colour word, so the
  producer is not in the slug and a `-1` / `-2` counter is the only separator. `merlo`
  (Галицкий и Галицкий) and `merlo-1` (Mantra Estate) also share one photo file.
- The slug naming convention is not uniform. 36 slugs use underscores instead of hyphens,
  all from five producers: Усадьба Перовских, Denisov Winery, Два Петра, JD winery,
  Винодельня Орлова.
- Three test-set slugs are absent from the 2026-09-15 catalogue dump:
  `chateau-tamagne-select-blanc-brut-svo-yo-vino`,
  `vinodelnya-uzunov-bunt-tsitronnyy-magaracha-beloe-suhoe-139`,
  `vinodelnya-uzunov-roze-kaberne-sovinon-rozovoe-ekstra-bryut-127`.
- Re-measured on the 2026-09-15 dump: 34 shared-photo groups over 69 cards, and 70 groups
  over 154 cards that share one producer and one name. The earlier figures, 25 / 50 and
  64 / 141, came from an older snapshot and a different normalisation.

## 2026-09-16

### Added
- Agent photo hunt, batch 1. Six agents worked wines 1-48 of the `needs_positive`
  queue and wrote **87 proposals**, **29 wine notes**, and **102 photo comments**.
  Photos went from 2025 to 2112. No label was written: every result is a proposal
  for the reviewer.
- `work/hunt/` holds the state of the hunt. `queue.json` is the frozen 570-wine
  queue. `progress.json` records which slug went to which agent in which batch.
  `slices/` holds the per-agent input. `results/` holds the per-agent output.
  A later batch reads `progress.json` and does not repeat a wine.

### Added
- Agent photo hunt, batch 2. Six agents worked wines 49-96 of the `needs_positive`
  queue under `work/hunt/POLICY.md` and wrote **155 proposals**. Every one of the 48
  wines got at least one proposal, and 46 of 48 reached the target of 3.
- `work/hunt/POLICY.md`. The project owner set it on 2026-09-16. It OVERRIDES the
  matching rules of the `wine-hunt` skill. A photo of the right wine in an older
  label design is now proposed as `variant`. A clean studio shot on a white
  background is now acceptable. A lineup shot, a label-only crop, and brand lifestyle
  photography are now forbidden.
- `docs/catalogue-defects.md`. It collects every catalogue defect and wrong photo that
  the hunt found, grouped by the decision each one needs.
- Per-agent scratchpads at `work/hunt/scratch/<agent>/`. They fix the collision of
  batch 1.

### The cigarpro.ru run
- `cigarpro.ru` added as a photo source on the owner's instruction. Its Russian wines
  section holds **2042 products**, each with about five of its own photographs.
  `work/hunt/cigarpro/harvest_index.py` walked all 69 listing pages;
  `work/hunt/cigarpro/match.py` paired the products with the wines that need a
  positive. **483 of the 548** such wines have at least one cigarpro candidate.
- Batch 1 gave 12 agents a slice of 72 wines. Every one of the 72 held **no proposal at
  all**: they are the residue that the search-engine hunts and the irecommend run could
  not fill. **51 of the 72 now hold a proposal**; 21 stay empty.
- **146 cigarpro proposals** were written: 81 `positive` and 60 `variant` still pending,
  plus 5 that the reviewer has already confirmed as `positive`. 86 of them are back
  labels.
- Every cigarpro image carries a `CIGARPRO.RU` watermark over the label, on every size.
  The owner accepts it on the condition that each proposal is marked. An audit agent
  checked all 141 pending cigarpro proposals: **141 of 141** begin with the exact
  marker `WATERMARK cigarpro.ru | `, **141 of 141** name a cigarpro product page in
  `source_url`, and **141 of 141** carry a confidence from 0.80 to 0.95. No defect.
- A session rate limit killed the whole first cigarpro run part-way. 86 proposals had
  already reached the server; no agent had written its results file. The remaining work
  was recomputed from `review-labels.json` and finished by a resumable workflow.
  `work/hunt/cigarpro/HOWTO.md` now tells an agent to write its results file after the
  first wine.

### The irecommend run
- Five agents worked the 33 wines that batches 1 and 2 left short of 3 proposals.
  irecommend held a matching product for **2 of the 33**. The 521 wall was not hiding
  anything: irecommend indexes a producer's mass-market SKU, not the reserve, limited,
  kosher or single-vineyard bottle. 13 proposals came out of the run, and 10 of those
  came from other sites. Detail and the screening rule for a later run are in
  `ResearchLog.md`.

### Result of both batches
- **242 proposals over 78 wines**: 202 `positive` and 40 `variant`. 96 of the 570
  wines of the queue were worked; 474 remain. 55 wine notes and 257 photo comments.
  The agent totals reconcile exactly with `review-labels.json`.
- Batch 2 produced 155 proposals against 87 in batch 1, from the same number of
  agents and wines. Two causes: the `variant` rule recovered photos that batch 1
  discarded, and batch 2 started with the source list, the rate limits and the traps
  that batch 1 had to find for itself.

### Added
- Right-click Delete in the review page. A right-click on a candidate photo, in the
  table or on the large image, opens a menu with one item. The item MARKS the photo;
  it does not touch the file. The existing "apply" button now carries out the pending
  deletions together with the pending moves, behind one dialog that states each
  consequence apart. A deletion MOVES the file to `work/trash/<slug>/` and drops the
  whole entry. A photo that carries both a `delete` and a `reassign_to` is deleted and
  is not moved. New route `POST /api/mark-delete`; new field `delete` on a photo
  entry; new count `deleting`.
- `derived/bottles-fixed/` in `svoe-wino-hackaton`, with a README. It holds bottle
  photos fetched by hand for the wines that the official upload dump does not carry.
  The dated snapshot under `sources/` MUST stay as received, so a fetched file does
  not go into it.

### Fixed
- `fanagoriya-fanagoriya-hey-bey-shardone-beloe-suhoe-13` had no catalogue bottle
  (`local_path: null`, `match: "none"`). The bottle photo was fetched from the
  `og:image` of its `vino-svoe.ru` page, 406x1500 webp, and stored in
  `derived/bottles-fixed/`. `derived/catalog.jsonl` now points at it with
  `match: "manual"` and a `manual_bottle` record of the source. **A rebuild of
  `catalog.jsonl` drops this repair**, because `build_catalog.py` has no override step.
- The `del` pill hid the comment badge. Both sat at `top: 4px; right: 4px`, and the
  pill has the higher `z-index`, so a photo that carried a comment showed no comment
  badge exactly when the reviewer was about to delete the comment with the photo. The
  badge now moves aside, and the pill no longer takes the pointer. Found by an
  adversarial review of the diff; 22 agents raised findings and this one alone
  survived refutation.
- `docs/API.md` said the `url` of a proposal MUST be `http` or `https`. A `data:` URL
  has always worked and is the way every agent proposes a picture from a blocked host.
  The document now states it.
- `docs/catalogue-defects.md` section D was misread by an agent as "the renders look
  the same". The wording now separates the renders, which ARE separable, from the
  candidate photos, which usually are not.

### Changed
- Top-up pass run with `06_topup.py --need 3 --redownload`. It reopened **1632**
  wines that hold fewer than 3 accepted photos and freed 6120 retryable candidates.
  The driver runs again with `--per-wine 40 --top 16`, deeper than the first pass.
- The stalled first pipeline pass was resumed. It had stopped mid stage 2 on
  2026-09-15 at 02:39. `GPU_TASKS.md` said "running" and was wrong; the entry is
  corrected.

### Found
- `aligote-avtorskoe` and `aligote-avtorskoe-vino` share one `bottle_path`. They are
  one wine in two catalogue rows.
- `alma-valley-pino-nuar-beloe-ekstra-bryut-115` holds two unlabelled photos,
  `01_conf095.jpg` and `02_conf095.jpg`, that show the still red Pinot Noir 2020.
  They are a different wine and SHOULD be labelled negative.
- The render of `alma-valley-shardone-rezerv-beloe-suhoe-14` is a 2020 bottle whose
  label reads 13,0 %, not 14.
- The label of `abrau-dyurso-abrau-estates-beloe-shardone-suhoe-12` reads
  `CHARDONNAY / SAUVIGNON BLANC`; the slug names only `shardone`.
- `alma-valley-merlo-rezerv` `-14` and `-15` cannot be told apart in a photo unless
  the bottom label line is readable. Two agents reached this result on their own.
- One proposal is known to be wrong and cannot be withdrawn by its author:
  `aratti-muskat-belyj-polusuhoe` `02_agent.jpg`. Read the photo comment.
- `porusski.me` does not send its intermediate certificate, so `POST /api/v1/propose`
  cannot fetch it. A different CA bundle does not help. The `data:` URL path is the
  general answer. `review_server.py` needs no change. Details in `ResearchLog.md`.

### Added
- `scripts/bench_vlm_models.py`. It compares vision models on the stage 4 identity
  task with the production prompt of `04_verify.py` and the manual labels of
  `review-labels.json` as the ground truth. The sample is stratified and
  deterministic. The run is resumable: a finished call is not repeated.
- `scripts/bench_vlm_score.py`. It scores the benchmark output for two decision
  rules, `same_wine` and the production rule `accept`, and reports latency and
  token cost. The `unusable` stratum is scored apart from the main measure.
- `work/vlm_bench.jsonl` and `work/vlm_bench_report.md`. The raw answers and the
  scored report of the first run: 4 models, 300 pairs, 1200 calls, 0 errors.
- A ResearchLog entry with the result: `qwen3.7-flash`, `qwen3.8-flash`, and
  `qwen3.8-max` have the same accuracy on this task, but not the same error
  profile and not the same cost.

## 2026-09-15

### Added
- An HTTP API under `/api/v1/` for an agent: `GET stats`, `GET wines` with the
  filters `all`, `unlabelled`, `needs_positive`, `has_proposal`,
  `fully_labelled`, `in_variant_group`, `GET wine/<slug>`,
  `GET wine/<slug>/photos?label=...`, `POST propose`, and
  `POST search-by-image`. Every picture is named by an absolute path, so an
  agent reads the bytes with its own file tool.
- The status `proposed`. An agent writes a proposal, not a label: the photo lands
  as `NN_agent.<ext>` and the entry holds `proposed`, `by`, `confidence`, and
  `source_url`. A proposal is not counted in `labelled`. The card has a dashed
  border and a tag with the confidence, and the filter `holds a photo proposed by
  an agent` lists them. The reviewer answers with the keys `1` to `4`.
- `docs/API.md` with every route, every field, and the rule of the proposals.
- The skill `wine-hunt` in `.claude/skills/wine-hunt/` with the working
  instructions of the agent: the queries, the checks against the variant group,
  the confidence floor of 0.8, and what the agent MUST NOT do.
- `scripts/08_variants.py`. It finds the wine slugs that hold the same wine in
  another bottle and writes `derived/variant-groups.json`. Two steps: the same
  producer and the same name in `catalog.jsonl`, then the cosine similarity of
  SigLIP2 embeddings of the catalogue bottle photos. The metadata step gives 28
  groups over 63 wines of `my/`.
- `scripts/09_apply_moves.py`. It moves the photos that the review tool marked for
  another slug. A report run is the default; `--apply` moves the files. The script
  is safe to run twice, and a name that is taken gets a `_moved2` suffix.
- `scripts/review_server.py`. A manual review tool for the `my/` photo set.
  It starts a local HTTP server on port 8154 and opens a browser.
  The page shows one table row per wine. Column 1 holds the catalogue bottle photo
  of the wine from the strapi dump. The next column holds the candidate photos of
  `my/<slug>/`. Each candidate photo has a "V" button and an "X" button.
  "V" means the photo shows this bottle. "X" means it does not.
  A second click on the same button clears the verdict.
  Every click is written to `review-verdicts.json` at once. The file is read again
  at the next start. The tool has eleven sort orders, nine filters, and a text search.
  A click on a photo opens it at full size.
  The tool uses the Python standard library only. It needs no install step.
- `SMOKE_TESTS.md` with the manual test cases of the review tool.

- Five-stage pipeline that builds a real-world photo test set for all 2,018 wines
  in the `vino-svoe.ru` dump: `scripts/01_search.py` … `scripts/05_report.py`,
  driven by `scripts/run_pipeline.py`.
- `scripts/common.py` with the SQLite state schema, the studio-host deny list,
  the user-generated-content host list, and the gx10 request helpers.
- `README.md` that describes the set, the pipeline, and the reports.

### Notes
- The review tool reads the slug-to-bottle-photo map from
  `../svoe-wino-hackaton/derived/catalog.jsonl`. That file is written by
  `../svoe-wino-hackaton/scripts/build_catalog.py`.
- The tool does not test that a bottle photo file is present at start.
  The strapi `uploads` directory holds about 15,800 files on an external volume.
  One `stat` call there costs a large fraction of a second, so 811 calls block
  the start for minutes. The browser requests each bottle photo only when the row
  scrolls into view. `/img/bottle` answers 404 when the file is absent.
- Current size of the review job: 814 wines and 1,892 candidate photos.
  4 wines have no catalogue bottle photo. 3 of them are absent from
  `catalog.jsonl`. 1 has no `upload_file`.

### Changed
- The wine column holds a text field for a note about the whole wine. It is one
  line high until it holds a text, and opens while it is used. The text is saved
  after a pause of 700 ms and when the cursor leaves the field, through
  `POST /api/wine-comment`. The table is not drawn again while the note is saved,
  so the cursor stays in the field.
- A note about a wine is stored in the new top level map `wines` of
  `review-labels.json`, keyed by the slug. It is apart from the labels, because
  it states something about the wine and not about one photo. The count
  `wine_notes` is new, and `prune_state` drops the note of a wine that `my/` no
  longer holds.
- A picture dragged from another browser tab is accepted, on a row of a wine or
  beside the table. Such a drag carries an address, not a file, so the page reads
  `text/uri-list`, the `src` of an `<img>` in `text/html`, or plain text, and the
  server fetches the address through `POST /api/fetch-image`. A `data:` address is
  decoded without a request.
- The media type of an added picture comes from the first bytes of the file, not
  from the `Content-Type` of the host. A real case: `api.vino-svoe.ru` answers a
  WebP picture with no `Content-Type`, and the first version refused it.
  The same test now also repairs a wrong type from the file manager.
- The fetch refuses an address that is not `http` or `https`, and an address whose
  host resolves to a loopback, private, link-local, reserved, or multicast
  address, so a dragged link cannot reach a service of this machine or of the
  local network. The request carries a browser user agent string.
- A file dropped beside the table opens a dialog that asks for the wine, so a photo
  can be added to a named slug without a search for its row. The dialog offers
  five wines with their bottle photo for what is typed, over the slug, the name,
  and the producer. It names only the wines that already have a directory in
  `my/`. A hint at the bottom of the window states both ways to drop.
- Fixed: the edit that added the move dialog cut too wide a slice of the page
  script and removed `applyMoves` and every drag and drop handler. The build
  between 21:05 and 21:20 had no drag and drop. The handlers are back, and the
  check after each edit now counts all 23 handlers of the page.
- A photo with a comment carries a round badge in the top right corner of its
  card. The pointer over the badge opens a panel with the whole text. The panel
  keeps the line breaks and scrolls when the text is long, so a comment that
  states a move is readable. Before this, the comment was the `title` of the
  card: the browser tooltip was slow, cut the text, and dropped the line breaks.
- The header states `N moves pending` with an `apply` button whenever a move is
  recorded and the file is not moved yet. The button asks for a confirmation,
  moves the files through `POST /api/apply-moves`, and rebuilds the table from
  the answer. Before this, a recorded move was visible only through a filter or
  through a run of the script, so it was easy to forget.
- A moved photo loses its label, because the label judged the photo against the
  old wine. The comment is kept, and one line is put in front of it:
  `до переноса в <new> был в <old> с таким комментарием:`. The entry gets
  `moved_from` and loses `reassign_to`, so a second run moves nothing.
  The entry travels to the key of the target slug and of the new file name.
- The move logic lives in `review_server.py` as `plan_moves`, `perform_moves`,
  and `move_note`. `scripts/09_apply_moves.py` imports the module and calls the
  same functions, so the button and the script act the same way.
- The move question is a dialog, not a `prompt`. The dialog offers the five wines
  that the photo most likely belongs to, each with its catalogue bottle photo,
  name, and producer. `GET /api/suggest` ranks them: a member of the variant
  group first, then the same producer, then a shared word of the name, then the
  same grape and the same category. A field below still takes any slug.
- An image file dropped on the row of a wine is added to `my/<slug>/` through
  `POST /api/upload`. The name is `<next number>_manual.<extension>`, so a photo
  added by hand is easy to tell apart and sorts after the photos that the
  pipeline found. A file is at most 20 MB and MUST be JPEG, PNG, WebP, GIF, or
  BMP. The row is outlined while a file is over it.
- The rank of a photo is read with `RANK_RE` (`^(\\d+)_`) instead of the full
  `NAME_RE`, so a `_manual` photo sorts by its number and not at the end.
- The large view holds a comment panel at the right. The panel takes a free text
  comment about one photo and one wine slug. The text is saved as it is typed,
  after a pause of 600 ms, and a move to another photo or a close of the view
  flushes the pending text first. `POST /api/comment` is the route, the field is
  `comment`, and `count_state` answers a `commented` count. A comment is at most
  4000 characters.
- A photo with a comment carries a coloured bar at the left of its card, and the
  comment is the tooltip of the card. The row states `N noted`. The filter
  `holds a comment` is new.
- The keys of the large view do not act while the cursor is in a field. `Esc`
  leaves the field, and a second `Esc` closes the view. Without this rule a `1`
  inside a comment would label the photo.
- A click in the comment panel no longer closes the large view. Only a click on
  the background closes it.
- The review tool holds a fourth label, `variant`, on the key `4`: this wine in
  another bottle, such as another vintage or another package design. The reason:
  the catalogue holds one slug per bottle, not one slug per wine, so a photo of
  the right wine in the wrong bottle fits neither `positive` nor `negative`.
- The rows of one variant group stand next to each other, whatever the sort, and
  share one background colour. Two colours are used in turn, so two groups next
  to each other stay apart. The filter `has a similar wine (variant group)` shows
  only the wines of a group.
- A `copy` button next to the slug puts the slug on the clipboard. It falls back
  to a hidden text field when the clipboard API is not available, because the
  tool runs over plain HTTP on the loopback address.
- A photo can be moved to another wine slug. The `move` button under the photo and
  the `m` key in the large view ask for the target slug, and the field completes
  from the 2,103 catalogue slugs. The tool writes `reassign_to` into the label
  file and does NOT move the file. `scripts/09_apply_moves.py` moves the files
  later, on one command. A moved card carries a dashed outline.
- A photo entry can hold a `label`, a `reassign_to`, or both. Clearing one field
  no longer drops the other. The entry is removed only when no field is left.
- `POST /api/reassign` is new. `count_state` answers a `reassigned` count.
  `GET /api/rows` answers the variant groups and the list of catalogue slugs.
- The review tool labels a photo with one of three labels instead of two verdicts:
  `positive`, `negative`, and `unusable`. The reason: a `negative` photo is a
  wanted result, not waste. The set needs negative samples, so a photo that shows
  a different wine stays in the set as a negative sample of its slug. The earlier
  `no` verdict read as a rejection, and the card was dimmed like waste.
  `unusable` is now the only label that takes a photo out of the set: no bottle,
  unreadable, or a duplicate. A `negative` card has its own blue colour and is not
  dimmed. Only an `unusable` card is dimmed.
  The keys are `1` positive, `2` negative, `3` unusable.
- The label file is `review-labels.json`. It was `review-verdicts.json`. The top
  key is `labels`, the entry field is `label`, and the value is one of the three
  label names. `version` is 2. The counts are `positive`, `negative`, `unusable`,
  and `labelled`. The old name and the old values held no data, so no migration
  was needed.
- The API routes are `POST /api/label` and `POST /api/labels`. The body field is
  `label`. `GET /api/rows` and `GET /api/state` answer with the key `labels`.
- The sort orders and the filters follow the three labels: `unlabelled first`,
  `positive count`, `negative count`, `unusable count`, `has a negative sample`,
  `has an unusable photo`, and so on.
- The large view writes its place into the address of the page as
  `#<slug>/<photo file name>`. Such an address can be sent to another person. The
  tool opens the large view at that photo when the address is opened, and clears
  the filter and the search when the wine is not in the current view. The address
  is written with `replaceState`, so the arrow keys do not fill the history.
- The large view of the review tool holds the keyboard. `Right` and `Left` go to the
  next and the previous photo of the wine on screen. `Down` and `Up` go to the next
  and the previous wine, at its first photo. `1` confirms the photo and `2` rejects
  it; the same key again clears the verdict. `Esc` closes the view.
  The keys follow the order that the table shows, so the sort and the filter also
  control the keyboard pass. The table scrolls to the wine on screen, so the place
  is held when the view closes.
- The large view states the verdict of the photo on screen in a badge at the top:
  `confirmed V`, `rejected X`, or `not reviewed`. The caption under the candidate
  photo states the place in the wine and the review progress of the wine.
- A click on the catalogue bottle in the table opens the large view at the first
  photo of that wine. The first version showed the bottle alone, and the arrow keys
  had nothing to move through.
- `setVerdict` takes a slug and a file name. It took a card element before. The
  large view has no card, so both the button of the table and the key of the large
  view now call the same function.
- The two images of the large view stay next to each other in the middle of the
  screen. The first version gave each image half of the width, so a wide monitor
  pushed the catalogue bottle and the candidate photo to opposite edges and the
  two labels were far apart. Each figure now shrinks to the width of its own
  image. The caption is held out of the width of the figure, so a long wine name
  wraps instead of moving the images apart.
- The large view of the review tool shows two images side by side: the catalogue
  bottle at the left, the candidate photo at the right. The first version showed the
  candidate photo alone, so the operator had to hold the label in memory while the
  large view covered the table. Each image has a caption. A click on a large image
  keeps the view open. A click on the background closes it, and so does `Esc`.
  A click on the catalogue bottle in the table shows that bottle alone.
- Stage 4 uses a stricter prompt. The first prompt accepted a photo that showed only the
  producer brand. A back-label close-up of a different Agora wine passed as a match.
  The new prompt requires the front label of that exact wine and rejects a back label,
  a cork, a box, a glass, or another wine of the same producer.
  It adds the field `front_label`. Acceptance now needs
  `same_wine=true`, `studio=false`, and `front_label=true`.
  On a 6-case probe the new prompt kept every true match and removed the false match.
- Stage 2 downloads through one flat task queue over many wines. The first version ran one
  wine at a time, so one slow host stalled a whole wine and throughput fell to 0.8 images/s.
  The flat queue reaches 5 to 8 images/s.
- Stage 2 rewrites `irecommend.ru` image URLs to the CDN mirror `cdn-irec.r-99.com`.
  Direct requests answered HTTP 521 for 1,585 of 1,585 tries. The mirror answered every try.
  A per-host limit of 12 requests in flight keeps the mirror stable.
- The driver takes `--stages`. Stages 2 and 3 run in one process, stage 4 in another.
  llama-swap on gx10 holds `siglip2` and `qwen3-vl-32b` at the same time, so the two
  processes do not make the host swap models.

### Measurements
- Stage 1 search: about 960 wines/h at one Yandex query per 1.3 s.
- Stage 2 download: 3,287 of 3,677 candidates fetched for 200 wines in 9.8 min.
- Stage 3 embed: 19 images/s including the border-whiteness measure.
- Stage 4 verify: 1.32 s per pair at 12 concurrent requests, about 340 wines/h.
  12 workers gave almost no gain over 6 workers, so the GPU is the limit.
- A smaller VLM input (320 px instead of 448 px) gave no speed gain and lower agreement.
- One call carrying 5 candidates cost 35 s and agreed with the pairwise verdicts
  on only 90% of cases. Pairwise verification with concurrency is both faster and more exact.
- Acceptance does not fall with the similarity rank: rank 1 accepted 59%, rank 8 accepted 42%.
  Verifying only the top 4 candidates would lose wines that reach 3 photos at ranks 5 to 8.

### Findings
- The official Svoe Vino API exposes `POST /v1/wines/search-by-photo`.
  The Swagger document is at `https://api.vino-svoe.ru/docs`
  and the specification at `https://api.vino-svoe.ru/docs/swagger-ui-init.js`.
  The endpoint needs no token. It is the baseline recognizer, not ground truth.
- DuckDuckGo image search rate-limits this host after a few dozen queries and answers 403.
  Yandex Images answers about 30 results per query and stayed available at one query per 1.3 s.
- SigLIP2 similarity alone is not a decision rule. A supermarket shelf photo of unrelated
  Spanish wines scored 0.55 against the reference bottle. The vision model rejected it at 0.95.
- SigLIP2 batching on gx10: one image per request costs 7.9 s with model load,
  a batch of 32 costs 30 ms per image.
- `qwen3-vl-32b` pairwise verification costs about 8 s per pair when it writes a reason,
  and about 0.6 s per pair with `max_tokens=120` and 4 concurrent requests.

### Incidents
- The volume `/Volumes/T7_2TB` reached 100% with 254 MB free during stage 2.
  The cause is not this project: the volume held 1.8 TB before the run and this project
  used 1.5 GB. `work/raw` and `work/thumbs` now live on `/Volumes/Storage`
  and are reached through symbolic links, so the project keeps its paths.
  The database stores absolute paths and the links keep them valid.
- Moving `work/raw` while stage 4 was running closed 333 wines with no check.
  Stage 4 read `os.path.exists()` on files that were in transit, found none, and marked
  each wine verified with zero verdicts. 314 of them had usable candidates.
  Stage 4 now separates the two cases: a wine with no candidate is closed, a wine whose
  candidate files are missing is skipped and stays open. The 314 wines were reopened.

### Result on the first 102 fully checked wines
- 55 wines (54%) have at least 1 real-world photo.
- 32 wines (31%) have at least 3.
- 215 photos accepted out of 854 checked, so the vision model rejects about 75%
  of what the search engines return. The search noise is the reason, not the filter.

### Cross-check against the official recognizer
- `scripts/07_api_check.py` sends every accepted photo to
  `POST https://api.vino-svoe.ru/v1/wines/search-by-photo` and records the rank of the
  expected slug in `candidates.api_rank`. 0 means the slug was not in the answer.
- On 200 accepted photos the official recognizer returned the expected slug
  at rank 1 for 28% and inside the top 5 for 66%.
- A visual check of 12 photos that the recognizer missed found that most are correct
  photos of the right wine that are simply hard: a steep angle, a close-up of part of the
  label, or several bottles in one scene. One of them reads "MUSCAT BLACK AGORA",
  which is the target wine.
- The acceptance rule was therefore left as it is. `api_rank` is reported per photo as a
  difficulty label: a photo the baseline already handles, or a photo that it misses.
- A minority of accepted photos show only the producer brand on a neck label or a cork.
  These stay in the set and are visible in the report for manual removal.

## 2026-09-15 — final result

### The set
- 2,018 wines searched. 128,483 candidate images found, 117,660 of them on
  user-generated-content hosts. 33,068 images downloaded.
- 25,172 pairwise vision checks made. 2,163 photos accepted. Acceptance rate 8.6%.
- 844 wines (42%) have at least 1 real-world photo. 386 wines (19%) have 3 or more.
  1,174 wines (58%) have none.
- `my/` holds 844 directories and 2,016 photos, at most 4 per wine, 308 MB.

### Why 3 photos per wine was not reached
- The limit is the corpus, not the filter. A search for a small Russian producer returns
  images of other wines of the same grape, other wines of the same producer, or shop
  stock photos. The vision model rejects them correctly.
- The deep pass proves the point. It made about 15,000 extra checks at depth 20 and added
  only 73 wines to the group with 3 photos.

### Cross-check with the official recognizer
- 1,974 accepted photos were sent to `POST /v1/wines/search-by-photo`.
- The expected slug came back at rank 1 for 888 photos (45%) and inside the top 5
  for 1,455 photos (74%).
- The 26% that the recognizer misses are mostly correct photos that are hard:
  a steep angle, a close-up of part of the label, or several bottles in one scene.

### Verification backends
- Three vision backends ran in parallel with work-stealing:
  `qwen3-vl-32b` on gx10 (6,497 calls), `qwen3.8-flash` on the qwencloud token-plan
  endpoint (9,075 calls), and `qwen3.7-flash` on dashscope-intl (2,538 calls).
- Both cloud models were checked against 24 pairs already judged by `qwen3-vl-32b`.
  Agreement was 24/24 for each, and every answer parsed as JSON.
- The `candidates.vlm_model` column records the backend for each verdict.
- The qwencloud endpoint throttles above 8 concurrent requests. At 16 workers the cost
  per call tripled. 8 workers is the setting.
- Adding the cloud backends raised the rate from 320 to about 800 wines/h.

### Remaining material
- 86,071 candidate images were found by search and never downloaded. Working through
  them would take about a day. The yield curve of the deep pass suggests it would add
  roughly 50 to 100 wines to the group with 3 photos.
