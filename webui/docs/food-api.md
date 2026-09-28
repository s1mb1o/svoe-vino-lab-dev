# Food API

Date: 2026-09-15.
Provider: Globus. Mode: live guest requests.
Evidence: [access check](validation/globus-access.json).
Prior contract: `../retail-query/docs/globus/store-search.md`.

## Portal routes

The Web UI calls these routes on our portal origin.
Our server-side service returns the complete recommendation response.
Store lookup, retailer access, and pairing rules stay in the service.
The current demo hosts this service inside the Nuxt server.
The browser does not call the retailer endpoints documented below.

`GET /api/food/stores` returns `{ provider: "globus", stores: FoodStore[] }`.
A store contains `id`, `name`, `address`, `location`, and `schedule`.

`POST /api/food/pairings` accepts JSON:

```json
{"slug":"priboj-marchenko-beloe-polusuhoe","storeId":5020}
```

For nearest-store selection, replace `storeId` with `location`.
`location` contains finite numeric `latitude` and `longitude`.
Latitude must be in [-90, 90]. Longitude must be in [-180, 180].
Do not send both selectors. Do not send a free-form upstream URL.
The request body limit is 2048 bytes.

The response follows `shared/food.ts`.
`distanceKm` is straight-line distance. Manual selection returns `null`.
`complete` is true only when three distinct products are returned.
`checkedAt` is an ISO 8601 timestamp.
All routes use `Cache-Control: no-store`.

| Status | Meaning |
| --- | --- |
| 200 | Live result. Inspect `complete` and `products.length`. |
| 400 | Invalid JSON, coordinates, selector, or unknown store ID. |
| 413 | Request body exceeds the limit. |
| 415 | Request content type is not JSON. |
| 422 | The wine has no metadata for pairing. |
| 502 | The retailer request failed or returned an invalid response. |

## Retailer sequence

Base URL: `https://digitalone.globus.ru/d1-mobile-bff/api/`.

1. Call `GET v1/directories/stores`.
2. Select the nearest store coordinate or the validated manual store ID.
3. Call `PATCH v1/context` with `{"context":{"purchase_method":1,"store_id":5020}}`.
4. Call `POST v6/catalog/search:result` for distinct food ideas.
5. Call `POST v5/catalog/pdp` for a selected product ID.

Search body:

```json
{"query":"моцарелла","sort":"default","pagination":{"page":1,"per_page":8},"filter":{"filter":[],"range":[]},"include":["products"]}
```

Detail body: `{"id":"<returned product ID>"}`.
Use fresh `X-App-Id` and `X-Device-Id` UUIDs for each portal request.
Keep these two IDs consistent inside that request.
Use a new `X-Request-ID` for each HTTP call.
Send `Env: prod`, JSON headers, and an honest application User-Agent.
The verified flow needs no authorization token, cookie, or supplied context hash.

## Product selection

Use source wine pairing labels first. Apply wine-style defaults for missing ideas.
Use at most six ideas. Search the first eight results per idea.
Validate product terms and preparation. Reject unavailable and adult products.
Require `active=true` and numeric `quantity_max>0` in search and detail records.
Try at most two matching detail records per idea.
Return one product per idea. Remove duplicate product IDs.
Use the source `price_per` string. Preserve its units and all returned price conditions.
Use `share_text` only for HTTPS `www.globus.ru/products/` URLs.
Use source images only from HTTPS `image.globus.ru`.

Each retailer HTTP call has a five-second timeout and a 512 KiB response limit.
The recommendation request has a twenty-second total upstream budget.
The browser waits at most twenty-five seconds for recommendations.
Reject redirects, non-JSON responses, access errors, and invalid response shapes.
Never fall back to demo products after a source error.

## Privacy and limits

Request browser location only after an explicit action.
Offer manual selection without location permission.
Calculate distance on the portal server. Do not send user coordinates to Globus.
Do not persist coordinates, photo content, guest identities, or recommendation requests.
Source images load directly from the retailer image host without a referrer.
No cart or purchase endpoint is used.
Geolocation requires HTTPS or secure localhost.

Globus uses application endpoints. Endpoint stability is not guaranteed.
The nearest store means the nearest store in the returned Globus directory.
A store farther than 50 km is marked as distant.
Do not claim delivery eligibility, route distance, or guaranteed physical stock.
Prices and stock are observations at `checkedAt`.
Recognition remains mock until configured. Food products are live even for the demo wine.
