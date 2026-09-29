# Change log

## 2026-09-29

- The bundle `data/gx10-siglip2-so400m-patch16-naflex-p512/` is in git now (owner
  messages of 2026-09-29 about 22:35 and 22:46). This replaces the answer "Keep out of
  git". The bundle is byte-identical to the gx10 prod bundle (6 of 6 SHA-256). A clone
  can run the real matcher with a SigLIP2 endpoint alone.
- Fixed the findings of the second matcher review of 2026-09-29 (owner message of
  2026-09-29T20:59:59+0300 and answers of 21:07:52):
  - `test_the_default_config_selects_the_siglip2_pipeline` checks only the selected entry
    of `config.yaml`. Since `f199e4d` the file also holds `cascade-p512-rot5`, and the
    test failed: 207 of 208 tests passed at `84035f9`.
  - `POST /v1/group/match` answers HTTP 503 before the SAM3 request when the selected
    pipeline has no vectors of the view `label` (a `siglip2` bundle, or the
    `group_embedding` of a `cascade` pipeline). Before, it answered HTTP 200 with
    `match: null` for each bottle. Each matcher has the new property `can_match_group`.
    The OpenAPI text of the HTTP 503 of the endpoint names the view.
  - With `packages_first: true`, the whole-photo ranking stays until the package is final.
    Before, the provisional crop cancelled it. A full SAM3 answer with no package then
    gave `{"slug": ""}` with no error. `config.yaml` has `packages_first: false`, so prod
    had no effect.
  - The bottle limit and the media limit of `POST /v1/group/match` keep the bottles with
    the highest `segmentation_score`. Before, the row filter gave row order, so a limit
    could drop a better bottle of a lower row. The response order does not change.
  - A card field of a wrong type in `wines.jsonl` stops the load with `BundleError`
    (item 7 of `docs/reports/2026-09-29_code-review.md`). Before, `WineCard` failed with
    HTTP 500 in each answer that held the wine. The local bundle
    `gx10-siglip2-so400m-patch16-naflex-p512` passes (2,094 cards).
  - Ruff passes: two unused imports went out of `audit.py` and `cascade_run.py`, one out
    of `tests/test_cascade.py`, and `labels.py` uses a function instead of a lambda.
  - `<workspace>/deploy/gx10/matcher-prod.md` names the image health check `GET /readyz`,
    as the Dockerfile does since `babef66`.
  - Five new tests. All 213 matcher tests pass, and
    `workbench/tests/test_matcher_parity.py` passes (10 tests).
- Added `eval/` in the svoe-vino-lab root: the organizers' evaluation set of 2026-09-17
  (`participant_test.sh`, `queries.tsv`, three photos in `queries/`, `checksums.sha256`),
  copied from `svoe-wino-hackaton/dataset/official-2026-09-17/eval/`. The organizers'
  `README.md` text stays verbatim. A new section describes the matcher start and the
  organizers' command with port `8158` instead of `8080`. The `README.md` line of
  `checksums.sha256` fails because of this section; the other five lines pass.
  `eval/.gitignore` holds `predictions.jsonl`. The root `README.md` links `eval/README.md`.
  A local run with `siglip2-p512-as-is` returned a slug for 3 of 3 photos. The details
  are in `ResearchLog.md`.
- Measured the backend `cascade` on the gx10 dev matcher (revision `f199e4d`; workbench
  plan 85, step 7; owner answers of 16:34:14 and 17:29:58). `official-real-photos`: R@1
  90.0 % at the cut 2.9 s and at 2.8 s, all answers within 3 s; `packages_first: true`
  gave 88.3 %, so the default stays `false`. `my`: R@1 83.3 % (83.42 % on the 1,647
  positives of the lab runs, against 74.26 % for `siglip2-p512-as-is`). A cut VLM call
  leaves vLLM within 0.2 s. `docs/cascade.md` now states the model lifetimes of the gx10
  gateway: `qwen3.5-9b-nvfp4` is pinned since 2026-09-29 16:03 MSK. The details are in
  `ResearchLog.md`.
- Added the backend `cascade` (workbench plan 85; owner message of
  2026-09-29T11:47:49+0300 and the answers of 11:59:36 to 13:53:47). At the start, in
  parallel: the barcode scan of the full photo (`qr-scanner`, engine `zxing-cpp`), one
  SAM3 `/segment_multi` request with the package nouns, `hand`, and `label`, an optional
  packages-only SAM3 request, and SigLIP2 of the whole photo. Then the crop embedding of
  the selected package (`main_scene.rank_packages`, the refined mask box of the lab), the
  scans of the package crop and of its label crop, and the VLM cluster re-rank
  (`qwen3.5-9b-nvfp4`, the lab prompts and rules, window 10). The answer order: a unique
  code of the package or label, a unique code of the full photo, a shared GTIN, the
  re-ranked crop ranking, the crop ranking, the whole ranking. New modules `cascade.py`,
  `cascade_run.py`, `services.py`, `photo.py`, `codes.py`, `labels.py`, `rerank.py`, and
  `docs/cascade.md`.
