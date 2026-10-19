# Smoke tests

## Wine&Dine Merge landing

Verified locally on 2026-10-19: type checks, the production build, 94 required build checks, and the first-load bundle check passed. Twenty existing optional catalog checks were skipped. All 16 production browser layouts passed in Chromium and WebKit. Physical-device verification was not performed.

1. Follow `/hackaton` → `/ideas` → the Game invitation → `/game`. Check the page heading, header label, canonical URL, and back link.
2. Confirm the existing portal age gate on a fresh browser context.
3. Check Play links to `https://game.chtozavino.ru/` and the separate pouring link to `https://game.chtozavino.ru/?mode=pour`.
4. Select each region. Check the matching scene and menu. Use arrow keys, Home, and End. Check focus follows the selected tab.
5. Open and close each native FAQ disclosure with mouse and keyboard.
6. Check 320, 390, 768, and 1440 pixel layouts in both system themes. Check local SVG loading, complete words, and no horizontal overflow.
7. Run `scripts/check-game-landing-browser.mjs` with the browser environment in `docs/game-landing.md`. Preserve the screenshots and JSON result. Browser emulation does not establish physical-device acceptance.

## Bottle result spacing (#67)

Verified locally on 2026-10-19: 40 cases passed in Chromium and WebKit, with both themes, two image shapes, and all five widths below. The gap was 9 px on desktop and 10 px on mobile. No image, title, or portal link was clipped. All 469 unit tests passed; 20 optional catalog snapshot tests were skipped. Type checks, the production build, and the bundle check passed.

- Open `/` and upload a bottle photo. Confirm that the full bottle is above «Лучшее совпадение» with a visible gap.
- Repeat with a tall bottle image and a square image at 320, 390, 767, 768, and 1440 px in both themes.
- Use a long title such as «БЮРНЬЕ.КРАСНОСТОП сухое красное». Confirm that the title wraps inside the card and that the portal link stays fully visible.
- Confirm that the image stays below «02 / ВАШЕ ВИНО» and «Совпадение найдено». Keep the full bottle outline visible.

## Dish drag-and-drop and HEIC

1. Run `npm run test:dinner-uploads` with the browser environment in `docs/dinner-lens.md`. Check the desktop dark/light layouts and 320/390-pixel mobile layouts.
2. Drop JPG, JPEG, PNG, WebP, HEIC and HEIF files. Repeat with uppercase names and empty/generic MIME. Confirm one normalized JPEG recognition request per valid file and no wine cards before confirmation.
3. Use the picker and mobile camera with the advertised formats. Confirm HEIC orientation and no source metadata copying. Physical camera capture needs a device check.
4. Drag over nested panel content and leave the target. Confirm stable highlighting and reset after drop. Replace a photo during preparation or recognition; cancel or switch modes. The latest photo must win.
5. Drop an invalid renamed file, a truncated HEIC, multiple files or an oversized file. Confirm a useful error and no provider request. An empty drop or cancelled picker must preserve the current photo.
6. Confirm the decoder does not load for JPEG/PNG/WebP or first paint. Run the bundle check after building.

## Producer map index and page layout

1. Open `/lineup`. Confirm 19 cards with a bottle, the counts, and the materials date. Check 1440, 390, and 320 px in both themes.
2. Confirm that `/lineup` has no `x-robots-tag` header and is in `/sitemap.xml`. Confirm `noindex` on `/lineup/abrau-durso`.
3. Select a card. Confirm the map page. Select «Все карты производителей». Confirm the index.
4. On `/lineup/abrau-durso?wine=abrau-dyurso-victor-dravigny-bryut`, confirm that the page scrolls to the selected wine and that the map has no inner scroll bar.
5. Select a product at 1440 px. Confirm that the details open in the popup.
5a. Scroll down the map. Confirm that the group picker and the locate button stay at the window top and stop before the footer. Select a group in the picker. Confirm that its heading is below the toolbar.
6. Open the guide from a scan result. Confirm the pan and zoom canvas and the side card at 1440 px.
7. With VoiceOver and TalkBack, confirm the card names on `/lineup` and the popup heading on a map page.

## «Винный дневник»

