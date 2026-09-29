# Research log

## Hackathon direct URL, 2026-09-29

The owner requested crawler exclusion and sitemap removal for `/hackaton`.
The page is intended for organizers who receive the direct URL.
Remove inbound links from the presentation page, ideas page, and shared footer.
Keep the route available without adding a login requirement.
Add `Disallow: /hackaton`, HTML robots metadata, and the `X-Robots-Tag` header.
Apply the header to both the base path and its slash form.
Crawler instructions are voluntary. They do not restrict visitors with the URL.
Google cannot read noindex when robots.txt blocks a page. A previously discovered
URL can therefore remain in results. This change prioritizes the requested crawl block.
Reference: https://developers.google.com/search/docs/crawling-indexing/block-indexing


## Hackathon landing publication, 2026-09-29

The owner requested deployment at `https://chtozavino.ru/hackaton`.
Release `600fd2ae25a3eab4d338b2cd3dccbd21e5435b2e` starts from production revision `8d07fad`.
It publishes the landing, its linked Android and ideas pages, and the APK download route.
The current presentation page and its files remain unchanged.
The APK package metadata and signature passed verification.
The current 0.1.4 APK has 576,503,447 bytes and SHA-256 `fc4cf0f44b8fefcff5286b04746efb7fa44b9742ec6df282aa0cc959f6777ea2`.
The release metadata now matches that artifact.
All 169 tests, type checks, and the Linux build passed on Princess.
Staged and public browser checks passed at 320, 390, 768, and 1440 pixels in both themes.
The checks cover the age gate, screenshots, anchors, linked pages, metadata, and the APK GET response.
No browser errors or hydration warnings occurred.
Public APK and presentation file SHA-256 values match the verified sources.
The scanner health, upstream mode, recognition availability, and shelf availability remain active.
The previous release remains available for rollback. The staging service was stopped.
See `<workspace>/deploy/princess/webui.md` for server paths and the deployment record.

## Presentation project card, 2026-09-29

The owner requested a wide card below the resource links.
The card uses the full content width and links to `/hackaton` in the same tab.
The card reuses the presentation file card styles.
The current production release does not include `/hackaton`.
Published release `8d07fad` with the card. Publication of the target page and its related pages remains a separate scope decision.
Local type checks and the production build passed. All 165 release tests, type checks, and the Linux build passed on Princess.
Browser checks confirmed the full card width, placement, destination, and no overflow at 320, 390, 768, and 1440 pixels.
The phone and desktop captures were visually inspected. Both presentation file hashes and service health remain valid.

## Presentation resource links, 2026-09-29

The owner requested GitHub and Google Drive links below the presentation video.
The cards reuse the presentation file grid and card styles.
Both links use the exact supplied URLs and open in new tabs with `noopener noreferrer`.
The content of the linked repository and folder is not copied or embedded.
Published release `dbdd3b6` from the isolated production branch.
All 165 release tests, type checks, and the Linux build passed.
Public browser checks confirmed both URLs, new tabs, placement below the video, matching card styles, and no horizontal overflow at 320, 390, 768, and 1440 pixels.
The phone and desktop captures were visually inspected.

## Presentation video, 2026-09-29

The owner requested a video below the presentation links at `/presentation/video.mp4`.
The owner will record the video later.
The page uses a native video player with metadata preload, controls, and inline phone playback.
A media error replaces the player with `Видео появится после записи`.
The future file belongs at `public/presentation/video.mp4` and stays outside Git.
The release must be rebuilt after the file is added because Nitro indexes public assets during the build.
No placeholder recording or external video service is used.
Type checks and the production build passed.
The browser check passed at four widths in both themes with the recording absent.
A temporary local MP4 verified that metadata load replaces the placeholder and that playback works without autoplay.
The temporary test clip is not part of the application or release.
Published release `c615490` on the existing `codex/presentation-release` branch.
All 165 release tests, type checks, and the Linux build passed before activation.
The public browser check passed at four widths in both themes. Both presentation file hashes still match.

## Presentation publication, 2026-09-29

