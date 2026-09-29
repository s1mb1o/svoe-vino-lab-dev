# Plan 85: matcher cascade pipeline and fast answer mode

Date: 2026-09-29. Project: `svoe-vino-lab`, production matcher `matcher/` (M) and lab
`workbench/` (W). Session: drink-atlas-workspace-ae [8dd8e8]. The owner approved the plan
at 2026-09-29T13:26:26+0300. The numbers 83 and 84 were taken by
`83_matcher-api-pipelines.md` and `84_background-new-wine-index.md` of other sessions.

## Context

The matcher runs the simplest lab pipeline (`siglip2-p512-as-is`, R@1 74.3 % on `my`). The
best lab pipeline adds a code lookup, a SAM3 package crop, and a VLM cluster re-rank
(R@1 85.5 %). The owner asks for these stages in the matcher, with more parallel work, and
for a time budget on `POST /v1/eval/predict`. The hackathon harness gives each request
10 s (`curl --max-time 10`, curl start to response) and the SLA is 3 s. The harness is
sequential; its photos are 3024×4032 WebP files of about 1.25 MB.

Owner decisions (2026-09-29, plan mode):

1. A timer starts at the HTTP request. Its limits are in `config.yaml`.
2. Fast answer mode applies to `POST /v1/eval/predict` alone. At 2.9 s, when an answer
   exists, return it. `POST /v1/match` runs the same stages with no 2.9 s cut.
   `POST /v1/group/match` does not change.
3. At the start, in parallel, each configurable: a barcode scan of the full photo
   (`qr-scanner`, engine `zxing-cpp`); SAM3 "full" (package + hand + label nouns, one
   pass); SAM3 "packages only"; SigLIP2 of the whole photo.
4. SigLIP2 so400m NaFlex p512 (configurable through the index name).
5. Score: the best cosine over all rows of a wine, so the maximum over the rotation angles
   of each reference image (plan 82 index `…-naflex-p512-rot5`).
6. VLM re-rank (`qwen3.5-9b-nvfp4`, the cluster rule) when rank 1 and another card of its
   cluster are in the top `window` (configurable, default 10).
7. After the full SAM3 answer, when time is left: two more scans, on the package crop and
   on its label crop. A package or label code wins over a full-photo code.
8. The VLM always starts when the rule triggers. At the deadline it is cancelled.
9. A new async backend `cascade` with `httpx.AsyncClient` (new pinned dependency). The
   `siglip2` backend stays unchanged, for rollback.
10. GTIN data: the matcher reads the table `wine_code` of the catalogue copy directly. No
    schema change, no 8168 restart. This is an owner exception to the plan 75 rule "fixed
    views only".
11. Fix the hand-selection SAM3 call in this task (see "New findings").
12. Benchmark: `official-real-photos` (81) and the full `my` (2,226), one photo at a time.
13. First merge the prod branch `codex/group-quality-filter` (`be84a94`) into `main`.
14. `packages_first` default `false`: the gx10 SAM3 server returns the requests of one
    batch together (`_run_jobs` in the version-controlled copy
    `~/Admin/gx10/scripts/inference/sam3/server.py`), so the second request cannot come
    back earlier. The A/B of Verification 7 decides.

## Measured facts

- SAM3 uncached (lab, 1 worker, with `hand`): median 1,500 ms, p95 5,888 ms. GPU cost at
  idle: 0.71 s for one image, 0.50 s per image at batch ≥ 2. `/segment_multi` encodes the
  image one time and labels each instance; `/segment` takes one noun and gives no `label`.
- SigLIP2 embedding 44–87 ms. qr-scanner `zxing-cpp` 10–200 ms (`auto` runs SAM3 + VLM for
  8–15 s and MUST NOT be used). VLM re-rank call 0.9–1.5 s idle, median 2.7 s and p90
  4.1 s at 4 in parallel.
- Lab rot5 runs on `my`: whole photo 77.35 %, box crop 79.60 %, masked crop 79.84 % R@1;
  the rot5 search costs 22 ms median, 40 ms p99 (163,440 × 1152 rows).