1. Set `NUXT_ACCOUNT_ENDPOINT` and `NUXT_ACCOUNT_TOKEN`. Confirm «Дневник» in the header on `/`, `/shelf`, `/ideas`, and `/android`. On a 360 px phone confirm the book icon and no horizontal scroll.
2. Open `/account`. Request a code for a test address, enter it, choose a username, and confirm that «Создать дневник» stays disabled until both boxes are checked. Confirm «Вы вошли как …».
3. In the browser storage panel confirm `__Host-cv_session` with HttpOnly, Secure, and SameSite=Lax, and no account token in `localStorage`.
4. Reload: the session stays. «Выйти»: the cookie is gone. Request a second code within a minute: «Слишком много попыток…». Enter a wrong code: «Неверный код. Осталось попыток: N.»
5. «Войти с Яндекс ID»: the browser opens `oauth.yandex.ru`. After the consent the browser returns to `/account` (or the sign-up step for a new identity). The address bar never shows `code=` on a page.
6. Log in, wait a day, and open `/account` again: still logged in. «Удалить аккаунт» shows «Удалить аккаунт <имя> и все данные?»; «Удалить навсегда» deletes it at once: «Аккаунт удалён». The cookie `__Host-cv_session` has an expiry of about 400 days.
7. Stop the account service. `/` and the scanner work; `/account` shows «Дневник временно недоступен».
8. Clear `NUXT_ACCOUNT_ENDPOINT`. The header has no link; `/api/account/config` returns `{"enabled":false,...}`.
9. In the network panel confirm no `mc.yandex.ru` request when a visit starts on `/account`.
10. With `TELEGRAM_BOT_USERNAME` set in the account service: «Привязать мессенджер» → «Telegram» shows «Открыть Telegram» with `https://t.me/<bot>?start=link_…`. Confirm in the bot. Back on the page, Telegram is under «Связанные мессенджеры» with «Отвязать», and «Способы входа» does not list it. «Отвязать» removes it.
11. With `MAX_WEBAPP_KEY` in the account service and `NUXT_ACCOUNT_MAX_APP_LINK` on the site: «Привязать мессенджер» → «MAX» shows the QR code and «Открыть в MAX». Open the link on a phone. In MAX log in by email code and confirm that the page names your MAX account. «Привязать»: «MAX привязан к дневнику.» On the site MAX is under «Связанные мессенджеры».
12. Open `https://max.chtozavino.ru/max` in an ordinary browser: only «Откройте дневник в MAX», no form. `https://max.chtozavino.ru/` redirects to `/max`; `/account`, `/shelf`, `/sw.js`, and `/api/account/yandex/start` return 404 on that host; `chtozavino.ru` still asks for HTTP Basic.
13. «Токены приложений» → «Создать токен»: the page shows the token once with the MCP configuration. «Готово» hides it; a reload does not show it. `curl -H 'Authorization: Bearer <token>' https://chtozavino.ru/api/app/v1/profile` returns the username (after the Caddy exemption). «Отозвать»: the same call returns 401.

## Wine for a dish

Verified locally on 2026-10-19: 319 unit tests passed, 20 existing optional catalog snapshot tests skipped; type check, production build and bundle check passed. Five browser configurations passed in Chromium and WebKit with dark/light palettes and 320/390/1440-pixel viewports. Real gx10 checks exhausted all pages for ribeye (8 wines), Olivier (12) and king crab (12), and completed one photo recognition with confirmation. Physical camera capture remains a manual device check.

1. At desktop widths and at 320/390-pixel mobile widths, confirm three visible mode links: «Одна бутылка», «Вся полка», «Вино к блюду». Confirm touch targets and no horizontal scrolling.
2. Open `/dish`. Enter a dish or select the mobile camera/file input. Confirm that a photo proposes a label but shows no wine cards before confirmation.
3. Correct the dish, change a sauce, or select a broad category. Confirm that explicit no-cream and still-wine choices reach the service correctly.
4. Submit and follow «Показать ещё» to exhaustion. Confirm source links, explanations, unique wine IDs and later discovery choices. Repeat for the three original dishes in `docs/dinner-lens.md`.
5. Change a sauce after a result. Confirm that old cards and the old cursor disappear. Switch modes during a request and confirm that a late response cannot restore them.
6. Disconnect the service and retry. Confirm a useful error, no mock result, and preserved cards when only a continuation fails.
7. Check the browser HTML, `/api/config`, and API responses for absence of the private endpoint, token, model receipts and diagnostics.
8. Run `npm run test:dinner` with Playwright and the documented live-check options. Check an actual phone camera separately.
9. Type an unknown dish with no photo. Confirm visible clarification and focus on the category. Confirm that a typed correction clears the old category, that a failed selection keeps a corrected photo label, and that recognition retry appears only for a failed recognition. After the last discovery page, focus must reach its first new wine heading.

## Producer map loading