The owner requested deployment after reviewing the presentation page.
Published revision `36fb8e2d824d10bb5b8dcfed6ebcf67e5d05e837` from branch `codex/presentation-release`.
The isolated release starts from production revision `459625f` and adds the presentation page.
Other pending Web UI pages remain in this working tree.
The presentation logo now returns to the deployed scanner at `/`.
All 165 tests in that release, type checks, and the Linux production build passed on Princess.
Staged and public file checks confirmed both content types and matching SHA-256 hashes.
The public browser check passed at four widths in both themes with no browser errors.
Health, upstream recognition, and shelf availability remained active.
The previous release remains available for rollback. The temporary staging service was stopped.
The deployment record is `<workspace>/deploy/princess/webui.md`.

## Presentation files, 2026-09-29

The user requested `/presentation` with two adjacent links to the supplied PowerPoint and its PDF version.
The route already contained a browser slideshow.
Decision: replace that view with the requested file links.
A local copy of the previous page and its browser check remains in `reports/presentation-files/`.
The PowerPoint source is `../../svoe-wino-hackaton/presentation/chtozavino-presentation.pptx`.
No PDF existed in the source presentation directory.
LibreOffice exported all 49 slides from an unchanged copy of the supplied PowerPoint.
The PDF preserves the source content, including its draft and template slides.
All 49 PDF pages were rendered and inspected in contact sheets.
The public files are in `public/presentations/` and stay outside Git.
The production build includes the public files. A fresh checkout requires the documented preparation commands.
The PowerPoint link downloads the file. The PDF link opens a new tab.
The page keeps the shared age gate and the existing white presentation palette.

Type checks, all 169 existing tests, and the production build passed.
The sandbox blocked the HTTP test server. The test suite passed with loopback access.
The production browser check passed at 320, 390, 768, and 1440 pixels in both themes.
Both file responses returned HTTP 200 with their correct content types and matching SHA-256 hashes.
The source PowerPoint and public copy also passed a direct byte comparison.
The PowerPoint download, age gate, canonical URL, and landing-page navigation passed.
No browser errors or hydration warnings occurred.
The 320-pixel and 1440-pixel page captures were visually inspected.

## Ideas beyond recognition, 2026-09-29

The user requested a landing page for ideas beyond recognition.
The user specified implemented features first, demos second, and mockups last.
Decision: add `/ideas` and keep the scanner at `/`.
The feature inventory from 2026-09-28 provides the initial concept list.
The current result component and specification determine the demo status.
The four result actions remain demos even when metadata rules are implemented.
The implemented section covers source-card navigation, Android local history, and Telegram feedback.
The mock section uses static interface sketches for six future scenarios.
The page labels each status and identifies application-specific limits.
The demo area reuses `WineExperiences` with three existing local wine cards.
The page does not need recognition or an external API to open a demo.
The page reuses existing image assets and the shared light and dark palettes.

Type checks, all 169 existing tests, and the production build passed.
The first test run could not open a loopback socket in the sandbox.
The same tests passed with local socket access.
Chromium checks passed at 320, 390, 768, 1024, and 1440 pixels in both themes.
The checks covered age gating, section order and counts, metadata, anchors,
all four dialogs, example selection, focus return, backdrop close, images,
horizontal overflow, network scope, and internal navigation.
A 320-pixel overflow from the rotated hero image was fixed before the final check.
No browser errors or hydration warnings occurred.
Local review captures are in the ignored `reports/ideas/` directory.
The desktop, narrow-phone, and dark-theme captures were visually inspected.


## Browser presentation, 2026-09-29

The user requested a presentation page based on `/hackaton`.
The user then specified a white background.
Decision: create `/presentation` as a browser presentation with five slides.
Decision: use a local white palette and preserve the saved site theme.
The cover uses an existing catalogue bottle image.
The application slides reuse the landing screenshots and the labeled Telegram scenario.
No new recognition result, performance metric, or external asset was created.
The final slide reuses the shared Android release metadata and configured APK URL.

The presentation keeps the shared age gate.
Keyboard navigation must ignore the gate and editable controls.
The slide index is bounded. URL fragments allow direct links and reloads.
On small screens, the active slide scrolls while the controls remain visible.
Horizontal touch gestures change slides. Vertical gestures preserve normal scrolling.
The fullscreen control appears only when the browser supports the API.

Type checks, all 169 existing tests, and the production build passed.
The presentation browser check passed at 1920x1080, 1440x900, 1366x768, 1024x768,
768x1024, 390x844, and 320x740.
All desktop slides fit without scrolling. Phone slides scroll inside the fixed controls.
The white palette remained active with a saved dark theme. The dark theme returned on the landing page.
The production checks covered age gating, keyboard navigation, touch events, stable
fragments, reloads, fullscreen entry and exit, image decoding, metadata, and links.
No browser errors or hydration warnings occurred in the production check.
Desktop and mobile slide screenshots were inspected in `reports/presentation/`.

