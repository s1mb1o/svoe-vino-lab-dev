# Smoke tests

## Mode pages

- Open `/`. Confirm «Одна бутылка», the title «Найти вино по фото — Что за вино?», and `aria-current="page"` on its link.
- Follow «Вся полка». Confirm the URL `/shelf`, the title «Найти вино на полке по фото — Что за вино?», and the canonical URL `https://chtozavino.ru/shelf`.
- Confirm that the switch discards the photo and the result of the previous mode. Use browser Back to return to `/`.
- Confirm that `/sitemap.xml` lists `/shelf`.
- With VoiceOver and TalkBack, confirm that the switch is a navigation named «Режим поиска вина» and that the current page is announced.

## HEIC uploads

Run these checks only with a matcher that has HEIC support (#24, #44).
With a matcher without HEIC support, a HEIC upload MUST show «Не удалось прочитать HEIC. Сохраните фото как JPEG.» in both modes.

- In both modes, confirm the hint «JPEG, PNG, WebP, HEIC · до 10 МБ».
- In Chrome, upload a `.heic` file. Confirm the text «Браузер не может показать это фото, но мы всё равно его проверим.» and a match.
- In «Вся полка», confirm that the result preview replaces the text.
- On an iPhone, upload from the photo library and from the camera. Confirm a match.
- Upload an AVIF file. Confirm HTTP 415 and the message about the formats.

## Yandex.Metrika

Release `10632011` passed these checks on staging and production on 2026-10-06.
All 169 tests, type checks, and the Linux build passed.
The real Metrika loader and both verified page-view requests returned HTTP 200.
The presentation files and video remain byte-identical to the previous release.

- Request `/`, `/android`, `/ideas`, `/presentation`, and `/hackaton`.
- Confirm one counter initialization script in each server-rendered HTML response.
- Confirm every supplied initialization option and counter ID `113460637`.
- Confirm one body-start noscript image with `https://mc.yandex.ru/watch/113460637`.
- Open a page in a new browser context. Confirm one asynchronous Metrika loader.
- Navigate through internal links. Confirm one `hit` for each successful URL change.
- For each `hit`, confirm that `document.title` at the call is the title of the new page.
  Check a link from `/ideas` to `/android`, browser Back, and the in-page anchor `#implemented`.
- Open `/IDEAS?utm_source=campaign` and follow the link to `/ideas`. Confirm one `hit` with the `/ideas` title.
- Confirm that app mounting does not send a second initial page view.
- Block the external Metrika loader. Confirm that the page and navigation still work.
- Confirm the existing age gate, service health, and presentation artifacts.

## Abrau-Durso still-wine completion

1. Open every new exact slug from `docs/product-line-maps/abrau-durso/catalog-extension.json`.
2. Confirm that the product is selected, its group is expanded, and its image loads without clipping.
3. Check the five still-wine groups at desktop, 390 px and 320 px widths in both themes.
4. Open the mobile popup. Confirm the exact portal URL and return to the same map position.
5. Confirm that the old 52 sheet products and all three aliases still resolve.
6. Confirm that `rozovoe-polusladkoe-2` remains unplaced after recognition, as requested by the owner.
7. Delay the Playfair font response on initial load. Confirm that the selected wine stays centered after the font loads.

## Additional producer maps

Check `official-5000-cabernet-sauvignon`, `wine-ona-skazala-da`, `wine-beloe-polusladkoe`, and all eight restored Zolotaya Balka images.
Check their full outlines on light and dark backgrounds. Compare bottle height inside one group.

1. Open `/lineup/<producer-id>?wine=<exact-slug>` for each registered producer.
2. Confirm that the exact product is selected and its collection is expanded.
3. Confirm that a gray product opens details without a portal link.
4. Expand every group. Confirm that every current product has a bottle image. Block one image request. Confirm that «Нет изображения» replaces only the failed image.
5. Change the producer with the preview selector. Confirm that old selection and popup state are cleared.
6. At 390 px, open details, return to the map, and confirm that the map position is preserved.
7. Repeat in light and dark themes. Check the 320 px layout and desktop side card.
8. Run `npm run test:line-map` and `npm run test:producer-maps` with `PORTAL_ORIGIN` and `PLAYWRIGHT_MODULE` set.

## Hackathon direct URL

Release `0c2f964` passed the checks below on staging and production on 2026-09-29.
All 169 existing tests, type checks, and the Linux build passed.

- Request `/hackaton`, `/hackaton/`, and `/hackaton?source=organizers`. Confirm HTTP 200.
- Confirm the `X-Robots-Tag` header and HTML robots metadata contain `noindex, nofollow, noarchive`.
- Confirm `robots.txt` contains `Disallow: /hackaton` and still advertises the sitemap.
- Confirm `sitemap.xml` omits `/hackaton` and keeps the other public pages.
- Confirm `/`, `/android`, `/ideas`, and `/presentation` have no links to `/hackaton`.
- Confirm those public pages do not receive the hackathon noindex header or metadata.
- Open `/hackaton` directly, confirm the age gate, and check the platform anchors and links.
- Navigate from `/hackaton` to `/ideas`. Confirm the robots metadata is removed after navigation.

## Hackathon publication verification, 2026-09-29

Release `600fd2a` passed 169 tests, type checks, and the Linux production build.
Staged and public browser checks passed at 320, 390, 768, and 1440 pixels in both themes.
The age gate, both WebApp screenshots, platform anchors, Android download, Telegram link, and related page links passed.
All screenshots loaded. The pages had no horizontal overflow or browser errors.
The public APK GET response has the expected attachment name, MIME type, byte count, and SHA-256.
The existing presentation page and both presentation file hashes remain valid.
Public service health and upstream availability passed.

## Ideas beyond recognition

- Open `/ideas` in a new profile. Confirm that the age gate blocks interaction.
- Confirm one H1 and the section order: implemented, demo, mock.
- Check the section links and counts: 3 implemented, 4 demos, 6 mockups.
- Confirm that implemented cards identify the relevant application.
- Open all four example dialogs. Close them with Escape, the close button, and a backdrop click.
- Confirm that focus returns to the dialog opener.
- Change the example wine. Confirm that the taste and label dialogs use that wine.
- Confirm that unsupported producers show an unavailable state with a separate Abrau-Durso preview link.
- Confirm that mockups have no working search, shopping, playback, quiz, or save controls.
- Check 320, 390, 768, 1024, and 1440 pixel widths in both themes without horizontal overflow.
- Confirm that images load and all internal page links work.
- Confirm that demo interactions do not request matcher, retailer, or location endpoints.
- Confirm `/ideas` links on `/hackaton` and in the shared footer.
- Confirm one canonical URL, `https://chtozavino.ru/ideas`, and a sitemap entry.


## Presentation files

Run `PLAYWRIGHT_MODULE=<path>/node_modules/playwright/index.mjs npm run test:presentation`
against a running server. Set `PORTAL_ORIGIN` to override `http://127.0.0.1:8153`.
The check saves local review screenshots in the ignored `reports/presentation/` directory.

- Open `/presentation` in a new profile. Confirm that the age gate blocks interaction.
- Accept the age gate and confirm one heading and two file links.
- Confirm that `Видео о проекте` appears below the file links.
- Confirm that GitHub and Google Drive cards appear side by side below the video and use the same styles as the presentation cards.
- Confirm that the resource cards use the exact owner-supplied URLs and open in new tabs.
- Confirm the presentation has no link to the organizers' `/hackaton` page.
- Without `/presentation/video.mp4`, confirm the placeholder `Видео появится после записи` and no broken player controls.
- With a valid recording, confirm native playback controls, inline phone playback, and no autoplay.
- Check that PowerPoint and PDF stay side by side at 320, 390, 768, and 1440 pixel widths without horizontal overflow.
- Check that the page stays white with a saved dark theme. Return to `/hackaton` and confirm that the saved theme still applies.
- Download the PowerPoint and confirm the filename is `chtozavino-presentation.pptx`.
- Open the PDF link in a new tab. Confirm that the PDF has 27 pages (presentation v14).
- Confirm that both file URLs return HTTP 200, the correct content type, and the same bytes as their public files.
- Confirm that the PowerPoint public copy matches the owner-supplied source.
- Build the production output and repeat the file checks against the production server.
- Confirm that the canonical URL is `https://chtozavino.ru/presentation`.
- Open the presentation from the link on `/hackaton`.

## Hackathon landing page

- Open `/hackaton` in a new browser profile and confirm the age gate.
- Accept the age confirmation. Confirm one H1 and three platform sections.
- Check widths of 320, 390, 768, 1024, and 1440 pixels in both themes.
- Confirm that both WebApp screenshots load, stay visible, and open at full size.
- Follow each platform anchor and confirm that it reaches the correct section.
- Open WebApp and confirm that the photo scanner loads at `/`.
- Confirm that the Android section mentions underground parking and local recognition.
- Confirm that the APK link uses the configured URL and shared release file name.
- Follow `О приложении` and confirm that `/android` loads.
- Confirm that the bot links use `https://t.me/ChtoZaVinoBot`.
- Confirm that WebApp and Telegram show their internet requirement.
- Confirm that the page tells visitors to install Android before going offline.
- Confirm that the page has one canonical URL, `https://chtozavino.ru/hackaton`.
- Confirm that `/sitemap.xml` omits `/hackaton`.

## Android landing page

- Open `/android` in a new browser profile.
- Confirm that the 18+ overlay blocks interaction and keeps the page content rendered.
- Accept the age confirmation.
- Confirm that the hero states offline operation and shows light and dark application
  screenshots.
- Confirm that the page shows image search, QR, barcode, on-device processing, 2,093
  wines, automatic acceleration, history, themes, and Android 9 support.
- Confirm that the page labels version 0.1.4 as a test version.
- Confirm that the first and last download actions use
  `/downloads/chtozavino-0.1.4-debug.apk` by default.
- Confirm that the local download response uses
  `application/vnd.android.package-archive`.
- Confirm that the attachment name is `chtozavino-0.1.4-debug.apk`.
- Confirm that a missing configured APK returns HTTP 404.
- Confirm that the header links from `/` to `/android` and back.
- Confirm that the page has one visible H1 after the age overlay closes.
- Confirm that the page works at 320 pixels and at a desktop width.
- Confirm that all page sections use the light and dark themes.
- Confirm that reduced-motion mode removes hover motion.
- Confirm that the canonical URL is `https://chtozavino.ru/android`.
- Confirm that the page publishes `SoftwareApplication` structured data.
- Confirm that the sitemap includes `/android`.

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

- Android landing page: type checks passed, all 169 tests passed in 14 files, and the
  production build passed.
- Android landing page: the local APK route returned HTTP 200 with the Android package
  content type, 576,503,269-byte content length, and the versioned attachment name.
- Android landing page: an invalid APK file name returned HTTP 404.
- Android landing page: the rendered response contained the unique canonical URL and
  the `SoftwareApplication` structured data.
- Android landing page: all six public WebP screenshots matched the verified Pixel 8
  source files byte for byte.
- Android landing page: desktop light and mobile light and dark layouts passed a visual
  check.
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
- Run the checks in the “Producer product-line map” section for graph coverage, selection, links, and navigation.
- Close every dialog with its close button, Escape, and backdrop. Confirm focus restoration.
- Check the actions and dialogs at 390 px and on desktop in light and dark themes.

Focused automated tests cover age storage, storage failures, taste inference, dish diversity, source evidence, style analogues, source URLs, graph identity, aliases, and product selection.
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

## Producer product-line map

1. Open `/lineup/abrau-durso`. Confirm the age gate. Check light and dark themes.
2. Check desktop, 390 px, and 320 px widths. Confirm that the page has no horizontal overflow.
3. Select a group. Select a linked product. Check the description and portal link.
4. Select a gray product. Check the description. Confirm that no portal link exists.
5. Recognize an Abrau-Durso wine. Open the guide. Confirm that its group opens and its product is selected.
6. Use the legacy Victor Dravigny slug. Confirm that the standard Brut product is selected.
7. Select another product. Return to the map. Confirm that zoom and canvas position remain unchanged.
8. Use the locate control. Confirm that the initial product is selected and visible again.
9. Drag with a mouse. Scroll with touch. Change zoom. Check the outermost groups at both zoom limits.
10. Open the guide with the keyboard. Use group controls and product controls. Press Escape. Confirm that focus returns to the opener.
11. Open the guide from a shelf result. Confirm that closing the guide retains the shelf result.
12. Use an unknown Abrau-Durso slug. Confirm that the separate card has no inferred tier.
13. Use another producer. Confirm the unavailable state and the explicit preview link.
14. Check that the preview uses noindex headers and does not claim recognition.

15. At 844 by 390 and 667 by 375 px, select linked and gray products. Confirm that detail actions remain reachable.
16. At 700, 701, 767, and 768 px, confirm that the page has no horizontal overflow.
17. On mobile, confirm that the initial product is selected and that no bottom card appears. Tap «О выбранном вине» or a product. Confirm a centered modal popup with full details. Close with Return, the close control, Escape, and the backdrop. Confirm the same selection, canvas position, scale, and opener focus.
18. In the mobile popup, use Tab and Shift+Tab. Confirm that focus stays inside the popup. Confirm that content scrolls and that actions remain reachable at 320 px and in short landscape windows.
19. Resize across 767/768 px with the popup open. Confirm that the desktop side card works and that no modal backdrop or scroll lock remains.
20. In WebKit, close the wine popup, the map dialog, and then the shelf card. Confirm that each close affects only the top dialog and restores its explicit opener.

21. At 800 by 650 and 1440 by 720 px, select the Cuvée Alexander II gift box. Confirm that the description has nonzero height and all actions remain reachable in the preview and scanner dialog.

Validation completed on 2026-10-16: all 176 tests, type checks, and the production build passed.
Chromium passed desktop and mobile checks in both themes.
WebKit passed the phone, landscape, breakpoint, and nested-dialog checks.
Read `docs/reviews/2026-10-15-product-line-map-resolution.md` for the evidence and limits.

Mobile popup validation completed on 2026-10-16:
Both complete Chromium and WebKit suites passed against the rebuilt preview.
The checks cover 320/390 px light and dark layouts, close/reopen, linked and gray products,
reading reset, 767/768 px transitions, short viewports, and scanner/shelf integration.
The three-dialog shelf case retains Tab, Shift+Tab, and programmatic focus inside the popup.
Closing each dialog restores its opener and the saved map/page scroll state.
The final browser runs reported no browser errors or hydration warnings.
The 176 unit tests, type checks, and production build passed.
Screenshots use browser emulation. These checks do not replace physical-device testing.

## Дербент Вино map

Open `/lineup/derbent-vino?wine=caucasian-dzharag`.
Check the selected catalog wine, a gray product, and the mobile popup.

## Золотая Балка map

Open `/lineup/zolotaya-balka?wine=balaklava-bryut-rezerv`.
Check the selected catalog wine, a gray product, and the mobile popup.

## Alma Valley map

Open `/lineup/alma-valley?wine=alma-valley-alma-graviti-pino-nuar-merlo-kaberne-sovinon-krasnoe-suhoe-14`.
Check the selected catalog wine, a gray product, and the mobile popup.

## Инкерман map

Open `/lineup/inkerman?wine=inkerman-muskatnoe-beloe`.
Check the selected catalog wine, a gray product, and the mobile popup.

## Массандра map

Open `/lineup/massandra?wine=aligote-avtorskoe`.
Check the selected catalog wine, a gray product, and the mobile popup.

## Ведерниковъ map

Open `/lineup/vedernikov?wine=rkacziteli-beloe-suhoe`.
Check the selected catalog wine, a gray product, and the mobile popup.

## ЗМВ Коктебель map

Open `/lineup/koktebel?wine=koktebel-casa-belyj-kupazh`.
Check the selected catalog wine, a gray product, and the mobile popup.

## Фанагория map

Open `/lineup/fanagoria?wine=cru-lermont-risling`.
Check the selected catalog wine, a gray product, and the mobile popup.

## Кубань-Вино map

Open `/lineup/kuban-vino?wine=aristov-anima-millesimato`.
Check the selected catalog wine, a gray product, and the mobile popup.

## Мысхако map

Open `/lineup/myskhako?wine=glera-manno`.
Check the selected catalog wine, a gray product, and the mobile popup.

## Expanded producer validation

Read `docs/validation/producer-maps.md` for the latest complete check.
Run `npm run test:producer-maps` in Chromium and WebKit.
Check the largest groups at 320 px and 1440 px.
Open a map from a controlled scanner result. Keep the recognized marker after another selection.
Simulate an image HTTP 404. Confirm the placeholder and the original portal link.

## Transparent product images

Open `/lineup/derbent-vino?wine=monte-garu-beloe-bryut`.
Check Monte Garu on the canvas and in the selected-wine panel. Confirm that no white rectangle surrounds the bottle.
Repeat at 1440 px in light theme and 390 px in dark theme.
Select Monte Garu rose semi-sweet. Confirm that the bottle scale matches the other bottles.
On mobile, open and close the product popup. Confirm that the map position and selection remain unchanged.
Check one edited image in each of the six producers listed in `docs/validation/product-image-cutouts.md`.
Check the two source-conflict placeholders. The Fanagoria catalog link remains available. The gray 5000 product still has no portal link.

Open `/lineup/fanagoria?wine=fanagoriya-dekanter-rkatsiteli-2019-beloe-suhoe-135`.
Check the complete Rkatsiteli 2019 outline on flat light and dark backgrounds.
Confirm that no opaque gray or white stripe remains outside the right contour.
Repeat in the desktop detail panel and mobile popup.

Open `/lineup/fanagoria?wine=fanagoriya-dekanter-saperavi-2017-krasnoe-suhoe-135`.
Check both sides of the neck on flat light and dark backgrounds.
Confirm that no white rectangle remains outside the bottle.
Check the desktop detail panel and the mobile popup.
Read `docs/validation/lineup-image-visual-review.md` before accepting a complete lineup image review.

## Visible bottle scale

Open `/lineup/fanagoria?wine=fanagoriya-100-ottenkov-krasnogo-pino-nuar-krasnoe-suhoe-135`.
Compare Pinot Noir with the other 100 Shades bottles. Check the actual outline height.
Check the Formula Q, Blanc de Blancs and Ice Wine groups.
Repeat in group previews, expanded nodes, desktop details and the mobile popup.
Check both themes. Confirm that no cap, base, box or label is clipped.
Check a gray product and an image HTTP 404. The placeholder and portal rules MUST remain correct.
