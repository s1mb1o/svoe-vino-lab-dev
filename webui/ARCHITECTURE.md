# Architecture

## Page

Nuxt renders one photo search page at `/`.
The app shell provides the source logo, a scanner label, and a link to the source portal.
`PhotoScanner` renders the upload, progress, and single-match states.
`useWineScanner` owns selection, cancellation, prediction, metadata lookup, and preview cleanup.

## Prediction

The browser sends one `FormData` image to `POST /v1/eval/predict`.
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

## Food recommendations

The demo data flow is `Web UI -> our portal API -> our server-side service -> response`.
The browser calls relative portal routes. The browser does not call retailer APIs.
The service owns store selection, product queries, pairing rules, and response normalization.
The UI renders the response and manages user interaction.
The current demo runs the portal API and service in the same Nuxt server.
This deployment does not imply that a separate backend service is already connected.
If the service moves to another process, keep the browser-facing portal contract stable.

`FoodRecommendations` mounts only for a matched wine with metadata.
`useFoodRecommendations` owns geolocation, manual store selection, requests, cancellation, and result state.
The component unmounts when photo search clears the match. Late food responses cannot replace the new wine result.
`server/utils/food-pairings.ts` maps source pairing labels to distinct food ideas.
Wine-style defaults fill missing categories. No LLM is required.
`server/utils/globus.ts` reads the live directory, chooses a store, and queries products in a fresh guest context.
Each request has separate app and device IDs. Concurrent users do not share a store selection.
Coordinates remain on the portal server. Globus receives the selected store ID and product queries.
The client shows source units, card conditions, availability time, and validated product URLs.
Product images load from the retailer CDN. Product links open the retailer page after a user action.
These media and navigation requests are separate from the portal data API.
Only products with positive `quantity_max` and `active=true` qualify.
Read `docs/food-api.md` for the integration boundary.

## Shelf photos

The current page switches between `PhotoScanner` and `ShelfUnavailable`.
`ShelfUnavailable` does not accept a photo and does not make an API request.
The default `NUXT_SHELF_MODE=disabled` setting makes `POST /api/shelf/segment` return HTTP 503 before it reads an upload or calls SAM3.

The implemented enabled path switches between `PhotoScanner` and `ShelfScanner`.
A mode change unmounts the previous scanner and cancels its requests.
`useShelfScanner` owns the shelf photo, segmentation, selection, and popup state.
The browser sends the photo to our `POST /api/shelf/segment` route.
`server/utils/shelf.ts` normalizes the image with Sharp and calls the configured SAM3 service.
The server validates the response. It clamps detector boxes and suppresses duplicate boxes.
The response contains the normalized photo, cropped transparent masks, and original-image bottle crops.
The browser positions masks and controls with normalized coordinates.
Small overlay images avoid a full-frame texture for each bottle.
The server retains at most 100 bottles and reports truncation.

Selecting a bottle opens a native dialog and passes its JPEG crop to `useWineScanner`.
The crop follows the existing `POST /v1/eval/predict` contract.
No prediction runs before a bottle selection.
Closing the popup cancels its recognition and food requests. The segmented shelf remains available.
Replacing the photo, resetting, and unmounting invalidate late responses and release transient data.
The server forwards client disconnection signals to segmentation and prediction requests.
The browser never receives the SAM3 endpoint. It never calls SAM3 directly.
