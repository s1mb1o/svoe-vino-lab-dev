# Change log

## 2026-09-28

### Princess deployment preparation

- Kept «Вся полка» selectable and replaced its scanner with a temporary-unavailable view.
- Removed shelf upload and camera actions from the disabled view.
- Added a server guard that rejects shelf requests before image parsing or SAM3 access.
- Made shelf processing opt-in through `NUXT_SHELF_MODE=enabled`.
- Recorded the Princess capacity check and deployment boundary.
- Verified 103 tests, type checks, and the production build.

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