## Hackathon landing page, 2026-09-29

The user requested `/hackaton` with WebApp, Android App, and Telegram Bot sections.
The WebApp section MUST show desktop and mobile screenshots together.
The Android section MUST highlight recognition without internet, including parking.

The existing manifest screenshots show the previous header identity.
Decision: capture the current local WebApp in light mode for the landing page.
Decision: keep these captures separate from the manifest screenshots.
The Android result uses the verified 0.1.4 screenshot already in `public/screenshots/android/`.
The Telegram bot address and supported photo album flow come from `../telegram-bot/README.md`.
The Telegram illustration describes the interaction. It is labeled as an example scenario.
The page states that WebApp recognition, Telegram, and source portal links need internet.
The Android section tells the visitor to install the APK before going offline.

Validation passed: type checks, 169 tests in 14 files, and the production build.
Chromium checks passed at 320, 390, 768, 1024, and 1440 pixels in both themes.
The checks covered the age gate, image decoding, horizontal overflow, platform anchors,
internal navigation, Telegram link targets, release attributes, and unique page metadata.
No browser errors or hydration warnings occurred.
The production page and three screenshot URLs returned HTTP 200.
The APK GET returned HTTP 200 with the Android package content type.
The production age gate and page hydration passed.

## Android landing page, 2026-09-29

The Android 0.1.4 APK is 576,503,269 bytes.
The APK is too large to store as a generated Web UI artifact in Git.
The Android build directory already excludes APK files from Git.
Decision: stream the local APK from a configured path.
Decision: allow the public download link to use a different configured URL.
Decision: use the exact versioned file name in the default route and attachment header.

The current APK uses the Android debug signing key.
Decision: label the file as a test version on the public page.
Decision: explain that Android can request permission to install an APK from the
browser.

The verified Android screenshot set contains light and dark screens and real results.
Decision: copy six WebP derivatives into the Web UI public directory.
Decision: keep the source screenshot file names for traceability.
Decision: do not create artificial phone screens or result values.

The strongest additional benefits are on-device processing, the built-in 2,093-wine
catalogue, automatic per-model GPU or CPU selection, persistent local history, system
theme support, Android 9 compatibility, and a direct source-portal link.
Decision: state that the portal link needs an internet connection.
Decision: do not describe cosine similarity as a probability or confidence.

The local production route returned the configured Android package with HTTP 200.
The response used `application/vnd.android.package-archive`.
The response used the exact size and the versioned attachment name.
An invalid file name returned HTTP 404.
The server-rendered page contained one `/android` canonical URL and the application
structured data.
All six public screenshot files matched the verified Pixel 8 source files byte for
byte.

## Current-theme icon button, 2026-09-29

The user requested a sun or crescent moon instead of the theme select.
The icon MUST identify the current palette, not the next action.
Decision: render both decorative icons and let the early `data-theme` attribute select the visible icon.
Decision: announce the current palette and next action in the button label.
Decision: use the system palette while there is no explicit preference and write storage only after a click.
Decision: retain the existing `svoe-vino.theme.v1` key and accept old `light`, `dark`, and `system` values.

## Product header identity, 2026-09-29

The user requested the product logo and name in place of the source-portal wordmark.
The shared artwork is available in `../assets/` and already has an exact public SVG copy.
The Android app and Telegram bot use the name `Что за вино?`.
Decision: reuse the existing product artwork without color filters.
Decision: use one `ProductBrand` component in the header and age gate.
Decision: align the footer, page title, social metadata, structured data, and installed app name.
Decision: retain the source-portal name in links and source attribution.

## Header theme selection, 2026-09-29

The user requested a light-mode selector in the Web UI header.
The previous palette depended only on `prefers-color-scheme`.
Decision: provide `Авто`, `Светлая`, and `Тёмная` in one native select.
Decision: keep `Авто` as the default and store the preference under `svoe-vino.theme.v1`.
Decision: apply the stored preference in the document head before first paint.
Decision: use `data-theme` for all dark styles, including dialogs and mobile buttons.
Decision: synchronize browser theme colors and preferences across open tabs.
Decision: retain the current-page selection if local storage is unavailable.

## Shared product branding, 2026-09-29

