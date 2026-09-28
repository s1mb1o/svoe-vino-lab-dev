# Change log

## 2026-09-28

- Added `POST /v1/group/match` for shelf photos.
- Added SAM3 bottle segmentation through canonical `SAM3_ENDPOINT`.
- Added normalized coordinates, cropped transparent masks, normalized previews, and best wine cards to the group response.
- Added one-request batch embedding for multiple SigLIP2 bottle crops.
- Added response limits, duplicate suppression, retry behavior, audit metadata, authorization, and OpenAPI coverage.
- Added unit and integration tests for the group endpoint.
