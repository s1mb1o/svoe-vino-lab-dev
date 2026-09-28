# Project context

Read the workspace `CLAUDE.md` first.
Write technical documents in STE-style English. Keep Russian UI labels unchanged.

## Product

This project is the web portal for the wine scanner task.
Use the visual identity of `https://vino-svoe.ru/`.
The primary page is «Найти вино по фото». Do not restore the catalog UX.
Automatically submit a valid selected image. Link the single result to the source portal.
Use `docs/specification.md` and `docs/api.md` as the implementation scope.
Do not copy tracking scripts or source application bundles.
Keep asset provenance in `docs/assets.md`.

## API

The evaluator sends one multipart file under `image`.
The success response contains `slug`. Do not replace this key with `wine_slug`.
Use mock prediction until a real endpoint is configured.
Never substitute mock output for an upstream error.

## Changes

Keep the Web UI code isolated in this directory.
Do not edit other `svoe-vino-lab` components for a Web UI task.
Update `ChangeLog.md`, `ResearchLog.md`, and `SMOKE_TESTS.md` when results change.
Do not commit secrets, uploads, dependency folders, or generated output.

## Result experiences

Read `docs/result-experiences.md`.
The rendered product action is a local demonstration.
It MUST NOT request real location or call a retailer API.
The existing Globus integration is retained as inactive reference code.
Do not render `FoodRecommendations` while the local demonstration is active.

## Shelf segmentation

Keep «Одна бутылка» as the default. Use «Вся полка» for multi-bottle photos.
Read `docs/shelf-mode.md` for the contract and limits.
The browser MUST call the same-origin `POST /v1/group/match` route.
Derive the upstream group URL from `NUXT_PREDICTION_ENDPOINT`.
Do not add a separate group endpoint variable.
Only the matcher may call SAM3.
Keep photos, masks, and responses out of Web UI disk storage and logs.
The matcher can archive the original group photo. Do not claim that it is never stored.
Use the matches returned by the group request. Do not recognize a selected bottle again.
Preserve the evaluator contract for single-bottle prediction.
