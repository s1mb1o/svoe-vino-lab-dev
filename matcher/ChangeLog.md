# Change log

## 2026-09-29

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
