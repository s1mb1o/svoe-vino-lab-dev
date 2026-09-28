# API contract

## Authority

Source: `../../svoe-wino-hackaton/dataset/official-2026-09-17/eval/participant_test.sh`.
Checked: 2026-09-28.

## Prediction

`POST /v1/eval/predict`

Send `multipart/form-data` with one file field named `image`.
Let the HTTP client set the multipart boundary.
Do not send a query ID or a hash field.

Successful response:

```json
{"slug":"priboj-marchenko-beloe-polusuhoe"}
```

The evaluator accepts HTTP 200 or 201.
The evaluator accepts a nonempty string in `slug`.
The evaluator also accepts the first object in a nonempty array.
The portal returns the object form.
The evaluator uses a 5-second connection timeout and a 10-second total timeout.
The evaluator does not retry requests or follow redirects.

The portal accepts JPEG, PNG, and WebP signatures.
The portal limits the image file to 10 MiB.
These validation limits are portal choices. The evaluator does not specify them.
The portal returns HTTP 400 for missing or multiple files.
The portal returns HTTP 413 for an oversized body or image.
The portal returns HTTP 415 for an unsupported image.
The portal returns HTTP 502 for upstream failure or invalid prediction output.
The portal returns HTTP 504 for upstream timeout.
Error bodies contain a readable `statusMessage`.

## Providers

`NUXT_PREDICTION_MODE=mock` is the default.
Mock mode returns a fixed demo slug for every valid image.
The response header `X-Prediction-Mode: mock` identifies mock output.

Set `NUXT_PREDICTION_MODE=upstream` to enable real prediction.
Set `NUXT_PREDICTION_ENDPOINT` to the complete prediction URL.
The proxy sends one `image` file to this URL.
The proxy allows HTTP 200 or 201 and validates `slug`.
The proxy uses an 8-second upstream timeout.
The proxy rejects redirects and does not substitute mock output for errors.

## Portal routes

- `GET /api/config`: return prediction mode, upload limit, catalog mode, and `shelfAvailable`.
- `GET /api/wines`: return demo wine records.
- `GET /api/wines/<slug>`: return one exact catalog match or HTTP 404.
- `GET /api/health`: return basic service status.

Catalog routes are portal-specific. They are not part of the evaluator contract.
The first release keeps catalog mode as `demo`, even when prediction mode is `upstream`.

## Photo search page

The browser automatically submits a valid selected image.
The app preserves the returned slug before fetching `/api/wines/<slug>`.
Metadata lookup has a separate 4-second timeout.
Metadata failure does not remove a successful prediction or its source link.
The source link always uses `https://vino-svoe.ru/wines/<encoded-slug>`.
The app does not provide a catalog browsing interface.

## Food recommendations

The separate [food API](food-api.md) provides live Globus store and product queries.
It does not change the evaluator prediction contract.

## Shelf segmentation

`POST /api/shelf/segment` accepts one multipart `image` with the existing upload limits.
The server calls `${SAM3_ENDPOINT}/segment`. The browser does not receive this address.
Read [the shelf contract](shelf-mode.md) for image normalization, response fields, and limits.
Successful output contains `image`, `bottles`, `detectedCount`, and `truncated`.
An empty `bottles` array is a valid result. It does not trigger mock segmentation.
The route returns 400 for an undecodable image, 503 for missing configuration, 502 for invalid service output, and 504 for timeout.
Responses use `Cache-Control: no-store`.
Wine recognition uses a selected bottle crop through the unchanged evaluator route.
