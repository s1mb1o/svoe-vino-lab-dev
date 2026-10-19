# Change log

## 2026-10-19 — Account-enabled phone header

- Keep all header actions inside 320- and 360-pixel viewports when the Diary link is enabled. Use the existing brand icon without its wordmark below 380 pixels.
- Preserve the full accessible home-link name and 44-pixel navigation controls.

## 2026-10-19 — Dinner Lens on the ideas page

- Replace the grocery mock with a Dinner Lens card in the implemented section. Describe photo or name entry, sauce and heat choices, and explanations for wine pairings. Link directly to `/dish`.
- Update section counts and balance the four implemented cards in two desktop columns.

## 2026-10-19 — Wine&Dine Merge landing

- Added `/game` with original game illustrations, a three-step introduction, selectable regional scenes, separate pouring practice, and a native FAQ.
- Added the Game invitation on `/ideas`. Kept `/hackaton` → `/ideas` as the existing entry path.
- Linked Play to the existing game origin and kept standalone pouring at `?mode=pour`.
- Added the portal header label, sitemap entry, canonical metadata, system themes, responsive layout, and keyboard region selection.
- Documented content evidence, artwork provenance, prototype limits, and browser verification.
- Passed type checks, the production build, 94 required build checks, and the first-load bundle check. Twenty existing optional catalog checks were skipped.
- Passed all 16 production browser layouts in Chromium and WebKit, including route navigation, region keyboard focus, FAQ disclosure, image loading, and exact game links.


## 2026-10-19 — One searchable dish picker

- Combine dish name and broad category in one editable picker. Browse up to three visual levels, search by name and category, select a broad group, or enter a custom dish. Preserve all 320 source IDs; fold extra intermediate class names into the second level.
- Support touch, keyboard navigation, photo corrections, and category clarification in the same field.

## 2026-10-19 — Visible sauce heading

- Show «Вкус» above the heat choices and «Соус» above the sauce choices, starting with «Сливочный». Keep the shared accessible legend and existing selection behavior.

## 2026-10-19 — Bottle result spacing (#67)

- Let the result image set the height of `.match-bottle`. Prevent the image container from shrinking. The bottle stays above «Лучшее совпадение» on desktop and mobile.
- Keep long wine titles inside the result card on narrow screens.

## 2026-10-19 — Wine-specific glass outlines

- Dinner Lens result cards use a narrow flute with three bubble dots for sparkling wine, a smaller tulip for still white wine, and a broad rounded bowl for still red wine. Choose the icon from the wine facts; sparkling takes priority over color.

## 2026-10-19 — Separate heat and sauce choices

- Separate «Неострое» and «Острое» from the five sauce presets on `/dish`. Use a vertical divider on desktop and a horizontal divider on phones. Keep all selection behavior and request attributes.
- Give the two groups accessible names: «Острота» and «Соус».

## 2026-10-19 — Keep only dish taste presets

- Remove «Какое вино» and «Сладость вина» from `/dish` on desktop and mobile. Remove their state and request constraints. Keep all seven taste/sauce presets and wine facts on result cards.
- Update browser checks to verify that the removed filter groups are absent and that recommendation requests contain no `user_constraints`.

## 2026-10-19 — Shorter upload hint on «Вино к блюду»

- The upload hint on `/dish` is «JPEG, HEIC, PNG, WebP». It does not show «JPG» (the same format as JPEG) or the 10 MB limit. The limit stays: a larger file still gets «Выберите фотографию размером до 10 МБ.»

## 2026-10-19 — Confirmations instead of a re-login; endless login

- Owner decision: no 15-minute re-login. «Удалить аккаунт» deletes after «Удалить навсегда»; the re-login panel («Подтвердить кодом из письма», «Подтвердить через Яндекс ID») and «Войти заново» are removed, with the Yandex `intent=reauth` flow and its cookie.
- «Отвязать» and «Отозвать» ask a yes/no question first.
- Sessions do not expire. The session cookie lasts 400 days (the browser maximum) and is set again at every visit.
- Tests: 469 (the six Yandex reauth tests removed; cookie lifetime and deletion tests added). Browser check of the confirmations, deletion, and the cookie lifetime: 9 checks.

## 2026-10-19 — Review fixes for the MAX link and application tokens

- The MAX Bridge, a third-party script, runs only on the mini-app host. On any other host `/max` redirects to `/account` (server middleware); `/api/account/config` reports `maxApp` only for the mini-app host, and the page also leaves `/max` without it.
- The host guard decides on the path that the router uses (`event.path`) and refuses dot segments, encoded dots and slashes, backslashes, and empty segments. The host compare ignores case, the port, and a trailing dot (`NUXT_ACCOUNT_MAX_HOST`).
- «Открыть Telegram» opens the one-time link by script: after an in-site navigation Metrika link tracking (`trackLinks`) cannot see the code, and the page holds no link with it.
- 21 new tests, including the guard as middleware with raw Host headers and paths (474 in total). Browser checks: Telegram 26, MAX 24 (mini app on its own host), tokens 16.

## 2026-10-19 — Three rows of Dinner Lens preferences

- Replace eight settings fields with three visible icon groups: seven composable sauce/taste presets, wine color and still/sparkling, and sweetness. Keep text labels, keyboard activation and pressed states. Wrap choices for narrow phones with 44-pixel targets.
- Preserve recipe defaults when a preset is unset. Support explicit no-cream and no-heat choices. Clear old results and pagination when a choice changes. Keep brut categories compatible with sparkling wine.
- Extend browser checks for every preset, combinations, toggling, request payloads, keyboard activation, and desktop/tablet/mobile layouts in both themes. Keep the Dinner Lens backend and API contract unchanged.
- Refine Russian label wrapping, dark-theme wine icons, linked reset hints, and high-contrast selection/focus indicators. Verify that labels fit and theme variables reach the controls.

## 2026-10-19 — Application tokens

