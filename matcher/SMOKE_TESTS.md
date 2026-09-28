# Matcher smoke tests

## Single image regression

- Send a known image to `POST /v1/eval/predict`.
- Confirm that the response contains the expected `slug`.
- Send the same image to `POST /v1/match`.
- Confirm that the response contains ranked candidates and wine cards.

## Group match

- Configure a version 2 matcher bundle.
- Set `SAM3_ENDPOINT` to the canonical SAM3 base URL.
- Send a shelf photo to `POST /v1/group/match`.
- Confirm that the response contains `image`, `detected_count`, `truncated`, and `bottles`.
- Confirm that each bottle has an `id`, `segmentation_score`, normalized `box`, transparent PNG `mask`, and best `match`.
- Render each mask inside its box over `image.preview`.
- Confirm that the mask follows the correct bottle.
- Confirm that each returned wine card links to its catalogue page.

## Group failures

- Remove `SAM3_ENDPOINT`.
- Confirm that `POST /v1/group/match` returns HTTP 503.
- Use an invalid bearer token.
- Confirm that the request returns HTTP 401 before SAM3 receives a request.
- Make SAM3 return invalid dimensions or a non-PNG mask.
- Confirm that the matcher returns HTTP 502 and does not return fake bottles.