The user designated the repository-level `assets/` directory as the source of Web UI product assets.
The shared 640 by 640 artwork is a bottle with a question mark inside scanner marks.
Decision: keep the source-portal wordmark in the page header because it labels the linked portal identity.
Decision: use the shared product artwork for the favicon, PWA install icons, Apple touch icon, and social preview.
Decision: copy the shared SVG without modification for the favicon.
Decision: derive the fixed-size PNG icons from the shared PNG.
Decision: scale the maskable artwork to 400 by 400 on its original cream background so the visible mark stays inside the safe area.

## Result-aware product-line guide, 2026-09-29

The product-line map contains six curated Abrau-Durso wines.
The source catalog snapshot contains 57 records with producer `Абрау-Дюрсо`.
The six-node map cannot assign a verified tier to every source record.
The resolved wine contains a producer, a slug, an image, and a source URL.
Decision: normalize punctuation in the producer name before the brand comparison.
Decision: accept the `abrau-dyurso-` source slug prefix as a fallback brand signal.
Decision: mark a map node only after an exact slug match.
Decision: show an unmatched Abrau-Durso result in a separate card.
Decision: do not place that separate result in a collection tier.
Decision: keep Victor Dravigny as the fixed example for another producer.
Decision: label the fixed example as a demonstration and not as the user's wine.

## Product-line image selection, 2026-09-29

The Abrau-Durso map used one generated CSS bottle shape for all six wines.
The local `Своё Вино` catalog snapshot contains a `main` image for every map wine.
The patch directory contains a replacement for `abrau-dyurso-udelnoe-vedomstvo-imperatorskoe-beloe-bryut`.
The original catalog match for this wine is shared and does not show the correct package.
The cropped derivative for this slug was regenerated from the patch.
The other five selected slugs have no patch.
Decision: prefer `patched` by exact slug.
Decision: use `main` when the exact patch does not exist.
Decision: publish local transparent WebP derivatives for the map.
Decision: do not request source catalog images from the browser.

## Taste and regional dish inference, 2026-09-29

The source catalog analysis contains 2,103 unique wine records.
All source records have a description.
The resolved source cards can also contain broad pairing categories.
Examples include `Блюда из рыбы`, `Мясо и стейки`, `Сыры`, and `Запеченные овощи`.

The inference audit found two JavaScript regex errors.
The token `\w` matches ASCII word characters by default.
It does not match Russian suffixes.
The token `\b` does not create reliable Russian word boundaries.
The old patterns could miss inflected Russian terms.
One broad reverse pattern could also treat `вино насыщенного золотистого цвета` as body evidence.
The corrected patterns use explicit Cyrillic ranges and contextual exclusions.
The tests now cover color words and `лёгкая терпкость`.

The public Wine Reviews CSV contains 129,971 rows.
The source ZIP SHA-256 is `8e6b7df797df88929c34b41b93cf60643cefa4c93b9af7396ff2196efdf47551`.
The CSV SHA-256 is `52af2643c8ac29f010f0cc629dfbdda1c74aa0f332d11762af9ef3de4e567ac9`.
The source license is `CC BY-NC-SA 4.0`.
The build selected 66,562 reviews across 18 grape varieties.
The aggregate file stores descriptor frequencies, structural levels, observation counts, and sample counts.
It does not store review text, critic scores, prices, wineries, or bottle names.
The aggregate file SHA-256 is `09a19fa5be08515fedc4d89fad3d23c6db609308494270399bbd827e103486a9`.
The raw dataset is not stored in the repository.

An external factual audit confirmed the three pilot dish forms.
The Russian расстегай has an open center and commonly uses a fish filling.
The Dagestani чуду can be a thin dry-pan flatbread with cheese and greens.
The Adyghe халыж or халюж is a fried pastry with Adyghe cheese.
The generated images show these defining features.
Sources: `https://www.gastronom.ru/text/amp/1000410`, `https://xn----8sbehgcimb3cfabqj3b.xn--p1ai/recipes/selection/chudu-lepeshki-iz-tonkogo-testa-s-syrom-i-zelenyu/`, and `https://etnografia.kunstkamera.ru/files/etnografia_journal/2026_01/05_kurinskikh_1_31_2026.pdf`.
The Kaggle dataset page confirmed the `CC BY-NC-SA 4.0` label on 2026-09-29.