- Added `matcher.fast_answer` for `POST /v1/eval/predict` with a `cascade` pipeline. The
  protection middleware notes the request start when uvicorn parsed the headers. At
  `answer_at_seconds` (default 2.9 s) the matcher answers when an answer exists and
  cancels the pending model calls; the HTTP client closes their connections. At
  `timeout_seconds` (default 9.5 s) with no answer it answers `{"slug": ""}`.
  `POST /v1/match` runs the same stages with no budget; its scores never increase.
- `POST /v1/group/match` of a `cascade` pipeline uses the SigLIP2 group ranking of
  `group_embedding`: the rot5 index has no view `label`.
- `catalog.load_codes` reads `wine_code` and `wine_catalog` of the catalogue copy (owner
  decision of 12:18:09: no new view). `siglip2.py` gives `model_png`, `request_body`, and
  `parse_vectors`; `model_input` gives the same bytes as before. The audit record gets
  `decision` and `stages`; the log line gets the decision source, reason, and time.
- Added `httpx==0.28.1` (and `httpcore`, `certifi` in the lock) for the async clients.
- New tests `test_cascade.py` (27), `test_cascade_api.py` (13), `test_codes.py` (13),
  `test_labels.py` (14), `test_rerank.py` (10), with the fakes of `cascade_fakes.py`, and
  `workbench/tests/test_matcher_parity.py` (10). All 208 matcher tests pass.
  `matcher/config.yaml` holds the entry `cascade-p512-rot5`; the default selection stays
  `siglip2-p512-as-is`.
- Fixed the SAM3 request of the hand selection (`hand_selection: true`; workbench plan
  85, step 2; owner answer of 2026-09-29T12:18:09+0300). The selector sent its five
  nouns in one field `text` to `/segment`. That route takes one noun and gives no
  `label`, so each detection gave HTTP 502. The selector now sends the nouns in the
  field `texts` to `/segment_multi`, as the group path does. `_request_sam3` takes the
  nouns of its caller; `_validate_sam3` requires that each instance carries one of them
  and checks `area`. `/segment` has no caller now. The fake SAM3 of the tests records
  the route, and a new test checks the route and the field. The tests had asserted the
  old field. 131 matcher tests pass.
- Merged the branch `codex/group-quality-filter` (`be84a94`, the prod shelf filter, and
  `c88464f`, the two-view acceptance gate) into `main` (workbench plan 85, step 1; owner
  answers of 2026-09-29T12:28:19+0300 and 13:33:22). The gate takes the query `k` of
  plan 83: each bottle gets up to `k` gated `candidates`, at most 5 (the gate compares
  the top 5 of the views `full` and `label`), and `match` is the first candidate or null.
  `_request_sam3` keeps both calls: the group nouns go to `/segment_multi`; a `text`
  prompt (hand selection) still goes to `/segment`.

- `POST /v1/group/match` accepts the optional query parameter `k` (1 to 20, default 1),
  the maximum number of candidates for each bottle (workbench plan 83, owner message of
  2026-09-29T11:57:03+0300). Each bottle has the new field `candidates`: up to `k`
  `MatchCandidate` objects, the best first; the first equals `match`, and the list is
  empty when `match` is null. `match` does not change, so a client that reads only
  `match` does not change; the portal validator ignores the new field. `openapi.yaml`,
  `README.md`, and `docs/group-match.md` state the parameter and the field. New test
  `test_group_endpoint_returns_k_candidates_for_each_bottle` in `tests/test_group.py`
  (k=3, k=20 gives the 5 wines of the test bundle, k=0/21/x give HTTP 422). 125 tests pass.
  Prod gets the change only with a redeploy.

- Workbench plan 82 (max-over-rotation matching): `load_bundle` accepts bundle format
  version 3 (one vector row for each angle of an image) and keeps the angle of each row in
  the new optional field `Bundle.angles` (None for versions 1 and 2). `load_catalog` reads
  a catalogue index whose records hold `angles`: each record gives one row for each angle
  to each owner wine, and the rows MUST cover the vector file one time. The ranking does
  not change: a wine scores the best cosine of its rows, which is the maximum over the
  rotation. The API answer does not change. New tests `tests/test_rotation.py` (6); the
  "unsupported" example of `test_siglip2.py` is version 4 now. 124 tests pass.

- Fixed HTTP 500 for a damaged JPEG, MPO, or WEBP. The admission check reads only the
  image header, so such a file can pass it. `model_input` now raises `ImageRejected`
  with HTTP 422 when the decoding fails. `POST /v1/eval/predict` and `POST /v1/match`
  answer HTTP 422 `image file is invalid or damaged`, as `README.md` documents. The
  audit record gets status 422 and `error_type` `ImageRejected`. SigLIP2 gets no request.
  In a fuzz run, 683 damaged files passed the admission check. Their decoding raised
  only `OSError`.
