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
«Одна бутылка» is at `/`. «Вся полка» is at `/shelf`.
Read `docs/shelf-mode.md` for the contract and limits.
The browser MUST call the same-origin `POST /v1/group/match` route.
Derive the upstream group URL from `NUXT_PREDICTION_ENDPOINT`.
Do not add a separate group endpoint variable.
Only the matcher may call SAM3.
Keep photos, masks, and responses out of Web UI disk storage and logs.
The matcher can archive the original group photo. Do not claim that it is never stored.
Use the matches returned by the group request. Do not recognize a selected bottle again.
Preserve the evaluator contract for single-bottle prediction.

## Producer product-line map

Read `docs/plans/01_product-line-map.md` and `docs/product-line-map-sources.md`.
Keep one JSON file per producer in `shared/data/product-line-maps/`.
Register each JSON through an explicit lazy loader in `shared/data/product-line-maps/index.ts`: `'<producer-id>': () => import('./<producer-id>.json')`.
Do not use `import.meta.glob` in this shared module. Nitro does not transform it in the server build.
After a map change, run `npm run line-maps:index` and commit `shared/data/product-line-index.json`. The build and the MCP server stop on a stale index.
Pages MUST import only the index through `shared/product-line-map.ts`. Load a full map with `loadProductLine`. Do not import a map JSON statically in app code.
After a build, run `npm run test:bundle`. It fails when `/` or `/shelf` loads map data at first paint.
Keep the pure types and functions in `shared/product-line-core.ts`. Do not add runtime imports to this module. The MCP server imports it in Node.js.
Keep each producer's independent catalog extract, crosswalk, and source provenance in `docs/product-line-maps/`.
Record exact source URLs, catalog sections, retrieval dates, and source hashes for reviewed maps.
Record the membership basis for each crosswalk entry.
Snapshot-only groups without a confirmed price position MUST use rank 0.
Run `npm run test:producer-maps` for new producers in addition to the Abrau regression suite.
A null or failed image MUST use the labeled placeholder. Image availability MUST NOT change catalog link availability.
Use `group_id` as the authoritative containment relation.
Keep `wine_slug` nullable. A null slug MUST NOT produce a portal link.
Keep recognized selection separate from current selection.
Only verified equivalent slugs MAY share one product node.
Do not merge kosher variants or distinct packages.
Do not infer numeric prices from premium tiers or slug suffixes.
The preview route MUST NOT claim that its selection came from recognition.
Center the map after the native dialog is visible.
Use viewport-specific scrolling when locating a product.
At widths up to 767 px, open product details in a native modal popup after a product tap.
Keep the initial product selected without opening the popup on map entry.
Keep the «О выбранном вине» control available for the current selection.
Closing the popup MUST preserve the map position and restore its opener.
Keep the parent map and shelf dialogs open when the popup closes.
Keep explicit Tab cycling inside the mobile popup. WebKit can reach the underlying shelf dialog without it.
Keep popup content scrollable and actions reachable in short viewports.
Record the clicked dialog opener through `event.currentTarget`. WebKit may not focus clicked buttons.
Run `npm run test:line-map` with the documented browser environment after map interaction changes.

### Product image checks

An alpha channel does not prove that the background is removed. Inspect alpha coverage and the visible outline.
Nearly transparent outer pixels can reduce bottle scale under CSS max-width. Verify the final image at the actual desktop and mobile sizes.
Imagegen display derivatives can change fine print. Keep original hashes and exact prompts in the producer provenance. Do not use generated microtext as product evidence.
A transparent border can surround an image with opaque stripe remnants. Composite every edited image on flat light and dark backgrounds. Inspect the complete contour before acceptance.

Use the optional `image.frame` geometry and `ProductLineImage.vue` to normalize visible bottle size. Read `docs/product-image-sizing.md`.
Do not compare HTML image-box heights when checking bottle scale. Compare the rendered alpha outline.
Recompute frame geometry when an image asset changes. Keep the original image dimensions consistent with its frame.
Visual checks MUST account for the clipped image-frame bounds. Do not wait on hidden lazy source images in WebKit.

Wait for `document.fonts.ready` before measuring a map centering target. A new group can wrap after the web font loads and move the selected product away from the center. Keep the delayed-font centering regression in `test:line-map`.

Apply image consumer class and style once to the frame. Keep native attributes on the inner image.
Run the pixel/frame checker after asset or frame changes. It checks actual dimensions and alpha containment.
