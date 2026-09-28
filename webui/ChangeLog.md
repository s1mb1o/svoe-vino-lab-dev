# Change log

## 2026-09-29

### Complete result metadata fallback

- Added an exact server-side wine lookup through the official `api.vino-svoe.ru` JSON endpoint.
- Kept the 12 local records as the mock and fast metadata path.
- Validated the returned slug, bottle image path, fields, redirects, response size, and timeout.
- Normalized source cards into the existing Web UI wine contract.
- Changed `catalogMode` from `demo` to `source-fallback`.
- Added source metadata normalization and failure tests.
- Verified the real Massandra slug through the local production build.
- Verified all 150 tests, type checks, and the production build.

### Owner-supplied shelf examples

- Replaced the Wikimedia shelf example with three unique photographs from the project owner.
- Added an accessible example selector before group matching.
- Converted the photographs to metadata-free WebP files below the upload limit.
- Kept every example on the same `/v1/group/match` path as an uploaded shelf photograph.
- Verified all 141 tests, type checks, and the production build.

### Production response status repair

- Preserved actionable matcher status codes through the single-bottle prediction proxy.
- Kept unexpected matcher statuses and invalid responses mapped to HTTP 502.
- Added regression tests for HTTP 400, 401, 408, 413, 415, 502, 503, and 504.
- Verified all 138 tests, type checks, and the production build.
- Deployed revision `11ebfbf` on Princess.
- Verified HTTP 413 for a JPEG dimension bomb and HTTP 503 for matcher overload.
- Verified the production shelf flow with 93 selectable and matched bottles.

## 2026-09-28

### Search discovery

- Kept the complete scanner page in server-rendered HTML while the 18+ gate blocks interaction as an overlay.
- Kept `Найти вино по фото` as the primary page heading.
- Added the canonical URL, Open Graph metadata, Twitter card metadata, and JSON-LD for the website and web application.
- Added `robots.txt` and a one-URL sitemap.
- Changed the legacy catalog redirects to HTTP 308.
- Added a seven-day cache policy for static reference assets.
- Added focused search-discovery tests and manual response checks.

### Matcher availability check

- Added a server-side matcher readiness check to `GET /api/config`.
- Derived `/healthz` from `NUXT_PREDICTION_ENDPOINT` without exposing the matcher URL to the browser.
- Added a 2-second readiness timeout and strict `{"status":"ok"}` validation.
- Disabled photo selection and shelf mode when the configured matcher is unavailable.
- Kept mock mode available without an upstream request.
- Verified all 125 tests, type checks, and the production build.

### Progressive Web App

- Added `@vite-pwa/nuxt` with a generated manifest, Workbox service worker, and automatic updates.
- Added a network-first page cache and precached the Nuxt bundles and app-shell assets.
- Added regular, maskable, and Apple touch icons from the Telegram bot wine-glass mark.
- Excluded photo uploads, `/api/`, and `/v1/` from Workbox runtime caches.
- Added PWA asset tests and production contract checks.
- Verified all 117 tests, type checks, the production build, live PWA endpoints, and browser metadata.

### Age gate and result experiences

- Added a mandatory 18+ gate with one local storage value and an explicit blocked state.
- Added four local actions after a wine result: products, label explanation, story, and product-line guide.
- Added a simulated SuperLenta flow with three fictional domestic products and one visible promotion label.
- Added a Syrah and Viognier explanation with an explicit illustrative-content notice.
- Added rotating fictional stories with a future-audio callout.
- Added an interactive Abrau-Durso map with zoom, current-wine navigation, selection, and public source links.
- Removed live retailer and geolocation calls from the rendered result UI.
- Added focused age and experience data tests.
- Verified all 115 tests, type checks, the production build, and three evaluator contract requests.
- Verified the desktop and 390 px mobile layouts in dark mode.

### Shelf group matching

- Connected the existing «Вся полка» tab to same-origin `POST /v1/group/match`.
- Reused `NUXT_PREDICTION_ENDPOINT` and derived the group path without a new environment variable.
- Added a bounded server proxy with response validation, timeout handling, and disconnect cancellation.
- Rendered matcher masks and normalized bottle controls on the returned shelf preview.
- Opened the ready wine match for each bottle without a second recognition request.
- Added explicit unmatched, empty, unavailable, retry, and stale-response states.
- Updated shelf browser tools, contract tests, state tests, and service documentation.
- Verified 115 tests, type checks, and the production build.