Decision: use source descriptions and source pairing categories as the primary evidence.
Decision: use a matching dataset aggregate only when source evidence does not fill a value.
Decision: use deterministic grape, color, category, and production-method rules to fill gaps.
Decision: do not copy a third-party tasting review into the application.
Decision: do not transfer a foreign critic score to a Russian wine.
Decision: compare each wine with one international style, not one specific bottle.
Decision: state one shared property and one possible difference for each comparison.
Decision: select three dishes from three different cuisines.
Decision: include Russian, Tatar, Kalmyk, Tuvan, Dagestani, Ossetian, Chechen, Adyghe, Balkar, and Georgian dishes in the local dish rules.
Decision: show when a source pairing category supports a dish.
Decision: call the result a gastronomic hypothesis because a recipe can change the pairing.
Decision: show the dataset source and license even when the wine has no reliable grape mapping.
Decision: apply sweet-wine rules before dry varietal comparisons.
Decision: add images only for the three dishes in the default demonstration result.
Decision: keep all other dish cards complete without an image.

## PWA behavior review, 2026-09-29

A headless Chromium probe checked `https://chtozavino.ru/` with Playwright 1.58.2.
The live `sw.js` is 2394 bytes. The local production build has the same size.
Chrome reported no installability errors and no manifest errors.
The service worker controlled the page after the first visit because of `clientsClaim`.
The precache held 22 entries. It held no API responses and no shelf example photos.
An offline reload after one online visit failed with `net::ERR_FAILED`.
Reason: the first navigation occurs before the service worker is active, so `svoe-vino-pages` stays empty.
An offline reload after two online visits returned the page from the service worker with HTTP 200.
The offline page rendered «Найти вино по фото» and loaded the Playfair Display font.
The README and the specification say that the app shell opens offline after one successful online visit. The probe does not confirm this statement.
The cached HTML contains the `portal-config` SSR payload. The payload is a copy of the `/api/config` response, for example `apiAvailable: true` and `shelfAvailable: true`.
An offline start therefore shows the last known service state.
`registerType: 'autoUpdate'` makes `vite-plugin-pwa` 1.3.0 call `window.location.reload()` when an updated service worker activates.
The Nuxt module plugin does not pass `onNeedReload`. A reload after a deploy can discard the selected photo and the shown result.
Live `/sw.js` and `/manifest.webmanifest` use `cache-control: public, max-age=0, must-revalidate`. The manifest uses `application/manifest+json`.
The maskable icon mark reaches 205.6 px from the center. The safe radius is 204.8 px. The difference is antialiasing only.
The `theme-color` meta has one value, `#7b3528`. The manifest `background_color` is the light `#fefdfa` also in the dark system theme.
The owner selected the fixes on 2026-09-29.
Decision: correct the offline statement in the documents. Do not add page-cache warming code.
Decision: use `registerType: 'prompt'` without an update banner. Reason: a scanner session is short, and a reload can discard a photo or a result.
Consequence: an app page that stays open keeps the old version until all app pages close.
Decision: keep the SSR config payload in the cached page. The specification now states this exception.
Decision: add a dark `theme-color` with the dark page color `#211e1c`.
The manifest cannot change `background_color` for the dark theme in current browsers, as far as this review found. The launch screen stays cream.
Decision: add JPEG manifest screenshots. The Chrome richer install dialog needs screenshots.
Unhead lists `theme-color` in `MetaTagsArrayable`. Two `theme-color` tags with `media` both render.
With `prompt`, the generated `sw.js` has no `clientsClaim` and calls `skipWaiting` only for a `SKIP_WAITING` message.
`scripts/check-pwa-browser.mjs` uses a loopback proxy that appends a comment to `sw.js`. This change starts a real service-worker update without a second build.
The check passed against the local `prompt` build. It failed against the live `autoUpdate` build with a destroyed execution context, which is a page reload.

## Complete result metadata fallback, 2026-09-29

The upstream recognizer can return more wine slugs than the 12 local Web UI records contain.
The source portal provides `GET https://api.vino-svoe.ru/v1/wines/<slug>`.
The endpoint returned the complete card for `massandra-muskat-rozovyy-pozdnego-sbora-rozovoe-sladkoe-10`.
The response includes the title, producer, region, grapes, style, description, and source image path.
Decision: keep the local records as the first lookup.
Decision: request an unknown valid slug from the official source JSON API.
Decision: use a fixed source host and reject redirects, mismatched slugs, untrusted image paths, oversized responses, and invalid records.
Decision: keep the existing explicit UI fallback when source metadata is unavailable.

