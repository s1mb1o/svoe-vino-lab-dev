# Group match API

Date: 2026-09-28.
Status: implemented.

## Purpose

`POST /v1/group/match` accepts one shelf photo.
The endpoint segments wine bottles in the photo.
The endpoint matches each returned bottle against the configured catalogue bundle.
The endpoint returns data that a later UI can place over the normalized photo.

## Request

The request MUST use `multipart/form-data`.
The image MUST be in the `image` field.
The endpoint uses the existing upload size, pixel, format, authorization, and queue limits.
The selected matcher pipeline MUST contain wine cards.
A pipeline of the backend `siglip2` or `cascade` MUST also hold vectors of the view `label`.
The query parameter `k` MAY set the maximum number of candidates for each bottle.
The range of `k` is 1 to 20. The default is 1. A value out of the range gives HTTP 422.

The matcher MUST read the SAM3 base URL from `SAM3_ENDPOINT`.
The matcher MUST send the normalized image to `${SAM3_ENDPOINT}/segment_multi`.
The request MUST use `texts=wine bottle, wine label`.
The request MUST use `threshold=0.4`.
The request MUST use `mask_threshold=0.5`.
The request MUST use `return_masks=true`.

## Image processing

The matcher MUST apply EXIF orientation.
The matcher MUST flatten transparency on white.
The matcher MUST resize the image inside 1600 by 1600 pixels without enlargement.
The matcher MUST encode the normalized image as JPEG without source metadata.

The matcher MUST validate the SAM3 dimensions, count, scores, boxes, and masks.
Each SAM3 mask MUST be a full-frame PNG.
The matcher MUST clamp each detector box to the normalized image.
The matcher MUST discard mask pixels outside the detector box.
The matcher MUST suppress a duplicate box when its intersection-over-union is at least 0.9.
The matcher MUST return a bottle only when a usable `wine label` mask is inside the bottle mask.
A usable label MUST have a short side of at least 2.5 percent of the image short side.
A usable label mask MUST cover at least 0.06 percent of the image area.
At least 80 percent of a usable label mask MUST be inside the bottle mask.
The label center MUST be between 20 and 90 percent of the bottle height.
The matcher MUST discard a bottle fragment that starts in the bottom 15 percent of the image.
The matcher MUST group bottles by their top coordinate.
The matcher MUST discard a bottle whose height is less than 65 percent of the median height in its group.
The matcher MUST keep at most 100 bottles.

The matcher MUST crop each bottle from the normalized photo.
The matcher MUST replace pixels outside the bottle mask with white pixels.
The matcher MUST add padding equal to five percent of the bottle width to each crop side.
The matcher MUST resize each internal crop inside 640 by 960 pixels without enlargement.
The matcher MUST also make a masked crop of the selected visible label.
The label crop MUST have eight percent horizontal padding.
The label crop MUST fit inside 640 by 640 pixels without enlargement.
The SigLIP2 backend MUST embed the bottle and label crops in one logical batch.

## Group recognition

Group recognition MUST rank the bottle crop against the bundle view `full`.
It MUST rank the label crop against the bundle view `label`.
It MUST consider the first five candidates of each view.
A candidate MUST occur in both lists.
The group score MUST be 60 percent of the full-view score plus 40 percent of the label-view score.
The candidate MUST be first in one view and in the first three candidates of the other view.
The group score MUST be at least 0.75.
The full-view score MUST be at least 0.78.
The label-view score MUST be at least 0.75.
The score margin over the next common candidate MUST be at least 0.015.
A full-view score of at least 0.925 and a label-view score of at least 0.84 MAY replace the margin rule.
The matcher MUST return `match: null` when these rules do not accept a candidate.
These rules MUST NOT change `POST /v1/eval/predict` or `POST /v1/match`.

## Response

The response MUST contain `pipeline`, `latency_ms`, `image`, `detected_count`, `truncated`, and `bottles`.
`image` MUST contain `width`, `height`, and `preview`.
`preview` MUST be a JPEG data URL of the normalized image.

Each bottle MUST contain `id`, `segmentation_score`, `box`, `mask`, `match`, and `candidates`.
`id` MUST be stable inside one response.
`box` MUST use `[left, top, right, bottom]` coordinates normalized to the returned image.
`mask` MUST be a cropped transparent PNG data URL.
The mask dimensions MUST match the pixel box dimensions.
`match` MUST contain the accepted `MatchCandidate` or `null` when the group recognition rules reject the candidates.
`candidates` MUST contain up to `k` accepted `MatchCandidate` objects, the best first. It holds at most 5 candidates: the rules compare the first 5 candidates of the views `full` and `label`.
The first candidate MUST equal `match`. The list MUST be empty when `match` is `null`.
Each candidate MUST contain the existing `WineCard` description.
The field `candidates` was added on 2026-09-29 (workbench plan 83). A client that reads only `match` does not change.

The response MUST order bottles by shelf band and then from left to right.
The response MUST keep at most 6 MiB of preview and mask data.
`detected_count` MUST contain the number of valid `wine bottle` SAM3 detections before quality filters, duplicate suppression, and response limits.
`truncated` MUST be true when a bottle limit or response media limit excludes a valid non-duplicate bottle.
When a limit excludes bottles, the matcher MUST keep the bottles with the highest `segmentation_score`.

## Errors

The endpoint MUST return HTTP 503 when `SAM3_ENDPOINT` is absent or invalid.
The endpoint MUST return HTTP 503 before the SAM3 request when the selected pipeline has no vectors of the view `label`.
The endpoint MUST return HTTP 502 for an invalid or failed SAM3 response.
The endpoint MUST return HTTP 504 when the 300-second SAM3 budget expires.
The endpoint MUST retry SAM3 once after a 5xx response, an empty response, or a transient transport failure.
The retry MUST stay inside the same 300-second budget.
The endpoint MUST reject redirects and a SAM3 response larger than 16 MiB.

The endpoint MUST NOT replace a SAM3 failure with fake segments.
The endpoint MUST NOT store masks or bottle crops.

## Verification

Automated tests MUST cover image normalization, box clamping, mask cropping, visible-label filtering, relative-size filtering, label crops, two-view ranking, uncertain-match rejection, duplicate suppression, ordering, limits, SAM3 validation, SAM3 retry, batch matching, the parameter `k`, authorization, and the OpenAPI contract.
The existing `/v1/eval/predict` and `/v1/match` contracts MUST remain unchanged.
