# Censored administration preview

Date: 2026-09-26

## Goal

Show a strongly blurred preview for a quarantined request.
Do not send the quarantine source to the browser.

## Requirements

1. The bot MUST create the preview only after moderation reports an unsafe result.
2. The preview MUST be an irreversible server-side transformation.
3. The transformation MUST apply EXIF orientation.
4. The transformation MUST reduce the longest side to 24 pixels.
5. The transformation MUST enlarge the reduced image to a maximum longest side of 768 pixels.
6. The transformation MUST apply a Gaussian blur with a radius of 18 pixels.
7. The transformation MUST encode the result as JPEG.
8. The preview MUST use the `censored` exposure class.
9. The browser MUST NOT receive the quarantine source.
10. CSS blur MUST NOT be the only censorship control.
11. The administration service MUST serve a `censored` artifact only when the current request has `moderation_safe = 0`.
12. The administration service MUST serve a `safe` artifact only when the current request has `moderation_safe = 1`.
13. A preview generation failure MUST NOT change the quarantine result.
14. The reconstruction command MUST create a censored preview for a previously quarantined request.
15. The reconstruction command MUST NOT call Telegram.

## Data model

Add `exposure` to `request_artifacts`.
The allowed application values are `safe` and `censored`.
Existing artifact rows use `safe`.

## Processing flow

1. Moderate the normalized in-memory image.
2. Save the unsafe source under `quarantine`.
3. Create the censored preview from the normalized in-memory image.
4. Save the censored preview under `artifacts`.
5. Store one `request_artifacts` row with `exposure = 'censored'`.
6. Send the existing rejection response to Telegram.

## Administration flow

1. Load only artifacts that match the current moderation result.
2. Show the censored preview in a separate group.
3. Serve only the derived preview file.
4. Keep HTTP Basic authentication, LAN restrictions, and `Cache-Control: no-store`.

## Verification

1. Test the irreversible downsample and blur transformation.
2. Test the `safe` and `censored` exposure rules.
3. Test that a quarantine source path cannot use the artifact route.
4. Test that a preview failure does not stop the rejection response.
5. Reconstruct the requested quarantined request.
6. Inspect the page at desktop and mobile widths.

