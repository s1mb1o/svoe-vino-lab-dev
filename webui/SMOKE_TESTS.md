# Smoke tests

## Automated checks

1. Run `npm run typecheck`.
2. Run `npm test` for API, result metadata, and photo search state checks.
3. Run `npm run build`.
4. Start the production server with `npm start`.
5. Run `npm run test:contract` against the production mock endpoint.
6. Run `npm run test:pwa` with `PLAYWRIGHT_MODULE` set against the production server.

The state tests check automatic submission, single-result resolution, metadata failures, cancellation, stale responses, retries, invalid files, and missing configuration.
The metadata tests check official source normalization, exact slug lookup, fixed image hosting, invalid records, response limits, and timeout handling.
The API health tests check URL derivation, response validation, network failure, and timeout behavior.
The PWA tests check the Nuxt module configuration, the update mode, both theme colors, icon and screenshot dimensions, and API cache exclusions.
The PWA browser check uses Chromium. It checks installability, the precache content, offline start after two visits, offline API failure, and a waiting service worker without a page reload after an update.
The search-discovery tests check the age overlay, canonical metadata, crawl files, permanent redirects, and static cache policy.
The contract check uses the unchanged official evaluator and its three images.
The contract check also checks the home page, compatibility redirects, metadata routes, image routes, manifest, service worker, and PWA icons.

## Manual browser checklist

- Open `/`. Confirm the photo search page has no catalog grid or filters.
- Check the layout on a phone and desktop.
- Confirm the shared bottle-scanner logo and `Что за вино?` name in the header and age gate.
- Check brand readability in both themes and beside the theme selector at 320px.
- Confirm the product name in the page title and app manifest.
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
- Open a fresh origin. Confirm the system palette and its current icon: sun for light, crescent moon for dark.
- Confirm that page load and system theme changes do not write `svoe-vino.theme.v1`.
- Click the theme icon. Confirm the opposite palette, the matching current icon, and the saved explicit preference.
- Reload after each click. Confirm the saved theme and matching icon.
- Change the system theme before an explicit choice. Confirm that the palette and icon follow the system.
- Change the system theme after an explicit choice. Confirm that the selected palette stays active.
- Check that existing `light` and `dark` preferences are retained and a legacy `system` value follows the system.
- Open a second tab. Change the theme in the first tab. Confirm that the second tab follows it.
- Check keyboard operation, reduced motion, and the header layout at 320px and desktop widths.
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
- Select a photo in the open installed app. Deploy a new build. Confirm that the page keeps the photo and does not reload.
- Close all app pages and reopen the app. Confirm that the new build is active.
- Check the browser install dialog on a phone and on desktop. Confirm the narrow and wide screenshots.
- Switch the selected theme. Confirm that browser theme metadata uses `#7b3528` in light mode and `#211e1c` in dark mode.
- While offline, submit a photo. Confirm a clear network error and no simulated result.
- Inspect service-worker cache storage. Confirm that it contains no `/api/`, `/v1/`, or uploaded photo response.

## Verification scope

The manual checklist is not a completed visual regression suite.
Physical camera operation and the real recognition service remain untested.
See `docs/verification-2026-09-15.md` for current results.

## Results on 2026-09-29

- Product identity: type checks, all 165 tests, and the production build passed. The header component preview passed both themes and the 320px layout. The logo loaded without a color filter and the theme selector remained accessible.
- Header theme selector: type checks, all 165 tests, and the production build passed.
- Header theme selector: the isolated component preview passed light/dark selection, reload persistence, tab synchronization, system-theme resolution, and header layout at 320px and desktop widths.
- Theme initialization: 12 combinations of stored preference, system theme, invalid preference, and blocked storage passed.
- The production page applied the system dark palette to the age overlay. Recognition flows were not repeated for this appearance change.
- Result-aware Abrau-Durso guide: type checks passed, all 165 tests passed in 13 files, and the production build passed.
- Product-line catalog images: the dark desktop dialog passed the visual check, type checks passed, all 164 tests passed in 13 files, and the production build passed.
- Taste inference audit and dish illustrations: type checks passed, all 163 tests passed in 13 files, and the production build passed.
- Taste passport and regional dishes: type checks passed, all 152 tests passed in 12 files, and the production build passed.
- PWA review fixes: type checks passed, and all 151 tests passed in 12 files.
- PWA review fixes: the production build passed with 22 precache entries.
- PWA review fixes: `npm run test:pwa` passed against the local production server.
- PWA review fixes: `npm run test:pwa` failed against the live `autoUpdate` build with a page reload after the update. This result confirms that the check detects the old behavior.
- PWA review fixes: the manifest, service-worker, icon, and screenshot assertions of `npm run test:contract` passed in a separate run.
- The full `npm run test:contract` stopped at the home-page assertion for `Проверяем подтверждение возраста`. The committed `AgeGate.vue` has no such text. This failure is older than the PWA review fixes.
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
- Open «Подобрать блюда». Confirm that three named dishes from three regional cuisines appear.
- Confirm that each dish shows either `КАТЕГОРИЯ ИЗ КАРТОЧКИ` or `ВЫВОД ПО СТИЛЮ`.
- Confirm that a source-backed dish names one pairing category from the resolved source card.
- Use the default example. Confirm images for the расстегай, чуду, and халюж.
- Confirm that each dish image has descriptive alternative text and a fixed 640 by 400 aspect ratio.
- Open «Рассказать об этикетке». Confirm the metadata grape name and illustrative Syrah and Viognier notice.
- Open «Паспорт вкуса». Confirm six taste dimensions and source or style labels on aroma families.
- Use Cabernet Sauvignon without a source description. Confirm the dataset label, 9,472-review sample count, source link, and `CC BY-NC-SA 4.0` license.
- Use the default example. Confirm the explicit message that its grape has no reliable aggregate match.
- Confirm that a sweet red wine uses the sweet-style analogue before a dry Cabernet analogue.
- Confirm that the international analogue includes a similarity, a difference, and a no-quality-comparison notice.
- Open «Путеводитель по линейке». Confirm the Abrau-Durso tiers and quality-rating notice.
- Confirm that all six nodes show distinct catalog bottle or can images instead of generic silhouettes.
- Confirm that «Удельное Ведомство Императорское, брют» shows the yellow-label `patched` image.
- Confirm that the other five nodes show their `main` images.
- Resolve one of the six mapped Abrau-Durso slugs. Confirm that its node shows `ВАШЕ ВИНО`.
- Confirm that the dialog heading says `ЛИНЕЙКА ВАШЕГО ПРОИЗВОДИТЕЛЯ`.
- Resolve an Abrau-Durso slug outside the six map nodes. Confirm that the result appears above the map without a collection tier.
- Resolve a wine from another producer. Confirm that Victor Dravigny shows `ПРИМЕР · ДЕМО`.
- Change map zoom. Select another node. Use the direction control to bring the current node into view.
- Confirm that the selected node exposes a normal source link.
- Close every dialog with its close button, Escape, and backdrop. Confirm focus restoration.
- Check the actions and dialogs at 390 px and on desktop in light and dark themes.

Focused automated tests cover age storage, storage failures, taste inference, dish diversity, source evidence, style analogues, source URLs, and one current map item.
The 2026-09-28 browser check covered dark desktop and 390 px mobile layouts.
The dish demo does not contain a browser location call.

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