1. After `npm run build`, run `npm run test:bundle`. Confirm that `/` and `/shelf` load no map data at first paint.
2. Open `/` with the browser network panel. Confirm that no producer map chunk loads.
3. Recognize an Abrau-Durso wine. Move the pointer over «Путеводитель по линейке», or focus it with Tab. Confirm that one map chunk loads.
4. Open the guide. Confirm that the recognized wine is selected and centered. Repeat from a shelf result.
5. Block the map chunk request and open the guide for another producer. Confirm «Не удалось загрузить карту». Unblock the request, select «Повторить», and confirm the map.
6. With VoiceOver and TalkBack, confirm that «Загружаем карту линейки…» and the failure message are announced.
7. Open `/lineup/abrau-durso` with JavaScript disabled. Confirm that the server renders the map.

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

## Eight producer review resolution, 2026-10-17

Check repeated record labels, exact linked identities, neutral unconfirmed groups, the Novy Svet and Soyuz conflict badges, and gray bottle visibility in both themes. Verify the 767/768 px Soyuz transition and the longest Novy Svet title. Verify that a gray addition has no portal link. Run both producer and Abrau browser suites.

## soyuz-vino review correction, 2026-10-17

Check historical brands at rank zero, the red Lac d’Azur conflict badge, package silhouettes, the alcoholic Perle can, and the 767/768 px transition.

## valery-zakharyin review correction, 2026-10-17

Check all four reserve entries. Confirm that the group description identifies distinct collections.

## chateau-pinot review correction, 2026-10-17

Check the confirmed Gravity labels and the seven unconfirmed blends. Confirm that neutral positioning does not change their portal links.

## esse review correction, 2026-10-17

Open the four corrected exact slugs. Check Unplugged membership, neutral positioning, separate duplicate-card labels, and the gray YELLOW GLOVES entry.

## sober-bash review correction, 2026-10-17

Check all six Грани products and all four amphora products. Keep separate catalog records distinct.

## belbek review correction, 2026-10-17

Check the rose blend descriptions and the unresolved card. Keep the Reserve addition selectable with no portal link.

## agora review correction, 2026-10-17

Check BLUSH MIRAGE, historical Yachting ageing, CUVEE source wording, and VINTAGE without claims about other series.

## novy-svet review correction, 2026-10-17

Check the two aged entries, two unconfirmed varietal entries, rank-zero special cuvees, and the limited Коронационное card.

## Sober Bash amphora source, 2026-10-17

Verify the Грани · Амфора source against the official Грани collection. Retain the four amphora product identities and their selection behavior.

## Novy Svet absence scope, 2026-10-17

Verify the Коронационное addition against the 44 exact Новый Свет. Дом шампанских вин catalog records. A display-name alias MUST NOT prove absence.

## Eight producer map verification, 2026-10-16

Check all eight routes in docs/validation/eight-producer-maps.md. Verify the selected catalog identity, bottle image, group, price guidance, portal link, and mobile popup. Select each gray addition and verify that it has local details but no portal link. Check 320 px, 390 px, desktop, both themes, and return to the map.

## Союз-Вино, 2026-10-16

Open /lineup/soyuz-vino with a linked wine slug. Check exact selection, bottle scale, desktop details, mobile popup, portal action, and return to the map. Check any null-slug additions without a portal link.

## AGORA WINERY, 2026-10-16

Open /lineup/agora with a linked wine slug. Check exact selection, bottle scale, desktop details, mobile popup, portal action, and return to the map. Check any null-slug additions without a portal link.

## Собер Баш, 2026-10-16

Open /lineup/sober-bash with a linked wine slug. Check exact selection, bottle scale, desktop details, mobile popup, portal action, and return to the map. Check any null-slug additions without a portal link.

## Бельбек, 2026-10-16

Open /lineup/belbek with a linked wine slug. Check exact selection, bottle scale, desktop details, mobile popup, portal action, and return to the map. Check any null-slug additions without a portal link.

## Новый Свет, 2026-10-16

Open /lineup/novy-svet with a linked wine slug. Check exact selection, bottle scale, desktop details, mobile popup, portal action, and return to the map. Check any null-slug additions without a portal link.

## Валерий Захарьин, 2026-10-16

Open /lineup/valery-zakharyin with a linked wine slug. Check exact selection, bottle scale, desktop details, mobile popup, portal action, and return to the map. Check any null-slug additions without a portal link.

## Шато Пино, 2026-10-16

Open /lineup/chateau-pinot with a linked wine slug. Check exact selection, bottle scale, desktop details, mobile popup, portal action, and return to the map. Check any null-slug additions without a portal link.

## ESSE, 2026-10-16

Open /lineup/esse with a linked wine slug. Check exact selection, bottle scale, desktop details, mobile popup, portal action, and return to the map. Check any null-slug additions without a portal link.

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