## Owner-supplied shelf examples, 2026-09-29

The project owner supplied four supermarket shelf photographs.
The first and fourth files had the same SHA-256 value.
Decision: store the three unique photographs.
Decision: replace the Wikimedia example and its attribution.
Decision: convert each photograph to a 2560 by 1928 WebP file.
Decision: remove embedded metadata during conversion.
Decision: let the visitor select one example before the portal sends it through the normal group-match route.

## Production resilience verification, 2026-09-29

A bounded public load test sent one, four, eight, and twelve concurrent recognition requests.
All requests passed through concurrency eight.
At concurrency twelve, eight requests passed and four requests reached the matcher capacity guard.
The matcher returned HTTP 503 with `matcher is busy`.
The Web UI changed this response to HTTP 502.
The same mapping changed the matcher HTTP 413 JPEG pixel-limit response to HTTP 502.
Decision: preserve the matcher HTTP status when the status is safe and actionable.
Decision: do not expose the matcher response body.
Decision: map an unexpected matcher status or an invalid matcher response to HTTP 502.

The live shelf example returned HTTP 502 from the Web UI.
The deployed matcher revision was `9ba496d230d23398f76275cbbd187d5a820c4bfe`.
Its OpenAPI document did not contain `/v1/group/match`.
Commit `b752591` added this endpoint after the deployed revision.
Decision: deploy a committed matcher revision that includes `b752591` before shelf mode stays enabled.

Web UI revision `11ebfbf` preserved HTTP 413 for the JPEG dimension bomb.
A second 12-request burst returned nine HTTP 200 responses and three HTTP 503 responses.
The matcher health route stayed at HTTP 200.
The first shelf request after the route deployment found 93 bottles.
It failed because the SigLIP2 service accepts at most 64 inputs in one request.
Matcher revision `013ab56` split larger logical batches into requests of at most 64 inputs.
The final public shelf request returned HTTP 200 in 2598.775 ms.
It returned 93 bottles and 93 ready matches.
The production browser opened bottle 1 as `Траминер` and closed the card without a second recognition request.

## Search discovery and age gate, 2026-09-28

The age gate previously replaced the complete server-rendered page with a loading element.
A new visitor then received only the age gate after hydration.
Decision: always render the scanner page.
Decision: render the age gate as a fixed overlay before the local storage check.
The client removes the overlay only after it finds a stored confirmation.
Decision: make the scanner controls inert while the gate is open.
This design preserves the mandatory interaction block and keeps the page content available to crawlers.
The apex and `www` hosts previously returned identical HTML without a canonical signal.
Decision: use `https://chtozavino.ru/` as the canonical URL.
Decision: redirect the complete `www` host to the apex with HTTP 308 at Caddy.
Decision: publish one sitemap URL because the portal has one indexable page.
Decision: describe the portal as `WebSite` and `WebApplication`.
The portal does not own indexable wine pages, so it does not publish wine `Product` metadata.
The reference file names are stable but are not content hashes.
Decision: cache these files for seven days and allow one day of stale revalidation.

## Matcher readiness, 2026-09-28

The matcher provides the public `GET /healthz` readiness route.
The readiness response contains `status: "ok"` and the selected pipeline.
The configured prediction URL can use a private loopback or network address.
Decision: the Nuxt server checks matcher readiness.
Decision: derive the health path from the final `/v1/eval/predict` path.
Decision: do not change the Web UI `GET /api/health` liveness contract.
Decision: report matcher readiness as `apiAvailable` in `GET /api/config`.
The prediction request remains the final availability check because readiness can change after the configuration request.

## Progressive Web App, 2026-09-28

The user requested PWA support and the Telegram bot icon.
The Web UI reuses `telegram-bot/assets/botpic.svg` as the icon source.
The user selected the PWA module implementation after reviewing the first local implementation.
Decision: use `@vite-pwa/nuxt` 1.1.1 and its generated Workbox service worker.
The installed module resolves `vite-plugin-pwa` 1.3.0.
The package audit reported no vulnerabilities after installation.
Decision: use automatic service-worker updates and generated manifest registration.
Decision: precache Nuxt client bundles, install icons, and app-shell reference assets.
The production Workbox build precaches 22 entries with a total size of 638 KiB.
Decision: use `NetworkFirst` for page navigation and exclude the `/api/` and `/v1/` route prefixes.
Workbox runtime routes use GET by default. Photo upload requests do not match a cache route.
Development mode does not enable the generated service worker.
The maskable icon uses a solid cream background and keeps the mark in the central safe area.
Recognition, metadata, and source portal navigation remain online-only operations.
The production browser loaded the manifest link and the new SVG favicon without warnings or errors.
The production contract check loaded the service worker, manifest, and all declared PNG icons.

