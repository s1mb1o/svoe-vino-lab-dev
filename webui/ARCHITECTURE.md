# Architecture

## Page

Nuxt renders one photo search page at `/`.
The app shell blocks the page with `AgeGate` until local storage contains the accepted 18+ value.
The app shell provides the source logo, a scanner label, and a link to the source portal.
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
Workbox uses `NetworkFirst` for same-origin page navigation.
The page route excludes `/api/` and `/v1/`.
The page route accepts only GET requests.
It does not store photo uploads or API responses.
The module applies service-worker updates automatically.
Recognition and metadata requests require a network connection.

## Result experiences

`WineExperiences` mounts after a resolved wine result.
It owns one native dialog and four local experience states.
The product demo uses fictional `shared/experiences.ts` data.
The simulated permission does not call `navigator.geolocation`.
The label demo reads grape names from the resolved wine and keeps its Syrah and Viognier copy explicitly illustrative.
The story demo rotates fictional text without audio or a network request.
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
