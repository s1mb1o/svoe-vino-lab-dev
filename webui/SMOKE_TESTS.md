# Smoke tests

## Automated checks

1. Run `npm run typecheck`.
2. Run `npm test` for API, result metadata, and photo search state checks.
3. Run `npm run build`.
4. Start the production server with `npm start`.
5. Run `npm run test:contract` against the production mock endpoint.

The state tests check automatic submission, single-result resolution, metadata failures, cancellation, stale responses, retries, invalid files, and missing configuration.
The metadata tests check official source normalization, exact slug lookup, fixed image hosting, invalid records, response limits, and timeout handling.
The API health tests check URL derivation, response validation, network failure, and timeout behavior.
The PWA tests check the Nuxt module configuration, icon dimensions, and API cache exclusions.
The search-discovery tests check the age overlay, canonical metadata, crawl files, permanent redirects, and static cache policy.
The contract check uses the unchanged official evaluator and its three images.
The contract check also checks the home page, compatibility redirects, metadata routes, image routes, manifest, service worker, and PWA icons.

## Manual browser checklist

- Open `/`. Confirm the photo search page has no catalog grid or filters.
- Check the layout on a phone and desktop.
- Select a file. Confirm the search starts once without a second submit action.
- Check the photo preview, progress, and one result with a direct source link.
- Use a recognized slug that is not in `server/data/wines.json`. Confirm that its source title and bottle image appear.
- Drop a photo. Confirm the same flow.
- Select a photo with the camera input on a physical phone.
- Replace a pending photo. Confirm the older response cannot change the result.
- Cancel and retry. Reset the page.
- Check mock disclosure before upload and on the result.
- Start upstream mode with an available matcher. Confirm that `/api/config` returns `apiAvailable: true`.
- Stop the matcher. Reload the page. Confirm the unavailable message and disabled photo actions.
- Start the matcher. Select «Повторить подключение». Confirm that photo actions become available.
- Check the system dark theme, keyboard controls, and reduced motion.
- Open a fresh browser origin. Confirm that the 18+ gate blocks the scanner.
- Read the raw HTML for `/`. Confirm that it contains `Найти вино по фото` before JavaScript runs.
- Inspect the hydrated document while the gate is open. Confirm that it contains one page H1 and the scanner content.
- Confirm that `robots.txt` and `sitemap.xml` return HTTP 200.
- Confirm that the page contains the apex canonical link, social metadata, and both JSON-LD types.
- Confirm that `/wines` and `/wines/<slug>` return HTTP 308.
- Confirm that `/reference/background.webp` returns the configured public cache policy.
- Confirm that `https://www.chtozavino.ru/` redirects to the apex with HTTP 308.
- Select the negative age action. Confirm that the blocked state does not store acceptance.
- Return and confirm age. Reload. Confirm that the accepted state remains in this browser.
- Build and start the production server. Confirm that the browser offers an install action.
- Install the portal. Confirm the shared bottle-scanner product logo and the standalone window.
- Open the installed app once while online. Disable the network and reopen it. Confirm that the app shell opens.
- While offline, submit a photo. Confirm a clear network error and no simulated result.
- Inspect service-worker cache storage. Confirm that it contains no `/api/`, `/v1/`, or uploaded photo response.

## Verification scope

The manual checklist is not a completed visual regression suite.
Physical camera operation and the real recognition service remain untested.
See `docs/verification-2026-09-15.md` for current results.

## Results on 2026-09-29

- Type checks passed.
- All 150 tests passed in 12 files.
- The production build passed.
- The three owner-supplied shelf examples passed WebP signature and upload-limit checks.
- Focused tests confirmed that the prediction proxy preserves actionable matcher status codes.
- A bounded production load test passed through eight concurrent recognition requests.
- The production matcher stayed healthy after the load test.
- The pre-deployment shelf check found that matcher revision `9ba496d` did not provide `/v1/group/match`.
- Web UI revision `11ebfbf` is active on Princess.
- The JPEG dimension bomb returned HTTP 413 through the production Web UI.
- A 12-request burst returned nine HTTP 200 responses and three HTTP 503 responses.
- Matcher revision `013ab56` is active on GX10 and passed the production deployment check.
- The public shelf example returned HTTP 200 with 93 detected and matched bottles.
- The production browser opened and closed a matched shelf wine card.