- Removed the per-request warnings filter from `validate_image`. The function runs in
  worker threads, and `warnings.catch_warnings()` changed the filter list of the whole
  process. Parallel requests could leave the filter installed. The explicit pixel check
  stays the size limit. A header above the Pillow warning limit still gets HTTP 413.
- The service now refuses to start when `SVOE_VINO_MATCHER_MAX_IMAGE_PIXELS` exceeds the
  Pillow limit 89478485. Before this change, a larger value had no effect: each image
  above the Pillow limit got HTTP 413.
- Recorded the stalled-upload slot defect in `docs/KNOWN_ISSUES.md` for a later fix.
  Recorded the HTTP 400 of hand selection for a damaged image there too. Added the code
  review report `docs/reports/2026-09-29_code-review.md`.
- Validation: all 118 matcher tests passed with `ResourceWarning` treated as an error.
  The new thread test failed before the fix. In a scratch copy, the new API test got
  HTTP 500 when either hunk of the damaged-image fix was reverted.
- Split process liveness (`GET /healthz`) from pipeline readiness (`GET /readyz`).
- Made readiness conditional on the selected configuration. Mock does not use an
  external service. SigLIP2 sends a small embedding probe. Enabled hand selection
  also checks SAM3.
- Changed Docker `HEALTHCHECK` to use `/readyz`. A required model outage now makes
  the container unhealthy while `/healthz` stays available.
- Added OpenAPI, unit, API, smoke, and documentation coverage for readiness.
- Validation: all 113 matcher tests passed with no skips and with `ResourceWarning`
  treated as an error.
- Pinned the `python:3.11-slim` Docker base image to its OCI digest.
- Added `requirements.lock` with the full Python 3.11 Linux dependency graph and
  distribution hashes. Docker and `matcher/tests/run_ci.sh` install it with
  `--require-hashes`.
- Mapped SigLIP2 service failures and invalid responses to HTTP 502.
- Mapped SigLIP2 request timeouts to HTTP 504.
- Added OpenAPI, audit, unit, API, smoke, and documentation coverage for these errors.
- Validation: all 105 matcher tests passed with no skips. The generated lock file was
  identical in an offline regeneration. The remote Docker build and `pip check` passed.
- Added optional `pipeline[].hand_selection` for SigLIP2. The default is `false`.
  Both single-image endpoints can select a package with SAM3 package and hand
  detections. The selector uses the workbench version 1 scene weights and a masked
  crop with a white background. Hand contact is a box-overlap heuristic.
- Kept hand selection out of `match_many` and `POST /v1/group/match`. A local API
  test with the option enabled confirms one `wine bottle` segmentation request and
  one embedding input for each retained bottle.
- Added strict option validation, single-image SAM3 error status codes, OpenAPI
  entries, behavior documentation, and 21 regression tests.
- Validation: all 102 matcher tests passed with `ResourceWarning` treated as an
  error. The tests used local fake services. No live GPU or production service was
  called or restarted for this change.
- Ran a bounded production stress test for valid WebP, invalid data, the 40-million-pixel limit, and request waves through 32 concurrent clients. Recorded the result in `docs/reports/2026-09-29_production-stress-test.md`.
- Renamed two WebP test fixtures from `.jpg` to `.webp` and updated all matcher references.
- Added group-only bottle and label view ranking.
- Added a conservative group acceptance gate based on two-view agreement, score, and margin.
- Changed uncertain group results from forced Top-1 matches to `match: null`.
- Added matched and unmatched counts to the internal request audit.
- Added group-only visible-label and relative-size quality filters.
- Changed the group SAM3 request to one `segment_multi` call for `wine bottle` and `wine label`.
- Masked background pixels in group matcher crops.
- Kept `POST /v1/eval/predict` and `POST /v1/match` unchanged.
- Split large SigLIP2 embedding batches into requests of at most 64 images.
- Fixed shelf matching when SAM3 returns more than 64 bottle crops.
- Accepted MPO uploads as JPEG-family images. Single-image and group matching process
  frame 0 explicitly. The request audit keeps the source format `MPO`.
- Added MPO admission and frame-selection regression tests. All 108 matcher tests pass.
- Reran the unchanged official harness for 1,223 prior R@1 photos. All 1,223 output
  rows passed the contract and returned the expected slug.

## 2026-09-28

- Added `POST /v1/group/match` for shelf photos.
- Added SAM3 bottle segmentation through canonical `SAM3_ENDPOINT`.
- Added normalized coordinates, cropped transparent masks, normalized previews, and best wine cards to the group response.
- Added one-request batch embedding for multiple SigLIP2 bottle crops.
- Added response limits, duplicate suppression, retry behavior, audit metadata, authorization, and OpenAPI coverage.
- Added unit and integration tests for the group endpoint.
