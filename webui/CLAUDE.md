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

## Food recommendations

The Web UI MUST query our portal API. Our server-side service MUST provide the response.
Keep store selection, pairing rules, and retailer API calls on the server.
Use the live Globus guest API for products. See `docs/food-api.md`.
Do not replace retailer errors with mock products.
Request location only through the explicit user action. Offer manual store selection.
Do not log or persist coordinates. Do not send coordinates to the retailer.
Use fresh guest identity headers for each recommendation request.
Preserve `price_per` units and promotion conditions. Basket `quantity` is not stock.

## Shelf segmentation

Keep «Одна бутылка» as the default. Use «Вся полка» for multi-bottle photos.
Read `docs/shelf-mode.md` for the contract and limits.
The browser MUST call our portal API. Only the server may call SAM3.
Use canonical `SAM3_ENDPOINT`. The GX10 base URL is `http://192.168.86.14:18081/upstream/sam3`.
Normalize orientation and strip photo metadata before forwarding images.
Keep photos, masks, and crops in memory. Do not log or persist them.
Recognize only the crop selected by the user. Preserve the evaluator contract.
Real segmentation does not imply real wine identity. Retain mock recognition disclosure.
