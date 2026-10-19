# Wine for a dish

The third scanner mode is «Вино к блюду» at `/dish`.
The mode is available on desktop and mobile. The default mode stays «Одна бутылка» at `/`.
The existing `/shelf` route and single-bottle evaluator contract stay unchanged.

## User flow

1. Drop one dish image on the photo panel, select JPG/JPEG, HEIC/HEIF, PNG or WebP up to 10 MiB, use the mobile camera, or enter a dish name. Dropping a new image replaces the previous photo and cancels its pending work. Cancelling the file picker preserves the current photo.
2. The browser checks file signatures, including uploads with an empty or generic MIME type. HEIC is decoded in a disposable local worker with pinned `heic-to` 1.6.6, including browsers without native HEIC support. Its metadata dimensions are bounded before pixel allocation. All formats become an upright JPEG with a maximum 1,600-pixel side and a 50-million-pixel input limit. Canvas re-encoding does not copy source EXIF/GPS; a browser can add its own technical image properties.
3. Photo recognition proposes a dish label. It never confirms hidden ingredients. Wine cards remain hidden until the user confirms or corrects the dish.
4. The user can select one of 16 broad categories when the exact dish is unknown. The name field offers the 200 dishes and 120 classes from the backend taxonomy.
5. Three visible icon rows replace the settings form. Seven taste/sauce presets set heat, cream, acidity and sauce sweetness. Compatible presets combine; opposite presets replace each other. The second row sets wine color and still/sparkling status. The third row sets wine sweetness. Clicking a selected choice clears that preference. No sauce choice preserves the recipe default; no wine choice adds no constraint. Explicit negatives, including no cream, are sent as negative values. A brut category selects sparkling wine; selecting still wine or clearing sparkling clears a brut category. Clearing sweetness leaves the visible wine-kind choice in place; it can be cleared separately. Rows wrap on narrow screens and retain at least 44-pixel targets. Each button has a visible text label, keyboard activation and `aria-pressed` state.
6. The server returns the first eligible wine page. Each card shows exact source facts, a reason and the source portal link. The label distinguishes editorial choices from discovery choices.
7. «Показать ещё» sends the opaque signed cursor without changing filters. Changing a dish or a filter discards old cards and cursors. A failed continuation preserves the existing cards and permits retry.

The browser does not store a photo or result in local storage. The portal does not write them to disk or logs. API responses use `Cache-Control: no-store` and are excluded from the existing service-worker API caching rules. The model provider receives the sanitized image through Dinner Lens.
Cancellation aborts the portal fetch and suppresses stale UI results. It does not guarantee interruption of already-running model work on gx10.
HEIC conversion has a separate 60-second bound. Cancellation, replacement, mode exit and conversion timeout terminate the decoder worker. The recognition deadline includes preparation time plus the existing upstream request budget. The large HEIC decoder is excluded from PWA precaching and loads only after a HEIC selection. Third-party license and source notices are under `public/third-party/`.

## Server boundary

The browser calls only these same-origin JSON routes:

| Portal route | Dinner Lens route |
| --- | --- |
| `POST /api/dinner/recognize` | `POST /v1/recognize-and-recommend` |
| `POST /api/dinner/recommendations` | `POST /v1/recommendations` |
| `POST /api/dinner/more` | `POST /v1/recommendations/more` |

Nuxt private runtime settings:

- `NUXT_DINNER_LENS_ENDPOINT`: the service origin, without credentials, query or path prefix.
- `NUXT_DINNER_LENS_API_TOKEN`: the existing Dinner Lens API bearer token. Inject it through the server environment. Never put it in public runtime configuration.

`/api/config` returns only `dinnerAvailable`. It never returns the endpoint or token. Availability means that the private settings are configured. It is not a live model readiness probe.
Missing settings produce an unavailable UI and HTTP 503. A service failure never becomes a mock result.

The proxy accepts JSON only, bounds body bytes before parsing, validates the supported input fields, rejects redirects and caps streamed responses at 2 MiB. Its total fetch deadline is 180 seconds. It validates source portal URLs, node IDs, result structure and cursor counts. It strips model receipts and internal diagnostics from browser responses. No price or stock value is invented.
Hard filters, curation, embeddings and cursor signing remain in Dinner Lens. The Web UI has no second wine-selection engine.

## Taxonomy labels

`shared/data/dinner-taxonomy.json` contains only original node IDs, parent IDs, kinds and Russian labels.
It records the SHA-256 of `dinner-lens/data/pairing-dataset.v4.json`.
After a backend taxonomy update, run `npm run dinner:taxonomy` from this directory in a full source checkout. Review and commit the label export with the client change.
The export contains no wine lists, eligibility rules, embeddings or benchmark labels.

## Verification

Run `npm run test`, `npm run typecheck`, `npm run build` and `npm run test:bundle`.
The optional full-catalog producer-map tests require their existing `PRODUCT_LINE_CATALOG_SNAPSHOT` input.

Set `PLAYWRIGHT_MODULE` to an installed Playwright `index.mjs` and `PORTAL_ORIGIN` to the running portal, then run `npm run test:dinner`.
The deterministic browser suite checks Chromium at 1,440, 1,024, 820 and 320 pixels, and mobile WebKit at 390 pixels. It checks both themes, the three icon rows, all seven taste presets, explicit negative values, combined sauces, preference reset, brut compatibility, keyboard activation, 44-pixel targets, three visible mode links, upload-action contrast, route reset, complete continuation, unknown-dish clarification, provider errors and horizontal overflow. Its API fixtures are test-only route interceptions. The running portal must have Dinner Lens configured because its initial availability is server-rendered. A local fixture run can use a non-secret dummy endpoint and token; browser routes intercept all recommendation requests.
For a protected portal, provide `PORTAL_BASIC_USER` and `PORTAL_BASIC_PASSWORD` through the test process environment. Do not put credentials in commands, receipts or screenshots.

To exercise the real service as well, configure the private portal settings and set `DINNER_LIVE_CHECK=1`.
Set `DINNER_TEST_IMAGE` to a local licensed dish photo to include a real VLM call through the full browser normalization and confirmation flow.
The live suite follows every wine page for grilled ribeye, Olivier with doctor's sausage, and steamed king crab with clarified butter. It verifies discovery results beyond curation and unique IDs. `BROWSER_ARTIFACT_DIR` selects an external directory for screenshots and receipts.
Camera attributes and mobile WebKit are automated checks. A physical phone camera still needs a device check.

Run `npm run test:dinner-uploads` with the same browser environment for drag-and-drop and format coverage. It exercises actual JPEG/PNG/WebP encoding and a synthetic rotated HEIC, including empty/generic MIME types, uppercase extensions, nested drop targets, invalid files and the HEIC file picker in Chromium and WebKit. These cases intercept recognition only after real browser decoding and normalization. Set `DINNER_HEIC_LIVE_IMAGE` to a local dish HEIC to add a real-service drop/recognition/confirmation check.