### Princess deployment preparation

- Kept «Вся полка» selectable and replaced its scanner with a temporary-unavailable view.
- Removed shelf upload and camera actions from the disabled view.
- Added a server guard that rejects shelf requests before image parsing or SAM3 access.
- Made shelf processing opt-in through `NUXT_SHELF_MODE=enabled`.
- Recorded the Princess capacity check and deployment boundary.
- Verified 103 tests, type checks, and the production build.
- Added `/api/predict` for browser requests so Princess can preserve its protected public evaluator route.

### Repository integration

- Moved the Web UI into `svoe-vino-lab/webui`.
- Excluded the standalone Git history, dependencies, generated output, and local reports.
- Updated the default evaluator path for the new directory depth and the current 2026-09-17 package.
- Added Web UI verification to the root GitLab CI configuration.

## 2026-09-15

### Shelf photo mode

- Added «Вся полка» beside the existing single-bottle mode.
- Added real SAM3 segmentation through our portal API and canonical `SAM3_ENDPOINT`.
- Added photo orientation normalization, metadata removal, validated masks, and original-image crops.
- Added numbered bottle controls, zoom, and a wine popup with the source link and food recommendations.
- Deferred recognition until the user selects a bottle. Preserved explicit mock identity disclosure.
- Added cancellation, retry, empty results, malformed response handling, and response limits.
- Added a public shelf example with CC BY 2.5 attribution.
- Added service and state checks. All 102 tests pass in seven files.
- Verified the production API with 94 real bottle masks and crops from the public example.
- Verified browser tools, wine popups, food recommendations, reset, and the unchanged official evaluator.
- Added a bounded retry for transient SAM3 connection failures observed during model loading.

### Demo service boundary

- Confirmed that the Web UI queries our portal API for stores and recommendations.
- Clarified that our server-side service owns retailer access and returns the prepared response.
- Documented the current Nuxt deployment and the stable contract for a later separate backend.
- Checked the client and server call sites. No runtime change was needed.

### Food recommendations

- Added «Подобрать 3 продукта к вину» after a matched wine.
- Added explicit geolocation and manual store selection.
- Integrated the live Globus directory, store context, search, and product details.
- Added three distinct food ideas with source prices, units, availability, conditions, images, and links.
- Kept the wine result visible and retained mock recognition disclosure.
- Added cancellation, partial stock, source error, distant store, and location denial states.
- Added request isolation and limited retailer response parsing.
- Added state, location, stock, pairing, and provider boundary tests.
- Verified 75 tests, type checks, production build, live food API, browser tool flow, and the unchanged evaluator.

### Photo search page

- Replaced the catalog UX with the dedicated «Найти вино по фото» home page.
- Added a responsive upload and single-result workspace in the source visual style.
- Automatically submit valid photo selections through the existing evaluator API.
- Show the best match bottle, title, and direct source portal link.
- Preserve successful prediction links when metadata fails or times out.
- Removed local catalog, filter, modal, and detail-page interfaces.
- Redirect old catalog bookmarks to the scanner and old detail links to the source portal.
- Added request state and metadata failure tests.
- Verified 41 tests, type checks, production build, and three official evaluator requests.
- Verified the complete demo upload through the browser tool surface.

### Initial implementation

- Created the repository with an empty initial commit.
- Added the portal specification, API contract, architecture, and acceptance plan.
- Created the private GitLab project `ashmelev/svoe-vino-webui`.
- Added the Nuxt catalog, filters, search, sorting, and exact slug detail pages.
- Added 12 source-backed demo wine records and local visual assets.
- Added the photo scanner with previews, cancellation, retries, and explicit mock results.
- Added the evaluator-compatible mock route and configurable upstream proxy.
- Added responsive styles, system dark mode, and native keyboard-accessible dialogs.
- Added optional WebMCP catalog tools and verified their input validation.
- Added 30 passing tests and a passing production build.
- Verified the unchanged official evaluator against the production mock endpoint with three images.
- Added GitLab CI and setup documentation.
- Aligned the package engine range and setup guide with the Nuxt runtime requirements.