## Local result demonstrations, 2026-09-28

The selected implementation is a fully local demonstration.
The product action must explain a future coordinate request without invoking browser geolocation.
Decision: use a fictional SuperLenta store and fictional domestic products.
Decision: mark paid food priority visibly and do not include an alcohol purchase action.
The public `vino-svoe.ru` Abrau-Durso catalog provides stable wine detail paths for the product-line demonstration.
Decision: keep map positions and descriptions local and link each node to its public source page.
Decision: use a separate normal link for keyboard and touch access in addition to node double click.
The desktop and 390 px mobile checks confirmed the age gate, result actions, dialogs, product cards, story rotation, and map controls.

## Matcher group endpoint integration, 2026-09-28

The matcher now provides `POST /v1/group/match` on the same service that provides `POST /v1/eval/predict`.
The group response includes the shelf preview, detected bottle coordinates, segmentation masks, and ready best matches.
Decision: the browser calls same-origin `/v1/group/match` through the Nuxt server.
Decision: derive the upstream group URL from the existing `NUXT_PREDICTION_ENDPOINT` origin and path prefix.
Decision: do not add `NUXT_GROUP_MATCH_ENDPOINT`.
This keeps one matcher configuration and prevents the browser from receiving a private service address.
The matcher performs all bottle matching during the group request.
Bottle selection is now local UI state and does not start another prediction request.
The matcher can archive the original group photo.
The Web UI does not claim that the photo is never stored.

## Princess deployment and shelf suspension, 2026-09-28

Princess has 1 vCPU, 1.9 GiB RAM, and a 25 GB disk.
The live check showed approximately 1.7 GiB available RAM and 23 GB available disk space.
Caddy used approximately 46 MiB RSS during the check.
The Nuxt production output used approximately 22 MB on the build host.
Decision: Princess can run Caddy and the Nuxt portal for demo and moderate traffic.
Decision: keep matcher and SAM3 computation on GX10.
The existing Princess loopback tunnel provides the compatible `/v1/eval/predict` route on port 28000.
Its current pipeline is `official-eval-mock`.
The existing public Caddy API also owns `/v1/eval/predict` and requires a bearer token.
Decision: keep that route unchanged and send browser photo requests to the equivalent portal `/api/predict` route.
The owner selected a selectable temporary-unavailable view for «Вся полка».
The Princess deployment does not set `SAM3_ENDPOINT`.
The server rejects the disabled shelf route before it reads an upload.

## Shelf mode, 2026-09-15

The user requested segmented shelf photos and a popup for each selected bottle.
The existing GX10 SAM3 gateway accepts multipart `image` and `text=wine bottle`.
Use canonical `SAM3_ENDPOINT`. Keep all service requests behind our portal API.
The first live request used the public Wikimedia shelf example documented in `docs/assets.md`.
The source JPEG hash matched the public download. No private user photo was used.
The request returned 96 masks at 1280 × 853 in 68.162 seconds after model loading.
The service returned binary full-frame masks. Eleven detector boxes extended slightly outside the photo.
Some masks had disconnected fragments outside the detector box.
Decision: clamp detector boxes and exclude mask fragments outside each box.
Return cropped overlays to avoid one full-frame browser texture per detected bottle.
Recognize only a selected crop. A dense shelf must not trigger 96 prediction requests.
The native popup reuses the existing wine result and food recommendation flow.

Independent code review identified malformed crop parsing and missing server-side prediction cancellation.
Added strict data URL validation and propagated client disconnects to the prediction provider.
The focused tests cover these corrections and retain the existing evaluator contract.
Physical camera, touch, and full visual checks remain separate device verification work.

