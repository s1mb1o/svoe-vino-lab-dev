# Pipeline artifact inspector

Date: 2026-09-26

## Goal

Add a visual inspector to the administration request page.
The inspector shows the image artifacts that each recognition step used or produced.

## Requirements

1. The bot MUST persist artifacts only after moderation reports that the image is safe.
2. The bot MUST NOT copy a quarantine image into the artifact store.
3. The artifact set MUST include the exact matcher input.
4. The artifact set MUST include the normalized moderation image.
5. The SAM3 request MUST ask for masks.
6. The artifact set MUST include each accepted SAM3 mask.
7. The artifact set MUST include one overlay with masks, boxes, prompt labels, and scores.
8. The artifact set MUST include the selected bottle box crop and masked cutout.
9. The artifact set MUST include the selected label box crop and masked cutout.
10. The artifact set SHOULD include the final Telegram result image.
11. Artifact generation failures MUST NOT stop recognition.
12. The administration service MUST serve artifacts only when the current request has `moderation_safe = 1`.
13. The administration service MUST require its existing authentication and network checks for artifact routes.
14. The administration service MUST NOT serve accepted source files or quarantine files directly.
15. A processing retry MUST replace the artifact index for the request.
16. A reconstruction command MUST create artifacts only for a previously safe request.
17. A reconstruction command MUST NOT send a Telegram message.

## Data model

Add the `request_artifacts` table.
Each row identifies one artifact for one request.
Each row stores the step, title, description, MIME type, relative path, dimensions, display order, metadata, and creation time.
Use `(request_id, artifact_key)` as the primary key.

Store artifact files below `BOT_DATA_ROOT/artifacts`.
Use one dated request directory for each request.
Use atomic file replacement.

## Pipeline changes

1. Ask `/segment_multi` for `return_masks=true`.
2. Validate each returned mask as an image with the expected dimensions.
3. Keep the validated mask with its segment record.
4. Select the bottle and label with the existing quality rules.
5. Generate the visual artifacts from the normalized moderation image.
6. Store artifacts after safe moderation.
7. Store the final result image before Telegram delivery.
8. Log an artifact error without image bytes and continue the request.

## Administration changes

1. Load the ordered artifact list for the request detail page.
2. Group artifacts by pipeline step.
3. Show a thumbnail, title, description, dimensions, and metadata.
4. Link each thumbnail to the full artifact route.
5. Add `img-src 'self'` to the Content Security Policy.
6. Return `404` when an artifact is absent, unsafe, or outside the artifact root.

## Reconstruction

Add `chto-za-vino-artifacts REQUEST_ID`.
The command reads only a previously accepted source image.
The command recreates the moderation image and SAM3 artifacts.
The command does not call the matcher.
The command does not use Telegram.

## Verification

1. Test SAM3 mask decoding and dimension validation.
2. Test crop, cutout, overlay, and artifact storage generation.
3. Test artifact database ordering and replacement.
4. Test that the artifact route requires authentication.
5. Test that an unsafe request cannot serve an artifact.
6. Test that path traversal cannot leave the artifact root.
7. Test that artifact generation failure does not stop recognition.
8. Run the reconstruction command for the reported request.
9. Inspect the request page at desktop and mobile widths.