- «Токены приложений» on `/account` (issue #65): create (name, 30/90/365 days, recent login), show once with «Скопировать токен» and the MCP client configuration, list with expiry and last use, «Отозвать».
- `GET /api/app/v1/profile` and `GET /api/app/v1/wines` for MCP clients with `Authorization: Bearer cvpat_...`. Uniform 401, 429 with `Retry-After`, 503 `unavailable`; no cookies, no cache. The MAX mini-app host rejects these routes.
- Public use needs the Caddy exemption of `/api/app/*` (open decision 1 of #65).
- 19 new tests (453 in total). End-to-end on a local stack: a token from the page read the profile through the real MCP server; after «Отозвать» the next call returned `unauthorized` (16 checks).

## 2026-10-19 — MAX link and the mini app

- `/max` is the diary mini app for MAX (plan 05, issue #50): the account page in MAX mode. It loads the MAX Bridge only there. In MAX the person logs in by email code and confirms «Привязать MAX-аккаунт «Имя Фамилия» к дневнику …?»; the signed `initData` goes to `POST /api/account/max/link`. Outside MAX it shows only «Откройте дневник в MAX» with the fixed link and QR code.
- «Привязать мессенджер» on `/account` offers «MAX» with the fixed deep link (`NUXT_ACCOUNT_MAX_APP_LINK`) and its QR code (`/api/account/max/qr.svg`, rendered on the server with `uqr`, now a direct dependency). «Отвязать» works for MAX too.
- Host guard for `NUXT_ACCOUNT_MAX_HOST`: only the mini-app page, its assets, the legal pages, and the email, sign-up, session, deletion, and MAX routes. Metrika and the Workbox page cache skip `/max`; it has its own header and footer.
- Telegram link review fixes: starting a link needs a recent login («Войти заново» on `reauth_required`); a notice stays visible after the last messenger is unlinked.
- 35 new tests (434 in total). Browser checks: the MAX link at 1280 and 390 px with simulated launch data (23 checks), the Telegram link again (26 checks), and the host guard with `curl`.

## 2026-10-19 — Telegram link

- «Связанные мессенджеры» on `/account` now has «Привязать мессенджер» → «Telegram» (issue #51). The page gets the bot deep link from `POST /api/account/links/telegram`, shows «Открыть Telegram», and reads the account again when the tab becomes visible or after «Я привязал». An expired link offers «Новая ссылка».
- «Отвязать» next to a linked Telegram calls `DELETE /api/account/identities/telegram`. The site has no unlink for login methods.
- `/api/account/config` reports `providers.telegram`. The server accepts only an `https://t.me/<bot>?start=link_<code>` link from the service. 9 new tests; a browser check of the link and unlink at 1280 and 390 px passed (26 checks).

## 2026-10-19 — Dish drag-and-drop and HEIC

- Accept one dropped dish photo on the upload panel, with a visible drop target and photo replacement during a pending request. Keep the picker and mobile camera.
- Support JPG/JPEG, HEIC/HEIF, PNG and WebP by content signature, including absent/generic MIME types. Reject invalid, empty, oversized and multiple files before model work.
- Decode HEIC locally in an on-demand cancellable worker, then normalize all inputs to upright JPEG without source EXIF/GPS. Preserve the 10 MiB and 50-million-pixel limits and the backend contract.
- Add rotated HEIC, format, metadata-bound and cancellation coverage. Publish the decoder license and source notices. Read `docs/dinner-lens.md`.

## 2026-10-19 — Messengers are not login methods

- «Способы входа» lists only email and Yandex ID. Telegram and MAX appear under «Связанные мессенджеры» with «Через них нельзя войти в дневник: они только сохраняют находки». The future link action is «Привязать мессенджер» (owner decision).


## 2026-10-19 — «Винный дневник»: Yandex reauth stays on the same account

- «Подтвердить через Яндекс ID» before account deletion could switch the session to another diary when the browser used another Yandex account. The callback now accepts the new session only for the same user; otherwise it keeps the current session, ends the new one, and shows «Вход выполнен в другой аккаунт Яндекс ID. Удаление отменено…».
- The confirmation heading names the account: «Удалить аккаунт <имя> и все данные?».
- 6 new tests (59 account tests; 398 in total, 20 existing skips).


## 2026-10-19 — «Винный дневник»: login and sign-up

- Add the header link «Дневник» (phones: the book icon) and the `/account` page: login by email code, login with Yandex ID, sign-up with two separate consents, the logged-in view, logout, and account deletion. Spec: `docs/account.md`.
- Add the `/api/account/*` server routes to the account service (issue #48): httpOnly `__Host-` cookies, an `Origin` check on state changes, `Cache-Control: no-store`, 2 s timeout, and a uniform error body. The Yandex callback answers only with HTTP 302.
- Account deletion after the 15-minute window offers a fresh login by email code or Yandex ID in the confirmation panel.
- Metrika does not start on `/account` and sends no hit for it. The Workbox page cache skips `/account*`.
- `NUXT_ACCOUNT_ENDPOINT`, `NUXT_ACCOUNT_TOKEN`, `NUXT_ACCOUNT_PUBLIC_ORIGIN`. An empty endpoint hides the link and turns the routes off.
- Security review (Codex): fixed a Metrika init script that did not parse on any page, an unbounded chunked request body, and a too short Yandex finish timeout. Accepted local-host risks are in `docs/account.md`.
- Checks: 53 new unit tests (351 in total: 331 passed, 20 existing skips), `nuxt typecheck`, production build, and a 25-step Chrome run against a local account service (Metrika starts on `/` and not on `/account`): sign-up, cookie flags, reload, logout, limit message, wrong code, login, deletion with reauth, Yandex start with PKCE, forged callback, phone header without overflow. Service down: the home page and the scanner work; the page shows «Дневник временно недоступен».

## 2026-10-19 — Wine for a dish

- Add «Вино к блюду» as the third scanner mode at `/dish`. Keep three visible touch-accessible links on phones.
- Connect the existing Dinner Lens API through bounded, authenticated server-only routes. Keep service addresses and bearer tokens out of browser configuration and responses.
- Add photo normalization, explicit dish confirmation, manual/category input, sauce and wine constraints, exact source-linked wine cards and signed-cursor continuation.
- Preserve cancellation, replacement and retry. Clear stale wine cards and cursors after a dish/filter change. Keep existing cards when a continuation fails.
- Export only the 320 taxonomy labels; all wine selection stays in Dinner Lens. Read `docs/dinner-lens.md`.
- Pass 319 unit tests (20 existing optional snapshot tests skipped), the type check, the production build and the bundle check. Pass desktop Chromium, 320-pixel mobile Chromium and 390-pixel mobile WebKit checks, including light and dark themes.
- Verify the real gx10 service through the portal proxy: ribeye 8 wines across 3 pages, Olivier 12 across 4, and king crab 12 across 4. Verify one real photo recognition followed by explicit confirmation without a second vision call.
- Apply the Opus review fixes: show manual unknown-dish clarification and focus its category control; restore focus after photo removal, cancellation and discovery pages; preserve corrected names on recommendation failures; reject inherited attribute keys and localize malformed responses.

## 2026-10-19 — Map load retry

- Keep keyboard focus inside the guide dialog after a successful «Повторить». The retry button disappears, so focus moves to the dialog heading.
- Add a blocked-chunk scenario to `npm run test:line-map`: failure alert, announced loading state and `aria-busy` on retry, centered map after the retry, focus inside the dialog. It passes in Chromium and WebKit.

## 2026-10-19 — Producer maps on demand

- Load a producer map only when the user opens «Путеводитель по линейке». Each of the 19 maps is a separate chunk of 4.7 to 21.6 KB gzip.
- The scanner pages import only the generated index `shared/data/product-line-index.json` (13 KB gzip). It gives the producer and the match state before the map loads.
- The first-load JavaScript of `/` drops from 296 KB to 139 KB gzip (12 files, gzip level 9). `npm run test:bundle` reports 134 KB gzip and fails when `/` or `/shelf` loads map data.
- Start the load when the pointer enters or the keyboard focuses the guide action. The dialog shows an announced loading state, and a retry after a failed load.
- `/lineup/<producer>` loads its map with `useAsyncData`. The server still renders the map.
- Validate the maps in the tests and in `prebuild`, not at module load. Add `npm run line-maps:index` and a test that fails on a stale index.
- The service worker still precaches all chunks. Offline behavior does not change.
- The MCP server reads the map list from the index (#25).
- Pass 278 unit tests (20 snapshot tests skipped), the type check, the build, and the bundle check. Pass `test:line-map` and `test:producer-maps` (81 checks) in Chromium and WebKit.
- Read `docs/plans/04_lazy-product-line-maps.md`.

## 2026-10-19 — Line-map browser suite

- Open shelf mode through the «Вся полка» link in `npm run test:line-map`. The mode switch is a pair of links since the mode pages, and the suite failed at this step on `main`.

## 2026-10-19 — Shared product-line core

- Move the pure product-line types, the resolver, and the validator to `shared/product-line-core.ts`. The module has no runtime imports.
- Keep the public exports of `shared/product-line-map.ts`. It binds the registered maps.
- Node.js can import the core module. The MCP server needs it to serve the same maps (#25).
- Accept a null producer in the resolver. The MCP catalog has records without a producer.
- Pass 274 unit tests (20 snapshot tests skipped), the type check, and the production build.

## 2026-10-19 — Log layout

- Move the 2026-10-16 and 2026-10-17 lineup entries from above the file title into the dated list.
- Apply this change to `ChangeLog.md`, `ResearchLog.md`, and `SMOKE_TESTS.md`.
- Use the heading format of each file. Keep the entry text unchanged.

## 2026-10-18 — Message for an unreadable HEIC photo

- Pass HTTP 422 from the matcher in `/v1/eval/predict` and `/v1/group/match`. Before, the portal changed it to 502 («повторите»).
- For HTTP 422, show «Не удалось прочитать HEIC. Сохраните фото как JPEG.» for a HEIC photo,
  and «Не удалось прочитать фото. Попробуйте другой снимок.» for other photos.
- The production matcher has no HEIF support yet (#24). It answers HTTP 422 for HEIC.

## 2026-10-18 — Presentation v14

- Replace `public/presentations/chtozavino-presentation.pptx` and `.pdf` with presentation v14 from the website.
  PPTX: 91456347 bytes, SHA-256 `1f399b2e0d91509633355b61e0856dd358e3fe54671e310ef486533ca6af99fd`.
  PDF: 8946863 bytes, 27 pages, SHA-256 `7afff5050353b30be57d1c30000a905a2b0164b214bc86b27e6973e9fafe7b03`.

## 2026-10-18 — Session Replay off

- Turn off Metrika Session Replay: `webvisor: false` (owner decision in #41).
  Also turn it off in the counter settings of Metrika.

## 2026-10-18 — Mode pages and HEIC uploads

- Give each scan mode its own page: «Одна бутылка» at `/`, «Вся полка» at `/shelf`.
  The mode switch is two links. `/shelf` has its own title, description, and canonical URL, and it is in the sitemap.
- Accept HEIC (HEIF) photos in both modes: file pickers, client checks, and the server signature check.
  The server sends them as `image.heif`. The upload hints say «JPEG, PNG, WebP, HEIC · до 10 МБ».
- Show a text in place of the preview when the browser cannot show the photo (HEIC in Chrome and Firefox).
- HEIC needs the matcher HEIC support (#24). Deploy the matcher first (#44).

## 2026-10-18 — Yandex.Metrika port

- Port the Yandex.Metrika change from the lab repository `svoe-vino-lab`, branch `codex/metrika-release` (#40).
- The lab commits are `10632011` (counter) and `af36345e` (verification record).
  The release IDs in the 2026-10-06 entry are lab revisions.
- This port does not include the presentation update of 2026-09-30 from the lab base.
- Send a client-navigation page view after Nuxt renders the head of the new page.
  Metrika now records the title of the new page, not the title of the previous page (#40).
  Production release `10632011` does not have this fix.

## 2026-10-17 — Eight producer review resolution

Complete the owner-authorized Claude Opus 5.5 Max review. Correct eight producer maps in separate commits. Fix image attribute forwarding and double gray filters. Add neutral record labels and default CI attribution. Pass 276 full-snapshot tests, type checks, the build, 81 producer cases per engine, and both Abrau suites.

## 2026-10-17 — soyuz-vino review correction

Use snapshot-only evidence for historical brands. Remove unsupported relative ranks. Flag the red-wine and white-grape contradiction.

## 2026-10-17 — valery-zakharyin review correction

Record the reserve label evidence for each reserve wine. Keep the group explicitly editorial.

## 2026-10-17 — chateau-pinot review correction

Use original labels to confirm Gravity membership. Keep historical blends without a confirmed collection in a neutral group.

## 2026-10-17 — esse review correction

Move four incorrectly ranked products to Unplugged. Record original-label evidence and the possible YELLOW GLOVES counterpart.

## 2026-10-17 — sober-bash review correction

List all six Грани products. Record exact source captures and original-label membership evidence.

## 2026-10-17 — belbek review correction

Describe the different rose blends. Record the possible Reserve counterpart without creating an unverified catalog link.

## 2026-10-17 — agora review correction

Correct BLUSH MIRAGE effervescence. Scope oak ageing to historical card evidence. Cite exact official range pages.

## 2026-10-17 — novy-svet review correction

Remove unsupported premium ranks from historical special cuvees. Separate explicit aged cards from varietal cards with no confirmed collection.

## 2026-10-17 — Structured absence validation

Validate exact producer values in structured absence checks. Keep the existing text-based absence evidence compatible.

## 2026-10-17 — Sober Bash amphora source

Correct the Sober Bash amphora subgroup source URL. Cite the official Грани collection.

## 2026-10-17 — Novy Svet absence scope

Use the exact Novy Svet snapshot producer value in the official-addition absence check. Check structured absence scopes against independent producer baselines.

## 2026-10-16 — Eight producer map verification

Add eight producer maps in eight separate implementation commits. Cover 370 exact catalog cards and eight official additions. Normalize bottle cutouts and image frames. Pass 275 unit tests, type checks, the production build, and 77 producer browser cases per engine. Pass the complete Abrau browser regressions in both engines.

## 2026-10-16 — Союз-Вино

Add Союз-Вино: 69 catalog cards, 1 official additions, and 19 groups. Ship normalized bottle assets and independent source evidence.

## 2026-10-16 — AGORA WINERY

Add AGORA WINERY: 32 catalog cards, 1 official additions, and 9 groups. Ship normalized bottle assets and independent source evidence.

## 2026-10-16 — Собер Баш

Add Собер Баш: 37 catalog cards, 1 official additions, and 6 groups. Ship normalized bottle assets and independent source evidence.

## 2026-10-16 — Бельбек

Add Бельбек: 39 catalog cards, 1 official additions, and 8 groups. Ship normalized bottle assets and independent source evidence.

## 2026-10-16 — Новый Свет

Add Новый Свет: 44 catalog cards, 1 official additions, and 5 groups. Ship normalized bottle assets and independent source evidence.

## 2026-10-16 — Валерий Захарьин

Add Валерий Захарьин: 46 catalog cards, 1 official additions, and 14 groups. Ship normalized bottle assets and independent source evidence.

## 2026-10-16 — Шато Пино

Add Шато Пино: 50 catalog cards, 1 official additions, and 12 groups. Ship normalized bottle assets and independent source evidence.

## 2026-10-16 — ESSE

Add ESSE: 53 catalog cards, 1 official additions, and 6 groups. Ship normalized bottle assets and independent source evidence.

## 2026-10-16 — Abrau-Durso identified catalog completion

- Add 21 still-wine cards in five groups. Extend Abrau-Durso to 73 products in 19 groups.
- Cover 56 of 57 snapshot cards. Keep `rozovoe-polusladkoe-2` excluded until identification, as requested by the owner.
- Preserve the original 52 products, three aliases, 20 gray products and original image bytes.
- Add local bottle images, measured frames, official collection sources and independent catalog crosswalks.
- Wait for web-font layout before centering a selected wine. Add a delayed-font browser regression.
- Pass 235 unit tests, type checks, the build, 126 new-slug browser cases and the existing Abrau suite in Chromium and WebKit.
- Record the largest catalog producers that have no map and the updated total catalog coverage of 618 out of 2,103 cards.


## 2026-10-16 — Complete bottle-image coverage

- Require an image and a measured frame for every current map product.
- Verify all 647 images across 11 producer maps. Preserve all 636 previous image files.
- Pass 233 unit tests, the production build and 88 desktop/mobile browser cases.
- Record official-photo recovery evidence and update smoke checks.


## 2026-10-16 — Zolotaya Balka missing bottle images

- Restore 8 missing bottle images from official product sources.
- Record source hashes, preparation details and measured image frames.
- Verify the restored images in desktop cards and mobile popups in Chromium and WebKit.


## 2026-10-16 — Massandra missing bottle images

- Restore 1 missing bottle image from official product sources.
- Record source hashes, preparation details and measured image frames.
- Verify the restored images in desktop cards and mobile popups in Chromium and WebKit.


## 2026-10-16 — Fanagoria missing bottle images

- Restore 1 missing bottle image from official product sources.
- Record source hashes, preparation details and measured image frames.
- Verify the restored images in desktop cards and mobile popups in Chromium and WebKit.


## 2026-10-16 — Derbent Vino missing bottle images

- Restore 1 missing bottle image from official product sources.
- Record source hashes, preparation details and measured image frames.
- Verify the restored images in desktop cards and mobile popups in Chromium and WebKit.
- Show the official caption and photo-label discrepancy in a product badge.


## 2026-10-16 — Bottle scale validation

- Resolve all 31 small-bottle observations through measured image frames.
- Verify 636 unchanged image hashes and 44 desktop/mobile sizing cases in Chromium and WebKit.
- Pass 232 tests, type checks, the build and both existing browser suites in both engines.
- Record per-producer commits and close the earlier framing observations.

## 2026-10-16 — zolotaya-balka image frames

- Record measured source-image frames for 35 products.
- Normalize visible bottle scale in group previews, product nodes and product details.
- Retain original image bytes and existing product identities.

## 2026-10-16 — vedernikov image frames

- Record measured source-image frames for 45 products.
- Normalize visible bottle scale in group previews, product nodes and product details.
- Retain original image bytes and existing product identities.

## 2026-10-16 — myskhako image frames

- Record measured source-image frames for 97 products.
- Normalize visible bottle scale in group previews, product nodes and product details.
- Retain original image bytes and existing product identities.

## 2026-10-16 — massandra image frames

- Record measured source-image frames for 45 products.
- Normalize visible bottle scale in group previews, product nodes and product details.
- Retain original image bytes and existing product identities.

## 2026-10-16 — kuban-vino image frames

- Record measured source-image frames for 103 products.
- Normalize visible bottle scale in group previews, product nodes and product details.
- Retain original image bytes and existing product identities.

## 2026-10-16 — koktebel image frames

- Record measured source-image frames for 28 products.
- Normalize visible bottle scale in group previews, product nodes and product details.
- Retain original image bytes and existing product identities.

## 2026-10-16 — inkerman image frames

- Record measured source-image frames for 17 products.
- Normalize visible bottle scale in group previews, product nodes and product details.
- Retain original image bytes and existing product identities.

## 2026-10-16 — fanagoria image frames

- Record measured source-image frames for 107 products.
- Normalize visible bottle scale in group previews, product nodes and product details.
- Retain original image bytes and existing product identities.

## 2026-10-16 — derbent-vino image frames

- Record measured source-image frames for 66 products.
- Normalize visible bottle scale in group previews, product nodes and product details.
- Retain original image bytes and existing product identities.

## 2026-10-16 — alma-valley image frames

- Record measured source-image frames for 41 products.
- Normalize visible bottle scale in group previews, product nodes and product details.
- Retain original image bytes and existing product identities.

## 2026-10-16 — abrau-durso image frames

- Record measured source-image frames for 52 products.
- Normalize visible bottle scale in group previews, product nodes and product details.
- Retain original image bytes and existing product identities.

## 2026-10-16 — Visible bottle sizing

- Size producer-map images from their measured visible frame.
- Preserve source aspect ratio and use one sizing component for previews, nodes and product details.
- Validate optional frame geometry and keep image-error placeholders available.
- Add a read-only frame measurement script and document the frame contract.

## 2026-10-16 — Complete lineup image review

- Review all 636 images on flat light and dark backgrounds.
- Correct the Decanter Saperavi 2017 background through built-in imagegen.
- Preserve source hashes, rejected output hashes and the exact replacement prompt.
- Record 31 open image-framing observations.
- Pass 65 map tests, the production build and eight Chromium/WebKit image cases.

## 2026-10-16 — Fanagoria Decanter background correction

- Regenerate the Rkatsiteli 2019 cutout from the original catalog image.
- Remove the visible stripe remnants outside the bottle. Keep the existing asset URL.
- Preserve the rejected output hashes and record the replacement prompt.
- Pass 65 map tests and eight Chromium and WebKit desktop and mobile checks. Rebuild and restart the local preview.

## 2026-10-16 — Bottle image validation

- Audit all referenced producer images and document the background-extraction workflow.
- Verify 82 edited images in Chromium and WebKit. Pass 48 desktop and mobile screen and interaction cases.
- Verify 231 tests with the full catalog snapshot, type checks, and the production build.
- Record the two unverified source photos and preserve their existing product-link behavior.

## 2026-10-16 — Kuban Vino bottle cutouts

- Replace 50 background images with reviewed transparent imagegen display assets.
- Fit the bottle frame and optimize WebP transfer size for desktop and mobile.
- Record exact prompts, source hashes, output hashes, and imagegen limitations.
- Reuse one generated cutout only for the two byte-identical source files.

## 2026-10-16 — Fanagoria bottle cutouts

- Replace 14 background images with reviewed transparent imagegen display assets.
- Fit the bottle frame and optimize WebP transfer size for desktop and mobile.
- Record exact prompts, source hashes, output hashes, and imagegen limitations.
- Use the labeled placeholder for the unverified wedding scene. Keep its catalog link.

## 2026-10-16 — Koktebel bottle cutouts

- Replace 2 background images with reviewed transparent imagegen display assets.
- Fit the bottle frame and optimize WebP transfer size for desktop and mobile.
- Record exact prompts, source hashes, output hashes, and imagegen limitations.

## 2026-10-16 — Alma Valley bottle cutouts

- Replace 1 background images with reviewed transparent imagegen display assets.
- Fit the bottle frame and optimize WebP transfer size for desktop and mobile.
- Record exact prompts, source hashes, output hashes, and imagegen limitations.

## 2026-10-16 — Zolotaya Balka bottle cutouts

- Replace 10 background images with reviewed transparent imagegen display assets.
- Fit the bottle frame and optimize WebP transfer size for desktop and mobile.
- Record exact prompts, source hashes, output hashes, and imagegen limitations.

## 2026-10-16 — Derbent Vino bottle cutouts

- Replace 5 background images with reviewed transparent imagegen display assets.
- Fit the bottle frame and optimize WebP transfer size for desktop and mobile.
- Record exact prompts, source hashes, output hashes, and imagegen limitations.
- Use the labeled placeholder for the official Cabernet Sauvignon photo whose label reads Cabernet Franc.

## 2026-10-16 — Producer map validation

- Validate all map data before the production build.
- Wait for visible images before browser screenshots.
- Verify 231 tests with the full source snapshot, type checks, the build, and both browser suites.
- Keep group evidence visible. Distinguish group methods from product facts.
- Use explicit producer form submission and recover image failures before hydration.
- Record source review, scanner integration checks, and production asset checks.

## 2026-10-16 — Мысхако map

- Add 20 groups and 97 product nodes in `myskhako.json`.
- Cover all 92 saved catalog cards. Add 5 verified products without catalog links.
- Record collection sources, exact catalog crosswalks, and asset provenance.

## 2026-10-16 — Кубань-Вино map

- Add 26 groups and 103 product nodes in `kuban-vino.json`.
- Cover all 97 saved catalog cards. Add 6 verified products without catalog links.
- Record collection sources, exact catalog crosswalks, and asset provenance.

## 2026-10-16 — Фанагория map

- Add 25 groups and 108 product nodes in `fanagoria.json`.
- Cover all 102 saved catalog cards. Add 6 verified products without catalog links.
- Record collection sources, exact catalog crosswalks, and asset provenance.

## 2026-10-16 — ЗМВ Коктебель map

- Add 10 groups and 28 product nodes in `koktebel.json`.
- Cover all 26 saved catalog cards. Add 2 verified products without catalog links.
- Record collection sources, exact catalog crosswalks, and asset provenance.

## 2026-10-16 — Ведерниковъ map

- Add 10 groups and 45 product nodes in `vedernikov.json`.
- Cover all 43 saved catalog cards. Add 2 verified products without catalog links.
- Record collection sources, exact catalog crosswalks, and asset provenance.

## 2026-10-16 — Массандра map

- Add 9 groups and 46 product nodes in `massandra.json`.
- Cover all 44 saved catalog cards. Add 2 verified products without catalog links.
- Record collection sources, exact catalog crosswalks, and asset provenance.

## 2026-10-16 — Инкерман map

- Add 6 groups and 17 product nodes in `inkerman.json`.
- Cover all 15 saved catalog cards. Add 2 verified products without catalog links.
- Record collection sources, exact catalog crosswalks, and asset provenance.

## 2026-10-16 — Alma Valley map

- Add 8 groups and 41 product nodes in `alma-valley.json`.
- Cover all 39 saved catalog cards. Add 2 verified products without catalog links.
- Record collection sources, exact catalog crosswalks, and asset provenance.

## 2026-10-16 — Золотая Балка map

- Add 10 groups and 43 product nodes in `zolotaya-balka.json`.
- Cover all 41 saved catalog cards. Add 2 verified products without catalog links.
- Record collection sources, exact catalog crosswalks, and asset provenance.

## 2026-10-16 — Дербент Вино map

- Add 8 groups and 67 product nodes in `derbent-vino.json`.
- Cover all 63 saved catalog cards. Add 4 verified products without catalog links.
- Record collection sources, exact catalog crosswalks, and asset provenance.

## 2026-10-16 — Additional producer map support

- Load each producer JSON through an explicit registry that works in both Vite and Nitro.
- Validate producer names, slug prefixes, and exact slugs across maps.
- Resolve exact catalog identities before producer metadata.
- Show an explicit placeholder when a verified image is unavailable.
- Add producer selection to the preview and reset map state on producer navigation.
- Test graph registration, exact lookup, local assets, and catalog crosswalks.

## 2026-10-16 — Mobile wine popup

- Replace the mobile bottom card with a centered modal popup.
- Open full product details from a bottle or «О выбранном вине».
- Keep the initial recognized product selected without covering the map on entry.
- Preserve the map position and scale when the popup closes.
- Keep the desktop side card and the parent map and shelf dialogs.
- Prevent WebKit keyboard focus from reaching the underlying shelf dialog.
- Verify 176 unit tests, type checks, the production build, and both complete browser suites.

## 2026-10-16 — Product-line map review completion

- Resolve the seven implementation review findings from Claude Opus 5.5 Max.
- Record the follow-up approval with non-blocking notes.
- Keep long product details accessible in compact desktop windows.
- Add shared browser regressions for 767/768 px and compact desktop cards.

## 2026-10-15 — Producer product-line map

- Replace the six-example Abrau-Durso map with a grouped product graph.
- Store 52 products and package variants in one producer JSON file.
- Preserve 14 families, 32 catalog slugs, 3 verified aliases, and 20 products without catalog links.
- Select and locate the recognized product when the guide opens.
- Keep the recognized marker when the user selects another product.
- Add selectable gray products, source dates, and relative price positioning.
- Add desktop side details and mobile bottom details.
- Add mouse pan, native touch pan, keyboard navigation, zoom, and a return control.
- Add a direct noindex review route at `/lineup/abrau-durso`.
- Add local source images and graph validation tests.
- Restore shelf-dialog focus from the clicked opener in WebKit.
- Keep mobile and short-height detail actions reachable through normal scrolling.
- Preserve keyboard focus when groups and details change.
- Anchor expand-all to the visible group after canvas movement.
- Improve gray product text contrast in both themes.
- Verify 176 unit tests, type checks, a production build, and the Chromium and WebKit browser suites.

## 2026-10-06 — Yandex.Metrika

- Add the owner-supplied counter `113460637` to all pages.
- Preserve the supplied initialization settings and asynchronous loader.
- Add the no-JavaScript image fallback at the start of the body.
- Send page views after successful client navigation. Keep the initial page view in the supplied script.
- Update the analytics documentation.
- Publish isolated release `10632011` on Princess. All 169 tests, type checks, and the Linux build passed.
- Verify all five public pages, client navigation, the fallback image, and blocked-loader behavior.
- Confirm HTTP 200 from the real Metrika loader and page-view endpoint.

## 2026-09-29 — Presentation files in git

- `public/presentations/` (pptx and pdf, 56 MB) is in git now. The page `/presentation`
  works from a clone (owner message of 2026-09-29 about 22:46).

## 2026-09-29 — Hackathon direct URL

- Remove `/hackaton` from the sitemap and public navigation.
- Add a robots.txt disallow rule and noindex metadata and response headers.
- Keep the page and its existing age gate available through the direct URL.
- Published release `0c2f964` on Princess. Local and Linux checks passed all 169 tests and type checks.
- Verified staged and public headers, HTML metadata, sitemap exclusion, navigation, direct access, and service health.


## 2026-09-29

### Hackathon landing publication

- Publish `/hackaton`, linked `/android` and `/ideas`, and the verified version 0.1.4 APK.
- Deploy isolated release `600fd2ae25a3eab4d338b2cd3dccbd21e5435b2e` from `codex/hackaton-release`.
- Preserve the deployed presentation page and both presentation files.
- Verify 169 tests, type checks, the Linux build, and public browser checks.
- Set Android release metadata to the published APK bytes and SHA-256.

## 2026-09-29

### Presentation project card

- Added a full-width card below the GitHub and Google Drive cards.
- Link to `/hackaton` and reuse the presentation card styles.
- Published release `8d07fad`. Verified 165 tests, type checks, the Linux build, and four public viewport widths.
- The target `/hackaton` page remains outside the production release and returns HTTP 404.

### Presentation resource links

- Added GitHub and Google Drive cards below the presentation video.
- Reuse the layout and card styles of the PowerPoint and PDF links.
- Open the owner-supplied URLs in new tabs.
- Published release `dbdd3b6`. Verified 165 tests, type checks, the Linux build, and four public viewport widths.

### Presentation video

- Added a video section below the PowerPoint and PDF links.
- Use the reserved URL `/presentation/video.mp4` with native controls and inline phone playback.
- Show a placeholder until the recording is available.
- Keep the future recording outside Git and document its public file location.
- Published release `c615490` and verified the public placeholder and presentation downloads.

### Presentation publication

- Published `/presentation` and both files at `https://chtozavino.ru/presentation`.
- Use release `36fb8e2` on the isolated `codex/presentation-release` branch.
- Base the release on the deployed scanner and keep other pending pages in this working tree.
- Point the presentation logo to the scanner at `/`.
- Verified 165 production tests, type checks, the Linux build, public file checksums, and browser behavior.

### Presentation files

- Replaced the browser slideshow at `/presentation` with adjacent PowerPoint and PDF links.
- Use the exact PowerPoint file supplied by the owner and export all 49 slides to PDF.
- Keep both links side by side at phone and desktop widths.
- Keep the white page, product branding, shared age gate, and canonical URL.
- Keep the presentation files outside Git and include them in the local production build.
- Document file preparation for a fresh checkout.
- Verified type checks, all 169 tests, and the production build.
- Verified both file responses, PowerPoint download, navigation, and adjacent links at four viewport widths in both themes.

### Ideas beyond recognition

- Added `/ideas` with three implemented scenarios, four interactive demos, and six mockups, in this order.
- Identify the available application and scope limits for each implemented scenario.
- Reuse the existing result dialogs with a selector for three local example wine cards.
- Label future concepts as inactive interface sketches.
- Add links from `/hackaton` and the shared footer, page metadata, and a sitemap entry.
- Verified type checks, all 169 existing tests, and the production build.
- Verified five viewport widths from 320 to 1440 pixels in both themes, all four dialogs, example selection, focus return, and navigation.


### Browser presentation

- Added `/presentation` with a cover, WebApp, Android, Telegram, and demo slide.
- Use a white background in both system themes without changing the saved theme.
- Reuse the landing page screenshots, product identity, and verified application links.
- Add keyboard navigation, touch navigation, slide selection, progress, and fullscreen support.
- Keep the shared age gate and hide the site header and footer on this route.
- Add a presentation link to `/hackaton` and a sitemap entry.
- Verified type checks, all 169 existing tests, and the production build.
- Added `test:presentation`. All five slides passed browser checks at seven viewport sizes from 320 to 1920 pixels.
- Verified age gating, bounded navigation, direct slide URLs, reloads, touch events, fullscreen, and theme preservation in the production build.

### Hackathon landing page

- Added `/hackaton` with WebApp, Android App, and Telegram Bot sections.
- Show desktop and mobile WebApp screenshots together. Each screenshot opens at full size.
- Highlight Android recognition without internet, including underground parking.
- Reuse the configured APK URL and shared release metadata.
- Link to the WebApp, the Android page, and `@ChtoZaVinoBot`.
- Keep the shared age gate and theme switcher. Add canonical and social metadata and a sitemap entry.
- Verified type checks, all 169 tests, and the production build.
- Verified five viewport widths in both themes, image loading, platform anchors, and navigation.
- Verified production HTML, image responses, and the APK download response.

### Android application landing page

- Added the `/android` landing page.
- Added a responsive light and dark layout with verified Pixel 8 screenshots.
- Added offline, image-search, QR, barcode, privacy, catalogue, accelerator, history,
  theme, and compatibility benefits.
- Added a versioned APK download action with configurable file and public URL values.
- Kept the generated APK outside Git.
- Added a local streaming route for the versioned APK.
- Added Android navigation to the shared header and footer context.
- Added Android search metadata, `SoftwareApplication` structured data, and a sitemap
  entry.
- Added automated coverage for content, release metadata, screenshot signatures,
  download routing, and navigation.
- Verified type checks, all 169 tests in 14 files, and the production build.
- Verified the APK response headers and the HTTP 404 response for an invalid file name.
- Verified the desktop and mobile layouts in the light and dark themes.

### Current-theme icon button

- Replaced the theme select with a sun or crescent moon button that shows the current palette.
- Follow the system theme until an explicit user choice and save only after a click.
- Retained saved choices, early palette application, and synchronization between tabs.
- Kept a 44px keyboard-accessible button on desktop and mobile.
- Verified all 165 tests, type checks, and the production build.
- Verified 10 system and saved-preference combinations and both icons with reload persistence in the browser.

### Product name and header logo

- Replaced the source-portal wordmark with the shared bottle-scanner logo and `Что за вино?`.
- Reused the product identity in the age gate and footer.
- Updated the browser title, social metadata, structured data, and installed app name.
- Preserved the artwork colors in both themes and adapted the header for narrow screens.
- Verified both header themes, the 320px layout, type checks, all 165 tests, and the production build.

### Header theme selector

- Added `Авто`, `Светлая`, and `Тёмная` to the page header.
- Store the selection in local storage and apply it before the first paint.
- Follow system theme changes in `Авто` and synchronize the selection between tabs.
- Apply the selected theme to dialogs, mobile actions, native controls, and browser theme colors.
- Keep the header controls within the 320px layout.
- Verified type checks, all 165 tests, and the production build.
- Verified both palettes, saved selection, tab synchronization, and the mobile header in a component preview.

### Shared product branding

- Replaced the Telegram-bot-derived favicon and PWA icon set with the repository-level product logo.
- Used the shared SVG directly for the favicon and the shared PNG for install, maskable, Apple touch, and social-image derivatives.
- Kept the source-portal wordmark in the page header.
- Added a regression check that the published favicon matches the shared SVG exactly.
- Verified all 165 tests, type checks, and the production build.

### Result-aware Abrau-Durso guide

- Connected the product-line guide to the resolved wine producer and slug.
- Marked an exact Abrau-Durso map match as `ВАШЕ ВИНО`.
- Changed the fixed fallback marker to `ПРИМЕР · ДЕМО` for other producers.
- Added a separate result card for an Abrau-Durso wine that does not have one of the six map nodes.
- Kept that separate wine outside unverified collection tiers.
- Added producer normalization and exact-slug regression tests.
- Verified all 165 tests, type checks, and the production build.

### Product-line catalog images

- Replaced the generic bottle silhouettes on the Abrau-Durso line map.
- Added six local catalog images from the `Своё Вино` 2026-09-17 snapshot.
- Preferred the `patched` image for `Удельное Ведомство Императорское, брют`.
- Used the catalog `main` image for the other five map wines.
- Added transparent WebP exports and image-source regression checks.
- Verified the dark desktop dialog, all 164 tests, type checks, and the production build.

### Taste inference audit, open data, and dish illustrations

- Corrected sweet and semisweet analogues so they run before dry varietal analogues.
- Corrected Russian-language inference patterns that used ASCII-only JavaScript word tokens.
- Reworded the summary to separate the source sugar category from inferred tasting characteristics.
- Prevented color descriptions from becoming floral or full-body evidence.
- Kept gentle astringency at the medium tannin level.
- Added build-time grape aggregates from the public Wine Reviews dataset.
- Added visible dataset, license, sample-count, and no-match disclosures.
- Stored no review text and no critic score.
- Added three generated editorial illustrations for the default regional dish recommendations.
- Added fixed image dimensions, lazy loading, alternative text, and an image-free fallback.
- Added regression tests for the corrected inference, aggregates, sweet styles, and pilot images.
- Verified all 163 tests, type checks, and the production build.

### Taste passport and regional dishes

- Replaced the fictional story action with `Паспорт вкуса`.
- Added deterministic body, acidity, tannin, sweetness, fruit, and oak estimates.
- Extracted source-backed aroma families from the resolved `Своё Вино` description.
- Added one international style analogue with explicit similarity and difference text.
- Replaced the fictional store products with three named dishes from distinct regional cuisines.
- Used source pairing categories before local style rules.
- Labeled every dish result as source-backed or style-derived.
- Added focused tests for profile bounds, aroma evidence, cuisine diversity, source evidence, and international analogues.
- Verified all 152 tests, type checks, and the production build.

### PWA review fixes

- Changed `registerType` from `autoUpdate` to `prompt`. An updated service worker now waits and does not reload an open page.
- Added light and dark `theme-color` metadata.
- Added narrow and wide home-page screenshots to the manifest.
- Corrected the offline statement: the app shell opens offline from the second online visit.
- Documented the server-rendered `/api/config` payload in the cached page.
- Added `npm run test:pwa`, a Chromium check for install, offline, cache, and update behavior.
- Added screenshot, update-mode, and theme-color assertions to the PWA tests and the contract check.
- Verified all 151 tests, type checks, the production build, and `npm run test:pwa`.

### Complete result metadata fallback

- Added an exact server-side wine lookup through the official `api.vino-svoe.ru` JSON endpoint.
- Kept the 12 local records as the mock and fast metadata path.
- Validated the returned slug, bottle image path, fields, redirects, response size, and timeout.
- Normalized source cards into the existing Web UI wine contract.
- Changed `catalogMode` from `demo` to `source-fallback`.
- Added source metadata normalization and failure tests.
- Verified the real Massandra slug through the local production build.
- Verified all 150 tests, type checks, and the production build.

### Owner-supplied shelf examples

- Replaced the Wikimedia shelf example with three unique photographs from the project owner.
- Added an accessible example selector before group matching.
- Converted the photographs to metadata-free WebP files below the upload limit.
- Kept every example on the same `/v1/group/match` path as an uploaded shelf photograph.
- Verified all 141 tests, type checks, and the production build.

### Production response status repair

- Preserved actionable matcher status codes through the single-bottle prediction proxy.
- Kept unexpected matcher statuses and invalid responses mapped to HTTP 502.
- Added regression tests for HTTP 400, 401, 408, 413, 415, 502, 503, and 504.
- Verified all 138 tests, type checks, and the production build.
- Deployed revision `11ebfbf` on Princess.
- Verified HTTP 413 for a JPEG dimension bomb and HTTP 503 for matcher overload.
- Verified the production shelf flow with 93 selectable and matched bottles.

## 2026-09-28

### Search discovery

- Kept the complete scanner page in server-rendered HTML while the 18+ gate blocks interaction as an overlay.
- Kept `Найти вино по фото` as the primary page heading.
- Added the canonical URL, Open Graph metadata, Twitter card metadata, and JSON-LD for the website and web application.
- Added `robots.txt` and a one-URL sitemap.
- Changed the legacy catalog redirects to HTTP 308.
- Added a seven-day cache policy for static reference assets.
- Added focused search-discovery tests and manual response checks.

### Matcher availability check

- Added a server-side matcher readiness check to `GET /api/config`.
- Derived `/healthz` from `NUXT_PREDICTION_ENDPOINT` without exposing the matcher URL to the browser.
- Added a 2-second readiness timeout and strict `{"status":"ok"}` validation.
- Disabled photo selection and shelf mode when the configured matcher is unavailable.
- Kept mock mode available without an upstream request.
- Verified all 125 tests, type checks, and the production build.

### Progressive Web App

- Added `@vite-pwa/nuxt` with a generated manifest, Workbox service worker, and automatic updates.
- Added a network-first page cache and precached the Nuxt bundles and app-shell assets.
- Added regular, maskable, and Apple touch icons from the Telegram bot wine-glass mark.
- Excluded photo uploads, `/api/`, and `/v1/` from Workbox runtime caches.
- Added PWA asset tests and production contract checks.
- Verified all 117 tests, type checks, the production build, live PWA endpoints, and browser metadata.

### Age gate and result experiences

- Added a mandatory 18+ gate with one local storage value and an explicit blocked state.
- Added four local actions after a wine result: products, label explanation, story, and product-line guide.
- Added a simulated SuperLenta flow with three fictional domestic products and one visible promotion label.
- Added a Syrah and Viognier explanation with an explicit illustrative-content notice.
- Added rotating fictional stories with a future-audio callout.
- Added an interactive Abrau-Durso map with zoom, current-wine navigation, selection, and public source links.
- Removed live retailer and geolocation calls from the rendered result UI.
- Added focused age and experience data tests.
- Verified all 115 tests, type checks, the production build, and three evaluator contract requests.
- Verified the desktop and 390 px mobile layouts in dark mode.

### Shelf group matching

- Connected the existing «Вся полка» tab to same-origin `POST /v1/group/match`.
- Reused `NUXT_PREDICTION_ENDPOINT` and derived the group path without a new environment variable.
- Added a bounded server proxy with response validation, timeout handling, and disconnect cancellation.
- Rendered matcher masks and normalized bottle controls on the returned shelf preview.
- Opened the ready wine match for each bottle without a second recognition request.
- Added explicit unmatched, empty, unavailable, retry, and stale-response states.
- Updated shelf browser tools, contract tests, state tests, and service documentation.
- Verified 115 tests, type checks, and the production build.

### Princess deployment preparation

- Kept «Вся полка» selectable and replaced its scanner with a temporary-unavailable view.
- Removed shelf upload and camera actions from the disabled view.
- Added a server guard that rejects shelf requests before image parsing or SAM3 access.
- Made shelf processing opt-in through `NUXT_SHELF_MODE=enabled`.
- Recorded the Princess capacity check and deployment boundary.
- Verified 103 tests, type checks, and the production build.
- Added `/api/predict` for browser requests so Princess can preserve its protected public evaluator route.

### Repository integration

- Moved the Web UI into `svoe-vino-lab/webui`.
- Excluded the standalone Git history, dependencies, generated output, and local reports.
- Updated the default evaluator path for the new directory depth and the current 2026-09-17 package.
- Added Web UI verification to the root GitLab CI configuration.

## 2026-09-15

### Shelf photo mode

- Added «Вся полка» beside the existing single-bottle mode.
- Added real SAM3 segmentation through our portal API and canonical `SAM3_ENDPOINT`.
- Added photo orientation normalization, metadata removal, validated masks, and original-image crops.
- Added numbered bottle controls, zoom, and a wine popup with the source link and food recommendations.
- Deferred recognition until the user selects a bottle. Preserved explicit mock identity disclosure.
- Added cancellation, retry, empty results, malformed response handling, and response limits.
- Added a public shelf example with CC BY 2.5 attribution.
- Added service and state checks. All 102 tests pass in seven files.
- Verified the production API with 94 real bottle masks and crops from the public example.
- Verified browser tools, wine popups, food recommendations, reset, and the unchanged official evaluator.
- Added a bounded retry for transient SAM3 connection failures observed during model loading.

### Demo service boundary

- Confirmed that the Web UI queries our portal API for stores and recommendations.
- Clarified that our server-side service owns retailer access and returns the prepared response.
- Documented the current Nuxt deployment and the stable contract for a later separate backend.
- Checked the client and server call sites. No runtime change was needed.

### Food recommendations

- Added «Подобрать 3 продукта к вину» after a matched wine.
- Added explicit geolocation and manual store selection.
- Integrated the live Globus directory, store context, search, and product details.
- Added three distinct food ideas with source prices, units, availability, conditions, images, and links.
- Kept the wine result visible and retained mock recognition disclosure.
- Added cancellation, partial stock, source error, distant store, and location denial states.
- Added request isolation and limited retailer response parsing.
- Added state, location, stock, pairing, and provider boundary tests.
- Verified 75 tests, type checks, production build, live food API, browser tool flow, and the unchanged evaluator.

### Photo search page

- Replaced the catalog UX with the dedicated «Найти вино по фото» home page.
- Added a responsive upload and single-result workspace in the source visual style.
- Automatically submit valid photo selections through the existing evaluator API.
- Show the best match bottle, title, and direct source portal link.
- Preserve successful prediction links when metadata fails or times out.
- Removed local catalog, filter, modal, and detail-page interfaces.
- Redirect old catalog bookmarks to the scanner and old detail links to the source portal.
- Added request state and metadata failure tests.
- Verified 41 tests, type checks, production build, and three official evaluator requests.
- Verified the complete demo upload through the browser tool surface.

### Initial implementation

- Created the repository with an empty initial commit.
- Added the portal specification, API contract, architecture, and acceptance plan.
- Created the private GitLab project `ashmelev/svoe-vino-webui`.
- Added the Nuxt catalog, filters, search, sorting, and exact slug detail pages.
- Added 12 source-backed demo wine records and local visual assets.
- Added the photo scanner with previews, cancellation, retries, and explicit mock results.
- Added the evaluator-compatible mock route and configurable upstream proxy.
- Added responsive styles, system dark mode, and native keyboard-accessible dialogs.
- Added optional WebMCP catalog tools and verified their input validation.
- Added 30 passing tests and a passing production build.
- Verified the unchanged official evaluator against the production mock endpoint with three images.
- Added GitLab CI and setup documentation.
- Aligned the package engine range and setup guide with the Nuxt runtime requirements.
