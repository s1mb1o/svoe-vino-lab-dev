# Change log

## 2026-09-29

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
