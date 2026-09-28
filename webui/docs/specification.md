# Photo search specification

Date: 2026-09-15.
Status: ready for implementation.
Authority: the user corrected the portal scope on 2026-09-15.
This specification replaces the previous catalog UX specification.

## Goal

The home page MUST be «Найти вино по фото».
The page MUST use the visual identity of `https://vino-svoe.ru/`.
The page MUST NOT reproduce the source portal catalog experience.
The page MUST provide «Одна бутылка» and «Вся полка» modes.
Read [the shelf mode specification](shelf-mode.md) for segmented shelf photos and wine popups.
The current deployment MUST keep «Вся полка» selectable and show a temporary-unavailable state.
The current deployment MUST NOT send a shelf photo or call SAM3.

## Visual design

Use the source logo, Playfair Display headings, burgundy controls, cream surfaces, and grapevine background.
Use one photo search workspace. Do not show a catalog grid, filters, sorting, or local wine detail navigation.
On desktop, place the upload area beside the result area.
On phones, place the result below the upload area. Keep the upload action prominent.
Show large touch targets. Prevent horizontal overflow.
Follow the system dark theme and reduced motion preference.

## Flow

1. The user selects one photo, takes a photo, drops one file, or selects the demo example.
2. The app validates the file and shows a preview.
3. The app MUST automatically submit one request. Do not require a second submit action.
4. The app MUST show progress and offer cancellation.
5. The app MUST show one best match with the bottle image and title when metadata is available.
6. The result MUST link directly to `https://vino-svoe.ru/wines/<slug>`.
7. The user MAY replace the photo, reset the page, or retry a failed request.

## State and errors

Accept JPEG, PNG, and WebP files up to 10 MiB.
Reject empty files and multiple files before prediction.
A new selection MUST cancel and invalidate the previous request.
A stale response MUST NOT change the current result.
Release the preview URL on replacement, reset, and unmount.
A valid prediction slug MUST survive metadata failure or timeout.
If metadata is unavailable, show the slug and its source portal link. Do not invent a bottle or title.
Show a readable message when configuration or prediction is unavailable.
Mock mode MUST be visible before upload and on the result.
The mock result MUST NOT claim to identify the uploaded image.
Do not display a confidence score. The evaluator response does not provide one.

## Routes and API

`/` is the primary page.
`/wines` and `/wines/` MUST redirect to `/` for existing bookmarks.
Previous local wine detail routes MUST redirect to the corresponding source portal page.
Preserve `POST /v1/eval/predict`: one multipart file named `image`, response `{"slug":"..."}`.
Preserve the existing mock and upstream provider configuration.
Use the local metadata fixture to resolve the demo result. Do not display the fixture as a catalog.
Photos MUST remain in request memory. Do not write photos to disk.

## Acceptance

- The home page presents photo search without a catalog interface.
- Valid selection sends exactly one automatic prediction request.
- A known result contains one bottle, title, and exact external portal link.
- Metadata errors preserve a successful prediction and external link.
- Cancellation and replacement prevent stale results.
- Mock disclosure remains visible.
- Type checks, relevant state tests, and production build pass.
- The unchanged official evaluator accepts the production mock endpoint.

## Limits

Real prediction is not available yet.
The metadata fixture contains 12 wines. Unknown slugs use an explicit metadata fallback.
Physical camera capture needs a supported phone and browser.

## Food recommendations

Date: 2026-09-15. Status: ready for implementation.
Authority: the user requested three food recommendations and selected a retailer with an accessible API.

Demo boundary clarification, 2026-09-15: the Web UI MUST query our portal API.
Our server-side service MUST provide the recommendation response.
The service MUST own retailer integration and pairing logic.
The browser MUST NOT call retailer data APIs or calculate the product selection.
The current demo MAY run the service inside the Nuxt server.
Keep the portal API contract stable if the service moves to a separate backend.

After a match, show «Подобрать 3 продукта к вину».
Keep the wine result visible while the food request runs.
Use the Globus guest API. Read its store directory and selected-store catalog.
Use source wine pairings first. Use wine color when source pairings are absent.
Do not query products for a wine without metadata.
Request browser location only after the user presses the location action.
Calculate straight-line distance on the server. Select the nearest Globus store.
Send only the selected store ID to Globus. Do not send user coordinates to Globus.
Offer manual store selection when location is unavailable or denied.
Show the store name, address, schedule, and distance when distance is known.
Describe distance as straight-line distance. Do not claim travel time or delivery eligibility.
For a distant store, state that the selected network has no nearby store.
Search distinct food categories. Show up to three distinct available products.
Require `active=true` and `quantity_max>0`. Do not interpret basket `quantity` as stock.
Show the product name, source image, price per unit, promotion conditions, pairing explanation, and source link.
Read the product link from its detail response. Validate the retailer URL before display.
Show fewer than three products explicitly when the API cannot supply three suitable products.
Show a source error instead of mock products when the retailer request fails.
Keep prediction mock disclosure separate from live retailer data.
Cancel and invalidate food requests when the wine changes, the user resets, or the component unmounts.
Do not persist or log coordinates. Use POST JSON for location input. Use `Cache-Control: no-store`.
Use a fresh guest context for each recommendation request. Do not share store context between users.

### Food API

`GET /api/food/stores` returns the live Globus directory for manual selection.
`POST /api/food/pairings` accepts `slug` and exactly one location selector.
The location selector is `location: { latitude, longitude }` or `storeId`.
The server resolves wine metadata and validates the store ID against the directory.
The response contains `provider`, `store`, `distanceKm`, `checkedAt`, `products`, and `complete`.
Each product contains `id`, `name`, `image`, `url`, `priceLabel`, `conditions`, `food`, and `reason`.
The API MUST validate inputs, bound upstream response size, reject redirects, and use request timeouts.
The API MUST NOT create a cart, order, or purchase.

### Food acceptance

- Nearest-store selection uses coordinates from the live directory.
- Simultaneous users cannot change another user's store context.
- Three recommendations represent distinct foods and use available products only.
- Unknown wines, invalid coordinates, source failures, and sparse stock have explicit states.
- Geolocation denial permits manual selection. Cancellation suppresses late responses.
- Tests use synthetic coordinates. Live checks use public store coordinates, not the user's location.
