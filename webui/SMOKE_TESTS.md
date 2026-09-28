# Smoke tests

## Automated checks

1. Run `npm run typecheck`.
2. Run `npm test` for API, result metadata, and photo search state checks.
3. Run `npm run build`.
4. Start the production server with `npm start`.
5. Run `npm run test:contract` against the production mock endpoint.

The state tests check automatic submission, single-result resolution, metadata failures, cancellation, stale responses, retries, invalid files, and missing configuration.
The contract check uses the unchanged official evaluator and its three images.
The contract check also checks the home page, compatibility redirects, metadata routes, and image routes.

## Manual browser checklist

- Open `/`. Confirm the photo search page has no catalog grid or filters.
- Check the layout on a phone and desktop.
- Select a file. Confirm the search starts once without a second submit action.
- Check the photo preview, progress, and one result with a direct source link.
- Drop a photo. Confirm the same flow.
- Select a photo with the camera input on a physical phone.
- Replace a pending photo. Confirm the older response cannot change the result.
- Cancel and retry. Reset the page.
- Check mock disclosure before upload and on the result.
- Check the system dark theme, keyboard controls, and reduced motion.

## Verification scope

The manual checklist is not a completed visual regression suite.
Physical camera operation and the real recognition service remain untested.
See `docs/verification-2026-09-15.md` for current results.

## Results on 2026-09-15

- Type checks and production build passed.
- All 103 tests passed in seven files.
- The official evaluator accepted three production mock responses.
- Browser tool verification completed the example upload and returned one source-linked bottle.
- Invalid browser tool inputs did not change the completed result.
- Reset cleared the photo preview and the result.
- The updated preview is open at `http://127.0.0.1:8153/`.

## Food recommendation checks

- Confirm that food data requests use our portal routes. Retailer API calls must remain server-side.
- Match a wine. Confirm «Подобрать 3 продукта к вину» appears after the result.
- Confirm no location prompt appears before the explicit action.
- Allow location. Confirm the nearest Globus store name, address, and straight-line distance.
- Deny location. Confirm the manual store selector remains available.
- Select a store manually. Confirm the result does not claim a distance.
- Check three distinct foods, source images, product names, price units, card conditions, and external links.
- Check a distant location. Confirm the distance warning.
- Cancel a request. Replace the wine. Confirm stale products do not appear.
- Simulate sparse stock and retailer failure. Confirm explicit partial and error states.
- Check the food cards on phone and desktop, in light and dark themes.

Automated tests cover location denial, explicit action gating, manual selection, cancellation, unmount, timeout, nearest-store geometry, guest isolation, stock filtering, preparation matching, invalid URLs, and partial results.
The production live check selected store 5020 from public synthetic coordinates approximately 111 m away.
The production result returned three actual products in 2563 ms.
The browser tool flow returned the same three foods through manual store selection.
All four invalid food tool inputs were rejected.
The physical location permission prompt and full visual checklist have not been exercised.

## Shelf checks

- Select «Вся полка». Confirm that the single-bottle state is cleared.
- Confirm that the page shows «Вся полка» as temporarily unavailable.
- Confirm that the page has no shelf file input, camera input, or example action.
- Confirm that no shelf API request occurs.
- Send a direct request to `/api/shelf/segment`. Confirm HTTP 503.
- Confirm that the response occurs without a SAM3 request.
- Use «Перейти к одной бутылке». Confirm that the photo scanner returns.

The checks below apply only after `NUXT_SHELF_MODE=enabled`:

- Upload a shelf photo or use «Попробовать на примере».
- Confirm that the browser calls our portal API and the server calls SAM3.
- Confirm that bottle masks and numbered controls track the photo dimensions.
- Use «Увеличить». Select a small bottle or use its numbered control.
- Confirm that prediction starts only after selection and uses the selected JPEG crop.
- Confirm that the popup shows loading, the wine result, its source link, and mock disclosure.
- Close with Escape, the close button, and a backdrop click. Confirm focus returns to the selection control.
- Close and immediately open another bottle. Confirm a delayed close event does not clear the new popup.
- Request food recommendations for the selected wine. Confirm the request still uses our portal.
- Cancel segmentation, retry, replace the photo, reset, and switch modes.
- Simulate no detections, invalid masks, and an unavailable service. Confirm explicit states without fake segments.
- Check phone touch controls, zoom scrolling, the bottom sheet, dark mode, and reduced motion.

Automated checks cover normalization, EXIF removal, mask and crop alignment, bounded boxes, duplicate suppression, malformed data, retries, cancellation, deferred recognition, and stale results.
The public example has source and license attribution in `docs/assets.md`.
Manual camera and visual checks remain unverified unless explicitly recorded in the verification report.