- Codes: 74 Active wines have a GTIN, 37 a QR URL; 2 GTIN values and 5 QR values are
  shared. The best run answered 32 of 2,226 photos by a code.
- p512 rule files: 208 clusters, 516 wines, 166 sheet and 42 verdict rules, 0 errors,
  built from an older vector file (wines added after 2026-09-28 are in no cluster).
- Gateway: `qwen3.5-9b-nvfp4` is vLLM in the non-exclusive group `small` (cold start
  about 3.5 min; a request for another `small` model stops it). `sam3` has no ttl. No
  call of this pipeline unloads another model of the pipeline.
- The best lab run used other settings: the "largest bottle" rule, the local zxing-cpp
  2.3.0 with tile scan, the p256 rules, the fixed 512 model. This combination was never
  measured as a whole.

## Design

### Configuration (`M/config.yaml`)

```yaml
matcher:
  pipeline: siglip2-p512-as-is   # unchanged until the benchmark; the prod switch is an owner step
  fast_answer:                   # POST /v1/eval/predict alone
    enabled: true
    answer_at_seconds: 2.9       # SLA 3.0 s minus a reserve of 0.1 s (Verification 5 checks it)
    timeout_seconds: 9.5         # harness timeout 10 s minus a reserve of 0.5 s

pipeline:
  - name: cascade-p512-rot5
    backend: cascade
    catalog: workbench/data/catalog                          # a catalogue copy (plan 75)
    embedding: gx10-siglip2-so400m-patch16-naflex-p512-rot5  # model, patches: index.json
    endpoint: "{env:SIGLIP2_ENDPOINT}"                       # gateway root
    whole_image: true              # SigLIP2 of the whole photo at t0 (fallback answer)
    barcode:
      endpoint: "{env:QR_SCANNER_ENDPOINT}"                  # …/upstream/qr-scanner
      engine: zxing-cpp
      crops: true                  # scan the package crop and the label crop
    sam3:
      endpoint: "{env:SAM3_ENDPOINT}"                        # …/upstream/sam3
      threshold: 0.35
      hand: true
      label: true
      packages_first: false        # a second request with the package nouns alone
    rerank:
      clusters: gx10-siglip2-so400m-patch16-naflex-p512      # directory of the rule files
      endpoint: "{env:VLM_ENDPOINT}"                         # http://…:18081/v1
      model: qwen3.5-9b-nvfp4
      window: 10
      side: 1536
      max_tokens: 256
      timeout_seconds: 60          # /v1/match; predict is bounded by the budget
```

