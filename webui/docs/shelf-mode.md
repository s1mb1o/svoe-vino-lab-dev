# Shelf photo mode

Date: 2026-09-15. Status: implemented but temporarily disabled.
Authority: the user requested a second mode for shelf photos with segmented bottles and clickable wine popups.

## Temporary availability

Decision date: 2026-09-28.
The owner selected a temporary-unavailable view for «Вся полка».
The switch MUST remain selectable.
The view MUST show that processing is temporarily unavailable.
The view MUST NOT show a file input or a camera input.
The browser MUST NOT call the shelf API from this view.
The server MUST reject the shelf API before it reads an upload or calls SAM3 when `NUXT_SHELF_MODE` is not `enabled`.
The Princess deployment MUST set `NUXT_SHELF_MODE=disabled` and MUST omit `SAM3_ENDPOINT`.

## Experience

The requirements in this section apply when shelf processing is enabled.
Keep «Одна бутылка» as the default mode. Add «Вся полка» beside it.
Preserve the existing visual identity, mobile layout, and single-bottle behavior.
A mode change MUST discard the previous mode's transient photo state and requests.
The shelf mode accepts a camera photo, a file, or one public example photo.
Use the existing JPEG, PNG, WebP, and 10 MiB limits.
Automatically submit a valid photo to our portal API.
Show progress, cancellation, retry, replacement, and an explicit empty result.
Show bottle masks and numbered hit areas on the normalized shelf photo.
Use normalized coordinates so the hit areas track responsive image size.
Provide numbered keyboard-accessible controls for small or overlapping bottles.

Selecting a bottle MUST open a modal wine popup immediately.
The popup MUST recognize only the selected crop through the existing prediction contract.
Show loading, the wine title and bottle image, its source portal link, or an explicit error.
Preserve the slug and link when wine metadata is missing.
Keep recognition mock disclosure separate from real segmentation.
Do not claim a successful wine identity from segmentation alone.
Reuse food recommendations for a selected wine with metadata.
Close on Escape, a close button, or a backdrop click. Restore focus to the selection control.
Use a bottom sheet on phones and a centered dialog on desktop.

## Service boundary

The browser MUST call our portal API. It MUST NOT call SAM3 directly.
`POST /api/shelf/segment` accepts one multipart `image`.
The server MUST decode the image, apply EXIF orientation, and remove metadata.
Limit decoded input to 40 megapixels. Resize inside 1600 by 1600 pixels.
Send the normalized JPEG to `${SAM3_ENDPOINT}/segment`.
Use `text=wine bottle`, `threshold=0.4`, `mask_threshold=0.5`, and `return_masks=true`.
Read the base URL only from canonical `SAM3_ENDPOINT`.
The configured GX10 URL is `http://192.168.86.14:18081/upstream/sam3`.
Keep service addresses private to the server.
Allow a 300-second total service budget because the gateway can load the model on demand.
Retry once on a 5xx, empty body, or transient transport reset or timeout within that same budget.
Never retry invalid output, permanent address errors, or an aborted request.
Reject redirects and responses larger than 16 MiB.
Validate dimensions, scores, boxes, and full-frame PNG masks.
Keep at most 100 non-duplicate bottles. Report truncation explicitly.

The portal response contains `image`, `bottles`, `detectedCount`, and `truncated`.
`image` contains normalized `width`, `height`, and a JPEG data URL.
Each bottle contains a stable response-local `id`, normalized `box`, a mask PNG data URL, and a JPEG crop data URL.
Masks MUST use transparent backgrounds for browser overlays.
Crop each overlay to its normalized box. Do not return full-frame masks to the browser.
Clamp detector boxes to the image. Ignore mask fragments outside each detector box.
Crop the normalized image on the server. Include the whole detected bottle.
Recognition starts only when the user selects a bottle.
Submit its server-produced crop as multipart `image` to `POST /v1/eval/predict`.
Keep the existing `slug` response unchanged.
Do not store user photos, crops, masks, or service responses on disk.
Use `Cache-Control: no-store`. Cancel upstream work when the client disconnects.
Do not substitute fake segments after a service error.

## Verification

- Single-bottle mode and the unchanged evaluator remain functional.
- A public shelf example returns several real masks through our portal.
- EXIF rotation, mask dimensions, normalized boxes, duplicate suppression, limits, and invalid service output have checks.
- Selection, replacement, cancellation, empty results, and popup state have checks.
- Recognition is deferred until a bottle selection.
- Late results cannot change a newer photo or popup.
- Test fixtures do not use private user photos or user location.

## Limits

SAM3 segments a visual concept. It does not identify a wine SKU.
Mock prediction returns the existing fixed demo slug for each selected crop.
A configured recognition endpoint is necessary for actual wine identity.
The service can miss occluded or small bottles. The interface must permit a closer new photo.
A native camera and physical touch interaction need device verification.
