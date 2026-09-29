# Change log

## 2026-09-29

- Added group-only visible-label and relative-size quality filters.
- Changed the group SAM3 request to one `segment_multi` call for `wine bottle` and `wine label`.
- Masked background pixels in group matcher crops.
- Kept `POST /v1/eval/predict` and `POST /v1/match` unchanged.
- Split large SigLIP2 embedding batches into requests of at most 64 images.
- Fixed shelf matching when SAM3 returns more than 64 bottle crops.

## 2026-09-28

- Added `POST /v1/group/match` for shelf photos.
- Added SAM3 bottle segmentation through canonical `SAM3_ENDPOINT`.
- Added normalized coordinates, cropped transparent masks, normalized previews, and best wine cards to the group response.
- Added one-request batch embedding for multiple SigLIP2 bottle crops.
- Added response limits, duplicate suppression, retry behavior, audit metadata, authorization, and OpenAPI coverage.
- Added unit and integration tests for the group endpoint.