- The client adds `/v1/embeddings`, `/segment_multi`, `/scan`, `/chat/completions` (the
  owner's variables of 2026-09-28T08:55:00). Prod and the benchmark use port 18081.
- Strict validation of a `cascade` entry and of `matcher.fast_answer`: an unknown key, a
  bool where a number is due, a non-finite number, `answer_at ≥ timeout`, `window < 2`,
  or `engine: auto` is a `ConfigError` that names the key. `fast_answer` is valid only
  with a `cascade` pipeline. Omitting `barcode`, `sam3`, or `rerank` turns that stage off.
- Fixed constants with the lab values: package nouns `wine bottle, can, packet, box`,
  label noun `label`, mask threshold 0.5; scans at long side 1600 px up or down; formats
  EAN-13, Code 128 only as a valid GTIN-13, and QR; SigLIP2 input long side ≤ 1024 px;
  the IoU 0.8 for "the same package"; per-call timeouts in match mode (SAM3 30 s, SigLIP2
  30 s, scanner 10 s). `rank_packages` still drops instances below 0.4
  (`group.DETECTION_THRESHOLD`); labels count from 0.35, as in the lab.

### Timer and budget

- `RequestProtectionMiddleware.__call__` (`M/protection.py:64`) takes
  `started_at = perf_counter()` after uvicorn parsed the headers, before the auth, the
  queue, the upload, and the multipart parse. It stores the value in
  `scope["state"]["started_at"]`. `predict` builds the budget from it (fallback: the
  handler start). The upload, the queue wait, and the archive write count in the budget.
- The connection-accept time is not available in uvicorn, and on a keep-alive connection
  it is not the request start. The harness runs one `curl` per photo.
- The time before the headers arrive (DNS, TCP, TLS, the edge, the tunnel) and the
  response transfer are outside the server clock. The reserve covers them.
- `match` gets no `answer_at` and no hard limit (only the per-call timeouts).

### Stages

| Stage | Starts | Work |
|---|---|---|
| `decode` | first | One decode: frame 0, EXIF, alpha on white. A damaged image gives 422, no call. |
| `scan_full` | after decode | Photo at long side 1600 → `/scan` → filter → lookup. |
| `sam3_full` | after decode | `/segment_multi`, package nouns + `hand` + `label`, JPEG q86 at 1600. |
| `sam3_packages` | after decode, if `packages_first` | Package nouns alone. |
| `whole` | after decode, if `whole_image` | `model_input` pixels → embed → `Bundle.ranked("full")`. |
| `crop` | the first SAM3 answer with a package; again when `sam3_full` selects a package with IoU < 0.8 | Box crop of the full-resolution photo (the refined-mask box, as the lab), ≤ 1024 → embed → rank. |
| `scan_package`, `scan_label` | `sam3_full` has a package (and a label) | Box + 10 % margin from the full-resolution photo, 1600 up or down → `/scan`. |
| `vlm` | the trigger holds on the primary ranking, the full SAM3 answer exists, no unique code | Label cut on white at long side 1536 (else the whole photo) → `/chat/completions`. |

- Package: `main_scene.rank_packages(...)[0]` (hand-aware when hands exist).
- Label: the port of `W/pipeline/alternatives.py` rules, with the selected package box as
  "the bottle": labels whose centre lies on the package, not the package itself, the
  largest wins, body labels give the box cut. No package but labels (a close-up): the
  largest label, no package test.
- Primary ranking: the crop ranking; with no package, the whole ranking (start `whole`
  if it is off). The re-rank applies to the primary ranking.
- The VLM answer depends on the rule and the picture alone. `decide` applies it to the
  current primary ranking. No retries (the lab sleeps 5 s between attempts).

### Decision and stop rules

```text
decide():
  1. first unique hit of (package codes, then label codes)        → final answer
  2. first unique hit of the full-photo codes                      → answer, not final
  3. first shared GTIN (crop codes, then full-photo codes)         → its wines first at 1.0
     (a shared QR URL never decides)
  4. re-ranked primary ranking > primary ranking > whole ranking   → answer, not final
loop:
  answer = decide(); if answer is final → return
  cancel the pending tasks that cannot change the answer (for example the VLM after a
  unique code, `whole` after the primary ranking in predict)
  no live task → return;  now ≥ timeout → return
  predict and now ≥ answer_at and answer exists → return
  wait for the first finished task, or answer_at, or timeout
finally: cancel every pending task (httpx closes each connection; vLLM should abort)
```

- predict: the first slug. At the hard limit with no answer: `{"slug": ""}` with 200.
  All tasks done, no answer, and at least one failure: the first failure with its status
  and detail (502 or 504, as today). A failed stage never fails the request by itself.
- match: code wines at 1.0, then the primary ranking without them (a unique code keeps a
  tail, so the bot margin stays above 0); remove duplicates and wines without a card;
  clamp each score to `min(max(s, -1), 1, previous)`, so scores never increase; cut at
  `k`. A shared GTIN gives each of its wines 1.0 (lab parity; the bot then sees margin 0).
- A code wine without a vector keeps its answer in predict; match needs its card.

### HTTP client and CPU work

- One `httpx.AsyncClient` per app, opened and closed in the FastAPI `lifespan`.
  `trust_env=False`, no redirects, explicit timeouts per call (`connect` 1 s, the rest
  the stage limit or the remaining budget), `keepalive_expiry` 2 s with one retry on a
  stale connection, `Limits(max_connections=64, max_keepalive_connections=16)`, streamed
  bodies with caps (SAM3 16 MB as today).
- CPU work (decode, resize, encode, mask refine limited to the region, the rot5 search)
  runs in a dedicated `ThreadPoolExecutor` (8 threads), never on the event loop. The
  default executor stays free for `validate_image` and the archive. Estimate: 0.45–0.8
  CPU-seconds per request, 0.25–0.4 s of it before the crop ranking.
- Request PNGs use `compress_level=1` (lossless, the same pixels, less CPU).

### Data

- Codes: `M/catalog.load_codes(catalog_dir)` reads, read-only, `SELECT c.kind, c.value,
  c.wine_slug FROM wine_code c JOIN wine_catalog w ON w.wine_slug = c.wine_slug WHERE
  w.state = 'Active' AND c.kind IN ('gtin', 'qr_url')` (the query of
  `W/pipeline/barcode.py`) → `{(kind, value): sorted slugs}`. A missing table or column
  is a `CatalogError` at start. Decoded values go through the exact port of
  `W/pipeline/codes.py` `clean_gtin` / `clean_qr_url`, the form of the stored values.
- Rules: `<catalog>/embeddings/<rerank.clusters>/clusters.json` and `cluster-rules.json`
  (`spaces.combined.clusters`, `spaces.label`, `cards`). `W/scripts/copy_catalog.py
  --embedding …-p512-rot5 --embedding …-naflex-p512 --no-images` already copies both
  directories with the rule files (about 770 MB). No workbench code change.
- Names for the verdict prompt: `matcher_wine.name`.

### Audit trace

`response_data` gets `decision` (`source`: `code_package`, `code_label`, `code_full`,
`gtin`, `rerank`, `crop`, `whole`, `none`; `reason`: `final`, `done`, `answer_at`,
`timeout`; `answered_ms`; the code), `stages` (`id`, `start_ms`, `end_ms`, `status` ok |
error | cancelled, `error`), and `rerank` (the lab explain record). They go into
`request.json`. The API response does not change. matcher-inspector reads only
`response.status_code` and `response.slug`.

### Files

- New `M/services.py`: async clients `embed`, `segment_multi`, `scan`, `chat`, the error
  mapping (`Siglip2Error`, `GroupMatchError`, new `ScanError`, `VlmError`).
- New `M/photo.py`: `decode`, the SAM3 copy, scaled PNGs, crops, the refined box.
- New `M/codes.py`: port of `W/pipeline/codes.py` (`check_digit`, `clean_gtin`,
  `clean_qr_url`) and of `W/pipeline/barcode.py` (`read` filter, `hits`, `find`,
  `is_unique`).
- New `M/labels.py`: port of `W/pipeline/alternatives.py` (`_label_candidates`,
  `body_labels`, `label_box_cut`, `label_cut`) and `W/pipeline/derive.py` `refine_mask`.
- New `M/rerank.py`: port of `W/pipeline/cluster_rerank.py` (`RuleBook`, `trigger`,
  prompts verbatim, `options_of`, `compared_answer`, `sheet_prompt`, `verdict_prompt`,
  `verdict_schema`, `sheet_scores`, `verdict_choice`, `reorder`, `png_of`) and
  `W/pipeline/label_rules.py` (`normalize`, `NOT_VISIBLE`, `parse_json`, the payload of
  `ask`).
- New `M/cascade.py` (config dataclasses, `CascadeMatcher`) and `M/cascade_run.py` (the
  run loop, `decide`, the blocking rules, the match pairs).
- `M/siglip2.py`: split `model_input` so it also runs on a decoded image; share the
  request body and the vector check. Behaviour unchanged.
- `M/group.py` (after the merge): `_validate_sam3` takes the allowed label set of its
  caller; `_normalize_image` keeps its 400 mapping.
- `M/main_scene.py`: the hand-selection fix, `/segment_multi` with `texts`.
- `M/catalog.py`: `load_codes`, the rule-file loader.
- `M/service.py`: `matcher.fast_answer`, the `cascade` dispatch, async default adapters
  on `_MatcherSettings` (`to_thread` of the sync methods), so `mock` and `siglip2` behave
  as today. Readiness of `cascade`: one SigLIP2 embedding, `GET <SAM3>/health`,
  `GET <scanner>/health`; never the VLM.
- `M/protection.py`: store `started_at`. `M/app.py`: async operations, the budget, the
  `lifespan`, the new errors in the expected tuple.
- `M/requirements.txt`, `M/requirements.lock`: `httpx` pinned; the lock regenerated with
  the `uv pip compile … --generate-hashes` command of `M/README.md`.
- `M/config.yaml`: the new entry (not selected).
- Tests: `M/tests/cascade_fakes.py` and new `M/tests/test_cascade*.py`,
  `test_codes.py`, `test_labels.py`, `test_rerank.py`; changes in `test_catalog.py`,
  `test_hand_selection.py`, `test_service.py`. New `W/tests/test_matcher_parity.py`:
  the matcher prompts and constants equal the lab ones (W already imports M).
- Docs: `M/README.md` (Russian, as the file), new `M/docs/cascade.md` (STE),
  `M/docs/hand-selection.md`, `M/TESTING.md`, `M/SMOKE_TESTS.md`, `M/ChangeLog.md`,
  `M/ResearchLog.md`; `<workspace>/deploy/gx10/matcher-dev.md`, `matcher-prod.md`,
  `matcher.env.example`, `<workspace>/deploy/ChangeLog.md` (the catalogue mount,
  `QR_SCANNER_ENDPOINT`, `VLM_ENDPOINT`).

## New findings (rule 42)

1. `M/main_scene.py:37-39` sends `text="wine bottle, can, packet, box, hand"` to
   `<SAM3>/segment`, which takes one noun and returns no `label`; with
   `require_labels=True` any detection gives HTTP 502. The test fake does not check the
   route or the field. Checked in the code and the gx10 service code, not live. Prod has
   `hand_selection: false`. Fixed in this plan (decision 11).
2. Prod runs `be84a94`, which is not on `main`. A deploy from `main` drops the shelf
   filter. Resolved by decision 13.
3. Reported, not fixed here: the deploy documents disagree on the rollback image
   (`matcher-prod.md:293` `11ebfbf`, `deploy/ChangeLog.md:18` `013ab56`); nothing keeps
   the VLM warm.

## Risks

1. The 0.1 s reserve may be too small for the public path (Princess edge + reverse SSH
   tunnel). Verification 5 measures the gap.
2. VLM cancellation needs llama-swap to pass the disconnect and vLLM to abort. Not
   verified; Verification 8 checks it. A cancelled SAM3 job still runs on the GPU.
3. Cold starts exceed 10 s (VLM about 3.5 min, NaFlex SigLIP2 about 48 s). Warm the
   models before an evaluation.
4. Memory: the rot5 matrix needs 753 MB; the load can peak at about 2.4 GB (an estimate
   from reading `M/catalog.py`: temporaries of the vector checks), in the shared gx10
   memory. Measure it at the dev start.
5. The planned combination was never measured. The bot thresholds were tuned on
   whole-photo p512 queries; the rotation and the crop raise the wrong scores too.
6. A parallel client gets 503 after the 0.25 s queue wait when 8 requests run (the
   harness is sequential; known issue 1 applies).

## Order of work

0. Record the owner message and all answers in `W/docs/owner-messages.md`. Read
   `W/ACTIVE_WORK.md` again and add this session's section with the files above. Copy
   this plan to `W/docs/plans/85_matcher-cascade-fast-answer.md`.
1. Merge `codex/group-quality-filter` into `main` through a private `GIT_INDEX_FILE`.
   First check that no session has uncommitted changes in the merged files. Resolve
   `M/group.py` and `M/tests/test_group.py`: keep the shelf filter of `be84a94` and the
   `text` / `require_labels` parameters of `main`. Run all matcher tests. Ask the owner
   for the merge commit.
2. The hand-selection fix and its test.
3. `httpx` and the lock file.
4. `codes.py`, `labels.py`, `rerank.py`, `photo.py`, the `catalog.py` loaders, the
   `siglip2.py` split, with unit tests and the parity test.
5. `services.py`, `cascade_run.py`, `cascade.py`, `service.py`, `protection.py`,
   `app.py`, with the fakes and the tests below.
6. Docs and `M/config.yaml`.
7. Ask the owner for the commit. Then the dev deployment and the benchmark
   (Verification 3–8). Results go to `M/ResearchLog.md` and `M/ChangeLog.md`.
8. Give the owner the prod switch commands (the owner runs the switch).

## Verification

1. Matcher unit tests: `~/.venvs/svoe-vino-lab/bin/python -W error::ResourceWarning -m
   unittest discover -s matcher/tests -v` from the svoe-vino-lab root; compare `Ran N`
   with the count of `def test_`; `matcher/tests/run_ci.sh` (no skips). Fakes
   (ThreadingHTTPServer, a delay per request): SAM3 (answers by `texts`), scanner (codes
   by image content), SigLIP2 (vector by content), VLM (records the payload and a client
   disconnect). Cases:
   - deadlines: all fast → the answer before `answer_at`; slow VLM → the crop answer at
     `answer_at` ± 0.15 s and the fake VLM sees the disconnect; slow SAM3 → the whole
     answer at `answer_at`; no answer at `answer_at` → the first answer after it; all
     hang → `""` at the hard limit; all fail → 502 with the first detail; a damaged image
     → 422 and no call; a body sent in parts over 0.3 s → the answer at `answer_at` from
     the first byte;
   - priority: package code > full-photo code > re-ranked > crop > whole; the full-photo
     code waits for the crop scans except at `answer_at`; shared GTIN; shared QR; an
     inactive wine's code is ignored;
   - SAM3: `packages_first` with a different package → a second crop embedding; IoU
     ≥ 0.8 → one; both SAM3 fail → 200 from `whole`; a close-up with labels and no
     package;
   - `/v1/match`: no cut; non-increasing scores (also the 1.0000001 clamp), ranks 1..n,
     unique slugs, `k`, cards; a unique code keeps a tail;
   - re-rank: the exact VLM payload; sheet and verdict order; `reorder` keeps the
     position scores; a VLM error or `finish_reason: length` keeps the base order;
   - ports: codes (GTIN-14, check digit, Code 128 GTIN only, QR), labels (the lab cases),
     `model_input` bytes unchanged by the split;
   - concurrency: 4 parallel predicts with a slow VLM return near `answer_at`; after 20
     cancellations a normal call works; no task is left in `asyncio.all_tasks()`;
   - config rules; the hand-selection fix (the fake checks `/segment_multi` and
     `texts`); `load_codes` on a fixture with `wine_code` and `wine_catalog`.
2. The present suites stay green, and `openapi.yaml` equals the live schema. W suite:
   `python3 -m unittest discover -s tests -p 'test_matcher_parity.py'`.
3. Local smoke (Mac, gateway 18081, a scratch catalogue copy): 20 photos of `my`; read the
   traces. Read `/running` first.
4. Dev deployment on gx10 port 29000 (`<workspace>/deploy/gx10/matcher-dev.md`; a
   committed revision; the catalogue copy under `/srv/svoe-vino-lab/dev/matcher/data/`;
   the four endpoint variables). Then `deploy/test/check.sh dev` and
   `matcher/tests/participant_test.sh` against `http://192.168.86.14:29000`.
5. Edge gap: the three official queries through the public edge from an outside host;
   compare `time_total` with the server `duration_ms`; set `answer_at_seconds` from it.
6. Benchmark: a row in `/Users/ashmelev/Admin/GPU_TASKS.md`; the driver under
   `caffeinate -ims -w <pid>`: `W/pipeline/remote_run.py --config <scratch config>` with an
   entry `backend: svoe-vino-ru`, url of dev `/v1/eval/predict`, `response: slug-object`,
   `workers: 1`; first `official-real-photos`, then `my`. Report R@1, false match at 1,
   the share within 3,000 ms, p50/p95/max, and the count of each answer source. Compare
   with the lab (74.26 % as-is, 79.60 % rot5 crop, 83.85 % barcode-rerank p512).
7. A/B on `official-real-photos`: `packages_first` false and true (time of the crop
   answer, share of `whole` answers).
8. VLM cancellation: a scratch config with `answer_at_seconds: 0.3`, photos that trigger
   the re-rank; `vllm:num_requests_running` of `/upstream/qwen3.5-9b-nvfp4/metrics` (the
   model is loaded then) MUST fall to 0 about 1 s after each answer.