## Results on 2026-09-28

- Type checks passed.
- All 125 tests passed in ten files.
- The production build passed.
- The production contract check passed for the manifest, service worker, and all PWA icons.
- The production browser loaded the manifest and icon metadata without warnings or errors.
- Shelf tests confirmed one group request and no request on bottle selection.
- Live matcher, physical camera, and visual device checks remain pending.

## Results on 2026-09-15

- Type checks and production build passed.
- All 103 tests passed in seven files.
- The official evaluator accepted three production mock responses.
- Browser tool verification completed the example upload and returned one source-linked bottle.
- Invalid browser tool inputs did not change the completed result.
- Reset cleared the photo preview and the result.
- The updated preview is open at `http://127.0.0.1:8153/`.

## Result experience checks

- Match a wine. Confirm that all four result actions appear.
- Open «Подобрать продукты». Confirm that the first view explains the mock permission.
- Select «Разрешить в демо». Confirm that the browser does not show a location permission prompt.
- Confirm the fictional SuperLenta store, three domestic products, pairing copy, and promotion label.
- Open «Рассказать об этикетке». Confirm the metadata grape name and illustrative Syrah and Viognier notice.
- Open «История о вине». Confirm the fiction notice and switch to another story.
- Open «Путеводитель по линейке». Confirm the Abrau-Durso tiers and quality-rating notice.
- Change map zoom. Select another node. Use the direction control to bring the current demo wine into view.
- Confirm that the selected node exposes a normal source link.
- Close every dialog with its close button, Escape, and backdrop. Confirm focus restoration.
- Check the actions and dialogs at 390 px and on desktop in light and dark themes.

Focused automated tests cover age storage, storage failures, experience fixtures, story rotation, source URLs, and one current map item.
The 2026-09-28 browser check covered dark desktop and 390 px mobile layouts.
The product demo did not invoke a browser location permission prompt.

## Shelf checks

- Select «Вся полка». Confirm that the single-bottle state is cleared.
- Select each of the three owner-supplied examples. Confirm that the large preview follows the selected thumbnail.
- Run each selected example or upload a shelf photo.
- Confirm that the browser sends one request to same-origin `/v1/group/match`.
- Confirm that the server derives the upstream group URL from `NUXT_PREDICTION_ENDPOINT`.
- Confirm that bottle masks and numbered controls track the photo dimensions.
- Use «Увеличить». Select a small bottle or use its numbered control.
- Confirm that selection does not send another recognition request.
- Confirm that a matched popup shows the wine description, matcher score, image, and source link.
- Confirm that an unmatched bottle shows an explicit unmatched state.
- Close with Escape, the close button, and a backdrop click. Confirm focus returns to the selection control.
- Close and immediately open another bottle. Confirm a delayed close event does not clear the new popup.
- Request food recommendations for the selected wine. Confirm the request still uses our portal.
- Cancel matching, retry, replace the photo, reset, and switch modes.
- Simulate no detections, invalid masks, malformed matches, and an unavailable service. Confirm explicit states without fake results.
- Remove or invalidate matcher configuration. Confirm the temporary-unavailable view returns without an upload control.
- Check phone touch controls, zoom scrolling, the bottom sheet, dark mode, and reduced motion.

Automated checks cover group URL derivation, one-request matching, response limits, normalized boxes, malformed data, timeout, cancellation, selection, and stale results.
The owner-supplied examples have conversion details and hashes in `docs/assets.md`.
Manual camera and visual checks remain unverified unless explicitly recorded in the verification report.
