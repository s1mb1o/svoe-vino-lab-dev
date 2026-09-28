# Shelf photo mode

Date: 2026-09-28. Status: implemented.
Authority: the user requested support for matcher `POST /v1/group/match` in the existing «Вся полка» tab.

## Availability

Keep «Одна бутылка» as the default mode.
Keep «Вся полка» selectable.
Enable `ShelfScanner` when `NUXT_PREDICTION_MODE=upstream` and `NUXT_PREDICTION_ENDPOINT` is a valid `/v1/eval/predict` URL.
Derive the matcher group URL by replacing the final `/v1/eval/predict` path with `/v1/group/match`.
Do not add a separate group endpoint variable.
Show `ShelfUnavailable` when the matcher configuration is absent or invalid.

## Experience

Preserve the existing visual identity, mobile layout, and single-bottle behavior.
A mode change MUST discard the previous mode photo, result, and pending request.
The shelf mode accepts a camera photo, one file, or the public example photo.
Use the existing JPEG, PNG, WebP, and 10 MiB upload limits.
Automatically submit a valid photo to `POST /v1/group/match` on the portal origin.
Show progress, cancellation, retry, replacement, and an explicit empty result.
Show the returned bottle masks and numbered hit areas on the returned preview.
Use normalized coordinates so each hit area tracks the responsive image size.
Provide numbered keyboard-accessible controls for small or overlapping bottles.

The group request MUST identify all detected bottles in one operation.
Selecting a bottle MUST NOT send another recognition request.
Selecting a bottle MUST open its ready matcher result in a modal.
Show the wine title, producer, region, type, matcher score, image, and source portal link when available.
Show an explicit unmatched state when `match` is `null`.
Reuse the local result experiences when the matcher returns wine metadata.
Close the modal on Escape, a close button, or a backdrop click.
Restore focus to the selection control.
Use a bottom sheet on phones and a centered dialog on desktop.

## Service boundary

The browser MUST call the same-origin portal route `POST /v1/group/match`.
The browser MUST NOT receive a private matcher address.
The Nuxt route MUST proxy one multipart file field named `image` to the derived matcher URL.
The matcher owns segmentation and wine matching, including any SAM3 calls.
The Web UI MUST NOT call SAM3 directly.
The route MUST reject redirects.
The route MUST allow a 330-second matcher budget.
The route MUST reject responses larger than 12 MiB.
The route MUST validate the complete matcher response before it returns data to the browser.
The route MUST use `Cache-Control: no-store`.
The route MUST cancel upstream work when the browser disconnects.
The Web UI MUST NOT write the upload, preview, masks, or matcher response to disk.
The matcher can archive the original group photo under its own service policy.
The UI MUST NOT claim that the original photo is never stored.

## Response contract

The success response contains `pipeline`, `latency_ms`, `image`, `detected_count`, `truncated`, and `bottles`.
`image` contains `width`, `height`, and a JPEG `preview` data URL.
Each bottle contains a response-local `id`, `segmentation_score`, normalized `box`, PNG `mask` data URL, and nullable `match`.
Each match contains `rank`, `slug`, `score`, and `wine`.
The wine card contains `name`, `page_url`, nullable descriptive fields, and `qr_urls`.

Example:

```json
{
  "pipeline": "sam3+matcher",
  "latency_ms": 842.4,
  "image": {
    "width": 1280,
    "height": 853,
    "preview": "data:image/jpeg;base64,..."
  },
  "detected_count": 2,
  "truncated": false,
  "bottles": [
    {
      "id": "b1",
      "segmentation_score": 0.93,
      "box": [0.10, 0.05, 0.40, 0.95],
      "mask": "data:image/png;base64,...",
      "match": {
        "rank": 1,
        "slug": "priboj-marchenko-beloe-polusuhoe",
        "score": 0.89,
        "wine": {
          "name": "Прибой Марченко белое полусухое",
          "page_url": "https://vino-svoe.ru/wines/priboj-marchenko-beloe-polusuhoe",
          "producer": "Винодельня Марченко",
          "category": "Вино",
          "region": "Кубань",
          "color": "Белое",
          "grapes": "Первенец Магарача",
          "sugar": "Полусухое",
          "image_url": null,
          "qr_urls": []
        }
      }
    }
  ]
}
```

An empty `bottles` array is valid.
`detected_count` MUST be greater than or equal to the number of returned bottles.
The client MUST reject malformed coordinates, scores, data URLs, duplicate IDs, or incomplete wine cards.
The server MUST preserve actionable matcher status codes for invalid uploads, unavailability, and timeout.
The server MUST map malformed matcher output and unexpected statuses to HTTP 502.

## Verification

- The browser sends one group request for one shelf photo.
- Selecting any returned bottle sends no additional request.
- Matched and unmatched bottles have explicit modal states.
- Masks and hit areas use the matcher coordinates.
- Replacement, cancellation, reset, empty results, invalid output, and stale responses have automated checks.
- URL derivation, upstream status handling, response limits, and timeout have automated checks.
- Single-bottle mode and the official evaluator contract remain unchanged.
- Test fixtures do not use private user photos or user location.

## Limits

The matcher can miss occluded or small bottles.
The matcher can return `match: null` for a detected bottle.
The user can submit a closer photo when the result is incomplete.
A native camera and physical touch interaction need device verification.
