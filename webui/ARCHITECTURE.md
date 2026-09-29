# Architecture

## Page

Nuxt renders one photo search page at `/`.
The app shell blocks the page with `AgeGate` until local storage contains the accepted 18+ value.
The app shell provides the shared product logo, the `Что за вино?` name, a scanner label, a theme selector, and a link to the source portal.
`ProductBrand` renders the same product identity in the header and age gate.
`ThemeSwitcher` stores the theme preference in local storage and listens for system and storage changes.
The head initialization script applies the saved palette before first paint.
The `data-theme` attribute selects the palette for the page and dialogs.
`PhotoScanner` renders the upload, progress, and single-match states.
`useWineScanner` owns selection, cancellation, prediction, metadata lookup, and preview cleanup.

## Prediction

The browser sends one `FormData` image to `POST /api/predict`.
The portal keeps `POST /v1/eval/predict` as an equivalent evaluator route.
The server selects the existing mock or upstream provider.
The wire response uses `slug`.
The browser stores the slug before resolving metadata.
Metadata failure does not invalidate recognition success.
The result URL uses `sourceWineUrl(slug)` and always targets the source portal.

## Metadata

The server keeps a 12-wine demo fixture for exact slug lookup.
The browser fetches only the matching record.
The fixture is not rendered as a browsable catalog.
Replace the metadata provider when complete catalog access is available.

## Compatibility

Old catalog paths redirect to the scanner home page.
Old local detail paths redirect to the matching source portal page.
The evaluator route and provider configuration stay unchanged.
The app uses local copies of the approved reference visual assets.
The Node server runs on the existing loopback port 8153.

## Progressive Web App

`@vite-pwa/nuxt` generates `manifest.webmanifest` and the Workbox service worker.
`NuxtPwaManifest` adds the generated manifest link to the document head.
The module registers the service worker only in a production build.
Workbox precaches the client bundles, install icons, and app-shell reference assets.
The favicon and install-icon derivatives come from the repository-level shared product logo in `../assets/`.
Workbox uses `NetworkFirst` for same-origin page navigation.
The page route excludes `/api/` and `/v1/`.
The page route accepts only GET requests.
It does not store photo uploads or API route responses.
A cached page contains the server-rendered `/api/config` payload.
The first navigation occurs before the service worker is active. The page cache fills from the second navigation.
`registerType: 'prompt'` keeps an updated service worker in the waiting state.
The generated service worker has no `clientsClaim` and calls `skipWaiting` only for a `SKIP_WAITING` message.
The app sends no such message. The new version becomes active after all app pages close.
The manifest lists two home-page screenshots from `public/screenshots/`. Workbox does not precache them.
`scripts/check-pwa-browser.mjs` checks install, offline, cache, and update behavior in Chromium.
Recognition and metadata requests require a network connection.

## Result experiences

`WineExperiences` mounts after a resolved wine result.
It owns one native dialog and four local experience states.
`shared/taste.ts` derives the taste passport, dish pairings, and international analogue.
The derivation reads the resolved wine description, source pairing categories, grape varieties, color, and category.
The derivation also reads `shared/data/wine-style-priors.json`.
`scripts/build-wine-style-priors.py` creates this file from the public Wine Reviews CSV.
The artifact stores only aggregate descriptor frequencies and structural levels for 18 grape varieties.
It stores no review text and no critic score.
Source description evidence has priority over a dataset aggregate.
A dataset aggregate has priority over a generic style fallback.
The UI always identifies the aggregate source and license.
The UI states when no grape mapping is available.
The derivation is deterministic and does not call an external model or recommendation service.
Three dish rules include local 640 by 400 WebP illustrations.
Other dish rules remain complete without an image.
The dish demo does not call `navigator.geolocation`.
The label demo reads grape names from the resolved wine and keeps its Syrah and Viognier copy explicitly illustrative.
The product-line guide compares the resolved producer and slug with the local Abrau-Durso map.
An exact local slug becomes the current node.
An Abrau-Durso slug without a local node stays outside the collection tiers.
Another producer keeps the fixed demonstration node.
The Abrau-Durso guide uses local map coordinates and public source portal links.
The previous retailer integration and API routes remain in the repository but are not part of the rendered result flow.

## Shelf photos

The page switches between `PhotoScanner`, `ShelfScanner`, and `ShelfUnavailable`.
`ShelfScanner` is available in upstream mode when `NUXT_PREDICTION_ENDPOINT` ends with `/v1/eval/predict`.
The server derives the upstream `/v1/group/match` URL from that configuration.
`ShelfUnavailable` does not accept a photo and does not make an API request.
A mode change unmounts the previous scanner and cancels its requests.
`useShelfScanner` owns the shelf photo, group result, selection, and popup state.
The browser sends the photo to same-origin `POST /v1/group/match`.
`server/utils/group.ts` proxies the image to the matcher and validates its response.
The matcher owns segmentation, wine matching, and any SAM3 access.
The response contains the preview, masks, normalized bottle boxes, and nullable wine matches.
The browser positions masks and controls with normalized coordinates.
The server retains at most 100 bottles and reports truncation.

Selecting a bottle opens a native dialog with the match already returned for that bottle.
Selection makes no network request.
Closing the popup cancels its result-experience requests. The matched shelf remains available.
Replacing the photo, resetting, and unmounting invalidate late responses and release transient data.
The server forwards client disconnection signals to the matcher request.
The browser never receives the private matcher endpoint or a SAM3 endpoint.
