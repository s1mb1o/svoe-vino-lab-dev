# API contract

## Authority

Source: `../../svoe-wino-hackaton/dataset/official-2026-09-17/eval/participant_test.sh`.
Checked: 2026-09-28.

## Prediction

`POST /v1/eval/predict`

The official evaluator uses this route.
The browser uses the equivalent portal route `POST /api/predict`.
Both routes share upload validation, forwarding and the response contract.
Their time budgets differ: the interactive portal allows a slow original-photo upload.

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
When the matcher rejects a low-score input, the portal preserves HTTP 200 with
`{"slug":""}`. This is a normal no-match result. The browser displays a retry prompt,
keeps the photo, and does not fetch wine metadata or write diary history.
The floor is configured by `matcher.min_score` in the matcher YAML (default `0.7`).
Missing, null, whitespace-only, and malformed slug values remain upstream errors.
The evaluator uses a 5-second connection timeout and a 10-second total timeout.
The evaluator does not retry requests or follow redirects.

The portal accepts JPEG, PNG, WebP, and HEIF (HEIC) signatures.
The production matcher decodes HEIF since 2026-10-18 (#24).
A matcher without HEIF support answers HTTP 422 for a HEIF file. The portal passes that status.
The portal limits the image file to 10 MiB.
These validation limits are portal choices. The evaluator does not specify them.
The portal returns HTTP 400 for missing or multiple files.
The portal returns HTTP 413 for an oversized body or image.
The portal returns HTTP 415 for an unsupported image.
The portal passes HTTP 422 from the matcher when the matcher cannot decode the image.
A matcher without HEIF support (#24) answers HTTP 422 for a HEIC photo.
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
The evaluator route uses an 8-second upstream timeout.
The interactive `/api/predict` route allows 30 seconds for the upstream request.
This upstream budget starts after the complete client upload has been read.
The proxy rejects redirects and does not substitute mock output for errors.

In upstream mode, `GET /api/config` derives the matcher readiness URL from `NUXT_PREDICTION_ENDPOINT`.
It replaces the final `/v1/eval/predict` path with `/healthz`.
The server sends `GET` to the readiness URL with a 2-second timeout.
The matcher is available only when the response is HTTP 200 and contains `{"status":"ok"}`.
The browser does not receive the private matcher URL.
Mock mode does not send a matcher readiness request.
The `apiAvailable` field is `true` in mock mode or after a successful readiness request.
The `shelfAvailable` field is `false` when matcher readiness fails.

## Portal routes

- `GET /api/config`: return prediction mode, matcher availability, upload limit, catalog mode, and `shelfAvailable`.
- `GET /api/wines`: return demo wine records.
- `GET /api/wines/<slug>`: return one exact local or source catalog match, or HTTP 404.
- `GET /api/wines/<slug>/offline`: return one public card and its pinned catalog version for an explicit device copy.
- `GET /api/health`: return basic service status.

Catalog routes are portal-specific. They are not part of the evaluator contract.
The portal reports catalog mode `source-fallback`.
It checks the 12 local records first.
It requests an unknown valid slug from `https://api.vino-svoe.ru/v1/wines/<slug>`.
The request has a 2.5-second timeout, a bounded response, no redirects, and a fixed host.
The portal validates the returned slug and image path before it returns the normalized card.

## Photo search page

The browser automatically submits a valid selected image.
It sends the original file without resizing, recompressing, or changing its bytes.
Its prediction request has a 120-second total budget for upload and recognition.
This supports the 10 MiB limit on slower mobile connections while keeping a finite deadline.
Cancel, replacement and route disposal still abort pending work immediately.
The app preserves the returned slug before fetching `/api/wines/<slug>`.
Metadata lookup has a separate 4-second timeout.
Metadata failure does not remove a successful prediction or its source link.
The source link always uses `https://vino-svoe.ru/wines/<encoded-slug>`.
The app does not provide a catalog browsing interface.

## Food recommendations

The separate [food API](food-api.md) provides live Globus store and product queries.
It does not change the evaluator prediction contract.

## Shelf group match

`POST /v1/group/match` accepts one multipart `image` with the existing upload limits.
The browser calls this same-origin portal route.
The server derives the upstream group URL from `NUXT_PREDICTION_ENDPOINT`.
It replaces the final `/v1/eval/predict` path with `/v1/group/match`.
No separate group endpoint variable is required.
The route is available only in upstream prediction mode with a valid matcher URL.
Read [the shelf contract](shelf-mode.md) for the complete response contract and limits.
Successful output contains `pipeline`, `latency_ms`, `image`, `bottles`, `detected_count`, and `truncated`.
Each bottle contains normalized coordinates, a mask, and a nullable ready match.
An empty `bottles` array is a valid result.
Selecting a bottle does not send another prediction request.
The route returns 400 for an invalid upload, 503 for missing configuration, 502 for invalid matcher output, and 504 for timeout.
Responses use `Cache-Control: no-store`.

## Strict alternatives

`GET /api/recommendations/alternatives` accepts `slug` and optional `color`, `sweetness`, and `sparkle`.
`slug` is an exact Active ID of the pinned catalog.
`color` uses the Russian labels in `ALTERNATIVE_COLORS`.
`sweetness` uses the keys in `ALTERNATIVE_SUGAR`.
`sparkle` is `still` or `sparkling`.
Unknown query keys, repeated values, and unsupported filters return HTTP 400.
An absent exact ID returns HTTP 404.
Success returns `base`, up to five `results`, `version`, and `explanation`.
Each result contains a public card, supported `reasons`, and explicit `missing` facts.
Success uses `Cache-Control: no-store`.
Producer exclusion and explicit filters run before ranking.
An empty result keeps the constraints.
Sweetness comes from the checked-in source portal category snapshot, with explicit source-name fallback.
Missing source color or sweetness can be supplied with the corresponding filter; otherwise the response explains the missing fact.
Builds check that the alternatives snapshot matches the selected catalog and category provenance.
Read [the F04 contract](f04-result-journey.md) for comparison and offline storage.

## Public card for a device copy

`GET /api/wines/<slug>/offline` returns `wine` and `version` from the same pinned snapshot as F04 comparison.
The route returns HTTP 400 for an invalid ID and HTTP 404 for an ID outside the snapshot.
The response uses `Cache-Control: no-store` and contains only public card fields.
It contains no account data or uploaded image. The image field is empty for the public placeholder.
The client requests this card after an explicit successful diary save or an explicit copy action.
A lookup failure does not undo the server save. The client reports the missing device copy and offers retry.
The existing IndexedDB store validates and bounds the committed copy.


## Account taste data

These same-origin routes require the existing owner session cookie and return `Cache-Control: no-store`.
All writes check Origin. Application tokens cannot call them.

| Route | Behavior |
| --- | --- |
| `GET /api/account/preferences` | `{preferences: object or null}` |
| `PUT /api/account/preferences` | Replace schema-version-1 colors, sparkling, sweetness, body, freshness, and grapes. |
| `DELETE /api/account/preferences` | Reset to null. |
| `GET /api/account/ratings` | List all owner ratings and tasting notes, newest update first. |
| `PUT /api/account/ratings/{slug}` | Replace `{rating: integer 1–5, note: string or null}`. Note: at most 500 Unicode characters. |
| `DELETE /api/account/ratings/{slug}` | Remove one rating and tasting note. |

The public read-only `GET /api/app/v1/profile` returns stored preferences.
`GET /api/app/v1/wines?collection=history` (default) adds `rating`, `note`, and `rated_at`.
Use `collection=rated` to read all ratings, including wines removed from history. Keep the same collection
when following `next_cursor`; pages may be shorter than `limit` to stay below the response bound.
Saved-wine private notes remain excluded. Read [account.md](account.md#preferences-and-tasting-ratings-2026-10-20).