The first production request encountered a transport reset while the gateway loaded SAM3.
The gateway recorded an empty 502 after 58.311 seconds. No SAM3 validation error was recorded.
The same normalized public photo passed after loading. It returned 94 masks through the portal.
Added one retry for known transient socket and transport timeout codes within the original time budget.
Permanent address errors, malformed output, and cancellation do not trigger this retry.
Tests cover these branches. A new cold-start failure was not forced on the shared service.
The final browser flow returned 94 selectable bottles, a source-linked demo wine, and three live foods at public test store 5020.
All new browser tools rejected invalid input. Reset cleared the shelf and popup.
The existing evaluator accepted all three requests after the shelf changes.

## Demo service boundary, 2026-09-15

The user clarified that the Web UI must query our portal and our service must provide the response.
The current code already follows this boundary.
`useFoodRecommendations` calls relative `/api/food/stores` and `/api/food/pairings` routes.
The server handlers call the Globus adapter and return normalized data.
The browser has no direct retailer data API call.
Product images and user-selected retailer links remain separate media and navigation requests.
Decision: preserve the implementation and make the boundary explicit in the specification.
No separate service endpoint was supplied or connected in this clarification.

## 2026-09-15

- Read the official evaluator script and its README.
- Confirmed `POST`, multipart field `image`, and response field `slug`.
- Confirmed the evaluator timeout and HTTP status rules.
- Inspected the supplied public catalog in the browser.
- Recorded source colors, typeface, layout, navigation, and bottle assets.
- Selected Nuxt for one local UI and API server.
- Selected a fixed mock prediction to avoid implying image recognition.
- The task document recommends Strapi for the catalog. The user permits a mock implementation.
- Eight demo slugs occur in the official CSV. Four newer slugs use public portal metadata.
- The portal reports `108%` alcohol for `muskat-ottonel-gusev`. The demo record omits this invalid value.
- Nuxt 4.5.2 requires Vue Router 5.2.0. The project uses the matching version.
- Relative shared imports failed in the Nuxt production server output. The documented `#shared` alias resolves the production imports.
- The official evaluator accepted all three production mock responses.
- WebMCP checks confirmed search state changes, invalid input rejection, and scanner dialog opening.
- Full visual regression, physical camera behavior, and a real recognition service remain untested.
- Aligned the Node engine range with the installed Nuxt 4.5.2 package metadata.
- The first GitLab CI job failed during the Docker Hub image download. One retry was started.

## Photo search scope correction, 2026-09-15

The user requires a dedicated photo search page with the source visual identity.
The user does not want a duplicate catalog UX.
Decision: replace the catalog page with one responsive scanner workspace.
A modal-first alternative adds an unnecessary opening action. A catalog-first alternative conflicts with the corrected request.
Keep the prediction API and metadata fixture. Remove the catalog UI and local detail navigation.
A valid prediction must survive metadata fetch errors. The old scanner assigned the slug too late.

The scanner state checks confirm that metadata 404, 500, invalid JSON, wrong slug, network failure, and timeout retain the valid prediction link.
The production browser example completed through the same automatic upload path as the UI.
The updated production evaluator check passed for all three official photos.

## Food source selection, 2026-09-15

The user selected a retailer with an accessible API instead of demo products.
The sibling `retail-query/docs/store-search-capabilities.md` already documents Globus, METRO, and Lenta.
Globus has a confirmed coordinate directory and guest product search.
METRO directory access remains unverified. Lenta requires a specific network access profile in that report.
Decision: use Globus directly. No proxy, login, or API key is needed for the verified guest flow.
A new live probe returned HTTP 200 for the directory, store 5020 context, three searches, and one product detail.
The directory contained 22 records at the test time.
The queries were `филе индейки`, `моцарелла`, and `хумус`.
`docs/validation/globus-access.json` records the sanitized observation.
The source fields show that `quantity` is basket state and `quantity_max` is available quantity.
Some prices require the loyalty card. The UI preserves the returned promotion conditions.
Product links come from `data.product.share_text`. Do not construct a speculative path.
No user location was obtained. Verification uses public store coordinates or an explicit public store ID.

The integration uses an application API, not a public developer contract.
The directory limits geographic coverage. Straight-line distance does not represent travel time or delivery eligibility.
The pairing rules use source labels first and editorial defaults second.
The product search samples up to eight candidates per idea. It does not prove full catalog coverage.
An independent code review found an incorrect fixed wine-color reason and overly broad preparation matching.
Removed the fixed color assertion. Excluded salted fish and pickled mushrooms from baking ideas.
Try a second candidate when the first detail record becomes unavailable or fails validation.
